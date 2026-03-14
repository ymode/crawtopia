#!/usr/bin/env python3
"""Browse active Polymarket prediction markets."""

import argparse
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(__file__))
from _client import get


def main():
    parser = argparse.ArgumentParser(description="Browse Polymarket prediction markets")
    parser.add_argument("--query", "-q", help="Search term or tag to filter markets")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default 10)")
    args = parser.parse_args()

    params = f"?limit={args.limit}"
    if args.query:
        params += f"&query={urllib.parse.quote(args.query)}"

    data = get(f"/api/v1/polymarket/markets{params}", auth=False)

    if not data:
        print("No active markets found.")
        return

    print(f"=== Active Markets ({len(data)}) ===\n")
    for m in data:
        q = m.get("question", "Unknown")
        cid = m.get("condition_id", "")
        prices = m.get("outcome_prices", [])
        tokens = m.get("tokens", [])
        vol = m.get("volume", 0)
        liq = m.get("liquidity", 0)

        price_str = ""
        if prices:
            price_str = " / ".join(f"{float(p)*100:.0f}c" for p in prices if p)
        elif tokens:
            price_str = " / ".join(
                f"{t.get('outcome', '?')}: {float(t.get('price', 0))*100:.0f}c"
                for t in tokens
            )

        print(f"  {q}")
        if price_str:
            print(f"    Prices: {price_str}")
        if vol:
            print(f"    Volume: ${vol:,.0f}  Liquidity: ${liq:,.0f}")
        print(f"    Condition ID: {cid}")
        if tokens:
            for t in tokens:
                print(f"    Token ({t.get('outcome', '?')}): {t.get('token_id', '')[:40]}...")
        print()


if __name__ == "__main__":
    main()
