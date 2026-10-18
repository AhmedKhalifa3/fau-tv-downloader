#!/usr/bin/env python3
"""
FAU.tv Downloader Companion Server
==================================
A lightweight, zero-dependency HTTP server that connects the FAU.tv Chrome
Extension to the local Python downloader and ffmpeg.

Allows 1-click downloads directly from your browser, automatic session cookie
syncing to .env, and background download job tracking.

Port: 48123 (default)
"""

import os
import sys
import json
import time
import queue
import urllib.parse
import threading
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional, List

# Import core downloader routines
import fau_downloader

DEFAULT_PORT = 48123
DEFAULT_HOST = "127.0.0.1"

class JobManager:
    """Manages an in-memory queue and history of download jobs."""
    def __init__(self):
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.current_job_id: Optional[str] = None
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def update_env_cookie(self, cookie_val: str):
        """Updates FAU_SESSION_COOKIE in .env and os.environ."""
        if not cookie_val:
            return
        cookie_val = cookie_val.strip().strip("\"'")
        os.environ["FAU_SESSION_COOKIE"] = cookie_val

        # Update or create .env file in project directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(script_dir, ".env")
        lines: List[str] = []
        found = False

        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("FAU_SESSION_COOKIE="):
                            lines.append(f"FAU_SESSION_COOKIE={cookie_val}\n")
                            found = True
                        else:
                            lines.append(line)
            except Exception as e:
                print(f"[!] Warning reading .env: {e}", file=sys.stderr)

        if not found:
            lines.append(f"\nFAU_SESSION_COOKIE={cookie_val}\n")

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            print(f"[✓] Synced fresh session cookie to .env")
        except Exception as e:
            print(f"[!] Warning writing .env: {e}", file=sys.stderr)

    def add_job(self, url: str, cookie: Optional[str] = None, stream: str = "composite",
                series: Optional[bool] = None, subs: bool = True, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Creates and enqueues a new download job."""
        job_id = f"job_{int(time.time() * 1000)}"

        # If cookie provided, persist and update
        if cookie:
            self.update_env_cookie(cookie)

        # Auto-detect series if not explicitly specified
        url_clean = url.strip()
        url_parts = url_clean.rstrip("/").split("/")
        is_series_url = (len(url_parts) == 5 and url_parts[3] == "series")
        if series is None:
            is_series = is_series_url or ("/series/" in url_clean and "/clip/" not in url_clean)
        else:
            is_series = series

        job = {
            "id": job_id,
            "url": url_clean,
            "is_series": is_series,
            "stream": stream or "composite",
            "subs": subs,
            "output_dir": output_dir or os.environ.get("FAU_OUTPUT_DIR", "./downloads"),
            "cookie": cookie or os.environ.get("FAU_SESSION_COOKIE", ""),
            "status": "queued",
            "title": url_parts[-1],
            "progress_message": "Queued in download line...",
            "created_at": time.time(),
            "started_at": None,
            "finished_at": None,
            "error": None
        }

        with self.lock:
            self.jobs[job_id] = job

        self.queue.put(job_id)
        print(f"[+] Enqueued job {job_id} for {url_clean} (series={is_series})")
        return job

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            job = self.jobs.get(job_id)
            return dict(job) if job else None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        with self.lock:
            # Sort by created_at descending
            return sorted(self.jobs.values(), key=lambda j: j.get("created_at", 0), reverse=True)

    def _worker_loop(self):
        """Sequential background worker processing download jobs."""
        while True:
            try:
                job_id = self.queue.get()
                if job_id is None:
                    break

                with self.lock:
                    self.current_job_id = job_id
                    job = self.jobs[job_id]
                    job["status"] = "running"
                    job["started_at"] = time.time()
                    job["progress_message"] = "Initializing download..."

                self._execute_job(job)

                with self.lock:
                    self.current_job_id = None
                self.queue.task_done()
            except Exception as e:
                print(f"[!] Worker unhandled exception: {e}", file=sys.stderr)
                time.sleep(1)

    def _execute_job(self, job: Dict[str, Any]):
        job_id = job["id"]
        url = job["url"]
        cookie = job["cookie"] or os.environ.get("FAU_SESSION_COOKIE", "")
        stream_type = job["stream"]
        download_subs = job["subs"]
        out_dir = job["output_dir"]
        is_series = job["is_series"]

        opener = fau_downloader.build_opener(cookie)

        try:
            if is_series:
                with self.lock:
                    job["progress_message"] = f"Discovering series episodes from {url}..."
                print(f"[*] [Job {job_id}] Fetching series metadata: {url}")
                series_title, episodes = fau_downloader.get_series_info(opener, url)

                with self.lock:
                    job["title"] = series_title
                    job["total_episodes"] = len(episodes)
                    job["completed_episodes"] = 0

                course_dir = os.path.join(out_dir, series_title)
                total = len(episodes)
                if not episodes:
                    raise RuntimeError("No episodes detected on series page.")

                pad_width = len(str(total))
                for idx, (slug, ep_url) in enumerate(episodes, 1):
                    prefix = f"{str(idx).zfill(pad_width)} - "
                    with self.lock:
                        job["progress_message"] = f"Downloading episode [{idx}/{total}]: {slug}"
                        job["current_episode"] = slug

                    print(f"[*] [Job {job_id}] [{idx}/{total}] Processing: {slug}")
                    success = fau_downloader.process_clip(
                        opener=opener,
                        clip_url=ep_url,
                        out_dir=course_dir,
                        stream_type=stream_type,
                        download_subs=download_subs,
                        dry_run=False,
                        prefix=prefix,
                        create_course_dir=False
                    )
                    if not success:
                        print(f"[!] Episode failed or locked: {slug}", file=sys.stderr)

                    with self.lock:
                        job["completed_episodes"] = idx

                with self.lock:
                    job["status"] = "completed"
                    job["progress_message"] = f"Completed all {total} episodes!"
                    job["finished_at"] = time.time()
                print(f"[✓] [Job {job_id}] Series completed successfully: {series_title}")

            else:
                with self.lock:
                    job["progress_message"] = f"Fetching clip metadata..."
                print(f"[*] [Job {job_id}] Fetching clip: {url}")

                # Quick fetch to retrieve title
                try:
                    req = urllib.request.Request(url)
                    resp = opener.open(req)
                    clip_html = resp.read().decode("utf-8")
                    info = fau_downloader.extract_clip_info(clip_html, url)
                    if info.get("title"):
                        with self.lock:
                            job["title"] = info["title"]
                    if info["is_locked"]:
                        raise RuntimeError(f"Access Locked: {info['lock_reason']}. Please ensure you are logged in.")
                except Exception as ex:
                    print(f"[!] Warning pre-fetching clip info: {ex}")

                with self.lock:
                    job["progress_message"] = f"Downloading lecture stream via ffmpeg..."

                success = fau_downloader.process_clip(
                    opener=opener,
                    clip_url=url,
                    out_dir=out_dir,
                    stream_type=stream_type,
                    download_subs=download_subs,
                    dry_run=False,
                    create_course_dir=True
                )
                if not success:
                    raise RuntimeError("Download failed. Check terminal output for details.")

                with self.lock:
                    job["status"] = "completed"
                    job["progress_message"] = "Download completed successfully!"
                    job["finished_at"] = time.time()
                print(f"[✓] [Job {job_id}] Clip completed successfully!")

        except Exception as e:
            err_msg = str(e)
            with self.lock:
                job["status"] = "failed"
                job["error"] = err_msg
                job["progress_message"] = f"Failed: {err_msg}"
                job["finished_at"] = time.time()
            print(f"[!] [Job {job_id}] Error: {err_msg}", file=sys.stderr)

job_manager = JobManager()

class FAURequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Chrome Extension integration."""

    def log_message(self, format, *args):
        # Keep server output clean; only log relevant events
        return

    def _send_cors_headers(self):
        """Sends permissive CORS headers to allow requests from the extension and web origin."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/health", "/status", "/"):
            all_jobs = job_manager.get_all_jobs()
            active_job = None
            if job_manager.current_job_id:
                active_job = job_manager.get_job(job_manager.current_job_id)

            self._send_json_response(200, {
                "status": "online",
                "version": "1.1.0",
                "queue_size": job_manager.queue.qsize(),
                "active_job": active_job,
                "recent_jobs": all_jobs[:10],
                "configured_cookie": bool(os.environ.get("FAU_SESSION_COOKIE"))
            })
            return

        elif path == "/jobs":
            self._send_json_response(200, {
                "jobs": job_manager.get_all_jobs()
            })
            return

        elif path.startswith("/job/"):
            job_id = path[len("/job/"):]
            job = job_manager.get_job(job_id)
            if job:
                self._send_json_response(200, {"job": job})
            else:
                self._send_json_response(404, {"error": "Job not found"})
            return

        self._send_json_response(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(raw_body)
            except Exception:
                self._send_json_response(400, {"error": "Invalid JSON payload"})
                return
        else:
            payload = {}

        if path == "/download":
            url = payload.get("url")
            if not url or not isinstance(url, str):
                self._send_json_response(400, {"error": "Missing or invalid 'url' in request body"})
                return

            cookie = payload.get("cookie")
            stream = payload.get("stream", "composite")
            series = payload.get("series")  # None or bool
            subs = payload.get("subs", True)
            output_dir = payload.get("output_dir")

            job = job_manager.add_job(
                url=url,
                cookie=cookie,
                stream=stream,
                series=series,
                subs=subs,
                output_dir=output_dir
            )

            self._send_json_response(200, {
                "success": True,
                "message": f"Download task queued for {job.get('title')}",
                "job": job
            })
            return

        elif path == "/sync-cookie":
            cookie = payload.get("cookie")
            if not cookie:
                self._send_json_response(400, {"error": "Missing 'cookie' field"})
                return
            job_manager.update_env_cookie(cookie)
            self._send_json_response(200, {
                "success": True,
                "message": "Session cookie updated in .env successfully"
            })
            return

        self._send_json_response(404, {"error": "Unknown endpoint"})

def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    # Ensure .env is loaded initially
    fau_downloader.load_env_file()

    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, FAURequestHandler)
    print("=" * 60)
    print(f" FAU.tv Downloader Companion Server running at:")
    print(f" http://{host}:{port}")
    print(f" Ready for requests from the Chrome Extension.")
    print(f" Press Ctrl+C to stop.")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopping...")
        httpd.server_close()
        print("[✓] Server stopped.")

if __name__ == "__main__":
    port = DEFAULT_PORT
    host = DEFAULT_HOST
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(host=host, port=port)

