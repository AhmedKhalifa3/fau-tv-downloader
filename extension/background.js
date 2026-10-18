/**
 * FAU.tv Downloader Companion - Background Service Worker
 * Handles communication with local server, cookie extraction, and notifications.
 */

const DEFAULT_PORT = 48123;
const COOKIE_NAME = "das_videoportal_der_fau_session";

async function getServerConfig() {
  const data = await chrome.storage.local.get({
    serverHost: "127.0.0.1",
    serverPort: DEFAULT_PORT,
    defaultStream: "composite",
    downloadSubs: true
  });
  return data;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 2500) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    return response;
  } finally {
    clearTimeout(id);
  }
}

/**
 * Retrieves the FAU.tv session cookie.
 */
async function getFauSessionCookie() {
  const domains = [
    "https://www.fau.tv",
    "https://fau.tv",
    "http://www.fau.tv"
  ];

  for (const url of domains) {
    try {
      const cookie = await chrome.cookies.get({ url, name: COOKIE_NAME });
      if (cookie && cookie.value) {
        return cookie.value;
      }
    } catch (err) {
      console.warn(`Error getting cookie for ${url}:`, err);
    }
  }

  // Fallback: search all cookies for fau.tv domain
  try {
    const all = await chrome.cookies.getAll({ name: COOKIE_NAME });
    for (const c of all) {
      if (c.domain.includes("fau.tv") && c.value) {
        return c.value;
      }
    }
  } catch (err) {
    console.warn("Error scanning domain cookies:", err);
  }

  return null;
}

/**
 * Checks connection to the local Python downloader server.
 */
async function checkServerStatus() {
  const config = await getServerConfig();
  const url = `http://${config.serverHost}:${config.serverPort}/health`;

  try {
    const resp = await fetchWithTimeout(url, { method: "GET" }, 2000);
    if (resp.ok) {
      const data = await resp.json();
      await updateBadge(true, data.active_job != null);
      return { online: true, data };
    }
  } catch (e) {
    // Server is unreachable
  }

  await updateBadge(false, false);
  return { online: false, data: null };
}

/**
 * Updates extension icon badge to reflect status.
 */
async function updateBadge(isOnline, hasActiveJob) {
  try {
    if (hasActiveJob) {
      await chrome.action.setBadgeText({ text: "DL" });
      await chrome.action.setBadgeBackgroundColor({ color: "#2ecc71" });
    } else if (isOnline) {
      await chrome.action.setBadgeText({ text: "ON" });
      await chrome.action.setBadgeBackgroundColor({ color: "#003865" });
    } else {
      await chrome.action.setBadgeText({ text: "" });
    }
  } catch (e) {
    // Ignore in contexts without action
  }
}

/**
 * Sends a download job to the local companion server.
 */
async function sendDownloadJob({ url, stream, series, subs }) {
  const config = await getServerConfig();
  const cookie = await getFauSessionCookie();

  const targetStream = stream || config.defaultStream || "composite";
  const targetSubs = subs !== undefined ? subs : config.downloadSubs;

  const serverUrl = `http://${config.serverHost}:${config.serverPort}/download`;

  try {
    const response = await fetchWithTimeout(
      serverUrl,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          cookie,
          stream: targetStream,
          series,
          subs: targetSubs
        })
      },
      5000
    );

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errData.error || `Server returned HTTP ${response.status}`,
        cookie
      };
    }

    const result = await response.json();

    // Trigger desktop notification
    try {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "icons/icon-128.png",
        title: "FAU.tv Downloader",
        message: result.message || "Download started in background!"
      });
    } catch (e) {
      // Notification optional
    }

    await updateBadge(true, true);
    return { success: true, result, cookie };
  } catch (e) {
    return {
      success: false,
      error: "server_offline",
      cookie
    };
  }
}

/**
 * Syncs the browser's live cookie directly to the local server's .env file.
 */
async function syncCookieToServer() {
  const cookie = await getFauSessionCookie();
  if (!cookie) {
    return { success: false, error: "No active FAU.tv session cookie found in browser." };
  }

  const config = await getServerConfig();
  const serverUrl = `http://${config.serverHost}:${config.serverPort}/sync-cookie`;

  try {
    const resp = await fetchWithTimeout(
      serverUrl,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cookie })
      },
      3000
    );

    if (resp.ok) {
      return { success: true, cookie };
    }
    return { success: false, error: "Server error updating .env", cookie };
  } catch (e) {
    return { success: false, error: "server_offline", cookie };
  }
}

// Runtime message listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    switch (message.type) {
      case "CHECK_SERVER": {
        const status = await checkServerStatus();
        sendResponse(status);
        break;
      }

      case "GET_COOKIE": {
        const cookie = await getFauSessionCookie();
        sendResponse({ cookie });
        break;
      }

      case "START_DOWNLOAD": {
        const res = await sendDownloadJob(message.payload);
        sendResponse(res);
        break;
      }

      case "SYNC_COOKIE": {
        const res = await syncCookieToServer();
        sendResponse(res);
        break;
      }

      case "GET_CONFIG": {
        const cfg = await getServerConfig();
        sendResponse(cfg);
        break;
      }

      case "SAVE_CONFIG": {
        await chrome.storage.local.set(message.payload);
        sendResponse({ success: true });
        break;
      }

      default:
        sendResponse({ error: "Unknown message type" });
    }
  })();

  return true; // Keep message channel open for async response
});

// Periodic lightweight health check when service worker wakes up
chrome.runtime.onInstalled.addListener(() => {
  checkServerStatus();
});

