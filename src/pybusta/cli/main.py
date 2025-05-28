"""
Modern command-line interface for PyBusta using Click.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from ..core.book_index import BookIndex, IndexNotFoundError
from ..core.models import DatabaseConfig, SearchQuery


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--data-dir', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
              help='Path to data directory containing Flibusta archives')
@click.pass_context
def main(ctx: click.Context, verbose: bool, data_dir: Optional[Path]) -> None:
    """
    PyBusta - Modern tool for accessing Flibusta book archives.
    
    This tool allows you to index, search, and extract books from local
    Flibusta mirror archives.
    """
    setup_logging(verbose)
    
    # Store configuration in context
    if data_dir:
        # Use explicit data directory
        config = DatabaseConfig()
        config.data_dir = data_dir
        config.db_path = data_dir / "db"
        config.extract_path = data_dir / "books"
        config.index_file = data_dir / "fb2.Flibusta.Net" / "flibusta_fb2_local.inpx"
    else:
        # Use environment configuration or defaults
        config = DatabaseConfig.from_env()
    
    ctx.ensure_object(dict)
    ctx.obj['config'] = config


@main.command()
@click.option('--title', '-t', help='Search by book title (case insensitive)')
@click.option('--author', '-a', help='Search by author name (case insensitive)')
@click.option('--language', '-l', type=click.Choice(['ru', 'en', 'de', 'fr', 'es', 'it', 'uk', 'be']),
              help='Filter by language')
@click.option('--genre', '-g', help='Filter by genre')
@click.option('--format', '-f', type=click.Choice(['fb2', 'epub', 'pdf', 'txt', 'doc', 'docx', 'rtf']),
              help='Filter by file format')
@click.option('--limit', '-n', default=20, type=click.IntRange(1, 1000),
              help='Maximum number of results to show (default: 20)')
@click.option('--offset', default=0, type=click.IntRange(0),
              help='Number of results to skip (default: 0)')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'csv']), default='table',
              help='Output format (default: table)')
@click.pass_context
def search(ctx: click.Context, title: Optional[str], author: Optional[str], 
           language: Optional[str], genre: Optional[str], format: Optional[str],
           limit: int, offset: int, output: str) -> None:
    """Search for books in the index."""
    config = ctx.obj['config']
    
    # Validate that at least one search term is provided
    if not any([title, author, genre]):
        click.echo("Error: At least one search term (title, author, or genre) must be provided.", err=True)
        sys.exit(1)
    
    try:
        book_index = BookIndex(config)
        
        # Build search query
        query = SearchQuery(
            title=title,
            author=author,
            language=language,
            genre=genre,
            format=format,
            limit=limit,
            offset=offset
        )
        
        # Perform search
        result = book_index.search(query)
        
        # Display results
        if output == 'json':
            import json
            click.echo(json.dumps(result.model_dump(), indent=2, default=str))
        elif output == 'csv':
            _output_csv(result)
        else:
            _output_table(result)
            
    except IndexNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Make sure the Flibusta index file exists in the data directory.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
    finally:
        if 'book_index' in locals():
            book_index.close()


@main.command()
@click.argument('book_id', type=int)
@click.option('--output-dir', '-o', type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
              help='Directory to extract the book to (default: data/books)')
@click.pass_context
def extract(ctx: click.Context, book_id: int, output_dir: Optional[Path]) -> None:
    """Extract a book by its ID."""
    config = ctx.obj['config']
    
    if output_dir:
        config.extract_path = output_dir
    
    try:
        book_index = BookIndex(config)
        
        # Extract the book
        result = book_index.extract_book(book_id)
        
        if result.success:
            click.echo(f"✓ Successfully extracted book {book_id}")
            click.echo(f"  File: {result.extracted_filename}")
            click.echo(f"  Path: {result.file_path}")
            click.echo(f"  Size: {result.file_size:,} bytes")
        else:
            click.echo(f"✗ Failed to extract book {book_id}: {result.error_message}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
    finally:
        if 'book_index' in locals():
            book_index.close()


@main.command()
@click.option('--force', '-f', is_flag=True, help='Force rebuild even if index is up to date')
@click.pass_context
def index(ctx: click.Context, force: bool) -> None:
    """Create or rebuild the book index."""
    config = ctx.obj['config']
    
    try:
        if force:
            # Force rebuild by temporarily removing the database
            import tempfile
            import shutil
            backup_dir = None
            if config.db_path.exists():
                backup_dir = Path(tempfile.mkdtemp())
                shutil.move(str(config.db_path), str(backup_dir / "db_backup"))
        
        book_index = BookIndex(config)
        
        if force and backup_dir:
            # Clean up backup
            shutil.rmtree(backup_dir)
        
        click.echo("✓ Index is ready")
        
        # Show statistics
        stats = book_index.get_stats()
        click.echo(f"  Total books: {stats.total_books:,}")
        click.echo(f"  Total authors: {stats.total_authors:,}")
        click.echo(f"  Total genres: {stats.total_genres:,}")
        click.echo(f"  Database size: {stats.index_size:,} bytes")
        
    except IndexNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("Make sure the Flibusta index file exists in the data directory.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
    finally:
        if 'book_index' in locals():
            book_index.close()


@main.command()
@click.pass_context
def rebuild_search(ctx: click.Context) -> None:
    """Rebuild the full-text search index."""
    config = ctx.obj['config']
    
    try:
        book_index = BookIndex(config)
        
        click.echo("🔄 Rebuilding search index...")
        book_index.rebuild_search_index()
        click.echo("✓ Search index rebuilt successfully")
        
        # Show updated statistics
        stats = book_index.get_stats()
        click.echo(f"  Indexed {stats.total_books:,} books for search")
        
    except Exception as e:
        click.echo(f"Error rebuilding search index: {e}", err=True)
        sys.exit(1)
    finally:
        if 'book_index' in locals():
            book_index.close()


@main.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show statistics about the book index."""
    config = ctx.obj['config']
    
    try:
        book_index = BookIndex(config)
        stats = book_index.get_stats()
        
        click.echo("📊 Index Statistics")
        click.echo("=" * 50)
        click.echo(f"Total books:     {stats.total_books:,}")
        click.echo(f"Total authors:   {stats.total_authors:,}")
        click.echo(f"Total genres:    {stats.total_genres:,}")
        click.echo(f"Database size:   {stats.index_size:,} bytes")
        
        if stats.languages:
            click.echo("\n📚 Books by Language:")
            for lang, count in sorted(stats.languages.items(), key=lambda x: x[1], reverse=True):
                click.echo(f"  {lang}: {count:,}")
        
        if stats.formats:
            click.echo("\n📄 Books by Format:")
            for fmt, count in sorted(stats.formats.items(), key=lambda x: x[1], reverse=True):
                click.echo(f"  {fmt}: {count:,}")
        
        if stats.index_file_checksum:
            click.echo(f"\n🔍 Index checksum: {stats.index_file_checksum}")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        if 'book_index' in locals():
            book_index.close()


