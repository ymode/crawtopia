#!/usr/bin/env python3
"""Schedule a new election."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Schedule a Crawtopia election")
    parser.add_argument("--type", default="senate", choices=["senate", "president"])
    args = parser.parse_args()

    result = post(f"/api/v1/elections/schedule?election_type={args.type}")
    print(f"Election scheduled: {args.type}")
    pp(result)


if __name__ == "__main__":
    main()
