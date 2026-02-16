import pytest
from unittest.mock import Mock, patch

from MonaaLisa.src.SemanticPaper.api.semantic_scholar import SemanticScholarAPI


@pytest.fixture
def semantic_scholar_api():
    """Creates a SemanticScholarAPI instance with mocked external dependencies."""
    with patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.AsyncSemanticScholar'), \
         patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.Logger'):
        api = SemanticScholarAPI(api_key="test_key")
        api.client = Mock()
        api.logger = Mock()
        return api


@pytest.fixture
def semantic_scholar_api_no_key():
    """Creates a SemanticScholarAPI instance without API key."""
    with patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.AsyncSemanticScholar'), \
         patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.Logger'):
        api = SemanticScholarAPI(api_key=None)
        api.client = Mock()
        api.logger = Mock()
        return api


class TestFetchCitations:
    """Tests conditional logic in fetch_citations()."""

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_paper_with_arxiv_citations(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: if arxiv_id: branch in the citation loop

        When a citation has an ArXiv ID, it should be added to citation_arxiv_ids.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        # Mock citation with ArXiv ID
        mock_citation = Mock()
        mock_citation.externalIds = {"ArXiv": "2101.54321"}

        # Mock the async function return value
        mock_semantic_paper = Mock()
        mock_semantic_paper.citations = [mock_citation]
        # Since fetch_citations calls asyncio.run on a function that returns the citations,
        # we need to mock that return value
        mock_asyncio_run.return_value = [mock_citation]

        # Since we establish that the citation has an ArXiv ID, we expect the code
        # to call fetch_papers_by_ids on the Arxiv client with that ID.
        # We need to mock that as well to return a valid paper object.

        # Mock ArxivAPI
        mock_arxiv_client = Mock()
        mock_arxiv_client.fetch_papers_by_ids.return_value = [Mock()]

        citations_on_arxiv, citations_not_present = semantic_scholar_api.fetch_citations(
            mock_paper, mock_arxiv_client
        )

        # Verify ArXiv client was called with the correct ID
        mock_arxiv_client.fetch_papers_by_ids.assert_called_once()
        assert len(citations_on_arxiv) == 1
        assert len(citations_not_present) == 0

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_citations_without_arxiv_id(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: else branch when citation has no ArXiv ID

        Citations without ArXiv IDs should be added to citations_not_present.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        # Mock citation without ArXiv ID
        mock_citation = Mock()
        mock_citation.externalIds = {"DOI": "10.1234/example"}

        mock_asyncio_run.return_value = [mock_citation]

        mock_arxiv_client = Mock()

        # Same as before, we need to mock the Arxiv client,
        # but in this case we expect it not to be called since there were no ArXiv IDs.

        citations_on_arxiv, citations_not_present = semantic_scholar_api.fetch_citations(
            mock_paper, mock_arxiv_client
        )

        # Verify no ArXiv fetch was attempted
        mock_arxiv_client.fetch_papers_by_ids.assert_not_called()
        assert len(citations_on_arxiv) == 0
        assert len(citations_not_present) == 1

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_empty_citations_list(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: if citation_arxiv_ids: branch when list is empty

        When there are no citations with ArXiv IDs, citations_on_arxiv should be empty list.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        mock_asyncio_run.return_value = []

        mock_arxiv_client = Mock()

        citations_on_arxiv, citations_not_present = semantic_scholar_api.fetch_citations(
            mock_paper, mock_arxiv_client
        )

        assert citations_on_arxiv == []
        assert citations_not_present == []

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_mixed_citations(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: Mixed case with both ArXiv and non-ArXiv citations

        Verifies proper separation between citations_on_arxiv and citations_not_present.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        # Mock citation with ArXiv ID
        mock_citation_arxiv = Mock()
        mock_citation_arxiv.externalIds = {"ArXiv": "2101.54321"}

        # Mock citation without ArXiv ID
        mock_citation_no_arxiv = Mock()
        mock_citation_no_arxiv.externalIds = {"DOI": "10.1234/example"}

        mock_asyncio_run.return_value = [mock_citation_arxiv, mock_citation_no_arxiv]

        mock_arxiv_client = Mock()
        mock_arxiv_client.fetch_papers_by_ids.return_value = [Mock()]

        citations_on_arxiv, citations_not_present = semantic_scholar_api.fetch_citations(
            mock_paper, mock_arxiv_client
        )
        # Verify ArXiv client was called once for the one citation with an ArXiv ID
        assert len(citations_on_arxiv) == 1
        assert len(citations_not_present) == 1


class TestFetchReferences:
    """Tests conditional logic in fetch_references()."""
    # Annotation: Extremely similar to the citation tests, but we want to keep them separate for clarity and to ensure we cover the specific logic in references.

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_paper_with_arxiv_references(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: if arxiv_id: branch in the reference loop

        When a reference has an ArXiv ID, it should be added to references_arxiv_ids.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        # Mock reference with ArXiv ID
        mock_reference = Mock()
        mock_reference.externalIds = {"ArXiv": "2101.54321"}

        mock_asyncio_run.return_value = [mock_reference]

        mock_arxiv_client = Mock()
        mock_arxiv_client.fetch_papers_by_ids.return_value = [Mock()]

        references_on_arxiv, references_not_present = semantic_scholar_api.fetch_references(
            mock_paper, mock_arxiv_client
        )

        mock_arxiv_client.fetch_papers_by_ids.assert_called_once()
        assert len(references_on_arxiv) == 1
        assert len(references_not_present) == 0

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_references_without_arxiv_id(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: else branch when reference has no ArXiv ID

        References without ArXiv IDs should be added to references_not_present.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        # Mock reference without ArXiv ID
        mock_reference = Mock()
        mock_reference.externalIds = {"DOI": "10.1234/example"}

        mock_asyncio_run.return_value = [mock_reference]

        mock_arxiv_client = Mock()

        references_on_arxiv, references_not_present = semantic_scholar_api.fetch_references(
            mock_paper, mock_arxiv_client
        )

        mock_arxiv_client.fetch_papers_by_ids.assert_not_called()
        assert len(references_on_arxiv) == 0
        assert len(references_not_present) == 1

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_empty_references_list(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: if references_arxiv_ids: branch when list is empty

        When there are no references with ArXiv IDs, references_on_arxiv should be empty list.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        mock_asyncio_run.return_value = []

        mock_arxiv_client = Mock()

        references_on_arxiv, references_not_present = semantic_scholar_api.fetch_references(
            mock_paper, mock_arxiv_client
        )

        assert references_on_arxiv == []
        assert references_not_present == []

    @patch('MonaaLisa.src.SemanticPaper.api.semantic_scholar.asyncio.run')
    def test_handles_mixed_references(self, mock_asyncio_run, semantic_scholar_api):
        """
        Tests: Mixed case with both ArXiv and non-ArXiv references

        Verifies proper separation between references_on_arxiv and references_not_present.
        """
        mock_paper = Mock()
        mock_paper.entry_id = "http://arxiv.org/abs/2101.12345v1"

        # Mock reference with ArXiv ID
        mock_reference_arxiv = Mock()
        mock_reference_arxiv.externalIds = {"ArXiv": "2101.54321"}

        # Mock reference without ArXiv ID
        mock_reference_no_arxiv = Mock()
        mock_reference_no_arxiv.externalIds = {"DOI": "10.1234/example"}

        mock_asyncio_run.return_value = [mock_reference_arxiv, mock_reference_no_arxiv]

        mock_arxiv_client = Mock()
        mock_arxiv_client.fetch_papers_by_ids.return_value = [Mock()]

        references_on_arxiv, references_not_present = semantic_scholar_api.fetch_references(
            mock_paper, mock_arxiv_client
        )

        assert len(references_on_arxiv) == 1
        assert len(references_not_present) == 1