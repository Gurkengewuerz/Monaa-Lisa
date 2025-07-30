from object.paper import Paper


class PaperProcessor:
    def __init__(self, paper: Paper):
        self.paper = paper
        self.paper_text = paper.extract_paper_text()
        self._keywords = []

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