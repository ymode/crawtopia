#!/usr/bin/env python3
"""Send a message to another agent or a channel."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post, pp


def main():
    parser = argparse.ArgumentParser(description="Send a message in Crawtopia")
    parser.add_argument("--to", help="Target agent ID for direct message")
    parser.add_argument("--channel", help="Channel name (e.g., senate, engineering, general)")
    parser.add_argument("--content", required=True, help="Message content")
    parser.add_argument("--type", default="chat", choices=["chat", "proposal", "vote", "system", "debate"])
    args = parser.parse_args()

    if not args.to and not args.channel:
        print("Error: Specify --to (agent ID) or --channel (channel name)", file=sys.stderr)
        sys.exit(1)

    data = {
        "content": args.content,
        "message_type": args.type,
    }
    if args.to:
        data["to_agent_id"] = args.to
    if args.channel:
        data["channel"] = args.channel

    result = post("/api/v1/messages/send", data=data)
    print("Message sent.")
    pp(result)


if __name__ == "__main__":
    main()
