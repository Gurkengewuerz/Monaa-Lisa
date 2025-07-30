import os
import sys
import tempfile
import textwrap
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
from util.logger import Logger
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
    text_as_xml = None
    logger = Logger("Paper")

    """
    26-July-2025 - Lenio
    Abstract: Returns a Paper object from an arXiv result.
    Args: arvix_result: arxiv.Result -> Arxiv result object containing paper metadata.
    Returns: Paper -> A Paper object with metadata from the arXiv result.
    """
    @classmethod
    def from_arxiv(cls, arxiv_result: arx.Result):
        return cls(
            entry_id=arxiv_result.entry_id.split("/")[-1],  # Extract the last part of the entry_id
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
                self.logger.info("Reading full text finished successfully!")
                return text.strip()

        except Exception as e:
            title = self.title if hasattr(self, 'title') else "Unknown paper"
            self.logger.error(f"Failed processing or fetching the PDF {title} with error: {str(e)}")
            return None

    """
    29-July-2025 - Lenio
    Abstract: Extracts metadata from the paper's PDF using Grobid.
    Args: None
    Returns: None
    """
    def extract_metadata(self):
        self.text_as_xml = self.extract_paper_text_semantic()
        references = self.extract_references()
        if references:
            self.logger.info("Extracted references from the paper!")
            self.references = references
            for reference in self.references:
                self.logger.debug(f"{self.title} referencing {reference.title}")
        sections = self.get_sections()
        if sections:
            for section in sections:
                self.logger.info(f"{section['title']}")
                # format text
                content = section['content'].strip().lstrip('.')
                wrapped_text = textwrap.fill(content,
                                             width=100,
                                             break_long_words=False,
                                             replace_whitespace=True,
                                             break_on_hyphens=True)

                self.logger.info(f"{wrapped_text}\n")


    """
    29-July-2025 - Lenio
    Abstract: Extracts references from the paper's PDF using Grobid.
    returns: List[Reference] -> A list of Reference objects found in the paper.
    """
    def extract_references(self) -> List['Reference']:
        references = []
        if self.text_as_xml is not None:
            data = self.text_as_xml.encode("utf-8")
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
                    self.logger.warning("Could not extract references from paper or none were found!")
                    # Sometimes the xpath seems to fail, gotta look into this later
            return references
        return []

    """
    30-July-2025 - Lenio
    Abstract: Extracts sections from the paper's XML text.
    Args: 
    - root: ET.Element -> The root element of the XML document.
    - ns: dict -> A dictionary containing XML namespaces.
    """
    def get_sections(self) -> list[dict]:
        data = self.text_as_xml.encode("utf-8")
        root = etree.fromstring(data)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        sections = []
        for section in root.findall('.//tei:body//tei:div', ns):
            # Get the section header and content xml elements
            head_element = section.find('.//tei:head', ns)
            content_elements = section.findall('.//tei:p', ns)
            # The section data dictionary
            section_data = {}
            # The index indicating the section number
            section_header_index = head_element.attrib.get('n', '')
            content = ""
            # Get all paragraphs in a section
            for paragraph in content_elements:
                content += paragraph.text.strip() + "\n"
            if section_header_index != "":
                # If section has a number in its attribute 'n'
                section_data['title'] = section_header_index + " " + (
                    head_element.text if head_element is not None else "")
            else:
                """ Sometimes grobid get's Sections wrong so if there is a section without an index
                    we merge its content with the previous section.
                """
                sections[-1]['content'] += "\n" + content
                continue
            # If section has a title add it's content to the section data
            section_data['content'] = content
            sections.append(section_data)
        return sections

    """
    27-July-2025 - Lenio
    Abstract: Extracts the full text of a paper using grobid and sets the text_as_xml attribute.
    Returns: Optional[str] -> Returns text of the paper as xml if successful, otherwise None.
    """
    def extract_paper_text_semantic(self) -> Optional[str]:
        local_logger = Logger("Grobid")
        temp_file_path = None
        try:
            response = requests.get(self.url)
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
            local_logger.info("Grobid processing finished successfully!")
            return grobid_response.text

        except Exception as e:
            local_logger.error(f"Error while extracting text: {str(e)}")
            return None

        finally:
            # Clean up the temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    local_logger.error(f"Failed to delete temporary file: {str(e)}")

#print(Paper.extract_paper_text_semantic("https://arxiv.org/pdf/2401.00001.pdf"))