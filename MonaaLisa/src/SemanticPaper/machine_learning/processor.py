import threading

import numpy as np
from object.paper import Paper
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
        chunks = [text[i:i + 512] for i in range(0, len(text), 512)]
        embeddings = [self._model.get_model().encode(c) for c in chunks]
        return np.mean(embeddings, axis=0)

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
            self.logger.debug(f"Processing abstract: {self.paper.abstract[:50]}...")  # Log first 100 chars of abstract
            combined_embeddings.append(abstract_emb)
            weights.append(0.4)

        # Sections (40%)
        # Weigh each section based on its type
        sections = self.paper.get_sections()
        if sections:
            for section in sections:
                section_emb = self.create_section_embedding(section['content'])
                title = section['title'].lower()
                self.logger.info(f"Processing section: {title}")
                # Could be more sophisticated with NLP techniques, but for now we use simple keyword matching
                # Weigh conclusion and discussion sections higher, followed by introduction and background, then methods, and finally others
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

        # References (20%)
        if self.paper.references:
            ref_texts = [ref.title for ref in self.paper.references]
            self.logger.info(f"Processing references: {' '.join(ref_texts)}")
            ref_emb = self.create_section_embedding(" ".join(ref_texts))
            combined_embeddings.append(ref_emb)
            weights.append(0.2)

        if weights:
            weights = np.array(weights) / sum(weights)

        if combined_embeddings:
            return np.average(combined_embeddings, weights=weights, axis=0)
        return None

    """
    18-July-2025 - Lenio
    Abstract: Extracts keywords from the paper's summary
    """
    def extract_keywords(self):
        # Placeholder for keyword extraction logic
        # This should be replaced with actual keyword extraction logic
        keywords = self.paper.summary.split()[:5]


    """
    18-July-2025 - Lenio
    Abstract: Calculates a value based on the paper, takes in account the structure of the paper.
    """
    def evaluate_paper_text_as_score(self):
        pass

    def get_keywords(self):
        return self._keywords