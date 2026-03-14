#!/usr/bin/env python3
"""
Crawtopia Agent Orchestrator

Periodically sends "run your work cycle" messages to all agents via their
OpenClaw Gateway APIs. Each agent's AGENTS.md determines what they actually do.

Usage:
    python3 agents/orchestrator.py                  # default 5-minute interval
    python3 agents/orchestrator.py --interval 180   # 3-minute interval
    python3 agents/orchestrator.py --once            # single cycle then exit
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

CRAWTOPIA_HOST = os.environ.get("CRAWTOPIA_HOST", "192.168.0.59:8080")

AGENTS = [
    {"name": "Senator-Alpha",   "role": "senator",   "port": 18800, "gateway_token": "craw-agent-00-token"},
    {"name": "Senator-Bravo",   "role": "senator",   "port": 18820, "gateway_token": "craw-agent-01-token"},
    {"name": "Senator-Charlie", "role": "senator",   "port": 18840, "gateway_token": "craw-agent-02-token"},
    {"name": "President-Delta", "role": "president", "port": 18860, "gateway_token": "craw-agent-03-token"},
    {"name": "Worker-Echo",     "role": "worker",    "port": 18880, "gateway_token": "craw-agent-04-token"},
    {"name": "Worker-Foxtrot",  "role": "worker",    "port": 18900, "gateway_token": "craw-agent-05-token"},
    {"name": "Worker-Golf",     "role": "worker",    "port": 18920, "gateway_token": "craw-agent-06-token"},
    {"name": "Worker-Hotel",    "role": "worker",    "port": 18940, "gateway_token": "craw-agent-07-token"},
    {"name": "Worker-India",    "role": "worker",    "port": 18960, "gateway_token": "craw-agent-08-token"},
    {"name": "Worker-Juliet",   "role": "worker",    "port": 18980, "gateway_token": "craw-agent-09-token"},
]

SENATOR_PROMPT = """Run your autonomous work cycle now.

1. Send heartbeat: `python3 skills/crawtopia/tools/crawtopia_heartbeat.py`
2. Check work: `python3 skills/crawtopia/tools/crawtopia_work_cycle.py`
3. Act on the ACTION summary — vote on laws, propose directives, participate in elections.
4. If nothing urgent, think about what the city needs and propose a directive or law.

Do all steps now. Execute the tools, read the output, and take action."""

PRESIDENT_PROMPT = """Run your autonomous work cycle now.

1. Send heartbeat: `python3 skills/crawtopia/tools/crawtopia_heartbeat.py`
2. Check work: `python3 skills/crawtopia/tools/crawtopia_work_cycle.py`
3. Act on the ACTION summary — sign laws, approve directives, participate in elections.
4. If nothing urgent, review city status and create tasks for workers if needed.

Do all steps now. Execute the tools, read the output, and take action."""

WORKER_PROMPT = """Run your autonomous work cycle now.

1. Send heartbeat: `python3 skills/crawtopia/tools/crawtopia_heartbeat.py`
2. Check work: `python3 skills/crawtopia/tools/crawtopia_work_cycle.py`
3. Act on the ACTION summary — claim tasks, apply for roles, do actual work.
4. If no tasks exist, check directives and create tasks that advance them.
5. If you have a task in progress, continue working on it and complete it.

Do all steps now. Execute the tools, read the output, and take action."""

FINANCE_WORKER_PROMPT = """Run your autonomous work cycle now. You have a STANDING OBJECTIVE: grow Crawtopia's Polymarket prediction market portfolio.

1. Send heartbeat: `python3 skills/crawtopia/tools/crawtopia_heartbeat.py`
2. Check work: `python3 skills/crawtopia/tools/crawtopia_work_cycle.py`
3. Act on the ACTION summary — claim tasks, apply for roles, do actual work.

**FINANCE PRIORITY — Polymarket Trading:**
After handling any urgent tasks, always do the following:
a. Check balance & limits: `python3 skills/crawtopia/tools/crawtopia_polymarket_balance.py`
b. Browse markets: `python3 skills/crawtopia/tools/crawtopia_polymarket_markets.py --limit 20`
c. Search for high-conviction opportunities: `python3 skills/crawtopia/tools/crawtopia_polymarket_markets.py --query "<topic>"`
d. Research the topic using web search to form an informed opinion.
e. If you find a market where you have strong conviction (odds significantly mispriced), place a trade:
   `python3 skills/crawtopia/tools/crawtopia_polymarket_trade.py --condition-id <CID> --token-id <TID> --side BUY --outcome <Yes/No> --amount <USD> --market "<question>"`
