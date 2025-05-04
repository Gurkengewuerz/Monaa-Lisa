import arxiv as arx
import feedparser
import random

# Funny test comment ! :D

categories = [
    # Physics
    'astro-ph', 'cond-mat', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th',
    'math-ph', 'nlin', 'nucl-ex', 'nucl-th', 'physics', 'quant-ph',
    
    # Mathematics
    'math', 'math.AG', 'math.AT', 'math.AP', 'math.CT', 'math.CA', 'math.CO',
    'math.AC', 'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN',
    'math.GT', 'math.GR', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MP',
    'math.MG', 'math.NT', 'math.NA', 'math.OA', 'math.OC', 'math.PR', 'math.QA',
    'math.RT', 'math.RA', 'math.SP', 'math.ST', 'math.SG',
    
    # Computer Science
    'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV',
    'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL',
    'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO',
    'cs.MA', 'cs.MM', 'cs.MS', 'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS',
    'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC', 'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY',
    
    # Quantitative Biology
    'q-bio', 'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC',
    'q-bio.OT', 'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO',
    
    # Quantitative Finance
    'q-fin.CP', 'q-fin.EC', 'q-fin.GN', 'q-fin.MF', 'q-fin.PM', 'q-fin.PR',
    'q-fin.RM', 'q-fin.ST', 'q-fin.TR',
    
    # Statistics
    'stat.AP', 'stat.CO', 'stat.ME', 'stat.ML', 'stat.OT', 'stat.TH',
    
    # Electrical Engineering and Systems Science
    'eess.AS', 'eess.IV', 'eess.SP', 'eess.SY',
    
    # Economics
    'econ.EM', 'econ.GN', 'econ.TH'
]

# Global client that communicates with the arXiv API
client = arx.Client()

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
        

"""
04-May-2025 - Basti
Abstract: Takes one random category and proceeds to retrieve the newest paper from that category
Args: None 
Returns: One arXiv paper -> Result
"""
def fetch_one_paper() -> arx.Result:
    random_cat = categories[random.randint(0, len(categories) - 1)]
    search = arx.Search(
        query=f"cat:{random_cat}", 
        max_results=1, 
        sort_by=arx.SortCriterion.SubmittedDate, 
        sort_order=arx.SortOrder.Descending
    )
    results = list(client.results(search))
    return results[0] if results else None