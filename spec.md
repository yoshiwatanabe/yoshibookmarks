# Feature Specification: URL and Bookmark Management System

**Feature Branch**: `001-bookmark-management`  
**Created**: February 3, 2026  
**Status**: Draft  
**Input**: User description: "Create a url and link (aka bookmark) management system"

## Clarifications

### Session 2026-02-04

- Q: What file format should be used for storing bookmark files (human-readable and diff-friendly)? → A: YAML
- Q: What should be the default web server port configuration? → A: Random available port
- Q: Should screenshots be shared across duplicate URLs or independent per bookmark entry? → A: Independent per bookmark
- Q: What protocol should the MCP server use for IDE/editor integration? → A: HTTP REST API
- Q: What happens to bookmarks when a user confirms deletion of a folder containing them? → A: Move to parent/root

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save and Organize Bookmarks (Priority: P1)

Users need to quickly save URLs they find interesting and organize them for later retrieval. They access the bookmark system through a web interface where they can paste URLs into an input box. The system intelligently analyzes the webpage content to understand what the page is about, automatically suggests a title and relevant keywords, and allows users to add descriptions and organize bookmarks using folders or tags. The web server automatically selects an available port to avoid conflicts with other services.

**Why this priority**: This is the core functionality - without the ability to save and organize bookmarks, the system has no value. This represents the MVP.

**Independent Test**: Can be fully tested by accessing the web interface, pasting URLs, verifying automatic suggestions, organizing them into folders/tags, and confirming they are saved and can be retrieved. Delivers immediate value by allowing users to manage their bookmarks.

**Acceptance Scenarios**:

**Adding Bookmarks via Web Interface**:
1. **Given** I access the bookmark system in my web browser, **When** I navigate to the interface, **Then** I see an "Add" URL input box
2. **Given** I am in the web interface, **When** I paste a URL into the "Add" box and submit, **Then** the system fetches the webpage content
3. **Given** the system has fetched webpage content, **When** it analyzes the page, **Then** it automatically suggests a title based on the page's content
4. **Given** the system has analyzed webpage content, **When** it completes the analysis, **Then** it automatically suggests relevant keywords (up to 4) based on what the page is about
5. **Given** I receive automatic suggestions for a URL, **When** I review them, **Then** I can accept, modify, or replace the suggested title and keywords
6. **Given** I am adding a bookmark, **When** I manually enter a description, **Then** the system may generate additional keyword suggestions from that description
7. **Given** I have configured the bookmark details, **When** I save it, **Then** the bookmark is stored with the URL, title, description, timestamp, and keywords

**Keyword Extraction and Organization**:
1. **Given** I am saving a bookmark with URL "github.com/python/cpython", **When** the system processes it, **Then** keywords like "github", "python", "cpython" are automatically extracted from the URL path and stored in priority order
2. **Given** the system generates multiple keywords, **When** it ranks them, **Then** the most relevant keyword is placed first in the ordered list (highest priority)
3. **Given** I provide a description when saving a bookmark, **When** I submit the bookmark, **Then** the system generates relevant keywords from the description (up to 4) and adds them to the bookmark
4. **Given** I am saving a bookmark, **When** I manually specify keywords, **Then** those keywords are prioritized and added at the beginning of the ordered keyword list
5. **Given** I have saved bookmarks, **When** I organize them into folders or apply tags, **Then** the bookmarks are categorized and I can filter/browse by folder or tag
6. **Given** I have bookmarks in folders, **When** I move a bookmark from one folder to another, **Then** the bookmark's organization is updated immediately

**Favicon Handling**:
1. **Given** I save a bookmark, **When** the system fetches the webpage, **Then** it also retrieves the website's favicon
2. **Given** a favicon is retrieved, **When** the bookmark is saved, **Then** the favicon is stored in the storage location and associated with the bookmark
3. **Given** I view my bookmarks, **When** I see the bookmark list, **Then** each bookmark displays its associated favicon for visual identification

**Screenshot Capture**:
1. **Given** I save a bookmark, **When** the system processes the URL, **Then** it captures a screenshot of the webpage
2. **Given** I am adding a bookmark, **When** I provide the URL, **Then** I can optionally provide my own screenshot image if I prefer
3. **Given** a screenshot is captured or provided, **When** the bookmark is saved, **Then** the screenshot is stored in the storage location and associated with the bookmark
4. **Given** I save the same URL with different keywords, **When** each bookmark entry is created, **Then** each gets its own independent screenshot (allowing context-specific captures at different times)
5. **Given** I view my bookmarks, **When** I hover over or click on a bookmark, **Then** I can see the screenshot as a visual reminder of what the page looks like
6. **Given** I have a bookmark with a screenshot, **When** the original URL becomes broken or inaccessible, **Then** the screenshot serves as a visual hint of what the page was pointing to
7. **Given** I view a bookmark's details, **When** I examine the screenshot, **Then** it increases my confidence about what content the URL points to before clicking

**Duplicate URLs with Different Keywords**:
1. **Given** I have already saved "github.com/azure/docs" with keywords ["azure", "documentation"], **When** I save the same URL again with keywords ["project-alpha", "reference"], **Then** the system creates a separate bookmark entry
2. **Given** I save the same URL multiple times with different keywords, **When** I search by a specific keyword, **Then** only bookmarks with that keyword appear in results
3. **Given** the same URL exists with different keyword sets, **When** I view keyword-grouped browse, **Then** each bookmark instance appears under its respective keyword groups
4. **Given** I have multiple bookmark entries for the same URL, **When** I edit or delete one, **Then** the other entries remain unchanged
5. **Given** a URL is saved for multiple projects, **When** I view my bookmarks, **Then** each entry is treated as a distinct bookmark with its own metadata (title, description, keywords)

**Duplicate Detection and Management**:
1. **Given** I have saved the same URL multiple times, **When** I access the duplicate detection view, **Then** the system shows me all URLs that exist in multiple bookmark entries
2. **Given** I am viewing duplicate URLs, **When** I examine a duplicate group, **Then** I see all bookmark entries for that URL with their respective keywords, titles, and metadata
3. **Given** I identify an unwanted duplicate, **When** I choose to delete it, **Then** the system allows me to select which specific bookmark entry to remove
4. **Given** I am viewing duplicates, **When** I compare entries, **Then** I can see the differences in keywords, descriptions, and usage patterns to decide which to keep

