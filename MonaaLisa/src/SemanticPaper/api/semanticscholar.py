import requests
import time

class SemanticScholarAPI:
    """
    25-May-2025 - Basti
    Abstract: Wrapper for Semantic Scholar API to fetch references and citations for arXiv papers,
    and (optionally) batch metadata for multiple Semantic Scholar paper IDs.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    @staticmethod
    def fetch_references_and_citations(arxiv_id):
        """
        Fetches references and citations for a given arXiv paper.
        Args:
            - arxiv_id: The arXiv ID (with or without version, or full URL)
        Returns:
            Dictionary with lists of reference and citation Semantic Scholar IDs, or None if not found.
        """
        if arxiv_id.startswith("http"):
            arxiv_id = arxiv_id.split("/")[-1]
        arxiv_id_no_version = arxiv_id.split('v')[0]
        paper_id = f"arXiv:{arxiv_id_no_version}"
        url = f"{SemanticScholarAPI.BASE_URL}/paper/{paper_id}"
        params = {
            "fields": "references.paperId,citations.paperId"
        }
        response = requests.get(url, params=params)
        if response.status_code == 404:
            print(f"Semantic Scholar: Paper {arxiv_id_no_version} not found (may be too new)! - (save it into the database as todo)")
            return None
        if response.status_code != 200:
            print(f"Semantic Scholar error: {response.status_code} - {response.text}")
            return None
        data = response.json()
        references = [ref["paperId"] for ref in data.get("references", []) if ref.get("paperId")]
        citations = [cit["paperId"] for cit in data.get("citations", []) if cit.get("paperId")]
        return {"references": references, "citations": citations}

    @staticmethod
    def fetch_papers_batch(paper_ids, fields=None, sleep=1):
        """
        Fetches metadata for a batch of Semantic Scholar paper IDs using the /paper/batch endpoint
        Args:
            - paper_ids: List of Semantic Scholar paper IDs (max 100 per request)
            - fields: Comma-separated string of fields to fetch (default: title,authors,year)
            - sleep: Seconds to wait between requests (default: 1)
        Returns:
            List of metadata dictionaries for each paper, or empty list on error.
        """
        if fields is None:
            fields = "title,authors,year"
        url = f"{SemanticScholarAPI.BASE_URL}/paper/batch"
        params = {"fields": fields}
        all_data = []
        for i in range(0, len(paper_ids), 100):
            batch = paper_ids[i:i+100]
            response = requests.post(url, params=params, json={"ids": batch})
            if response.status_code != 200:
                print(f"Semantic Scholar batch error: {response.status_code} - {response.text}")
                continue
            data = response.json()
            all_data.extend(data.get("data", []))
            time.sleep(sleep)
        return all_data