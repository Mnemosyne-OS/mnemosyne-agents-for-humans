"""Connectivity check: no model, no credentials. Proves Python -> npx -> MCP."""
import sys

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from watcher.agent import mnemosyne_client, MCP_PACKAGE

client = mnemosyne_client()
with client:
    tools = client.list_tools_sync()
    names = sorted(getattr(t, "tool_name", None) or t.tool_spec["name"] for t in tools)
    print(f"MCP {MCP_PACKAGE}: {len(names)} tools reachable from Strands")
    need = ["mnemosyne_agents", "mnemosyne_agent_collisions", "mnemosyne_todo_add",
            "mnemosyne_agenda_add", "mnemosyne_cockpit_update", "mnemosyne_query"]
    for n in need:
        print(("  OK   " if n in names else "  MISS ") + n)