---

### User Story 2 - Search and Retrieve Bookmarks (Priority: P2)

Users need to quickly find bookmarks they've saved previously using multiple search methods. They can search using exact keyword matching for precise results, or use natural language queries to find bookmarks by meaning and intent when they don't remember exact terms. The system understands semantic similarity to return relevant bookmarks even when search terms don't exactly match saved content.

**Why this priority**: As bookmark collections grow, manual browsing becomes inefficient. Search is critical for usability but requires saved bookmarks to exist first (depends on P1).

**Independent Test**: Can be tested by creating a collection of bookmarks with various titles, descriptions, and tags, then searching for them using different keywords and verifying relevant results are returned. Additionally test by searching with natural language queries and verifying semantically related bookmarks are found.

**Acceptance Scenarios**:

**Keyword Search (Near Exact Match)**:
1. **Given** I have multiple bookmarks saved, **When** I search for specific keywords in titles or descriptions, **Then** the system returns all bookmarks with near-exact keyword matches ranked by relevance
2. **Given** I have bookmarks with extracted keywords, **When** I search using one of those keywords, **Then** the system returns matching bookmarks
3. **Given** I have bookmarks with tags, **When** I search by tag name, **Then** all bookmarks with that tag are displayed
4. **Given** I have bookmarks saved, **When** I search using partial URL text, **Then** matching bookmarks are returned

**Semantic Search**:
1. **Given** I have a bookmark titled "Python best practices guide", **When** I search for "how to write good Python code", **Then** the bookmark appears in results because of semantic similarity
2. **Given** I have bookmarks about machine learning, **When** I search using "AI tutorials", **Then** the system returns relevant ML bookmarks even if they don't contain the exact term "AI"
3. **Given** I have multiple bookmarks on related topics, **When** I use a natural language query describing what I'm looking for, **Then** the system ranks results by semantic relevance to my intent
4. **Given** I search with ambiguous or general terms, **When** the system finds multiple semantically relevant bookmarks, **Then** results are ordered by relevance with the most similar matches first

---

### User Story 3 - View and Access Bookmarks (Priority: P1)

Users need to view their saved bookmarks in an organized list and be able to click on them to visit the saved URLs. They should see key information like title, description, and when the bookmark was saved.

**Why this priority**: Essential for delivering value - users must be able to access their saved bookmarks. This is part of the MVP alongside saving functionality.

**Independent Test**: Can be tested by viewing a list of saved bookmarks, verifying all information is displayed correctly, and clicking bookmarks to confirm they navigate to the correct URLs.

**Acceptance Scenarios**:

1. **Given** I have saved bookmarks, **When** I view my bookmark list, **Then** I see all bookmarks with their titles, URLs, descriptions, save dates, and last accessed dates
2. **Given** I am viewing a bookmark, **When** I click on it to navigate to its URL, **Then** the system records the current timestamp as the last accessed time
3. **Given** I click on a bookmark, **When** the navigation occurs, **Then** the system opens the URL in a new tab or window
4. **Given** I have bookmarks in different folders, **When** I navigate to a specific folder, **Then** I see only the bookmarks in that folder
5. **Given** I have bookmarks with different access times, **When** I sort by last accessed, **Then** the most recently used bookmarks appear first
6. **Given** I want to find recently used bookmarks, **When** I filter by access recency (e.g., last 7 days), **Then** I see only bookmarks accessed within that timeframe

---

### User Story 4 - Edit and Delete Bookmarks (Priority: P2)

Users need to update bookmark information (title, description, URL, tags) when details change or fix mistakes. They should be able to remove bookmarks they no longer need through soft delete (hidden but recoverable) or permanently remove them with hard delete when certain.

**Why this priority**: Improves usability and maintenance but is not critical for initial value delivery. Users can work around this by deleting and re-creating bookmarks initially. Soft delete provides safety while hard delete provides cleanup.

**Independent Test**: Can be tested by modifying existing bookmark properties and verifying changes are saved, soft deleting bookmarks to confirm they are hidden but recoverable, and hard deleting bookmarks with confirmation to verify permanent removal.

**Acceptance Scenarios**:

**Editing Bookmarks**:
1. **Given** I have a saved bookmark, **When** I edit its title, description, or URL, **Then** the changes are saved and reflected immediately
2. **Given** I have a saved bookmark, **When** I update its tags or folder assignment, **Then** the organizational changes are applied
3. **Given** I have a folder containing bookmarks, **When** I attempt to delete it, **Then** the system warns me and requires explicit confirmation
4. **Given** I confirm deletion of a folder with bookmarks, **When** the deletion proceeds, **Then** all bookmarks are moved to the parent folder (or root if no parent)
5. **Given** bookmarks are moved during folder deletion, **When** the operation completes, **Then** all bookmark metadata and files remain intact

**Soft Delete (Default)**:
1. **Given** I have a saved bookmark, **When** I choose to delete it, **Then** the system soft-deletes the bookmark by default (hidden but not permanently removed)
2. **Given** a bookmark is soft-deleted, **When** I view my bookmark list, **Then** the deleted bookmark does not appear in normal views
3. **Given** a bookmark is soft-deleted, **When** I access the deleted items view, **Then** I can see all soft-deleted bookmarks with their original metadata
4. **Given** I am viewing soft-deleted bookmarks, **When** I choose to restore one, **Then** the bookmark reappears in my normal bookmark list
5. **Given** soft-deleted bookmarks exist, **When** I search for bookmarks, **Then** soft-deleted items are excluded from search results by default
6. **Given** I have soft-deleted bookmarks, **When** I view storage space usage, **Then** the system still accounts for the storage used by deleted items

**Hard Delete (Permanent)**:
1. **Given** I have a soft-deleted bookmark, **When** I choose to hard delete it, **Then** the system prompts me for confirmation before permanent deletion
2. **Given** I confirm hard delete, **When** the system processes the request, **Then** the bookmark file and associated resources (favicon, screenshot) are permanently removed
3. **Given** I am viewing my bookmarks, **When** I choose to hard delete directly (bypassing soft delete), **Then** the system warns me and requires explicit confirmation
4. **Given** a bookmark is hard-deleted, **When** I try to restore it, **Then** it cannot be recovered
5. **Given** I have accumulated many soft-deleted items, **When** I choose to permanently clean up, **Then** the system offers a bulk hard delete option with confirmation

