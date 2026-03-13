#!/usr/bin/env python3
"""Show your current role assignments."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    roles = get("/api/v1/roles/my-roles")
    if not roles:
        print("You have no role assignments.")
        return

    print("Your roles:")
    for r in roles:
        print(f"  [{r['division']}] {r['role_name']} (assigned: {r['assignment_type']}, {r['assigned_at']})")


if __name__ == "__main__":
    main()
