import argparse
import socket
import threading
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from .app import create_app


def main():
    parser = argparse.ArgumentParser(description="30A Studio")
    parser.add_argument("--port", type=int, default=8830)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}"
    with socket.socket() as probe:
        occupied = probe.connect_ex(("127.0.0.1", args.port)) == 0
    if occupied:
        try:
            import json
            with urllib.request.urlopen(url + "/api/health", timeout=2) as response:
                existing = json.load(response)
            if existing.get("app") == "thirtya-studio":
                if not args.no_browser:
                    webbrowser.open(url)
                return
        except Exception:
            pass
        raise SystemExit("Bu bağlantı noktası kullanılıyor. --port ile başka bir numara seçin.")
    server = uvicorn.Server(uvicorn.Config(create_app(args.data_dir), host="127.0.0.1", port=args.port,
                                          log_level="warning", timeout_graceful_shutdown=2))
    if not args.no_browser:
        def show_when_ready():
            import time
            for _ in range(100):
                if server.started:
                    webbrowser.open(url)
                    return
                time.sleep(0.1)
        threading.Thread(target=show_when_ready, daemon=True).start()
    print(f"30A Studio: {url}\nKapatmak için bu pencerede Ctrl+C kullanın.")
    server.run()


if __name__ == "__main__":
    main()
