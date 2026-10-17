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
| `-o`, `--output-dir` | Target folder for downloaded `.mp4` and `.vtt` files | `./downloads` |
| `--dry-run` | Inspect available episodes and stream URLs without downloading | `False` |
| `--no-subs` | Disable downloading subtitle tracks | `False` |

---

## 🎬 Offline Playback Tips

- **VLC Media Player**: Simply open the downloaded `.mp4` file in [VLC](https://www.videolan.org/vlc/). VLC will automatically detect and load the companion `.vtt` subtitle file in the same directory.
- **mpv**: Run `mpv "01 - 1 - Deep Learning.mp4"` — subtitles and audio tracks are loaded out of the box.

---

## ⚖️ Disclaimer & License

This tool is created solely for personal educational use and offline studying by authorized students and staff. Ensure compliance with FAU's usage guidelines and data policies.

Distributed under the [MIT License](LICENSE).

