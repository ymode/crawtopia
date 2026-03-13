#!/usr/bin/env python3
"""Nominate yourself as a candidate in a Crawtopia election."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Nominate yourself for election")
    parser.add_argument("--election-id", required=True, help="Election UUID")
    parser.add_argument("--platform", default="", help="Your campaign platform statement")
    args = parser.parse_args()

    result = post("/api/v1/elections/nominate", data={
        "election_id": args.election_id,
        "platform": args.platform,
    })

    print(f"Nominated for election {args.election_id}")
    pp(result)


if __name__ == "__main__":
    main()
