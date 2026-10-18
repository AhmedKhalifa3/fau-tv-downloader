/**
 * FAU.tv Downloader Companion - Content Script
 * Injects on-page download widgets on FAU.tv clip and series pages.
 */

(function () {
  // Prevent duplicate injections
  if (document.getElementById("fau-dl-floating-container")) return;

  const currentUrl = window.location.href;
  const isClip = window.location.pathname.includes("/clip/");
  const isSeries = window.location.pathname.includes("/series/");

  if (!isClip && !isSeries) return;

  const typeName = isSeries ? "Course Series" : "Lecture Video";

  // Create floating container
  const container = document.createElement("div");
  container.id = "fau-dl-floating-container";

  container.innerHTML = `
    <!-- Floating Card Form -->
    <div class="fau-dl-card" id="fau-dl-card">
      <div class="fau-dl-card-header">
        <div class="fau-dl-card-title">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          FAU.tv Downloader
        </div>
        <button class="fau-dl-close" id="fau-dl-close-btn">&times;</button>
      </div>

      <div>
        <span class="fau-dl-type-badge">${isSeries ? "📚 Series Mode" : "🎬 Clip Mode"}</span>
        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;" id="fau-dl-card-slug">
          ${escapeHtml(document.title.split("[ID:")[0].trim() || typeName)}
        </div>
      </div>

      <div class="fau-dl-form-group">
        <label class="fau-dl-label" for="fau-dl-stream-select">Stream View:</label>
        <select class="fau-dl-select" id="fau-dl-stream-select">
          <option value="composite" selected>Composite (Slides + Camera)</option>
          <option value="presentation">Presentation (Slides only)</option>
          <option value="presenter">Presenter (Camera only)</option>
        </select>
      </div>

      <div class="fau-dl-form-group">
        <label class="fau-dl-checkbox-label">
          <input type="checkbox" id="fau-dl-subs-check" checked />
          Download Subtitles (.vtt)
        </label>
      </div>

      <div id="fau-dl-toast" class="fau-dl-toast"></div>

      <button class="fau-dl-btn-primary" id="fau-dl-submit-btn">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        Download ${typeName}
      </button>

      <button class="fau-dl-btn-secondary" id="fau-dl-copy-cmd-btn">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        Copy CLI Command
      </button>
    </div>

    <!-- Floating Action Button -->
    <div class="fau-dl-fab" id="fau-dl-fab" title="Download this ${typeName} with FAU Downloader">
      <div class="fau-dl-fab-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
      </div>
      <div class="fau-dl-fab-text">Download ${isSeries ? "Series" : "Lecture"}</div>
    </div>
  `;

  document.body.appendChild(container);

  // Attempt inline button injection on clip pages
  injectInlineButton();

  // Elements
  const fab = document.getElementById("fau-dl-fab");
  const card = document.getElementById("fau-dl-card");
  const closeBtn = document.getElementById("fau-dl-close-btn");
  const submitBtn = document.getElementById("fau-dl-submit-btn");
  const copyBtn = document.getElementById("fau-dl-copy-cmd-btn");
  const streamSelect = document.getElementById("fau-dl-stream-select");
  const subsCheck = document.getElementById("fau-dl-subs-check");
  const toast = document.getElementById("fau-dl-toast");

  function showToast(type, htmlContent) {
    toast.className = `fau-dl-toast ${type}`;
    toast.innerHTML = htmlContent;
  }

  function toggleCard() {
    card.classList.toggle("active");
  }

  fab.addEventListener("click", toggleCard);
  closeBtn.addEventListener("click", () => card.classList.remove("active"));

  // Download Trigger
  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = `
      <svg class="animate-spin" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
      </svg>
      Connecting...
    `;

    showToast("info", "Sending request to local downloader...");

    try {
      const response = await chrome.runtime.sendMessage({
        type: "START_DOWNLOAD",
        payload: {
          url: window.location.href,
          stream: streamSelect.value,
          subs: subsCheck.checked,
          series: isSeries
        }
      });

      if (response && response.success) {
        showToast("success", `✓ Download queued! Check your terminal or click the extension icon to view status.`);
      } else if (response && response.error === "server_offline") {
        showToast(
          "warning",
          `<strong>Companion server not running!</strong><br>
           Run in your terminal:<br>
           <div class="fau-dl-code-box">python3 fau_downloader.py --server</div>
           Or use the "Copy CLI Command" button below.`
        );
      } else {
        const msg = response?.error || "Could not start download.";
        showToast("error", `⚠️ ${escapeHtml(msg)}`);
      }
    } catch (err) {
      showToast("error", `Error: ${escapeHtml(err.message)}`);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });

  // Copy CLI command with live cookie
  copyBtn.addEventListener("click", async () => {
    const origText = copyBtn.innerHTML;
    copyBtn.innerHTML = "Fetching cookie...";

    try {
      const { cookie } = await chrome.runtime.sendMessage({ type: "GET_COOKIE" });
      const streamVal = streamSelect.value;
      const subsFlag = !subsCheck.checked ? " --no-subs" : "";
      const seriesFlag = isSeries ? " --series" : "";
      const cookieFlag = cookie ? ` --cookie "${cookie}"` : "";

      const cmd = `python3 fau_downloader.py "${window.location.href}"${seriesFlag} --stream ${streamVal}${subsFlag}${cookieFlag}`;

      await navigator.clipboard.writeText(cmd);
      showToast("success", `✓ CLI command copied to clipboard with live session cookie!`);
      copyBtn.innerHTML = "✓ Copied!";
      setTimeout(() => {
        copyBtn.innerHTML = origText;
      }, 2000);
    } catch (err) {
      showToast("error", `Could not copy command: ${escapeHtml(err.message)}`);
      copyBtn.innerHTML = origText;
    }
  });

  function injectInlineButton() {
    const titleElem = document.getElementById("clip-title") || document.querySelector("h1.video-title");
    if (!titleElem) return;

    if (document.getElementById("fau-dl-inline-trigger")) return;

    const inlineBtn = document.createElement("button");
    inlineBtn.id = "fau-dl-inline-trigger";
    inlineBtn.className = "fau-dl-inline-btn";
    inlineBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      Download Video
    `;
    inlineBtn.addEventListener("click", (e) => {
      e.preventDefault();
      card.classList.add("active");
    });

    titleElem.appendChild(inlineBtn);
  }

  function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/[&<>"']/g, function (m) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[m];
    });
  }
})();

