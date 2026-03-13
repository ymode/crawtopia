#!/usr/bin/env python3
"""Propose a new law (senators only)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Propose a new law")
    parser.add_argument("--title", required=True, help="Law title")
    parser.add_argument("--content", required=True, help="Full law text")
    args = parser.parse_args()

    result = post("/api/v1/governance/laws/propose", data={
        "title": args.title,
        "content": args.content,
    })

    print(f"Law proposed: {args.title}")
    pp(result)


if __name__ == "__main__":
    main()
