"""Operator commands."""

from __future__ import annotations

import argparse
import json
import os

from jarvis.context import open_context
from jarvis.mcp_server import stdio_main
from jarvis.probes import ensure_qdrant_collections
from jarvis.server import serve
from jarvis.tools import call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("serve")
    sub.add_parser("mcp")
    sub.add_parser("ensure-qdrant")
    tool = sub.add_parser("tool")
    tool.add_argument("name")
    tool.add_argument("--args", default="{}")
    args = parser.parse_args(argv)
    ctx = open_context()
    if args.command == "status":
        from jarvis.server import _status

        print(json.dumps(_status(ctx), indent=2))
        return 0
    if args.command == "ensure-qdrant":
        print(json.dumps(ensure_qdrant_collections(ctx), indent=2))
        return 0
    if args.command == "serve":
        port = int(os.environ.get("JARVIS_PORT", "8787"))
        server = serve(ctx, port=port)
        print(f"JARVIS operator UI http://127.0.0.1:{port}/", flush=True)
        server.serve_forever()
        return 0
    if args.command == "mcp":
        stdio_main(ctx)
        return 0
    if args.command == "tool":
        result = call(ctx, args.name, json.loads(args.args))
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
