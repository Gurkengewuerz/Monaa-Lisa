from playground import Playground
from SemanticPaper.api.arxiv import ArxivAPI


class ArxivPlayground(Playground):

    def __init__(self):
        super().__init__(name="Arxiv",
                       description="A playground for testing arxiv-related functionalities.")
        self.arxiv_client = ArxivAPI()


    def test(self):
        self.logger.info("Testing arxiv functionalities...")
        latest = self.arxiv_client.fetch_latest_paper()
        self.logger.info(f"Paper attributes: {attributes}")
        self.logger.info(f"Latest Paper Title: {latest.title}")