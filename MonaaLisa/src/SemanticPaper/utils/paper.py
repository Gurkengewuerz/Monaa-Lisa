import arxiv, os, time, requests
import tempfile 
import pymupdf
from typing import Optional

"""
06-May-2025 - Basti
Abstract: Downloads and extracts the papers PDF using streaming to minimize memory usage
Args:

- paper: arxiv.Resukt -> A given paper returned from a Result() object

Returns: str -> Extracted text from a PDF (optional) - None if fetching failed
"""
def get_paper_text(paper: arxiv.Result) -> Optional[str]:
    try:
        response = requests.get(paper.pdf_url)
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
        title = paper.title if hasattr(paper, 'title') else "Unknown paper"
        print(f"Failed processing or fetching the PDF {title} with error: {str(e)}")
        return None
