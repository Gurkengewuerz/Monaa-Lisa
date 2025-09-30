from playground import Playground
from util.logger import Logger

from arxiv_playground import ArxivPlayground
from paper_playground import PaperPlayground

"""
29-September-2025 - Lenio
Abstract: Manages different playgrounds for testing various functionalities.
"""
class PlaygroundManager:

    def __init__(self):
        self.logger = Logger("PlaygroundManager")
        self.playgrounds = {}

    def register_playground(self, name, playground: Playground):
        self.playgrounds[name] = playground

    def get_playground(self, name):
        return self.playgrounds.get(name, None)

    def list_playgrounds(self):
        return list(self.playgrounds.keys())

    def run_all_tests(self):
        for name, playground in self.playgrounds.items():
            self.logger.info(f"Running test for playground: {name}")
            playground.test()

if __name__ == "__main__":
    manager = PlaygroundManager()
    # Example usage:
    # from playground.arxiv import ArxivPlayground
    # arxiv_playground = ArxivPlayground()
    # manager.register_playground("Arxiv", arxiv_playground)
    arxiv_playground = ArxivPlayground()
    paper_playground = PaperPlayground()
    manager.register_playground("Arxiv", arxiv_playground)
    manager.register_playground("Paper-Arxiv", paper_playground)
    manager.logger.info(f"Registered Playgrounds: {manager.list_playgrounds()}")
    manager.run_all_tests()