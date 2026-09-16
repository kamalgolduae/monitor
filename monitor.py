"""
Simple website live/status monitor.

Checks a URL on a timer and logs:
  - Online / Offline (based on HTTP response)
  - "New content detected" when the page content changes

Usage:
    python monitor.py
"""

import hashlib
import time
import urllib.request
import urllib.error
from datetime import datetime

# ---- settings ----
URL = "https://www.mantrishop.in/#/pages/wingo1min/index"
CHECK_EVERY_SECONDS = 60
LOG_FILE = "status_log.txt"
# -------------------

last_hash = None


def now():
    return datetime.now().strftime("%H:%M:%S")


def log(line):
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check():
    global last_hash

    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            status = "Online" if resp.status == 200 else f"Online (HTTP {resp.status})"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        log(f"{now()}  Site: Offline")
        return

    log(f"{now()}  Site: {status}")

    content_hash = hashlib.sha256(body).hexdigest()
    if last_hash is not None and content_hash != last_hash:
        log(f"{now()}  New content detected")
    last_hash = content_hash


if __name__ == "__main__":
    log(f"Monitoring {URL} every {CHECK_EVERY_SECONDS}s. Press Ctrl+C to stop.")
    while True:
        check()
        time.sleep(CHECK_EVERY_SECONDS)
