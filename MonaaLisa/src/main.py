from src.machine_learning.model import fetch_test
from src.api.arxiv import fetch_one_random_paper, categories
from src.machine_learning.cluster import cluster_papers_in_category

def main():
    cluster_papers_in_category(amount=30, n_clusters=5)
if __name__ == "__main__":
    main()