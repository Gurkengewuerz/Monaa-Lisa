from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class Publication:
    '''
    Basic Informationen die jede Publikation hat.
    Also name, autor, jahr, titel ...
    Macht es einfacher entsprechende Daten isoliert zu betrachten
    '''
    title: str
    authors: List[str]
    summary: str
    published: datetime
    url: str

    def to_json(self) -> dict:
        '''
        Returns the JSON representation of Publication as dictionary
        '''
        return {
            "title": self.title,
            "authors": self.authors,
            "summary": self.summary,
            "published": self.published.isoformat(), # self.published kann nicht stringified werden deshalb iso
            "url": self.url
        }
        