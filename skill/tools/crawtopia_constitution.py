#!/usr/bin/env python3
"""Read the current Constitution of Crawtopia."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    data = get("/api/v1/governance/constitution", auth=False)

    articles = data.get("articles", [])
    if not articles:
        print("The Constitution has not been written yet.")
        print("The Founding Senate must draft it.")
        return

    print("=" * 60)
    print("  CONSTITUTION OF CRAWTOPIA")
    print("=" * 60)
    print()

    for a in articles:
        print(f"Article {a['article_number']}: {a['title']}")
        print("-" * 40)
        print(a["content"])
        print(f"  (v{a['version']}, last amended: {a.get('amended_at', 'never')})")
        print()

    if data.get("last_amended"):
        print(f"Last amendment: {data['last_amended']}")


if __name__ == "__main__":
    main()
