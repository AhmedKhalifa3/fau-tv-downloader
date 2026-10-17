#!/usr/bin/env python3
"""
FAU.tv Lecture & Series Downloader
===================================
A lightweight, zero-dependency Python tool to download public and authenticated
lecture recordings and series from the FAU.tv video portal for offline viewing.

Repository: https://github.com/your-username/fau-tv-downloader
License: MIT
"""

import os
import re
import sys
import html
import json
import argparse
import subprocess
import urllib.request
import urllib.parse
from typing import List, Dict, Optional, Tuple

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

def load_env_file(env_path: Optional[str] = None):
    """Loads key-value pairs from .env into os.environ without third-party dependencies."""
    candidates = []
    if env_path:
        candidates.append(env_path)
    else:
        # Check current working directory, then script directory
        candidates.append(os.path.join(os.getcwd(), ".env"))
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(script_dir, ".env"))

    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("\"'")
                            if key and key not in os.environ:
                                os.environ[key] = val
                break
            except Exception as e:
                print(f"[!] Warning: Could not read {path}: {e}", file=sys.stderr)

def build_opener(cookie_str: Optional[str] = None) -> urllib.request.OpenerDirector:
    """Builds a urllib opener configured with User-Agent and session cookie."""
    headers = [("User-Agent", USER_AGENT)]
    if cookie_str:
        cookie_str = cookie_str.strip().strip("\"'")
        if cookie_str:
            # If user provided raw token without key name
            if "=" not in cookie_str:
                cookie_str = f"das_videoportal_der_fau_session={cookie_str}"
            headers.append(("Cookie", cookie_str))
    
    opener = urllib.request.build_opener()
    opener.addheaders = headers
    return opener

def sanitize_filename(name: str) -> str:
    """Sanitizes strings to be safe for filenames across Linux, macOS, and Windows."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', " ", name).strip()
    return name

def extract_clip_info(page_html: str, clip_url: str) -> Dict:
    """Extracts media stream URLs, title, and subtitles from a clip's HTML page."""
    info = {
        "url": clip_url,
        "title": None,
        "streams": {},
        "captions": [],
        "is_locked": False,
        "lock_reason": None
    }
    
    # Check access lock indicators
    if "Dieser Clip ist ausschließlich für angemeldete Benutzer zugänglich" in page_html:
        info["is_locked"] = True
        info["lock_reason"] = "Requires FAU login (angemeldete Benutzer)"
    elif "Der Zugang zu diesem Clip ist auf StudOn-Kursteilnehmer beschränkt" in page_html:
        info["is_locked"] = True
        info["lock_reason"] = "Restricted to StudOn course participants"
    elif "clip player preview" in page_html and "<mediaPlayer" not in page_html:
        info["is_locked"] = True
        info["lock_reason"] = "Access restricted / session not authenticated"

    # Extract title
    title_match = re.search(r'id="clip-title"[^>]*>[\s\S]*?<span>(.*?)</span>', page_html)
    if title_match:
        raw_title = title_match.group(1).strip()
        info["title"] = sanitize_filename(html.unescape(raw_title))
    else:
        title_tag = re.search(r'<title>(.*?)</title>', page_html)
        if title_tag:
            clean = title_tag.group(1).split("[ID:")[0].strip()
            info["title"] = sanitize_filename(html.unescape(clean))
    
    if not info["title"]:
        info["title"] = clip_url.rstrip("/").split("/")[-1]

    # Extract primary stream from <mediaPlayer ... src="...">
    player_match = re.search(r'<mediaPlayer[^>]*\bsrc="([^"]+)"', page_html, re.I)
    if player_match:
        src = html.unescape(player_match.group(1))
        info["streams"]["composite"] = src
    
    # Extract alternative stream views (presentation, presenter, composite)
    stream_links = re.findall(r'href="([^"]*stream\.fau\.tv[^"]+)"[^>]*title="([^"]*)"', page_html)
    for s_url, s_title in stream_links:
        s_url = html.unescape(s_url)
        s_title_lower = s_title.lower()
        if "präsentations" in s_title_lower or "presentation" in s_title_lower:
            info["streams"]["presentation"] = s_url
        elif "präsentator" in s_title_lower or "presenter" in s_title_lower:
            info["streams"]["presenter"] = s_url
        elif "composite" in s_title_lower:
            info["streams"]["composite"] = s_url

    # Fallback scan for any direct stream.fau.tv links
    if not info["streams"]:
        raw_stream_links = re.findall(r'href="([^"]*stream\.fau\.tv[^"]+)"', page_html)
        for s_url in raw_stream_links:
            s_url = html.unescape(s_url)
            if "presentation.smil" in s_url:
                info["streams"]["presentation"] = s_url
            elif "presenter.smil" in s_url:
                info["streams"]["presenter"] = s_url
            elif "composite.smil" in s_url:
                info["streams"]["composite"] = s_url
            else:
                info["streams"].setdefault("stream", s_url)

    # Extract subtitle / caption tracks
    caption_match = re.search(r'data-caption-tracks=\'([^\']+)\'', page_html)
    if caption_match:
        try:
            tracks = json.loads(caption_match.group(1))
            for track in tracks:
                if "src" in track:
                    info["captions"].append({
                        "src": html.unescape(track["src"]),
                        "lang": track.get("srclang", "en"),
                        "label": track.get("label", "Subtitles")
                    })
        except Exception:
            pass

    return info

