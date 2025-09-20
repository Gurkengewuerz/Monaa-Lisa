import requests
import time

import time
import requests


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
        tries = 3
        last_exc = None
        response = None
        for _ in range(tries):
            try:
                response = requests.get(url, params=params, timeout=(3.05, 15))
                break
            except Exception as e:
                last_exc = e
        if response is None:
            raise last_exc
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
            chunk = paper_ids[i:i+100]
            tries = 3
            last_exc = None
            for _ in range(tries):
                try:
                    resp = requests.post(url, params=params, json={"ids": chunk}, timeout=(3.05, 30))
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict) and "data" in data:
                            all_data.extend(data.get("data", []))
                        else:
                            all_data.extend(data)
                        break
                    else:
                        last_exc = Exception(f"SemanticScholar batch error {resp.status_code}")
                except Exception as e:
                    last_exc = e
            if last_exc:
                # skip this chunk after retries
                continue
            time.sleep(sleep)
        return all_data