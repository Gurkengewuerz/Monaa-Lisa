import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, Column, String, DateTime, Integer, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
from SemanticPaper.logger.logger import setup_logger

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
logger = setup_logger()

DATABASE_URL = os.environ.get("DATABASE_URL")
print(f"Database URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Paper(Base):
    __tablename__ = "papers"
    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(String, unique=True, index=True)
    title = Column(String)
    authors = Column(String)
    summary = Column(String)
    published = Column(DateTime)
    url = Column(String)
    hash = Column(String, unique=True, index=True)
    related_papers = Column(JSON, nullable=True) 
    citations = Column(JSON, nullable=True)       
def save_to_db(paper, paper_hash):
    session = SessionLocal()
    db_paper = Paper(
        entry_id=paper.entry_id,
        title=paper.title,
        authors=", ".join(str(a) for a in paper.authors),
        summary=paper.summary,
        published=paper.published,
        url=paper.pdf_url,
        hash=paper_hash,
        related_papers=None,  
        citations=None        
    )
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

def paper_exists(session, paper_hash):
    return session.query(Paper).filter_by(hash=paper_hash).first() is not None

# Add a function to update citations and related papers later
def update_paper_references(paper_id, related_papers, citations):
    session = SessionLocal()
    try:
        paper = session.query(Paper).filter_by(entry_id=paper_id).first()
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
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")