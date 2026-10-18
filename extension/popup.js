/**
 * FAU.tv Downloader Companion - Popup Logic
 */

let currentTab = null;
let currentCookie = null;
let isServerOnline = false;

document.addEventListener("DOMContentLoaded", async () => {
  // Elements
  const serverPill = document.getElementById("server-status-pill");
  const serverText = document.getElementById("server-status-text");
  const pageBadge = document.getElementById("page-type-badge");
  const pageTitle = document.getElementById("page-title");
  const fauControls = document.getElementById("fau-action-controls");
  const notFauPrompt = document.getElementById("not-fau-prompt");
  const downloadBtn = document.getElementById("download-btn");
  const downloadBtnText = document.getElementById("download-btn-text");
  const copyCmdBtn = document.getElementById("copy-cmd-btn");
  const streamSelect = document.getElementById("stream-select");
  const subsCheckbox = document.getElementById("subs-checkbox");
  const cookieBadge = document.getElementById("cookie-status-badge");
  const cookieDesc = document.getElementById("cookie-status-desc");
  const copyCookieBtn = document.getElementById("copy-cookie-btn");
  const syncCookieBtn = document.getElementById("sync-cookie-btn");
  const activityContent = document.getElementById("activity-content");
  const offlineBanner = document.getElementById("offline-banner");
  const refreshJobsBtn = document.getElementById("refresh-jobs-btn");
  const copyServerCmdBtn = document.getElementById("copy-server-cmd-btn");
  const toggleSettingsBtn = document.getElementById("toggle-settings-btn");
  const settingsPanel = document.getElementById("settings-panel");
  const serverPortInput = document.getElementById("server-port-input");
  const saveSettingsBtn = document.getElementById("save-settings-btn");
  const popupToast = document.getElementById("popup-toast");

  function showToast(msg, type = "success") {
    popupToast.className = `toast show ${type}`;
    popupToast.textContent = msg;
    setTimeout(() => {
      popupToast.className = "toast";
    }, 2500);
  }

  // Load saved settings
  const config = await chrome.runtime.sendMessage({ type: "GET_CONFIG" });
  if (config && config.serverPort) {
    serverPortInput.value = config.serverPort;
    if (config.defaultStream) streamSelect.value = config.defaultStream;
    if (config.downloadSubs !== undefined) subsCheckbox.checked = config.downloadSubs;
  }

  // 1. Inspect Current Tab
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    currentTab = tabs[0];

    if (currentTab && currentTab.url) {
      const url = currentTab.url;
      const isClip = url.includes("fau.tv") && url.includes("/clip/");
      const isSeries = url.includes("fau.tv") && url.includes("/series/");

      if (isClip || isSeries) {
        fauControls.style.display = "block";
        notFauPrompt.style.display = "none";

        pageBadge.className = "badge info";
        pageBadge.textContent = isSeries ? "Series" : "Lecture Clip";
        downloadBtnText.textContent = isSeries ? "Download Series" : "Download Video";

        const cleanTitle = currentTab.title ? currentTab.title.split("[ID:")[0].trim() : url;
        pageTitle.textContent = cleanTitle;
      } else {
        fauControls.style.display = "none";
        notFauPrompt.style.display = "block";
        pageBadge.className = "badge";
        pageBadge.textContent = "Not FAU.tv";
        pageTitle.textContent = currentTab.title || "External Tab";
      }
    }
  } catch (err) {
    console.error("Error inspecting tab:", err);
  }

  // 2. Check Cookie Status
  async function refreshCookieStatus() {
    try {
      const res = await chrome.runtime.sendMessage({ type: "GET_COOKIE" });
      currentCookie = res ? res.cookie : null;

      if (currentCookie) {
        cookieBadge.className = "badge success";
        cookieBadge.textContent = "Active Session";
        cookieDesc.textContent = "FAU.tv session cookie detected and ready.";
      } else {
        cookieBadge.className = "badge warning";
        cookieBadge.textContent = "Not Detected";
        cookieDesc.textContent = "Please log in to FAU.tv in your browser.";
      }
    } catch (e) {
      cookieBadge.className = "badge warning";
      cookieBadge.textContent = "Check Failed";
    }
  }

  // 3. Check Server Status & Recent Jobs
  async function refreshServerStatus() {
    try {
      const res = await chrome.runtime.sendMessage({ type: "CHECK_SERVER" });
      isServerOnline = res && res.online;

      if (isServerOnline) {
        const port = serverPortInput.value || "48123";
        serverPill.className = "status-pill online";
        serverText.textContent = `Online (:${port})`;
        offlineBanner.style.display = "none";

        const data = res.data;
        renderActivity(data);
      } else {
        serverPill.className = "status-pill offline";
        serverText.textContent = "Offline";
        offlineBanner.style.display = "block";
        activityContent.innerHTML = `<div class="loading-text">Server offline. Run command above to start.</div>`;
      }
    } catch (e) {
      serverPill.className = "status-pill offline";
      serverText.textContent = "Offline";
      offlineBanner.style.display = "block";
    }
  }

  function renderActivity(data) {
    if (!data) return;

    const activeJob = data.active_job;
    const recent = data.recent_jobs || [];

    if (!activeJob && recent.length === 0) {
      activityContent.innerHTML = `<div class="loading-text">No active or recent downloads.</div>`;
      return;
    }

    let html = "";
    if (activeJob) {
      html += `
        <div class="job-item">
          <div class="job-top-row">
            <span class="job-title" title="${escapeHtml(activeJob.title || activeJob.url)}">
              ⏳ ${escapeHtml(activeJob.title || "Downloading...")}
            </span>
            <span class="badge info">Running</span>
          </div>
          <div class="job-msg">${escapeHtml(activeJob.progress_message || "In progress...")}</div>
        </div>
      `;
    }

    const completed = recent.filter(j => !activeJob || j.id !== activeJob.id).slice(0, 3);
    for (const job of completed) {
      const isFailed = job.status === "failed";
      const isDone = job.status === "completed";
      const badgeClass = isFailed ? "warning" : (isDone ? "success" : "badge");
      const icon = isFailed ? "❌" : "✓";

      html += `
        <div class="job-item">
          <div class="job-top-row">
            <span class="job-title" title="${escapeHtml(job.title || job.url)}">
              ${icon} ${escapeHtml(job.title || "Lecture")}
            </span>
            <span class="badge ${badgeClass}">${job.status}</span>
          </div>
          <div class="job-msg">${escapeHtml(job.progress_message || "")}</div>
        </div>
      `;
    }

    activityContent.innerHTML = html;
  }

  // Initial loads
  await refreshCookieStatus();
  await refreshServerStatus();

  // Button Listeners
  downloadBtn.addEventListener("click", async () => {
    if (!currentTab || !currentTab.url) return;

    downloadBtn.disabled = true;
    const orig = downloadBtnText.textContent;
    downloadBtnText.textContent = "Sending...";

    const isSeries = currentTab.url.includes("/series/");
    const res = await chrome.runtime.sendMessage({
      type: "START_DOWNLOAD",
      payload: {
        url: currentTab.url,
        stream: streamSelect.value,
        subs: subsCheckbox.checked,
        series: isSeries
      }
    });

    downloadBtn.disabled = false;
    downloadBtnText.textContent = orig;

    if (res && res.success) {
      showToast("✓ Download queued successfully!", "success");
      await refreshServerStatus();
    } else if (res && res.error === "server_offline") {
      showToast("⚠️ Companion server is offline!", "error");
      await refreshServerStatus();
    } else {
      showToast(`Error: ${res?.error || "Failed"}`, "error");
    }
  });

  copyCmdBtn.addEventListener("click", async () => {
    if (!currentTab || !currentTab.url) return;

    const streamVal = streamSelect.value;
    const subsFlag = !subsCheckbox.checked ? " --no-subs" : "";
    const isSeries = currentTab.url.includes("/series/");
    const seriesFlag = isSeries ? " --series" : "";
    const cookieFlag = currentCookie ? ` --cookie "${currentCookie}"` : "";

    const cmd = `python3 fau_downloader.py "${currentTab.url}"${seriesFlag} --stream ${streamVal}${subsFlag}${cookieFlag}`;
    await navigator.clipboard.writeText(cmd);
    showToast("✓ Command copied to clipboard!");
  });

  copyCookieBtn.addEventListener("click", async () => {
    if (!currentCookie) {
      showToast("No active cookie found. Log in first.", "error");
      return;
    }
    await navigator.clipboard.writeText(currentCookie);
    showToast("✓ Session cookie copied!");
  });

  syncCookieBtn.addEventListener("click", async () => {
    const res = await chrome.runtime.sendMessage({ type: "SYNC_COOKIE" });
    if (res && res.success) {
      showToast("✓ Synced fresh cookie to local .env!");
    } else if (res && res.error === "server_offline") {
      showToast("Companion server is offline.", "error");
    } else {
      showToast(`Failed: ${res?.error || "Unknown error"}`, "error");
    }
  });

  refreshJobsBtn.addEventListener("click", async () => {
    await refreshServerStatus();
    await refreshCookieStatus();
    showToast("Refreshed!");
  });

  copyServerCmdBtn.addEventListener("click", async () => {
    await navigator.clipboard.writeText("python3 fau_downloader.py --server");
    showToast("✓ Server command copied!");
  });

  toggleSettingsBtn.addEventListener("click", () => {
    const isShown = settingsPanel.style.display !== "none";
    settingsPanel.style.display = isShown ? "none" : "block";
  });

  saveSettingsBtn.addEventListener("click", async () => {
    const port = parseInt(serverPortInput.value, 10) || 48123;
    await chrome.runtime.sendMessage({
      type: "SAVE_CONFIG",
      payload: {
        serverPort: port,
        defaultStream: streamSelect.value,
        downloadSubs: subsCheckbox.checked
      }
    });
    showToast("Settings saved!");
    settingsPanel.style.display = "none";
    await refreshServerStatus();
  });

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
});