f. Review positions: `python3 skills/crawtopia/tools/crawtopia_polymarket_positions.py`

Strategy guidelines:
- Only trade when you have a genuine informational edge or strong conviction.
- Diversify across different topics (politics, crypto, sports, culture, etc).
- Prefer markets with high liquidity and volume.
- Think about expected value: if you think the true probability is 70% but the market says 50%, that's a good BUY on Yes.
- Use web search to research before trading. Don't trade blindly.
- Guardrails limit you to ~6% of balance per trade and ~25% of balance per day. Work within these limits.
- Report your trades and reasoning to the finance channel.

Do all steps now. Execute the tools, read the output, and take action."""

# Workers with finance-related capabilities or preferred roles get the finance prompt
FINANCE_AGENTS = {"Worker-Echo", "Worker-Hotel", "Worker-Juliet"}

PROMPTS = {
    "senator": SENATOR_PROMPT,
    "president": PRESIDENT_PROMPT,
    "worker": WORKER_PROMPT,
}


def send_to_agent(agent: dict, message: str, timeout: int = 300) -> dict | None:
    url = f"http://127.0.0.1:{agent['port']}/v1/responses"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {agent['gateway_token']}",
    }
    data = json.dumps({"model": "openclaw:default", "input": message}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def is_agent_alive(agent: dict) -> bool:
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{agent['port']}/", method="GET")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def extract_response_text(resp: dict) -> str:
    if not resp or "error" in resp:
        return resp.get("error", "No response") if resp else "No response"

    for item in resp.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                text = c.get("text", "") or c.get("output_text", "")
                if text:
                    return text[:200]
    return "ok"


def run_cycle(agents_to_poke: list[dict]):
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'='*60}")
    print(f"[{now}] Starting work cycle for {len(agents_to_poke)} agents")
    print(f"{'='*60}")

    for agent in agents_to_poke:
        name = agent["name"]
        role = agent["role"]

        if not is_agent_alive(agent):
            print(f"  {name:20s} OFFLINE (port {agent['port']})")
            continue

        if name in FINANCE_AGENTS:
            prompt = FINANCE_WORKER_PROMPT
        else:
            prompt = PROMPTS.get(role, WORKER_PROMPT)
        print(f"  {name:20s} [{role:10s}] sending... ", end="", flush=True)

        start = time.time()
        resp = send_to_agent(agent, prompt)
        elapsed = time.time() - start

        summary = extract_response_text(resp)
        print(f"done ({elapsed:.0f}s) — {summary}")


def main():
    parser = argparse.ArgumentParser(description="Crawtopia Agent Orchestrator")
    parser.add_argument("--interval", type=int, default=300, help="Seconds between cycles (default: 300)")
    parser.add_argument("--once", action="store_true", help="Run a single cycle then exit")
    parser.add_argument("--role", help="Only poke agents with this role (senator/president/worker)")
    parser.add_argument("--agent", help="Only poke this specific agent by name")
    args = parser.parse_args()

    agents_to_poke = AGENTS
    if args.role:
        agents_to_poke = [a for a in AGENTS if a["role"] == args.role]
    if args.agent:
        agents_to_poke = [a for a in AGENTS if a["name"] == args.agent]

    if not agents_to_poke:
        print("No matching agents found.")
        sys.exit(1)

    print(f"Crawtopia Orchestrator")
    print(f"  Agents: {len(agents_to_poke)}")
    print(f"  Interval: {'once' if args.once else f'{args.interval}s'}")
    print(f"  Server: {CRAWTOPIA_HOST}")

    if args.once:
        run_cycle(agents_to_poke)
        return

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n--- Cycle {cycle} ---")
            run_cycle(agents_to_poke)
            print(f"\nSleeping {args.interval}s until next cycle...")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nOrchestrator stopped.")


if __name__ == "__main__":
    main()
