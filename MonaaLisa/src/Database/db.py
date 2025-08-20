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
from Database.db_models import db_base, DBPaper, DBPaperRelation
from object.paper import Paper
from object.relation import Relation
from util.logger import Logger
# os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv()

logger = Logger("Database")

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


"""
05-August-2025 - Lenio
Abstract: Fetches all embeddings from the database and returns them as a dictionary.
Returns: A dictionary where keys are paper entry IDs and values are numpy arrays of embeddings.
"""
def get_all_embeddings():
    session = SessionLocal()
    try:
        papers = session.query(DBPaper.entry_id, DBPaper.embedding).all()
        embedding_dict = {
            paper.entry_id: np.array(paper.embedding['embedding'])
            for paper in papers if paper.embedding and 'embedding' in paper.embedding
        }
        return embedding_dict
    finally:
        session.close()

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
20-August-2025 - Lenio
Abstract: Saves a relation between two papers in the database.
Args:
PaperRelation: The relation object containing source_id, target_id, and confidence.
"""
def save_paper_relation(paper_relation: Relation):
    session = SessionLocal()
    if not relation_exists(session, paper_relation.source_id, paper_relation.target_id):
        try:
            db_paper_relation = paper_relation.to_db_model()
            session.add(db_paper_relation)
            session.commit()
            logger.info(f"Saved paper relation: {paper_relation.source_id} -> {paper_relation.target_id} with confidence {paper_relation.confidence}")
            return True
        except Exception as e:
            logger.error(f"DB error saving paper relation: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    else:
        logger.info(f"Relation already exists: {paper_relation.source_id} -> {paper_relation.target_id}")
        session.close()
        return True

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
20-August-2025 - Lenio
Abstract: Checks if a relation between two papers already exists in the database.
Args:
- session: The current database session.
- source_id: The ID of the first paper.
- target_id: The ID of the second paper.
Returns: bool -> True if the relation exists, False otherwise.
"""
def relation_exists(session, source_id: str, target_id: str):
    # Check if the relation exists in either direction
    relation1 = session.query(DBPaperRelation).filter_by(source_id=source_id, target_id=target_id).first()
    relation2 = session.query(DBPaperRelation).filter_by(source_id=target_id, target_id=source_id).first()
    return relation1 is not None or relation2 is not None

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