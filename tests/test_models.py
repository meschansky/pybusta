"""
Tests for PyBusta data models.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile

from pybusta.core.models import (
    Book, SearchQuery, DatabaseConfig, SearchResult, 
    ExtractionResult, IndexStats
)


class TestBook:
    """Test the Book model."""
    
    def test_valid_book_creation(self):
        """Test creating a valid book."""
        book = Book(
            id=12345,
            title="Test Book",
            author="Test Author",
            extension="pdf",
            filesize=1024000,
            language="en",
            year=2023
        )
        
        assert book.id == 12345
        assert book.title == "Test Book"
        assert book.author == "Test Author"
        assert book.extension == "pdf"
        assert book.filesize == 1024000
        assert book.language == "en"
        assert book.year == 2023
    
    def test_book_text_cleaning(self):
        """Test text field cleaning."""
        book = Book(
            id=12345,
            title="  Test    Book  ",  # Extra whitespace
            author="  Test     Author  ",  # Extra whitespace
            extension="pdf",
            filesize=1024000
        )
        
        assert book.title == "Test Book"  # Should be cleaned
        assert book.author == "Test Author"  # Should be cleaned
    
    def test_book_validation_errors(self):
        """Test book validation errors."""
        with pytest.raises(ValueError):
            Book(
                # Missing required fields
                title="Test",
                # author missing
                # extension missing
                # filesize missing
            )


class TestSearchQuery:
    """Test the SearchQuery model."""
    
    def test_valid_search_query(self):
        """Test creating a valid search query."""
        query = SearchQuery(
            title="test book",
            author="test author",
            language="en",
            limit=25
        )
        
        assert query.title == "test book"  # Should be cleaned but not uppercased
        assert query.author == "test author"
        assert query.language == "en"
        assert query.limit == 25
    
    def test_search_query_defaults(self):
        """Test search query defaults."""
        query = SearchQuery()
        
        assert query.title is None
        assert query.author is None
        assert query.limit == 50  # Updated default
        assert query.offset == 0
    
    def test_has_search_terms(self):
        """Test has_search_terms method."""
        query1 = SearchQuery()
        assert not query1.has_search_terms()
        
        query2 = SearchQuery(title="test")
        assert query2.has_search_terms()
        
        query3 = SearchQuery(author="author")
        assert query3.has_search_terms()
        
        query4 = SearchQuery(format="pdf")
        assert query4.has_search_terms()
    
    def test_search_query_validation(self):
        """Test search query field validation."""
        # Test with extra whitespace
        query = SearchQuery(
            title="  test   book  ",
            author="  test    author  "
        )
        
        assert query.title == "test book"
        assert query.author == "test author"


class TestDatabaseConfig:
    """Test the DatabaseConfig model."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = DatabaseConfig()
        
        assert config.data_dir == Path("data")
        assert config.db_path == Path("data/db")
        assert config.extract_path == Path("data/books")
        assert config.tmp_path == Path("/tmp/pybusta")
        assert config.index_file == Path("data/fb2.Flibusta.Net/flibusta_fb2_local.inpx")
    
    def test_custom_config(self):
        """Test custom configuration values."""
        # Use temporary directories to avoid read-only file system issues
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_data_dir = Path(temp_dir) / "data"
            custom_db_path = Path(temp_dir) / "db"
            
            config = DatabaseConfig(
                data_dir=custom_data_dir,
                db_path=custom_db_path
            )
            
            assert config.data_dir == custom_data_dir
            assert config.db_path == custom_db_path
            assert config.data_dir.exists()  # Should be created by validator


class TestExtractionResult:
    """Test the ExtractionResult model."""
    
    def test_successful_extraction(self):
        """Test successful extraction result."""
        result = ExtractionResult(
            book_id=12345,
            original_filename="book.fb2",
            extracted_filename="Author - Title.fb2",
            file_path=Path("/tmp/extracted/book.fb2"),
            file_size=1024000,
            success=True
        )
        
        assert result.success is True
        assert result.book_id == 12345
        assert result.original_filename == "book.fb2"
        assert result.extracted_filename == "Author - Title.fb2"
        assert result.file_path == Path("/tmp/extracted/book.fb2")
        assert result.file_size == 1024000
        assert result.error_message is None
    
    def test_failed_extraction(self):
        """Test failed extraction result."""
        result = ExtractionResult(
            book_id=12345,
            original_filename="book.fb2",
            extracted_filename="Author - Title.fb2",
            file_path=Path("/tmp/extracted/book.fb2"),
            file_size=0,
            success=False,
            error_message="Extraction failed: file not found"
        )
        
        assert result.success is False
        assert result.error_message == "Extraction failed: file not found"
        assert result.file_size == 0


class TestIndexStats:
    """Test the IndexStats model."""
    
    def test_index_stats_creation(self):
        """Test creating index stats."""
        stats = IndexStats(
            total_books=1000,
            total_authors=500,
            total_genres=50,
            languages={"en": 500, "ru": 300, "fr": 200},
            formats={"fb2": 600, "epub": 400},
            index_size=5000000,
            last_updated=datetime(2023, 12, 1)
        )
        
        assert stats.total_books == 1000
        assert stats.total_authors == 500
        assert stats.total_genres == 50
        assert stats.languages == {"en": 500, "ru": 300, "fr": 200}
        assert stats.formats == {"fb2": 600, "epub": 400}
        assert stats.index_size == 5000000
    
    def test_index_stats_defaults(self):
        """Test index stats defaults."""
        stats = IndexStats()
        
        assert stats.total_books == 0
        assert stats.total_authors == 0
        assert stats.total_genres == 0
        assert stats.languages == {}
        assert stats.formats == {}
        assert stats.index_size == 0
        assert stats.last_updated is None
        assert stats.index_file_checksum is None 