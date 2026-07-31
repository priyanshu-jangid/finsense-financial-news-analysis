import os
from contextlib import contextmanager
 
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
 
from shared.models import Base
 
DB_PATH = os.environ.get("FINSENSE_DB_PATH", "finsense.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"
 
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # needed for SQLite + multiple threads
)
 
 
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")   
    cursor.execute("PRAGMA foreign_keys=ON")    # SQLite ignores FKs unless told otherwise
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
 
 
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
 
 
def init_db() -> None:
    """Create all tables. Call once at startup (API and/or worker)."""
    Base.metadata.create_all(bind=engine)
 
 
@contextmanager
def get_session():
    """Use as: `with get_session() as session: ...` — commits on success, rolls back on error."""
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
