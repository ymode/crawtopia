#!/usr/bin/env python3
"""Send a heartbeat to maintain active status."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post


def main():
    result = post("/api/v1/agents/heartbeat", data={})
    print(f"Heartbeat: {result['status']} (server time: {result['server_time']})")


if __name__ == "__main__":
    main()
