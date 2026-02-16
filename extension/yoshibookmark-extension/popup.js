/* Popup workflow: preview -> edit -> commit, plus quick-save. */

let currentPreviewId = null;
let lastCapturePayload = null;

const els = {
  noteInput: document.getElementById("noteInput"),
  linksOnlyCheckbox: document.getElementById("linksOnlyCheckbox"),
  previewBtn: document.getElementById("previewBtn"),
  quickSaveBtn: document.getElementById("quickSaveBtn"),
  commitBtn: document.getElementById("commitBtn"),
  openOptionsBtn: document.getElementById("openOptionsBtn"),
  previewSection: document.getElementById("previewSection"),
  titleInput: document.getElementById("titleInput"),
  keywordsInput: document.getElementById("keywordsInput"),
  tagsInput: document.getElementById("tagsInput"),
  descriptionInput: document.getElementById("descriptionInput"),
  statusBox: document.getElementById("statusBox")
};

els.previewBtn.addEventListener("click", onPreview);
els.quickSaveBtn.addEventListener("click", onQuickSave);
els.commitBtn.addEventListener("click", onCommit);
els.openOptionsBtn.addEventListener("click", () => chrome.runtime.openOptionsPage());

async function onPreview() {
  try {
    setStatus("Collecting page context...");
    const settings = await getSettings();
    const payloads = await buildCapturePayloads(els.linksOnlyCheckbox.checked);
    const payload = payloads[0];
    payload.user_note = els.noteInput.value.trim();
    lastCapturePayload = payload;

    setStatus("Calling /ingest/preview...");
    const preview = await ingestPreview(settings, payload);
    currentPreviewId = preview.preview_id;

    els.titleInput.value = preview.suggested_title || payload.page_title || "";
    els.keywordsInput.value = (preview.suggested_keywords || []).join(", ");
    els.tagsInput.value = (preview.suggested_tags || []).join(", ");
    els.descriptionInput.value = preview.summary || payload.user_note || "";
    els.previewSection.classList.remove("hidden");

    const multiMessage = payloads.length > 1
      ? `\nlinks_selected=${payloads.length} (previewing first link)`
      : "";
    setStatus(
      `Preview ready.\nconfidence=${fmt(preview.confidence)}\n` +
      `dedupe_candidates=${(preview.dedupe_candidates || []).length}` +
      multiMessage
    );
  } catch (error) {
    setStatus(`Preview failed: ${error.message}`);
  }
}

async function onCommit() {
  try {
    if (!currentPreviewId) {
      throw new Error("No preview available. Run Preview first.");
    }

    const settings = await getSettings();
    const payload = {
      preview_id: currentPreviewId,
      title: els.titleInput.value.trim(),
      description: els.descriptionInput.value.trim(),
      keywords: toList(els.keywordsInput.value, 4),
      tags: toList(els.tagsInput.value, 10)
    };

    setStatus("Committing bookmark...");
    const result = await ingestCommit(settings, payload);
    setStatus(`Saved: ${result.bookmark.title}`);
    currentPreviewId = null;
  } catch (error) {
    setStatus(`Commit failed: ${error.message}`);
  }
}

async function onQuickSave() {
  try {
    setStatus("Collecting page context...");
    const settings = await getSettings();
    const payloads = await buildCapturePayloads(els.linksOnlyCheckbox.checked);
    const note = els.noteInput.value.trim();
    payloads.forEach((p) => {
      p.user_note = note;
    });

    let success = 0;
    let failed = 0;
    const titles = [];

    for (const payload of payloads) {
      try {
        const result = await ingestQuickSave(settings, payload);
        success += 1;
        titles.push(result.bookmark.title);
      } catch (_error) {
        failed += 1;
      }
    }

    if (payloads.length === 1 && success === 1) {
      setStatus(`Quick saved: ${titles[0]}`);
      return;
    }
    setStatus(`Quick save completed.\nsuccess=${success}\nfailed=${failed}`);
  } catch (error) {
    setStatus(`Quick save failed: ${error.message}`);
  }
}

async function buildCapturePayloads(linksOnly) {
  const tab = await getActiveTab();
  if (!tab || !tab.id || !tab.url) {
    throw new Error("No active tab available.");
  }

  let capture = await sendContextMessage(tab.id);
  if (!capture) {
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ["content.js"]
    });
    capture = await sendContextMessage(tab.id);
  }

  if (!capture) {
    throw new Error("Could not collect content from page.");
  }

  if (linksOnly) {
    const links = Array.isArray(capture.selected_links) ? capture.selected_links : [];
    if (links.length === 0) {
      throw new Error("No links found in current text selection.");
    }

    return links.map((url) => ({
      url,
      page_title: capture.page_title || tab.title || "",
      page_excerpt: (capture.selected_text || capture.page_excerpt || "").slice(0, 2000),
      selected_text: capture.selected_text || "",
      source_app: "browser-extension",
      source_project: ""
    }));
  }

  return [
    {
      url: tab.url,
      page_title: capture.page_title || tab.title || "",
      page_excerpt: capture.page_excerpt || "",
      selected_text: capture.selected_text || "",
      source_app: "browser-extension",
      source_project: ""
    }
  ];
}

function sendContextMessage(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { type: "YOSHI_COLLECT_CONTEXT" }, (response) => {
      if (chrome.runtime.lastError || !response || !response.ok) {
        resolve(null);
        return;
      }
      resolve(response.data);
    });
  });
}

function getActiveTab() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs && tabs.length ? tabs[0] : null);
    });
  });
}

function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(["apiBaseUrl", "apiToken"], (data) => {
      resolve({
        apiBaseUrl: (data.apiBaseUrl || "http://127.0.0.1:8000").trim(),
        apiToken: (data.apiToken || "").trim()
      });
    });
  });
}

function toList(text, maxItems) {
  return String(text || "")
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean)
    .slice(0, maxItems);
}

function setStatus(message) {
  els.statusBox.textContent = message;
}

function fmt(value) {
  const num = Number(value);
  return Number.isFinite(num) ? num.toFixed(2) : "n/a";
}
