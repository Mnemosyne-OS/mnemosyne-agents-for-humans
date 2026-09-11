"""CLI entry point: `python -m watcher [prompt]`.

With no argument it runs the standup: read the other agents, check for a
collision, file what matters. With an argument it passes your sentence straight
to the agent, so the same binary is both the demo and a REPL.
"""

from __future__ import annotations

import sys

from .agent import watcher_agent
from .model import ModelUnavailable

STANDUP = (
    "Give me the standup for this machine. Which coding-agent sessions are "
    "there, which ones have shown a sign of life recently, and are any two of "
    "them live in the same working tree and branch right now? If there is a "
    "real collision, file it in my backlog and put a follow-up in my calendar. "
    "Keep your status card up to date while you work."
)


def main() -> int:
    prompt = " ".join(sys.argv[1:]).strip() or STANDUP
    try:
        with watcher_agent() as (agent, info):
            print(
                f"model: {info['model']}\n"
                f"mcp:   {info['mcp']} ({info['tools']} tools)\n",
                flush=True,
            )
            agent(prompt)
    except ModelUnavailable as exc:
        # A provider that cannot be built is named, never silently swapped:
        # a demo that quietly ran on a different model proves nothing.
        print(f"model unavailable: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface the real reason, then exit
        print(f"run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
