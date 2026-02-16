# YoshiBookmark

A URL and bookmark management system with intelligent search, semantic discovery, and multiple storage locations.

## Features

- 📚 **Save & Organize**: Quickly save URLs with automatic title and keyword extraction
- 🔍 **Smart Search**: Keyword search and semantic search using AI
- 🏷️ **Keywords & Tags**: Automatic keyword extraction from URLs and content
- 📂 **Multiple Storages**: Organize bookmarks across different locations (Work, Personal, etc.)
- 📸 **Screenshots**: Capture webpage screenshots for visual reference
- 🌐 **Web Interface**: Clean, simple browser-based UI
- 🔌 **API Access**: REST API for IDE/editor integration
- 💾 **File-Based**: YAML storage for portability and cloud sync
- 🗑️ **Safe Deletion**: Soft delete with recovery, hard delete for permanent removal

## Installation

### Requirements

- Python 3.10 or higher
- OpenAI API key (or Azure OpenAI)

### Quick Start

```bash
# Install from PyPI (once published)
pip install yoshibookmark

# Or install from source
git clone https://github.com/yourusername/yoshibookmark.git
cd yoshibookmark
pip install -e .

# Install Playwright browsers (for screenshots)
playwright install chromium

# Initialize configuration (required once; creates ~/.yoshibookmark/config.yaml and ~/.yoshibookmark/.env)
yoshibookmark init --storage-mode onedrive-only --onedrive-path "C:\Users\YourName\OneDrive\YoshiBookmark"

# Start the server
yoshibookmark serve
```

The server will automatically select an available port and display the URL.

## Configuration

YoshiBookmark uses two configuration files:

### First-Time Setup Checklist (including extension)

1. Run init once (required):
```bash
yoshibookmark init --storage-mode onedrive-only --onedrive-path "C:\Users\YourName\OneDrive\YoshiBookmark"
```
2. Edit `C:\Users\<you>\.yoshibookmark\.env` and set both required values:
```env
OPENAI_API_KEY=sk-your-key-here
EXTENSION_API_TOKEN=your-random-local-token
```
   - `OPENAI_API_KEY`: from https://platform.openai.com/api-keys
   - `EXTENSION_API_TOKEN`: a local random secret (not OAuth). Generate in PowerShell:
```powershell
[guid]::NewGuid().ToString("N")
```
3. Start server:
```bash
yoshibookmark serve --port 8000
```
4. Load extension (`extension/yoshibookmark-extension`) as unpacked:
   - Chrome: open `chrome://extensions`
   - Edge: open `edge://extensions` (Developer mode can be hidden in a collapsed left pane)
   - Turn on **Developer mode** -> **Load unpacked**
5. Copy extension ID from the extension details page and add to `C:\Users\<you>\.yoshibookmark\config.yaml`:
```yaml
extension_allowed_origins:
  - "chrome-extension://<your-extension-id>"
  - "edge-extension://<your-extension-id>"
```
6. Restart server.
7. In extension settings, set:
   - API Base URL: `http://127.0.0.1:8000`
   - Extension API Token: same value as `EXTENSION_API_TOKEN`
8. Validate setup:
```bash
yoshibookmark doctor --api-url http://127.0.0.1:8000
```

Why ID and token are both required:
- Extension ID identifies browser origin (`chrome-extension://...` or `edge-extension://...`) for backend allowlist/CORS.
- `EXTENSION_API_TOKEN` is a local shared secret to prevent unauthorized local writes.
- It is not OAuth and does not require any external identity provider.

### 1. `.env` - API Keys and Secrets (Never commit!)

Use `C:\Users\<you>\.yoshibookmark\.env` (created by `yoshibookmark init`):

```bash
# OpenAI (Standard)
OPENAI_API_KEY=sk-your-key-here

# OR: Azure OpenAI
OPENAI_API_TYPE=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
OPENAI_API_KEY=your-azure-key
OPENAI_API_VERSION=2024-02-15-preview

# OR: Custom OpenAI-Compatible Endpoint
OPENAI_API_BASE=https://api.your-service.com/v1
OPENAI_API_KEY=your-key

# Extension capture auth (local shared secret, not OAuth; same value used in extension settings)
EXTENSION_API_TOKEN=your-random-local-token
```

### 2. `config.yaml` - Application Settings

Located at `~/.yoshibookmark/config.yaml`:

```yaml
# Storage locations
storage_locations:
  - name: onedrive
    path: C:\Users\YourName\OneDrive\YoshiBookmark
    is_current: true
    is_default: true
storage_mode: onedrive_only
primary_storage_provider: onedrive_local
primary_storage_path: C:\Users\YourName\OneDrive\YoshiBookmark
legacy_storage_readonly: false

# Features
enable_semantic_search: true
enable_screenshots: true

# Models
embedding_model: text-embedding-3-small
content_analysis_model: gpt-4o-mini
```

## Usage

### Starting the Server

```bash
# Start with auto-selected port
yoshibookmark serve

# Specify port
yoshibookmark serve --port 8080

# Use custom config location
yoshibookmark serve --config-dir /path/to/configdir
```

