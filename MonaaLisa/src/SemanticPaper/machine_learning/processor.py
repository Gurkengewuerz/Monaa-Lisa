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
        if not text or not text.strip():
            self.logger.warning("Empty text provided for embedding")
            return None
            
        chunks = [text[i:i + 512] for i in range(0, len(text), 512)]
        embeddings = []
        
        for chunk in chunks:
            if chunk.strip(): 
                emb = self._model.get_model().encode(chunk)
                embeddings.append(emb)
        
        if not embeddings:
            self.logger.warning("No valid chunks found for embedding")
            return None
            
        embeddings = np.array(embeddings)
        result = np.mean(embeddings, axis=0)
        self.logger.debug(f"Created embedding with shape: {result.shape}")
        return result


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
            if abstract_emb is not None:
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
                if section_emb is not None:
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
            ref_texts = [ref.title for ref in self.paper.references]
            self.logger.info(f"Processing references: {' '.join(ref_texts)}")
            ref_emb = self.create_section_embedding(" ".join(ref_texts))
            # Check if embedding valid
            if ref_emb is not None:
                combined_embeddings.append(ref_emb)
                weights.append(0.2)
            else:
                self.logger.warning("No valid embedding for references found.")

        if not combined_embeddings:  # Check if no embeddings were created
            return None

        weights = np.array(weights) / sum(weights)
        combined_embeddings = [emb for emb in combined_embeddings if emb is not None]

        try:
            # Debug: Log embedding shapes
            if combined_embeddings:
                shapes = [emb.shape for emb in combined_embeddings]
                self.logger.debug(f"Embedding shapes: {shapes}")
                
                # Ensure all embeddings have the same shape
                expected_shape = combined_embeddings[0].shape
                valid_embeddings = []
                valid_weights = []
                
                for i, emb in enumerate(combined_embeddings):
                    if emb.shape == expected_shape:
                        valid_embeddings.append(emb)
                        valid_weights.append(weights[i])
                    else:
                        self.logger.warning(f"Skipping embedding with shape {emb.shape}, expected {expected_shape}")
                
                if not valid_embeddings:
                    self.logger.error("No valid embeddings with consistent shape")
                    return None
                
                # Renormalize weights
                valid_weights = np.array(valid_weights)
                valid_weights = valid_weights / np.sum(valid_weights)
                
                emb_matrix = np.stack(valid_embeddings, axis=0)
                return np.average(emb_matrix, axis=0, weights=valid_weights)
            else:
                self.logger.error("No embeddings to process")
                return None
        except Exception as e:
            self.logger.error(f"Error while calculating average: {e}")
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
