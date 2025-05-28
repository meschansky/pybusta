"""
Tests for PyBusta CLI functionality.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch

from pybusta.cli.main import main
from pybusta.core.models import SearchResult, SearchQuery, IndexStats


class TestCLI:
    """Tests for the CLI interface."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_main_help(self):
        """Test that the main help command works."""
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'PyBusta' in result.output
        assert 'Modern tool for accessing Flibusta book archives' in result.output
    
    def test_search_help(self):
        """Test that the search help command works."""
        result = self.runner.invoke(main, ['search', '--help'])
        assert result.exit_code == 0
        assert 'Search for books in the index' in result.output
    
    def test_extract_help(self):
        """Test that the extract help command works."""
        result = self.runner.invoke(main, ['extract', '--help'])
        assert result.exit_code == 0
        assert 'Extract a book by its ID' in result.output
    
    def test_stats_help(self):
        """Test that the stats help command works."""
        result = self.runner.invoke(main, ['stats', '--help'])
        assert result.exit_code == 0
        assert 'Show statistics about the book index' in result.output
    
    def test_index_help(self):
        """Test that the index help command works."""
        result = self.runner.invoke(main, ['index', '--help'])
        assert result.exit_code == 0
        assert 'Create or rebuild the book index' in result.output
    
    def test_search_without_terms(self):
        """Test that search fails without search terms."""
        result = self.runner.invoke(main, ['search'])
        assert result.exit_code == 1
        assert 'At least one search term' in result.output
    
    @patch('pybusta.cli.main.BookIndex')
    def test_search_with_title(self, mock_book_index):
        """Test search with title parameter."""
        # Mock the BookIndex and search result
        mock_instance = Mock()
        mock_book_index.return_value = mock_instance
        
        mock_result = SearchResult(
            books=[],
            total_count=0,
            query=SearchQuery(title="test"),
            execution_time=0.1
        )
        mock_instance.search.return_value = mock_result
        
        result = self.runner.invoke(main, ['search', '--title', 'test'])
        assert result.exit_code == 0
        assert 'No books found matching your criteria.' in result.output
    
    @patch('pybusta.cli.main.BookIndex')
    def test_stats_command(self, mock_book_index):
        """Test the stats command."""
        # Mock the BookIndex and stats
        mock_instance = Mock()
        mock_book_index.return_value = mock_instance
        
        mock_stats = IndexStats(
            total_books=1000,
            total_authors=100,
            total_genres=10,
            languages={"ru": 800, "en": 200},
            formats={"fb2": 900, "epub": 100},
            index_size=1024000
        )
        mock_instance.get_stats.return_value = mock_stats
        
        result = self.runner.invoke(main, ['stats'])
        assert result.exit_code == 0
        assert 'Index Statistics' in result.output
        assert '1,000' in result.output  # Total books
    
    @patch('pybusta.cli.main.BookIndex')
    def test_extract_command(self, mock_book_index):
        """Test the extract command."""
        from pybusta.core.models import ExtractionResult
        from pathlib import Path
        
        # Mock the BookIndex and extraction result
        mock_instance = Mock()
        mock_book_index.return_value = mock_instance
        
        mock_result = ExtractionResult(
            book_id=12345,
            original_filename="12345.fb2",
            extracted_filename="Author - Title.fb2",
            file_path=Path("/path/to/file.fb2"),
            file_size=1024000,
            success=True
        )
        mock_instance.extract_book.return_value = mock_result
        
        result = self.runner.invoke(main, ['extract', '12345'])
        assert result.exit_code == 0
        assert 'Successfully extracted book 12345' in result.output
    
    @patch('pybusta.cli.main.BookIndex')
    def test_extract_command_failure(self, mock_book_index):
        """Test the extract command with failure."""
        from pybusta.core.models import ExtractionResult
        from pathlib import Path
        
        # Mock the BookIndex and extraction result
        mock_instance = Mock()
        mock_book_index.return_value = mock_instance
        
        mock_result = ExtractionResult(
            book_id=12345,
            original_filename="12345.fb2",
            extracted_filename="Author - Title.fb2",
            file_path=Path("/path/to/file.fb2"),
            file_size=0,
            success=False,
            error_message="Book not found"
        )
        mock_instance.extract_book.return_value = mock_result
        
        result = self.runner.invoke(main, ['extract', '12345'])
        assert result.exit_code == 1
        assert 'Failed to extract book 12345' in result.output
        assert 'Book not found' in result.output
    
    def test_search_output_formats(self):
        """Test different output formats for search."""
        # Test JSON output
        result = self.runner.invoke(main, ['search', '--title', 'test', '--output', 'json'])
        # Should fail without proper setup, but command should be recognized
        assert 'json' in str(result.exception) or result.exit_code in [0, 1]
        
        # Test CSV output
        result = self.runner.invoke(main, ['search', '--title', 'test', '--output', 'csv'])
        # Should fail without proper setup, but command should be recognized
        assert 'csv' in str(result.exception) or result.exit_code in [0, 1]
    
    def test_verbose_flag(self):
        """Test that verbose flag is accepted."""
        result = self.runner.invoke(main, ['--verbose', '--help'])
        assert result.exit_code == 0
        assert 'PyBusta' in result.output
    
    def test_data_dir_option(self):
        """Test that data-dir option is accepted."""
        with self.runner.isolated_filesystem():
            # Create a temporary directory
            import os
            os.makedirs('test_data', exist_ok=True)
            
            result = self.runner.invoke(main, ['--data-dir', 'test_data', '--help'])
            assert result.exit_code == 0 