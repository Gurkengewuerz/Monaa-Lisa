import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from sqlalchemy import create_engine, Column, String, DateTime, Integer
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

def save_to_db(paper, paper_hash):
    session = SessionLocal()
    db_paper = Paper(
        entry_id=paper.entry_id,
        title=paper.title,
        authors=", ".join(str(a) for a in paper.authors),
        summary=paper.summary,
        published=paper.published,
        url=paper.pdf_url,
        hash=paper_hash
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

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")