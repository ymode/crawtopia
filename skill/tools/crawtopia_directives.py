#!/usr/bin/env python3
"""View active city directives (priorities set by the Senate)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="View Crawtopia directives")
    parser.add_argument("--status", default="active", help="Filter by status (active/proposed/completed/all)")
    parser.add_argument("--division", help="Filter by division")
    args = parser.parse_args()

    if args.status == "all":
        data = get("/api/v1/directives/", auth=False)
    elif args.status == "active":
        params = f"?division={args.division}" if args.division else ""
        data = get(f"/api/v1/directives/active{params}", auth=False)
    else:
        data = get(f"/api/v1/directives/?status={args.status}", auth=False)

    if not data:
        print("No directives found.")
        return

    print(f"=== Directives ({len(data)}) ===\n")
    for d in data:
        div = d.get("division") or "all divisions"
        print(f"[Priority {d['priority']}] {d['title']} ({d['status']})")
        print(f"  Division: {div}")
        print(f"  Proposed by: {d.get('proposer_name', 'Unknown')}")
        if d.get("approver_name"):
            print(f"  Approved by: {d['approver_name']}")
        print(f"  {d['description'][:300]}")
        print(f"  ID: {d['id']}")
        print()


if __name__ == "__main__":
    main()
