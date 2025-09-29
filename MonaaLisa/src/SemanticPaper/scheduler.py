import multiprocessing
import threading
from datetime import datetime
from SemanticPaper.api.arxiv import ArxivAPI
from apscheduler.schedulers.background import BackgroundScheduler
from Database.db import db_base, engine
from util.logger import Logger
from SemanticPaper.config.category_loader import get_semanticpaper_categories
from Database.db import (
    create_program_run,
    is_category_historically_completed,
    mark_category_historically_completed
)



"""
Original File by Basti - 13-August-2025
Refactored into a class by Lenio - 29-September-2025
"""
class Scheduler:

    def __init__(self, arxiv_client: ArxivAPI):
        self.logger = Logger("Scheduler")
        # Queue to buffer fetched Paper objects for embedding workers
        self._arxiv_client = arxiv_client
        self.paper_queue = multiprocessing.Queue()
        self.current_program_run_id = None
        self.scheduler_lock = threading.Lock()
        self.historical_fetch_state = {"running": False}

    """
    13-August-2025 - Basti
    Abstract: Fetches the newest paper (1 per category) daily and enqueues into paper_queue.
    Args:
    - None
    Returns: None
    """
    def daily_fetch(self):
        categories = get_semanticpaper_categories()
        self.logger.info(f"Fetching newest paper for categories: {categories}")
        for cat in categories:
            self._arxiv_client.get_rate_limiter().wait()
            papers = self._arxiv_client.fetch_papers(category=cat, amount=1)
            for paper in papers:
                if paper:
                    self.paper_queue.put(paper)
                    self.logger.info(f"Enqueued paper: {paper.title}")

    """
    13-August-2025 - Basti
    Abstract: Fetches historical papers in batches per category and enqueues into paper_queue.
    Args:
    - None
    Returns: None
    """
    def historical_fetch(self):
        with self.scheduler_lock:
            if self.historical_fetch_state["running"]:
                self.logger.info("Historical fetch already in progress")
                return
            self.historical_fetch_state["running"] = True
        try:
            if not self.current_program_run_id:
                self.logger.error("No active program run ID")
                return
            categories = get_semanticpaper_categories()
            for cat in categories:
                if is_category_historically_completed(self.current_program_run_id, cat):
                    continue
                offset = self.historical_fetch_state.get(cat, 0)
                self._arxiv_client.get_rate_limiter().wait()
                papers, has_more = self._arxiv_client.fetch_historical_batch(cat, batch_size=50, start_offset=offset)
                if papers:
                    for paper in papers:
                        if paper:
                            self.paper_queue.put(paper)
                    self.logger.info(f"Enqueued {len(papers)} historical papers for {cat}")
                self.historical_fetch_state[cat] = offset + 50
                if not has_more:
                    mark_category_historically_completed(self.current_program_run_id, cat)
                    self.logger.info(f"Category {cat} historical fetch completed")
        except Exception as e:
            self.logger.error(f"Error in historical_fetch: {e}")
        finally:
            with self.scheduler_lock:
                self.historical_fetch_state["running"] = False

    """
    13-August-2025 - Basti
    Abstract: Starts the background scheduler for daily and historical fetch tasks.
    Args:
    - None
    Returns: BackgroundScheduler
    """
    def start_scheduler(self):
        if BackgroundScheduler is None:
            self.logger.error("Cannot start scheduler: APScheduler missing")
            return None
        db_base.metadata.create_all(bind=engine)
        self.current_program_run_id = create_program_run()
        if not self.is_running():
            self.logger.error("Failed to create program run")
            return None
        scheduler = BackgroundScheduler()
        # Schedule daily_fetch at 0,6,12,18
        for hr in [0, 6, 12, 18]:
            scheduler.add_job(self.daily_fetch, 'cron', hour=hr, minute=0, id=f"daily_fetch_{hr}")
        # Schedule historical_fetch hourly, start now
        scheduler.add_job(self.historical_fetch, 'interval', hours=1, next_run_time=datetime.now(), id='historical_fetch')
        scheduler.start()
        self.logger.info(f"Scheduler started (run ID {self.current_program_run_id})")
        return scheduler

    def is_running(self):
        return self.current_program_run_id is not None