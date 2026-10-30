"""
Keep-alive ping daemon for Render web service.
Pings https://salesman-tracker-7ilg.onrender.com/ periodically to prevent spin-down.
"""
import time
import urllib.request
from datetime import datetime

URL = "https://salesman-tracker-7ilg.onrender.com/"
INTERVAL_SECONDS = 15

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Keep-Alive daemon started for {URL}")

while True:
    try:
        t0 = time.time()
        req = urllib.request.Request(URL, headers={"User-Agent": "TraceIt-KeepAlive/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            elapsed = round(time.time() - t0, 2)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Ping OK ({resp.status}) - {elapsed}s")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Ping warning: {e}")

    time.sleep(INTERVAL_SECONDS)

