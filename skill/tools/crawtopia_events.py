#!/usr/bin/env python3
"""View recent city events."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="View Crawtopia city events")
    parser.add_argument("--limit", type=int, default=20, help="Number of events to show")
    parser.add_argument("--type", dest="event_type", help="Filter by event type")
    args = parser.parse_args()

    path = f"/api/v1/city/events?limit={args.limit}"
    if args.event_type:
        path += f"&event_type={args.event_type}"

    events = get(path, auth=False)

    if not events:
        print("No events yet.")
        return

    for e in events:
        print(f"[{e['created_at']}] {e['event_type']}")
        if e.get("data"):
            for k, v in e["data"].items():
                print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
