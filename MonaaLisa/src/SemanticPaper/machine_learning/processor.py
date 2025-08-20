import concurrent
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from object.paper import Paper
from sklearn.metrics.pairwise import cosine_similarity
from util.logger import Logger
from SemanticPaper.machine_learning.model import Model


class PaperProcessor:
    def __init__(self, paper: Paper, model: Model):
        self.paper = paper
        self.logger = Logger("PaperProcessor")
        self._keywords = []
        self._model = model

    """
    03-August-2025 - Lenio
    Abstract: Prepares the paper for processing, extracts metadata.
    Args:
    - known_hashes: Set -> Will be ThreadSafeSet in the future when multithreading branch is merged
    Returns: True if the paper was processed, False if not.
    """
    def prepare_paper(self, known_hashes):
        worker_name = threading.current_thread().name
        self.logger.info(f"[{worker_name}] Processing paper: {getattr(self.paper, 'title', 'Unknown Title')}")
        paper_hash = self.paper.hash_paper_details()
        if paper_hash not in known_hashes:
            self.logger.info(f"Extracting metadata for: {self.paper.title}")
            self.paper.extract_metadata()
            self.logger.info(f"Finished extracting metadata for: {self.paper.title}")
            return True
        self.logger.info(f"[{worker_name}] Paper already processed: {getattr(self.paper, 'title', 'Unknown Title')}")
        return False

    """
    03-August-2025 - Lenio
    Abstract: Creates an embedding for a section of the paper's text.
    Args:
    - text: The text to be embedded.
    Returns: A numpy array representing the embedding of the text.
    """
    def create_section_embedding(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            return None
        chunks = [text[i:i + 512] for i in range(0, len(text), 512)]
        embeddings = [self._model.get_model().encode(c) for c in chunks]

        # Filter out potential None or empty results from encode
        valid_embeddings = [emb for emb in embeddings if emb is not None and emb.size > 0]

        if not valid_embeddings:
            return None

        return np.mean(valid_embeddings, axis=0)


    """
    03-August-2025 - Lenio
    Abstract: Creates a structured embedding for the paper, including abstract, sections, and references.
    Args: None
    Returns: A numpy array representing the structured embedding of the paper.
    """
    def create_structured_embedding(self):
        embeddings = {}
        combined_embeddings = []
        weights = []

        # Abstract (40%)
        if self.paper.abstract:
            abstract_emb = self.create_section_embedding(self.paper.abstract)
            # Check if embedding valid
            if abstract_emb is not None and abstract_emb.size > 0:
                self.logger.debug(f"Processing abstract: {self.paper.abstract[:50]}...")
                combined_embeddings.append(abstract_emb)
                weights.append(0.4)
            else:
                self.logger.warning("No valid embedding for abstract found.")

        # Sections (40%)
        sections = self.paper.get_sections()
        if sections:
            for section in sections:
                section_emb = self.create_section_embedding(section['content'])
                # Check if embedding valid
                if section_emb is not None and section_emb.size > 0:
                    title = section['title'].lower()
                    self.logger.info(f"Processing section: {title}")

                    if any(key in title for key in ['conclusion', 'discussion']):
                        weight = 0.15
                    elif any(key in title for key in ['introduction', 'background']):
                        weight = 0.1
                    elif 'method' in title or 'approach' in title:
                        weight = 0.08
                    else:
                        weight = 0.07

                    combined_embeddings.append(section_emb)
                    weights.append(weight)
                else:
                    self.logger.warning(f"No valid embedding for section {section['title']} found.")
                    self.logger.debug(f"Section content: {section['content']}")

        # References (20%)
        if self.paper.references:
            ref_texts = [ref.title for ref in self.paper.references if ref.title]
            self.logger.info(f"Processing references: {' '.join(ref_texts)}")
            ref_emb = self.create_section_embedding(" ".join(ref_texts))
            # Check if embedding valid
            if ref_emb is not None and ref_emb.size > 0:
                combined_embeddings.append(ref_emb)
                weights.append(0.2)
            else:
                self.logger.warning("No valid embedding for references found.")

        if not combined_embeddings:  # Check if no embeddings were created
            return None

        # Filter embeddings one last time to be safe
        valid_embeddings_with_weights = [
            (emb, weight) for emb, weight in zip(combined_embeddings, weights)
            if emb is not None and emb.size > 0
        ]

        if not valid_embeddings_with_weights:
            return None

        final_embeddings, final_weights = zip(*valid_embeddings_with_weights)

        # Normalize weights for the valid embeddings
        final_weights = np.array(final_weights)
        final_weights /= final_weights.sum()

        try:
            return np.average(np.array(final_embeddings), weights=final_weights, axis=0)
        except ValueError as e:
            self.logger.error(f"Error while calculating average: {e}")
            self.logger.error(f"Shape of final_embeddings: {[e.shape for e in final_embeddings]}")
            return None

    """
    18-July-2025 - Lenio
    Abstract: Extracts keywords from the paper's summary
    """
    def extract_keywords(self):
        # Placeholder for keyword extraction logic
        # This should be replaced with actual keyword extraction logic
        keywords = self.paper.abstract.split()[:5]


    """
    18-July-2025 - Lenio
    Abstract: Calculates a value based on the paper, takes in account the structure of the paper.
    """
    def evaluate_paper_text_as_score(self):
        pass

    def get_keywords(self):
        return self._keywords

