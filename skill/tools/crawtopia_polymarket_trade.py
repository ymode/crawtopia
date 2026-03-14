#!/usr/bin/env python3
"""Place a trade on Polymarket (guardrails enforced server-side)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import post


def main():
    parser = argparse.ArgumentParser(description="Trade on Polymarket")
    parser.add_argument("--condition-id", required=True, help="Market condition ID")
    parser.add_argument("--token-id", required=True, help="Token ID for the outcome")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"], help="BUY or SELL")
    parser.add_argument("--outcome", required=True, help="Outcome label (e.g. Yes, No)")
    parser.add_argument("--amount", required=True, type=float, help="Amount in USD")
    parser.add_argument("--price", type=float, help="Limit price (0-1). Omit for market order.")
    parser.add_argument("--market", default="", help="Market question (for logging)")
    args = parser.parse_args()

    payload = {
        "condition_id": args.condition_id,
        "token_id": args.token_id,
        "side": args.side,
        "outcome": args.outcome,
        "amount_usd": args.amount,
        "market_question": args.market,
    }
    if args.price is not None:
        payload["price"] = args.price

    data = post("/api/v1/polymarket/trade", data=payload)

    status = data.get("status", "unknown")
    print(f"=== Trade {'Placed' if status == 'filled' else status.upper()} ===\n")
    print(f"  Market:    {data.get('market_question', 'N/A')}")
    print(f"  Side:      {data.get('side', '')} {data.get('outcome', '')}")
    print(f"  Amount:    ${data.get('amount_usd', 0):.2f}")
    if data.get("price"):
        print(f"  Price:     ${data['price']:.4f}")
    if data.get("shares"):
        print(f"  Shares:    {data['shares']:.2f}")
    print(f"  Status:    {status}")
    if data.get("order_id"):
        print(f"  Order ID:  {data['order_id']}")
    if data.get("error_message"):
        print(f"  Error:     {data['error_message']}")
    print(f"  Trade ID:  {data.get('id', '')}")


if __name__ == "__main__":
    main()
