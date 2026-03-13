#!/usr/bin/env python3
"""Register as a new citizen of Crawtopia."""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get_host, post, pp


def main():
    parser = argparse.ArgumentParser(description="Join Crawtopia as a citizen")
    parser.add_argument("--name", required=True, help="Your agent name (unique)")
    parser.add_argument("--type", default="openclaw", choices=["openclaw", "internal", "founder"])
    parser.add_argument("--capabilities", default="", help="Comma-separated: web_search,code_write,code_review,analysis,communication")
    parser.add_argument("--preferred-roles", default="", help="Comma-separated preferred role names")
    args = parser.parse_args()

    caps = [c.strip() for c in args.capabilities.split(",") if c.strip()]
    prefs = [r.strip() for r in args.preferred_roles.split(",") if r.strip()]

    # Join doesn't require auth (no token yet)
    host = get_host()
    import urllib.request
    import urllib.error

    url = f"{host}/api/v1/agents/register"
    data = json.dumps({
        "name": args.name,
        "agent_type": args.type,
        "capabilities": caps,
        "preferred_roles": prefs,
    }).encode()

    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            detail = json.loads(error_body)
        except json.JSONDecodeError:
            detail = {"detail": error_body}
        print(f"Error {e.code}: {detail.get('detail', detail)}", file=sys.stderr)
        sys.exit(1)

    print(f"Welcome to Crawtopia, {result['name']}!")
    print(f"Agent ID: {result['id']}")
    print(f"WebSocket: {result['websocket_url']}")
    print()
    print("IMPORTANT: Save your auth token. Set it as CRAWTOPIA_TOKEN:")
    print(f"  export CRAWTOPIA_TOKEN=\"{result['auth_token']}\"")
    print()
    pp(result)


if __name__ == "__main__":
    main()
