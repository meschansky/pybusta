"""
OPDS feed generators for PyBusta.

This module contains the logic for generating various OPDS feeds including
navigation feeds, acquisition feeds, and search results.
"""

import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

from ..core.book_index import BookIndex
from ..core.models import SearchQuery, SearchResult
from .models import OPDSFeed, OPDSEntry, OPDSLink, book_to_opds_entry

logger = logging.getLogger(__name__)


class OPDSFeedGenerator:
    """Generates OPDS feeds for PyBusta."""
    
    def __init__(self, book_index: BookIndex, base_url: str):
        """Initialize the feed generator."""
        self.book_index = book_index
        self.base_url = base_url.rstrip('/')
        
    def _get_feed_id(self, path: str) -> str:
        """Generate a consistent feed ID for a given path."""
        return f"urn:uuid:pybusta-{path.replace('/', '-').strip('-')}"
        
    def _get_navigation_links(self) -> List[OPDSLink]:
        """Get standard navigation links for feeds."""
        return [
            OPDSLink(
                rel="self",
                href=f"{self.base_url}/opds",
                type="application/atom+xml;profile=opds-catalog;kind=navigation"
            ),
            OPDSLink(
                rel="start",
                href=f"{self.base_url}/opds",
                type="application/atom+xml;profile=opds-catalog;kind=navigation",
                title="OPDS Catalog Root"
            ),
            OPDSLink(
                rel="search",
                href=f"{self.base_url}/opds/search{{?query}}",
                type="application/opensearchdescription+xml",
                title="Search"
            )
        ]
        
    def _get_acquisition_links(self, current_path: str) -> List[OPDSLink]:
        """Get standard links for acquisition feeds."""
        return [
            OPDSLink(
                rel="self",
                href=f"{self.base_url}{current_path}",
                type="application/atom+xml;profile=opds-catalog;kind=acquisition"
            ),
            OPDSLink(
                rel="start",
                href=f"{self.base_url}/opds",
                type="application/atom+xml;profile=opds-catalog;kind=navigation",
                title="OPDS Catalog Root"
            ),
            OPDSLink(
                rel="up",
                href=f"{self.base_url}/opds",
                type="application/atom+xml;profile=opds-catalog;kind=navigation",
                title="Up"
            )
        ]
        
    def generate_root_feed(self) -> str:
        """Generate the OPDS catalog root navigation feed."""
        logger.info("Generating OPDS root feed")
        
        try:
            stats = self.book_index.get_stats()
        except Exception as e:
            logger.warning(f"Could not get stats for root feed: {e}")
            stats = None
            
        # Create navigation entries
        entries = [
            OPDSEntry(
                id=self._get_feed_id("new"),
                title="New Publications",
                updated=datetime.now(),
                summary="Recently added publications to the catalog",
                links=[
                    OPDSLink(
                        rel="http://opds-spec.org/sort/new",
                        href=f"{self.base_url}/opds/new",
                        type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                        title="New Publications"
                    )
                ]
            ),
            OPDSEntry(
                id=self._get_feed_id("popular"),
                title="Popular Publications",
                updated=datetime.now(),
                summary="Most downloaded publications from the catalog",
                links=[
                    OPDSLink(
                        rel="http://opds-spec.org/sort/popular",
                        href=f"{self.base_url}/opds/popular",
                        type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                        title="Popular Publications"
                    )
                ]
            ),
            OPDSEntry(
                id=self._get_feed_id("authors"),
                title="Browse by Author",
                updated=datetime.now(),
                summary="Browse publications by author",
                links=[
                    OPDSLink(
                        rel="subsection",
                        href=f"{self.base_url}/opds/authors",
                        type="application/atom+xml;profile=opds-catalog;kind=navigation",
                        title="Authors"
                    )
                ]
            ),
            OPDSEntry(
                id=self._get_feed_id("genres"),
                title="Browse by Genre",
                updated=datetime.now(),
                summary="Browse publications by genre",
                links=[
                    OPDSLink(
                        rel="subsection",
                        href=f"{self.base_url}/opds/genres",
                        type="application/atom+xml;profile=opds-catalog;kind=navigation",
                        title="Genres"
                    )
                ]
            ),
            OPDSEntry(
                id=self._get_feed_id("all"),
                title="All Publications",
                updated=datetime.now(),
                summary=f"All {stats.total_books if stats else 'available'} publications in the catalog",
                links=[
                    OPDSLink(
                        rel="subsection",
                        href=f"{self.base_url}/opds/all",
                        type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                        title="All Publications"
                    )
                ]
            )
        ]
        
        subtitle = "Flibusta Digital Library OPDS Catalog"
        if stats:
            subtitle += f" - {stats.total_books:,} books available"
            
        feed = OPDSFeed(
            id=self._get_feed_id("root"),
            title="PyBusta OPDS Catalog",
            subtitle=subtitle,
            updated=datetime.now(),
            links=self._get_navigation_links(),
            entries=entries
        )
        
        return feed.to_xml()
        
    def generate_search_results(self, query: str, limit: int = 20, offset: int = 0) -> str:
        """Generate OPDS feed for search results."""
        logger.info(f"Generating OPDS search results for query: {query}")
        
        try:
            search_query = SearchQuery(
                title=query,
                author=query,
                limit=limit,
                offset=offset
            )
            result = self.book_index.search(search_query)
            
            # Convert books to OPDS entries
            entries = [book_to_opds_entry(book, self.base_url) for book in result.books]
            
            # Calculate pagination
            total_pages = (result.total_count + limit - 1) // limit if result.total_count > 0 else 1
            current_page = (offset // limit) + 1
            
            # Pagination links
            links = self._get_acquisition_links(f"/opds/search?query={query}")
            
            if current_page > 1:
                prev_offset = max(0, offset - limit)
                links.append(OPDSLink(
                    rel="previous",
                    href=f"{self.base_url}/opds/search?query={query}&offset={prev_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                    title="Previous"
                ))
                
            if current_page < total_pages:
                next_offset = offset + limit
                links.append(OPDSLink(
                    rel="next",
                    href=f"{self.base_url}/opds/search?query={query}&offset={next_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                    title="Next"
                ))
                
            feed = OPDSFeed(
                id=self._get_feed_id(f"search-{query}"),
                title=f"Search Results for '{query}'",
                subtitle=f"Found {result.total_count} results in {result.execution_time:.2f}s",
                updated=datetime.now(),
                links=links,
                entries=entries,
                total_results=result.total_count,
                items_per_page=limit,
                start_index=offset + 1
            )
            
            return feed.to_xml()
            
        except Exception as e:
            logger.error(f"Error generating search results: {e}")
            # Return empty feed on error
            feed = OPDSFeed(
                id=self._get_feed_id("search-error"),
                title=f"Search Results for '{query}'",
                subtitle="Search failed",
                updated=datetime.now(),
                links=self._get_acquisition_links(f"/opds/search?query={query}"),
                entries=[]
            )
            return feed.to_xml()
            
    def generate_new_publications(self, limit: int = 20, offset: int = 0) -> str:
        """Generate OPDS feed for new publications."""
        logger.info("Generating OPDS new publications feed")
        
        try:
            # Search for recent publications (this is a simplified approach)
            search_query = SearchQuery(limit=limit, offset=offset)
            result = self.book_index.search(search_query)
            
            entries = [book_to_opds_entry(book, self.base_url) for book in result.books]
            
            # Pagination links
            links = self._get_acquisition_links("/opds/new")
            
            if offset > 0:
                prev_offset = max(0, offset - limit)
                links.append(OPDSLink(
                    rel="previous",
                    href=f"{self.base_url}/opds/new?offset={prev_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition"
                ))
                
            if len(result.books) == limit:  # Might have more
                next_offset = offset + limit
                links.append(OPDSLink(
                    rel="next",
                    href=f"{self.base_url}/opds/new?offset={next_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition"
                ))
                
            feed = OPDSFeed(
                id=self._get_feed_id("new"),
                title="New Publications",
                subtitle="Recently added publications",
                updated=datetime.now(),
                links=links,
                entries=entries,
                total_results=result.total_count,
                items_per_page=limit,
                start_index=offset + 1
            )
            
            return feed.to_xml()
            
        except Exception as e:
            logger.error(f"Error generating new publications feed: {e}")
            raise
            
    def generate_popular_publications(self, limit: int = 20, offset: int = 0) -> str:
        """Generate OPDS feed for popular publications."""
        logger.info("Generating OPDS popular publications feed")
        
        try:
            # For now, this is the same as new publications
            # In a real implementation, you'd sort by download count or popularity
            search_query = SearchQuery(limit=limit, offset=offset)
            result = self.book_index.search(search_query)
            
            entries = [book_to_opds_entry(book, self.base_url) for book in result.books]
            
            # Pagination links
            links = self._get_acquisition_links("/opds/popular")
            
            if offset > 0:
                prev_offset = max(0, offset - limit)
                links.append(OPDSLink(
                    rel="previous",
                    href=f"{self.base_url}/opds/popular?offset={prev_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition"
                ))
                
            if len(result.books) == limit:  # Might have more
                next_offset = offset + limit
                links.append(OPDSLink(
                    rel="next",
                    href=f"{self.base_url}/opds/popular?offset={next_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition"
                ))
                
            feed = OPDSFeed(
                id=self._get_feed_id("popular"),
                title="Popular Publications",
                subtitle="Most popular publications",
                updated=datetime.now(),
                links=links,
                entries=entries,
                total_results=result.total_count,
                items_per_page=limit,
                start_index=offset + 1
            )
            
            return feed.to_xml()
            
        except Exception as e:
            logger.error(f"Error generating popular publications feed: {e}")
            raise
            
    def generate_all_publications(self, limit: int = 20, offset: int = 0) -> str:
        """Generate OPDS feed for all publications."""
        logger.info("Generating OPDS all publications feed")
        
        try:
            search_query = SearchQuery(limit=limit, offset=offset)
            result = self.book_index.search(search_query)
            
            entries = [book_to_opds_entry(book, self.base_url) for book in result.books]
            
            # Pagination links
            links = self._get_acquisition_links("/opds/all")
            
            if offset > 0:
                prev_offset = max(0, offset - limit)
                links.append(OPDSLink(
                    rel="previous",
                    href=f"{self.base_url}/opds/all?offset={prev_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition"
                ))
                
            if len(result.books) == limit:  # Might have more
                next_offset = offset + limit
                links.append(OPDSLink(
                    rel="next",
                    href=f"{self.base_url}/opds/all?offset={next_offset}&limit={limit}",
                    type="application/atom+xml;profile=opds-catalog;kind=acquisition"
                ))
                
            feed = OPDSFeed(
                id=self._get_feed_id("all"),
                title="All Publications",
                subtitle=f"Complete catalog with {result.total_count:,} publications",
                updated=datetime.now(),
                links=links,
                entries=entries,
                total_results=result.total_count,
                items_per_page=limit,
                start_index=offset + 1
            )
            
            return feed.to_xml()
            
        except Exception as e:
            logger.error(f"Error generating all publications feed: {e}")
            raise
            
    def generate_opensearch_description(self) -> str:
        """Generate OpenSearch description document."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
    <ShortName>PyBusta</ShortName>
    <Description>Search the PyBusta digital library catalog</Description>
    <Tags>books ebooks library flibusta</Tags>
    <Contact>admin@example.com</Contact>
    <Url type="application/atom+xml;profile=opds-catalog;kind=acquisition"
         template="{self.base_url}/opds/search?query={{searchTerms}}&amp;offset={{startIndex?}}&amp;limit={{count?}}"/>
    <Url type="text/html"
         template="{self.base_url}/search?title={{searchTerms}}&amp;page={{startPage?}}"/>
    <LongName>PyBusta Digital Library Search</LongName>
    <Image height="64" width="64" type="image/png">{self.base_url}/static/favicon.png</Image>
    <Query role="example" searchTerms="tolstoy" />
    <Developer>PyBusta</Developer>
    <Attribution>PyBusta digital library system</Attribution>
    <SyndicationRight>open</SyndicationRight>
    <AdultContent>false</AdultContent>
    <Language>en-us</Language>
    <Language>ru-ru</Language>
    <OutputEncoding>UTF-8</OutputEncoding>
    <InputEncoding>UTF-8</InputEncoding>
</OpenSearchDescription>'''

    def generate_single_entry(self, book_id: int) -> str:
        """Generate OPDS entry for a single book."""
        logger.info(f"Generating OPDS entry for book {book_id}")
        
        try:
            # Search for the specific book
            search_query = SearchQuery(limit=1)
            result = self.book_index.search(search_query)
            
            # Find the book with matching ID (simplified approach)
            book = None
            for b in result.books:
                if b.id == book_id:
                    book = b
                    break
                    
            if not book:
                raise ValueError(f"Book {book_id} not found")
                
            entry = book_to_opds_entry(book, self.base_url)
            
            # Create a minimal feed with just this entry
            feed = OPDSFeed(
                id=self._get_feed_id(f"book-{book_id}"),
                title=f"Book Entry: {book.title}",
                updated=datetime.now(),
                links=[
                    OPDSLink(
                        rel="self",
                        href=f"{self.base_url}/opds/books/{book_id}",
                        type="application/atom+xml;type=entry;profile=opds-catalog"
                    ),
                    OPDSLink(
                        rel="up",
                        href=f"{self.base_url}/opds",
                        type="application/atom+xml;profile=opds-catalog;kind=navigation"
                    )
                ],
                entries=[entry]
            )
            
            return feed.to_xml()
            
        except Exception as e:
            logger.error(f"Error generating entry for book {book_id}: {e}")
            raise 