import asyncio
import os

from SemanticPaper.api.semantic_scholar import SemanticScholarAPI
from playground import Playground
from SemanticPaper.api.arxiv import ArxivAPI
from object.paper import Paper
import dotenv
dotenv.load_dotenv()


"""
27-December-2025 - Lenio
A playground for testing semantic scholar functionalities.
"""
class SemanticScholarPlayground(Playground):

    def __init__(self):
        super().__init__(name="SemanticScholar-Arxiv",
                       description="A playground for testing semantic scholar functionalities.")


    def test(self):
        self.logger.info("Testing semantic scholar functionalities...")
        semanticscholar_client = SemanticScholarAPI(os.environ["SEMANTIC_SCHOLAR_API_KEY"])
        arxiv_client = ArxivAPI()
        pape = semanticscholar_client.fetch_paper("9e5e96f78f4e5f53fa0dc8f090d189ceae5bac7b")
        print(type(pape))
        print(type(semantic_paper_to_dict(pape)))
        print(semantic_paper_to_dict(pape))

"""
24-December-2025 - Lenio
Converts a semantic scholar Paper object (or list of such objects) to a dictionary.
Handles nested objects recursively.
Args:
    obj: A semantic scholar Paper object or a list of such objects.
Returns:
    dict: A dictionary representation of the Paper object or a list of such dictionaries.
"""
def semantic_paper_to_dict(obj):
    if isinstance(obj, list):
        return [semantic_paper_to_dict(x) for x in obj]
    if hasattr(obj, 'raw_data'):
        return obj.raw_data
    if hasattr(obj, '__dict__'):
        return {k: semantic_paper_to_dict(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
    return obj