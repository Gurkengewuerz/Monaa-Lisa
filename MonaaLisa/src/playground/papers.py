from object.paper import Paper
from playground.playground import Playground


class PaperPlayground(Playground):

    def __init__(self):
        super().__init__(name="Paper Playground",
                       description="A playground for testing paper-related functionalities.")


    def test(self):
        print("Testing paper functionalities...")
        sample_paper = Paper.from_arxiv({"title": "Sample Paper", "authors": "Author Fleck", "summary": "This is a sample summary.", "published": "2024-01-01", "id": "http://arxiv.org/abs/1234.5678"})
        list_of_papers = [sample_paper, sample_paper]


if __name__ == "__main__":
    playground = PaperPlayground()