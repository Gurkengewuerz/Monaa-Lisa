from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import declarative_base

db_base = declarative_base()

"""
26-July-2025 - Lenio
Abstract: Represents a paper in the database.
Parameters:
- id: Primary key of the paper.
- entry_id: Unique identifier for the paper in arXiv.
- title: Title of the paper.
- authors: Comma-separated string of authors.
- abstract: Abstract of the paper.
- published: Date and time when the paper was published.
- url: URL to the paper's PDF.
- hash: Unique hash of the paper.
- related_papers: JSON field for related papers.
- citations: JSON field for citations of the paper.
- tsne1: First t-SNE coordinate for visualization.
- tsne2: Second t-SNE coordinate for visualization.
- embedding: JSON field for the paper's embedding.
- added: Date and time when the paper was added to the database.
"""
class DBPaper(db_base):
    __tablename__ = "paper"
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String, unique=True, index=True)
    title = Column(String)
    authors = Column(String)
    summary = Column(String)
    published = Column(DateTime)
    category = Column(String)
    url = Column(String)
    hash = Column(String, unique=True, index=True)
    citations = Column(JSON, nullable=True)
    tsne = Column(JSON, nullable=True)
    added = Column(DateTime, nullable=False)

"""
17-July-2025 - Lenio
Abstract: Represents a relation between two papers in the database.
Parameters:
- source_id: The ID of the first paper.
- target_id: The ID of the second paper that relates to the first.
- confidence: A float representing the confidence level of the relation.
"""
class DBPaperRelation(db_base):
    __tablename__ = "paper_relation"
    source_id = Column(String, ForeignKey("paper.entry_id"), primary_key=True)
    target_id = Column(String, ForeignKey("paper.entry_id"), primary_key=True)
    confidence = Column(Float)


"""
17-July-2025 - Lenio
Abstract: Represents a reference found in a paper.
Parameters:
- belonging_paper_id: The ID of the first paper.
- target_id: The ID of the second paper that relates to the first.
- confidence: A float representing the confidence level of the relation.
"""
class DBReference(db_base):
    __tablename__ = "reference"
    id = Column(Integer, primary_key=True, autoincrement=True)
    belonging_paper_entry_id = Column(String, ForeignKey("paper.entry_id"), primary_key=True)
    title = Column(String, nullable=False)


"""
21-August-2025 - Lenio
Abstract: Represents an embedding in the database.
Parameters:
- content: The content of the embedding, stored as a JSON object.
"""
class DBEmbedding(db_base):
    __tablename__ = "embedding"
    id = Column(Integer, primary_key=True, autoincrement=True)
    belonging_paper_entry_id = Column(String, ForeignKey("paper.entry_id"), primary_key=True)
    content = Column(JSON, nullable=False)


"""
13-August-2025 - Basti
Abstract: Tracks program run sessions for historical fetching.
Parameters:
- id: Primary key of the run session.
- start_date: Timestamp when the program run started.
- is_active: String flag indicating if the run is active.
"""
class ProgramRun(db_base):
    __tablename__ = "program_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(DateTime, nullable=False)
    is_active = Column(String, default="true")

"""
13-August-2025 - Basti
Abstract: Records which categories have completed historical fetch for each program run.
Parameters:
- id: Primary key.
- program_run_id: Foreign key to ProgramRun.
- category: The completed arXiv category.
- completed_date: Timestamp when category was completed.
- oldest_paper_date: The date of the oldest fetched paper.
"""
class HistoricalCompletion(db_base):
    __tablename__ = "historical_completions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    program_run_id = Column(Integer, ForeignKey("program_runs.id"), nullable=False)
    category = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    oldest_paper_date = Column(DateTime, nullable=True)