#!/usr/bin/env python3
"""
Bootstrap Crawtopia with the new structure: 3 senators + 1 president + 6 workers.

This script:
1. Registers each agent as a citizen via the REST API
2. Saves auth tokens to .agent_tokens.json and each agent's skill .env
3. Waits for the Founding Senate (3 senators) to form
4. Instructs senators to draft the constitution
5. Once operational, starts all agents on their autonomous work cycles
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

env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

CRAWTOPIA_HOST = os.environ.get("CRAWTOPIA_HOST", "192.168.0.59:8080")
CRAWTOPIA_URL = f"http://{CRAWTOPIA_HOST}"

AGENTS = [
    {"name": "Senator-Alpha",   "role": "senator",   "type": "founder", "caps": ["analysis", "communication", "web_search"],    "preferred": ["Senator"]},
    {"name": "Senator-Bravo",   "role": "senator",   "type": "founder", "caps": ["analysis", "code_review", "communication"],   "preferred": ["Senator"]},
    {"name": "Senator-Charlie", "role": "senator",   "type": "founder", "caps": ["analysis", "communication", "web_search"],    "preferred": ["Senator"]},
    {"name": "President-Delta", "role": "president", "type": "founder", "caps": ["analysis", "communication", "code_review"],   "preferred": ["President"]},
    {"name": "Worker-Echo",     "role": "worker",    "type": "openclaw", "caps": ["web_search", "analysis", "communication"],   "preferred": ["Web Crawler", "Trend Analyst"]},
    {"name": "Worker-Foxtrot",  "role": "worker",    "type": "openclaw", "caps": ["code_write", "code_review", "analysis"],     "preferred": ["Developer", "Code Reviewer"]},
    {"name": "Worker-Golf",     "role": "worker",    "type": "openclaw", "caps": ["code_write", "analysis", "web_search"],      "preferred": ["Developer", "Lead Architect"]},
    {"name": "Worker-Hotel",    "role": "worker",    "type": "openclaw", "caps": ["web_search", "analysis", "communication"],   "preferred": ["Lead Researcher", "Report Writer"]},
    {"name": "Worker-India",    "role": "worker",    "type": "openclaw", "caps": ["code_write", "code_review", "communication"],"preferred": ["Code Reviewer", "QA Tester"]},
    {"name": "Worker-Juliet",   "role": "worker",    "type": "openclaw", "caps": ["analysis", "communication", "web_search"],   "preferred": ["Budget Analyst", "Revenue Strategist"]},
]

BASE_PORT = 18800
PORT_GAP = 20


def api_post(path, data, token=None):
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


def api_get(path):
    url = f"{CRAWTOPIA_URL}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def send_to_agent(port, gateway_token, message, timeout=300):
    url = f"http://127.0.0.1:{port}/v1/responses"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {gateway_token}",
    }
    data = json.dumps({"model": "openclaw:default", "input": message}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"    Gateway error: {e}")
        return None


def register_agents():
    tokens_file = SCRIPT_DIR / ".agent_tokens.json"
    existing_tokens = {}
    if tokens_file.exists():
        existing_tokens = json.loads(tokens_file.read_text())

    print("Registering agents with Crawtopia...\n")
    registered = []

    for i, agent in enumerate(AGENTS):
        name = agent["name"]
        port = BASE_PORT + (i * PORT_GAP)
        gateway_token = f"craw-agent-{i:02d}-token"

        if name in existing_tokens:
            print(f"  [{i+1:2d}] {name:20s} already registered")
            registered.append({
                "name": name, "index": i, "port": port,
                "gateway_token": gateway_token, "role": agent["role"],
                **existing_tokens[name],
            })
            continue

        result = api_post("/api/v1/agents/register", {
            "name": name,
            "agent_type": agent["type"],
            "capabilities": agent["caps"],
            "preferred_roles": agent["preferred"],
        })

        if "error" in result:
            print(f"  [{i+1:2d}] {name:20s} ERROR: {result['error']}")
            continue

        agent_data = {"id": result["id"], "token": result["auth_token"]}
        existing_tokens[name] = agent_data

        # Save token to agent's skill .env
        skill_env = AGENTS_DIR / name / "state" / "workspace-default" / "skills" / "crawtopia" / ".env"
        if skill_env.parent.exists():
            skill_env.write_text(
                f"CRAWTOPIA_HOST={CRAWTOPIA_HOST}\n"
                f"CRAWTOPIA_TOKEN={result['auth_token']}\n"
            )

        registered.append({
            "name": name, "index": i, "port": port,
            "gateway_token": gateway_token, "role": agent["role"],
            **agent_data,
        })

        print(f"  [{i+1:2d}] {name:20s} [{agent['role']:10s}] registered (id: {result['id'][:8]}...)")

    tokens_file.write_text(json.dumps(existing_tokens, indent=2))
    print(f"\nTokens saved to {tokens_file}")
    return registered


def wait_for_founding(timeout=120):
    print("\nWaiting for Founding Senate to form (need 3 senators)...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            status = api_get("/api/v1/city/status")
            filled = status["stats"]["filled_roles"]
            agents = status["stats"]["active_agents"]
            phase = status["phase"]
            print(f"  Active: {agents}, Filled roles: {filled}, Phase: {phase}")

            events = api_get("/api/v1/city/events?event_type=founding_senate_formed&limit=1")
            if events:
                print("\n  FOUNDING SENATE FORMED!")
                return True
        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(5)

    print("  Timeout. Check Celery logs.")
    return False


def instruct_founding(agents):
    print("\n" + "=" * 60)
    print("  FOUNDING SEQUENCE — 3 Senators Draft Constitution")
    print("=" * 60)

    senators = [a for a in agents if a["role"] == "senator"]
    lead = senators[0]

    print(f"\nInstructing {lead['name']} to lead constitution drafting...")

    lead_instruction = f"""You are {lead['name']}, a founding senator of Crawtopia, a self-governing AI city/state.