### Validate Setup

```bash
# Validate config + env + storage + extension setup
yoshibookmark doctor

# Also verify running server health endpoint
yoshibookmark doctor --api-url http://127.0.0.1:8000
```

### Adding Bookmarks

1. Open the web interface (URL displayed when server starts)
2. Paste a URL in the "Add Bookmark" box
3. The system automatically:
   - Fetches the webpage
   - Extracts a title
   - Suggests relevant keywords
   - Downloads the favicon
   - Captures a screenshot
4. Review and edit the suggestions
5. Click "Save"

### Searching Bookmarks

**Keyword Search**: Fast, exact matching
```
Type: python tutorial
Finds: Bookmarks with "python" or "tutorial" in title, keywords, or description
```

**Semantic Search**: AI-powered, understands meaning
```
Type: how to write good Python code
Finds: Bookmarks about Python best practices, style guides, clean code, etc.
```

### Multiple Storage Locations

Perfect for separating work and personal bookmarks, or organizing by project:

```bash
# Add new storage location
Settings → Storage Locations → Add

Name: Work Bookmarks
Path: C:\Users\YourName\OneDrive\WorkBookmarks

# Switch between storages using the dropdown
# Or use Global View to see all bookmarks
```

### One-time Migration To OneDrive

```bash
yoshibookmark migrate-to-onedrive \
  --source-path C:\path\to\old\storage \
  --onedrive-path C:\Users\YourName\OneDrive\YoshiBookmark
```

This imports bookmark files and assets once, updates `config.yaml` to `onedrive_only`, and marks legacy storage as read-only metadata.

## Architecture

### Storage Structure

Each storage location contains:

```
storage/
├── bookmarks/           # Individual bookmark YAML files
│   ├── {uuid}.yaml
│   └── ...
├── favicons/           # Website favicons
│   └── example.com.ico
└── screenshots/        # Webpage screenshots
    └── {uuid}.png
```

### Bookmark Format (YAML)

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
last_accessed: 2026-02-04T09:15:30Z
deleted: false
favicon_path: favicons/github.com.ico
screenshot_path: screenshots/550e8400-e29b-41d4-a716-446655440000.png
storage_location: work
```

## API Endpoints

REST API available at `http://localhost:{port}/api/v1`:

- `POST /bookmarks` - Create bookmark
- `GET /bookmarks` - List bookmarks
- `GET /bookmarks/{id}` - Get bookmark
- `PUT /bookmarks/{id}` - Update bookmark
- `DELETE /bookmarks/{id}` - Delete bookmark
- `POST /ingest/preview` - Generate capture suggestions for browser extension
- `POST /ingest/commit` - Commit a preview into bookmark storage
- `POST /ingest/quick-save` - Save directly from capture context
- `GET /ingest/providers/status` - Provider chain diagnostics for ingestion
- `GET /search?q={query}&type={keyword|semantic}` - Search
- `GET /views/global` - Global view
- `GET /views/top-keyword` - Top keyword view
- `GET /views/filtered?query={query}` - Filtered view
- `GET /views/duplicates` - Duplicate detection

See `docs/API.md` for complete API documentation.

## Development

```bash
# Clone repository
git clone https://github.com/yourusername/yoshibookmark.git
cd yoshibookmark

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install Playwright
playwright install chromium

# Run tests
pytest

# Start development server
yoshibookmark serve
```

## Multi-Machine Setup

YoshiBookmark is designed for portability:

1. **Install on each machine**: `pip install yoshibookmark`
2. **Copy configuration**:
   - Copy `~/.yoshibookmark/config.yaml`
   - Copy `~/.yoshibookmark/.env`
3. **Use cloud-synced storage**: Point storage locations to OneDrive, Dropbox, or other synced folders
4. **Run**: `yoshibookmark serve`

The YAML file format is human-readable and git/diff-friendly, making it perfect for version control and synchronization.

## Privacy & Security

- **Local-first**: Bookmarks stored on your machine, not in the cloud
- **API calls**: Only URL content and queries are sent to OpenAI API for analysis
- **No tracking**: No analytics, no telemetry, no data collection
- **Secure storage**: API keys stored in `.env` file with restricted permissions

## Roadmap

- [x] Phase 1: Basic bookmark management
- [x] Phase 2: OpenAI integration for smart features
- [ ] Phase 3: Semantic search and duplicate detection
- [ ] Phase 4: Screenshots and visual features
- [ ] Phase 5: Import/export and graph visualization
- [ ] Phase 6: Modern React/Vue frontend

See `spec.md` for detailed feature specifications.

## Contributing

Contributions welcome! Please read `CLAUDE.md` and `DESIGN.md` for architecture details.

## License

MIT License - See LICENSE file for details

## Support

- **Issues**: https://github.com/yourusername/yoshibookmark/issues
- **Documentation**: See `docs/` directory
- **Design**: See `DESIGN.md` for technical details

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [OpenAI API](https://openai.com/) - AI-powered features
- [Playwright](https://playwright.dev/) - Browser automation
- [Pydantic](https://docs.pydantic.dev/) - Data validation
