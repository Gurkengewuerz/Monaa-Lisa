from util.logger import Logger
from abc import abstractmethod


class Playground:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = Logger(f"Playground-{self.name}")

    @abstractmethod
    def test(self):
        pass