import multiprocessing
import threading
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from Database.db import db_base, engine
from config import cfg
from util.logger import Logger
from SemanticPaper.api.arxiv import fetch_papers, fetch_historical_batch
from SemanticPaper.api.arxiv import rate_limiter 
from SemanticPaper.config.category_loader import get_semanticpaper_categories
from Database.db import (
    create_program_run,
    is_category_historically_completed,
    mark_category_historically_completed,
    ensure_historical_start,
    update_historical_progress,
)
import threading
import queue

logger = Logger("Scheduler")

# Queue to buffer fetched Paper objects for embedding workers (thread-safe)
# will now be initialized after constants are defined
paper_queue = None
current_program_run_id = None
scheduler_lock = threading.Lock()
historical_fetch_state = {"running": False}
goal_dates_cache = {}

# Tuning knobs via env vars
HISTORICAL_FETCH_INTERVAL_SECONDS = cfg.get_int(
    "semanticpaper",
    "historical_fetch_interval_seconds",
    int(os.getenv("HISTORICAL_FETCH_INTERVAL_SECONDS", "60"))
)
QUEUE_MAX_SIZE = cfg.get_int(
    "semanticpaper",
    "queue_max_size",
    int(os.getenv("QUEUE_MAX_SIZE", "200"))
)

# Initialize bounded queue now that QUEUE_MAX_SIZE is defined
paper_queue = queue.Queue(maxsize=QUEUE_MAX_SIZE)


"""
13-August-2025 - Basti
Abstract: Fetches the newest paper (1 per category) daily and enqueues into paper_queue.
Args:
- None
Returns: None
"""
def daily_fetch():
    categories = get_semanticpaper_categories()
    logger.info(f"Fetching newest paper for categories: {categories}")
    for cat in categories:
        rate_limiter.wait()
        papers = fetch_papers(category=cat, amount=1)
        for paper in papers:
            if paper:
                paper_queue.put(paper)
                logger.info(f"Enqueued paper: {paper.title}")

"""
13-August-2025 - Basti
Abstract: Fetches historical papers in batches per category and enqueues into paper_queue.
Args:
- None
Returns: None
"""
def historical_fetch():
    global current_program_run_id
    with scheduler_lock:
        if historical_fetch_state["running"]:
            logger.info("Historical fetch already in progress")
            return
        historical_fetch_state["running"] = True
    try:
        try:
            qsize = paper_queue.qsize()
        except NotImplementedError:
            qsize = 0
        if qsize >= QUEUE_MAX_SIZE:
            logger.info(f"Queue size {qsize} >= max {QUEUE_MAX_SIZE}; skipping fetch this cycle")
            return
        if not current_program_run_id:
            logger.error("No active program run ID")
            return
        categories = get_semanticpaper_categories()
        for cat in categories:
            if is_category_historically_completed(current_program_run_id, cat):
                continue
            goal_date = goal_dates_cache.get(cat)
            if goal_date is None:
                try:
                    papers_goal, _ = fetch_historical_batch(cat, batch_size=1, start_offset=0)
                    goal_date = papers_goal[0].published if papers_goal else None
                    goal_dates_cache[cat] = goal_date
                except Exception as e:
                    logger.error(f"Failed to determine goal date for {cat}: {e}")
                    goal_date = None
            # Ensure we have a start record for this category/runwith optional goal
            if not ensure_historical_start(current_program_run_id, cat, goal_date):
                logger.info(f"Skipping {cat} this cycle: could not create start record")
                continue
            offset = historical_fetch_state.get(cat, 0)
            rate_limiter.wait()
            papers, has_more = fetch_historical_batch(cat, batch_size=50, start_offset=offset)
            if papers:
                for paper in papers:
                    if paper:
                        paper_queue.put(paper)
                logger.info(f"Enqueued {len(papers)} historical papers for {cat}")
                try:
                    min_date = min(p.published for p in papers if p is not None)
                    update_historical_progress(current_program_run_id, cat, min_date)
                except Exception as e:
                    logger.error(f"Failed updating progress for {cat}: {e}")
            historical_fetch_state[cat] = offset + (len(papers) if papers else 0)
            if not has_more:
                final_oldest = None
                if papers and len(papers) > 0:
                    try:
                        final_oldest = min(p.published for p in papers if p is not None)
                    except Exception:
                        final_oldest = None
                mark_category_historically_completed(current_program_run_id, cat, final_oldest)
                logger.info(f"Category {cat} historical fetch completed")
    except Exception as e:
        logger.error(f"Error in historical_fetch: {e}")
    finally:
        with scheduler_lock:
            historical_fetch_state["running"] = False

"""
13-August-2025 - Basti
Abstract: Starts the background scheduler for daily and historical fetch tasks.
Args:
- None
Returns: BackgroundScheduler
"""
def start_scheduler():
    global current_program_run_id
    if BackgroundScheduler is None:
        logger.error("Cannot start scheduler: APScheduler missing")
        return None
    db_base.metadata.create_all(bind=engine)
    current_program_run_id = create_program_run()
    if not current_program_run_id:
        logger.error("Failed to create program run")
        return None
    scheduler = BackgroundScheduler()
    # Schedule daily_fetch at 0,6,12,18
    for hr in [0, 6, 12, 18]:
        scheduler.add_job(daily_fetch, 'cron', hour=hr, minute=0, id=f"daily_fetch_{hr}")
    # Schedule historical_fetch  start now
    scheduler.add_job(
        historical_fetch,
        'interval',
        seconds=HISTORICAL_FETCH_INTERVAL_SECONDS,
        next_run_time=datetime.now(),
        id='historical_fetch'
    )
    scheduler.start()
    logger.info(f"Scheduler started (run ID {current_program_run_id})")
    return scheduler
