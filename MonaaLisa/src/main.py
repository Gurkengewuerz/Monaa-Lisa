from SemanticPaper.machine_learning.mapper import Mapper
from SemanticPaper.machine_learning.processor import PaperProcessor
from SemanticPaper.api.semanticscholar import SemanticScholarAPI
from SemanticPaper.api.arxiv import fetch_papers
from util.logger import Logger
from Database.db import save_paper_to_db, save_paper_relation, get_all_embeddings
from dotenv import load_dotenv
from SemanticPaper.machine_learning.model import Model
import concurrent.futures
import os
import time

logger = Logger("Main")

semantic = SemanticScholarAPI()

load_dotenv(".env_public")

UPDATE_INTERVAL = int(os.environ.get("ARXIV_FETCH_INTERVAL", 3600))
HASH_FILE = 'parsed_hashes.txt'

model = Model()

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
Abstract: Continuously fetches the latest papers from arXiv, processes new ones in parallel, embeds them,
     saves results to the database and updates known hashes. Runs in an infinite loop with periodic updates (Default: Every Hours/3600s).
Args:
- max_workers: int -> Number of threads to use for parallel paper processing.
Returns: None
"""
def entry(max_workers:int = 4):
    logger.info(f"Starting SemanticPaper! Updating arXiv every {UPDATE_INTERVAL}s")
    known_hashes = load_hashes()
    existing_embeddings = get_all_embeddings()
    logger.info(f"ThreadPoolExecutor will use {max_workers} workers.")

    while True:
        logger.info("Fetching latest 10 papers from arXiv...")
        latest_papers = fetch_papers(amount=10)
        new_papers = []
        embeddings = []
        paper_objs = []
        paper_hashes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            processors = [PaperProcessor(paper, model) for paper in latest_papers]
            futures = [executor.submit(processor.prepare_paper, known_hashes) for processor in processors]

            for processor, future in zip(processors, futures):
                if future.result():
                    embedding = processor.create_structured_embedding()
                    if embedding is not None:
                        embeddings.append(embedding)
                        processor.paper.embedding = embedding
                        paper_objs.append(processor.paper)
                        paper_hashes.append(processor.paper.hash)
                        new_papers.append(processor.paper)

        if embeddings:
            tsne_coords = model.extract_tsne_coordinates(embeddings)
            logger.info(f"Extracted embeddings for {len(embeddings)} papers.")
            for i, paper in enumerate(paper_objs):
                mapper = Mapper(paper)
                embedding_dict = {
                    "Embedding": embeddings[i].tolist(),
                    "tsne1": tsne_coords[i][0],
                    "tsne2": tsne_coords[i][1]
                }

                relations = mapper.map_paper(existing_embeddings)
                logger.info(f"Found {len(relations)} relations for {paper.title}")
                for relation in relations:
                    logger.info(f"Similar paper: {relation.source_id} with similarity score: {relation.confidence}")
                    save_paper_relation(relation)
                save_paper_to_db(paper, paper_hashes[i], embedding_dict)
                save_hash(paper_hashes[i])
                known_hashes.add(paper_hashes[i])
        if not new_papers:
            logger.info("No new papers to process.")

        logger.info(f"Sleeping for {UPDATE_INTERVAL} seconds...")
        time.sleep(UPDATE_INTERVAL)


def main():
    entry(max_workers=5)

if __name__ == "__main__":
    main()