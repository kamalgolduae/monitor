"""
Single-run website monitor + HTML generator + Telegram alert.

Meant to be invoked on a schedule by a GitHub Actions workflow (see
.github/workflows/monitor.yml). Each run:
  1. Checks the target URL once.
  2. Appends the result to status_log.txt.
  3. Regenerates index.html from the log.
  4. If the last 3 checks are all Offline, sends a Telegram alert
     (once per streak - it won't spam every run while still down,
     and sends a recovery message when the site comes back).

Env vars (set as GitHub Actions secrets):
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html import escape
from pathlib import Path

# ---- settings ----
URL = "https://www.mantrishop.in/#/pages/wingo1min/index"
ROOT = Path(__file__).parent
LOG_FILE = ROOT / "status_log.txt"
HTML_FILE = ROOT / "index.html"
STATE_FILE = ROOT / "alert_state.json"
MAX_LOG_LINES = 2000
OFFLINE_STREAK_THRESHOLD = 3
# -------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def now_str():
    return datetime.now().strftime("%H:%M:%S")


def check_site():
    try:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return "Online" if resp.status == 200 else f"Online (HTTP {resp.status})"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return "Offline"


def log_status(status):
    line = f"{now_str()}  Site: {status}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) > MAX_LOG_LINES:
        LOG_FILE.write_text("\n".join(lines[-MAX_LOG_LINES:]) + "\n", encoding="utf-8")

    return line


def parse_line(line):
    match = re.match(r"(\d{2}:\d{2}:\d{2})\s+Site:\s+(Online|Offline)", line, re.I)
    if match:
        return {"time": match.group(1), "status": match.group(2).capitalize()}
    return None


def last_n_statuses(lines, n):
    statuses = []
    for line in reversed(lines):
        data = parse_line(line)
        if data:
            statuses.append(data["status"])
        if len(statuses) >= n:
            break
    return statuses  # most recent first


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured (missing secrets), skipping alert")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text}).encode()
    try:
        urllib.request.urlopen(url, data=data, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"alerted": False}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


def generate_html(lines):
    rows = []
    for line in lines[-100:]:
        data = parse_line(line)
        if not data:
            continue
        color = "#22c55e" if data["status"] == "Online" else "#ef4444"
        icon = "\U0001F7E2" if data["status"] == "Online" else "\U0001F534"
        rows.append(f"""
        <tr>
            <td>{escape(data["time"])}</td>
            <td>{icon} <span style="color:{color}">
                {escape(data["status"])}
            </span></td>
        </tr>
        """)

    latest = None
    for line in reversed(lines):
        data = parse_line(line)
        if data:
            latest = data
            break

    if latest:
        status = latest["status"]
        color = "#22c55e" if status == "Online" else "#ef4444"
        icon = "\U0001F7E2" if status == "Online" else "\U0001F534"
    else:
        status = "Unknown"
        color = "#999"
        icon = "⚪"

    rows_html = "".join(reversed(rows))

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="60">
<title>Live Website Monitor</title>
<style>
body {{
    background:#111827;
    color:white;
    font-family:Arial,sans-serif;
    margin:40px;
}}
.container {{
    max-width:900px;
    margin:auto;
}}
.card {{
    background:#1f2937;
    padding:25px;
    border-radius:12px;
    margin-bottom:20px;
}}
.status {{
    font-size:30px;
    font-weight:bold;
    color:{color};
}}
table {{
    width:100%;
    border-collapse:collapse;
}}
td {{
    padding:10px;
    border-bottom:1px solid #374151;
}}
.time {{
    color:#9ca3af;
    width:150px;
}}
</style>
</head>
<body>
<div class="container">
<div class="card">
    <h1>LIVE WEBSITE MONITOR</h1>
    <div class="status">
        {icon} {status}
    </div>
    <p>Last update: {latest["time"] if latest else "N/A"} (checked every ~5 min by GitHub Actions)</p>
    <p>Target: {escape(URL)}</p>
</div>
<div class="card">
    <h2>Activity (most recent first)</h2>
    <table>
        <tr>
            <th align="left">Time</th>
            <th align="left">Status</th>
        </tr>
        {rows_html}
    </table>
</div>
</div>
</body>
</html>
"""
    HTML_FILE.write_text(html, encoding="utf-8")


def main():
    status = check_site()
    log_status(status)
    print(f"{now_str()}  Site: {status}")

    lines = LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    generate_html(lines)

    recent = last_n_statuses(lines, OFFLINE_STREAK_THRESHOLD)
    state = load_state()

    is_down_streak = (
        len(recent) == OFFLINE_STREAK_THRESHOLD
        and all(s == "Offline" for s in recent)
    )

    if is_down_streak:
        if not state.get("alerted"):
            send_telegram(
                f"⚠️ Site DOWN: {OFFLINE_STREAK_THRESHOLD} consecutive "
                f"offline checks for {URL}"
            )
            state["alerted"] = True
            save_state(state)
    else:
        if state.get("alerted"):
            send_telegram(f"✅ Site back ONLINE: {URL}")
        if state.get("alerted") is not False:
            state["alerted"] = False
            save_state(state)


if __name__ == "__main__":
    main()
