import os
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
import arxiv as arx
from typing import List, Optional, Dict
import json

import pymupdf
import requests
from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from Database.db_models import DBPaper


@dataclass
class Paper:
    entry_id: str
    title: str
    authors: List[str]
    abstract: str
    published: datetime
    url: str
    hash: Optional[str] = None
    related_papers: Optional[Dict] = None # TODO # Should not show up here but rather in a separate table
    citations: Optional[Dict] = None # TODO # Should not show up here but rather in a separate table (maybe)
    tsne1: Optional[float] = None
    tsne2: Optional[float] = None
    embedding: Optional[Dict] = None
    added: Optional[datetime] = None

    """
    26-July-2025 - Lenio
    Abstract: Returns a Paper object from an arXiv result.
    Args: arvix_result: arxiv.Result -> Arxiv result object containing paper metadata.
    Returns: Paper -> A Paper object with metadata from the arXiv result.
    """
    @classmethod
    def from_arxiv(cls, arxiv_result: arx.Result):
        return cls(
            entry_id=arxiv_result.entry_id,
            title=arxiv_result.title,
            authors=[str(a) for a in arxiv_result.authors], # TODO # Normalize authors as objects
            abstract=arxiv_result.summary,
            published=arxiv_result.published,
            url=arxiv_result.pdf_url
        )

    """
    26-July-2025 - Lenio
    Abstract: Converts the Paper object to a SQLAlchemy model.
    Args: DBPaper: SQLAlchemy model class for the paper.
    Returns: DBPaper -> An instance of the SQLAlchemy model with the paper's data.
    """
    def to_db_model(self):
        return DBPaper(
            entry_id=self.entry_id,
            title=self.title,
            authors=", ".join(self.authors),
            summary=self.abstract,
            published=self.published,
            url=self.url,
            hash=self.hash,
            related_papers=self.related_papers,
            citations=self.citations,
            tsne1=self.tsne1,
            tsne2=self.tsne2,
            embedding=json.dumps(self.embedding) if self.embedding else None,
            added=self.added or datetime.now()
        )

    def extract_paper_text(self) -> Optional[str]:
        try:
            response = requests.get(self.url)
            if not response.ok:
                raise Exception(f"Failed to download PDF: HTTP Error Code is - {response.status_code}")

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_file.flush()

                doc = pymupdf.open(tmp_file.name)
                text = ""

                for page in doc:
                    text += page.get_text()

                doc.close()
                os.unlink(tmp_file.name)
                print("READING FULL TEXT FINISHED! =)")
                return text

        except Exception as e:
            title = self.title if hasattr(self, 'title') else "Unknown paper"
            print(f"Failed processing or fetching the PDF {title} with error: {str(e)}")
            return None

