#!/usr/bin/env python3
"""View detailed Polymarket positions and trade history."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="Polymarket positions and trade history")
    parser.add_argument("--history", action="store_true", help="Show trade history instead of positions")
    parser.add_argument("--limit", type=int, default=20, help="Max history entries")
    args = parser.parse_args()

    if args.history:
        trades = get(f"/api/v1/polymarket/trades?limit={args.limit}")
        if not trades:
            print("No trade history.")
            return
        print(f"=== Trade History ({len(trades)}) ===\n")
        for t in trades:
            status_icon = {
                "filled": "+", "failed": "X", "pending": "~", "cancelled": "-"
            }.get(t["status"], "?")
            print(f"  [{status_icon}] {t.get('side', '')} {t.get('outcome', '')} "
                  f"${t.get('amount_usd', 0):.2f} — {t.get('market_question', '')[:80]}")
            print(f"      Status: {t['status']}  Agent: {t.get('agent_name', '')}")
            if t.get("error_message"):
                print(f"      Error: {t['error_message'][:100]}")
            print(f"      ID: {t['id']}  {t.get('created_at', '')}")
            print()
        return

    positions = get("/api/v1/polymarket/positions")
    if not positions:
        print("No open positions.")
        return

    total_value = 0
    print(f"=== Open Positions ({len(positions)}) ===\n")
    for p in positions:
        size = p.get("size", 0)
        avg = p.get("avg_price", 0)
        value = size * avg
        total_value += value
        print(f"  {p.get('side', '?')} {size:.2f} shares @ ${avg:.4f} (cost: ${value:.2f})")
        print(f"    Token:     {p.get('token_id', '')[:50]}...")
        print(f"    Condition: {p.get('condition_id', '')[:50]}...")
        if p.get("cur_price") is not None:
            cur_value = size * p["cur_price"]
            pnl = cur_value - value
            print(f"    Current:   ${p['cur_price']:.4f}  Value: ${cur_value:.2f}  P&L: ${pnl:+.2f}")
        print()

    print(f"  Total cost basis: ${total_value:.2f}")


if __name__ == "__main__":
    main()
