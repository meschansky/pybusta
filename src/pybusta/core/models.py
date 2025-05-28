"""
Data models for PyBusta using Pydantic for validation and serialization.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator, ConfigDict, field_validator


class BookFormat(str, Enum):
    """Supported book formats."""
    FB2 = "fb2"
    EPUB = "epub"
    PDF = "pdf"
    TXT = "txt"
    DOC = "doc"
    DOCX = "docx"
    RTF = "rtf"


class Language(str, Enum):
    """Supported languages."""
    RU = "ru"
    EN = "en"
    DE = "de"
    FR = "fr"
    ES = "es"
    IT = "it"
    UK = "uk"
    BE = "be"


class Book(BaseModel):
    """Model representing a book in the database."""
    
    id: Optional[int] = None
    author: str
    title: str
    extension: str
    filesize: int
    language: Optional[str] = None
    year: Optional[int] = None
    pages: Optional[int] = None
    identifier: Optional[str] = None
    md5: Optional[str] = None
    commentary: Optional[str] = None
    generic: Optional[str] = None
    visible: Optional[str] = None
    locator: Optional[str] = None
    local: Optional[int] = None
    added: Optional[datetime] = None
    lastmodified: Optional[datetime] = None
    coverurl: Optional[str] = None
    tags: Optional[str] = None
    identifierwodash: Optional[str] = None
    library: Optional[str] = None
    publisher: Optional[str] = None
    city: Optional[str] = None
    edition: Optional[str] = None
    dpi: Optional[int] = None
    color: Optional[str] = None
    cleaned: Optional[str] = None
    orientation: Optional[str] = None
    paginated: Optional[str] = None
    scanned: Optional[str] = None
    bookmarked: Optional[str] = None
    searchable: Optional[str] = None
    filesize_reported: Optional[int] = None
    filename: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            Path: str
        }
    )
    
    @field_validator('author', 'title')
    @classmethod
    def clean_text_fields(cls, v: str) -> str:
        """Clean and normalize text fields."""
        if not v:
            return v
        # Remove extra whitespace and normalize
        return " ".join(v.split())


class SearchQuery(BaseModel):
    """Model for search queries."""
    
    title: Optional[str] = None
    author: Optional[str] = None
    genre: Optional[str] = None
    format: Optional[str] = None
    language: Optional[str] = None
    limit: int = 50
    offset: int = 0
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    @field_validator('title', 'author', 'genre')
    @classmethod
    def clean_search_terms(cls, v: Optional[str]) -> Optional[str]:
        """Clean search terms by removing extra whitespace."""
        if not v:
            return v
        return " ".join(v.split())
    
    def has_search_terms(self) -> bool:
        """Check if the query has any search terms."""
        return any([
            self.title,
            self.author,
            self.genre,
            self.format,
            self.language
        ])


class SearchResult(BaseModel):
    """Model for search results."""
    
    books: List[Book] = Field(default_factory=list, description="List of found books")
    total_count: int = Field(0, ge=0, description="Total number of matching books")
    query: SearchQuery = Field(..., description="Original search query")
    execution_time: float = Field(0.0, ge=0, description="Query execution time in seconds")


class ExtractionResult(BaseModel):
    """Model for book extraction results."""
    
    book_id: int = Field(..., description="ID of extracted book")
    original_filename: str = Field(..., description="Original filename in archive")
    extracted_filename: str = Field(..., description="Filename after extraction")
    file_path: Path = Field(..., description="Full path to extracted file")
    file_size: int = Field(..., ge=0, description="Size of extracted file")
    success: bool = Field(..., description="Whether extraction was successful")
    error_message: Optional[str] = Field(None, description="Error message if extraction failed")


class DatabaseConfig(BaseModel):
    """Configuration for database connections."""
    
    data_dir: Path = Field(Path("data"), description="Base data directory")
    db_path: Path = Field(Path("data/db"), description="Database directory")
    extract_path: Path = Field(Path("data/books"), description="Book extraction directory")
    tmp_path: Path = Field(Path("/tmp/pybusta"), description="Temporary files directory")
    index_file: Optional[Path] = Field(None, description="Path to Flibusta index file")
    
    @field_validator('data_dir', 'db_path', 'extract_path', 'tmp_path')
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure directories exist."""
        if v:
            v.mkdir(parents=True, exist_ok=True)
        return v
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create configuration from environment variables."""
        import os
        
        # Get base data directory from environment or default
        data_dir = Path(os.getenv('PYBUSTA_DATA_DIR', 'data'))
        
        # Build other paths relative to data_dir unless explicitly set
        config_data = {
            'data_dir': data_dir,
            'db_path': Path(os.getenv('PYBUSTA_DB_PATH', str(data_dir / 'db'))),
            'extract_path': Path(os.getenv('PYBUSTA_EXTRACT_PATH', str(data_dir / 'books'))),
            'tmp_path': Path(os.getenv('PYBUSTA_TMP_PATH', '/tmp/pybusta')),
        }
        
        # Handle index file path
        index_file_env = os.getenv('PYBUSTA_INDEX_FILE')
        if index_file_env:
            config_data['index_file'] = Path(index_file_env)
        
        return cls(**config_data)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Set index_file default after data_dir is processed
        if self.index_file is None:
            self.index_file = self.data_dir / "fb2.Flibusta.Net" / "flibusta_fb2_local.inpx"


class IndexStats(BaseModel):
    """Statistics about the book index."""
    
    total_books: int = Field(0, ge=0, description="Total number of books in index")
    total_authors: int = Field(0, ge=0, description="Total number of unique authors")
    total_genres: int = Field(0, ge=0, description="Total number of unique genres")
    languages: Dict[str, int] = Field(default_factory=dict, description="Books per language")
    formats: Dict[str, int] = Field(default_factory=dict, description="Books per format")
    index_size: int = Field(0, ge=0, description="Database size in bytes")
    last_updated: Optional[datetime] = Field(None, description="Last index update time")
    index_file_checksum: Optional[str] = Field(None, description="Checksum of source index file")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat() if v else None}
    ) 