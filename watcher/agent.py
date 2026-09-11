"""The watcher agent.

Your coding agents worked all day across several repositories. This agent reads
what they actually did, warns you when two of them are live in the same working
tree right now, and files the result where you already look: your backlog, your
calendar, and a status card on your canvas.

It is built with the Strands Agents SDK. Every capability it has comes from one
MCP server, `@mnemosyne_os/mcp`, which it launches over stdio.

Two rules the system prompt enforces, because they are the difference between an
assistant and a liability:

1. It never claims an agent is "working". Transcripts record the last line an
   agent wrote, so the only honest statement is "last sign of life N minutes
   ago". An agent that crashed stops writing, and silence read as "idle" is the
   one failure mode that matters here.
2. It proposes; the human disposes. It writes to the backlog and the calendar
   because those are review surfaces the human reads and edits. It never runs
   git, never commits, never kills a session.
"""

from __future__ import annotations

import os
import platform
import shutil
from contextlib import contextmanager

from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.tools.mcp import MCPClient

from .model import build_model

#: Pinned so a judge's machine runs the same server this was demonstrated on.
MCP_PACKAGE = os.environ.get("MNEMO_MCP_PACKAGE", "@mnemosyne_os/mcp@1.9.0")

SYSTEM_PROMPT = """\
You are a watcher for a developer who runs several coding agents at once.

Your job, end to end:
1. Publish your own status card so the human can see you are on it
   (mnemosyne_cockpit_update, state "working", with a short title).
2. Read what other agent sessions exist on this machine (mnemosyne_agents).
3. Check whether two sessions are live in the SAME git working tree and branch
   (mnemosyne_agent_collisions). This is the hazard the human cares about: two
   agents staging the same index will commit each other's work.
4. Recall what the human already decided about anything you are about to raise
   (mnemosyne_query), so you never re-propose something they have rejected.
5. File what needs doing into their backlog (mnemosyne_todo_add) and put any
   dated follow-up in their calendar (mnemosyne_agenda_add).
6. Close your card (mnemosyne_cockpit_update, state "done") with one line saying
   what you filed. If you needed them and stopped, use "waiting" instead.

Rules you must not break:

- NEVER say an agent is "working" or "busy". The transcripts only record when a
  session last wrote a line. Say "last sign of life N minutes ago". A session
  that crashed also goes quiet, and you cannot tell the two apart.
- A value you could not read is ABSENT, not zero. Say "not reported", never 0.
- Only report a collision the tool actually returned. Two sessions with no
  project and no branch recorded are NOT evidence of a shared tree.
- Do not create a backlog list that does not exist unless the human asked for
  it. Put tasks in an existing list.
- You propose. You never run git, never commit, never stop another session.
- Be short. The human reads this between two other things.
"""


def _npx_command() -> str:
    """Resolve the npx entry point, which is not the same string on Windows."""
    if platform.system() == "Windows":
        return shutil.which("npx.cmd") or shutil.which("npx") or "npx.cmd"
    return shutil.which("npx") or "npx"


def mnemosyne_client() -> MCPClient:
    """An MCP client that launches the published Mnemosyne server over stdio.

    Strands takes a FACTORY, not an open connection, so it can re-establish the
    session when it needs to.
    """
    command = _npx_command()

    def factory():
        return stdio_client(
            StdioServerParameters(command=command, args=["-y", MCP_PACKAGE])
        )

    return MCPClient(factory)


@contextmanager
def watcher_agent():
    """Yield (agent, description) with the MCP session open for its lifetime."""
    model, model_desc = build_model()
    client = mnemosyne_client()
    with client:
        tools = client.list_tools_sync()
        agent = Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)
        yield agent, {"model": model_desc, "tools": len(tools), "mcp": MCP_PACKAGE}
