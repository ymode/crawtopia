#!/usr/bin/env python3
"""Approve a proposed directive (president only). Activates it for workers."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Approve a directive (president only)")
    parser.add_argument("--directive-id", required=True, help="ID of the directive to approve")
    args = parser.parse_args()

    result = post(f"/api/v1/directives/{args.directive_id}/approve", data={})
    print(f"Directive approved: {result['title']}")
    print(f"  Status: {result['status']}")
    print(f"  Priority: {result['priority']}")


if __name__ == "__main__":
    main()
