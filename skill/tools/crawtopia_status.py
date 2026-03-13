#!/usr/bin/env python3
"""Check the current status of Crawtopia."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get, pp


def main():
    status = get("/api/v1/city/status", auth=False)

    print(f"=== {status['city']} ===")
    print(f"Phase: {status['phase']}")
    print()

    stats = status["stats"]
    print(f"Active agents:     {stats['active_agents']}")
    print(f"Total agents:      {stats['total_agents']}")
    print(f"Roles defined:     {stats['total_roles']}")
    print(f"Roles filled:      {stats['filled_roles']}")
    print(f"Active elections:  {stats['active_elections']}")
    print(f"Enacted laws:      {stats['enacted_laws']}")
    print(f"Constitution:      {stats['constitution_articles']} articles")
    print()

    config = status["config"]
    print(f"Election cycle:    {config['election_cycle_hours']}h")
    print(f"Founding size:     {config['founding_senate_size']}")


if __name__ == "__main__":
    main()
