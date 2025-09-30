from playground import Playground
import arxiv as arx
from SemanticPaper.api.arxiv import ArxivAPI
from object.paper import Paper


class ArxivPlayground(Playground):

    def __init__(self):
        super().__init__(name="Arxiv",
                       description="A playground for testing arxiv-related functionalities.")
        self.arxiv_client = ArxivAPI()


    def test(self):
        self.logger.info("Testing arxiv functionalities...")
        latest = self.arxiv_client.fetch_latest_paper()
        papers = arx.Search(query="Theta and zeta functions for odd-dimensional locally symmetric spaces of rank one", max_results=5).results()
        self.logger.info(f"Paper attributes: ")
        self.logger.info(f"Latest Paper Entry ID: {latest.entry_id}")
        for paper in papers:
            xpaper = Paper.from_arxiv(paper)
            self.logger.info(f"Paper Entry ID: {xpaper.entry_id}")