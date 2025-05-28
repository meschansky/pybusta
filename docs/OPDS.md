# OPDS Support in PyBusta

PyBusta now includes comprehensive support for OPDS (Open Publication Distribution System), allowing e-book readers and library applications to browse and download books from the Flibusta archive.

## What is OPDS?

OPDS is an open standard catalog format for distributing electronic publications. It's based on Atom feeds and allows e-book readers like:

- **Calibre** - Popular e-book management software
- **FBReader** - Cross-platform e-book reader
- **KyBook** - iOS e-book reader
- **Moon+ Reader** - Android e-book reader
- **Aldiko** - Android e-book reader
- And many others

to discover, browse, and download books from digital libraries.

## PyBusta OPDS Endpoints

### Root Catalog
- **URL**: `/opds/`
- **Description**: Main entry point providing navigation to different catalog sections
- **Content-Type**: `application/atom+xml;profile=opds-catalog;kind=navigation`

### Search
- **URL**: `/opds/search?query={searchTerms}`
- **Description**: Search for books by title, author, or keywords
- **Parameters**:
  - `query` (required): Search query string
  - `limit` (optional): Results per page (1-100, default: 20)
  - `offset` (optional): Pagination offset (default: 0)
- **Content-Type**: `application/atom+xml;profile=opds-catalog;kind=acquisition`

### New Publications
- **URL**: `/opds/new`
- **Description**: Recently added publications
- **Parameters**: `limit`, `offset` (same as search)
- **Content-Type**: `application/atom+xml;profile=opds-catalog;kind=acquisition`

### Popular Publications
- **URL**: `/opds/popular`
- **Description**: Most popular publications
- **Parameters**: `limit`, `offset` (same as search)
- **Content-Type**: `application/atom+xml;profile=opds-catalog;kind=acquisition`

### All Publications
- **URL**: `/opds/all`
- **Description**: Complete catalog with all publications
- **Parameters**: `limit`, `offset` (same as search)
- **Content-Type**: `application/atom+xml;profile=opds-catalog;kind=acquisition`

### Single Book Entry
- **URL**: `/opds/books/{book_id}`
- **Description**: Complete OPDS entry for a specific book
- **Content-Type**: `application/atom+xml;type=entry;profile=opds-catalog`

### OpenSearch Description
- **URL**: `/opds/opensearch.xml`
- **Description**: OpenSearch description document for search functionality
- **Content-Type**: `application/opensearchdescription+xml`

## Setting Up OPDS in E-Book Readers

### Calibre

1. Open Calibre
2. Go to "Get books" → "Get books from web"
3. Add a new news source
4. Enter PyBusta OPDS URL: `http://your-server:port/opds/`
5. Calibre will automatically discover the catalog structure

### FBReader

1. Open FBReader
2. Go to Network Library
3. Add new catalog
4. Enter: `http://your-server:port/opds/`
5. FBReader will load the catalog for browsing

### Mobile E-Readers

Most mobile e-readers support OPDS catalogs:

1. Look for "Add Catalog", "Network Library", or "OPDS" in settings
2. Enter the catalog URL: `http://your-server:port/opds/`
3. The reader will connect and allow browsing

## OPDS Features in PyBusta

### Navigation Structure
- **Root catalog** with organized sections
- **Search functionality** with OpenSearch support
- **Pagination** for large result sets
- **Proper MIME types** for different content

### Book Metadata
Each book entry includes:
- Title and authors
- Genre and language information
- Publication year
- Summary/description
- Cover image links
- Download links

### Standards Compliance
- **OPDS 1.2** specification compliant
- **Atom feed** format with proper namespaces
- **OpenSearch** integration for search
- **Dublin Core** metadata elements
- **HTTP caching** headers for performance

### Security & Performance
- **Proper CORS** headers for cross-origin access
- **HTTP caching** with appropriate cache lifetimes
- **Error handling** with graceful degradation
- **Rate limiting** ready (configure in web server)

## Troubleshooting

### Common Issues

1. **Catalog not loading in reader**
   - Check that PyBusta is accessible from the reader's network
   - Verify the URL is correct (include `/opds/` at the end)
   - Check firewall settings

2. **Search not working**
   - Ensure the OpenSearch description is accessible at `/opds/opensearch.xml`
   - Some readers may need time to cache the search template

3. **Downloads failing**
   - Verify that the underlying book extraction and download APIs work
   - Check that the book files exist in the Flibusta archive

4. **Performance issues**
   - Consider enabling caching in your web server (nginx, Apache)
   - Adjust pagination limits in large catalogs
   - Monitor database performance for search queries

### Testing OPDS Feeds

You can test OPDS feeds manually:

```bash
# Test root catalog
curl -H "Accept: application/atom+xml" http://localhost:8000/opds/

# Test search
curl -H "Accept: application/atom+xml" "http://localhost:8000/opds/search?query=tolstoy"

# Test OpenSearch description
curl http://localhost:8000/opds/opensearch.xml
```

## Future Enhancements

Planned improvements for OPDS support:

- **Author browsing** (`/opds/authors`) - Browse books by author
- **Genre browsing** (`/opds/genres`) - Browse books by genre/category  
- **Language filtering** - Filter content by language
- **Format-specific feeds** - Separate feeds for different file formats
- **Faceted search** - Advanced search with multiple criteria
- **Authentication** - Support for password-protected catalogs
- **Acquisition profiles** - Different download formats per book

## Examples

### Adding PyBusta to Calibre

1. In Calibre, click "Get books" → "Get books from web"
2. Click "Add custom news source"
3. Fill in:
   - Title: "PyBusta Library"
   - URL: `http://your-server:8000/opds/`
   - RSS: Leave unchecked
4. Click "Add source"
5. Your PyBusta catalog will appear in the news sources

### Mobile Reader Setup (KyBook example)

1. Open KyBook app
2. Go to "Catalogs" tab
3. Tap "+" to add new catalog
4. Enter:
   - Name: "PyBusta"
   - URL: `http://your-server:8000/opds/`
5. Tap "Add"
6. The catalog will appear and you can browse books

## Technical Details

PyBusta's OPDS implementation follows modern web standards:

- **XML namespace declarations** for proper parsing
- **Rel attribute standards** for link relationships
- **Content negotiation** via Accept headers
- **Proper HTTP status codes** for error conditions
- **UTF-8 encoding** for international character support

The implementation is designed to work with the widest range of OPDS clients while maintaining performance and security. 