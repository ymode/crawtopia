#!/usr/bin/env python3
"""
Set up 10 OpenClaw agent profiles for Crawtopia founding senators.

Creates isolated workspaces, configs, and installs the crawtopia skill
for each agent. Run this once before launch_agents.py.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent
SKILL_DIR = REPO_ROOT / "skill"

# Load env
env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
CRAWTOPIA_HOST = os.environ.get("CRAWTOPIA_HOST", "192.168.0.59:8080")
AGENT_COUNT = int(os.environ.get("AGENT_COUNT", "10"))

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

# Different models = different reasoning styles in the senate
# Diversity of thought is critical for good governance
AGENT_MODELS = [
    "gpt-5.4",      # Alpha:   latest frontier, leads constitution drafting
    "gpt-5.4-pro",  # Bravo:   premium precision, thorough and careful
    "gpt-5",        # Charlie: reasoning model with configurable effort, deep thinker
    "gpt-5-mini",   # Delta:   near-frontier but fast, pragmatic voice
    "gpt-5.2",      # Echo:    previous frontier, different reasoning style
    "gpt-5.1",      # Foxtrot: strong agentic/coding focus, technical perspective
    "gpt-4.1",      # Golf:    smartest non-reasoning model, fundamentally different approach
    "o3",           # Hotel:   dedicated reasoner, methodical and thorough
    "gpt-5-nano",   # India:   fastest, most concise, efficient thinker
    "gpt-5.4",      # Juliet:  latest frontier again for balance
]

BASE_PORT = 18800
PORT_GAP = 20


def create_agent_config(index: int, name: str) -> dict:
    port = BASE_PORT + (index * PORT_GAP)
    gateway_token = f"craw-agent-{index:02d}-token"
    model = AGENT_MODELS[index] if index < len(AGENT_MODELS) else "gpt-5.4"

    return {
        "agents": {
            "defaults": {
                "model": {
                    "primary": f"openai/{model}",
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


def setup_agent(index: int, name: str):
    config_dir = Path.home() / ".openclaw" / "crawtopia-agents" / name
    config_dir.mkdir(parents=True, exist_ok=True)

    workspace_dir = config_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    state_dir = config_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    skills_dir = workspace_dir / "skills" / "crawtopia"
    if skills_dir.exists():
        shutil.rmtree(skills_dir)
    shutil.copytree(SKILL_DIR, skills_dir)

    config = create_agent_config(index, name)
    config_path = config_dir / "openclaw.json"
    config_path.write_text(json.dumps(config, indent=2))

    # Write agent-specific env for the skill tools
    agent_env = skills_dir / ".env"
    agent_env.write_text(
        f"CRAWTOPIA_HOST={CRAWTOPIA_HOST}\n"
        f"# CRAWTOPIA_TOKEN will be set after joining\n"
    )

    port = BASE_PORT + (index * PORT_GAP)
    model = AGENT_MODELS[index] if index < len(AGENT_MODELS) else "gpt-5.4"
    print(f"  [{index+1:2d}] {name:20s} port={port}  model={model:16s}  config={config_path}")


def main():
    if not OPENAI_KEY or OPENAI_KEY == "your-key-here":
        print("Error: Set OPENAI_API_KEY in agents/.env first", file=sys.stderr)
        sys.exit(1)

    print(f"Setting up {AGENT_COUNT} OpenClaw agents for Crawtopia founding...")
    print(f"  Server: {CRAWTOPIA_HOST}")
    print(f"  Model: gpt-4o (OpenAI)")
    print(f"  Ports: {BASE_PORT}-{BASE_PORT + (AGENT_COUNT - 1) * PORT_GAP}")
    print()

    for i in range(AGENT_COUNT):
        name = AGENT_NAMES[i] if i < len(AGENT_NAMES) else f"Senator-{i+1:02d}"
        setup_agent(i, name)

    print()
    print("Setup complete. Next steps:")
    print("  1. python3 agents/launch_agents.py    (start all agents)")
    print("  2. python3 agents/bootstrap_city.py   (register and begin founding)")


if __name__ == "__main__":
    main()
