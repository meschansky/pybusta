"""
OPDS models for XML generation and data structures.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from ..core.models import Book


@dataclass
class OPDSLink:
    """Represents an OPDS link element."""
    
    rel: str
    href: str
    type: str
    title: Optional[str] = None
    length: Optional[int] = None
    price: Optional[str] = None
    currency: Optional[str] = None
    
    def to_xml(self, parent: Element) -> Element:
        """Convert to XML element."""
        link = SubElement(parent, "link")
        link.set("rel", self.rel)
        link.set("href", self.href)
        link.set("type", self.type)
        
        if self.title:
            link.set("title", self.title)
        if self.length:
            link.set("length", str(self.length))
            
        if self.price and self.currency:
            price_elem = SubElement(link, "{http://opds-spec.org/2010/catalog}price")
            price_elem.set("currencycode", self.currency)
            price_elem.text = self.price
            
        return link


@dataclass
class OPDSEntry:
    """Represents an OPDS catalog entry."""
    
    id: str
    title: str
    updated: datetime
    summary: Optional[str] = None
    content: Optional[str] = None
    authors: Optional[List[str]] = None
    language: Optional[str] = None
    issued: Optional[str] = None
    categories: Optional[List[Dict[str, str]]] = None
    links: Optional[List[OPDSLink]] = None
    
    def to_xml(self, parent: Element) -> Element:
        """Convert to XML entry element."""
        entry = SubElement(parent, "entry")
        
        # Required elements
        SubElement(entry, "id").text = self.id
        SubElement(entry, "title").text = self.title
        SubElement(entry, "updated").text = self.updated.isoformat() + "Z"
        
        # Optional elements
        if self.summary:
            summary_elem = SubElement(entry, "summary")
            summary_elem.set("type", "text")
            summary_elem.text = self.summary
            
        if self.content:
            content_elem = SubElement(entry, "content")
            content_elem.set("type", "text")
            content_elem.text = self.content
            
        # Authors
        if self.authors:
            for author in self.authors:
                author_elem = SubElement(entry, "author")
                SubElement(author_elem, "name").text = author
                
        # Dublin Core elements
        if self.language:
            dc_lang = SubElement(entry, "{http://purl.org/dc/terms/}language")
            dc_lang.text = self.language
            
        if self.issued:
            dc_issued = SubElement(entry, "{http://purl.org/dc/terms/}issued")
            dc_issued.text = self.issued
            
        # Categories
        if self.categories:
            for cat in self.categories:
                cat_elem = SubElement(entry, "category")
                for key, value in cat.items():
                    cat_elem.set(key, value)
                    
        # Links
        if self.links:
            for link in self.links:
                link.to_xml(entry)
                
        return entry


@dataclass
class OPDSFeed:
    """Represents an OPDS catalog feed."""
    
    id: str
    title: str
    updated: datetime
    author_name: str = "PyBusta"
    author_uri: str = "https://github.com/meschansky/pybusta"
    subtitle: Optional[str] = None
    icon: Optional[str] = None
    links: Optional[List[OPDSLink]] = None
    entries: Optional[List[OPDSEntry]] = None
    total_results: Optional[int] = None
    items_per_page: Optional[int] = None
    start_index: Optional[int] = None
    
    def to_xml(self) -> str:
        """Convert to XML string."""
        # Create root feed element with namespaces
        feed = Element("feed")
        feed.set("xmlns", "http://www.w3.org/2005/Atom")
        feed.set("xmlns:dc", "http://purl.org/dc/terms/")
        feed.set("xmlns:opds", "http://opds-spec.org/2010/catalog")
        feed.set("xmlns:opensearch", "http://a9.com/-/spec/opensearch/1.1/")
        
        # Required elements
        SubElement(feed, "id").text = self.id
        SubElement(feed, "title").text = self.title
        SubElement(feed, "updated").text = self.updated.isoformat() + "Z"
        
        # Author
        author = SubElement(feed, "author")
        SubElement(author, "name").text = self.author_name
        SubElement(author, "uri").text = self.author_uri
        
        # Optional elements
        if self.subtitle:
            SubElement(feed, "subtitle").text = self.subtitle
            
        if self.icon:
            SubElement(feed, "icon").text = self.icon
            
        # OpenSearch elements
        if self.total_results is not None:
            SubElement(feed, "{http://a9.com/-/spec/opensearch/1.1/}totalResults").text = str(self.total_results)
            
        if self.items_per_page is not None:
            SubElement(feed, "{http://a9.com/-/spec/opensearch/1.1/}itemsPerPage").text = str(self.items_per_page)
            
        if self.start_index is not None:
            SubElement(feed, "{http://a9.com/-/spec/opensearch/1.1/}startIndex").text = str(self.start_index)
            
        # Links
        if self.links:
            for link in self.links:
                link.to_xml(feed)
                
        # Entries
        if self.entries:
            for entry in self.entries:
                entry.to_xml(feed)
                
        # Pretty print XML
        rough_string = tostring(feed, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")[:-1]  # Remove trailing newline


def book_to_opds_entry(book: Book, base_url: str) -> OPDSEntry:
    """Convert a PyBusta Book to an OPDS entry."""
    # Create unique ID
    entry_id = f"urn:uuid:book-{book.id}"
    
    # Format authors
    authors = []
    if hasattr(book, 'author') and book.author:
        authors = book.author.split(',') if isinstance(book.author, str) else [str(book.author)]
    
    # Format categories based on genre
    categories = []
    if hasattr(book, 'generic') and book.generic:
        categories = [{
            "term": book.generic,
            "label": book.generic,
            "scheme": "http://www.bisg.org/standards/bisac_subject/index.html"
        }]
    
    # Create acquisition links
    links = []
    
    # Add cover image if available
    links.append(OPDSLink(
        rel="http://opds-spec.org/image/thumbnail",
        href=f"{base_url}/api/books/{book.id}/cover",
        type="image/jpeg"
    ))
    
    # Add acquisition link
    links.append(OPDSLink(
        rel="http://opds-spec.org/acquisition/open-access",
        href=f"{base_url}/api/download/{book.id}",
        type="application/octet-stream",
        title=f"Download {book.title}"
    ))
    
    # Add link to complete entry
    links.append(OPDSLink(
        rel="alternate",
        href=f"{base_url}/opds/books/{book.id}",
        type="application/atom+xml;type=entry;profile=opds-catalog",
        title=f"Complete catalog entry for {book.title}"
    ))
    
    return OPDSEntry(
        id=entry_id,
        title=book.title,
        updated=datetime.now(),
        summary=getattr(book, 'commentary', None) or f"Book by {', '.join(authors) if authors else 'Unknown Author'}",
        authors=authors,
        language=getattr(book, 'language', 'ru'),  # Default to Russian for Flibusta
        issued=str(getattr(book, 'year', None)) if getattr(book, 'year', None) else None,
        categories=categories,
        links=links
    ) 