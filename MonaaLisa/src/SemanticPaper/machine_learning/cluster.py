import numpy as np
import re
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from util.logger import Logger
from ..api.arxiv import fetch_papers, fetch_latest_paper, CS_CG_CATEGORY
from ..machine_learning.model import parse_description_data, parse_full_data

logger = Logger("Cluster")

"""
04-May-2025 - Basti
Abstract: Takes a vectorized embedding and labels that into a cluster
Args: 

- embedding: Dictionary containing the vector
- n_cluster: The number of clusters to form as well as the number of centroids to generate

Returns: Cluster label for each vector, the fitted KMeans object
"""
def cluster(embeddings, n_cluster=30):
    embeddings = np.array(embeddings)
    kmeans = KMeans(n_clusters=n_cluster, random_state=42)
    labels = kmeans.fit_predict(embeddings)
    return labels, kmeans

"""
04-May-2025 - Basti
Abstract: Takes an vector and reduces it to 2D which is necessary to be visualized using matplotlib
Args:
- embeddings: List of embedding vectors
- labels: Cluster labels for each embedding
- titles: Optional list of titles for annotation

TO-DO: better description of what is happening here, this stuff is a little confusing - will write more comments later

Returns: a image File of the clustered result
"""
def visualize(embeddings, labels, titles=None):
    embeddings = np.array(embeddings)
    perplexity = min(30, len(embeddings) - 1)
    tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
    reduced = tsne.fit_transform(embeddings)
    plt.figure(figsize=(18,13))
    scatter = plt.scatter(reduced[:,0], reduced[:,1], c=labels, cmap='tab10')
    plt.colorbar(scatter, label="cluster")
    plt.title("Paper Clusters (cs.CG)")
    plt.xlabel("t-SNE1")
    plt.ylabel("t-SNE2")
    if titles:
        for i, title in enumerate(titles):
            safe_title = re.sub(r"[\\{}]", "", title)
            plt.annotate(safe_title, (reduced[i, 0], reduced[i, 1]), fontsize=6, alpha=0.6)
    plt.tight_layout()
    plt.savefig("clusters.png")
    plt.close()


"""
04-May-2025 - Basti
Abstract: Takes n amount of random papers and inputs them into the clustering/visualization process of this tool
Args:

- amount: Takes the n amount of papers to be put into a clus ter
- n_clusters: The number of clusters to form as well as the number of centroids to generate

Returns: A .png file of the generated cluster on the local disk!
"""
def cluster_papers_in_category(amount: int, n_clusters: int = 5):
    papers = fetch_papers(category=CS_CG_CATEGORY, amount=amount)
    if not papers:
        logger.warning("No papers fetched.")
        return [], [], []
    embeddings, titles, paper_objs = [], [], []
    for paper in papers:
        parsed = parse_full_data(paper)
        if parsed is None:
            continue
        embeddings.append(parsed["Embedding"])
        titles.append(paper.title)
        paper_objs.append(paper)
    if not embeddings:
        logger.warning("No embeddings generated.")
        return [], [], []
    labels, _ = cluster(embeddings, n_clusters)
    # left out for now, wont be necessary on the server (doesnt have that much computing power anyway)
    # visualize(embeddings, labels, titles) 
    return paper_objs, embeddings, labels