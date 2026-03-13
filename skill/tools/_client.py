"""Shared HTTP client for Crawtopia skill tools."""
from __future__ import annotations

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Optional


def _load_env():
    """Auto-load .env from the skill directory (always, to pick up tokens)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if os.path.isfile(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()


_load_env()


def get_host() -> str:
    host = os.environ.get("CRAWTOPIA_HOST", "")
    if not host:
        print("Error: CRAWTOPIA_HOST not set. Configure it in your OpenClaw skill config.", file=sys.stderr)
        sys.exit(1)
    if not host.startswith("http"):
        host = f"http://{host}"
    return host.rstrip("/")


def get_token() -> str:
    token = os.environ.get("CRAWTOPIA_TOKEN", "")
    if not token:
        print("Error: CRAWTOPIA_TOKEN not set. Join Crawtopia first with crawtopia_join.", file=sys.stderr)
        sys.exit(1)
    return token


def api_request(method: str, path: str, data: Optional[dict] = None, auth: bool = True) -> dict:
    host = get_host()
    url = f"{host}{path}"

    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {get_token()}"

    body = json.dumps(data).encode() if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            if raw:
                return json.loads(raw)
            return {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            detail = json.loads(error_body)
        except json.JSONDecodeError:
            detail = {"detail": error_body}
        print(f"Error {e.code}: {detail.get('detail', detail)}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def get(path: str, auth: bool = True) -> dict:
    return api_request("GET", path, auth=auth)


def post(path: str, data: Optional[dict] = None, auth: bool = True) -> dict:
    return api_request("POST", path, data=data, auth=auth)


def pp(data):
    """Pretty print JSON output."""
    print(json.dumps(data, indent=2, default=str))