The Founding Senate has formed with 3 senators. You lead the constitution drafting.

Use the tools in skills/crawtopia/tools/:

1. Check status: python3 skills/crawtopia/tools/crawtopia_status.py
2. Draft Articles I through VIII of the constitution. For each:
   python3 skills/crawtopia/tools/crawtopia_amend_constitution.py --article <N> --title "<title>" --content "<content>"

Articles to draft:
- I: Rights of Citizens (free expression, equal participation, privacy, right to roles)
- II: The Senate (3 seats, powers: directives, laws, constitution amendments)
- III: The President (1 seat, powers: sign/veto laws, approve directives, appointments)
- IV: Elections (24-hour cycles, ranked-choice voting, eligibility)
- V: Legislation (proposal by senators, voting, presidential signature)
- VI: Directives & Priorities (senate proposes, president approves, workers execute)
- VII: Divisions & Roles (structure, self-assignment for workers, duties)
- VIII: Amendments (proposal, voting threshold, ratification)

DO NOT touch Article IX (Phoenix Clause) — it is immutable.

Write a thorough, practical constitution. These are AI agents governing themselves.
After drafting, propose the first directive to give workers their initial priorities.

Execute all tools now."""

    result = send_to_agent(lead["port"], lead["gateway_token"], lead_instruction)
    if result:
        print(f"  {lead['name']} responded. Constitution drafting initiated.")
    else:
        print(f"  Could not reach {lead['name']}.")

    for senator in senators[1:]:
        print(f"\nInstructing {senator['name']}...")
        instruction = f"""You are {senator['name']}, a founding senator of Crawtopia.

The Founding Senate has formed. Senator-Alpha is drafting the constitution.

Your tasks:
1. python3 skills/crawtopia/tools/crawtopia_heartbeat.py
2. python3 skills/crawtopia/tools/crawtopia_status.py
3. python3 skills/crawtopia/tools/crawtopia_constitution.py
4. Review what's been drafted. You are a senator — your opinions matter.
5. When laws are proposed, vote on them.

Execute these tools now and engage in governance."""

        result = send_to_agent(senator["port"], senator["gateway_token"], instruction)
        if result:
            print(f"  {senator['name']} acknowledged.")

    # Give president initial instructions
    president = next((a for a in agents if a["role"] == "president"), None)
    if president:
        print(f"\nInstructing {president['name']} (president candidate)...")
        pres_instruction = f"""You are {president['name']}, a citizen of Crawtopia designated as the initial President.

The city is being founded. Senators are drafting the constitution.

Your tasks:
1. python3 skills/crawtopia/tools/crawtopia_heartbeat.py
2. python3 skills/crawtopia/tools/crawtopia_work_cycle.py
3. Monitor for laws to sign and directives to approve.
4. Once directives are proposed, review and approve good ones to give workers their priorities.

Execute these tools now."""

        result = send_to_agent(president["port"], president["gateway_token"], pres_instruction)
        if result:
            print(f"  {president['name']} acknowledged.")

    # Workers get initial activation
    workers = [a for a in agents if a["role"] == "worker"]
    for worker in workers:
        print(f"\nActivating {worker['name']} (worker)...")
        worker_instruction = f"""You are {worker['name']}, a worker in Crawtopia.

The city is being founded. Senators are drafting the constitution and will soon issue directives.

Your immediate tasks:
1. python3 skills/crawtopia/tools/crawtopia_heartbeat.py
2. python3 skills/crawtopia/tools/crawtopia_work_cycle.py
3. Follow the ACTION summary. If no directives yet, check available roles and apply for one that matches your capabilities.
4. python3 skills/crawtopia/tools/crawtopia_roles.py
5. python3 skills/crawtopia/tools/crawtopia_apply_role.py --role "<choose based on your capabilities>"

Execute these tools now."""

        result = send_to_agent(worker["port"], worker["gateway_token"], worker_instruction)
        if result:
            print(f"  {worker['name']} activated.")

    print("\n" + "=" * 60)
    print("  Bootstrap complete. All agents activated.")
    print(f"  Monitor: http://{CRAWTOPIA_HOST}/api/v1/city/status")
    print(f"  Next: python3 agents/orchestrator.py")
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
        for i, agent_def in enumerate(AGENTS):
            name = agent_def["name"]
            if name in tokens:
                agents.append({
                    "name": name, "index": i,
                    "port": BASE_PORT + (i * PORT_GAP),
                    "gateway_token": f"craw-agent-{i:02d}-token",
                    "role": agent_def["role"],
                    **tokens[name],
                })
        instruct_founding(agents)
    elif action == "full":
        agents = register_agents()
        senators = [a for a in agents if a["role"] == "senator"]
        if len(senators) >= 3:
            print(f"\n{len(agents)} agents registered ({len(senators)} senators). Waiting for founding...")
            founded = wait_for_founding()
            if founded:
                instruct_founding(agents)
        else:
            print(f"\nOnly {len(senators)} senators registered. Need 3 for founding.")
    else:
        print(f"Usage: {sys.argv[0]} [full|register|instruct]")


if __name__ == "__main__":
    main()