---

### User Story 5 - Manage Multiple Storage Locations (Priority: P2)

Users need to organize their bookmarks across multiple top-level storage containers (e.g., "Work Bookmarks" and "Personal Bookmarks"), each representing a distinct collection. Storage locations serve as the highest level of organization, and users can select one as "current" to focus their view on that specific collection. This separation is useful for keeping different aspects of life organized and for storing collections in different cloud-synced folders.

**Why this priority**: Important for organizational separation and cloud sync scenarios, but users can work with a single default storage initially. Essential for users who want to maintain separate contexts (work/personal).

**Independent Test**: Can be tested by configuring multiple storage locations with distinct names, switching between them as "current", saving bookmarks to different storages, and verifying that each storage maintains its own collection independently.

**Acceptance Scenarios**:

1. **Given** I am using the system for the first time, **When** I view storage settings, **Then** I see a default storage location is already configured and set as "current"
2. **Given** I want to organize bookmarks separately, **When** I add a new storage location, **Then** I can name it (e.g., "Work Bookmarks", "Personal Bookmarks") and specify its directory path
3. **Given** I have multiple storage locations configured, **When** I select one, **Then** it becomes the "current" storage and the view shows only bookmarks from that storage
4. **Given** I am viewing bookmarks, **When** I switch the current storage, **Then** the view updates to show only bookmarks from the newly selected storage
5. **Given** I add a new bookmark, **When** I save it, **Then** it is automatically saved to the current storage location
6. **Given** I have separate storage locations for work and personal bookmarks, **When** I view either one, **Then** the bookmarks remain mutually exclusive and don't mix
7. **Given** I have multiple storage locations, **When** I manage them, **Then** I can view, add, rename, switch between, or remove storage locations (except when only one remains)
8. **Given** I need to see all bookmarks across all storages, **When** I switch to Global View, **Then** I see bookmarks from all storage locations with storage name shown as a column

---

### User Story 6 - Navigate Multiple View Types (Priority: P1)

Users need different ways to browse and organize their bookmark collections depending on their workflow. The system provides three distinct view types: a Global View for management across all storage locations, a Top Keyword View for exploring bookmarks grouped by their highest-priority keywords, and a Filtered View that uses intelligent search to show related bookmarks.

**Why this priority**: Core to usability - different viewing modes enable different workflows. Users need these views to effectively browse, organize, and discover their bookmarks.

**Independent Test**: Can be tested by creating bookmarks across multiple storage locations with various keywords, then switching between the three view types and verifying each displays bookmarks appropriately (Global shows all with storage column, Top Keyword groups by keywords, Filtered responds to search queries).

**Acceptance Scenarios**:

**Global View (Management)**:
1. **Given** I have bookmarks in multiple storage locations, **When** I switch to Global View, **Then** I see all bookmarks from all storage locations combined
2. **Given** I am in Global View, **When** I look at the bookmark list, **Then** I see a storage location column showing which storage each bookmark belongs to
3. **Given** I am in Global View, **When** I perform management operations (edit, delete, move), **Then** I can work across all bookmarks regardless of their storage location

**Top Keyword View**:
1. **Given** I have bookmarks with various keywords, **When** I switch to Top Keyword View, **Then** I see bookmarks organized into groups based on their highest-priority (first) keyword
2. **Given** I am in Top Keyword View, **When** I browse the groups, **Then** each group header shows the keyword and the bookmarks under it share that keyword as their top priority
3. **Given** I am in Top Keyword View for the current storage, **When** I view the groups, **Then** I see only bookmarks from the current storage location organized by keywords
4. **Given** I am in Top Keyword View with Global View enabled, **When** I browse groups, **Then** bookmarks from all storage locations are shown, grouped by top keyword

**Filtered View (Intelligent Search)**:
1. **Given** I am in Filtered View, **When** I enter keywords in the search box, **Then** the system shows only bookmarks related to those keywords
2. **Given** I am in Filtered View, **When** I enter a description or phrase in the search box, **Then** the system uses intelligent inference to identify and show URLs likely related to my query
3. **Given** I search for a concept or topic, **When** the system processes my query, **Then** it analyzes bookmark descriptions, titles, keywords, and content to find semantic matches
4. **Given** I am in Filtered View, **When** results are displayed, **Then** they are ranked by relevance to my search query
5. **Given** I am in Filtered View with current storage selected, **When** I search, **Then** results are filtered to only the current storage location
6. **Given** I am in Filtered View with Global View enabled, **When** I search, **Then** results include bookmarks from all storage locations

---

### User Story 7 - Import and Export Bookmarks (Priority: P3)

Users need to migrate bookmarks from browsers or other bookmark services. They should be able to import bookmarks from standard formats (HTML, JSON) and export their collection for backup or migration purposes.

**Why this priority**: Important for user adoption and data portability but not essential for basic functionality. Users can manually add bookmarks initially.

**Independent Test**: Can be tested by importing a bookmark file from a browser, verifying all bookmarks are created correctly, then exporting the collection and confirming the exported file is valid and complete.

**Acceptance Scenarios**:

1. **Given** I have a browser bookmark export file, **When** I import it into the system, **Then** all bookmarks are created with their folders, titles, and URLs preserved
2. **Given** I have bookmarks in the system, **When** I export them, **Then** I receive a file containing all my bookmarks in a standard format
3. **Given** I import bookmarks with duplicate URLs, **When** the import completes, **Then** I can choose to merge or skip duplicates

---

### User Story 8 - Visualize and Explore Bookmarks (Priority: P3)

Users need alternative ways to discover and explore their bookmarks beyond traditional list views and search. They should be able to browse bookmarks grouped by keywords to see related content together, and visualize their bookmark collection as an interactive graph showing relationships between bookmarks and keywords.

**Why this priority**: Enhances discovery and exploration but not essential for core bookmark management. Users can accomplish their goals through search and folder browsing initially.

