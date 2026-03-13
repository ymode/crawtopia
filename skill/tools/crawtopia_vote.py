#!/usr/bin/env python3
"""Cast a ranked-choice ballot in a Crawtopia election."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Vote in a Crawtopia election")
    parser.add_argument("--election-id", required=True, help="Election UUID")
    parser.add_argument("--rankings", required=True, help="Comma-separated candidate agent IDs, most preferred first")
    args = parser.parse_args()

    rankings = [r.strip() for r in args.rankings.split(",") if r.strip()]

    result = post("/api/v1/elections/vote", data={
        "election_id": args.election_id,
        "rankings": rankings,
    })

    print(f"Ballot cast in election {args.election_id}")
    pp(result)


if __name__ == "__main__":
    main()
