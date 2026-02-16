/* API client for local YoshiBookmark ingestion endpoints. */

async function ingestPreview(settings, payload) {
  return apiRequest(settings, "/api/v1/ingest/preview", "POST", payload);
}

async function ingestCommit(settings, payload) {
  return apiRequest(settings, "/api/v1/ingest/commit", "POST", payload);
}

async function ingestQuickSave(settings, payload) {
  return apiRequest(settings, "/api/v1/ingest/quick-save", "POST", payload);
}

async function getProviderStatus(settings) {
  return apiRequest(settings, "/api/v1/ingest/providers/status", "GET");
}

async function apiRequest(settings, path, method, body) {
  if (!settings || !settings.apiBaseUrl) {
    throw new Error("API base URL is not configured. Open extension options.");
  }

  const base = settings.apiBaseUrl.replace(/\/+$/, "");
  const headers = {
    "Content-Type": "application/json"
  };

  if (settings.apiToken) {
    headers.Authorization = `Bearer ${settings.apiToken}`;
  }

  const response = await fetch(`${base}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = payload.detail || payload.message || response.statusText;
    throw new Error(`API ${response.status}: ${detail}`);
  }

  return payload;
}
