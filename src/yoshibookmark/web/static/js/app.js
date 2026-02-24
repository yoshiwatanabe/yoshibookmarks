(() => {
  const searchInput = document.getElementById("searchInput");
  const bookmarksGrid = document.getElementById("bookmarksGrid");
  const emptyState = document.getElementById("emptyState");
  const loading = document.getElementById("loading");
  const totalCount = document.getElementById("totalCount");
  const filterButtons = document.querySelectorAll(".filter-btn");
  const addBookmarkBtn = document.getElementById("addBookmarkBtn");
  const stats = document.getElementById("stats");

  let activeFilter = "all";
  let searchDebounce = null;

  function setLoading(isLoading) {
    loading.style.display = isLoading ? "block" : "none";
  }

  function setEmpty(isEmpty) {
    emptyState.style.display = isEmpty ? "block" : "none";
  }

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function renderRecallResults(payload) {
    const results = payload.results || [];
    totalCount.textContent = String(results.length);
    const mode = payload.mode === "hybrid" ? "Hybrid recall" : "Keyword recall";
    const fallback = payload.fallback_reason
      ? ` | fallback: ${payload.fallback_reason}`
      : "";
    stats.innerHTML = `<span>Total: <strong id="totalCount">${results.length}</strong></span> <span> | ${mode}${fallback}</span>`;

    if (!results.length) {
      bookmarksGrid.innerHTML = "";
      setEmpty(true);
      return;
    }

    setEmpty(false);
    bookmarksGrid.innerHTML = results
      .map((item) => {
        const bookmark = item.bookmark || {};
        const snippet = item.snippet || bookmark.description || "";
        const tags = (bookmark.tags || []).join(", ");
        const keywords = (bookmark.keywords || []).join(", ");
        const score = typeof item.score === "number" ? item.score.toFixed(3) : "-";
        return `
          <article class="bookmark-card">
            <h3><a href="${escapeHtml(bookmark.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(bookmark.title)}</a></h3>
            <p class="bookmark-url">${escapeHtml(bookmark.url || "")}</p>
            <p>${escapeHtml(snippet)}</p>
            <p><strong>Keywords:</strong> ${escapeHtml(keywords)}</p>
            <p><strong>Tags:</strong> ${escapeHtml(tags)}</p>
            <p><strong>Storage:</strong> ${escapeHtml(bookmark.storage_location || "unknown")} | <strong>Score:</strong> ${score}</p>
          </article>
        `;
      })
      .join("");
  }

  function renderBookmarkList(payload) {
    const items = payload.bookmarks || [];
    totalCount.textContent = String(items.length);
    stats.innerHTML = `<span>Total: <strong id="totalCount">${items.length}</strong></span>`;
    if (!items.length) {
      bookmarksGrid.innerHTML = "";
      setEmpty(true);
      return;
    }

    setEmpty(false);
    bookmarksGrid.innerHTML = items
      .map((bookmark) => {
        const description = bookmark.description || "";
        const tags = (bookmark.tags || []).join(", ");
        const keywords = (bookmark.keywords || []).join(", ");
        return `
          <article class="bookmark-card">
            <h3><a href="${escapeHtml(bookmark.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(bookmark.title)}</a></h3>
            <p class="bookmark-url">${escapeHtml(bookmark.url || "")}</p>
            <p>${escapeHtml(description)}</p>
            <p><strong>Keywords:</strong> ${escapeHtml(keywords)}</p>
            <p><strong>Tags:</strong> ${escapeHtml(tags)}</p>
            <p><strong>Storage:</strong> ${escapeHtml(bookmark.storage_location || "unknown")}</p>
          </article>
        `;
      })
      .join("");
  }

  async function fetchBookmarkList() {
    setLoading(true);
    setEmpty(false);

    try {
      const includeDeleted = activeFilter === "deleted";
      const response = await fetch(`/api/v1/bookmarks?include_deleted=${includeDeleted}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      let bookmarks = payload.bookmarks || [];

      if (activeFilter === "recent") {
        bookmarks = bookmarks
          .slice()
          .sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")))
          .slice(0, 20);
      }

      renderBookmarkList({ bookmarks });
    } catch (error) {
      bookmarksGrid.innerHTML = `<p>Failed to load bookmarks: ${escapeHtml(error.message)}</p>`;
      setEmpty(false);
    } finally {
      setLoading(false);
    }
  }

  async function runRecall(query) {
    setLoading(true);
    setEmpty(false);
    try {
      const response = await fetch("/api/v1/recall/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          limit: 20,
          scope: "all",
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      renderRecallResults(payload);
    } catch (error) {
      bookmarksGrid.innerHTML = `<p>Recall failed: ${escapeHtml(error.message)}</p>`;
      setEmpty(false);
    } finally {
      setLoading(false);
    }
  }

  searchInput.addEventListener("input", (event) => {
    const query = event.target.value.trim();
    if (searchDebounce) {
      clearTimeout(searchDebounce);
    }
    searchDebounce = setTimeout(() => {
      if (query.length === 0) {
        fetchBookmarkList();
      } else {
        runRecall(query);
      }
    }, 300);
  });

  for (const button of filterButtons) {
    button.addEventListener("click", () => {
      for (const el of filterButtons) {
        el.classList.remove("active");
      }
      button.classList.add("active");
      activeFilter = button.dataset.filter || "all";
      if (!searchInput.value.trim()) {
        fetchBookmarkList();
      }
    });
  }

  addBookmarkBtn.addEventListener("click", () => {
    window.open("/docs#/bookmarks/create_bookmark_api_v1_bookmarks_post", "_blank", "noopener");
  });

  fetchBookmarkList();
})();
