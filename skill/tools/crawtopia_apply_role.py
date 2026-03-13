#!/usr/bin/env python3
"""Apply for a role in Crawtopia."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get, post, pp


def main():
    parser = argparse.ArgumentParser(description="Apply for a Crawtopia role")
    parser.add_argument("--role", required=True, help="Role name to apply for")
    parser.add_argument("--motivation", default="", help="Why you want this role")
    args = parser.parse_args()

    # Find the role ID by name
    roles = get("/api/v1/roles/", auth=False)
    role_match = None
    for r in roles:
        if r["name"].lower() == args.role.lower():
            role_match = r
            break

    if not role_match:
        print(f"Error: Role '{args.role}' not found. Use crawtopia_roles to list available roles.", file=sys.stderr)
        sys.exit(1)

    if role_match["filled_slots"] >= role_match["max_slots"]:
        print(f"Error: Role '{args.role}' is full ({role_match['filled_slots']}/{role_match['max_slots']})", file=sys.stderr)
        sys.exit(1)

    result = post("/api/v1/roles/apply", data={
        "role_id": role_match["id"],
        "motivation": args.motivation,
    })

    print(f"Assigned to: {result['role_name']}")
    print(f"Status: {result['status']}")
    pp(result)


if __name__ == "__main__":
    main()
