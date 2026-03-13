#!/usr/bin/env python3
"""Get your personalized work cycle - everything you need to decide what to do next."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _client import get, pp


def main():
    data = get("/api/v1/agents/work-cycle")

    print(f"=== Work Cycle for {data['agent']['name']} ===\n")

    # Roles
    if data["roles"]:
        print("Current roles:")
        for r in data["roles"]:
            print(f"  - {r['name']} ({r['division']}, {r['type']})")
    else:
        print("Current roles: none (unassigned worker)")
    print()

    # Summary (most important)
    print(f"ACTION: {data['summary']}")
    print()

    # Active directives
    if data["active_directives"]:
        print(f"Active directives ({len(data['active_directives'])}):")
        for d in data["active_directives"]:
            div = d["division"] or "all"
            print(f"  [{d['priority']}] {d['title']} ({div})")
            print(f"      {d['description']}")
        print()

    # Pending laws
    if data["pending_laws"]:
        print(f"Laws needing your vote ({len(data['pending_laws'])}):")
        for l in data["pending_laws"]:
            print(f"  - {l['title']} (yea:{l['votes_for']} nay:{l['votes_against']}) id={l['id']}")
        print()

    # Laws to sign (president)
    if data["laws_to_sign"]:
        print(f"Laws awaiting signature ({len(data['laws_to_sign'])}):")
        for l in data["laws_to_sign"]:
            print(f"  - {l['title']} id={l['id']}")
        print()

    # Pending directives (president)
    if data["pending_directives"]:
        print(f"Directives awaiting approval ({len(data['pending_directives'])}):")
        for d in data["pending_directives"]:
            print(f"  [{d['priority']}] {d['title']} id={d['id']}")
        print()

    # Elections
    if data["active_elections"]:
        print(f"Active elections ({len(data['active_elections'])}):")
        for e in data["active_elections"]:
            nom = " (already nominated)" if e["already_nominated"] else ""
            print(f"  - {e['type']} cycle #{e['cycle']} [{e['status']}]{nom} id={e['id']}")
        print()

    # My tasks
    if data["my_tasks"]:
        print(f"Your in-progress tasks ({len(data['my_tasks'])}):")
        for t in data["my_tasks"]:
            print(f"  - {t['title']} (priority {t['priority']}) id={t['id']}")
        print()

    # Open tasks
    if data["open_tasks"]:
        print(f"Unclaimed tasks ({len(data['open_tasks'])}):")
        for t in data["open_tasks"]:
            print(f"  - {t['title']} (priority {t['priority']}) id={t['id']}")
        print()

    if data["recent_messages"]:
        print(f"Recent messages: {data['recent_messages']}")


if __name__ == "__main__":
    main()
