import numpy as np
import re
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from src.api.arxiv import fetch_papers, fetch_one_random_paper
from src.machine_learning.model import parse_description_data, parse_full_data

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
def visualize(embeddings, labels, titles=None, categories=None):
    embeddings = np.array(embeddings)
    perplexity = min(30, len(embeddings) - 1)
    tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
    reduced = tsne.fit_transform(embeddings)
    plt.figure(figsize=(18,13))
    if categories:
        unique_cats = sorted(set(categories))
        cat_to_idx = {cat: i for i, cat in enumerate(unique_cats)}
        color_vals = [cat_to_idx[cat] for cat in categories]
        n_colors = len(unique_cats)
        if n_colors <= 20:
            cmap = cm.get_cmap('tab20', n_colors)
        else:
            cmap = cm.get_cmap('hsv', n_colors)
        scatter = plt.scatter(reduced[:,0], reduced[:,1], c=color_vals, cmap=cmap)
        plt.xticks([])
        plt.yticks([])
        handles = [plt.Line2D([0], [0], marker='o', color='w', label=cat,
                              markerfacecolor=cmap(i), markersize=10)
                   for i, cat in enumerate(unique_cats)]
        plt.legend(handles=handles, bbox_to_anchor=(1.05, 1), loc='upper left', title="Categories")
    else:
        scatter = plt.scatter(reduced[:,0], reduced[:,1], c=labels, cmap='tab10')
        plt.colorbar(scatter, label="cluster")
    plt.title("Paper Clusters by Category")
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
    papers = []
    seen_ids = set()
    tries = 0
    while len(papers) < amount and tries < amount*5:
        paper = fetch_one_random_paper()
        paper_id = getattr(paper, "entry_id", getattr(paper, "id", None))
        if paper and paper_id and paper_id not in seen_ids:
            papers.append(paper)
            seen_ids.add(paper_id)
        tries += 1
    if not papers:
        print("No papers fetched.")
        return
    embeddings, titles, categories = [], [], []
    for paper in papers:
        parsed = parse_full_data(paper)
        embeddings.append(parsed["Embedding"])
        titles.append(paper.title)
        categories.append(getattr(paper, "categories", [getattr(paper, "category", "unknown")])[0])
    labels, _ = cluster(embeddings, n_clusters)
    visualize(embeddings, labels, titles, categories)