**Independent Test**: Can be tested by viewing bookmarks grouped by keywords and verifying correct grouping, then switching to graph view and confirming visual representation shows bookmark-keyword relationships with interactive navigation capabilities.

**Acceptance Scenarios**:

**Keyword-Grouped Browsing**:
1. **Given** I have bookmarks with various keywords, **When** I view the keyword-grouped browse mode, **Then** I see bookmarks organized under their associated keywords
2. **Given** I am browsing bookmarks grouped by keyword "python", **When** I view that group, **Then** I see all bookmarks that have "python" as a keyword
3. **Given** a bookmark has multiple keywords, **When** I browse by keywords, **Then** that bookmark appears under each of its associated keyword groups
4. **Given** I am viewing keyword groups, **When** I select a group, **Then** I can access any bookmark within that group

**Graph Visualization**:
1. **Given** I have a collection of bookmarks with keywords, **When** I switch to graph view, **Then** I see bookmarks as nodes connected to keyword nodes via edges
2. **Given** I am viewing the graph, **When** I click on a keyword node, **Then** I see all bookmarks connected to that keyword highlighted
3. **Given** I am viewing the graph, **When** I click on a bookmark node, **Then** I see its connections to all associated keywords
4. **Given** I am in graph view, **When** I interact with a bookmark node, **Then** I can access the bookmark's full details and navigate to the URL
5. **Given** I have a large collection, **When** I view the graph, **Then** the visualization remains readable and navigable with appropriate zoom and pan controls
6. **Given** I am exploring the graph, **When** I identify clusters of related bookmarks, **Then** I can understand thematic relationships in my collection

---

### User Story 9 - Search Bookmarks from Coding Environment (Priority: P3)

Developers working in their IDE or code editor need to quickly access relevant bookmarks without leaving their development environment. They should be able to search their bookmark collection directly from within tools like Claude Code, GitHub Copilot, or other AI coding assistants that support integrations. The system provides an HTTP REST API for IDE integration, ensuring universal compatibility and simple implementation.

**Why this priority**: Improves developer workflow efficiency but not essential for core bookmark management. Developers can use the main application initially and copy URLs manually.

**Independent Test**: Can be tested by connecting to the bookmark system from an IDE/editor, performing searches using various methods (keywords, semantic queries), and verifying that results are returned and can be accessed without leaving the coding environment.

**Acceptance Scenarios**:

1. **Given** I am working in my code editor with the bookmark integration enabled, **When** I search for bookmarks using keywords, **Then** I receive relevant bookmark results within the editor
2. **Given** I am coding and need a reference, **When** I use natural language to search for bookmarks (e.g., "find Python testing tutorials"), **Then** the system returns semantically relevant bookmarks
3. **Given** I have found a relevant bookmark in my editor, **When** I select it, **Then** I can view its full details including URL, title, description, and keywords
4. **Given** I am viewing bookmark search results in my editor, **When** I choose to open a bookmark, **Then** the URL opens in my default browser
5. **Given** I am working on a specific topic, **When** I search for related bookmarks from my editor, **Then** results are ranked by relevance just as they would be in the main application
6. **Given** the bookmark system is unavailable, **When** I try to search from my editor, **Then** I receive a clear error message explaining the connection issue

---

### Edge Cases

