"""
Database models and connection management using SQLAlchemy.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Index, 
    create_engine, event, text, func, inspect
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.engine import Engine
import logging
from contextlib import contextmanager
from sqlalchemy.exc import OperationalError

from pybusta.core.models import Book, DatabaseConfig

logger = logging.getLogger(__name__)

# Create the base class for our models
Base = declarative_base()


class BookRecord(Base):
    """SQLAlchemy model for books table."""
    
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(200), nullable=False, index=True)
    genre = Column(String(100), index=True)
    language = Column(String(10), nullable=False, index=True)
    format = Column(String(10), nullable=False)
    size = Column(Integer, nullable=False)
    archive_file = Column(String(200), nullable=False)
    date_added = Column(DateTime, default=datetime.utcnow)
    
    # Create composite indexes for common queries
    __table_args__ = (
        Index('idx_author_title', 'author', 'title'),
        Index('idx_title_author', 'title', 'author'),
        Index('idx_language_format', 'language', 'format'),
    )


class BookSearchRecord(Base):
    """SQLAlchemy model for full-text search table."""
    
    __tablename__ = "book_search"
    
    rowid = Column(Integer, primary_key=True)
    id = Column(Integer, nullable=False, index=True)
    author = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    language = Column(String(10), nullable=False)


class SettingsRecord(Base):
    """SQLAlchemy model for application settings."""
    
    __tablename__ = "settings"
    
    name = Column(String(100), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance."""
    cursor = dbapi_connection.cursor()
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys=ON")
    # Use WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    # Increase cache size
    cursor.execute("PRAGMA cache_size=10000")
    # Use memory for temporary tables
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self, db_path: Path):
        """Initialize database manager.
        
        Args:
            db_path: Path to the database directory
        """
        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Create database URL
        db_file = self.db_path / "pybusta.db"
        self.database_url = f"sqlite:///{db_file}"
        
        # Create engine with optimizations
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            }
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create tables
        self.create_tables()
        
        # Initialize FTS if needed
        self._init_fts()
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def _init_fts(self) -> None:
        """Initialize full-text search virtual table."""
        with self.get_session() as session:
            try:
                # Check if FTS table exists
                result = session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='book_search_fts'")
                )
                if not result.fetchone():
                    logger.info("Creating FTS virtual table...")
                    
                    # Drop existing FTS table if it exists but is not properly configured
                    try:
                        session.execute(text("DROP TABLE IF EXISTS book_search_fts"))
                    except Exception:
                        pass
                    
                    # Create FTS virtual table
                    session.execute(text("""
                        CREATE VIRTUAL TABLE book_search_fts USING fts5(
                            id UNINDEXED,
                            author,
                            title,
                            language UNINDEXED,
                            content='book_search',
                            content_rowid='rowid'
                        )
                    """))
                    
                    # Drop existing triggers if they exist
                    try:
                        session.execute(text("DROP TRIGGER IF EXISTS book_search_ai"))
                        session.execute(text("DROP TRIGGER IF EXISTS book_search_ad")) 
                        session.execute(text("DROP TRIGGER IF EXISTS book_search_au"))
                    except Exception:
                        pass
                    
                    # Create triggers to keep FTS in sync
                    session.execute(text("""
                        CREATE TRIGGER book_search_ai AFTER INSERT ON book_search BEGIN
                            INSERT INTO book_search_fts(rowid, id, author, title, language)
                            VALUES (new.rowid, new.id, new.author, new.title, new.language);
                        END
                    """))
                    
                    session.execute(text("""
                        CREATE TRIGGER book_search_ad AFTER DELETE ON book_search BEGIN
                            INSERT INTO book_search_fts(book_search_fts, rowid, id, author, title, language)
                            VALUES('delete', old.rowid, old.id, old.author, old.title, old.language);
                        END
                    """))
                    
                    session.execute(text("""
                        CREATE TRIGGER book_search_au AFTER UPDATE ON book_search BEGIN
                            INSERT INTO book_search_fts(book_search_fts, rowid, id, author, title, language)
                            VALUES('delete', old.rowid, old.id, old.author, old.title, old.language);
                            INSERT INTO book_search_fts(rowid, id, author, title, language)
                            VALUES (new.rowid, new.id, new.author, new.title, new.language);
                        END
                    """))
                    
                    # Populate FTS table with existing data
                    session.execute(text("""
                        INSERT INTO book_search_fts(rowid, id, author, title, language)
                        SELECT rowid, id, author, title, language FROM book_search
                    """))
                    
                    session.commit()
                    logger.info("FTS virtual table created successfully")
                else:
                    logger.debug("FTS virtual table already exists")
                    
            except Exception as e:
                logger.error(f"Error initializing FTS: {e}")
                session.rollback()
                # Continue without FTS - we'll fall back to LIKE queries
    
    def rebuild_fts(self) -> None:
        """Rebuild the FTS index."""
        with self.get_session() as session:
            try:
                logger.info("Rebuilding FTS index...")
                
                # Drop and recreate FTS table
                session.execute(text("DROP TABLE IF EXISTS book_search_fts"))
                
                # Recreate FTS table
                session.execute(text("""
                    CREATE VIRTUAL TABLE book_search_fts USING fts5(
                        id UNINDEXED,
                        author,
                        title,
                        language UNINDEXED,
                        content='book_search',
                        content_rowid='rowid'
                    )
                """))
                
                # Populate with existing data
                session.execute(text("""
                    INSERT INTO book_search_fts(rowid, id, author, title, language)
                    SELECT rowid, id, author, title, language FROM book_search
                """))
                
                session.commit()
                logger.info("FTS index rebuilt successfully")
                
            except Exception as e:
                logger.error(f"Error rebuilding FTS: {e}")
                session.rollback()
                raise
    
    def close(self) -> None:
        """Close database connections."""
        self.engine.dispose()
    
    def get_database_size(self) -> int:
        """Get the size of the database file in bytes."""
        db_file = Path(self.database_url.replace("sqlite:///", ""))
        return db_file.stat().st_size if db_file.exists() else 0 