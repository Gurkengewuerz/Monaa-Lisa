from abc import ABC, abstractmethod
from typing import List
from MonaaLisa.src.datamodels.data_source import DataSource
from MonaaLisa.src.datamodels.models import Publication

class BaseScraper(ABC):
    """
    Abstract base class for scrapers

    Attributes:
        data_source (DataSource): An instance of a class that inherits from DataSource.
        query (str): The search query.
        max_results (int): The maximum number of results to retrieve.
        headers (dict): The headers to use for the requests.
    """
    
    # Default headers t fake a browser request
    DEFAULT_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'}
    def __init__(self, data_source: DataSource, query: str, max_results: int = 5, headers: dict = None):
        """
        Initializes the BaseScraper with the given attributes

        Args:
            data_source (DataSource): An instance of a class that inherits from DataSource.
            query (str): The search query.
            max_results (int): The maximum number of results to retrieve.
            headers (dict, optional): The headers to use for the requests. Defaults to None.
        """
        self.data_source = data_source
        self.query = query
        self.max_results = max_results        
        self.headers = headers if headers is not None else self.DEFAULT_HEADERS

    def scrape(self) -> List[Publication]:
        """
        Scrapes

        Returns:
            List[Publication]: A list of Publication
        """
        return self.data_source.fetch_publications(self.query, self.max_results)