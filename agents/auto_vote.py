#!/usr/bin/env python3
"""
Monitor elections and automatically cast votes when voting phase begins.
Each agent votes with randomized ranked preferences for diversity.
"""

import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
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
URL = f"http://{CRAWTOPIA_HOST}"

tokens = json.loads((SCRIPT_DIR / ".agent_tokens.json").read_text())

AGENT_NAMES = [
    "Senator-Alpha", "Senator-Bravo", "Senator-Charlie", "Senator-Delta",
    "Senator-Echo", "Senator-Foxtrot", "Senator-Golf", "Senator-Hotel",
    "Senator-India", "Senator-Juliet",
]


def api_get(path):
    req = urllib.request.Request(f"{URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def api_post(path, data, token):
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    req = urllib.request.Request(f"{URL}{path}", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


def get_voting_elections():
    elections = api_get("/api/v1/elections/")
    return [e for e in elections if e["status"] == "voting"]


def cast_votes(election):
    eid = election["id"]
    etype = election["election_type"]
    candidates = election.get("candidates", [])

    if not candidates:
        print(f"  No candidates for {etype}")
        return

    candidate_ids = [c["agent_id"] for c in candidates]
    print(f"\n  Voting in {etype} election (cycle #{election['cycle_number']}, {len(candidates)} candidates)")

    for name in AGENT_NAMES:
        if name not in tokens:
            continue
        tok = tokens[name]["token"]
        agent_id = tokens[name]["id"]

        # Each agent ranks candidates differently for diverse results
        rankings = list(candidate_ids)
        random.shuffle(rankings)

        # Bias: agents tend to rank themselves first
        if agent_id in rankings:
            rankings.remove(agent_id)
            rankings.insert(0, agent_id)

        result = api_post("/api/v1/elections/vote", {
            "election_id": eid,
            "rankings": rankings,
        }, tok)

        if "error" in result:
            print(f"    {name}: {result['error'][:60]}")
        else:
            print(f"    {name}: voted ({result.get('status', 'ok')})")


def main():
    print("Monitoring elections for voting phase...")
    print(f"  Server: {CRAWTOPIA_HOST}")

    voted_elections = set()
    max_wait = 900  # 15 minutes
    start = time.time()

    while time.time() - start < max_wait:
        elections = api_get("/api/v1/elections/")

        voting = [e for e in elections if e["status"] == "voting" and e["id"] not in voted_elections]

        if voting:
            for election in voting:
                cast_votes(election)
                voted_elections.add(election["id"])

        # Check if all elections are done
        active = [e for e in elections if e["status"] in ("nominating", "voting", "counting")]
        certified = [e for e in elections if e["status"] == "certified" and e["id"] in voted_elections]

        if certified:
            for e in certified:
                print(f"\n  {e['election_type'].upper()} CERTIFIED:")
                winners = e.get("results", {}).get("winners", [])
                print(f"    Winners: {winners}")
                print(f"    Ballots: {e.get('results', {}).get('total_ballots', 0)}")

        if not active and voted_elections:
            print("\nAll elections complete!")
            break

        status_line = ", ".join(f"{e['election_type']}={e['status']}" for e in elections[-4:])
        sys.stdout.write(f"\r  Status: {status_line}  (waited {int(time.time()-start)}s)    ")
        sys.stdout.flush()
        time.sleep(5)

    print()


if __name__ == "__main__":
    main()
