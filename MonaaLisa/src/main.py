from SemanticPaper.api.arxiv import ArxivAPI
from SemanticPaper.machine_learning.mapper import Mapper
from SemanticPaper.machine_learning.processor import PaperProcessor
from SemanticPaper.machine_learning.reducer import UMAPReducer
from SemanticPaper.scheduler import Scheduler
from util.logger import Logger
from Database.db import (
    save_paper_to_db,
    save_paper_relation,
    get_all_embeddings,
    get_embedding_labels,
    engine,
    update_paper_projection,
    get_entry_ids_missing_projection,
)
from Database.db_models import db_base
from dotenv import load_dotenv
from config import cfg
from SemanticPaper.machine_learning.model import Model
from SemanticPaper.config.category_loader import get_semanticpaper_categories
import threading
import faulthandler
import os
import signal
import sys

logger = Logger("Main")

load_dotenv(".env_public")
HASH_FILE = 'parsed_hashes.txt'

arxiv_client = ArxivAPI()
model = Model(arxiv_client)
scheduler = Scheduler(arxiv_client)
reducer = UMAPReducer()
# Initialize the embedding cache, which will store embeddings of papers to avoid fetching them from the db everytime
embedding_cache = {}
embedding_cache_lock = threading.Lock()
embedding_labels: dict[str, str | None] = {}
embedding_labels_lock = threading.Lock()
pending_projection_ids: set[str] = set()
pending_projection_lock = threading.Lock()
try:
    faulthandler.enable()
except Exception:
    pass
"""
25-May-2025 - Basti
Abstract: Loads the local parsed_hashes file
Args:
- None
Returns: Set filled with all parsed/known papers (hashed)
"""
def load_hashes():
    if not os.path.exists(HASH_FILE):
        return set()
    with open(HASH_FILE, "r") as f:
        return set(line.strip() for line in f)
"""
25-May-2025 - Basti
Abstract: Saves one hash string to the local parsed_hashes file
Args:
- hash_str: -> the hash of a peper
Returns: None
"""
def save_hash(hash_str):
    with open(HASH_FILE, "a") as f:
        f.write(hash_str + "\n")

"""
13-August-2025 - Basti
Abstract: Helper Function for the Entry() Method
Args:
- worker_id -> ID of one of x workers that have been assigned
Returns: None
"""
def paper_worker(worker_id, known_hashes):
    logger.info(f"Worker {worker_id} started")
    while True:
        paper =  scheduler.paper_queue.get()
        if paper is None:
            break
        active_categories = get_semanticpaper_categories()
        if getattr(paper, 'category', None) and paper.category not in active_categories:
            logger.warning(f"Worker {worker_id}: Category '{paper.category}' removed; skipping paper '{paper.title}'")
            continue
        processor = PaperProcessor(paper, model, reducer)
        if processor.prepare_paper(known_hashes):
            embedding = processor.create_structured_embedding()
            if embedding is not None:
                processor.paper.embedding = embedding
                mapper = Mapper(processor.paper)
                # Prepare embeddings snapshot for projection and mapping
                
                with embedding_cache_lock:
                    current_embeddings = embedding_cache.copy()
                with embedding_labels_lock:
                    current_labels = embedding_labels.copy()
                projection_embeddings = current_embeddings.copy()
                projection_embeddings[processor.paper.entry_id] = embedding

                """ - Basti - 19-December-2025
                with projection_labels, we add the current paper's category
                to ensure that supervised UMAP has the correct label information
                """
                projection_labels = current_labels.copy()
                projection_labels[processor.paper.entry_id] = processor.paper.category

                projection = processor.compute_projection_coordinates(
                    projection_embeddings,
                    projection_labels
                )
                if projection is not None:
                    # save the projection to the paper in the db
                    processor.paper.tsne = {"x": projection[0], "y": projection[1], "method": "umap"}
                else:
                    processor.paper.tsne = None

                relations = mapper.map_paper(current_embeddings)
                logger.info(f"Found {len(relations)} relations for {paper.title}")
                if save_paper_to_db(processor.paper):
                    if processor.paper.tsne is None:
                        mark_projection_pending(processor.paper.entry_id)
                    for relation in relations:
                        logger.info(f"Similar paper: {relation.source_id} with similarity score: {relation.confidence}")
                        save_paper_relation(relation)
                    # Save the embedding to the cache
                    with embedding_cache_lock:
                        embedding_cache[processor.paper.entry_id] = processor.paper.embedding
                    with embedding_labels_lock:
                        embedding_labels[processor.paper.entry_id] = processor.paper.category
                    reducer.notify_dataset_change(embedding_cache, embedding_labels)
                    save_hash(processor.paper.hash)
                    known_hashes.add(processor.paper.hash)
                    backfill_pending_projections()
    logger.info(f"Worker {worker_id} exiting")

