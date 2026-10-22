#!/usr/bin/env python3
"""One entry point for the terminal eye, browser studio and desktop studio."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="DAVA Animation Studio")
    parser.add_argument("mode", choices=["terminal", "web", "desktop"], nargs="?", default="terminal")
    parser.add_argument("--port", type=int, default=8080, help="Web port; default 8080")
    args, extra = parser.parse_known_args()
    if args.mode == "terminal":
        return subprocess.call([sys.executable, str(ROOT / "terminal/DAVA_KOZ_01.py"), *extra])
    if args.mode == "desktop":
        return subprocess.call([sys.executable, str(ROOT / "desktop/run.py"), *extra])
    if extra:
        parser.error("Noma'lum web parametrlari: " + " ".join(extra))
    if not 1 <= args.port <= 65535:
        parser.error("Port 1–65535 orasida bo'lsin.")
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT / "web"))
    try:
        with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
            print(f"DAVA Space Studio: http://127.0.0.1:{args.port}", flush=True)
            print("To'xtatish: Ctrl+C", flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        print(f"Web server ochilmadi: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
