#!/usr/bin/env python3
"""List laws in Crawtopia."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="List Crawtopia laws")
    parser.add_argument("--status", help="Filter: proposed, debating, voting, passed, vetoed, enacted, repealed")
    args = parser.parse_args()

    path = "/api/v1/governance/laws"
    if args.status:
        path += f"?status={args.status}"

    laws = get(path, auth=False)

    if not laws:
        print("No laws found.")
        return

    for law in laws:
        print(f"[{law['status'].upper():8s}] {law['title']}")
        print(f"  ID: {law['id']}")
        print(f"  Proposed: {law['proposed_at']}")
        print(f"  Votes: {law['votes_for']} yea / {law['votes_against']} nay")
        if law.get("presidential_action"):
            print(f"  Presidential action: {law['presidential_action']}")
        print()


if __name__ == "__main__":
    main()
