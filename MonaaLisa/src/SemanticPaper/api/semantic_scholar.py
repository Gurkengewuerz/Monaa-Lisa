import asyncio
from typing import Tuple

import semanticscholar.Paper as SemanticScholarPaper
from semanticscholar import AsyncSemanticScholar

from SemanticPaper.api.arxiv import ArxivAPI
from object.paper import Paper
from util.logger import Logger


class SemanticScholarAPI:

    def __init__(self, api_key: str | None = None):
        self.client = AsyncSemanticScholar(api_key=api_key)
        self.logger = Logger("SemanticScholarAPI")
        if api_key:
            self.logger.debug("SemanticScholarAPI initialized with API key (authenticated).")
        else:
            self.logger.debug("SemanticScholarAPI initialized without API key (unauthenticated).")

    def fetch_paper(self, semantic_scholar_id: str) -> Paper:
        async def fetch_semantic_scholar_paper(paper_id: str):
            return await self.client.get_paper(paper_id)

        return asyncio.run(fetch_semantic_scholar_paper(semantic_scholar_id))

    def fetch_arxiv_paper(self, arxiv_id: str) -> Paper:
        async def fetch_arxiv_paper_async(aid: str):
            return await self.client.get_paper(f"ARXIV:{aid}")

        return asyncio.run(fetch_arxiv_paper_async(arxiv_id))

    def fetch_citations(self, p_paper: Paper, arxiv_client: ArxivAPI) -> Tuple[list[Paper], list[SemanticScholarPaper]]:
        async def get_citations(paper_obj: Paper):
            entry_id = paper_obj.entry_id or ""
            parts = entry_id.split("/")
            raw_id = "/".join(parts[1:]) if len(parts) >= 2 else (parts[-1] if parts else "")
            normalized_paper_id = raw_id.split("v")[0] if raw_id else ""

            paper = await self.client.get_paper(f"ARXIV:{normalized_paper_id}")
            return getattr(paper, "citations", []) or []

        citations = asyncio.run(get_citations(p_paper))

        def _external_ids(obj) -> dict:
            ext = getattr(obj, "externalIds", None)
            return ext if isinstance(ext, dict) else {}

        citation_arxiv_ids: list[str] = []
        citations_not_present: list[SemanticScholarPaper] = []

        for c in citations:
            ext = _external_ids(c)
            arxiv_id = ext.get("ArXiv")
            if arxiv_id:
                citation_arxiv_ids.append(arxiv_id)
            else:
                citations_not_present.append(c)

        if citation_arxiv_ids:
            self.logger.info(citation_arxiv_ids)
            citations_on_arxiv = arxiv_client.fetch_papers_by_ids(citation_arxiv_ids)
        else:
            citations_on_arxiv = []
        return (citations_on_arxiv, citations_not_present)


    def fetch_references(self, p_paper: Paper, arxiv_client: ArxivAPI) -> Tuple[list[Paper], list[SemanticScholarPaper]]:
        async def get_references(paper_obj: Paper):
            entry_id = paper_obj.entry_id or ""
            parts = entry_id.split("/")
            raw_id = "/".join(parts[1:]) if len(parts) >= 2 else (parts[-1] if parts else "")
            normalized_paper_id = raw_id.split("v")[0] if raw_id else ""

            paper = await self.client.get_paper(f"ARXIV:{normalized_paper_id}")
            return getattr(paper, "references", []) or []

        references = asyncio.run(get_references(p_paper))

        def _external_ids(obj) -> dict:
            ext = getattr(obj, "externalIds", None)
            return ext if isinstance(ext, dict) else {}

        references_arxiv_ids: list[str] = []
        references_not_present: list[SemanticScholarPaper] = []

        for r in references:
            ext = _external_ids(r)
            arxiv_id = ext.get("ArXiv")
            if arxiv_id:
                references_arxiv_ids.append(arxiv_id)
            else:
                references_not_present.append(r)

        if references_arxiv_ids:
            self.logger.info(references_arxiv_ids)
            references_on_arxiv = arxiv_client.fetch_papers_by_ids(references_arxiv_ids)
        else:
            references_on_arxiv = []
        return (references_on_arxiv, references_not_present)
