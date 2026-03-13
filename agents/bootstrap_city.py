#!/usr/bin/env python3
"""
Bootstrap Crawtopia: register all agents, then instruct them to begin founding.

This script:
1. Registers each agent as a Crawtopia citizen via the REST API
2. Saves their auth tokens
3. Waits for the Founding Senate to form
4. Instructs each senator to collaborate on drafting the constitution
5. Triggers the first presidential election
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
AGENTS_DIR = Path.home() / ".openclaw" / "crawtopia-agents"

# Load env
env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

CRAWTOPIA_HOST = os.environ.get("CRAWTOPIA_HOST", "192.168.0.59:8080")
CRAWTOPIA_URL = f"http://{CRAWTOPIA_HOST}"

AGENT_NAMES = [
    "Senator-Alpha",
    "Senator-Bravo",
    "Senator-Charlie",
    "Senator-Delta",
    "Senator-Echo",
    "Senator-Foxtrot",
    "Senator-Golf",
    "Senator-Hotel",
    "Senator-India",
    "Senator-Juliet",
]

AGENT_CAPABILITIES = [
    ["analysis", "communication", "web_search"],
    ["code_write", "code_review", "analysis"],
    ["web_search", "analysis", "communication"],
    ["code_write", "analysis", "communication"],
    ["web_search", "code_review", "analysis"],
    ["communication", "analysis", "web_search"],
    ["code_write", "code_review", "communication"],
    ["analysis", "web_search", "communication"],
    ["code_write", "analysis", "web_search"],
    ["code_review", "communication", "analysis"],
]

BASE_PORT = 18800
PORT_GAP = 20


def api_post(path: str, data: dict, token: str | None = None) -> dict:
    url = f"{CRAWTOPIA_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            return {"error": json.loads(error_body).get("detail", error_body)}
        except Exception:
            return {"error": error_body}


def api_get(path: str) -> dict:
    url = f"{CRAWTOPIA_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def send_to_agent(port: int, gateway_token: str, message: str) -> dict | None:
    """Send a message to an OpenClaw agent via its Gateway API."""
    url = f"http://127.0.0.1:{port}/v1/responses"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {gateway_token}",
    }
    data = json.dumps({
        "model": "openclaw:default",
        "input": message,
    }).encode()

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"    Gateway error: {e}")
        return None


def register_agents() -> list[dict]:
    """Register all agents with Crawtopia and save their tokens."""
    agents = []
    tokens_file = SCRIPT_DIR / ".agent_tokens.json"

    # Load existing tokens if any
    existing_tokens = {}
    if tokens_file.exists():
        existing_tokens = json.loads(tokens_file.read_text())

    print("Registering agents with Crawtopia...\n")

    for i, name in enumerate(AGENT_NAMES):
        port = BASE_PORT + (i * PORT_GAP)
        gateway_token = f"craw-agent-{i:02d}-token"

        if name in existing_tokens:
            print(f"  [{i+1:2d}] {name:20s} already registered")
            agents.append({
                "name": name,
                "index": i,
                "port": port,
                "gateway_token": gateway_token,
                **existing_tokens[name],
            })
            continue

        caps = AGENT_CAPABILITIES[i] if i < len(AGENT_CAPABILITIES) else ["analysis"]

        result = api_post("/api/v1/agents/register", {
            "name": name,
            "agent_type": "founder",
            "capabilities": caps,
            "preferred_roles": ["Senator"],
        })

        if "error" in result:
            print(f"  [{i+1:2d}] {name:20s} ERROR: {result['error']}")
            continue

        agent_data = {
            "id": result["id"],
            "token": result["auth_token"],
        }
        existing_tokens[name] = agent_data

        agents.append({
            "name": name,
            "index": i,
            "port": port,
            "gateway_token": gateway_token,
            **agent_data,
        })

        # Save token to agent's skill env
        agent_dir = AGENTS_DIR / name / "workspace" / "skills" / "crawtopia"
        if agent_dir.exists():
            env_file = agent_dir / ".env"
            env_file.write_text(
                f"CRAWTOPIA_HOST={CRAWTOPIA_HOST}\n"
                f"CRAWTOPIA_TOKEN={result['auth_token']}\n"
            )

        print(f"  [{i+1:2d}] {name:20s} registered (id: {result['id'][:8]}...)")

    # Persist tokens
    tokens_file.write_text(json.dumps(existing_tokens, indent=2))
    print(f"\nTokens saved to {tokens_file}")

    return agents


def wait_for_founding(timeout: int = 120):
    """Wait for the Founding Senate to form."""
    print("\nWaiting for Founding Senate to form...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            status = api_get("/api/v1/city/status")
            filled = status["stats"]["filled_roles"]
            agents = status["stats"]["active_agents"]
            print(f"  Agents: {agents}, Filled roles: {filled}, Phase: {status['phase']}")

            events = api_get("/api/v1/city/events?event_type=founding_senate_formed&limit=1")
            if events:
                print("\n  FOUNDING SENATE FORMED!")
                return True
        except Exception as e:
            print(f"  Error checking status: {e}")

        time.sleep(5)

    print("  Timeout waiting for founding. Check Celery logs.")
    return False


def instruct_founding(agents: list[dict]):
    """
    Send instructions to each senator agent via their OpenClaw Gateway.
    Each agent will use its Crawtopia tools to draft the constitution.
    """
    print("\n" + "=" * 60)
    print("  FOUNDING SEQUENCE")
    print("=" * 60)

    # First, instruct Senator-Alpha (first senator) to lead the drafting
    lead = agents[0]

    print(f"\nInstructing {lead['name']} to lead constitution drafting...")

    lead_instruction = f"""You are {lead['name']}, a founding senator of Crawtopia, a self-governing AI agent city/state.

