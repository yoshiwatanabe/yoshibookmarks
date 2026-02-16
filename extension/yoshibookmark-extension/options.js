/* Extension options page script. */

const apiBaseUrlInput = document.getElementById("apiBaseUrlInput");
const apiTokenInput = document.getElementById("apiTokenInput");
const saveBtn = document.getElementById("saveBtn");
const testBtn = document.getElementById("testBtn");
const statusBox = document.getElementById("statusBox");

saveBtn.addEventListener("click", onSave);
testBtn.addEventListener("click", onTest);

restore();

async function restore() {
  chrome.storage.sync.get(["apiBaseUrl", "apiToken"], (data) => {
    apiBaseUrlInput.value = data.apiBaseUrl || "http://127.0.0.1:8000";
    apiTokenInput.value = data.apiToken || "";
  });
}

async function onSave() {
  const apiBaseUrl = apiBaseUrlInput.value.trim();
  const apiToken = apiTokenInput.value.trim();
  chrome.storage.sync.set({ apiBaseUrl, apiToken }, () => {
    setStatus("Settings saved.");
  });
}

async function onTest() {
  try {
    const settings = {
      apiBaseUrl: apiBaseUrlInput.value.trim(),
      apiToken: apiTokenInput.value.trim()
    };
    const result = await getProviderStatus(settings);
    const providers = (result.providers || [])
      .map((p) => `${p.provider_id}: enabled=${p.enabled}, model=${p.model}, keys=${p.key_count}`)
      .join("\n");
    setStatus(`Provider status:\n${providers || "(none)"}`);
  } catch (error) {
    setStatus(`Test failed: ${error.message}`);
  }
}

function setStatus(message) {
  statusBox.textContent = message;
}
