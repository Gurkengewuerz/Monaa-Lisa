from src.machine_learning.model import fetch_test, parse_data
from src.api.arxiv import fetch_one_random_paper

def main():
    print(parse_data(fetch_one_random_paper()))

if __name__ == "__main__":
    main()