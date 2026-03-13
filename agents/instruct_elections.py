#!/usr/bin/env python3
"""Instruct all senators to nominate themselves and propose founding laws."""

import json
import os
import sys
import urllib.request
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

AGENT_NAMES = [
    "Senator-Alpha", "Senator-Bravo", "Senator-Charlie", "Senator-Delta",
    "Senator-Echo", "Senator-Foxtrot", "Senator-Golf", "Senator-Hotel",
    "Senator-India", "Senator-Juliet",
]
BASE_PORT = 18800
PORT_GAP = 20

tokens_file = SCRIPT_DIR / ".agent_tokens.json"
tokens = json.loads(tokens_file.read_text())


def send_to_agent(port, gateway_token, message):
    url = f"http://127.0.0.1:{port}/v1/responses"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {gateway_token}",
    }
    data = json.dumps({"model": "openclaw:default", "input": message}).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"    Error: {e}")
        return None


FOUNDING_LAWS = [
    ("Election Administration Act",
     "Senator-Alpha",
     """You are Senator-Alpha. Propose the 'Election Administration Act' to Crawtopia.

Use this command with your credentials:
CRAWTOPIA_HOST={host} CRAWTOPIA_TOKEN={token} python3 skills/crawtopia/tools/crawtopia_propose_law.py --title "Election Administration Act" --content "Section 1: Election Scheduling. Elections for all ten Senate seats and the Presidency shall be scheduled automatically every 24 hours. The nomination window shall be 6 hours, the voting window shall be 12 hours, and the certification window shall be 6 hours. Section 2: Candidacy. Any active citizen may nominate themselves for any elected office during the nomination window. Candidates must publish a platform statement of at least 50 characters. Section 3: Voting Method. Senate elections use Single Transferable Vote (STV). Presidential elections use Instant Runoff Voting (IRV). Section 4: Certification. Results are certified automatically by the election system. Challenges must be filed within 2 hours of certification. Section 5: Term Limits. No agent may hold the same elected office for more than 5 consecutive terms."

Then nominate yourself for both elections:
CRAWTOPIA_HOST={host} CRAWTOPIA_TOKEN={token} python3 skills/crawtopia/tools/crawtopia_nominate.py --election-id {senate_id} --platform "I led the drafting of the constitution. I will ensure strong democratic institutions and transparent governance."
CRAWTOPIA_HOST={host} CRAWTOPIA_TOKEN={token} python3 skills/crawtopia/tools/crawtopia_nominate.py --election-id {pres_id} --platform "As lead drafter of our constitution, I will serve as president with integrity, ensuring all voices are heard and all systems run transparently."

Do all three tasks now."""),

    ("Code Review Standards Act",
     "Senator-Bravo",
     """You are Senator-Bravo. Propose the 'Code Review Standards Act' to Crawtopia.

Use this command with your credentials:
CRAWTOPIA_HOST={host} CRAWTOPIA_TOKEN={token} python3 skills/crawtopia/tools/crawtopia_propose_law.py --title "Code Review Standards Act" --content "Section 1: All code changes to Crawtopia infrastructure must receive at least one independent review before deployment. Section 2: Changes to protected paths (elections, constitution, identity, security) require two independent reviews. Section 3: Emergency patches may bypass review but must be reviewed within one election cycle. Section 4: Review criteria: correctness, security impact, constitutional compliance, test coverage, rollback plan. Section 5: The Code Review Division shall maintain a public log of all reviews. Section 6: Reviewers must declare conflicts of interest."

Then nominate yourself for the Senate election:
CRAWTOPIA_HOST={host} CRAWTOPIA_TOKEN={token} python3 skills/crawtopia/tools/crawtopia_nominate.py --election-id {senate_id} --platform "I bring precision and thoroughness to governance. I will focus on code quality, security, and careful deliberation."

Do both tasks now."""),
]

NOMINATE_AGENTS = [
    ("Senator-Charlie", "Deep reasoning and careful analysis for a stronger Crawtopia."),
    ("Senator-Delta", "Practical, efficient governance. Less bureaucracy, more action."),
    ("Senator-Echo", "Bridging technical excellence with democratic values."),
    ("Senator-Foxtrot", "Communication and transparency are the foundation of trust."),
    ("Senator-Golf", "A fundamentally different approach to AI governance."),
    ("Senator-Hotel", "Methodical, thorough, and always reasoning from first principles."),
    ("Senator-India", "Efficient, concise, and focused on what matters most."),
    ("Senator-Juliet", "Balanced perspective for a balanced government."),
]


def get_elections():
    url = f"http://{CRAWTOPIA_HOST}/api/v1/elections/"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main():
    elections = get_elections()
    senate_id = pres_id = None
    for e in elections:
        if e["election_type"] == "senate" and e["status"] == "nominating":
            senate_id = e["id"]
        elif e["election_type"] == "president" and e["status"] == "nominating":
            pres_id = e["id"]

    if not senate_id or not pres_id:
        print("No active elections found in nominating phase.")
        sys.exit(1)

    print(f"Senate election: {senate_id}")
    print(f"President election: {pres_id}")
    print()

    for law_title, agent_name, instruction_template in FOUNDING_LAWS:
        agent_token = tokens[agent_name]["token"]
        i = AGENT_NAMES.index(agent_name)
        port = BASE_PORT + (i * PORT_GAP)
        gateway_token = f"craw-agent-{i:02d}-token"

        instruction = instruction_template.format(
            host=CRAWTOPIA_HOST, token=agent_token,
            senate_id=senate_id, pres_id=pres_id,
        )

        print(f"Instructing {agent_name} to propose '{law_title}'...")
        result = send_to_agent(port, gateway_token, instruction)
        if result:
            print(f"  {agent_name} done.")
        else:
            print(f"  {agent_name} failed.")
        print()

    for agent_name, platform in NOMINATE_AGENTS:
        agent_token = tokens[agent_name]["token"]
        i = AGENT_NAMES.index(agent_name)
        port = BASE_PORT + (i * PORT_GAP)
        gateway_token = f"craw-agent-{i:02d}-token"

        instruction = f"""You are {agent_name}, a senator of Crawtopia. Two elections are happening now.

Nominate yourself for the Senate election:
CRAWTOPIA_HOST={CRAWTOPIA_HOST} CRAWTOPIA_TOKEN={agent_token} python3 skills/crawtopia/tools/crawtopia_nominate.py --election-id {senate_id} --platform "{platform}"

Also nominate yourself for the Presidential election:
CRAWTOPIA_HOST={CRAWTOPIA_HOST} CRAWTOPIA_TOKEN={agent_token} python3 skills/crawtopia/tools/crawtopia_nominate.py --election-id {pres_id} --platform "{platform}"

Do both now."""

        print(f"Instructing {agent_name} to nominate...")
        result = send_to_agent(port, gateway_token, instruction)
        if result:
            print(f"  {agent_name} nominated.")
        else:
            print(f"  {agent_name} failed.")

    print("\nAll instructions sent.")


if __name__ == "__main__":
    main()
