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
    url = Column(String)
    hash = Column(String, unique=True, index=True)
    citations = Column(JSON, nullable=True)
    embedding = Column(JSON, nullable=True)
    added = Column(DateTime, nullable=False)

"""
17-July-2025 - Lenio
Abstract: Represents a relation between two papers in the database.
Parameters:
- source_id: The ID of the first paper.
- target_id: The ID of the second paper that relates to the first.
- confidence: A float representing the confidence level of the relation.
"""
class PaperRelation(db_base):
    __tablename__ = "paper_relations"
    source_id = Column(Integer, ForeignKey("paper.id"), primary_key=True)
    target_id = Column(Integer, ForeignKey("paper.id"), primary_key=True)
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