# PyBusta

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A modern Python library and CLI utility to access, index, query, and extract files from local Flibusta mirror archives.

## ✨ Features

- **🚀 Fast Search**: Lightning-fast full-text search with SQLite FTS5
- **🔒 Secure**: Modern security practices with input validation and safe file handling
- **📱 Responsive Web UI**: Beautiful, mobile-friendly web interface
- **🛠️ Modern CLI**: Powerful command-line interface with rich output formatting
- **🔌 REST API**: Complete REST API with automatic documentation
- **📊 Statistics**: Detailed analytics about your book collection
- **🎯 Type Safety**: Full type hints and Pydantic data validation
- **🧪 Well Tested**: Comprehensive test suite with high coverage

## 🚀 Quick Start

### Installation

```bash
# Install from source
git clone https://github.com/meschansky/pybusta.git
cd pybusta
pip install -e .

# Or install development dependencies
pip install -e ".[dev]"
```

### Setup

1. **Prepare your data directory:**
   ```bash
   mkdir -p data/fb2.Flibusta.Net
   ```

2. **Copy your Flibusta archive:**
   ```bash
   # Copy or symlink your Flibusta mirror to:
   # data/fb2.Flibusta.Net/flibusta_fb2_local.inpx
   # data/fb2.Flibusta.Net/*.zip (archive files)
   ```

3. **Create the search index:**
   ```bash
   pybusta index
   ```

## 📖 Usage

### Command Line Interface

```bash
# Search for books
pybusta search --title "example book" --author "example author"

# Search with filters
pybusta search --title "python" --language en --format epub --limit 50

# Extract a book by ID
pybusta extract 12345

# View statistics
pybusta stats

# Get help
pybusta --help
```

#### Search Examples

```bash
# Search by title
pybusta search --title "война и мир"

# Search by author
pybusta search --author "толстой"

# Combined search with filters
pybusta search --title "python" --author "lutz" --language en --format pdf

# Output as JSON
pybusta search --title "python" --output json

# Output as CSV
pybusta search --title "python" --output csv > results.csv
```

### Web Interface

```bash
# Start the web server
pybusta-web

# Or with custom settings
python -m pybusta.web.main
```

Then open http://localhost:8080 in your browser.

### Python API

```python
from pybusta import BookIndex, SearchQuery

# Initialize the index
book_index = BookIndex()

# Search for books
query = SearchQuery(
    title="python programming",
    author="lutz",
    language="en",
    limit=10
)
results = book_index.search(query)

# Print results
for book in results.books:
    print(f"{book.id}: {book.title} by {book.author}")

# Extract a book
extraction_result = book_index.extract_book(12345)
if extraction_result.success:
    print(f"Book extracted to: {extraction_result.file_path}")

# Get statistics
stats = book_index.get_stats()
print(f"Total books: {stats.total_books:,}")
```

## 🌐 Web Interface

The modern web interface provides:

- **Search Form**: Intuitive search with multiple filters
- **Results Table**: Sortable, paginated results with download links
- **Statistics Dashboard**: Visual charts and detailed analytics
- **Responsive Design**: Works perfectly on desktop and mobile
- **REST API**: Complete API with Swagger documentation at `/api/docs`

### API Endpoints

- `GET /api/search` - Search for books
- `POST /api/extract/{book_id}` - Extract a book
- `GET /api/download/{book_id}` - Download an extracted book
- `GET /api/stats` - Get index statistics
- `GET /api/docs` - API documentation

## 🔧 Configuration

### Environment Variables

```bash
# Data directory (default: ./data)
export PYBUSTA_DATA_DIR="/path/to/your/data"

# Database path (default: data/db)
export PYBUSTA_DB_PATH="/path/to/database"

# Extraction path (default: data/books)
export PYBUSTA_EXTRACT_PATH="/path/to/extracted/books"
```

### Custom Configuration

```python
from pybusta.core.models import DatabaseConfig
from pybusta import BookIndex

config = DatabaseConfig(
    data_dir=Path("/custom/data"),
    db_path=Path("/custom/db"),
    extract_path=Path("/custom/books")
)

book_index = BookIndex(config)
```

## 🧪 Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/meschansky/pybusta.git
cd pybusta

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pybusta --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black src tests

# Sort imports
isort src tests

# Type checking
mypy src

# Linting
flake8 src tests
```

### Running the Web Server in Development

```bash
# With auto-reload
uvicorn pybusta.web.main:app --reload --host 0.0.0.0 --port 8080
```

## 📊 Performance

PyBusta 2.0 includes significant performance improvements:

- **SQLite FTS5**: Full-text search is 10x faster than the original implementation
- **Batch Processing**: Index creation is 5x faster with batch database operations
- **Connection Pooling**: Improved database connection management
- **Optimized Queries**: Better query planning and indexing strategies

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Format your code (`black src tests`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## 📝 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Original PyBusta project and contributors
- [FastAPI](https://fastapi.tiangolo.com/) for the modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for the database ORM
- [Click](https://click.palletsprojects.com/) for the CLI framework

## 📞 Support

- **Documentation**: [GitHub Wiki](https://github.com/meschansky/pybusta/wiki)
- **Issues**: [GitHub Issues](https://github.com/meschansky/pybusta/issues)
- **Discussions**: [GitHub Discussions](https://github.com/meschansky/pybusta/discussions)

---

**PyBusta 2.0** - Modern, fast, and user-friendly book archive management.
