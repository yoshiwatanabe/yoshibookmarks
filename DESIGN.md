# Detailed System Design - YoshiBookmark

## 1. System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Clients                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Web Browser │  │   CLI Tool   │  │ IDE/Editor   │      │
│  │  (HTML/JS)   │  │   (Python)   │  │ Integration  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │ HTTP REST API
          ┌──────────────────▼──────────────────┐
          │      FastAPI Application            │
          │  ┌────────────────────────────────┐ │
          │  │      API Routes Layer          │ │
          │  │  /bookmarks, /search, /views   │ │
          │  └────────────┬───────────────────┘ │
          │               │                      │
          │  ┌────────────▼───────────────────┐ │
          │  │    Core Services Layer         │ │
          │  │  ┌──────────────────────────┐  │ │
          │  │  │ BookmarkManager          │  │ │
          │  │  │ SearchEngine             │  │ │
          │  │  │ StorageManager           │  │ │
          │  │  │ ContentAnalyzer          │  │ │
          │  │  │ ScreenshotCapture        │  │ │
          │  │  └──────────────────────────┘  │ │
          │  └────────────┬───────────────────┘ │
          └───────────────┼─────────────────────┘
                          │
          ┌───────────────▼─────────────────────┐
          │      External Services              │
          │  ┌────────────┐  ┌────────────────┐ │
          │  │ OpenAI API │  │   Playwright   │ │
          │  │ (GPT +     │  │   (Headless    │ │
          │  │ Embeddings)│  │    Browser)    │ │
          │  └────────────┘  └────────────────┘ │
          └─────────────────────────────────────┘
                          │
          ┌───────────────▼─────────────────────┐
          │      File System Storage            │
          │  ┌─────────────────────────────┐    │
          │  │  Storage Locations          │    │
          │  │  ├─ Work/                   │    │
          │  │  │  ├─ bookmarks/*.yaml     │    │
          │  │  │  ├─ favicons/*.ico       │    │
          │  │  │  └─ screenshots/*.png    │    │
          │  │  └─ Personal/               │    │
          │  │     ├─ bookmarks/*.yaml     │    │
          │  │     ├─ favicons/*.ico       │    │
          │  │     └─ screenshots/*.png    │    │
          │  └─────────────────────────────┘    │
          └─────────────────────────────────────┘
```

### Component Responsibilities

#### API Routes Layer
- HTTP request handling and validation
- Authentication/authorization (future)
- Response formatting (JSON)
- Error handling and status codes

#### Core Services Layer

**BookmarkManager**
- CRUD operations for bookmarks
- Folder/tag management
- Soft delete and hard delete
- Last accessed timestamp tracking
- Duplicate detection

**SearchEngine**
- Keyword/text search
- Semantic search with OpenAI embeddings
- Embedding cache management
- Result ranking and filtering

**StorageManager**
- YAML file I/O operations
- Multi-storage location management
- File locking and concurrency
- In-memory index management
- File watching for external changes

**ContentAnalyzer**
- Webpage fetching and parsing
- Title extraction via OpenAI GPT
- Keyword generation via OpenAI GPT
- Favicon downloading
- Metadata extraction

**ScreenshotCapture**
- Playwright browser management
- Screenshot capture with retries
- Image optimization and storage
- Error handling for dynamic pages

## 2. Technology Stack Details

### Backend
- **Language**: Python 3.10+
- **Web Framework**: FastAPI 0.100+
- **ASGI Server**: Uvicorn
- **Async HTTP**: httpx
- **YAML**: PyYAML or ruamel.yaml
- **Web Scraping**: BeautifulSoup4, Playwright
- **Validation**: Pydantic (built into FastAPI)
- **Environment Variables**: python-dotenv

### AI/ML
- **OpenAI Python SDK**: openai>=1.0.0
- **Models**:
  - Embeddings: `text-embedding-3-small` (fast, cheap, good quality)
  - Content Analysis: `gpt-4o-mini` (fast, cost-effective)

### Frontend (MVP)
- **HTML5/CSS3**: Semantic markup
- **JavaScript**: Vanilla ES6+
- **CSS Framework**: Simple.css or Water.css (classless, minimal)
- **Icons**: Feather Icons or similar lightweight set

### Development & Distribution
- **Package Manager**: pip
- **Build System**: setuptools or Poetry
- **Environment**: venv
- **Testing**: pytest
- **Linting**: ruff or flake8
- **Type Checking**: mypy

## 3. Data Models

### Bookmark Model

```python
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class Bookmark(BaseModel):
    """Core bookmark data structure."""

    # Required fields
    id: str = Field(..., description="Unique identifier (UUID)")
    url: HttpUrl = Field(..., description="The bookmarked URL")
    title: str = Field(..., min_length=1, max_length=500)
    keywords: List[str] = Field(
        default_factory=list,
        max_items=4,
        description="Ordered list of keywords (priority order)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional fields
    description: Optional[str] = Field(None, max_length=5000)
    tags: List[str] = Field(default_factory=list)
    folder_path: Optional[str] = Field(None, description="Folder hierarchy path")
    last_modified: Optional[datetime] = None
    last_accessed: Optional[datetime] = None

    # Soft delete
    deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None

    # Asset references
    favicon_path: Optional[str] = Field(None, description="Relative path to favicon")
    screenshot_path: Optional[str] = Field(None, description="Relative path to screenshot")

    # Metadata
    storage_location: str = Field(..., description="Which storage this belongs to")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "url": "https://github.com/python/cpython",
                "title": "CPython Official Repository",
                "keywords": ["python", "cpython", "github"],
                "description": "Official Python implementation source code",
                "tags": ["programming", "open-source"],
                "folder_path": "development/python",
                "created_at": "2026-02-03T10:30:00Z",
                "storage_location": "work"
            }
        }
```

### YAML File Format

Each bookmark is stored as a YAML file: `{bookmark_id}.yaml`

```yaml
id: 550e8400-e29b-41d4-a716-446655440000
url: https://github.com/python/cpython
title: CPython Official Repository
keywords:
  - python
  - cpython
  - github
description: Official Python implementation source code
tags:
  - programming
  - open-source
folder_path: development/python
created_at: 2026-02-03T10:30:00Z
last_modified: 2026-02-03T14:22:00Z
last_accessed: 2026-02-04T09:15:30Z
deleted: false
deleted_at: null
favicon_path: favicons/github.com.ico
screenshot_path: screenshots/550e8400-e29b-41d4-a716-446655440000.png
storage_location: work
```

### Storage Location Model

```python
class StorageLocation(BaseModel):
    """Represents a storage location (e.g., Work, Personal)."""

    name: str = Field(..., description="Display name")
    path: str = Field(..., description="Absolute path to storage directory")
    is_current: bool = Field(default=False, description="Currently active storage")
    is_default: bool = Field(default=False, description="Default storage")
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Configuration Model

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvSettings(BaseSettings):
    """Settings loaded from .env file (secrets and credentials)."""

    # OpenAI Configuration
    openai_api_key: str
    openai_api_base: Optional[str] = None  # Custom endpoint (e.g., Azure)
    openai_api_type: str = "openai"  # "openai" or "azure"
    openai_api_version: Optional[str] = None  # For Azure

    # Azure OpenAI (if using Azure)
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment_name: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

class AppConfig(BaseModel):
    """Application configuration from config.yaml."""

    # Server settings
    host: str = "127.0.0.1"
    port: Optional[int] = None  # Auto-select if None

    # Storage
    storage_locations: List[StorageLocation]

    # Features
    enable_semantic_search: bool = True
    enable_screenshots: bool = True
    screenshot_timeout: int = 10  # seconds

    # OpenAI Model Selection
    embedding_model: str = "text-embedding-3-small"
    content_analysis_model: str = "gpt-4o-mini"

    # Cache settings
    cache_embeddings: bool = True
    max_cache_size_mb: int = 100

    # Logging
    log_level: str = "INFO"
```

## 4. File Structure

### Project Directory Structure

```
yoshibookmark/
├── src/
│   └── yoshibookmark/
│       ├── __init__.py
│       ├── __main__.py              # Entry point: python -m yoshibookmark
│       ├── cli.py                   # CLI commands
│       ├── config.py                # Configuration management
│       │
│       ├── api/                     # FastAPI routes
│       │   ├── __init__.py
│       │   ├── bookmarks.py         # Bookmark CRUD endpoints
│       │   ├── search.py            # Search endpoints
│       │   ├── views.py             # View-related endpoints
│       │   ├── storage.py           # Storage management endpoints
│       │   └── health.py            # Health check endpoints
│       │
│       ├── core/                    # Core business logic
│       │   ├── __init__.py
│       │   ├── bookmark_manager.py  # Bookmark operations
│       │   ├── search_engine.py     # Search logic
│       │   ├── storage_manager.py   # File I/O and indexing
│       │   ├── content_analyzer.py  # Web content analysis
│       │   └── screenshot.py        # Screenshot capture
│       │
│       ├── models/                  # Pydantic models
│       │   ├── __init__.py
│       │   ├── bookmark.py
│       │   ├── storage.py
│       │   └── config.py
│       │
│       ├── utils/                   # Utilities
│       │   ├── __init__.py
│       │   ├── yaml_handler.py      # YAML I/O
│       │   ├── file_lock.py         # File locking
│       │   └── url_utils.py         # URL validation/parsing
│       │
│       └── web/                     # Frontend assets
│           ├── static/
│           │   ├── css/
│           │   │   └── style.css
│           │   ├── js/
│           │   │   ├── app.js
│           │   │   ├── search.js
│           │   │   └── views.js
│           │   └── icons/
│           └── templates/
│               └── index.html
│
├── tests/
│   ├── __init__.py
│   ├── test_bookmark_manager.py
│   ├── test_search_engine.py
│   ├── test_storage_manager.py
│   └── fixtures/
│
├── docs/
│   ├── API.md
│   └── USER_GUIDE.md
│
├── pyproject.toml               # Project metadata and dependencies
├── requirements.txt             # Pinned dependencies
├── setup.py                     # Setup script
├── README.md
├── CLAUDE.md
├── DESIGN.md
├── spec.md
└── .gitignore
```

### Storage Directory Structure

Each storage location has this structure:

```
{storage_path}/
├── bookmarks/                   # Individual bookmark YAML files
│   ├── 550e8400-e29b-41d4-a716-446655440000.yaml
│   ├── 661f9511-f3ac-52e5-b827-557766551111.yaml
│   └── ...
├── favicons/                    # Downloaded favicons
│   ├── github.com.ico
│   ├── stackoverflow.com.ico
│   └── ...
├── screenshots/                 # Captured screenshots
│   ├── 550e8400-e29b-41d4-a716-446655440000.png
│   ├── 661f9511-f3ac-52e5-b827-557766551111.png
│   └── ...
└── .metadata/                   # Storage metadata (optional)
    └── info.yaml
```

## 5. API Design

### Base URL
`http://localhost:{port}/api/v1`

### Endpoints

#### Bookmarks

**Create Bookmark**
```http
POST /api/v1/bookmarks
Content-Type: application/json

{
  "url": "https://example.com",
  "title": "Example Site",  // Optional, auto-generated if not provided
  "description": "My notes about this site",
  "keywords": ["example", "test"],  // Optional, auto-generated if not provided
  "tags": ["work", "reference"],
  "folder_path": "projects/example-project"
}

Response 201:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://example.com",
  "title": "Example Domain - Official Site",  // AI-generated
  "keywords": ["example", "test", "domain", "website"],  // User + AI keywords
  "description": "My notes about this site",
  "tags": ["work", "reference"],
  "folder_path": "projects/example-project",
  "created_at": "2026-02-04T10:00:00Z",
  "favicon_path": "favicons/example.com.ico",
  "screenshot_path": "screenshots/550e8400-e29b-41d4-a716-446655440000.png",
  "storage_location": "work"
}
```

**List Bookmarks**
```http
GET /api/v1/bookmarks?storage={storage_name}&include_deleted={bool}&folder={path}

Response 200:
{
  "bookmarks": [...],
  "total": 150,
  "storage": "work"
}
```

**Get Bookmark**
```http
GET /api/v1/bookmarks/{id}

Response 200:
{
  "id": "...",
  "url": "...",
  ...
}
```

**Update Bookmark**
```http
PUT /api/v1/bookmarks/{id}
Content-Type: application/json

{
  "title": "Updated Title",
  "keywords": ["new", "keywords"]
}

Response 200:
{
  "id": "...",
  "title": "Updated Title",
  "last_modified": "2026-02-04T10:30:00Z",
  ...
}
```

**Delete Bookmark (Soft)**
```http
DELETE /api/v1/bookmarks/{id}?hard=false

Response 200:
{
  "id": "...",
  "deleted": true,
  "deleted_at": "2026-02-04T10:35:00Z"
}
```

**Delete Bookmark (Hard)**
```http
DELETE /api/v1/bookmarks/{id}?hard=true

Response 204 No Content
```

**Restore Bookmark**
```http
POST /api/v1/bookmarks/{id}/restore

Response 200:
{
  "id": "...",
  "deleted": false,
  "deleted_at": null
}
```

**Access Bookmark (Track last accessed)**
```http
POST /api/v1/bookmarks/{id}/access

Response 200:
{
  "id": "...",
  "last_accessed": "2026-02-04T10:40:00Z"
}
```

#### Search

**Keyword Search**
```http
GET /api/v1/search?q={query}&storage={storage_name}&type=keyword

Response 200:
{
  "query": "python",
  "results": [
    {
      "id": "...",
      "url": "...",
      "title": "...",
      "relevance_score": 0.95,
      "matched_fields": ["keywords", "title"]
    }
  ],
  "total": 15,
  "search_type": "keyword"
}
```

**Semantic Search**
```http
GET /api/v1/search?q={query}&storage={storage_name}&type=semantic

Response 200:
{
  "query": "how to write good Python code",
  "results": [
    {
      "id": "...",
      "url": "...",
      "title": "Python Best Practices Guide",
      "relevance_score": 0.87,
      "similarity": 0.87
    }
  ],
  "total": 8,
  "search_type": "semantic"
}
```

#### Views

**Global View**
```http
GET /api/v1/views/global?sort_by={field}&order={asc|desc}

Response 200:
{
  "bookmarks": [
    {
      "id": "...",
      "storage_location": "work",
      "title": "...",
      ...
    }
  ],
  "storage_locations": ["work", "personal"],
  "total": 250
}
```

**Top Keyword View**
```http
GET /api/v1/views/top-keyword?storage={storage_name}&global={bool}

Response 200:
{
  "keyword_groups": [
    {
      "keyword": "python",
      "count": 25,
      "bookmarks": [...]
    },
    {
      "keyword": "javascript",
      "count": 18,
      "bookmarks": [...]
    }
  ],
  "storage": "work"
}
```

**Filtered View**
```http
GET /api/v1/views/filtered?query={query}&storage={storage_name}&global={bool}

Response 200:
{
  "query": "...",
  "filtered_bookmarks": [...],
  "total": 42
}
```

**Duplicate Detection View**
```http
GET /api/v1/views/duplicates?storage={storage_name}

Response 200:
{
  "duplicate_groups": [
    {
      "url": "https://github.com/python/cpython",
      "count": 3,
      "bookmarks": [
        {
          "id": "...",
          "keywords": ["python", "source"],
          "last_accessed": "..."
        },
        {
          "id": "...",
          "keywords": ["cpython", "reference"],
          "last_accessed": "..."
        }
      ]
    }
  ],
  "total_duplicates": 15
}
```

#### Storage Management

**List Storage Locations**
```http
GET /api/v1/storage

Response 200:
{
  "storage_locations": [
    {
      "name": "work",
      "path": "/path/to/work",
      "is_current": true,
      "is_default": true,
      "bookmark_count": 150
    },
    {
      "name": "personal",
      "path": "/path/to/personal",
      "is_current": false,
      "is_default": false,
      "bookmark_count": 95
    }
  ]
}
```

**Add Storage Location**
```http
POST /api/v1/storage
Content-Type: application/json

{
  "name": "research",
  "path": "/path/to/research"
}

Response 201:
{
  "name": "research",
  "path": "/path/to/research",
  "is_current": false,
  "is_default": false
}
```

**Set Current Storage**
```http
POST /api/v1/storage/{name}/set-current

Response 200:
{
  "name": "research",
  "is_current": true
}
```

#### Health & Info

**Health Check**
```http
GET /api/v1/health

Response 200:
{
  "status": "healthy",
  "version": "0.1.0",
  "storage_accessible": true,
  "openai_configured": true
}
```

## 6. Core Service Implementations

### 6.1 StorageManager

```python
class StorageManager:
    """Manages file I/O, indexing, and multi-storage."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.storage_locations: Dict[str, StorageLocation] = {}
        self.in_memory_index: Dict[str, Dict[str, Bookmark]] = {}  # {storage_name: {id: bookmark}}
        self.embedding_cache: Dict[str, List[float]] = {}

    async def initialize(self):
        """Load all storage locations and build in-memory index."""
        for storage in self.config.storage_locations:
            await self.load_storage(storage.name)

    async def load_storage(self, storage_name: str):
        """Load all bookmarks from a storage location into memory."""
        storage = self.get_storage_location(storage_name)
        bookmarks_path = Path(storage.path) / "bookmarks"

        self.in_memory_index[storage_name] = {}

        for yaml_file in bookmarks_path.glob("*.yaml"):
            try:
                bookmark = await self.load_bookmark_file(yaml_file)
                self.in_memory_index[storage_name][bookmark.id] = bookmark
            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")

    async def save_bookmark(self, bookmark: Bookmark, storage_name: str):
        """Save bookmark to YAML file with file locking."""
        storage = self.get_storage_location(storage_name)
        file_path = Path(storage.path) / "bookmarks" / f"{bookmark.id}.yaml"

        async with FileLocker(file_path):
            yaml_content = self.serialize_bookmark(bookmark)
            await asyncio.to_thread(file_path.write_text, yaml_content)

        # Update in-memory index
        if storage_name not in self.in_memory_index:
            self.in_memory_index[storage_name] = {}
        self.in_memory_index[storage_name][bookmark.id] = bookmark

    def get_bookmarks(
        self,
        storage_name: Optional[str] = None,
        include_deleted: bool = False,
        folder_path: Optional[str] = None
    ) -> List[Bookmark]:
        """Get bookmarks from in-memory index with filters."""
        if storage_name:
            bookmarks = list(self.in_memory_index.get(storage_name, {}).values())
        else:
            # Global view - all storages
            bookmarks = []
            for storage_bookmarks in self.in_memory_index.values():
                bookmarks.extend(storage_bookmarks.values())

        # Apply filters
        if not include_deleted:
            bookmarks = [b for b in bookmarks if not b.deleted]

        if folder_path:
            bookmarks = [b for b in bookmarks if b.folder_path == folder_path]

        return bookmarks
```

### 6.2 ContentAnalyzer

```python
class ContentAnalyzer:
    """Analyzes webpage content using OpenAI."""

    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def analyze_url(self, url: str) -> Dict[str, Any]:
        """Fetch URL and analyze content for title and keywords."""

        # Fetch webpage content
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return {
                "title": self.extract_domain_name(url),
                "keywords": self.extract_keywords_from_url(url),
                "error": str(e)
            }

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Get text content (first 3000 chars for GPT)
        text_content = soup.get_text(separator=' ', strip=True)[:3000]

        # Get existing title as fallback
        existing_title = soup.title.string if soup.title else url

        # Analyze with GPT
        analysis = await self.analyze_with_gpt(url, text_content, existing_title)

        # Extract keywords from URL as backup
        url_keywords = self.extract_keywords_from_url(url)

        # Combine keywords (GPT keywords + URL keywords, limit to 4)
        all_keywords = analysis.get("keywords", []) + url_keywords
        unique_keywords = list(dict.fromkeys(all_keywords))[:4]  # Remove duplicates, limit to 4

        return {
            "title": analysis.get("title", existing_title),
            "keywords": unique_keywords,
            "suggested_description": analysis.get("description", "")
        }

    async def analyze_with_gpt(self, url: str, content: str, fallback_title: str) -> Dict[str, Any]:
        """Use GPT to analyze content and extract title/keywords."""

        prompt = f"""Analyze this webpage and provide:
1. A concise, descriptive title (max 100 chars)
2. Up to 4 relevant keywords that describe the content
3. A brief one-sentence description

URL: {url}
Content: {content}

Respond in JSON format:
{{
  "title": "...",
  "keywords": ["...", "...", "...", "..."],
  "description": "..."
}}
"""

        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a content analyzer that extracts titles and keywords from web content. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )

            result = json.loads(response.choices[0].message.content)
            return result

        except Exception as e:
            logger.error(f"GPT analysis failed: {e}")
            return {
                "title": fallback_title,
                "keywords": [],
                "description": ""
            }

    def extract_keywords_from_url(self, url: str) -> List[str]:
        """Extract keywords from URL path segments."""
        parsed = urlparse(url)

        # Get domain without TLD
        domain_parts = parsed.netloc.split('.')
        if len(domain_parts) > 2:
            domain_keyword = domain_parts[-2]  # e.g., 'github' from 'github.com'
        else:
            domain_keyword = domain_parts[0]

        # Get path segments
        path_segments = [s for s in parsed.path.split('/') if s and s not in ['', 'index.html']]

        # Clean and filter
        keywords = [domain_keyword] + path_segments[:3]
        keywords = [k.lower() for k in keywords if len(k) > 2 and not k.isdigit()]

        return keywords[:4]

    async def download_favicon(self, url: str, storage_path: Path) -> Optional[str]:
        """Download favicon for URL."""
        parsed = urlparse(url)
        domain = parsed.netloc

        favicon_urls = [
            f"{parsed.scheme}://{domain}/favicon.ico",
            f"{parsed.scheme}://{domain}/favicon.png",
        ]

        for favicon_url in favicon_urls:
            try:
                response = await self.http_client.get(favicon_url)
                response.raise_for_status()

                # Save favicon
                favicon_filename = f"{domain}.ico"
                favicon_path = storage_path / "favicons" / favicon_filename
                favicon_path.parent.mkdir(parents=True, exist_ok=True)

                await asyncio.to_thread(favicon_path.write_bytes, response.content)

                return f"favicons/{favicon_filename}"

            except Exception:
                continue

        return None
```

### 6.3 SearchEngine

```python
class SearchEngine:
    """Handles keyword and semantic search."""

    def __init__(self, openai_client: OpenAI, storage_manager: StorageManager):
        self.client = openai_client
        self.storage_manager = storage_manager
        self.embedding_cache: Dict[str, List[float]] = {}

    async def keyword_search(
        self,
        query: str,
        storage_name: Optional[str] = None
    ) -> List[Tuple[Bookmark, float]]:
        """Perform keyword/text search with relevance scoring."""

        bookmarks = self.storage_manager.get_bookmarks(storage_name)
        query_lower = query.lower()
        results = []

        for bookmark in bookmarks:
            score = 0.0
            matched_fields = []

            # Search in title (highest weight)
            if query_lower in bookmark.title.lower():
                score += 1.0
                matched_fields.append("title")

            # Search in keywords (high weight)
            for keyword in bookmark.keywords:
                if query_lower in keyword.lower():
                    score += 0.8
                    matched_fields.append("keywords")
                    break

            # Search in description
            if bookmark.description and query_lower in bookmark.description.lower():
                score += 0.5
                matched_fields.append("description")

            # Search in URL
            if query_lower in str(bookmark.url).lower():
                score += 0.3
                matched_fields.append("url")

            # Search in tags
            for tag in bookmark.tags:
                if query_lower in tag.lower():
                    score += 0.6
                    matched_fields.append("tags")
                    break

            if score > 0:
                results.append((bookmark, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    async def semantic_search(
        self,
        query: str,
        storage_name: Optional[str] = None,
        top_k: int = 20
    ) -> List[Tuple[Bookmark, float]]:
        """Perform semantic search using OpenAI embeddings."""

        # Get query embedding
        query_embedding = await self.get_embedding(query)

        # Get all bookmarks
        bookmarks = self.storage_manager.get_bookmarks(storage_name)

        # Compute similarities
        similarities = []
        for bookmark in bookmarks:
            # Get bookmark embedding (from cache or compute)
            bookmark_text = self.prepare_bookmark_text(bookmark)
            bookmark_embedding = await self.get_embedding(bookmark_text, bookmark.id)

            # Compute cosine similarity
            similarity = self.cosine_similarity(query_embedding, bookmark_embedding)
            similarities.append((bookmark, similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    async def get_embedding(self, text: str, cache_key: Optional[str] = None) -> List[float]:
        """Get embedding from cache or OpenAI API."""

        if cache_key and cache_key in self.embedding_cache:
            return self.embedding_cache[cache_key]

        try:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model="text-embedding-3-small",
                input=text
            )

            embedding = response.data[0].embedding

            # Cache it
            if cache_key:
                self.embedding_cache[cache_key] = embedding

            return embedding

        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536

    def prepare_bookmark_text(self, bookmark: Bookmark) -> str:
        """Prepare bookmark text for embedding."""
        parts = [
            bookmark.title,
            " ".join(bookmark.keywords),
            bookmark.description or "",
            " ".join(bookmark.tags)
        ]
        return " ".join(parts)

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
```

### 6.4 ScreenshotCapture

```python
class ScreenshotCapture:
    """Captures webpage screenshots using Playwright."""

    def __init__(self):
        self.playwright = None
        self.browser = None

    async def initialize(self):
        """Initialize Playwright browser."""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

    async def capture_screenshot(
        self,
        url: str,
        storage_path: Path,
        bookmark_id: str,
        timeout: int = 10
    ) -> Optional[str]:
        """Capture screenshot of URL."""

        if not self.browser:
            await self.initialize()

        try:
            page = await self.browser.new_page(viewport={"width": 1280, "height": 720})

            # Navigate with timeout
            await page.goto(url, timeout=timeout * 1000, wait_until="networkidle")

            # Capture screenshot
            screenshot_filename = f"{bookmark_id}.png"
            screenshot_path = storage_path / "screenshots" / screenshot_filename
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)

            await page.screenshot(path=str(screenshot_path), full_page=False)

            await page.close()

            return f"screenshots/{screenshot_filename}"

        except Exception as e:
            logger.error(f"Failed to capture screenshot for {url}: {e}")
            return None

    async def cleanup(self):
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
```

## 7. Frontend Design (MVP)

### Simple HTML/CSS/JS Structure

**index.html** (simplified structure)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YoshiBookmark</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div id="app">
        <!-- Header -->
        <header>
            <h1>📚 YoshiBookmark</h1>
            <div class="storage-selector">
                <select id="storage-select">
                    <option value="">Global View</option>
                    <option value="work">Work</option>
                    <option value="personal">Personal</option>
                </select>
            </div>
        </header>

        <!-- Add Bookmark Form -->
        <section class="add-bookmark">
            <h2>Add Bookmark</h2>
            <form id="add-bookmark-form">
                <input type="url" id="url-input" placeholder="Paste URL here" required>
                <button type="submit">Add</button>
            </form>
            <div id="analyzing" style="display:none;">Analyzing webpage...</div>
            <div id="bookmark-preview" style="display:none;">
                <!-- Preview with editable title/keywords -->
            </div>
        </section>

        <!-- View Tabs -->
        <nav class="view-tabs">
            <button class="tab active" data-view="list">List</button>
            <button class="tab" data-view="top-keyword">Top Keywords</button>
            <button class="tab" data-view="filtered">Search</button>
        </nav>

        <!-- Search Bar (visible in filtered view) -->
        <section class="search-bar" id="search-section" style="display:none;">
            <input type="text" id="search-input" placeholder="Search bookmarks...">
            <label>
                <input type="checkbox" id="semantic-search"> Semantic Search
            </label>
        </section>

        <!-- Bookmarks Display -->
        <main id="bookmarks-container">
            <!-- Dynamically populated by JavaScript -->
        </main>
    </div>

    <script src="/static/js/app.js" type="module"></script>
</body>
</html>
```

**app.js** (simplified structure)

```javascript
// State management
const state = {
    currentStorage: null,
    currentView: 'list',
    bookmarks: [],
    searchQuery: ''
};

// API calls
async function fetchBookmarks(storage = null) {
    const url = storage
        ? `/api/v1/bookmarks?storage=${storage}`
        : `/api/v1/bookmarks`;

    const response = await fetch(url);
    const data = await response.json();
    return data.bookmarks;
}

async function addBookmark(url) {
    const response = await fetch('/api/v1/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
    });
    return await response.json();
}

async function searchBookmarks(query, semantic = false) {
    const type = semantic ? 'semantic' : 'keyword';
    const url = `/api/v1/search?q=${encodeURIComponent(query)}&type=${type}`;

    const response = await fetch(url);
    const data = await response.json();
    return data.results;
}

// Rendering
function renderBookmarks(bookmarks) {
    const container = document.getElementById('bookmarks-container');

    if (bookmarks.length === 0) {
        container.innerHTML = '<p>No bookmarks found</p>';
        return;
    }

    container.innerHTML = bookmarks.map(bookmark => `
        <div class="bookmark-card" data-id="${bookmark.id}">
            <div class="bookmark-favicon">
                ${bookmark.favicon_path
                    ? `<img src="/storage/${bookmark.storage_location}/${bookmark.favicon_path}" alt="">`
                    : '🔖'
                }
            </div>
            <div class="bookmark-content">
                <h3><a href="${bookmark.url}" target="_blank">${bookmark.title}</a></h3>
                <p class="description">${bookmark.description || ''}</p>
                <div class="keywords">
                    ${bookmark.keywords.map(k => `<span class="keyword">${k}</span>`).join('')}
                </div>
                <div class="metadata">
                    <span>Added: ${new Date(bookmark.created_at).toLocaleDateString()}</span>
                    ${bookmark.last_accessed
                        ? `<span>Last accessed: ${new Date(bookmark.last_accessed).toLocaleDateString()}</span>`
                        : ''
                    }
                </div>
            </div>
            <div class="bookmark-actions">
                <button onclick="editBookmark('${bookmark.id}')">Edit</button>
                <button onclick="deleteBookmark('${bookmark.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

// Event listeners
document.getElementById('add-bookmark-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = document.getElementById('url-input').value;

    document.getElementById('analyzing').style.display = 'block';

    try {
        const bookmark = await addBookmark(url);
        state.bookmarks.unshift(bookmark);
        renderBookmarks(state.bookmarks);
        e.target.reset();
    } catch (error) {
        alert('Failed to add bookmark: ' + error.message);
    } finally {
        document.getElementById('analyzing').style.display = 'none';
    }
});

// Real-time search
let searchTimeout;
document.getElementById('search-input')?.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        const query = e.target.value;
        const semantic = document.getElementById('semantic-search').checked;

        if (query.length > 0) {
            const results = await searchBookmarks(query, semantic);
            renderBookmarks(results);
        } else {
            renderBookmarks(state.bookmarks);
        }
    }, 300); // Debounce 300ms
});

// Initialize
async function init() {
    state.bookmarks = await fetchBookmarks(state.currentStorage);
    renderBookmarks(state.bookmarks);
}

init();
```

## 8. Package Distribution

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=65.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "yoshibookmark"
version = "0.1.0"
description = "A URL and bookmark management system with intelligent search"
authors = [{name = "Your Name", email = "your.email@example.com"}]
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
keywords = ["bookmarks", "url-management", "search", "semantic-search"]

dependencies = [
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",  # For settings management
    "pyyaml>=6.0",
    "httpx>=0.24.0",
    "beautifulsoup4>=4.12.0",
    "openai>=1.0.0",
    "playwright>=1.40.0",
    "python-multipart>=0.0.6",  # For file uploads
    "python-dotenv>=1.0.0",  # For .env file support
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
]

[project.scripts]
yoshibookmark = "yoshibookmark.cli:main"

[project.urls]
Homepage = "https://github.com/yourusername/yoshibookmark"
Documentation = "https://github.com/yourusername/yoshibookmark/blob/main/README.md"
Repository = "https://github.com/yourusername/yoshibookmark"

[tool.setuptools]
packages = ["yoshibookmark"]
package-dir = {"" = "src"}

[tool.setuptools.package-data]
yoshibookmark = ["web/**/*"]
```

### CLI Entry Point (cli.py)

```python
import click
import uvicorn
import asyncio
from pathlib import Path

