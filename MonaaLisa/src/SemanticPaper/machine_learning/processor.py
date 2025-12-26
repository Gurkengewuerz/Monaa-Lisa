import threading
# why do we type check here? to avoid circular imports 
from typing import TYPE_CHECKING

import numpy as np

from object.paper import Paper
from object.embedding import Embedding
from util.logger import Logger
from SemanticPaper.machine_learning.model import Model
# please let this finally fix the fuckinmg circular import issue
if TYPE_CHECKING:
    from SemanticPaper.machine_learning.reducer import UMAPReducer


class PaperProcessor:
    def __init__(self, paper: Paper, model: Model, reducer: 'UMAPReducer | None' = None):
        self.paper = paper
        self.logger = Logger("PaperProcessor")
        self._keywords = []
        self._model = model
        self._reducer = reducer

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
            try:
                self.paper.extract_metadata()
                self.logger.info(f"Finished extracting metadata for: {self.paper.title}")
            except Exception as e:
                self.logger.error(f"Unexpected error during metadata extraction for '{self.paper.title}': {e}")
                return False
            return True
        self.logger.info(f"[{worker_name}] Paper already processed: {getattr(self.paper, 'title', 'Unknown Title')}")
        return False

    """
    03-August-2025 - Lenio
    Abstract: Creates an embedding for a section of the paper's text.
    Args:
    - text: The text to be embedded.
    Returns: An Embedding object or None.
    """
    def create_section_embedding(self, text: str) -> Embedding | None:
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
        result_array = np.mean(embeddings, axis=0)
        self.logger.debug(f"Created embedding with shape: {result_array.shape}")
        return Embedding(content=result_array, belonging_paper_entry_id=self.paper.entry_id)


    """
    03-August-2025 - Lenio
    Abstract: Creates a structured embedding for the paper, including abstract, sections, and references.
    Args: None
    Returns: An Embedding object or None.
    """
    def create_structured_embedding(self) -> Embedding | None:
        combined_embeddings = []
        weights = []

        # Abstract (40%)
        if self.paper.abstract:
            abstract_emb = self.create_section_embedding(self.paper.abstract)
            if abstract_emb:
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
                if section_emb:
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
            if ref_texts:
                self.logger.info(f"Processing references: {' '.join(ref_texts)}")
                ref_emb = self.create_section_embedding(" ".join(ref_texts))
                if ref_emb:
                    combined_embeddings.append(ref_emb)
                    weights.append(0.2)
                else:
                    self.logger.warning("No valid embedding for references found.")

        if not combined_embeddings:
            self.logger.error("No embeddings were created to combine.")
            return None

        # Extract numpy arrays from Embedding objects for calculation
        embedding_arrays = [emb.content for emb in combined_embeddings]

        # Normalize weights
        final_weights = np.array(weights)
        final_weights /= final_weights.sum()

        try:
            # Ensure all arrays have the same shape before averaging
            first_shape = embedding_arrays[0].shape
            if not all(arr.shape == first_shape for arr in embedding_arrays):
                self.logger.error("Inconsistent embedding shapes cannot be averaged.")
                # Optional: Filter for consistent shapes if that's desired
                return None

            weighted_average = np.average(embedding_arrays, weights=final_weights, axis=0)
            emb = Embedding(belonging_paper_entry_id=self.paper.entry_id, content=weighted_average)
            self.paper._paper_txt = None
            self.paper._grobid_xml = None
            return emb
        except Exception as e:
            self.logger.error(f"Error while calculating weighted average of embeddings: {e}")
            return None


    """
    14 Dec 2025 - Basti
    Abstract: computes the 2D coordinates for the paper using the shared UMAP reducer
    Args:
    - existing_embeddings: dict -> of existing embeddings to consider for projection
    Returns: Tuple (x, y) or None if projection could not be computed
    """
    def compute_projection_coordinates(self, existing_embeddings: dict[str, Embedding], labels: dict[str, str] | None = None):
        if self._reducer is None:
            # this happens in case of not enough embeddings yet to fit the reducer
            self.logger.debug("UMAP reducer not available yet")
            return None
        if self.paper.embedding is None:
            self.logger.warning("Cannot compute projection without a paper embedding")
            return None

        """
        
        """
        combined_embeddings = dict(existing_embeddings)
        combined_embeddings[self.paper.entry_id] = self.paper.embedding
        # add label for this paper if available
        if labels is None:
            labels = {}
        
        labels = dict(labels)
        labels[self.paper.entry_id] = getattr(self.paper, "category", None)

        coords = self._reducer.transform(self.paper.embedding, combined_embeddings, labels)
        if coords is None:
            return None
        try:
            
            x, y = float(coords[0]), float(coords[1])
            return x, y
        except (TypeError, ValueError, IndexError):
            self.logger.error("Invalid projection coordinates returned by reducer: %s", coords)
            return None

    """
    18-July-2025 - Lenio
    Abstract: Extracts keywords from the paper's summary
    """
    def extract_keywords(self):
        # Placeholder for keyword extraction logic
        # This should be replaced with actual keyword extraction logic
        keywords = self.paper.abstract.split()[:5]

    def get_keywords(self):
        return self._keywords