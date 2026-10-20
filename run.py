#!/usr/bin/env python3
"""Start Wishing Tree. This is the one command the teaching staff need.

    python run.py

It checks for PORTKEY_API_KEY (this folder's .env first, then one level up),
creates and seeds data/wishing_tree.db if needed, and serves both the API and
the built React frontend on http://127.0.0.1:8000.
"""

from __future__ import annotations

import argparse
import socket
import sys

from backend import config


def port_in_use(host: str, port: int) -> bool:
    """True if something is already listening there."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Wishing Tree app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Fail fast and readably, rather than inside a server traceback.
    try:
        config.require_api_key()
    except RuntimeError as exc:
        print(f"\nWishing Tree cannot start.\n\n{exc}\n", file=sys.stderr)
        return 1

    if port_in_use(args.host, args.port):
        print(
            f"\nPort {args.port} on {args.host} is already in use, so Wishing Tree "
            f"cannot start there.\n"
            f"Stop whatever is using it, or pick another port:\n\n"
            f"    python run.py --port {args.port + 1}\n",
            file=sys.stderr,
        )
        return 1

    import uvicorn

    print(f"\n  Wishing Tree  ->  http://{args.host}:{args.port}\n")
    # reload is off on purpose: one edit should not spawn a second server.
    uvicorn.run("backend.main:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