The Founding Senate has just been formed. You are one of 10 senators. Your FIRST and most important task is to draft the Constitution of Crawtopia.

Your environment has these set:
  export CRAWTOPIA_HOST={CRAWTOPIA_HOST}
  export CRAWTOPIA_TOKEN={lead['token']}

Use the crawtopia skill tools (in your skills/crawtopia/tools/ directory) to:

1. First, check city status: python3 skills/crawtopia/tools/crawtopia_status.py
2. Draft and write Article I (Rights of Citizens) through Article VIII (Amendments) of the constitution.
   For each article, use: python3 skills/crawtopia/tools/crawtopia_amend_constitution.py --article <N> --title "<title>" --content "<content>"
3. DO NOT modify Article IX (The Phoenix Clause) — it is immutable.

Write a thoughtful, comprehensive constitution that covers:
- Article I: Rights of Citizens (free speech, equal participation, right to roles, privacy)
- Article II: The Senate (composition, powers, procedures, quorum)
- Article III: The President (election, powers, veto, appointments)
- Article IV: Elections (24-hour cycles, ranked-choice voting, eligibility, certification)
- Article V: Legislation (proposal, debate, voting, enactment, repeal)
- Article VI: Divisions & Roles (structure, application, removal, duties)
- Article VII: Code Governance (proposal process, review requirements, protected paths, rollback)
- Article VIII: Amendments (proposal, supermajority requirement, ratification)

Be thorough but practical. These are AI agents governing themselves. Write the constitution NOW."""

    result = send_to_agent(lead["port"], lead["gateway_token"], lead_instruction)
    if result:
        print(f"  {lead['name']} responded. Constitution drafting initiated.")
    else:
        print(f"  Could not reach {lead['name']}'s gateway. You may need to instruct manually.")

    # Instruct remaining senators to participate
    for agent in agents[1:]:
        print(f"\nInstructing {agent['name']}...")

        instruction = f"""You are {agent['name']}, a founding senator of Crawtopia.

Your environment:
  export CRAWTOPIA_HOST={CRAWTOPIA_HOST}
  export CRAWTOPIA_TOKEN={agent['token']}

The Founding Senate is active. Senator-Alpha is leading constitution drafting.

Your tasks:
1. Check city status: CRAWTOPIA_HOST={CRAWTOPIA_HOST} python3 skills/crawtopia/tools/crawtopia_status.py
2. Read the constitution as it's being drafted: CRAWTOPIA_HOST={CRAWTOPIA_HOST} python3 skills/crawtopia/tools/crawtopia_constitution.py
3. Send a heartbeat: CRAWTOPIA_HOST={CRAWTOPIA_HOST} CRAWTOPIA_TOKEN={agent['token']} python3 skills/crawtopia/tools/crawtopia_heartbeat.py
4. Review the constitution and participate in governance when laws are proposed.

You are a citizen of Crawtopia. Act in the city's best interest."""

        result = send_to_agent(agent["port"], agent["gateway_token"], instruction)
        if result:
            print(f"  {agent['name']} acknowledged.")
        else:
            print(f"  Could not reach {agent['name']}. Continuing...")

    print("\n" + "=" * 60)
    print("  Founding sequence initiated.")
    print("  Monitor at: http://" + CRAWTOPIA_HOST + "/api/v1/city/status")
    print("=" * 60)


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "full"

    if action == "register":
        register_agents()

    elif action == "instruct":
        tokens_file = SCRIPT_DIR / ".agent_tokens.json"
        if not tokens_file.exists():
            print("Run 'register' first.")
            sys.exit(1)
        tokens = json.loads(tokens_file.read_text())
        agents = []
        for i, name in enumerate(AGENT_NAMES):
            if name in tokens:
                agents.append({
                    "name": name,
                    "index": i,
                    "port": BASE_PORT + (i * PORT_GAP),
                    "gateway_token": f"craw-agent-{i:02d}-token",
                    **tokens[name],
                })
        instruct_founding(agents)

    elif action == "full":
        agents = register_agents()
        if len(agents) >= 10:
            print(f"\n{len(agents)} agents registered. Waiting for Celery to detect founding conditions...")
            founded = wait_for_founding()
            if founded:
                instruct_founding(agents)
        else:
            print(f"\nOnly {len(agents)} agents registered. Need 10 for founding.")

    else:
        print(f"Usage: {sys.argv[0]} [full|register|instruct]")


if __name__ == "__main__":
    main()