"""
13-August-2025 - Basti
Abstract: Entry Point of SemanticPaper
Args:
- num_workers: Amount of workers to be used to fetch papers (they do not calculate their embeddings!)
Returns: None
"""
def main(num_workers: int = 5):
    log_level = cfg.get("semanticpaper", "log_level", os.getenv("LOG_LEVEL", "DEBUG"))
    logger.set_level(log_level)
    logger.info(f"Initializing scheduler system (log level={log_level})...")

    known_hashes = load_hashes()
    logger.info(f"Loaded {len(known_hashes)} known hashes")
    try:
        db_base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.warning(f"Failed to pre-create tables: {e}")
    logger.info("Loading existing embeddings into cache...")
    with embedding_cache_lock:
        embedding_cache.update(get_all_embeddings())
    with embedding_labels_lock:
        embedding_labels.update(get_embedding_labels())
    reducer.bootstrap(embedding_cache, embedding_labels)
    missing_ids = get_entry_ids_missing_projection()
    if missing_ids:
        with pending_projection_lock:
            pending_projection_ids.update(missing_ids)
        backfill_pending_projections()
    logger.info(f"Loaded {len(embedding_cache)} embeddings into cache.")
    logger.info("Starting scheduler...")
    scheduler.start_scheduler()
    if not scheduler.is_running():
        logger.error("Scheduler failed to start, exiting.")
        return

    logger.info(f"Starting {num_workers} worker threads...")
    threads = []
    for i in range(num_workers):
        t = threading.Thread(target=paper_worker, args=(i+1, known_hashes), name=f"Worker-{i+1}")
        t.start()
        threads.append(t)



    """Graceful shutdown helper - Basti - 13. August 2025"""
    def shutdown(signum, frame):
        logger.info("Shutdown signal received, stopping workers...")
        for _ in threads:
            scheduler.paper_queue.put(None)
        for t in threads:
            t.join()
        scheduler.shutdown()
        logger.info("All workers stopped, exiting.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("System running. Press Ctrl+C to stop.")
    signal.pause()


"""
What does these new functions do?
14-Dec-2025 - Basti

-> UMAP needs to "warm up" with some data, so if I would run a cold start
with UMAP, a lot of the papers would get NULL Values in the db -> useless
These methods help to keep track of which papers need to be backfilled later
"""


"""
14-Dec-2025 - Basti
Abstract: Marks a paper's projection as pending (to be backfilled later)
Args:
- entry_id: -> the entry_id of the paper
Returns: None
"""
def mark_projection_pending(entry_id: str):
    with pending_projection_lock:
        pending_projection_ids.add(entry_id)

"""
14 -Dec-2025 - Basti
Abstract: Retrieves the list of entry_ids pending projection
Args:
- None
Returns: List of entry_ids
"""
def get_pending_projection_ids() -> list[str]:
    with pending_projection_lock:
        return list(pending_projection_ids)

"""
14-Dec-2025 - Basti
Abstract: Clears an entry_id from the pending projection set
Args:
- entry_id: -> the entry_id of the paper
Returns: None
"""
def clear_pending_projection(entry_id: str):
    with pending_projection_lock:
        pending_projection_ids.discard(entry_id)

"""
14-Dec-2025 - Basti
Abstract: Backfills all pending projections using the current reducer and embedding cache
Args:
- None
Returns: None
"""
def backfill_pending_projections():
    pending_ids = get_pending_projection_ids()
    if not pending_ids or not reducer.has_model():
        return
    with embedding_cache_lock:
        embeddings_snapshot = embedding_cache.copy()
    with embedding_labels_lock:
        labels_snapshot = embedding_labels.copy()
    for entry_id in pending_ids:
        embedding = embeddings_snapshot.get(entry_id)
        if embedding is None:
            continue
        coords = reducer.transform(embedding, embeddings_snapshot, labels_snapshot)
        if coords is None:
            continue
        projection = {"x": float(coords[0]), "y": float(coords[1]), "method": "umap"}
        if update_paper_projection(entry_id, projection):
            clear_pending_projection(entry_id)



if __name__ == "__main__":
    workers = cfg.get_int("semanticpaper", "num_workers", int(os.getenv("NUM_WORKERS", str(5))))
    main(workers)