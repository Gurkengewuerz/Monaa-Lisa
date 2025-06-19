from SemanticPaper.api.semanticscholar import SemanticScholarAPI
from SemanticPaper.api.arxiv import hash_paper_details, fetch_latest_paper, fetch_papers
from SemanticPaper.logger.logger import setup_logger
from Database.db import SessionLocal, Paper, save_to_db
from dotenv import load_dotenv
from SemanticPaper.machine_learning.model import parse_full_data, extract_tsne_coordinates
import concurrent.futures
import os
import time
import threading

logger = setup_logger()

semantic = SemanticScholarAPI()

load_dotenv(".env_public")

UPDATE_INTERVAL = int(os.environ.get("ARXIV_FETCH_INTERVAL", 3600))
HASH_FILE = 'parsed_hashes.txt'

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
25-May-2025 - Basti
Abstract: Saves one hash string to the local parsed_hashes file
Args:
- hash_str: -> the hash of a paper
Returns: None
"""
def process_paper(paper, known_hashes):
    worker_name = threading.current_thread().name
    logger.info(f"[{worker_name}] Processing paper: {getattr(paper, 'title', 'Unknown Title')}")
    paper_hash = hash_paper_details(paper)

    if paper_hash not in known_hashes:
        current_embedding = parse_full_data(paper)
        if current_embedding is not None:
            logger.info(f"[{worker_name}] Finished embedding for: {getattr(paper, 'title', 'Unknown Title')}")
            return (paper, paper_hash, current_embedding["Embedding"])
        logger.info(f"[{worker_name}] Failed to embed: {getattr(paper, 'title', 'Unknown Title')}")
        return None
    logger.info(f"[{worker_name}] Paper already processed: {getattr(paper, 'title', 'Unknown Title')}")
    return None


"""
25-May-2025 - Basti
Abstract: Continuously fetches the latest papers from arXiv, processes new ones in parallel, embeds them,
     saves results to the database and updates known hashes. Runs in an infinite loop with periodic updates (Default: Every Hours/3600s).
Args:
- max_workers: int -> Number of threads to use for parallel paper processing.
Returns: None
"""
def entry(max_workers:int = 4):
    logger.info(f"Starting SemanticPaper! Updating arXiv every {UPDATE_INTERVAL}s")
    known_hashes = load_hashes()

    logger.info(f"ThreadPoolExecutor will use {max_workers} workers.")

    while True:
        logger.info("Fetching latest 10 papers from arXiv...")
        latest_papers = fetch_papers(amount=10)
        new_papers = []
        embeddings = []
        paper_objs = []
        paper_hashes = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:

            results = executor.map(lambda paper: process_paper(paper, known_hashes), latest_papers)
            for result in results:
                if result:
                    paper, paper_hash, embedding = result
                    embeddings.append(embedding)
                    paper_objs.append(paper)
                    paper_hashes.append(paper_hash)
                    new_papers.append(paper)
                else:
                    pass

        if embeddings:
            tsne_coords = extract_tsne_coordinates(embeddings)
            for i, paper in enumerate(paper_objs):
                embedding_dict = {
                    "Embedding": embeddings[i],
                    "tsne1": tsne_coords[i][0],
                    "tsne2": tsne_coords[i][1]
                }
                save_to_db(paper, paper_hashes[i], embedding_dict)
                save_hash(paper_hashes[i])
                known_hashes.add(paper_hashes[i])
                logger.info(f"Saved paper with tSNE coords: {paper.title}")

        if not new_papers:
            logger.info("No new papers to process.")

        logger.info(f"Sleeping for {UPDATE_INTERVAL} seconds...")
        time.sleep(UPDATE_INTERVAL)


def main():
    entry(max_workers=5)

if __name__ == "__main__":
    main()