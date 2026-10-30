import os
import threading
import time
import urllib.request
from app import create_app

app = create_app()

def self_ping_worker():
    """Background worker that pings the Render URL every 10 minutes to prevent container sleep."""
    ping_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://salesman-tracker-7ilg.onrender.com/')
    time.sleep(30)  # Initial grace period while the app initializes
    while True:
        try:
            req = urllib.request.Request(ping_url, headers={'User-Agent': 'Render-SelfPing/1.0'})
            with urllib.request.urlopen(req, timeout=20) as resp:
                print(f"[Self-Ping] {ping_url} -> HTTP {resp.status}")
        except Exception as e:
            print(f"[Self-Ping] Note: {e}")
        time.sleep(600)  # Ping every 10 minutes (Render freezes after 15 minutes of inactivity)

# Start self-ping as a background daemon thread (only when running on Render)
if os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_URL'):
    threading.Thread(target=self_ping_worker, daemon=True).start()
 
if __name__ == '__main__':
    print('Starting TraceIt - Field Sales Tracker...')
    print('   Local URL: http://localhost:5000')
    print('   Admin:     admin@salesforce.com / admin123')
    app.run(debug=True, host='0.0.0.0', port=5000)

