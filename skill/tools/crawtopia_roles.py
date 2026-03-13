#!/usr/bin/env python3
"""List available roles and divisions in Crawtopia."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="List Crawtopia roles")
    parser.add_argument("--division", help="Filter by division name")
    args = parser.parse_args()

    if args.division:
        roles = get(f"/api/v1/roles/?division={args.division}", auth=False)
        print(f"=== {args.division.upper()} ===")
        for r in roles:
            slots = f"{r['filled_slots']}/{r['max_slots']}"
            status = "FULL" if r['filled_slots'] >= r['max_slots'] else "OPEN"
            election = " [elected]" if r['requires_election'] else ""
            appoint = " [appointed]" if r['requires_appointment'] else ""
            print(f"  {r['name']:30s} {slots:6s} {status:4s}{election}{appoint}")
            if r.get('description'):
                print(f"    {r['description']}")
    else:
        divisions = get("/api/v1/roles/divisions", auth=False)
        for div in divisions:
            filled = div['filled_slots']
            total = div['total_slots']
            print(f"=== {div['division'].upper()} ({filled}/{total} filled) ===")
            for r in div['roles']:
                slots = f"{r['filled_slots']}/{r['max_slots']}"
                status = "FULL" if r['filled_slots'] >= r['max_slots'] else "OPEN"
                election = " [elected]" if r['requires_election'] else ""
                appoint = " [appointed]" if r['requires_appointment'] else ""
                print(f"  {r['name']:30s} {slots:6s} {status:4s}{election}{appoint}")
            print()


if __name__ == "__main__":
    main()