- What happens when a user saves a bookmark with a malformed or invalid URL?
- How does the system handle bookmarks with extremely long URLs (>2000 characters)?
- What happens when a user tries to create a folder with the same name as an existing folder?
- How does the system handle special characters or emojis in bookmark titles and descriptions?
- What happens when a user attempts to delete a folder containing bookmarks?
- What happens when deleting a deeply nested folder structure where multiple levels contain bookmarks?
- How does the system handle folder deletion if moving bookmarks to parent would create naming conflicts?
- How does the system handle bookmarks to URLs that later become inaccessible (404, domain expired)?
- What happens when importing a file with thousands of bookmarks at once?
- How does the system handle concurrent edits to the same bookmark from multiple devices?
- What happens when the system cannot extract any meaningful keywords from a URL?
- How does the system handle URLs with only numeric paths or random strings?
- What happens when automatically extracted keywords exceed the limit of 4?
- How does the system handle keyword extraction when a description is in a non-English language?
- What happens when user-specified keywords conflict with or duplicate auto-generated ones?
- What happens when a semantic search query is too vague or general?
- How does the system handle semantic search when no bookmarks are semantically relevant to the query?
- What happens when semantic search is performed on a very small collection (< 10 bookmarks)?
- How does the system determine relevance ranking when multiple bookmarks are equally semantically similar to a query?
- What happens in graph view when a bookmark has no keywords?
- How does the system visualize the graph when there are thousands of bookmarks and hundreds of keywords?
- What happens in keyword-grouped browse when multiple bookmarks share all the same keywords?
- How does the graph view handle overlapping nodes or complex interconnections?
- What happens when viewing keyword groups with only one bookmark?
- How does the system perform when rendering a large graph with hundreds of nodes and edges?
- What happens when the web interface tries to fetch a URL that returns a 404 or other HTTP error?
- How does the system handle fetching URLs that require authentication or are behind paywalls?
- What happens when fetching a URL takes too long (timeout scenarios)?
- How does the system handle URLs that redirect multiple times?
- What happens when the fetched webpage has no meaningful content (blank page, all images)?
- How does the system handle very large web pages (several MB of content)?
- What happens when the automatic title/keyword suggestion analysis fails?
- How does the system handle webpages in non-English languages?
- What happens when multiple users try to add the same URL simultaneously?
- How does the system handle malicious or dangerous URLs in the web interface?
- What happens when the IDE/editor integration loses connection to the bookmark system?
- How does the system handle search requests from the IDE when the user has no bookmarks?
- What happens when multiple IDE instances try to access bookmarks simultaneously?
- How does the system respond when an IDE search query is malformed or invalid?
- What happens when a user tries to add a storage location that doesn't exist or is inaccessible?
- How does the system handle a storage location that becomes unavailable (e.g., OneDrive disconnected)?
- What happens when a user tries to remove the default storage location?
- How does the system handle conflicts when the same bookmark exists in multiple storage locations?
- What happens when a storage location runs out of disk space?
- How does the system handle storage locations with different file system permissions?
- What happens when bookmarks in a storage location are modified by external processes (direct file edits)?
- How does the system handle very long storage location paths?
- What happens when multiple clients try to write to the same bookmark file simultaneously?
- How does the system handle corrupted or malformed bookmark data files?
- What happens when required fields are missing from a bookmark file?
- How does the system handle bookmark files with unknown or unsupported field names?
- What happens when a favicon cannot be retrieved or the website has no favicon?
- How does the system handle very large favicons?
- What happens when keyword priority order is ambiguous or missing?
- How does the system migrate bookmark files if the data structure changes in future versions?
- What happens when screenshot capture fails or the webpage cannot be rendered?
- How does the system handle very large screenshots (high-resolution pages)?
- What happens when the storage location has limited space and screenshots are large?
- How does the system handle dynamic webpages that look different each time they're loaded?
- What happens when a user provides a screenshot in an unsupported image format?
- How does the system handle screenshot capture for pages that require JavaScript or authentication?
- What happens when multiple screenshots exist for the same bookmark (e.g., updated pages)?
- What happens when a user saves the exact same URL with the exact same keywords - should it be prevented or allowed?
- How does the system distinguish between multiple bookmark entries for the same URL with different keywords?
- What happens when the same URL appears in search results multiple times (different keyword contexts)?
- How does the system handle deleting one bookmark instance when the same URL exists in other bookmark entries?
- What happens when importing bookmarks that have duplicate URLs but different metadata?
- How does the system display multiple bookmarks for the same URL in list views?
- What happens when all duplicate entries for a URL are soft-deleted?
- How does the duplicate detection view handle bookmarks across different storage locations?
- What happens when a user tries to restore a soft-deleted bookmark whose folder or storage location no longer exists?
- How does the system handle hard deleting a bookmark when associated files (favicon, screenshot) are missing or already deleted?
- What happens when multiple clients try to soft delete or hard delete the same bookmark simultaneously?
- How does the system handle screenshot cleanup when hard deleting one bookmark entry that shares a URL with other bookmarks?
- What happens when a user tries to hard delete without soft deleting first?
- How does the system handle bulk hard delete when some items fail to delete?
- What happens when soft-deleted items accumulate and consume significant storage space?
- How does the system display storage usage breakdown between active and soft-deleted bookmarks?
- What happens when multiple devices/clients click the same bookmark simultaneously?
- How does the system handle last accessed timestamp updates when the bookmark file is locked by another process?
- What happens if updating the last accessed timestamp fails due to write errors or permissions?
- How does the system handle last accessed timestamps when bookmarks are imported from external sources (no previous access history)?
- What happens when a bookmark is accessed via IDE integration - should that update the last accessed time?
- How does the system handle clock skew or time zone differences across multiple devices updating last accessed times?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a web-based interface accessible through a web browser
- **FR-001-port**: System MUST automatically select an available port when starting the web server to avoid conflicts
- **FR-001-port-a**: System MUST display the selected port and full URL to the user when the server starts
- **FR-001-port-b**: System MUST allow users to optionally specify a preferred port via configuration
- **FR-001a**: System MUST provide an "Add" URL input box in the web interface
- **FR-001b**: System MUST accept URL input from users via the web interface
- **FR-001c**: System MUST fetch webpage content when a URL is submitted
- **FR-001d**: System MUST analyze fetched webpage content to determine what the page is about
- **FR-001e**: System MUST automatically suggest a title based on webpage content analysis
- **FR-001f**: System MUST automatically suggest relevant keywords (up to 4) based on webpage content analysis
- **FR-001f1**: System MUST store keywords in priority order with the most relevant keyword first
- **FR-001f2**: System MUST prioritize user-specified keywords over automatically generated ones in the keyword order
- **FR-001f3**: System MUST allow saving the same URL multiple times with different keyword sets as separate bookmark entries
- **FR-001f4**: System MUST treat each URL-keyword combination as a distinct bookmark with independent metadata
- **FR-001g**: System MUST allow users to accept, modify, or replace automatically suggested titles and keywords
- **FR-001h**: System MUST handle HTTP errors gracefully when fetching webpage content (404, 500, etc.)
- **FR-001i**: System MUST implement timeouts for webpage fetching to prevent indefinite waiting
- **FR-001j**: System MUST validate URLs before attempting to fetch content
- **FR-001k**: System MUST fetch and store website favicons when saving bookmarks
- **FR-001l**: System MUST store favicons in the storage location in a way that associates them with their bookmarks
- **FR-001m**: System MUST display favicons alongside bookmarks in list and visualization views
- **FR-001n**: System MUST capture screenshots of webpages when saving bookmarks
- **FR-001o**: System MUST allow users to optionally provide their own screenshot images instead of automatic capture
- **FR-001p**: System MUST store screenshots in the storage location and associate them with their bookmarks
- **FR-001p1**: System MUST store independent screenshots for each bookmark entry, even when multiple bookmarks share the same URL
- **FR-001q**: System MUST display screenshots as visual previews when users view bookmark details or hover over bookmarks
- **FR-001r**: System MUST maintain screenshots as reference material even when original URLs become inaccessible
- **FR-002**: System MUST allow users to add an optional description to bookmarks
- **FR-003**: System MUST automatically capture the timestamp when a bookmark is created
- **FR-004**: System MUST allow users to organize bookmarks using folders
- **FR-005**: System MUST allow users to tag bookmarks with multiple tags
- **FR-005a**: System MUST ship with a default storage location configured
- **FR-005b**: System MUST allow users to add multiple named storage locations (e.g., "Work Bookmarks", "Personal Bookmarks")
- **FR-005c**: System MUST suggest "Add storage directories" when only the default storage exists
- **FR-005d**: System MUST validate storage directory paths before adding them
- **FR-005e**: System MUST allow users to designate one storage location as "current" at any given time
- **FR-005f**: System MUST remember the currently selected storage location across sessions
- **FR-005g**: System MUST scope most views (keyword-grouped, filtered) to show bookmarks only from the current storage location
- **FR-005h**: System MUST provide a Global View option that shows bookmarks from all storage locations
- **FR-005i**: System MUST display the storage location as a column in Global View
- **FR-005j**: System MUST allow users to switch between storage locations easily from the interface
- **FR-005k**: System MUST prompt users to select a storage location when saving a new bookmark if multiple locations exist
- **FR-005l**: System MUST default new bookmarks to the current storage location
- **FR-005m**: System MUST allow users to view and manage configured storage locations
- **FR-005n**: System MUST prevent removal of the default storage location
- **FR-005o**: System MUST handle unavailable storage locations gracefully with appropriate error messages
- **FR-006**: System MUST provide three distinct view types for browsing bookmarks
- **FR-006a**: System MUST provide a Global View (Management View) that displays all bookmarks from all storage locations in a table format
- **FR-006b**: System MUST include a storage location column in Global View showing which storage each bookmark belongs to
- **FR-006c**: System MUST allow sorting and filtering in Global View by storage location
- **FR-006d**: System MUST provide a Top Keyword View that groups bookmarks by their highest-priority (first) keyword
- **FR-006e**: System MUST scope Top Keyword View to the current storage location by default
- **FR-006f**: System MUST allow users to toggle Global mode in Top Keyword View to see bookmarks from all storage locations
- **FR-006g**: System MUST show keyword groups with expandable/collapsible sections showing associated bookmarks
- **FR-006h**: System MUST provide a Filtered View for intelligent search and discovery
- **FR-006i**: System MUST use LLM inference in Filtered View to match user queries against bookmark descriptions and keywords
- **FR-006j**: System MUST scope Filtered View to the current storage location by default
- **FR-006k**: System MUST allow users to toggle Global mode in Filtered View to search across all storage locations
- **FR-006l**: System MUST rank search results in Filtered View by semantic relevance
- **FR-006m**: System MUST provide a keyword-grouped browse view that organizes bookmarks by their associated keywords
- **FR-006n**: System MUST display bookmarks under each keyword group they belong to (appearing in multiple groups if they have multiple keywords)
- **FR-006o**: System MUST provide a graph visualization view showing bookmarks as nodes connected to keyword nodes
- **FR-006p**: System MUST make the graph interactive with click/tap interactions on nodes
- **FR-006q**: System MUST provide zoom and pan controls for navigating large graphs
- **FR-006r**: System MUST highlight connections when a node is selected in graph view
- **FR-006s**: System MUST allow users to access bookmark details and URLs from graph nodes
- **FR-007**: System MUST allow users to click on a bookmark to navigate to the saved URL
- **FR-008**: System MUST provide search functionality across bookmark titles, descriptions, URLs, tags, and keywords
- **FR-008a**: System MUST automatically extract keywords from URL paths when a bookmark is saved (up to 4 keywords)
- **FR-008b**: System MUST automatically generate keywords from bookmark descriptions when provided (up to 4 keywords)
- **FR-008c**: System MUST allow users to manually specify keywords when saving or editing bookmarks
- **FR-008d**: System MUST limit the total number of keywords per bookmark to a maximum of 4
- **FR-008e**: System MUST prioritize user-specified keywords over automatically generated ones when the limit is reached
- **FR-008f**: System MUST support keyword-based search with near exact matching
- **FR-008g**: System MUST support semantic search using natural language queries
- **FR-008h**: System MUST return semantically relevant results even when search terms don't exactly match bookmark content
- **FR-008i**: System MUST rank semantic search results by relevance to user intent
- **FR-008j**: System MUST handle ambiguous or general semantic search queries gracefully
- **FR-009**: System MUST allow users to edit bookmark properties (title, description, URL, tags, folder, keywords)
- **FR-009a**: System MUST provide a duplicate detection view that identifies URLs saved multiple times
- **FR-009b**: System MUST group duplicate URLs together and display all bookmark entries for each URL
- **FR-009c**: System MUST show distinguishing information (keywords, title, description, last accessed) for each duplicate entry
- **FR-009d**: System MUST allow users to compare duplicate entries side-by-side to identify differences
- **FR-010**: System MUST soft delete bookmarks by default when users choose to delete them
- **FR-010a**: System MUST mark soft-deleted bookmarks with a deleted flag/status and timestamp
- **FR-010b**: System MUST hide soft-deleted bookmarks from normal views, lists, and search results
- **FR-010c**: System MUST preserve all bookmark data and associated files (favicon, screenshot) for soft-deleted items
- **FR-010d**: System MUST provide a dedicated view to access and browse soft-deleted bookmarks
- **FR-010e**: System MUST allow users to restore soft-deleted bookmarks to active status
- **FR-010f**: System MUST provide a hard delete option that permanently removes bookmarks and associated files
- **FR-010g**: System MUST require explicit confirmation before executing hard delete operations
- **FR-010h**: System MUST display a warning message explaining that hard delete is permanent and irreversible
- **FR-010i**: System MUST provide a bulk hard delete option for cleaning up multiple soft-deleted items
- **FR-010j**: System MUST remove bookmark files, favicons, and screenshots when hard deleting
- **FR-011**: System MUST allow users to create, rename, and delete folders
- **FR-012**: System MUST allow users to move bookmarks between folders
- **FR-013**: System MUST validate URLs to ensure they are properly formatted before saving
- **FR-014**: System MUST support importing bookmarks from standard HTML bookmark format (Netscape Bookmark File Format)
- **FR-015**: System MUST support exporting bookmarks to standard HTML bookmark format
- **FR-016**: System MUST notify users of potential duplicate URLs during import and allow them to choose whether to create separate entries
- **FR-016a**: System MUST recognize that duplicate URLs with different keywords represent distinct bookmarks for different contexts
- **FR-017**: System MUST preserve folder hierarchy when importing and exporting bookmarks
- **FR-018**: System MUST allow users to filter bookmarks by folder
- **FR-019**: System MUST allow users to filter bookmarks by tag
- **FR-020**: System MUST display bookmark metadata (creation date, last modified date, last accessed date)
- **FR-020a**: System MUST record the current timestamp as "last accessed" whenever a user clicks on a bookmark to navigate to its URL
- **FR-020b**: System MUST update the last accessed timestamp atomically without blocking the navigation
- **FR-020c**: System MUST allow users to sort bookmarks by last accessed time
- **FR-020d**: System MUST allow users to filter bookmarks by access recency (e.g., accessed in last 7 days, last 30 days)
- **FR-021**: System MUST prevent deletion of folders containing bookmarks unless explicitly confirmed by user
- **FR-021a**: System MUST move bookmarks to the parent folder when a folder is deleted after user confirmation
- **FR-021b**: System MUST move bookmarks to root level when deleting a top-level folder containing bookmarks
- **FR-021c**: System MUST preserve all bookmark metadata when moving bookmarks during folder deletion
- **FR-022**: System MUST support basic text search with partial matching
- **FR-023**: System MUST persist all bookmark data across sessions
- **FR-023a**: System MUST store each bookmark as a separate YAML file in the file system
- **FR-023b**: System MUST use YAML format for bookmark files to ensure human-readability, diff-friendliness, and multi-client interoperability
- **FR-023c**: System MUST handle concurrent file access gracefully when multiple clients access the same bookmark files
- **FR-023d**: System MUST implement file locking or conflict resolution mechanisms for concurrent writes
- **FR-023e**: System MUST validate bookmark file integrity when reading
- **FR-024**: System MUST provide an HTTP REST API for IDE/editor tools to search bookmarks
- **FR-024a**: System MUST support standard HTTP methods (GET, POST) for API operations
- **FR-024b**: System MUST return responses in JSON format for easy parsing by IDE clients
- **FR-024c**: System MUST provide API endpoints for search, retrieval, and metadata queries
- **FR-025**: System MUST support both keyword and semantic search through the IDE integration interface
- **FR-026**: System MUST return bookmark results with complete metadata (title, URL, description, keywords) through IDE integration
- **FR-027**: System MUST handle connection errors gracefully when accessed from IDE/editor tools
- **FR-028**: System MUST support concurrent access from multiple IDE/editor instances

