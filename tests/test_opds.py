"""
Tests for OPDS functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from xml.etree.ElementTree import fromstring

from pybusta.core.models import Book, SearchResult, SearchQuery
from pybusta.opds.models import OPDSFeed, OPDSEntry, OPDSLink, book_to_opds_entry
from pybusta.opds.feeds import OPDSFeedGenerator


class TestOPDSModels:
    """Test OPDS model classes."""
    
    def test_opds_link_to_xml(self):
        """Test OPDSLink XML generation."""
        link = OPDSLink(
            rel="self",
            href="http://example.com/feed",
            type="application/atom+xml",
            title="Test Feed"
        )
        
        # Create a mock parent element
        from xml.etree.ElementTree import Element
        parent = Element("feed")
        link_elem = link.to_xml(parent)
        
        assert link_elem.get("rel") == "self"
        assert link_elem.get("href") == "http://example.com/feed"
        assert link_elem.get("type") == "application/atom+xml"
        assert link_elem.get("title") == "Test Feed"
    
    def test_opds_entry_to_xml(self):
        """Test OPDSEntry XML generation."""
        entry = OPDSEntry(
            id="urn:uuid:test-123",
            title="Test Book",
            updated=datetime(2023, 1, 1, 12, 0, 0),
            summary="A test book",
            authors=["Test Author"],
            language="en",
            links=[
                OPDSLink(
                    rel="http://opds-spec.org/acquisition/open-access",
                    href="http://example.com/download/123",
                    type="application/epub+zip"
                )
            ]
        )
        
        from xml.etree.ElementTree import Element
        parent = Element("feed")
        entry_elem = entry.to_xml(parent)
        
        # Check basic elements
        assert entry_elem.find("id").text == "urn:uuid:test-123"
        assert entry_elem.find("title").text == "Test Book"
        assert entry_elem.find("summary").text == "A test book"
        
        # Check author
        author_elem = entry_elem.find("author")
        assert author_elem is not None
        assert author_elem.find("name").text == "Test Author"
        
        # Check link
        link_elem = entry_elem.find("link")
        assert link_elem is not None
        assert link_elem.get("rel") == "http://opds-spec.org/acquisition/open-access"
    
    def test_opds_feed_to_xml(self):
        """Test OPDSFeed XML generation."""
        feed = OPDSFeed(
            id="urn:uuid:test-feed",
            title="Test Feed",
            updated=datetime(2023, 1, 1, 12, 0, 0),
            subtitle="A test feed",
            entries=[
                OPDSEntry(
                    id="urn:uuid:test-entry",
                    title="Test Entry",
                    updated=datetime(2023, 1, 1, 12, 0, 0)
                )
            ]
        )
        
        xml_string = feed.to_xml()
        
        # Parse and verify XML structure
        root = fromstring(xml_string)
        
        # Check with namespace - the root will have namespaces
        assert root.tag == "{http://www.w3.org/2005/Atom}feed"
        
        # Find elements by namespace
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        id_elem = root.find("atom:id", ns)
        title_elem = root.find("atom:title", ns)
        subtitle_elem = root.find("atom:subtitle", ns)
        
        assert id_elem is not None
        assert id_elem.text == "urn:uuid:test-feed"
        assert title_elem.text == "Test Feed"
        assert subtitle_elem.text == "A test feed"
        
        # Check entry
        entry = root.find("atom:entry", ns)
        assert entry is not None
        entry_title = entry.find("atom:title", ns)
        assert entry_title.text == "Test Entry"
    
    def test_book_to_opds_entry(self):
        """Test converting a Book to OPDSEntry."""
        book = Book(
            id=123,
            title="Test Novel",
            author="Jane Doe,John Smith",  # Use 'author' not 'authors'
            extension="fb2",
            filesize=1024000,
            language="en",
            year=2023
        )
        
        entry = book_to_opds_entry(book, "http://example.com")
        
        assert entry.id == "urn:uuid:book-123"
        assert entry.title == "Test Novel"
        assert entry.authors == ["Jane Doe", "John Smith"]
        assert entry.language == "en"
        assert entry.issued == "2023"
        
        # Check links
        assert len(entry.links) == 3  # cover, download, alternate
        download_link = next(
            link for link in entry.links 
            if link.rel == "http://opds-spec.org/acquisition/open-access"
        )
        assert download_link.href == "http://example.com/api/download/123"


class TestOPDSFeedGenerator:
    """Test OPDS feed generation."""
    
    @pytest.fixture
    def mock_book_index(self):
        """Create a mock BookIndex."""
        mock_index = Mock()
        
        # Mock search results
        mock_books = [
            Book(
                id=1,
                title="Test Book 1",
                author="Author One",
                extension="fb2",
                filesize=1024000,
                language="en"
            ),
            Book(
                id=2,
                title="Test Book 2",
                author="Author Two",
                extension="epub",
                filesize=2048000,
                language="en"
            )
        ]
        
        # Create a proper SearchQuery
        mock_query = SearchQuery(title="test")
        
        mock_result = SearchResult(
            books=mock_books,
            total_count=2,
            execution_time=0.1,
            query=mock_query
        )
        mock_index.search.return_value = mock_result
        
        # Mock stats
        from pybusta.core.models import IndexStats
        mock_stats = IndexStats(
            total_books=1000,
            total_authors=500,
            total_genres=50,
            languages={"en": 800, "ru": 200},
            formats={"fb2": 600, "epub": 400},
            index_size=100*1024*1024  # 100 MB
        )
        mock_index.get_stats.return_value = mock_stats
        
        return mock_index
    
    @pytest.fixture
    def feed_generator(self, mock_book_index):
        """Create an OPDSFeedGenerator with mock dependencies."""
        return OPDSFeedGenerator(mock_book_index, "http://example.com")
    
    def test_generate_root_feed(self, feed_generator):
        """Test root feed generation."""
        xml_string = feed_generator.generate_root_feed()
        
        # Parse XML and verify structure
        root = fromstring(xml_string)
        
        # Check with namespace
        assert root.tag == "{http://www.w3.org/2005/Atom}feed"
        
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        title = root.find("atom:title", ns)
        assert title is not None
        assert "PyBusta OPDS Catalog" in title.text
        
        # Check for navigation entries
        entries = root.findall("atom:entry", ns)
        assert len(entries) >= 4  # new, popular, authors, genres, all
        
        entry_titles = []
        for entry in entries:
            title_elem = entry.find("atom:title", ns)
            if title_elem is not None:
                entry_titles.append(title_elem.text)
        
        assert "New Publications" in entry_titles
        assert "Popular Publications" in entry_titles
        assert "All Publications" in entry_titles
    
    def test_generate_search_results(self, feed_generator):
        """Test search results feed generation."""
        xml_string = feed_generator.generate_search_results("test query", limit=10, offset=0)
        
        # Parse XML and verify structure
        root = fromstring(xml_string)
        
        assert root.tag == "{http://www.w3.org/2005/Atom}feed"
        
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        title = root.find("atom:title", ns)
        assert "Search Results for 'test query'" in title.text
        
        # Check for book entries
        entries = root.findall("atom:entry", ns)
        assert len(entries) == 2  # Mock returns 2 books
        
        # Check OpenSearch elements
        total_results = root.find(".//{http://a9.com/-/spec/opensearch/1.1/}totalResults")
        assert total_results is not None
        assert total_results.text == "2"
    
    def test_generate_new_publications(self, feed_generator):
        """Test new publications feed generation."""
        xml_string = feed_generator.generate_new_publications(limit=20, offset=0)
        
        # Parse XML and verify structure
        root = fromstring(xml_string)
        
        assert root.tag == "{http://www.w3.org/2005/Atom}feed"
        
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        title = root.find("atom:title", ns)
        assert title.text == "New Publications"
        
        # Check for book entries
        entries = root.findall("atom:entry", ns)
        assert len(entries) == 2  # Mock returns 2 books
    
    def test_generate_opensearch_description(self, feed_generator):
        """Test OpenSearch description generation."""
        xml_string = feed_generator.generate_opensearch_description()
        
        # Parse XML and verify structure
        root = fromstring(xml_string)
        
        # The root element will have the OpenSearch namespace
        assert root.tag == "{http://a9.com/-/spec/opensearch/1.1/}OpenSearchDescription"
        
        ns = {"os": "http://a9.com/-/spec/opensearch/1.1/"}
        short_name = root.find("os:ShortName", ns)
        assert short_name is not None
        assert short_name.text == "PyBusta"
        
        # Check for URL templates
        urls = root.findall("os:Url", ns)
        assert len(urls) >= 1
        
        opds_url = None
        for url in urls:
            if "opds-catalog" in url.get("type", ""):
                opds_url = url
                break
        
        assert opds_url is not None
        assert "searchTerms" in opds_url.get("template")
    
    def test_generate_single_entry(self, feed_generator, mock_book_index):
        """Test single book entry generation."""
        # Mock the search to return a specific book
        mock_book = Book(
            id=123,
            title="Specific Test Book",
            author="Test Author",
            extension="fb2",
            filesize=1024000
        )
        mock_query = SearchQuery(title="test")
        mock_result = SearchResult(
            books=[mock_book],
            total_count=1,
            execution_time=0.05,
            query=mock_query
        )
        mock_book_index.search.return_value = mock_result
        
        xml_string = feed_generator.generate_single_entry(123)
        
        # Parse XML and verify structure
        root = fromstring(xml_string)
        
        assert root.tag == "{http://www.w3.org/2005/Atom}feed"
        
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        assert entry is not None
        
        title = entry.find("atom:title", ns)
        assert title.text == "Specific Test Book"
        
        # Check for acquisition links
        links = entry.findall("atom:link", ns)
        acquisition_links = [
            link for link in links 
            if link.get("rel") == "http://opds-spec.org/acquisition/open-access"
        ]
        assert len(acquisition_links) >= 1
    
    def test_error_handling(self, feed_generator, mock_book_index):
        """Test error handling in feed generation."""
        # Make the mock raise an exception
        mock_book_index.search.side_effect = Exception("Database error")
        
        # Search should return an error feed instead of raising
        xml_string = feed_generator.generate_search_results("failing query")
        root = fromstring(xml_string)
        
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        title = root.find("atom:title", ns)
        assert "Search Results for 'failing query'" in title.text
        
        subtitle = root.find("atom:subtitle", ns)
        assert subtitle.text == "Search failed"
        
        # Should have no entries
        entries = root.findall("atom:entry", ns)
        assert len(entries) == 0 