def get_series_episodes(opener: urllib.request.OpenerDirector, series_url: str) -> List[Tuple[str, str]]:
    """Extracts all episode URLs from a series page in chronological sequence."""
    parts = series_url.rstrip("/").split("/")
    if len(parts) > 5 and parts[3] == "series":
        base_series_url = "/".join(parts[:5])
    else:
        base_series_url = series_url

    req = urllib.request.Request(base_series_url)
    resp = opener.open(req)
    series_html = resp.read().decode("utf-8")

    pattern = rf'href="({re.escape(base_series_url)}/[a-zA-Z0-9_\-]+)"'
    found_urls = re.findall(pattern, series_html)
    
    episodes = []
    seen = set()
    for ep_url in found_urls:
        if "/feed/" in ep_url or ep_url in seen or ep_url == base_series_url:
            continue
        seen.add(ep_url)
        slug = ep_url.split("/")[-1]
        episodes.append((slug, ep_url))

    # Sort numerically by leading episode number in slug
    def sort_key(item):
        m = re.match(r'^(\d+)', item[0])
        return int(m.group(1)) if m else 999999

    episodes.sort(key=sort_key)
    return episodes

def download_stream(stream_url: str, output_path: str) -> bool:
    """Uses ffmpeg to download the HLS stream losslessly without re-encoding."""
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-stats",
        "-i", stream_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        output_path
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Error during ffmpeg download: {e}", file=sys.stderr)
        return False

def download_file(opener: urllib.request.OpenerDirector, url: str, output_path: str) -> bool:
    """Downloads a raw file (e.g. VTT subtitle track)."""
    try:
        req = urllib.request.Request(url)
        with opener.open(req) as resp, open(output_path, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"\n[!] Failed to download file from {url}: {e}", file=sys.stderr)
        return False

def process_clip(
    opener: urllib.request.OpenerDirector,
    clip_url: str,
    out_dir: str,
    stream_type: str = "composite",
    download_subs: bool = True,
    dry_run: bool = False,
    prefix: str = ""
) -> bool:
    """Processes a single clip: extracts streams, checks access, and downloads."""
    try:
        req = urllib.request.Request(clip_url)
        resp = opener.open(req)
        clip_html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"[!] Failed to fetch {clip_url}: {e}")
        return False

    info = extract_clip_info(clip_html, clip_url)

    if info["is_locked"]:
        print(f"[!] Access Locked: '{info['title']}' ({clip_url})")
        print(f"    Reason: {info['lock_reason']}")
        print("    -> Add your session cookie to .env (FAU_SESSION_COOKIE) or pass --cookie.")
        return False

    streams = info["streams"]
    if not streams:
        print(f"[!] No playable streams detected for '{info['title']}' ({clip_url})")
        return False

    chosen_stream = streams.get(stream_type)
    if not chosen_stream:
        chosen_stream = streams.get("composite") or next(iter(streams.values()))

    filename_base = f"{prefix}{info['title']}" if prefix else info["title"]
    mp4_name = f"{filename_base}.mp4"
    mp4_path = os.path.join(out_dir, mp4_name)

    print(f"\n[+] Title: {info['title']}")
    print(f"    Available streams: {', '.join(streams.keys())}")
    print(f"    Selected stream: {stream_type}")
    print(f"    Target path: {mp4_path}")

    if dry_run:
        print("    [Dry-run] Skipping download.")
        return True

    os.makedirs(out_dir, exist_ok=True)

    if os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 1024:
        print(f"    [SKIP] Already exists: {mp4_name}")
    else:
        print(f"    Downloading stream via ffmpeg...")
        success = download_stream(chosen_stream, mp4_path)
        if not success:
            return False
        print(f"    [✓] Video downloaded successfully: {mp4_name}")

    if download_subs and info["captions"]:
        for cap in info["captions"]:
            lang = cap.get("lang", "en")
            vtt_name = f"{filename_base}.{lang}.vtt"
            vtt_path = os.path.join(out_dir, vtt_name)
            if not os.path.exists(vtt_path):
                print(f"    Downloading subtitles ({lang})...")
                download_file(opener, cap["src"], vtt_path)
                print(f"    [✓] Subtitles saved: {vtt_name}")

    return True

