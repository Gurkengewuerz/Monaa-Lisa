from sentence_transformers import SentenceTransformer
from src.api.arxiv import fetch_one_paper

"""
Testing it as of 4th May 2025 with this Pretrained Sentence Transformer
replace this later with SciBERT or allenai/specter
"""
model = SentenceTransformer("all-MiniLM-L6-v2")


"""
04-May-2025 - Basti
Abstract: Just a quick check to see if I actually retrieve a random paper from a random category and can work with it
Args: None
Returns: The metadata of the random paper


Additional Comment: I should start writing unit tests..
"""
def fetch_test():
    paper = fetch_one_paper()
    if paper:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(str(author) for author in paper.authors)}")
        print(f"Published: {paper.published}")
        print(f"Abstract: {paper.summary}")
        print(f"PDF URL: {paper.pdf_url}")
        print(f"Entry ID: {paper.entry_id}")
    else:
        print("No paper found! Something went wrong fetching the arXiv API... or my code :(")