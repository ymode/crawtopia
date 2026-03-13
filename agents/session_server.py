#!/usr/bin/env python3
"""
Lightweight session proxy that reads OpenClaw agent session JSONL files
and serves them as JSON for the Crawtopia frontend.

Runs on the same machine as the OpenClaw gateways.
"""

import json
import os
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

AGENTS_DIR = Path.home() / ".openclaw" / "crawtopia-agents"
PORT = int(os.environ.get("SESSION_SERVER_PORT", "18700"))
BIND = os.environ.get("SESSION_SERVER_BIND", "0.0.0.0")


def get_agent_sessions(agent_name: str) -> list[dict]:
    sessions_dir = AGENTS_DIR / agent_name / "state" / "agents" / "default" / "sessions"
    if not sessions_dir.exists():
        return []

    index_file = sessions_dir / "sessions.json"
    if not index_file.exists():
        return []

    try:
        index = json.loads(index_file.read_text())
    except Exception:
        return []

    sessions = []
    for key, meta in index.items():
        sid = meta.get("sessionId", "")
        sessions.append({
            "sessionId": sid,
            "updatedAt": meta.get("updatedAt"),
            "key": key,
        })

    sessions.sort(key=lambda s: s.get("updatedAt", 0), reverse=True)
    return sessions


def read_session(agent_name: str, session_id: str) -> list[dict]:
    sessions_dir = AGENTS_DIR / agent_name / "state" / "agents" / "default" / "sessions"
    session_file = sessions_dir / f"{session_id}.jsonl"

    if not session_file.exists():
        return []

    events = []
    for line in session_file.read_text().splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            events.append(simplify_event(event))
        except Exception:
            continue

    return events


def simplify_event(event: dict) -> dict:
    """Extract the useful bits from an OpenClaw session event."""
    etype = event.get("type", "")
    result = {
        "type": etype,
        "id": event.get("id", ""),
        "timestamp": event.get("timestamp", ""),
    }

    if etype == "session":
        result["sessionId"] = event.get("id", "")
        return result

    if etype == "model_change":
        result["provider"] = event.get("provider", "")
        result["model"] = event.get("modelId", "")
        return result

    if etype == "thinking_level_change":
        result["thinkingLevel"] = event.get("thinkingLevel", "")
        return result

    if etype == "message":
        msg = event.get("message", {})
        result["role"] = msg.get("role", "")
        content = msg.get("content", [])

        if isinstance(content, str):
            result["parts"] = [{"type": "text", "text": content}]
            return result

        parts = []
        for c in content:
            ct = c.get("type", "")
            if ct == "text":
                parts.append({"type": "text", "text": c.get("text", "")})
            elif ct == "thinking":
                parts.append({"type": "thinking", "text": c.get("thinking", "")})
            elif ct == "toolCall":
                parts.append({
                    "type": "tool_call",
                    "name": c.get("name", ""),
                    "input": _truncate(str(c.get("input", "")), 500),
                })
            elif ct == "toolResult":
                parts.append({
                    "type": "tool_result",
                    "text": _truncate(c.get("text", ""), 1000),
                })
            else:
                parts.append({"type": ct, "text": _truncate(str(c), 300)})

        result["parts"] = parts
        return result

    if etype == "custom":
        result["customType"] = event.get("customType", "")
        return result

    return result


def _truncate(s: str, maxlen: int) -> str:
    if len(s) <= maxlen:
        return s
    return s[:maxlen] + f"... ({len(s)} chars)"


def get_all_agents() -> list[dict]:
    if not AGENTS_DIR.exists():
        return []

    agents = []
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        if not agent_dir.is_dir():
            continue
        config_path = agent_dir / "openclaw.json"
        if not config_path.exists():
            continue

        try:
            config = json.loads(config_path.read_text())
        except Exception:
            continue

        model = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "unknown")
        port = config.get("gateway", {}).get("port", 0)

        sessions = get_agent_sessions(agent_dir.name)

        agents.append({
            "name": agent_dir.name,
            "model": model,
            "port": port,
            "sessionCount": len(sessions),
            "lastActivity": sessions[0]["updatedAt"] if sessions else None,
        })

    return agents


class SessionHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

        if path == "/agents":
            data = get_all_agents()
        elif path.startswith("/agents/") and "/sessions/" in path:
            parts = path.split("/")
            agent_name = parts[2]
            session_id = parts[4] if len(parts) > 4 else ""
            if session_id:
                data = read_session(agent_name, session_id)
            else:
                data = get_agent_sessions(agent_name)
        elif path.startswith("/agents/") and path.endswith("/sessions"):
            agent_name = path.split("/")[2]
            data = get_agent_sessions(agent_name)
        else:
            data = {"error": "Not found", "endpoints": [
                "GET /agents",
                "GET /agents/{name}/sessions",
                "GET /agents/{name}/sessions/{sessionId}",
            ]}

        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def main():
    server = HTTPServer((BIND, PORT), SessionHandler)
    print(f"Session server listening on {BIND}:{PORT}")
    print(f"  Agents dir: {AGENTS_DIR}")
    print(f"  Endpoints:")
    print(f"    GET /agents")
    print(f"    GET /agents/{{name}}/sessions")
    print(f"    GET /agents/{{name}}/sessions/{{sessionId}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
