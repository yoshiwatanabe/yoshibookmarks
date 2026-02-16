/* Content script for extracting capture context from the current page. */

function collectCaptureContext() {
  const title = document.title || "";
  const selection = (window.getSelection && window.getSelection().toString()) || "";
  const bodyText = (document.body && document.body.innerText) || "";
  const excerpt = bodyText.replace(/\s+/g, " ").trim().slice(0, 2000);
  const selectedLinks = collectSelectedLinks(selection);

  return {
    page_title: title,
    selected_text: selection.slice(0, 1000),
    page_excerpt: excerpt,
    selected_links: selectedLinks
  };
}

function collectSelectedLinks(selectionText) {
  const links = [];
  const seen = new Set();

  const sel = window.getSelection && window.getSelection();
  if (sel && sel.rangeCount > 0) {
    for (let i = 0; i < sel.rangeCount; i += 1) {
      const range = sel.getRangeAt(i);
      const fragment = range.cloneContents();
      const anchors = fragment.querySelectorAll ? fragment.querySelectorAll("a[href]") : [];
      anchors.forEach((a) => addUrl(a.href));
    }
  }

  // Also parse plain-text URLs from the selection.
  const regex = /https?:\/\/[^\s<>"')\]]+/gi;
  let match = regex.exec(selectionText || "");
  while (match) {
    addUrl(match[0]);
    match = regex.exec(selectionText || "");
  }

  return links;

  function addUrl(url) {
    try {
      const parsed = new URL(url);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        return;
      }
      const normalized = parsed.toString();
      if (!seen.has(normalized)) {
        seen.add(normalized);
        links.push(normalized);
      }
    } catch (_error) {
      // Ignore invalid URL candidates.
    }
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type !== "YOSHI_COLLECT_CONTEXT") {
    return;
  }

  try {
    const data = collectCaptureContext();
    sendResponse({ ok: true, data });
  } catch (error) {
    sendResponse({ ok: false, error: String(error) });
  }
});