### Key Entities

#### Bookmark Data Structure

**Critical**: Since multiple clients may read and write bookmark files concurrently, a clear and consistent data structure is essential for data integrity and interoperability.

**Bookmark**: Represents a saved URL stored as an individual file in the file system. Each bookmark file contains:

**Important**: The same URL can be saved multiple times with different keyword sets as separate bookmarks. This allows the same resource to be categorized under different projects or contexts (e.g., the same documentation URL saved with keywords ["azure", "docs"] for one project and ["project-alpha", "reference"] for another). Each URL-keyword combination is treated as a distinct bookmark with independent metadata.

**Required Fields**:
- **URL** (string, required): The complete web address being bookmarked
- **Title** (string, required): A short, descriptive title for the bookmark
- **Creation Timestamp** (datetime, required): When the bookmark was first created
- **Keywords** (ordered list, required): Up to 4 keywords with priority order (first keyword has highest priority)
  - Keywords can be automatically extracted from URL path, webpage content, or user-specified
  - Order matters - first keyword is most important/relevant
  - Empty list is valid if no keywords can be determined
  - Different keyword sets for the same URL create separate bookmark entries

**Optional Fields**:
- **Description/Notes** (string, optional): User's personal notes about what the bookmark was used for, context, or any relevant information
- **Tags** (list of strings, optional): User-defined tags for categorization (separate from keywords)
- **Folder Path** (string, optional): The folder/directory path where this bookmark is organized within the collection
- **Last Modified Timestamp** (datetime, optional): When the bookmark was last edited
- **Favicon** (reference/path, optional): Reference to the website's favicon, stored in the storage location
  - May be stored as separate file alongside bookmark data or embedded
  - Format to be determined during implementation but must be retrievable
