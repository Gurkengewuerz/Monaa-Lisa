import arxiv as arx
from object.paper import Paper
from util.logger import Logger
import os
from SemanticPaper.api.rate_limiter import RateLimiter

"""
Original File by Basti - 04-May-2025
Refactored into a class by Lenio - 20-September-2025
Abstract: This class provides methods to interact with the arXiv API, including fetching papers by category,
fetching the latest paper, and reading paper metadata.
"""
class ArxivAPI:

    def __init__(self):
        self.logger = Logger("ArxivAPI")
        self.client = arx.Client()
        self.rate_limiter = RateLimiter(min_interval=float(os.getenv("ARXIV_MIN_INTERVAL", "3.0")))


    """
    29-September-2025 - Lenio
    Abstract: Returns the rate limiter instance.
    Returns: RateLimiter instance
    """
    def get_rate_limiter(self) -> RateLimiter:
        return self.rate_limiter

    """
    04-May-2025 - Basti
    Abstract: Retrieves a paper and prints out its metadata
    Args:
        - paper: The current paper to be read out
    
    Returns: Metadata of the provided Paper
    """
    def read_meta(self, paper: Paper):
        if paper:
            self.logger.info(f"Title: {paper.title}\n")
            self.logger.info(f"Authors: {', '.join(str(author) for author in paper.authors)}\n")
            self.logger.info(f"Published: {paper.published}\n")
            self.logger.info(f"Abstract: {paper.abstract}\n")
            self.logger.info(f"PDF URL: {paper.url}\n")
            self.logger.info(f"Entry ID: {paper.entry_id}\n")


        else:
            self.logger.error("No Paper!")

    """
    04-May-2025 - Basti
    Abstract: Takes one paper from the cs_CG category and proceeds to retrieve the newest paper from that category
    Args: None 
    Returns: One arXiv paper -> Result
    """
    def fetch_latest_paper(self) -> Paper:
        self.rate_limiter.wait()
        search = arx.Search(
            query=f"cat:cs.CG",
            max_results=1,
            sort_by=arx.SortCriterion.SubmittedDate,
            sort_order=arx.SortOrder.Descending
        )
        results = list(self.client.results(search))
        return Paper.from_arxiv(results[0]) if results else None

    """
    04-May-2025 - Basti
    Abstract: Fetches a x amount of papers in y category
    Args:
    
    - category: Category from one of arXiv's category
    - amount: Amount of papers to be fetched starting from the newest papers
    
    Returns: List -> of fetches papers
    """
    def fetch_papers(self, category: str = "CS_CG_CATEGORY", amount: int = 10) -> list:
        self.rate_limiter.wait()
        search = arx.Search(
            query=f"cat:{category}",
            max_results=amount,
            sort_by=arx.SortCriterion.SubmittedDate,
            sort_order=arx.SortOrder.Descending
        )
        papers = []
        for result in search.results():
            if result:
                paper = Paper.from_arxiv(result)
                paper.category = category
                papers.append(paper)
            else:
                papers.append(None)
        return papers


    def fetch_historical_batch(self, category: str = "CS_CG_CATEGORY", batch_size: int = 50, start_offset: int = 0) -> tuple[list[Paper], bool]:
        self.rate_limiter.wait()
        try:
            total_needed = start_offset + batch_size
            search = arx.Search(
                query=f"cat:{category}",
                max_results=total_needed,
                sort_by=arx.SortCriterion.SubmittedDate,
                sort_order=arx.SortOrder.Ascending
            )

            all_results = list(self.client.results(search))
            target_results = all_results[start_offset:start_offset + batch_size]
            papers = []
            for result in target_results:
                if result:
                    paper = Paper.from_arxiv(result)
                    paper.category = category
                    papers.append(paper)

            has_more = len(all_results) > total_needed
            self.logger.info(f"Fetched {len(papers)} historical papers for {category} (offset: {start_offset})")
            return papers, has_more

        except Exception as e:
            self.logger.error(f"Error fetching historical batch for {category}: {e}")
            return [], False