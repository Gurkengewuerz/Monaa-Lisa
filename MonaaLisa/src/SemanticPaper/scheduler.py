import multiprocessing
from apscheduler.schedulers.background import BackgroundScheduler
from util.logger import Logger
from SemanticPaper.api.arxiv import fetch_papers
from SemanticPaper.config.category_loader import get_semanticpaper_categories

logger = Logger("Scheduler")

# Queue to buffer fetched Paper objects for embedding workers
paper_queue = multiprocessing.Queue()

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
    categories = get_semanticpaper_categories()
    logger.info(f"Starting historical fetch for categories: {categories}")
    # Placeholder: implement batching logic down to first paper
    for cat in categories:
        # TODO: fetch all historical papers in batches
        pass
    logger.info("Completed historical fetch.")

"""
13-August-2025 - Basti
Abstract: Starts the background scheduler for daily and historical fetch tasks.
Args:
- None
Returns: BackgroundScheduler
"""
def start_scheduler():
    scheduler = BackgroundScheduler()
    # Schedule daily_fetch every day at 00:00 - TODO: Make this configurable (do we even have a proper .env for SemanticPaper?)
    scheduler.add_job(daily_fetch, 'cron', hour=0, minute=0, id='daily_fetch')
    # schedule historical_fetch once at startup (interval=0) or daily at 01:00
    scheduler.add_job(historical_fetch, 'cron', hour=1, minute=0, id='historical_fetch')
    scheduler.start()
    logger.info("Scheduler started with daily and historical fetch jobs.")
    return scheduler