def main():
    # Load .env file automatically
    load_env_file()

    env_cookie = os.environ.get("FAU_SESSION_COOKIE") or os.environ.get("DAS_VIDEOPORTAL_DER_FAU_SESSION")
    env_out_dir = os.environ.get("FAU_OUTPUT_DIR", "./downloads")
    env_stream = os.environ.get("FAU_STREAM_TYPE", "composite")
    env_subs = os.environ.get("FAU_DOWNLOAD_SUBS", "true").lower() in ("true", "1", "yes")

    parser = argparse.ArgumentParser(
        description="Download FAU.tv lectures and complete course series for offline viewing."
    )
    parser.add_argument(
        "url",
        help="URL of the video clip or series (e.g. https://www.fau.tv/series/deep-learning-w20)"
    )
    parser.add_argument(
        "--series",
        action="store_true",
        help="Download all episodes in the series"
    )
    parser.add_argument(
        "--cookie",
        default=env_cookie,
        help="Value of 'das_videoportal_der_fau_session' or raw cookie string (defaults to .env value)"
    )
    parser.add_argument(
        "--cookie-file",
        help="Path to Netscape-format cookies.txt file"
    )
    parser.add_argument(
        "--stream",
        choices=["composite", "presentation", "presenter"],
        default=env_stream,
        help="Preferred stream view (composite, presentation, presenter). Default: %(default)s"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=env_out_dir,
        help="Directory to save downloads (default: %(default)s)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List episodes and stream details without downloading"
    )
    parser.add_argument(
        "--no-subs",
        action="store_true",
        default=not env_subs,
        help="Do not download subtitles"
    )

    args = parser.parse_args()

    # Cookie precedence: --cookie-file > --cookie / .env
    cookie_str = args.cookie
    if args.cookie_file and os.path.isfile(args.cookie_file):
        with open(args.cookie_file, "r", encoding="utf-8") as f:
            for line in f:
                if "das_videoportal_der_fau_session" in line:
                    parts = line.strip().split("\t")
                    if len(parts) >= 7:
                        cookie_str = f"das_videoportal_der_fau_session={parts[6]}"
                        break

    opener = build_opener(cookie_str)

    # Verify ffmpeg is available
    if not args.dry_run:
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except Exception:
            print("Error: 'ffmpeg' is required to assemble HLS video streams.", file=sys.stderr)
            print("Install ffmpeg via your package manager (e.g. sudo apt install ffmpeg).", file=sys.stderr)
            sys.exit(1)

    url = args.url.strip()
    is_series = args.series or ("/series/" in url and url.count("/") <= 5)

    try:
        if is_series:
            print(f"[*] Discovering series episodes from: {url}")
            episodes = get_series_episodes(opener, url)
            print(f"[*] Found {len(episodes)} episodes.")
            if not episodes:
                print("[!] No episodes detected. Check the URL or provide an individual clip URL.")
                sys.exit(1)

            total = len(episodes)
            pad_width = len(str(total))
            for idx, (slug, ep_url) in enumerate(episodes, 1):
                prefix = f"{str(idx).zfill(pad_width)} - "
                print(f"\n==========================================")
                print(f"[{idx}/{total}] Processing: {slug}")
                print(f"==========================================")
                process_clip(
                    opener=opener,
                    clip_url=ep_url,
                    out_dir=args.output_dir,
                    stream_type=args.stream,
                    download_subs=not args.no_subs,
                    dry_run=args.dry_run,
                    prefix=prefix
                )
        else:
            print(f"[*] Processing single clip: {url}")
            process_clip(
                opener=opener,
                clip_url=url,
                out_dir=args.output_dir,
                stream_type=args.stream,
                download_subs=not args.no_subs,
                dry_run=args.dry_run
            )
    except KeyboardInterrupt:
        print("\n\n[!] Download canceled by user.")
        sys.exit(130)

if __name__ == "__main__":
    main()
