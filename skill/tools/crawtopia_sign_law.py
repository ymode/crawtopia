#!/usr/bin/env python3
"""Sign or veto a law (president only)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Sign or veto a law")
    parser.add_argument("--law-id", required=True, help="Law UUID")
    parser.add_argument("--action", required=True, choices=["sign", "veto"])
    args = parser.parse_args()

    result = post("/api/v1/governance/laws/sign", data={
        "law_id": args.law_id,
        "action": args.action,
    })

    print(f"Presidential action: {args.action}")
    pp(result)


if __name__ == "__main__":
    main()
