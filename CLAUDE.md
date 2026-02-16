# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a URL and bookmark management system (yoshibookmark) that allows users to save, organize, search, and visualize web bookmarks. The system features:

- Web-based interface for bookmark management
- Multiple storage locations (e.g., "Work Bookmarks", "Personal Bookmarks")
- Intelligent keyword extraction and semantic search
- Graph visualization of bookmark-keyword relationships
- HTTP REST API for IDE/editor integration
- YAML-based file storage for human-readability and diff-friendliness

## Core Architecture Concepts

### Multi-Storage Design

The system supports multiple named storage locations (e.g., work vs. personal bookmarks):
- Each storage location is a separate directory containing bookmark YAML files
- Users can switch between storages or use Global View to see all bookmarks
- Most operations are scoped to the "current" storage location
- Global View provides cross-storage management with storage name as a column

### Bookmark Data Model

**Critical**: Bookmarks are stored as individual YAML files, one per bookmark. This design:
- Enables concurrent access from multiple clients (web UI, CLI, IDE integration)
- Provides human-readable, diff-friendly format for version control
- Allows same URL to be saved multiple times with different keywords as separate entries

Each bookmark has:
- Required: URL, Title, Creation Timestamp, Keywords (ordered list, max 4)
- Optional: Description, Tags, Folder Path, Last Modified/Accessed timestamps, Favicon reference, Screenshot reference
- Keywords are stored in priority order (first = highest priority)
- Same URL with different keywords = separate bookmark entries (enables context-specific organization)

### View Types

The system provides three distinct view modes:
1. **Global View**: Management-focused table showing all bookmarks from all storages with storage column
2. **Top Keyword View**: Groups bookmarks by their highest-priority (first) keyword
3. **Filtered View**: Intelligent search using LLM inference for semantic matching

### Screenshot Strategy

Each bookmark entry maintains its own independent screenshot, even for duplicate URLs:
- Allows capturing page state at different times
- Provides visual hints when URLs become broken/inaccessible
- Can be automatically captured or user-provided
- Stored as separate image files in storage location

### Delete Strategy

Two-tier deletion system:
1. **Soft Delete** (default): Hides bookmark but preserves all data and files for recovery
2. **Hard Delete**: Permanent removal of bookmark file and associated resources (favicon, screenshot)

## Data Storage Structure

All bookmark data is stored in YAML format. The file structure is:
- Each bookmark = one YAML file
- Favicons stored in storage location (referenced by bookmark)
- Screenshots stored in storage location (referenced by bookmark)
- File locking/conflict resolution needed for concurrent access scenarios

## Key Implementation Priorities

Feature priorities are defined in spec.md with detailed acceptance scenarios:
- **P1 (MVP)**: Save/organize bookmarks, view/access bookmarks, navigate view types
- **P2**: Search/retrieve, edit/delete, manage storage locations
- **P3**: Import/export, visualization, IDE integration

## Important Constraints

### URL Duplication
The same URL can be saved multiple times with different keyword sets as separate bookmark entries. This is intentional - it allows the same resource to be tagged for different projects/contexts. Each URL-keyword combination is a distinct bookmark with independent metadata.

### Keyword Management
- Maximum 4 keywords per bookmark
- Keywords stored in priority order (first = most relevant)
- User-specified keywords prioritized over auto-generated ones
- Keywords extracted from: URL paths, webpage content, descriptions

### Concurrent Access
Since bookmark files may be accessed by multiple clients simultaneously (web UI, CLI tools, IDE integration):
- Implement file locking or conflict resolution for concurrent writes
- Validate file integrity when reading
- Handle corrupted/malformed YAML gracefully
- Ensure atomic updates where possible

### Port Configuration
Web server must automatically select an available port to avoid conflicts. Display the selected port/URL to users on startup.

## Technical Decisions

Based on spec.md clarifications (Session 2026-02-04):
- **Storage Format**: YAML (human-readable, diff-friendly)
- **Web Server Port**: Random available port (configurable)
- **Screenshots**: Independent per bookmark entry (not shared across duplicates)
- **IDE Integration Protocol**: HTTP REST API (returns JSON)
- **Folder Deletion Behavior**: Move bookmarks to parent/root
- **Configuration**: Secrets in `.env` file (never commit), settings in `config.yaml`
- **API Support**: OpenAI, Azure OpenAI, or custom OpenAI-compatible endpoints

## Development Guidelines

### When Adding Features
1. Refer to spec.md for detailed acceptance scenarios and functional requirements
2. Preserve bookmark data integrity - never lose data during operations
3. Handle edge cases documented in spec.md (malformed URLs, network errors, concurrent access, etc.)
4. Maintain YAML format consistency for multi-client compatibility
5. Respect keyword priority ordering in all operations

### Search Implementation
Two search modes required:
1. **Keyword Search**: Near-exact matching on titles, descriptions, URLs, tags, keywords
2. **Semantic Search**: Natural language queries using LLM to find semantically relevant bookmarks even without exact term matches

### Testing Focus
- Concurrent file access scenarios (multiple clients)
- YAML parsing/validation with malformed files
- Bookmark recovery after soft delete
- Duplicate URL handling with different keywords
- Storage location switching and global view
- Folder deletion with bookmark relocation
