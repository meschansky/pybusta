"""
Modern BookIndex implementation with type safety and proper error handling.
"""

import hashlib
import logging
import shutil
import time
import zipfile
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple, Union

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session

from .database import BookRecord, BookSearchRecord, DatabaseManager, SettingsRecord
from .models import (
    Book, BookFormat, DatabaseConfig, ExtractionResult, 
    IndexStats, Language, SearchQuery, SearchResult
)

logger = logging.getLogger(__name__)


class BookIndexError(Exception):
    """Base exception for BookIndex operations."""
    pass


class IndexNotFoundError(BookIndexError):
    """Raised when the Flibusta index file is not found."""
    pass


class ExtractionError(BookIndexError):
    """Raised when book extraction fails."""
    pass


class BookIndex:
    """
    Modern implementation of the book index with type safety and proper error handling.
    
    This class provides functionality to:
    - Index books from Flibusta archive files
    - Search books using full-text search
    - Extract books from archives
    - Manage database operations
    """
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the BookIndex.
        
        Args:
            config: Database configuration. If None, uses default configuration.
        """
        self.config = config or DatabaseConfig()
        self.db_manager = DatabaseManager(self.config.db_path)
        self._index_field_mapping = {
            0: 'author',
            1: 'genre', 
            2: 'title',
            5: 'bookid',
            6: 'size',
            9: 'format',
            10: 'date_added',
            11: 'language'
        }
        
        # Initialize index if needed
        if self._should_rebuild_index():
            logger.info("Index needs to be rebuilt")
            self.create_index()
        else:
            logger.info("Using existing index")
    
    def _should_rebuild_index(self) -> bool:
        """Check if the index needs to be rebuilt."""
        if not self.config.index_file or not self.config.index_file.exists():
            logger.warning(f"Index file not found: {self.config.index_file}")
            return False
        
        # Check if database exists
        with self.db_manager.get_session() as session:
            book_count = session.query(func.count(BookRecord.id)).scalar()
            if book_count == 0:
                return True
            
            # Check if index file has changed
            current_checksum = self._calculate_index_checksum()
            stored_checksum = self._get_stored_checksum(session)
            
            return current_checksum != stored_checksum
    
    def _calculate_index_checksum(self) -> str:
        """Calculate MD5 checksum of the index file."""
        if not self.config.index_file or not self.config.index_file.exists():
            return ""
        
        hash_md5 = hashlib.md5()
        with open(self.config.index_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_stored_checksum(self, session: Session) -> Optional[str]:
        """Get the stored checksum from the database."""
        setting = session.query(SettingsRecord).filter(
            SettingsRecord.name == "index_file_checksum"
        ).first()
        return setting.value if setting else None
    
    def _store_checksum(self, session: Session, checksum: str) -> None:
        """Store the checksum in the database."""
        setting = session.query(SettingsRecord).filter(
            SettingsRecord.name == "index_file_checksum"
        ).first()
        
        if setting:
            setting.value = checksum
        else:
            setting = SettingsRecord(name="index_file_checksum", value=checksum)
            session.add(setting)
    
    def create_index(self) -> None:
        """Create the book index from the Flibusta archive."""
        if not self.config.index_file or not self.config.index_file.exists():
            raise IndexNotFoundError(f"Index file not found: {self.config.index_file}")
        
        logger.info("Starting index creation")
        start_time = time.time()
        
        # Clear existing data
        with self.db_manager.get_session() as session:
            session.query(BookRecord).delete()
            session.query(BookSearchRecord).delete()
            session.commit()
        
        # Extract and process index files
        self._extract_index_archive()
        
        try:
            total_books = 0
            for index_file in self._get_index_files():
                logger.info(f"Processing {index_file}")
                books_processed = self._process_index_file(index_file)
                total_books += books_processed
                logger.info(f"Processed {books_processed} books from {index_file}")
            
            # Store checksum
            with self.db_manager.get_session() as session:
                checksum = self._calculate_index_checksum()
                self._store_checksum(session, checksum)
                session.commit()
            
            elapsed_time = time.time() - start_time
            logger.info(f"Index creation completed. Processed {total_books} books in {elapsed_time:.2f} seconds")
            
        finally:
            # Clean up temporary files
            if self.config.tmp_path.exists():
                shutil.rmtree(self.config.tmp_path)
    
    def _extract_index_archive(self) -> None:
        """Extract the index archive to temporary directory."""
        self.config.tmp_path.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(self.config.index_file, 'r') as archive:
            archive.extractall(self.config.tmp_path)
    
    def _get_index_files(self) -> Generator[Path, None, None]:
        """Get iterator over index files."""
        return self.config.tmp_path.glob("*.inp")
    
    def _process_index_file(self, index_file: Path) -> int:
        """Process a single index file and return number of books processed."""
        books_processed = 0
        archive_name = index_file.stem + ".zip"
        
        with self.db_manager.get_session() as session:
            with open(index_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        if line.strip():
                            book_data = self._parse_book_metadata(line, archive_name)
                            if book_data:
                                self._store_book_data(session, book_data)
                                books_processed += 1
                                
                                # Commit in batches for better performance
                                if books_processed % 1000 == 0:
                                    session.commit()
                                    
                    except Exception as e:
                        logger.warning(f"Error processing line {line_num} in {index_file}: {e}")
                        continue
            
            session.commit()
        
        return books_processed
    
    def _parse_book_metadata(self, line: str, archive_name: str) -> Optional[Dict]:
        """Parse a line of book metadata."""
        try:
            fields = line.strip().split('\x04')
            if len(fields) < 12:
                return None
            
            # Map fields to book data
            book_data = {}
            for index, field_name in self._index_field_mapping.items():
                if index < len(fields):
                    book_data[field_name] = fields[index].strip()
            
            # Clean and validate data
            book_data['archive_file'] = archive_name
            book_data['author'] = book_data.get('author', '').replace(',', ' ').replace(':', '').strip()
            book_data['title'] = book_data.get('title', '').strip()
            book_data['genre'] = book_data.get('genre', '').replace(':', '').strip()
            
            # Convert size to integer
            try:
                book_data['size'] = int(book_data.get('size', 0))
            except (ValueError, TypeError):
                book_data['size'] = 0
            
            # Validate required fields
            if not book_data.get('bookid') or not book_data.get('title') or not book_data.get('author'):
                return None
            
            return book_data
            
        except Exception as e:
            logger.warning(f"Error parsing metadata: {e}")
            return None
    
    def _store_book_data(self, session: Session, book_data: Dict) -> None:
        """Store book data in the database."""
        try:
            # Create book record
            book_record = BookRecord(
                id=int(book_data['bookid']),
                title=book_data['title'],
                author=book_data['author'],
                genre=book_data.get('genre'),
                language=book_data.get('language', 'ru'),
                format=book_data.get('format', 'fb2'),
                size=book_data['size'],
                archive_file=book_data['archive_file']
            )
            session.merge(book_record)  # Use merge to handle duplicates
            
            # Create search record
            search_record = BookSearchRecord(
                id=int(book_data['bookid']),
                author=book_data['author'].upper(),
                title=book_data['title'].upper(),
                language=book_data.get('language', 'ru')
            )
            session.merge(search_record)
            
        except Exception as e:
            logger.error(f"Error storing book data: {e}")
            raise
    
    def search(self, query: SearchQuery) -> SearchResult:
        """
        Search for books using the provided query.
        
        Args:
            query: Search query parameters
            
        Returns:
            SearchResult containing matching books and metadata
        """
        start_time = time.time()
        
        with self.db_manager.get_session() as session:
            # Build the query
            db_query = session.query(BookRecord)
            
            # Apply filters
            conditions = []
            
            if query.title:
                conditions.append(self._build_title_condition(session, query.title))
            
            if query.author:
                conditions.append(self._build_author_condition(session, query.author))
            
            if query.language:
                conditions.append(BookRecord.language == query.language)
            
            if query.genre:
                conditions.append(BookRecord.genre.ilike(f"%{query.genre}%"))
            
            if query.format:
                conditions.append(BookRecord.format == query.format)
            
            # Apply conditions
            if conditions:
                db_query = db_query.filter(and_(*conditions))
            
            # Get total count
            total_count = db_query.count()
            
            # Apply pagination and get results
            books_data = db_query.offset(query.offset).limit(query.limit).all()
            
            # Convert to Book models
            books = []
            for book_record in books_data:
                try:
                    book = Book(
                        id=book_record.id,
                        title=book_record.title,
                        author=book_record.author,
                        extension=book_record.format,  # Map database 'format' to model 'extension'
                        filesize=book_record.size,     # Map database 'size' to model 'filesize'
                        language=book_record.language,
                        added=book_record.date_added
                    )
                    books.append(book)
                except Exception as e:
                    logger.warning(f"Error converting book record {book_record.id}: {e}")
                    continue
            
            execution_time = time.time() - start_time
            
            return SearchResult(
                books=books,
                total_count=total_count,
                query=query,
                execution_time=execution_time
            )
    
    def _build_title_condition(self, session: Session, title: str):
        """Build search condition for title with FTS fallback."""
        if len(title) > 2:
            try:
                # Try FTS search first
                fts_query = f'title:"{title}"'
                fts_results = session.execute(
                    text("SELECT id FROM book_search_fts WHERE book_search_fts MATCH :query"),
                    {"query": fts_query}
                ).fetchall()
                book_ids = [row[0] for row in fts_results]
                if book_ids:
                    return BookRecord.id.in_(book_ids)
                else:
                    # No FTS results, fall back to LIKE
                    return BookRecord.title.ilike(f"%{title}%")
            except Exception as e:
                logger.warning(f"FTS search failed for title '{title}': {e}")
                # Fall back to LIKE search
                return BookRecord.title.ilike(f"%{title}%")
        else:
            return BookRecord.title.ilike(f"%{title}%")
    
    def _build_author_condition(self, session: Session, author: str):
        """Build search condition for author with FTS fallback."""
        if len(author) > 2:
            try:
                # Try FTS search first
                fts_query = f'author:"{author}"'
                fts_results = session.execute(
                    text("SELECT id FROM book_search_fts WHERE book_search_fts MATCH :query"),
                    {"query": fts_query}
                ).fetchall()
                book_ids = [row[0] for row in fts_results]
                if book_ids:
                    return BookRecord.id.in_(book_ids)
                else:
                    # No FTS results, fall back to LIKE
                    return BookRecord.author.ilike(f"%{author}%")
            except Exception as e:
                logger.warning(f"FTS search failed for author '{author}': {e}")
                # Fall back to LIKE search
                return BookRecord.author.ilike(f"%{author}%")
        else:
            return BookRecord.author.ilike(f"%{author}%")
    
    def rebuild_search_index(self) -> None:
        """Rebuild the full-text search index."""
        logger.info("Rebuilding search index...")
        self.db_manager.rebuild_fts()
        logger.info("Search index rebuilt successfully")
    
    def extract_book(self, book_id: int) -> ExtractionResult:
        """
        Extract a book by its ID.
        
        Args:
            book_id: The ID of the book to extract
            
        Returns:
            ExtractionResult with extraction details
        """
        with self.db_manager.get_session() as session:
            book_record = session.query(BookRecord).filter(BookRecord.id == book_id).first()
            
            if not book_record:
                return ExtractionResult(
                    book_id=book_id,
                    original_filename="",
                    extracted_filename="",
                    file_path=Path(),
                    file_size=0,
                    success=False,
                    error_message=f"Book with ID {book_id} not found"
                )
            
            try:
                # Ensure extraction directory exists
                self.config.extract_path.mkdir(parents=True, exist_ok=True)
                
                # Build file paths
                archive_path = self.config.data_dir / "fb2.Flibusta.Net" / book_record.archive_file
                original_filename = f"{book_id}.{book_record.format}"
                
                # Create safe filename for extraction
                safe_title = "".join(c for c in book_record.title if c.isalnum() or c in (' ', '-', '_')).strip()
                safe_author = "".join(c for c in book_record.author if c.isalnum() or c in (' ', '-', '_')).strip()
                extracted_filename = f"{safe_author} - {safe_title}.{book_record.format}"
                extracted_path = self.config.extract_path / extracted_filename
                
                # Extract from archive
                if not archive_path.exists():
                    return ExtractionResult(
                        book_id=book_id,
                        original_filename=original_filename,
                        extracted_filename=extracted_filename,
                        file_path=extracted_path,
                        file_size=0,
                        success=False,
                        error_message=f"Archive file not found: {archive_path}"
                    )
                
                with zipfile.ZipFile(archive_path, 'r') as archive:
                    # Extract to temporary location first
                    temp_path = self.config.extract_path / original_filename
                    archive.extract(original_filename, self.config.extract_path)
                    
                    # Rename to final location
                    temp_path.rename(extracted_path)
                
                file_size = extracted_path.stat().st_size
                
                return ExtractionResult(
                    book_id=book_id,
                    original_filename=original_filename,
                    extracted_filename=extracted_filename,
                    file_path=extracted_path,
                    file_size=file_size,
                    success=True,
                    error_message=None
                )
                
            except Exception as e:
                logger.error(f"Error extracting book {book_id}: {e}")
                return ExtractionResult(
                    book_id=book_id,
                    original_filename=original_filename if 'original_filename' in locals() else "",
                    extracted_filename=extracted_filename if 'extracted_filename' in locals() else "",
                    file_path=extracted_path if 'extracted_path' in locals() else Path(),
                    file_size=0,
                    success=False,
                    error_message=str(e)
                )
    
    def get_stats(self) -> IndexStats:
        """Get statistics about the book index."""
        with self.db_manager.get_session() as session:
            # Basic counts
            total_books = session.query(func.count(BookRecord.id)).scalar() or 0
            total_authors = session.query(func.count(func.distinct(BookRecord.author))).scalar() or 0
            total_genres = session.query(func.count(func.distinct(BookRecord.genre))).scalar() or 0
            
            # Language distribution
            language_stats = session.query(
                BookRecord.language, func.count(BookRecord.id)
            ).group_by(BookRecord.language).all()
            languages = {lang: count for lang, count in language_stats}
            
            # Format distribution
            format_stats = session.query(
                BookRecord.format, func.count(BookRecord.id)
            ).group_by(BookRecord.format).all()
            formats = {fmt: count for fmt, count in format_stats}
            
            # Get checksum
            checksum = self._get_stored_checksum(session)
            
            return IndexStats(
                total_books=total_books,
                total_authors=total_authors,
                total_genres=total_genres,
                languages=languages,
                formats=formats,
                index_size=self.db_manager.get_database_size(),
                index_file_checksum=checksum
            )
    
    def close(self) -> None:
        """Close database connections and clean up resources."""
        self.db_manager.close() 