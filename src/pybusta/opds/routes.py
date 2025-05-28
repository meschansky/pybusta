"""
FastAPI routes for OPDS endpoints.

This module provides the HTTP endpoints for the OPDS catalog,
following the OPDS 1.2 specification.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import Response

from ..core.book_index import BookIndex
from .feeds import OPDSFeedGenerator

logger = logging.getLogger(__name__)


def create_opds_router(get_book_index_func) -> APIRouter:
    """Create OPDS router with dependency injection."""
    
    router = APIRouter(prefix="/opds", tags=["opds"])
    
    def get_opds_generator(
        request: Request,
        index: BookIndex = Depends(get_book_index_func)
    ) -> OPDSFeedGenerator:
        """Get OPDS feed generator with base URL."""
        # Construct base URL from request
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        return OPDSFeedGenerator(index, base_url)
    
    @router.get(
        "/",
        summary="OPDS Catalog Root",
        description="The main entry point for the OPDS catalog, providing navigation to different sections.",
        responses={
            200: {
                "description": "OPDS navigation feed",
                "content": {"application/atom+xml;profile=opds-catalog;kind=navigation": {}}
            }
        }
    )
    async def opds_root(generator: OPDSFeedGenerator = Depends(get_opds_generator)):
        """Get the OPDS catalog root feed."""
        try:
            feed_xml = generator.generate_root_feed()
            return Response(
                content=feed_xml,
                media_type="application/atom+xml;profile=opds-catalog;kind=navigation",
                headers={
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "X-OPDS-Version": "1.2"
                }
            )
        except Exception as e:
            logger.error(f"Error generating OPDS root feed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate OPDS catalog")
    
    @router.get(
        "/search",
        summary="Search Publications",
        description="Search for publications in the catalog using keywords.",
        responses={
            200: {
                "description": "OPDS acquisition feed with search results",
                "content": {"application/atom+xml;profile=opds-catalog;kind=acquisition": {}}
            },
            400: {"description": "Missing or invalid search query"}
        }
    )
    async def opds_search(
        query: str = Query(..., description="Search query (title, author, or keywords)"),
        limit: int = Query(20, ge=1, le=100, description="Maximum number of results per page"),
        offset: int = Query(0, ge=0, description="Number of results to skip (for pagination)"),
        generator: OPDSFeedGenerator = Depends(get_opds_generator)
    ):
        """Search for publications."""
        if not query.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
            
        try:
            feed_xml = generator.generate_search_results(query.strip(), limit, offset)
            return Response(
                content=feed_xml,
                media_type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                headers={
                    "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
                    "X-OPDS-Version": "1.2"
                }
            )
        except Exception as e:
            logger.error(f"Error generating OPDS search results: {e}")
            raise HTTPException(status_code=500, detail="Search failed")
    
    @router.get(
        "/new",
        summary="New Publications",
        description="Recently added publications to the catalog.",
        responses={
            200: {
                "description": "OPDS acquisition feed with new publications",
                "content": {"application/atom+xml;profile=opds-catalog;kind=acquisition": {}}
            }
        }
    )
    async def opds_new(
        limit: int = Query(20, ge=1, le=100, description="Maximum number of results per page"),
        offset: int = Query(0, ge=0, description="Number of results to skip (for pagination)"),
        generator: OPDSFeedGenerator = Depends(get_opds_generator)
    ):
        """Get new publications feed."""
        try:
            feed_xml = generator.generate_new_publications(limit, offset)
            return Response(
                content=feed_xml,
                media_type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                headers={
                    "Cache-Control": "public, max-age=1800",  # Cache for 30 minutes
                    "X-OPDS-Version": "1.2"
                }
            )
        except Exception as e:
            logger.error(f"Error generating new publications feed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate new publications feed")
    
    @router.get(
        "/popular",
        summary="Popular Publications",
        description="Most popular and frequently downloaded publications.",
        responses={
            200: {
                "description": "OPDS acquisition feed with popular publications",
                "content": {"application/atom+xml;profile=opds-catalog;kind=acquisition": {}}
            }
        }
    )
    async def opds_popular(
        limit: int = Query(20, ge=1, le=100, description="Maximum number of results per page"),
        offset: int = Query(0, ge=0, description="Number of results to skip (for pagination)"),
        generator: OPDSFeedGenerator = Depends(get_opds_generator)
    ):
        """Get popular publications feed."""
        try:
            feed_xml = generator.generate_popular_publications(limit, offset)
            return Response(
                content=feed_xml,
                media_type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                headers={
                    "Cache-Control": "public, max-age=1800",  # Cache for 30 minutes
                    "X-OPDS-Version": "1.2"
                }
            )
        except Exception as e:
            logger.error(f"Error generating popular publications feed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate popular publications feed")
    
    @router.get(
        "/all",
        summary="All Publications",
        description="Complete catalog of all available publications.",
        responses={
            200: {
                "description": "OPDS acquisition feed with all publications",
                "content": {"application/atom+xml;profile=opds-catalog;kind=acquisition": {}}
            }
        }
    )
    async def opds_all(
        limit: int = Query(20, ge=1, le=100, description="Maximum number of results per page"),
        offset: int = Query(0, ge=0, description="Number of results to skip (for pagination)"),
        generator: OPDSFeedGenerator = Depends(get_opds_generator)
    ):
        """Get all publications feed."""
        try:
            feed_xml = generator.generate_all_publications(limit, offset)
            return Response(
                content=feed_xml,
                media_type="application/atom+xml;profile=opds-catalog;kind=acquisition",
                headers={
                    "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                    "X-OPDS-Version": "1.2"
                }
            )
        except Exception as e:
            logger.error(f"Error generating all publications feed: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate all publications feed")
    
    @router.get(
        "/books/{book_id}",
        summary="Single Book Entry",
        description="Complete OPDS entry for a specific book.",
        responses={
            200: {
                "description": "OPDS entry document for the book",
                "content": {"application/atom+xml;type=entry;profile=opds-catalog": {}}
            },
            404: {"description": "Book not found"}
        }
    )
    async def opds_book_entry(
        book_id: int,
        generator: OPDSFeedGenerator = Depends(get_opds_generator)
    ):
        """Get OPDS entry for a specific book."""
        try:
            feed_xml = generator.generate_single_entry(book_id)
            return Response(
                content=feed_xml,
                media_type="application/atom+xml;type=entry;profile=opds-catalog",
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                    "X-OPDS-Version": "1.2"
                }
            )
        except ValueError as e:
            # Book not found
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error generating book entry for {book_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate book entry")
    
    @router.get(
        "/opensearch.xml",
        summary="OpenSearch Description",
        description="OpenSearch description document for search functionality.",
        responses={
            200: {
                "description": "OpenSearch description document",
                "content": {"application/opensearchdescription+xml": {}}
            }
        }
    )
    async def opensearch_description(
        generator: OPDSFeedGenerator = Depends(get_opds_generator)
    ):
        """Get OpenSearch description document."""
        try:
            opensearch_xml = generator.generate_opensearch_description()
            return Response(
                content=opensearch_xml,
                media_type="application/opensearchdescription+xml",
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                }
            )
        except Exception as e:
            logger.error(f"Error generating OpenSearch description: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate OpenSearch description")
    
    # Placeholder routes for future implementation
    @router.get(
        "/authors",
        summary="Browse by Author",
        description="Browse publications organized by author (not yet implemented).",
        responses={
            501: {"description": "Not implemented yet"}
        }
    )
    async def opds_authors():
        """Browse by author (placeholder)."""
        raise HTTPException(status_code=501, detail="Author browsing not yet implemented")
    
    @router.get(
        "/genres",
        summary="Browse by Genre",
        description="Browse publications organized by genre (not yet implemented).",
        responses={
            501: {"description": "Not implemented yet"}
        }
    )
    async def opds_genres():
        """Browse by genre (placeholder)."""
        raise HTTPException(status_code=501, detail="Genre browsing not yet implemented")
    
    return router 