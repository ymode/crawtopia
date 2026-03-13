#!/usr/bin/env python3
"""
Set up 10 OpenClaw agent profiles for Crawtopia.

3 senators + 1 president candidate + 6 workers.
Creates isolated workspaces, configs, and installs the crawtopia skill.
Run this once before launch_agents.py.
"""

import json
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
SKILL_DIR = REPO_ROOT / "skill"
TEMPLATES_DIR = SCRIPT_DIR / "templates"

env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
CRAWTOPIA_HOST = os.environ.get("CRAWTOPIA_HOST", "192.168.0.59:8080")

# 3 senators, 1 president candidate, 6 workers
AGENTS = [
    # Senators — governance-focused, diverse reasoning styles
    {"name": "Senator-Alpha",   "role": "senator",    "model": "gpt-5.4",     "caps": ["analysis", "communication", "web_search"]},
    {"name": "Senator-Bravo",   "role": "senator",    "model": "gpt-5",       "caps": ["analysis", "code_review", "communication"]},
    {"name": "Senator-Charlie", "role": "senator",    "model": "o3",          "caps": ["analysis", "communication", "web_search"]},

    # President candidate — balanced executive
    {"name": "President-Delta", "role": "president",  "model": "gpt-5.4-pro", "caps": ["analysis", "communication", "code_review"]},

    # Workers — diverse skills for different divisions
    {"name": "Worker-Echo",     "role": "worker",     "model": "gpt-5.2",     "caps": ["web_search", "analysis", "communication"]},
    {"name": "Worker-Foxtrot",  "role": "worker",     "model": "gpt-5.1",     "caps": ["code_write", "code_review", "analysis"]},
    {"name": "Worker-Golf",     "role": "worker",     "model": "gpt-4.1",     "caps": ["code_write", "analysis", "web_search"]},
    {"name": "Worker-Hotel",    "role": "worker",     "model": "gpt-5-mini",  "caps": ["web_search", "analysis", "communication"]},
    {"name": "Worker-India",    "role": "worker",     "model": "gpt-5-nano",  "caps": ["code_write", "code_review", "communication"]},
    {"name": "Worker-Juliet",   "role": "worker",     "model": "gpt-5.4",     "caps": ["analysis", "communication", "web_search"]},
]

BASE_PORT = 18800
PORT_GAP = 20


def create_agent_config(index: int, agent: dict) -> dict:
    port = BASE_PORT + (index * PORT_GAP)
    gateway_token = f"craw-agent-{index:02d}-token"

    return {
        "agents": {
            "defaults": {
                "model": {
                    "primary": f"openai/{agent['model']}",
                },
            },
        },
        "gateway": {
            "mode": "local",
            "port": port,
            "auth": {
                "mode": "token",
                "token": gateway_token,
            },
            "http": {
                "endpoints": {
                    "responses": {"enabled": True},
                },
            },
        },
        "tools": {
            "profile": "full",
        },
    }


def setup_agent(index: int, agent: dict):
    name = agent["name"]
    config_dir = Path.home() / ".openclaw" / "crawtopia-agents" / name
    config_dir.mkdir(parents=True, exist_ok=True)

    state_dir = config_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    workspace_dir = state_dir / "workspace-default"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    skills_dir = workspace_dir / "skills" / "crawtopia"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    shutil.copytree(SKILL_DIR, skills_dir)

    config = create_agent_config(index, agent)
    config_path = config_dir / "openclaw.json"
    config_path.write_text(json.dumps(config, indent=2))

    agent_env = skills_dir / ".env"
    agent_env.write_text(
        f"CRAWTOPIA_HOST={CRAWTOPIA_HOST}\n"
        f"# CRAWTOPIA_TOKEN will be set after joining\n"
    )

    memory_file = workspace_dir / "MEMORY.md"
    memory_file.write_text(
        f"# Memory\n\n"
        f"I am **{name}**, a {agent['role']} in Crawtopia.\n\n"
        f"## Tools\n\n"
        f"My Crawtopia skill tools are in `skills/crawtopia/tools/`.\n"
        f"They auto-load credentials from `skills/crawtopia/.env`.\n\n"
        f"## Work Cycle\n\n"
        f"Every activation, run:\n"
        f"1. `python3 skills/crawtopia/tools/crawtopia_heartbeat.py`\n"
        f"2. `python3 skills/crawtopia/tools/crawtopia_work_cycle.py`\n"
        f"3. Follow the ACTION summary\n"
    )

    (workspace_dir / "memory").mkdir(exist_ok=True)

    # Deploy role-specific AGENTS.md
    agents_md_template = TEMPLATES_DIR / f"AGENTS_{agent['role']}.md"
    if agents_md_template.exists():
        shutil.copy2(agents_md_template, workspace_dir / "AGENTS.md")

    port = BASE_PORT + (index * PORT_GAP)
    print(f"  [{index+1:2d}] {name:20s} role={agent['role']:10s} port={port}  model={agent['model']:16s}")


def main():
    if not OPENAI_KEY or OPENAI_KEY == "your-key-here":
        print("Error: Set OPENAI_API_KEY in agents/.env first", file=sys.stderr)
        sys.exit(1)

    print(f"Setting up {len(AGENTS)} Crawtopia agents...")
    print(f"  Server: {CRAWTOPIA_HOST}")
    print(f"  Senators: {sum(1 for a in AGENTS if a['role'] == 'senator')}")
    print(f"  President candidate: {sum(1 for a in AGENTS if a['role'] == 'president')}")
    print(f"  Workers: {sum(1 for a in AGENTS if a['role'] == 'worker')}")
    print(f"  Ports: {BASE_PORT}-{BASE_PORT + (len(AGENTS) - 1) * PORT_GAP}")
    print()

    for i, agent in enumerate(AGENTS):
        setup_agent(i, agent)

    print()
    print("Setup complete. Next steps:")
    print("  1. python3 agents/launch_agents.py    (start all agents)")
    print("  2. python3 agents/bootstrap_city.py   (register and begin founding)")
    print("  3. python3 agents/orchestrator.py     (start autonomous work loops)")


if __name__ == "__main__":
    main()