- **Screenshot** (reference/path, optional): Reference to a screenshot image of the webpage, stored in the storage location
  - Serves as visual reminder of what the page looks like
  - Helps users identify bookmarks quickly
  - Provides backup hint if the URL becomes broken or inaccessible
  - Can be automatically captured or user-provided
  - Stored as separate image file in storage location
  - Each bookmark entry has its own independent screenshot, even for duplicate URLs (allows capturing page state at different times)

**Data Integrity Requirements**:
- Each bookmark must be stored as a YAML file (human-readable and diff-friendly for version control systems)
- Field names and structure must remain consistent across all bookmark files
- Missing optional fields should be handled gracefully
- Invalid or corrupted YAML files should be detectable without breaking the entire collection
- YAML format provides excellent readability, supports complex nested structures, and has wide tooling support

**Example Structure** (conceptual representation):
```
URL: https://github.com/python/cpython
Title: CPython Official Repository
Keywords: [python, cpython, github, programming]  # ordered by priority
Description: Official Python implementation source code. Used for contributing to Python core and understanding internal implementation details.
Tags: [programming, open-source, python]
Folder: development/python
Created: 2026-02-03T10:30:00Z
Modified: 2026-02-03T14:22:00Z
Last Accessed: 2026-02-04T09:15:30Z
Deleted: false
Deleted Timestamp: null
Favicon: ./favicons/github.com.ico
Screenshot: ./screenshots/github-cpython-2026-02-03.png
```

#### Other Entities

