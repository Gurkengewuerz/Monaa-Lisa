import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Optional

import numpy as np
import requests
from arxiv import arxiv
from pymupdf import pymupdf



sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from Database.db_models import db_base, DBPaper, ProgramRun, HistoricalCompletion
from object.paper import Paper
from util.logger import Logger
# os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv()

logger = Logger("Database")

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
def save_paper_to_db(paper: Paper, paper_hash, embedding: dict):
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

    combined_embedding = {
        "embedding": embedding["Embedding"].tolist() if isinstance(embedding["Embedding"], np.ndarray) else embedding[
            "Embedding"],
        "tsne1": float(tsne1) if tsne1 is not None else None,
        "tsne2": float(tsne2) if tsne2 is not None else None
    }
    db_paper = paper.to_db_model()
    logger.info("hash: " + paper.hash)
    db_paper.embedding = combined_embedding
    db_paper.hash = paper_hash
    # in the future when we have more calls to grobid this should not happen but rather in a sooner step so we process each paper only once
    references = paper.references if paper.references else []
    for ref in references:
        db_reference = ref.to_db_model()
        logger.info(f"Adding reference to DB: {db_reference.title}")
        session.add(db_reference)
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
    logger.info("Creating database tables...")
    db_base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully!")

"""
13-August-2025 - Basti
Abstract: Creates a new program run record and returns its ID.
"""
def create_program_run():
    session = SessionLocal()
    try:
        # Deactivate any prior runs
        session.query(ProgramRun).filter_by(is_active="true").update({"is_active": "false"})
        run = ProgramRun(start_date=datetime.now(), is_active="true")
        session.add(run)
        session.commit()
        logger.info(f"Created ProgramRun ID: {run.id}")
        return run.id
    except Exception as e:
        logger.error(f"Error creating program run: {e}")
        session.rollback()
        return None
    finally:
        session.close()

"""
13-August-2025 - Basti
Abstract: Checks if a category is already completed historically in this run.
"""
def is_category_historically_completed(program_run_id, category):
    session = SessionLocal()
    try:
        exists = session.query(HistoricalCompletion).filter_by(
            program_run_id=program_run_id, category=category
        ).first() is not None
        return exists
    except Exception as e:
        logger.error(f"Error checking completion: {e}")
        return False
    finally:
        session.close()

"""
13-August-2025 - Basti
Abstract: Marks a category as completed historically for this run.
"""
def mark_category_historically_completed(program_run_id, category, oldest_paper_date=None):
    session = SessionLocal()
    try:
        record = HistoricalCompletion(
            program_run_id=program_run_id,
            category=category,
            completed_date=datetime.now(),
            oldest_paper_date=oldest_paper_date
        )
        session.add(record)
        session.commit()
        logger.info(f"Marked {category} completed for run {program_run_id}")
        return True
    except Exception as e:
        logger.error(f"Error marking completion: {e}")
        session.rollback()
        return False
    finally:
        session.close()