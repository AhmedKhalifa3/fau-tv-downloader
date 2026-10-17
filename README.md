# FAU.tv Lecture & Series Downloader 🎓📺

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](#features)

A fast, lightweight, zero-dependency Python tool to download public and authenticated lecture recordings and full course series from Friedrich-Alexander-Universität's video portal ([FAU.tv](https://www.fau.tv)) for offline viewing.

---

## ✨ Features

- **🎓 Supports Authenticated Courses**: Seamlessly downloads protected lecture series that require FAU IdM / SSO / StudOn login using your session cookie.
- **⚡ Zero Re-Encoding Loss**: Uses `ffmpeg` stream copying (`-c copy`) to assemble HLS `.m3u8` streams into single `.mp4` files in seconds without loss of video/audio quality.
- **📚 Batch Series Downloads**: Automatically discovers and sequentially downloads all episodes in a course series (e.g., Deep Learning, Pattern Recognition) with clean numeric indexing (`01 - ...`, `02 - ...`).
- **🎥 Multi-Angle Stream Selection**:
  - `composite`: Both lecture slides and lecturer side-by-side (default & recommended).
  - `presentation`: Fullscreen high-resolution slides only.
  - `presenter`: Lecturer camera video only.
- **💬 Automatic Subtitles**: Downloads available auto-generated `.vtt` subtitles with matching filenames so media players like VLC automatically load captions.
- **🔄 Smart Resume**: Skips already downloaded videos if a download is interrupted or when re-running.
- **📦 Zero External Python Dependencies**: Built entirely with Python's standard library (`urllib`, `json`, `argparse`, `re`). No `pip install` required!
- **🔐 Secure `.env` Support**: Built-in support to read your session cookie from `.env` so you don't have to repeatedly pass credentials in command line history.

---

## 🛠️ Prerequisites

### 1. Python 3.8+
Check your Python version:
```bash
python3 --version
```

### 2. FFmpeg
`ffmpeg` is required to download and mux the HLS video fragments into an `.mp4` container.

- **Ubuntu / Debian**:
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```
- **Arch Linux**:
  ```bash
  sudo pacman -S ffmpeg
  ```
- **macOS** (via Homebrew):
  ```bash
  brew install ffmpeg
  ```
- **Windows** (via winget or Chocolatey):
  ```bash
  winget install Gyan.FFmpeg
  ```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/your-username/fau-tv-downloader.git
cd fau-tv-downloader
```

### 2. Configure your session cookie (`.env`)
Copy the template configuration file:
```bash
cp .env.example .env
```

Open `.env` and set `FAU_SESSION_COOKIE` with your cookie value:
```env
FAU_SESSION_COOKIE=eyJpdiI6...
```

#### 🔍 How to get your FAU.tv session cookie (10 seconds)
1. Open your browser and log in to [FAU.tv](https://www.fau.tv).
2. Press `F12` (or right-click $\rightarrow$ **Inspect**) to open Browser Developer Tools.
3. Navigate to:
   - **Chrome / Edge / Brave**: `Application` tab $\rightarrow$ `Cookies` (left sidebar) $\rightarrow$ `https://www.fau.tv`.
   - **Firefox**: `Storage` tab $\rightarrow$ `Cookies` $\rightarrow$ `https://www.fau.tv`.
   - **Safari**: `Storage` tab $\rightarrow$ `Cookies` $\rightarrow$ `fau.tv`.
4. Locate the cookie named **`das_videoportal_der_fau_session`**.
5. Copy its **Value** and paste it into `.env`.

> **Note**: Your `.env` file is automatically ignored by Git in `.gitignore` to keep your credentials private.
>
> **💡 Cookie Freshness Tip**: FAU session cookies expire after idle timeouts or if you log out in your browser. If you ever see an `Access Locked` error, simply log back in to FAU.tv in your browser, copy a fresh cookie, and update `.env`.

---

### 3. Run the Downloader

#### Download an Entire Course Series:
```bash
python3 fau_downloader.py "https://www.fau.tv/series/deep-learning-w20" --series
```

#### Download a Single Episode:
```bash
python3 fau_downloader.py "https://www.fau.tv/series/deep-learning-w20/16-deep-learning-w20"
```

#### Inspect without downloading (`--dry-run`):
```bash
python3 fau_downloader.py "https://www.fau.tv/series/deep-learning-w20" --series --dry-run
```

---

## ⚙️ Command-Line Options

| Argument | Description | Default |
| :--- | :--- | :--- |
| `url` | URL of the clip or series to download | *Required* |
| `--series` | Download all episodes found in the course series | `False` |
| `--cookie` | Session cookie string (overrides `.env`) | Value from `.env` |
| `--cookie-file` | Path to a Netscape `cookies.txt` file | `None` |
| `--stream` | Stream view: `composite`, `presentation`, or `presenter` | `composite` |
| `-o`, `--output-dir` | Base directory for downloads (course subfolder is created inside) | `./downloads` |
| `--flat` | Do not create course subfolders; save directly in output-dir | `False` |
| `--dry-run` | Inspect available episodes and stream URLs without downloading | `False` |
| `--no-subs` | Disable downloading subtitle tracks | `False` |

---

## 🎬 Offline Playback Tips

- **VLC Media Player**: Simply open the downloaded `.mp4` file in [VLC](https://www.videolan.org/vlc/). VLC will automatically detect and load the companion `.vtt` subtitle file in the same directory.
- **mpv**: Run `mpv "01 - 1 - Deep Learning.mp4"` — subtitles and audio tracks are loaded out of the box.

---

## ❓ Troubleshooting & Common Issues

### 1. `[!] Access Locked: Reason: Requires FAU login` (Expired / Stale Cookies)
- **Cause**: FAU.tv session cookies (`das_videoportal_der_fau_session`) have a limited lifespan and expire after idle timeouts or if you log out in your browser.
- **Solution**:
  1. Open [FAU.tv](https://www.fau.tv) in your browser and log in again.
  2. Open Developer Tools (`F12`) $\rightarrow$ **Application / Storage** $\rightarrow$ **Cookies**.
  3. Copy the **fresh** value of `das_videoportal_der_fau_session` and update it in your `.env` file.

### 2. `[!] Access Locked: Reason: Restricted to StudOn course participants`
- **Cause**: The video or course is "kursgebunden" (course-bound). It requires you to be an enrolled member of the specific StudOn course associated with the lecture.
- **Solution**:
  1. Open the course on [StudOn](https://www.studon.fau.de) and join/enroll in it (e.g. click *"Beitreten"*).
  2. **Important**: After enrolling on StudOn, **log out of FAU.tv and log back in** in your browser. This forces FAU.tv to perform a fresh Single Sign-On (SSO) handshake with IdM/StudOn to synchronize your new course permissions.
  3. Copy the newly issued `das_videoportal_der_fau_session` cookie into `.env`.

### 3. Session Invalidation on Browser Logout
- When you click "Abmelden" (Log Out) in your browser, FAU.tv invalidates that session ID server-side. Do not log out in your browser while downloads are queued or running with that session cookie.

---

## ⚖️ Legal & Ethical Usage Guidelines

Before using or contributing to this repository, please review the following legal context regarding copyright law, university terms, and personal educational use:

### 1. The Right to Private Copy (*Recht auf Privatkopie* — § 53 UrhG)
Under **Section 53 of the German Copyright Act (*Urheberrechtsgesetz - UrhG*)**, individuals are legally permitted to make single copies of copyrighted works for **strictly private, non-commercial educational study**, provided that:
- **Lawfully Accessible Source**: You access the media through your own authorized university account via the official portal.
- **No DRM Circumvention (§ 95a UrhG)**: German and EU law prohibit circumventing "effective technical measures" (such as Widevine, PlayReady, or FairPlay encryption). FAU.tv uses standard, unencrypted HTTP Live Streaming (HLS). Authentication checks verify your enrollment status, but the streams themselves are not DRM-encrypted.

### 2. Terms of Use vs. Copyright Law
- **Statutory Law**: Under § 53 UrhG, making a personal backup or offline copy for your own study when internet access is unavailable (e.g. while commuting or traveling) is protected under the private study doctrine.
- **Portal Guidelines**: FAU.tv states in its FAQ that protected media are intended for online viewing. Bypassing the lack of an official download button for personal study is a personal use matter, but must never be used to facilitate wider distribution.

### 3. 🚫 Strict Prohibitions & Red Lines
To ensure compliance with the law and university IT policies:
- ❌ **NO Public Redistribution**: Never upload, mirror, or share downloaded lecture recordings on public hosting services (YouTube, Google Drive, Mega, Telegram, torrents, etc.).
- ❌ **NO Credential Sharing**: Never share or commit your `.env` file, session cookies, or login credentials.
- ❌ **NO Commercial Use**: The tool and downloaded content must only be used for personal, non-commercial academic study.

### 4. 🛡️ Responsible Server Etiquette
- This downloader processes episodes sequentially to respect university server bandwidth.
- Avoid modifying the tool to make aggressive, high-concurrency requests that could degrade service for other students.

---

## 📄 License & Disclaimer

This project is distributed under the [MIT License](LICENSE).

**Disclaimer**: This tool is an independent, open-source project intended solely for personal study and offline viewing by authorized university students. It is neither affiliated with, endorsed by, nor officially connected to Friedrich-Alexander-Universität Erlangen-Nürnberg (FAU) or the Regionales Rechenzentrum Erlangen (RRZE). Users are solely responsible for ensuring their usage complies with all applicable local laws, campus regulations, and institutional guidelines.

