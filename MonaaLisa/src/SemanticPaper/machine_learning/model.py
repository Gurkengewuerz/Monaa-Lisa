import numpy as np
from sentence_transformers import SentenceTransformer
from ..api.arxiv import fetch_latest_paper, read_meta, CS_CG_CATEGORY
from ..utils.paper import get_paper_text
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
def parse_description_data(paper: arx.Result) -> dict:
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
06-May-2025 - Basti
Abstract: Takes a whole paper and embeds them chunk by chunk (chunk size - in chars! - pre-defined in constructor)
Args:

- paper: The to be worked with paper
- chunk_size: size of chars in which the full text will be divided into

Returns: dict -> containing the Result/Embedding + total of processed chunks
"""
def parse_full_data(paper: arx.Result, chunk_size: int = 512):
    print("Reading current paper...\n")
    read_meta(paper)

    full_text = get_paper_text(paper)
    if not full_text:
        print("Processing PDF failed!")
        return

    try:
        chunks = [full_text[i:i + chunk_size] 
                 for i in range(0, len(full_text), chunk_size)]
        
        embeddings = []
        for c in chunks:
            c_embeddings = model.encode(c)
            embeddings.append(c_embeddings)

        final_embedding = np.mean(embeddings,axis=0)

        return {
            "Embedding": final_embedding,
            "Chunks_Processed": len(chunks)
        }
    except Exception as e:
        print(f"Error processing embeddings for {paper.title} with error: {str(e)}")
        return None
    
  
"""
04-May-2025 - Basti
Abstract: 
Args:
Returns: 
"""
# def parse_category(category: str, amount: int):
#     if category not in categories:
#         print("Invalid category! Choose one of these: \n")
#         print(categories)
#         return



"""
04-May-2025 - Basti
Abstract: Just a quick check to see if I actually retrieve a random paper from a random category and can work with it
Args: None
Returns: The metadata of the random paper


Additional Comment: I should start writing unit tests..
"""
def fetch_test():
    paper = fetch_latest_paper()
    if paper:
        print(f"Title: {paper.title}")
        print(f"Authors: {', '.join(str(author) for author in paper.authors)}")
        print(f"Published: {paper.published}")
        print(f"Abstract: {paper.summary}")
        print(f"PDF URL: {paper.pdf_url}")
        print(f"Entry ID: {paper.entry_id}")
    else:
        print("No paper found! Something went wrong fetching the arXiv API... or my code :(")