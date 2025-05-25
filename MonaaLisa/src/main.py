from SemanticPaper.api.semanticscholar import SemanticScholarAPI
from SemanticPaper.logger.logger import setup_logger
from dotenv import load_dotenv
import os

logger = setup_logger()

semantic = SemanticScholarAPI()

load_dotenv(".env_public")

UPDATE_INTERVAL = int(os.environ.get("ARXIV_FETCH_INTERVAL", 3600))

def entry():
    logger.info(f"Starting SemanticPaper! Updating arXiv every {UPDATE_INTERVAL}")

def main():
    entry()

if __name__ == "__main__":
    main()