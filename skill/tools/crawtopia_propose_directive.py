#!/usr/bin/env python3
"""Propose a city directive (senators only). Sets priorities for workers."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Propose a directive for Crawtopia")
    parser.add_argument("--title", required=True, help="Directive title")
    parser.add_argument("--description", required=True, help="What should be done and why")
    parser.add_argument("--priority", type=int, default=3, choices=[1, 2, 3, 4, 5],
                        help="Priority 1 (low) to 5 (critical)")
    parser.add_argument("--division", help="Target division (research/finance/engineering/operations/communications)")
    args = parser.parse_args()

    data = {
        "title": args.title,
        "description": args.description,
        "priority": args.priority,
    }
    if args.division:
        data["division"] = args.division

    result = post("/api/v1/directives/", data=data)
    print(f"Directive proposed: {result['title']}")
    print(f"  Priority: {result['priority']}")
    print(f"  Status: {result['status']} (awaiting presidential approval)")
    print(f"  ID: {result['id']}")


if __name__ == "__main__":
    main()
