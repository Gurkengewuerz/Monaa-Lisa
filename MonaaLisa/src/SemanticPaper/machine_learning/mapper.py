import concurrent
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from object.paper import Paper
from object.relation import Relation
from util.logger import Logger


class Mapper:

    def __init__(self, paper: Paper):
        self.paper = paper
        self.logger = Logger("Mapper")
        self.logger.info(f"Initialized Mapper for paper: {self.paper.title}")


    """
        20-August-2025 - Lenio & Reviewed by Nico
        Abstract: Compares a new embedding with existing embeddings to find similar papers.
        Args:
        - new_embedding: The embedding of the new paper.
        - existing_embeddings: A dictionary of existing embeddings where keys are paper IDs and values are numpy
        arrays of embeddings.
        - threshold: A float representing the similarity threshold for considering two embeddings as similar.
        Returns: A dictionary where keys are paper IDs and values are similarity scores.
    """
    def compare_embeddings(self, existing_embeddings, threshold=0.7):
        similarities = defaultdict(float)
        # No longer creating this array on every call to process_chunk (Nico suggestion)
        new_emb = np.array(self.paper.embedding.content).reshape(1, -1)

        def process_chunk(chunk_items):
            chunk_results = {}
            for entry_id, existing_emb in chunk_items:
                if entry_id != self.paper.entry_id and existing_emb is not None:
                    sim = float(cosine_similarity(new_emb, existing_emb.content.reshape(1, -1))[0][0])
                    if sim >= threshold:
                        chunk_results[entry_id] = sim
            return chunk_results

        def chunks(data, size=100):
            # Implemented Nico's suggestion for better chunking
            items = list(data.items())
            for i in range(0, len(data), size):
                yield items[i:i + size]

        with ThreadPoolExecutor(max_workers=4) as executor:
            chunk_futures = [
                executor.submit(process_chunk, chunk)
                for chunk in chunks(existing_embeddings)
            ]

            for future in concurrent.futures.as_completed(chunk_futures):
                similarities.update(future.result())

        return similarities

    """
    20-August-2025 - Lenio
    Abstract: Maps the paper's embedding to existing embeddings and returns PaperRelation objects
    Returns: A list of PaperRelation objects representing the relations found.
    """
    def map_paper(self, existing_embeddings):
        similarities = self.compare_embeddings(existing_embeddings)
        relations = []
        for entry_id, similarity in similarities.items():
            relation = Relation(
                source_id=self.paper.entry_id,
                target_id=entry_id,
                confidence=similarity
            )
            relations.append(relation)
        return relations
