# FAU.tv Downloader — Chrome Extension Companion 🚀

A lightweight Chrome Extension that integrates directly with [FAU.tv](https://www.fau.tv) to provide **1-click downloads** for lecture videos and complete course series with **automatic session authentication**.

---

## ✨ Features

- **🔑 Zero Manual Cookie Copying**: Automatically extracts your active `das_videoportal_der_fau_session` cookie directly from the browser.
- **📥 Injected On-Page Button**: Adds a native "Download Lecture" / "Download Series" button directly on FAU.tv video and course pages.
- **⚡ 1-Click Cookie Sync**: Save your live browser session cookie into `.env` with a single click.
- **📺 Multi-Stream Selection**: Choose between `Composite` (Slides + Presenter), `Presentation` (Slides only), or `Presenter` (Camera only).
- **📋 Instant CLI Command Copy**: If you prefer running commands manually, the extension generates a ready-to-paste CLI command pre-filled with your current tab URL and active session cookie.
- **📊 Real-Time Activity**: View running downloads and recent download status right from the extension popup.

---

## 🛠️ How to Install (Takes 30 seconds)

### 1. Open Chrome Extension Management
Open your Chromium-based browser (Google Chrome, Brave, Microsoft Edge) and navigate to:
```
chrome://extensions
```
*(In Brave: `brave://extensions` | In Edge: `edge://extensions`)*

### 2. Enable Developer Mode
Toggle the **Developer mode** switch in the top-right corner of the page.

### 3. Load the Extension
1. Click **"Load unpacked"** in the top-left corner.
2. Select the `extension/` folder inside this repository (`fau-tv-downloader/extension`).
3. You'll see **FAU.tv Downloader Companion** appear in your extension list!
4. *(Recommended)* Click the puzzle icon in Chrome's toolbar and pin **FAU.tv Downloader** for quick access.

---

## 🚀 How to Use

### Step 1: Start the Companion Downloader Server
In your terminal, start the local listener in the project directory:
```bash
python3 fau_downloader.py --server
```
*(Or run `python3 fau_server.py`)*

### Step 2: Browse FAU.tv
1. Log in to [FAU.tv](https://www.fau.tv).
2. Open any lecture recording or series page (e.g. Deep Learning, Pattern Recognition).
3. Click the floating green/blue **"Download"** button on the page, or open the extension popup from the toolbar.
4. Click **"Download"** — your local server immediately queues and downloads the lecture via `ffmpeg` in the background!

