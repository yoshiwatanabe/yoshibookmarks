# YoshiBookmark Capture Extension (Private)

Private Chromium MV3 extension for local capture into YoshiBookmark ingestion APIs.

## 5-Minute First Run

1. Initialize YoshiBookmark once (creates `~/.yoshibookmark/config.yaml` and `.env`):
```powershell
yoshibookmark init --storage-mode onedrive-only --onedrive-path "C:\Users\<you>\OneDrive\YoshiBookmark"
```

2. Add both required values to `C:\Users\<you>\.yoshibookmark\.env`:
```env
OPENAI_API_KEY=sk-...
EXTENSION_API_TOKEN=<random-local-secret>
```
   - `OPENAI_API_KEY`: from https://platform.openai.com/api-keys
   - `EXTENSION_API_TOKEN`: local shared secret (not OAuth), generate with:
```powershell
[guid]::NewGuid().ToString("N")
```

3. Start server:
```powershell
yoshibookmark serve --port 8000
```

4. Load extension in browser:
   - Open `chrome://extensions` or `edge://extensions`
   - Turn on **Developer mode**
     - In Edge, this toggle is often in the left pane. Expand/click that pane first if collapsed.
   - Click **Load unpacked**
   - Select `extension/yoshibookmark-extension`

5. Copy Extension ID:
   - Open extension **Details**
   - Copy ID (e.g., `akegejjndolaellmldpmchibfhjcldgi`)

6. Add origin to `config.yaml`:
```yaml
extension_allowed_origins:
  - "chrome-extension://<your-extension-id>"
  - "edge-extension://<your-extension-id>"
```

7. Restart server and configure extension Settings:
   - API Base URL: `http://127.0.0.1:8000`
   - Extension API Token: same as `EXTENSION_API_TOKEN`

8. Click **Test Provider Status** in extension Settings.

## What it does

- Capture current page URL + title + selected text + page excerpt.
- `Preview` flow:
  - Calls `POST /api/v1/ingest/preview`
  - Shows suggested title/keywords/tags/description
  - Lets you edit, then `Save Bookmark` via `POST /api/v1/ingest/commit`
- `Quick Save` flow:
  - Calls `POST /api/v1/ingest/quick-save` directly
- Optional mode: `Capture highlighted links only`
  - If enabled, extension extracts URLs from current text selection.
  - `Quick Save` saves all selected links.
  - `Preview` opens editable preview for the first selected link.

## Backend prerequisites

1. Set token in YoshiBookmark `.env`:

```env
EXTENSION_API_TOKEN=replace-with-random-local-token
```

2. Add extension origin in `config.yaml`:

```yaml
extension_allowed_origins:
  - chrome-extension://<your-extension-id>
```

3. Restart YoshiBookmark server.

## Why Extension ID and Token are needed

- **Extension ID**: Browser origin identifier (`chrome-extension://...` or `edge-extension://...`).
  - Backend uses this in `extension_allowed_origins` (CORS allowlist).
  - Without it, browser blocks extension -> API calls.

- **EXTENSION_API_TOKEN**: Local shared secret.
  - Prevents random local pages/extensions from writing bookmarks to your API.
  - Not OAuth, not cloud identity, and no external provider setup is required.

## Install locally (Chrome/Edge/Brave)

1. Open `chrome://extensions` (or equivalent).
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select this folder: `extension/yoshibookmark-extension`.
5. Open extension `Details` and copy extension ID.
6. Add that ID to `extension_allowed_origins` and restart backend.
7. Open extension `Settings`:
   - `API Base URL`: e.g. `http://127.0.0.1:8000`
   - `Extension API Token`: same as `EXTENSION_API_TOKEN`

## Notes

- This extension is intentionally private and local-use.
- API keys for model providers remain backend-side only.

## Second Machine Setup (OneDrive Sync)

If you run YoshiBookmark on another machine with the same OneDrive data folder:

1. Install and sync OneDrive first.
2. Run:
```powershell
yoshibookmark init --storage-mode onedrive-only --onedrive-path "C:\Users\<you>\OneDrive\Data\yoshibookmark_data"
```
3. Configure that machine's `.env` with `OPENAI_API_KEY` and `EXTENSION_API_TOKEN`.
4. Install this extension again on that machine/browser and get its new extension ID.
5. Add that new origin to that machine's `config.yaml` (`extension_allowed_origins`).
6. Restart server and run:
```powershell
yoshibookmark doctor --api-url http://127.0.0.1:8000
```
