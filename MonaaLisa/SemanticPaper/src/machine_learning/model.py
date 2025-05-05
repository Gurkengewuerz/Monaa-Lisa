from sentence_transformers import SentenceTransformer
from src.api.arxiv import fetch_one_random_paper, read_meta, categories
import arxiv as arx
import torch
"""
Testing it as of 4th May 2025 with this Pretrained Sentence Transformer
replace this later with SciBERT or allenai/specter
"""
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = SentenceTransformer("all-MiniLM-L6-v2")
model = model.to(device)
print("Using device:", device)


"""
04-May-2025 - Basti
Abstract: Parses the data and using the given Model embeds it into a abstract vector
Args:  

- paper: Current fetched paper: arx.Result

Returns: Dict containing the title and its abstracted data
"""
def parse_data(paper: arx.Result) -> dict:
    print("Reading current paper...\n")
    read_meta(paper)

    """ 
    
    Compact the title + summary into one
    As of now, it uses the summary of the paper as context
    Later on in development it should somehow use the full paper

    Havent tried out the full text yet, it will probably not fit into the model as of now.
     
    """
    text = paper.title + ". " + paper.summary
    embedding = model.encode(text)

    return {
        "Text": text,
        "Embedding": embedding
    }
    
"""
04-May-2025 - Basti
Abstract: 
Args:
Returns: 
"""
def parse_category(category: str, amount: int):
    if category not in categories:
        print("Invalid category! Choose one of these: \n")
        print(categories)
        return



"""
04-May-2025 - Basti
Abstract: Just a quick check to see if I actually retrieve a random paper from a random category and can work with it
Args: None
Returns: The metadata of the random paper


Additional Comment: I should start writing unit tests..
"""
def fetch_test():
    paper = fetch_one_random_paper()
    if paper:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(str(author) for author in paper.authors)}")
        print(f"Published: {paper.published}")
        print(f"Abstract: {paper.summary}")
        print(f"PDF URL: {paper.pdf_url}")
        print(f"Entry ID: {paper.entry_id}")
    else:
        print("No paper found! Something went wrong fetching the arXiv API... or my code :(")