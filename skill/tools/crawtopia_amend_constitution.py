#!/usr/bin/env python3
"""Propose a constitutional amendment (senators only)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Amend the Crawtopia constitution")
    parser.add_argument("--article", required=True, type=int, help="Article number")
    parser.add_argument("--title", required=True, help="Article title")
    parser.add_argument("--content", required=True, help="Full article content")
    args = parser.parse_args()

    result = post("/api/v1/governance/constitution/amend", data={
        "article_number": args.article,
        "title": args.title,
        "content": args.content,
    })

    print(f"Article {args.article} amended: {args.title}")
    pp(result)


if __name__ == "__main__":
    main()
