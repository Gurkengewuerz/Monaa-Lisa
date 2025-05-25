# from SemanticPaper.machine_learning.model import fetch_test
# from SemanticPaper.api.arxiv import fetch_one_random_paper, CS_CG_CATEGORY
# from SemanticPaper.machine_learning.cluster import cluster_papers_in_category
from SemanticPaper.api.semanticscholar import SemanticScholarAPI
from dotenv import load_dotenv
import os, logging
logging.basicConfig(
    filename='latest_semanticpaper.log',
    encoding='utf-8',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)
semantic = SemanticScholarAPI()

load_dotenv(".env_public")

UPDATE_INTERVAL = int(os.environ.get("ARXIV_FETCH_INTERVAL", 3600))

def entry():
    logger.info(f"Starting SemanticPaper! Updating arXiv every {UPDATE_INTERVAL}")

def main():
    entry()

if __name__ == "__main__":
    main()