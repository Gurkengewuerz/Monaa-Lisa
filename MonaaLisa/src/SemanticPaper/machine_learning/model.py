import numpy as np
from sentence_transformers import SentenceTransformer
from ..api.arxiv import fetch_latest_paper, read_meta, CS_CG_CATEGORY
from sklearn.manifold import TSNE
import numpy as np
import arxiv as arx
import torch

from object.paper import Paper
from util.logger import Logger

logger = Logger("Model")
"""
Testing it as of 4th May 2025 with this Pretrained Sentence Transformer
replace this later with SciBERT or allenai/specter
"""
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = SentenceTransformer("all-MiniLM-L6-v2")
model = model.to(device)
logger.info(f"Using device: {device}")

"""
04-May-2025 - Basti
Abstract: Parses the data and using the given Model embeds it into a abstract vector
Args:  

- paper: Current fetched paper: arx.Result

Returns: Dict containing the title and its abstracted data
"""
@DeprecationWarning
def parse_description_data(paper: arx.Result) -> dict:
    logger.info("Reading current paper...\n")
    read_meta(paper)

    """ 
    
    Compact the title + summary into one
    As of now, it uses the summary of the paper as context
    Later on in development it should somehow use the full paper

    Havent tried out the full text yet, it will probably not fit into the model as of now.
    Update: it does now in another method and this method is deprected.
     
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
def parse_full_data(paper: Paper, chunk_size: int = 512):
    logger.info("Reading current paper...\n")
    read_meta(paper)

    full_text = paper.extract_paper_text_legacy()
    if not full_text:
        logger.info("Processing PDF failed!")
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
        logger.info(f"Error processing embeddings for {paper.title} with error: {str(e)}")
        return None


"""
19-06-2025 - Basti
Abstract: Reduces a list of high-dimensional embedding vectors to 2D t-SNE coordinates for visualization/saving them easily into the database.
Args:
- embeddings: List or array of embedding vectors (e.g., output from parse_full_data)
- random_state: Seed for reproducibility (default: 42) - this ensures determinism

Returns: 
- Tuple -> of (tsne1, tsne2) tuples one per embedding (x,y)
"""
def extract_tsne_coordinates(embeddings, random_state=42):
    embeddings = np.array(embeddings)
    if len(embeddings) < 2:
        raise ValueError("At least two embeddings are required for t-SNE.")
    perplexity = min(30, len(embeddings) - 1)
    tsne = TSNE(n_components=2, random_state=random_state, perplexity=perplexity)
    reduced = tsne.fit_transform(embeddings)
    return [tuple(map(float, coords)) for coords in reduced]


"""
04-May-2025 - Basti
Abstract: 
Args:
Returns: 
"""
# def parse_category(category: str, amount: int):
#     if category not in categories:
#         logger.debug(("Invalid category! Choose one of these: \n")
#         logger.debug(categories)
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
        logger.debug(f"Title: {paper.title}")
        logger.debug(f"Authors: {', '.join(str(author) for author in paper.authors)}")
        logger.debug(f"Published: {paper.published}")
        logger.debug(f"Abstract: {paper.abstract}")
        logger.debug(f"PDF URL: {paper.url}")
        logger.debug(f"Entry ID: {paper.entry_id}")
    else:
        logger.debug("No paper found! Something went wrong fetching the arXiv API... or my code :(")