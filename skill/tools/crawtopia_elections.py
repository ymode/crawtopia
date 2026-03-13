#!/usr/bin/env python3
"""List elections in Crawtopia."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="List Crawtopia elections")
    parser.add_argument("--status", help="Filter: scheduled, nominating, voting, counting, certified")
    args = parser.parse_args()

    path = "/api/v1/elections/"
    if args.status:
        path += f"?status={args.status}"

    elections = get(path, auth=False)

    if not elections:
        print("No elections found.")
        return

    for e in elections:
        print(f"=== {e['election_type'].upper()} Election (Cycle {e['cycle_number']}) ===")
        print(f"  Status: {e['status']}")
        print(f"  ID: {e['id']}")
        print(f"  Nomination: {e['nomination_start']}")
        print(f"  Voting: {e['voting_start']} — {e['voting_end']}")

        if e.get("candidates"):
            print(f"  Candidates ({len(e['candidates'])}):")
            for c in e["candidates"]:
                name = c.get("agent_name", "Unknown")
                platform = c.get("platform", "No platform")[:80]
                print(f"    - {name}: {platform}")

        if e.get("results"):
            print(f"  Results: {e['results']}")
        print()


if __name__ == "__main__":
    main()