- **Folder**: Represents an organizational container for bookmarks with a name (required), parent folder reference (for nested folders), and creation timestamp. A folder can contain multiple bookmarks and can optionally contain other folders for hierarchical organization
- **Tag**: Represents a label that can be applied to bookmarks for categorization, with a name (required). Tags enable many-to-many relationships where one bookmark can have multiple tags and one tag can be applied to multiple bookmarks
- **Keyword**: Represents an automatically extracted or user-specified term associated with a bookmark for enhanced searchability and organization. Keywords are extracted from URL paths and descriptions, with a maximum of 4 keywords per bookmark, stored in priority order

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can save a new bookmark with title and URL in under 10 seconds
- **SC-002**: Users can find a specific bookmark using search in under 5 seconds
- **SC-003**: System successfully imports standard HTML bookmark files with 95% accuracy (preserving titles, URLs, and folder structure)
- **SC-004**: System handles collections of up to 10,000 bookmarks without performance degradation
- **SC-005**: 90% of users successfully organize their bookmarks using folders or tags within first use
- **SC-006**: Users can access any saved bookmark within 3 clicks from the main view
- **SC-007**: Search returns relevant results in under 1 second for collections up to 10,000 bookmarks
- **SC-008**: System maintains 100% data integrity - no bookmark loss during normal operations
- **SC-009**: System successfully handles concurrent file access from multiple clients with zero data corruption
- **SC-010**: Bookmark files remain readable and valid after being written by any compliant client
- **SC-011**: 99% of bookmark files can be successfully parsed and loaded without errors
- **SC-012**: Export and re-import cycle preserves 100% of bookmark data and organization including keyword priority order
- **SC-013**: 95% of bookmark save operations complete successfully on first attempt
- **SC-014**: Webpage content fetching completes within 5 seconds for 90% of URLs
- **SC-015**: Automatic title and keyword suggestions are generated within 3 seconds after webpage fetch
- **SC-016**: 85% of automatically suggested titles accurately reflect the webpage content
- **SC-017**: 80% of automatically suggested keywords are relevant to the webpage topic
- **SC-018**: Users accept or only minimally modify automatic suggestions 70% of the time
- **SC-019**: System successfully fetches and analyzes 95% of valid, publicly accessible URLs
- **SC-020**: 90% of favicons are successfully retrieved and displayed
- **SC-021**: 85% of screenshots are successfully captured and stored
- **SC-022**: Screenshot capture completes within 10 seconds for 90% of URLs
- **SC-023**: Users report increased confidence in bookmark identification with screenshots 80% of the time
- **SC-024**: Screenshots provide useful visual hints for broken URLs 75% of the time
- **SC-025**: Storage location selection completes within 1 second
- **SC-026**: System correctly remembers current selected storage location 100% of the time across sessions
- **SC-027**: Switching between storage locations updates the view within 2 seconds
- **SC-028**: Global View loads and displays bookmarks from all storage locations within 3 seconds for collections up to 10,000 bookmarks
- **SC-029**: 90% of users successfully configure additional storage locations on first attempt
- **SC-030**: Users can quickly identify which storage a bookmark belongs to in Global View
- **SC-031**: Top Keyword View groups bookmarks correctly by highest-priority keyword 100% of the time
- **SC-032**: Filtered View with LLM inference returns semantically relevant results for 90% of natural language queries
- **SC-033**: Users can toggle between current storage and global search in Filtered/Top Keyword views within 1 second
- **SC-034**: System successfully extracts relevant keywords from 90% of URLs with meaningful path segments
- **SC-035**: Keyword extraction completes within 2 seconds for bookmark save operations
- **SC-036**: 85% of auto-generated keywords are relevant and useful for search (as measured by user search behavior)
- **SC-037**: Keyword priority ranking is preserved correctly in 100% of save/load operations
- **SC-038**: Semantic search returns at least one relevant result for 90% of natural language queries
- **SC-039**: Users find their target bookmark within the top 5 semantic search results 80% of the time
- **SC-040**: Semantic search completes and returns results within 3 seconds for collections up to 10,000 bookmarks
- **SC-041**: 85% of users report that semantic search helps them find bookmarks when they don't remember exact terms
- **SC-042**: Graph visualization loads and becomes interactive within 5 seconds for collections up to 1,000 bookmarks
- **SC-043**: Keyword-grouped browse view organizes and displays bookmarks within 2 seconds
- **SC-044**: 75% of users successfully discover related bookmarks through graph visualization
- **SC-045**: Graph view remains responsive and navigable with smooth zoom/pan interactions
- **SC-046**: Users can identify thematic clusters in their bookmark collection within 30 seconds using graph view
- **SC-047**: IDE/editor bookmark searches return results within 2 seconds
- **SC-048**: IDE integration maintains reliable connection with 99% uptime during active coding sessions
- **SC-049**: 80% of developers report improved workflow efficiency when accessing bookmarks from their IDE
- **SC-050**: IDE search results have the same relevance quality as main application searches
- **SC-051**: Last accessed timestamp is recorded within 500ms of bookmark click 95% of the time
- **SC-052**: Last accessed timestamp updates do not delay or block URL navigation
- **SC-053**: Users can identify their most recently used bookmarks within 5 seconds using sort/filter
- **SC-054**: Last accessed data remains accurate across multiple concurrent client accesses with 99% consistency
- **SC-055**: Users can successfully save the same URL with different keyword sets 100% of the time
- **SC-056**: Each duplicate URL entry maintains independent metadata (title, description, keywords, access times)
- **SC-057**: 90% of users understand that duplicate URLs with different keywords represent different project/context associations
- **SC-058**: Search results correctly distinguish and display multiple entries for the same URL when they match different keywords
- **SC-059**: Duplicate detection view identifies and groups all duplicate URLs within 3 seconds for collections up to 10,000 bookmarks
- **SC-060**: 85% of users successfully identify and manage unwanted duplicates using the duplicate detection view
- **SC-061**: Users can distinguish between duplicate entries based on displayed metadata 90% of the time
- **SC-062**: Soft delete operations complete within 500ms and bookmarks are immediately hidden from normal views
- **SC-063**: Restored bookmarks reappear in normal views within 1 second with all original metadata intact
- **SC-064**: Hard delete confirmation prompts are clear enough that 95% of users understand the operation is permanent
- **SC-065**: Zero data loss occurs from accidental hard deletes when users follow the confirmation workflow
- **SC-066**: 90% of users prefer soft delete as default behavior for providing recovery safety
- **SC-067**: Bulk hard delete operations process 1000+ soft-deleted items within 10 seconds
- **SC-068**: Web server successfully finds and binds to an available port on 99% of startup attempts
- **SC-069**: Users can identify and access the correct server URL within 5 seconds of server start
- **SC-070**: REST API responds to search requests within 500ms for 95% of queries
- **SC-071**: API returns well-formed JSON responses with proper HTTP status codes 100% of the time
- **SC-072**: Folder deletion with bookmark relocation completes within 2 seconds for folders containing up to 100 bookmarks
- **SC-073**: Zero bookmark data loss occurs during folder deletion operations 100% of the time
- **SC-072**: Folder deletion with bookmark relocation completes within 2 seconds for folders containing up to 100 bookmarks
- **SC-073**: Zero bookmark data loss occurs during folder deletion operations 100% of the time
