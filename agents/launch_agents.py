#!/usr/bin/env python3
"""
Launch all 10 OpenClaw agent gateways as background processes.

Each agent runs on its own port with its own workspace.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
AGENTS_DIR = Path.home() / ".openclaw" / "crawtopia-agents"
PID_DIR = SCRIPT_DIR / ".pids"

# Load env from agents/.env
env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


def get_agents():
    if not AGENTS_DIR.exists():
        print("Error: Run setup_agents.py first", file=sys.stderr)
        sys.exit(1)

    agents = []
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        config_path = agent_dir / "openclaw.json"
        if config_path.exists():
            config = json.loads(config_path.read_text())
            agents.append({
                "name": agent_dir.name,
                "dir": agent_dir,
                "config_path": config_path,
                "state_dir": agent_dir / "state",
                "port": config["gateway"]["port"],
                "token": config["gateway"]["auth"]["token"],
            })
    return agents


def launch_agent(agent: dict) -> subprocess.Popen:
    env = os.environ.copy()
    env["OPENCLAW_CONFIG_PATH"] = str(agent["config_path"])
    env["OPENCLAW_STATE_DIR"] = str(agent["state_dir"])

    log_path = agent["dir"] / "gateway.log"

    with open(log_path, "w") as log_file:
        proc = subprocess.Popen(
            ["openclaw", "gateway", "--port", str(agent["port"])],
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    return proc


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "start"

    if action == "stop":
        stop_all()
        return

    if action == "status":
        check_status()
        return

    agents = get_agents()
    if not agents:
        print("No agents found. Run setup_agents.py first.")
        sys.exit(1)

    PID_DIR.mkdir(exist_ok=True)

    print(f"Launching {len(agents)} OpenClaw agents...\n")

    for agent in agents:
        pid_file = PID_DIR / f"{agent['name']}.pid"

        # Check if already running
        if pid_file.exists():
            old_pid = int(pid_file.read_text().strip())
            try:
                os.kill(old_pid, 0)
                print(f"  {agent['name']:20s} already running (pid {old_pid}, port {agent['port']})")
                continue
            except ProcessLookupError:
                pid_file.unlink()

        proc = launch_agent(agent)
        pid_file.write_text(str(proc.pid))
        print(f"  {agent['name']:20s} started (pid {proc.pid}, port {agent['port']})")

    print(f"\nAll agents launched. Waiting for gateways to initialize...")
    time.sleep(5)

    # Quick health check
    import urllib.request
    import urllib.error

    healthy = 0
    for agent in agents:
        try:
            url = f"http://127.0.0.1:{agent['port']}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                healthy += 1
                print(f"  {agent['name']:20s} port {agent['port']} — healthy")
        except Exception:
            print(f"  {agent['name']:20s} port {agent['port']} — starting up...")

    print(f"\n{healthy}/{len(agents)} gateways responding.")
    print("Run: python3 agents/launch_agents.py status   (check all)")
    print("Run: python3 agents/launch_agents.py stop     (stop all)")
    print("Next: python3 agents/bootstrap_city.py        (register with Crawtopia)")


def stop_all():
    if not PID_DIR.exists():
        print("No running agents found.")
        return

    for pid_file in sorted(PID_DIR.iterdir()):
        if pid_file.suffix == ".pid":
            pid = int(pid_file.read_text().strip())
            name = pid_file.stem
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"  Stopped {name} (pid {pid})")
            except ProcessLookupError:
                print(f"  {name} already stopped")
            pid_file.unlink()

    print("All agents stopped.")


def check_status():
    import urllib.request
    import urllib.error

    agents = get_agents()
    if not agents:
        print("No agents configured.")
        return

    for agent in agents:
        pid_file = PID_DIR / f"{agent['name']}.pid" if PID_DIR.exists() else None
        pid_status = "no pid"
        if pid_file and pid_file.exists():
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, 0)
                pid_status = f"pid {pid}"
            except ProcessLookupError:
                pid_status = "dead"

        gw_status = "down"
        try:
            url = f"http://127.0.0.1:{agent['port']}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                gw_status = "healthy"
        except Exception:
            pass

        print(f"  {agent['name']:20s} port={agent['port']}  process={pid_status:12s}  gateway={gw_status}")


if __name__ == "__main__":
    main()