@click.group()
def main():
    """YoshiBookmark - URL and Bookmark Management System"""
    pass

@main.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=None, type=int, help='Port to bind to (auto-select if not specified)')
@click.option('--config', default=None, help='Path to config file')
def serve(host, port, config):
    """Start the bookmark server."""

    # Load or create config
    if config:
        config_path = Path(config)
    else:
        config_path = Path.home() / '.yoshibookmark' / 'config.yaml'

    if not config_path.exists():
        click.echo(f"No config found at {config_path}")
        click.echo("Run 'yoshibookmark init' first to create configuration")
        return

    # Auto-select port if not specified
    if port is None:
        import socket
        sock = socket.socket()
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()

    click.echo(f"Starting YoshiBookmark server at http://{host}:{port}")

    uvicorn.run(
        "yoshibookmark.api:app",
        host=host,
        port=port,
        reload=False
    )

@main.command()
@click.option('--azure', is_flag=True, help='Configure for Azure OpenAI')
def init(azure):
    """Initialize configuration."""
    config_dir = Path.home() / '.yoshibookmark'
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / 'config.yaml'
    env_file = config_dir / '.env'

    if config_file.exists() and env_file.exists():
        click.echo(f"Config already exists at {config_dir}")
        if not click.confirm("Overwrite existing configuration?"):
            return

    # Interactive setup
    click.echo("Welcome to YoshiBookmark!")
    click.echo("\nLet's set up your configuration.\n")

    # API Configuration
    if azure:
        click.echo("Configuring for Azure OpenAI...")
        api_key = click.prompt("Azure OpenAI API Key", hide_input=True)
        endpoint = click.prompt("Azure OpenAI Endpoint (e.g., https://your-resource.openai.azure.com)")
        deployment = click.prompt("Deployment Name")
        api_version = click.prompt("API Version", default="2024-02-15-preview")

        env_content = f"""# Azure OpenAI Configuration
OPENAI_API_KEY={api_key}
OPENAI_API_TYPE=azure
AZURE_OPENAI_ENDPOINT={endpoint}
AZURE_OPENAI_DEPLOYMENT_NAME={deployment}
OPENAI_API_VERSION={api_version}
"""
    else:
        click.echo("Configuring for OpenAI...")
        api_key = click.prompt("OpenAI API Key", hide_input=True)

        if click.confirm("Use custom endpoint?", default=False):
            custom_endpoint = click.prompt("Custom API Base URL")
            env_content = f"""# OpenAI Configuration (Custom Endpoint)
OPENAI_API_KEY={api_key}
OPENAI_API_BASE={custom_endpoint}
"""
        else:
            env_content = f"""# OpenAI Configuration
OPENAI_API_KEY={api_key}
"""

    # Storage Configuration
    default_storage_path = click.prompt(
        "Default storage path",
        default=str(config_dir / 'storage' / 'default')
    )

    # Create .env file
    with open(env_file, 'w') as f:
        f.write(env_content)

    # Secure .env file permissions (Unix-like systems)
    if os.name != 'nt':  # Not Windows
        os.chmod(env_file, 0o600)

    # Create config.yaml
    config = {
        'storage_locations': [
            {
                'name': 'default',
                'path': default_storage_path,
                'is_current': True,
                'is_default': True
            }
        ],
        'enable_semantic_search': True,
        'enable_screenshots': True,
        'embedding_model': 'text-embedding-3-small',
        'content_analysis_model': 'gpt-4o-mini'
    }

    import yaml
    with open(config_file, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    # Create storage directories
    storage_path = Path(default_storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / 'bookmarks').mkdir(exist_ok=True)
    (storage_path / 'favicons').mkdir(exist_ok=True)
    (storage_path / 'screenshots').mkdir(exist_ok=True)

    click.echo(f"\n✓ Credentials saved to {env_file}")
    click.echo(f"✓ Configuration saved to {config_file}")
    click.echo(f"✓ Storage created at {storage_path}")
    click.echo("\n⚠️  IMPORTANT: Never commit .env file to version control!")
    click.echo("\nRun 'yoshibookmark serve' to start the server!")

@main.command()
@click.argument('url')
@click.option('--title', help='Bookmark title')
@click.option('--keywords', help='Comma-separated keywords')
def add(url, title, keywords):
    """Add a bookmark from command line."""
    # Implementation here
    click.echo(f"Adding bookmark: {url}")

if __name__ == '__main__':
    main()
```

## 9. Installation & Setup

### For End Users

```bash
# Install from PyPI (once published)
pip install yoshibookmark

# Initialize configuration
yoshibookmark init

# Start server
yoshibookmark serve

# Or specify port
yoshibookmark serve --port 8080
```

### For Developers

```bash
# Clone repository
git clone https://github.com/yourusername/yoshibookmark.git
cd yoshibookmark

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium

# Initialize configuration
yoshibookmark init

# Run tests
pytest

# Start development server
yoshibookmark serve
```

## 10. Implementation Phases

### Phase 1: MVP (Priority P1)
**Goal**: Basic bookmark management with simple UI

**Components:**
1. ✓ Project structure and packaging setup
2. ✓ Configuration management (config.yaml, CLI init)
3. ✓ Storage manager (YAML I/O, in-memory index)
4. ✓ Basic bookmark CRUD (create, read, update, delete)
5. ✓ Simple content analyzer (fetch URL, extract title)
6. ✓ FastAPI routes (bookmarks CRUD)
7. ✓ Simple HTML/CSS/JS frontend
8. ✓ List view
9. ✓ Add bookmark form
10. ✓ CLI serve command with auto-port selection

**Deferred from Phase 1:**
- Semantic search
- Screenshots
- OpenAI integration (use BeautifulSoup title extraction only)
- Advanced views

**Deliverable**: Users can add, view, edit, delete bookmarks via web UI

---

### Phase 2: Intelligent Features (Priority P1-P2)
**Goal**: Add AI-powered features

**Components:**
1. ✓ OpenAI integration for content analysis
2. ✓ GPT-based title and keyword extraction
3. ✓ Keyword search implementation
4. ✓ Top Keyword View
5. ✓ Global View with storage column
6. ✓ Favicon downloading
7. ✓ Multi-storage location support
8. ✓ Storage switcher in UI

**Deliverable**: Intelligent bookmark organization with multiple storage locations

---

### Phase 3: Search & Discovery (Priority P2)
**Goal**: Advanced search capabilities

**Components:**
1. ✓ OpenAI embeddings integration
2. ✓ Semantic search implementation
3. ✓ Embedding cache management
4. ✓ Filtered View with semantic search
5. ✓ Real-time search in UI
6. ✓ Duplicate detection view
7. ✓ Last accessed tracking

**Deliverable**: Powerful search with natural language queries

---

### Phase 4: Visual Features (Priority P2-P3)
**Goal**: Screenshots and enhanced UX

**Components:**
1. ✓ Playwright integration
2. ✓ Screenshot capture
3. ✓ Screenshot display in UI
4. ✓ Soft delete implementation
5. ✓ Hard delete with confirmation
6. ✓ Restore functionality

**Deliverable**: Visual bookmarks with screenshot previews and safe deletion

---

### Phase 5: Import/Export & Visualization (Priority P3)
**Goal**: Data portability and graph visualization

**Components:**
1. ✓ HTML bookmark import (Netscape format)
2. ✓ Export functionality
3. ✓ Graph visualization (D3.js or similar)
4. ✓ Keyword-grouped browse
5. ✓ IDE integration API endpoints

**Deliverable**: Complete feature set from spec.md

---

### Phase 6: Modern Frontend (Future)
**Goal**: Upgrade to React/Vue for better UX

**Components:**
1. ✓ React/Vue setup
2. ✓ Drag-and-drop for folders/tags
3. ✓ Real-time filtering
4. ✓ Smooth animations
5. ✓ Mobile-responsive design

**Deliverable**: Modern, interactive UI

## 11. Testing Strategy

### Unit Tests
- `test_bookmark_manager.py`: CRUD operations, validation
- `test_search_engine.py`: Keyword and semantic search
- `test_storage_manager.py`: File I/O, locking, indexing
- `test_content_analyzer.py`: URL fetching, GPT analysis
- `test_screenshot.py`: Screenshot capture

### Integration Tests
- API endpoint tests
- End-to-end bookmark creation flow
- Search flows
- Multi-storage operations

### Manual Testing Checklist
- [ ] Add bookmark with valid URL
- [ ] Add bookmark with invalid URL (error handling)
- [ ] Edit bookmark details
- [ ] Soft delete and restore
- [ ] Hard delete with confirmation
- [ ] Keyword search
- [ ] Semantic search
- [ ] Switch storage locations
- [ ] Global view with multiple storages
- [ ] Top keyword view grouping
- [ ] Screenshot capture success/failure
- [ ] Concurrent file access (multiple clients)

## 12. Configuration Management

### Two-File Configuration Approach

**Secrets in .env** (never commit to git)
**Settings in config.yaml** (can commit to git)

### .env Format (API Keys and Secrets)

```bash
# OpenAI Configuration (Standard)
OPENAI_API_KEY=sk-...

# OR: Azure OpenAI Configuration
# OPENAI_API_TYPE=azure
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
# OPENAI_API_KEY=your-azure-api-key
# OPENAI_API_VERSION=2024-02-15-preview

# OR: Custom OpenAI-Compatible Endpoint
# OPENAI_API_BASE=https://api.your-service.com/v1
# OPENAI_API_KEY=your-api-key
```

### .env.example (Template - commit this to git)

```bash
# OpenAI API Configuration
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here

# For Azure OpenAI, uncomment and configure:
# OPENAI_API_TYPE=azure
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
# OPENAI_API_VERSION=2024-02-15-preview

# For custom OpenAI-compatible endpoints:
# OPENAI_API_BASE=https://api.your-service.com/v1
```

### config.yaml Format (Non-Secret Settings)

```yaml
# Server Configuration
host: 127.0.0.1
port: null  # Auto-select

# Storage Locations
storage_locations:
  - name: default
    path: /home/user/.yoshibookmark/storage/default
    is_current: true
    is_default: true

  - name: work
    path: /home/user/OneDrive/WorkBookmarks
    is_current: false
    is_default: false

# Feature Flags
enable_semantic_search: true
enable_screenshots: true
screenshot_timeout: 10

# OpenAI Model Selection
embedding_model: text-embedding-3-small
content_analysis_model: gpt-4o-mini

# Cache Settings
cache_embeddings: true
max_cache_size_mb: 100

# Logging
log_level: INFO
```

### Configuration Loading

```python
# config.py
import os
from pathlib import Path
from typing import Optional
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

class EnvSettings(BaseSettings):
    """Load secrets from .env file."""
    openai_api_key: str
    openai_api_base: Optional[str] = None
    openai_api_type: str = "openai"
    openai_api_version: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment_name: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path.home() / '.yoshibookmark'

        self.config_dir = config_dir
        self.config_file = config_dir / 'config.yaml'
        self.env_file = config_dir / '.env'

    def load_env_settings(self) -> EnvSettings:
        """Load environment settings from .env file."""
        # Load .env file
        if self.env_file.exists():
            load_dotenv(self.env_file)

        return EnvSettings()

    def load_app_config(self) -> AppConfig:
        """Load app configuration from config.yaml."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file) as f:
            data = yaml.safe_load(f)

        return AppConfig(**data)

    def save_app_config(self, config: AppConfig):
        """Save app configuration to config.yaml."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, 'w') as f:
            yaml.safe_dump(config.model_dump(), f, default_flow_style=False)

    def create_env_file_template(self):
        """Create .env file from user input."""
        env_content = f"""# OpenAI API Configuration
OPENAI_API_KEY=your-api-key-here

# For Azure OpenAI, uncomment and configure:
# OPENAI_API_TYPE=azure
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
# OPENAI_API_VERSION=2024-02-15-preview

# For custom OpenAI-compatible endpoints:
# OPENAI_API_BASE=https://api.your-service.com/v1
"""

        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.env_file, 'w') as f:
            f.write(env_content)
