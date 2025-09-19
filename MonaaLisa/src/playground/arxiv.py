from playground.playground import Playground


class ArxivPlayground(Playground):

    def __init__(self):
        super().__init__(name="Arxiv Playground",
                       description="A playground for testing arxiv-related functionalities.")


    def test(self):
        print("Testing arxiv functionalities...")
        # todo: rewrite arxiv file to a class and use it here

if __name__ == "__main__":
    playground = ArxivPlayground()