from abc import abstractmethod


class Playground:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.test()

    @abstractmethod
    def test(self):
        pass