```

## 13. Error Handling

### Common Scenarios

1. **URL Fetch Failures**
   - Timeout: Return domain name as title, extract keywords from URL
   - 404/500: Show user-friendly error, allow manual title entry
   - Network error: Queue for retry or allow offline mode

2. **OpenAI API Failures**
   - Rate limit: Implement exponential backoff
   - Invalid API key: Show setup instructions
   - Quota exceeded: Fallback to simple title extraction

3. **Screenshot Failures**
   - Timeout: Skip screenshot, continue with bookmark creation
   - Dynamic page: Use longer timeout or skip
   - Authentication required: Skip screenshot

4. **File System Errors**
   - Disk full: Alert user, prevent new bookmarks
   - Permission denied: Show clear error message
   - Corrupted YAML: Log error, skip file, continue loading others

5. **Concurrent Access**
   - File lock timeout: Retry with backoff
   - Conflicting edits: Last-write-wins or show merge UI

## 14. Performance Considerations

### For 100s of Bookmarks

**Memory Usage:**
- ~1KB per bookmark YAML = 100 bookmarks = 100KB
- Embeddings: 1536 floats × 4 bytes × 100 = ~600KB
- Total: <10MB for entire collection in memory

**Startup Time:**
- Load 100 YAML files: <100ms
- Build in-memory index: <50ms
- Total: <200ms startup time

**Search Performance:**
- Keyword search: O(n) through 100 bookmarks = <5ms
- Semantic search: Compute similarities for 100 embeddings = <50ms
- Both well within acceptable limits

**Conclusion**: No optimization needed for 100s of bookmarks. In-memory approach is perfect.

## 15. Security Considerations

### API Security
- No authentication in MVP (localhost only)
- Future: Add API key authentication for remote access
- CORS: Restrict to localhost in production

### Data Privacy
- Bookmarks stored locally (not in cloud)
- OpenAI API: URL and content sent for analysis (document this)
- Future: Option to disable OpenAI features for privacy

### Input Validation
- URL validation (prevent XSS, injection)
- File path validation (prevent directory traversal)
- YAML parsing (prevent code injection)

## 16. Deployment Considerations

### Portability
- ✓ Single pip install command
- ✓ Works on Windows, Mac, Linux
- ✓ No external database dependencies
- ✓ Playwright auto-downloads browser

### Multi-Machine Setup
1. Install: `pip install yoshibookmark`
2. Copy config: `~/.yoshibookmark/config.yaml`
3. Point storage locations to synced folders (OneDrive, Dropbox, etc.)
4. Run: `yoshibookmark serve`

### Future: Cloud Sync
- Storage locations can be in cloud-synced folders
- File-based approach enables automatic sync
- YAML format is diff-friendly for version control

## 17. Future Enhancements

### Beyond MVP

1. **Browser Extension**
   - One-click bookmark from browser
   - Right-click context menu
   - Communicate with local server via API

2. **Mobile App**
   - React Native or Flutter
   - Access bookmarks from phone
   - Share to YoshiBookmark

3. **Collaborative Features**
   - Share bookmark collections
   - Export public collection as website
   - Import from shared collections

4. **Advanced Analytics**
   - Most accessed bookmarks
   - Usage patterns over time
   - Keyword trends

5. **AI Enhancements**
   - Automatic tagging based on reading patterns
   - Smart recommendations
   - Related bookmark suggestions
   - Summarization of bookmarked content

## Summary

This design provides:
- ✓ Clean architecture with separation of concerns
- ✓ Portable Python package with venv support
- ✓ Simple MVP frontend (upgrade to React later)
- ✓ OpenAI integration for intelligent features
- ✓ File-based storage (perfect for 100s of bookmarks)
- ✓ Multi-storage support
- ✓ Clear implementation phases
- ✓ Easy installation and setup

Next steps: Begin Phase 1 implementation following this design.
