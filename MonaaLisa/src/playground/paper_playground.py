from playground import Playground
from SemanticPaper.api.arxiv import ArxivAPI
from object.paper import Paper


class PaperPlayground(Playground):

    def __init__(self):
        super().__init__(name="Paper-Arxiv",
                       description="A playground for testing paper-related functionalities.")


    def test(self):
        self.logger.info("Testing paper functionalities...")
        paper = Paper(entry_id="XM300", title="Analysis of complex things", authors=["Author A", "Author B"], abstract="yes this paper covers some complex things", published="2024-01-01", url="http://arxiv.org/pdf/XM300")
        self.logger.info(f"Sample Paper Title: {paper.title}")