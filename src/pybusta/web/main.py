"""
Modern FastAPI web application for PyBusta.
"""

import logging
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..core.book_index import BookIndex, IndexNotFoundError
from ..core.models import (
    Book, DatabaseConfig, ExtractionResult, 
    IndexStats, SearchQuery, SearchResult
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="PyBusta",
    description="Modern web interface for accessing Flibusta book archives",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Global configuration
config = DatabaseConfig()
book_index: Optional[BookIndex] = None

# Templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_book_index() -> BookIndex:
    """Dependency to get BookIndex instance."""
    global book_index
    if book_index is None:
        try:
            book_index = BookIndex(config)
        except IndexNotFoundError as e:
            raise HTTPException(status_code=503, detail=str(e))
    return book_index


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    logger.info("Starting PyBusta web application")
    try:
        global book_index
        book_index = BookIndex(config)
        logger.info("BookIndex initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize BookIndex: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    logger.info("Shutting down PyBusta web application")
    if book_index:
        book_index.close()


# API Routes

@app.get("/api/search", response_model=SearchResult)
async def api_search(
    title: Optional[str] = Query(None, description="Search by title"),
    author: Optional[str] = Query(None, description="Search by author"),
    language: Optional[str] = Query(None, description="Filter by language"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    format: Optional[str] = Query(None, description="Filter by format"),
    limit: int = Query(20, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    index: BookIndex = Depends(get_book_index)
) -> SearchResult:
    """Search for books via API."""
    if not any([title, author, genre]):
        raise HTTPException(
            status_code=400, 
            detail="At least one search term (title, author, or genre) must be provided"
        )
    
    try:
        query = SearchQuery(
            title=title,
            author=author,
            language=language,
            genre=genre,
            format=format,
            limit=limit,
            offset=offset
        )
        return index.search(query)
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@app.get("/api/books/{book_id}", response_model=Book)
async def api_get_book(
    book_id: int,
    index: BookIndex = Depends(get_book_index)
) -> Book:
    """Get book details by ID."""
    try:
        query = SearchQuery(limit=1)
        # Search by ID (we'll need to modify search to support ID search)
        result = index.search(query)
        
        # For now, let's extract and return basic info
        # This is a simplified implementation
        extraction_result = index.extract_book(book_id)
        if not extraction_result.success:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Return a basic book object (this would need proper implementation)
        raise HTTPException(status_code=501, detail="Not implemented yet")
        
    except Exception as e:
        logger.error(f"Get book error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get book")


@app.post("/api/extract/{book_id}", response_model=ExtractionResult)
async def api_extract_book(
    book_id: int,
    index: BookIndex = Depends(get_book_index)
) -> ExtractionResult:
    """Extract a book by ID."""
    try:
        result = index.extract_book(book_id)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error_message)
        return result
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        raise HTTPException(status_code=500, detail="Extraction failed")


@app.get("/api/download/{book_id}")
async def api_download_book(
    book_id: int,
    index: BookIndex = Depends(get_book_index)
):
    """Download an extracted book."""
    try:
        result = index.extract_book(book_id)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error_message)
        
        if not result.file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=result.file_path,
            filename=result.extracted_filename,
            media_type='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


@app.get("/api/stats", response_model=IndexStats)
async def api_get_stats(
    index: BookIndex = Depends(get_book_index)
) -> IndexStats:
    """Get index statistics."""
    try:
        return index.get_stats()
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# Web Interface Routes

@app.get("/", response_class=HTMLResponse)
async def web_home(request: Request):
    """Home page with search form."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def web_search(
    request: Request,
    title: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    format: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    index: BookIndex = Depends(get_book_index)
):
    """Search results page."""
    try:
        limit = 20
        offset = (page - 1) * limit
        
        if any([title, author, genre]):
            query = SearchQuery(
                title=title,
                author=author,
                language=language,
                genre=genre,
                format=format,
                limit=limit,
                offset=offset
            )
            result = index.search(query)
        else:
            result = SearchResult(
                books=[],
                total_count=0,
                query=SearchQuery(),
                execution_time=0.0
            )
        
        # Calculate pagination
        total_pages = (result.total_count + limit - 1) // limit
        
        return templates.TemplateResponse("search_results.html", {
            "request": request,
            "result": result,
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1 if page < total_pages else None
        })
        
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Search failed. Please try again."
        })


@app.get("/stats", response_class=HTMLResponse)
async def web_stats(
    request: Request,
    index: BookIndex = Depends(get_book_index)
):
    """Statistics page."""
    try:
        stats = index.get_stats()
        return templates.TemplateResponse("stats.html", {
            "request": request,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Web stats error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load statistics."
        })


@app.get("/extract/{book_id}")
async def web_extract_book(
    book_id: int,
    index: BookIndex = Depends(get_book_index)
):
    """Extract and download a book."""
    try:
        result = index.extract_book(book_id)
        if not result.success:
            raise HTTPException(status_code=404, detail=result.error_message)
        
        return FileResponse(
            path=result.file_path,
            filename=result.extracted_filename,
            media_type='application/octet-stream'
        )
    except Exception as e:
        logger.error(f"Web extract error: {e}")
        raise HTTPException(status_code=500, detail="Extraction failed")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


def main():
    """Run the web application."""
    uvicorn.run(
        "pybusta.web.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main() 