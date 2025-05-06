# Nico
from abc import ABC, abstractmethod
from typing import List
from models import Publication


class DataSource(ABC): # ABC = abstrakte BASISklasse
    '''
    Die DataSource-Oberklasse definiert ein generisches Interface für das Abrufen und Parsen von 
    Publikationendas von spezifischen Datenquellen abgeleitet
    Es ist eine ABC also abstrakt.
    So können wir für arxiv, open-access usw eigene Klassen erstellen die der scraper dann sammeln kann
    '''
    @abstractmethod
    def fetch_publications(self, query: str, max_results: int = 5) -> List[Publication]:
        '''
        Fetches publications with given configs
        '''
    
    @abstractmethod
    def parse_publications(self, raw_data: str) -> List[Publication]:
        '''
        Fetches publications with given configs
        '''
    