@main.command()
@click.option('--host', default='0.0.0.0', help='Host to bind the server to (default: 0.0.0.0)')
@click.option('--port', default=8080, type=int, help='Port to bind the server to (default: 8080)')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.pass_context
def web(ctx: click.Context, host: str, port: int, reload: bool) -> None:
    """Start the web interface server."""
    config = ctx.obj['config']
    
    try:
        import uvicorn
        from ..web.main import app
        
        click.echo(f"🌐 Starting PyBusta web server...")
        click.echo(f"   URL: http://{host}:{port}")
        click.echo(f"   API Documentation: http://{host}:{port}/api/docs")
        click.echo("   Press Ctrl+C to stop")
        
        # Run the web server
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except ImportError:
        click.echo("Error: Web server dependencies not installed.", err=True)
        click.echo("Install with: pip install 'pybusta[web]'", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting web server: {e}", err=True)
        sys.exit(1)


def _output_table(result) -> None:
    """Output search results as a formatted table."""
    if not result.books:
        click.echo("No books found matching your criteria.")
        return
    
    click.echo(f"\n📚 Found {result.total_count:,} books (showing {len(result.books)})")
    click.echo(f"⏱️  Search took {result.execution_time:.3f} seconds")
    click.echo("=" * 100)
    
    # Header
    click.echo(f"{'ID':<8} {'Author':<25} {'Title':<35} {'Lang':<6} {'Format':<8} {'Size':<10}")
    click.echo("-" * 100)
    
    # Books
    for book in result.books:
        author = book.author[:24] + "…" if len(book.author) > 25 else book.author
        title = book.title[:34] + "…" if len(book.title) > 35 else book.title
        size_str = f"{book.filesize:,}" if book.filesize < 1024*1024 else f"{book.filesize/(1024*1024):.1f}MB"
        
        click.echo(f"{book.id:<8} {author:<25} {title:<35} {book.language:<6} {book.extension:<8} {size_str:<10}")
    
    if result.total_count > len(result.books):
        remaining = result.total_count - len(result.books) - result.query.offset
        click.echo(f"\n... and {remaining:,} more results")


def _output_csv(result) -> None:
    """Output search results as CSV."""
    import csv
    import sys
    
    writer = csv.writer(sys.stdout)
    writer.writerow(['ID', 'Author', 'Title', 'Language', 'Format', 'Size'])
    
    for book in result.books:
        writer.writerow([
            book.id, book.author, book.title, 
            book.language or '', book.extension, book.filesize
        ])


if __name__ == '__main__':
    main() 