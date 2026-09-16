import re
import time
from pathlib import Path
from html import escape

# =========================
# CONFIGURATION
# =========================
TXT_FILE = Path(r"C:\Users\JUNAID CK\OneDrive\Desktop\monitor\status_log.txt")
HTML_FILE = Path(r"C:\Users\JUNAID CK\OneDrive\Desktop\monitor\status.html")

CHECK_INTERVAL = 1  # seconds


def parse_line(line):
    """
    Example:
    13:50:01  Site: Online
    """
    match = re.match(r"(\d{2}:\d{2}:\d{2})\s+Site:\s+(Online|Offline)", line, re.I)

    if match:
        return {
            "time": match.group(1),
            "status": match.group(2).capitalize()
        }

    return None


def generate_html(lines):
    rows = []

    # Show latest 100 entries
    for line in lines[-100:]:
        data = parse_line(line)

        if not data:
            continue

        color = "#22c55e" if data["status"] == "Online" else "#ef4444"
        icon = "🟢" if data["status"] == "Online" else "🔴"

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
        icon = "🟢" if status == "Online" else "🔴"
    else:
        status = "Unknown"
        color = "#999"
        icon = "⚪"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="2">

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

    <p>Last update: {latest["time"] if latest else "N/A"}</p>
</div>

<div class="card">
    <h2>Activity</h2>

    <table>
        <tr>
            <th align="left">Time</th>
            <th align="left">Status</th>
        </tr>

        {"".join(rows)}
    </table>
</div>

</div>

</body>
</html>
"""

    HTML_FILE.write_text(html, encoding="utf-8")


def main():
    print("Live TXT → HTML monitor started")
    print(f"TXT:  {TXT_FILE}")
    print(f"HTML: {HTML_FILE}")

    last_size = 0

    while True:
        try:
            if TXT_FILE.exists():

                size = TXT_FILE.stat().st_size

                if size != last_size:
                    text = TXT_FILE.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )

                    lines = text.splitlines()

                    generate_html(lines)

                    last_size = size

                    print(
                        f"Updated HTML: "
                        f"{time.strftime('%H:%M:%S')}"
                    )

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopped.")
            break

        except Exception as e:
            print("Error:", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
