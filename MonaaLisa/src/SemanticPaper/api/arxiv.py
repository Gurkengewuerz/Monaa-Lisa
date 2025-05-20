import arxiv as arx
import feedparser
import random



# Funny test comment ! :D

# categories = [
#     # Physics
#     'astro-ph', 'cond-mat', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th',
#     'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'physics', 'quant-ph',
    
#     # Mathematics
#     'math', 'math.AG', 'math.AT', 'math.AP', 'math.CT', 'math.CA', 'math.CO',
#     'math.AC', 'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN',
#     'math.GT', 'math.GR', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MP',
#     'math.MG', 'math.NT', 'math.NA', 'math.OA', 'math.OC', 'math.PR', 'math.QA',
#     'math.RT', 'math.RA', 'math.SP', 'math.ST', 'math.SG',
    
#     # Computer Science
#     # cs.CG - Scheffer Fokus
#     'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV',
#     'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL',
#     'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
#     'cs.MA', 'cs.MM', 'cs.MS', 'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS',
#     'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC', 'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY',
    
#     # Quantitative Biology
#     'q-bio', 'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC',
#     'q-bio.OT', 'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO',
    
#     # Quantitative Finance
#     'q-fin.CP', 'q-fin.EC', 'q-fin.GN', 'q-fin.MF', 'q-fin.PM', 'q-fin.PR',
#     'q-fin.RM', 'q-fin.ST', 'q-fin.TR',
    
#     # Statistics
#     'stat.AP', 'stat.CO', 'stat.ME', 'stat.ML', 'stat.OT', 'stat.TH',
    
#     # Electrical Engineering and Systems Science
#     'eess.AS', 'eess.IV', 'eess.SP', 'eess.SY',
    
#     # Economics
#     'econ.EM', 'econ.GN', 'econ.TH'
# ]

CS_CG_CATEGORY = 'cs_CG'

# Global client that communicates with the arXiv API
client = arx.Client()


"""
04-May-2025 - Basti
Abstract: Retrieves a paper and prints out its metadata
Args:
    - paper: The current paper to be read out

Returns: Metadata of the provided Paper
"""
def read_meta(paper: arx.Result):
    if paper:
        print(f"Title: {paper.title}\n")
        print(f"Authors: {', '.join(str(author) for author in paper.authors)}\n")
        print(f"Published: {paper.published}\n")
        print(f"Abstract: {paper.summary}\n")
        print(f"PDF URL: {paper.pdf_url}\n")
        print(f"Entry ID: {paper.entry_id}\n")
    else:
        print("No Paper!")

"""
04-May-2025 - Basti
Abstract: Takes one paper from the cs_CG category and proceeds to retrieve the newest paper from that category
Args: None 
Returns: One arXiv paper -> Result
"""
def fetch_one_random_paper() -> arx.Result:
    search = arx.Search(
        query=f"cat:{CS_CG_CATEGORY}", 
        max_results=1, 
        sort_by=arx.SortCriterion.SubmittedDate, 
        sort_order=arx.SortOrder.Descending
    )
    results = list(client.results(search))
    return results[0] if results else None

"""
04-May-2025 - Basti
Abstract: Fetches a x amount of papers in y category
Args:

- category: Category from one of arXiv's category
- amount: Amount of papers to be fetched starting from the newest papers

Returns: List -> of fetches papers
"""
def fetch_papers(category: str = CS_CG_CATEGORY, amount: int = 10) -> list:
    search = arx.Search(
        query=f"cat:{category}",
        max_results=amount,
        sort_by=arx.SortCriterion.SubmittedDate, 
        sort_order=arx.SortOrder.Descending
    )
    return list(search.results())














"""
///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
FROM HERE ON ONLY SOME TESTING FUNCTIONS WILL BE DECLARED - THESE WILL LATER MOVE TO UNIT TESTS - IGNORE FOR NOW!

"""

"""
04-May-2025 - Basti
Abstract: Simple method to test (as of now the API of testing_arxiv - should not have much use for production)
Args:
Returns: 
"""
def testing_arxiv():
    search = arx.Search(
        query="submittedDate:[NOW-7DAYS TO NOW]",
        max_results = 10,
        sort_by = arx.SortCriterion.SubmittedDate,
        sort_order = arx.SortOrder.Descending
    )

    results = client.results(search)

    for r in results:
        print(f"Title: {r.title}\nDate: {r.published}")


"""
04-May-2025 - Basti
Abstract: Simple method to fetch the newest arXiv Results using feedparser instead of the arXiv Python API
Args:
Returns:
"""
def testing_feedparser():
    url = "http://export.arxiv.org/api/query?search_query=all:*&sortBy=lastUpdatedDate&sortOrder=descending&max_results=5&version=2"
    feed = feedparser.parse(url)
    print(len(feed.entries))
    for entry in feed.entries:
        print(f"Title: {entry.title}")
        print(f"Updated: {entry.updated}")
        print(f"Link: {entry.link}")
        print('-' * 80)



"""
04-May-2025 - Basti
Abstract: Tests if every category is accessible and is reachable through the arXiv API
Args:
Returns: 
"""
@DeprecationWarning
def test_categories():
    print("Deprecated now! Categories have all passed the check as of 4th May 2025")
    client = arx.Client()
    for cat in categories:
        current_search = arx.Search(query=f"{cat}", max_results=1, sort_by=arx.SortCriterion.SubmittedDate, sort_order=arx.SortOrder.Descending)
        results = list(client.results(current_search))
        if len(results) == 0:
            print(f"Failed for category: {cat}")
            break

        print(f"Category {cat} passed!")
        

