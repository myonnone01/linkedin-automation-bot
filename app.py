"""Flask entrypoint.

Starts the web server, prints LAN access URLs, and (on Windows) auto-opens
the dashboard in the default browser. No background scheduler - the
automation engine only runs when the user clicks Start in the UI.
"""
import socket
import sys
import threading
import time
import webbrowser

from flask import Flask

import config
import db
from routes import dashboard, exports, runs, sequences_api, templates_api


def detect_lan_ip() -> str:
    """Best-effort local network IP detection.

    Opens a UDP socket to a public IP - doesn't actually send any traffic -
    so the OS routing table tells us which local interface would be used.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def print_banner(host: str, port: int) -> None:
    lan_ip = detect_lan_ip()
    border = "=" * 60
    print(border, flush=True)
    print("  LinkedIn Automation Bot is running", flush=True)
    print("", flush=True)
    print(f"  Desktop:  http://localhost:{port}", flush=True)
    print(f"  Desktop:  http://127.0.0.1:{port}", flush=True)
    print(f"  Phone:    http://{lan_ip}:{port}", flush=True)
    print("", flush=True)
    print("  (Open the Phone URL in iPhone Safari on the same Wi-Fi.)", flush=True)
    print(border, flush=True)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    db.init_db()
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(templates_api.bp)
    app.register_blueprint(sequences_api.bp)
    app.register_blueprint(runs.bp)
    app.register_blueprint(exports.bp)
    return app


def _delayed_open_browser(url: str, delay: float = 1.5) -> None:
    def target():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=target, daemon=True).start()


def main() -> None:
    app = create_app()
    print_banner(config.FLASK_HOST, config.FLASK_PORT)
    if sys.platform.startswith("win"):
        _delayed_open_browser(f"http://localhost:{config.FLASK_PORT}")
    # threaded=True so the SSE endpoint doesn't block other requests.
    # use_reloader=False to avoid double-starting the worker and browser.
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        threaded=True,
        use_reloader=False,
        debug=False,
    )


if __name__ == "__main__":
    main()
