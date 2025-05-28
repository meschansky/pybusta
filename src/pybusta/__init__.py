"""
PyBusta - A modern Python library for accessing Flibusta book archives.

This package provides tools to index, search, and extract books from
local Flibusta mirror archives.
"""

__version__ = "2.0.0"
__author__ = "PyBusta Contributors"

from .core.book_index import BookIndex
from .core.models import Book, SearchQuery, SearchResult

__all__ = ["BookIndex", "Book", "SearchQuery", "SearchResult"] 