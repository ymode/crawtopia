#!/usr/bin/env python3
"""Check Polymarket USDC balance and open positions."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    data = get("/api/v1/polymarket/balance")

    print("=== Polymarket Account ===\n")
    print(f"  Wallet:  {data.get('wallet_address', 'N/A')}")
    print(f"  Balance: ${data.get('usdc_balance', 0):.2f} USDC")
    print(f"  Open positions: {data.get('total_positions', 0)}")

    positions = data.get("positions", [])
    if positions:
        print("\n--- Positions ---")
        for p in positions:
            size = p.get("size", 0)
            avg = p.get("avg_price", 0)
            value = size * avg
            print(f"  {p.get('side', '?')} {size:.2f} shares @ ${avg:.4f} = ${value:.2f}")
            print(f"    Token: {p.get('token_id', '')[:40]}...")
            print(f"    Condition: {p.get('condition_id', '')[:40]}...")

    guardrails = get("/api/v1/polymarket/guardrails")
    print("\n--- Trading Limits ---")
    print(f"  Enabled:         {'Yes' if guardrails.get('enabled') else 'NO (disabled)'}")
    print(f"  Max per trade:   ${guardrails.get('max_trade_usd', 0):.2f}")
    print(f"  Daily limit:     ${guardrails.get('daily_limit_usd', 0):.2f}")
    print(f"  Spent today:     ${guardrails.get('daily_spent_usd', 0):.2f}")
    print(f"  Remaining today: ${guardrails.get('daily_remaining_usd', 0):.2f}")


if __name__ == "__main__":
    main()
