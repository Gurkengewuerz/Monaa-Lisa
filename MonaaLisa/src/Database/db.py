import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Optional

import requests
from arxiv import arxiv
from pymupdf import pymupdf



sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from Database.db_models import db_base, DBPaper
from object.paper import Paper
from SemanticPaper.logger.logger import setup_logger
# os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv()
logger = setup_logger()

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


"""
25-May-2025 - Basti
Abstract: Saves one given arXiv paper into the Postgres database
Args:
- paper: The given arXiv paper
- paper_hash: The corresponding hash
- embedding: dict -> numpy dictionary containing coordinates, datatype and parsed 
Returns: bool -> True if: paper was successfully committed to the database | False if: commit failed/Exception occured
"""  
def save_to_db(paper: Paper, paper_hash, embedding: dict):
    session = SessionLocal()

    if paper_exists(session, paper_hash):
        logger.info(f"Paper already exists in DB: {paper.title} (hash: {paper_hash})")
        session.close()
        return True

    tsne1 = embedding.get("tsne1") or embedding.get("tSNE1")
    tsne2 = embedding.get("tsne2") or embedding.get("tSNE2")
    try:
        tsne1 = float(tsne1) if tsne1 is not None else None
    except (ValueError, TypeError):
        tsne1 = None
    try:
        tsne2 = float(tsne2) if tsne2 is not None else None
    except (ValueError, TypeError):
        tsne2 = None

    combined_embedding = json.dumps({"tsne1": tsne1, "tsne2": tsne2})
    db_paper = paper.to_db_model()
    db_paper.embedding = combined_embedding
    db_paper.tsne1 = tsne1
    db_paper.tsne2 = tsne2
    db_paper.hash = paper_hash
    session.add(db_paper)
    try:
        session.commit()
        logger.info(f"Saved paper to DB: {paper.title}")
        return True
    except Exception as e:
        logger.error(f"DB error: {e}")
        session.rollback()
        return False
    finally:
        session.close()
"""
25-May-2025 - Basti
Abstract: Checks if a paper hash already exists in the database
Args:
- session: -> Current database session
- paper_hash: -> the hash of the given arXiv paper
Returns: bool -> True if: query of the paper is not Null/None | False if: query of the paper is None 
"""
def paper_exists(session, paper_hash):
    return session.query(DBPaper).filter_by(hash=paper_hash).first() is not None

"""
25-May-2025 - Basti
Abstract: (for future development) - 
Args:
- None
Returns: 
"""
@FutureWarning
def update_paper_references(paper_id, related_papers, citations):
    session = SessionLocal()
    try:
        paper = session.query(DBPaper).filter_by(entry_id=paper_id).first()
        if paper:
            paper.related_papers = related_papers
            paper.citations = citations
            session.commit()
            logger.info(f"Updated references for paper: {paper.title}")
            return True
        else:
            logger.warning(f"Paper with ID {paper_id} not found for reference update")
            return False
    except Exception as e:
        logger.error(f"DB error updating references: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("Creating database tables...")
    db_base.metadata.create_all(bind=engine)
    print("Tables created successfully!")