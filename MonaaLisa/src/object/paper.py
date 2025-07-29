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
from object.reference import Reference
from lxml import etree


@dataclass
class Paper:
    entry_id: str
    title: str
    authors: List[str]
    abstract: str
    published: datetime
    url: str
    hash: Optional[str] = None
    references: Optional[List[Reference]] = None
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
            citations=self.citations,
            tsne1=self.tsne1,
            tsne2=self.tsne2,
            embedding=json.dumps(self.embedding) if self.embedding else None,
            added=self.added or datetime.now()
        )


    """
    29-July-2025 - Lenio
    Abstract: Extracts the full text of a paper from its PDF URL.
    Annotation: This method will be replaced by Grobid in the future.
    """
    def extract_paper_text_legacy(self) -> Optional[str]:
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
                return text.strip()

        except Exception as e:
            title = self.title if hasattr(self, 'title') else "Unknown paper"
            print(f"Failed processing or fetching the PDF {title} with error: {str(e)}")
            return None

    """
    29-July-2025 - Lenio
    Abstract: Extracts metadata from the paper's PDF using Grobid.
    Args: None
    Returns: None
    """
    def extract_metadata(self):
        references = self.extract_references()
        if references:
            print("successfully extracted references from the paper!")
            self.references = references
            for reference in self.references:
                print(f" - {reference.title}")


    """
    29-July-2025 - Lenio
    Abstract: Extracts references from the paper's PDF using Grobid.
    returns: List[Reference] -> A list of Reference objects found in the paper.
    """
    def extract_references(self) -> List['Reference']:
        references = []
        text_as_xml = self.extract_paper_text_semantic(self.url)
        if text_as_xml is not None:
            data = text_as_xml.encode("utf-8")
            root = etree.fromstring(data)
            ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
            # Search for <div type="references"> in the <back> section
            references_xml = root.findall('.//tei:div[@type="references"]//tei:biblStruct', ns)
            for ref in references_xml:
                titles = ref.findall('.//tei:title', ns)
                if len(titles) > 0:
                    # Filter None values and use empty string as fallback
                    title_texts = [title.text or "" for title in titles]
                    # Only join non-empty strings
                    combined_title = ", ".join(filter(None, title_texts))
                    if combined_title:  # Only create reference if there is a title
                        references.append(Reference(self.entry_id, combined_title))
            else:
                    print(f"No titles found in reference: {etree.tostring(ref, pretty_print=True).decode('utf-8')}")
            return references
        return []

    """
    27-July-2025 - Lenio
    Abstract: Extracts the full text of a paper using grobid from a given URL, only for testing right now.
    Args: url: str -> The URL of the paper to extract text from.
    Returns: Optional[str] -> The extracted text from the paper, or None if extraction fails.
    """
    @staticmethod
    def extract_paper_text_semantic(url: str) -> Optional[str]:
        temp_file_path = None
        try:
            response = requests.get(url)
            if not response.ok:
                raise Exception(f"Failed to download PDF: HTTP Error Code is - {response.status_code}")

            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(response.content)
                temp_file_path = tmp_file.name

            # Send to Grobid for processing
            with open(temp_file_path, 'rb') as pdf_file:
                files = {'input': pdf_file}
                grobid_url = 'http://grobid:8070/api/processFulltextDocument'
                grobid_response = requests.post(
                    grobid_url,
                    files=files,
                    headers={'Accept': 'application/xml'}
                )

            if not grobid_response.ok:
                raise Exception(f"Grobid-Processing failed: {grobid_response.status_code}")
            print("Grobid processing finished successfully!")
            return grobid_response.text

        except Exception as e:
            print(f"Error while extracting text: {str(e)}")
            return None

        finally:
            # Clean up the temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"Failed to delete temporary file: {str(e)}")

#print(Paper.extract_paper_text_semantic("https://arxiv.org/pdf/2401.00001.pdf"))