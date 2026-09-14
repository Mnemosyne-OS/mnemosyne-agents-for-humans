# Watcher — the agent that tells you what your other agents did

**Demo video (2 min 43):** https://youtu.be/jSU2gm1HrkY

You run several coding agents at once. By the evening you have four sessions
across three repositories and no idea which of them touched what, which one is
still alive, or whether two of them are about to commit over each other.

Watcher is a [Strands Agents](https://strandsagents.com) agent that reads what
those sessions already wrote to disk, and files the result where you already
look: your backlog, your calendar, and a status card on your canvas.

It handles one ordinary task end to end, and it does it without you opening
anything.

## What it actually does

```
$ python -m watcher

model: Anthropic API · claude-sonnet-4-5-20250929
mcp:   @mnemosyne_os/mcp@1.9.0 (23 tools)

I pinned a card on your canvas and looked at the machine.

11 agent sessions on disk, 3 with a sign of life in the last 10 minutes.

⚠ Two of them are in the same working tree AND the same branch:
   _MNEMOSYNE OS @ main   last line 2 min ago   (this one is me)
   _MNEMOSYNE OS @ main   last line 6 min ago

That is the case where `git add -A` takes the other session's work into your
commit. I put it at the top of your backlog and left a follow-up on Friday.
Card closed.
```

## Why this is an agent *for humans*

Three decisions carry the whole thing, and each one is a refusal.

**It never says an agent is "working".** A transcript records the last line a
session wrote. A session that crashed also stops writing, so "quiet" and "dead"
look identical from the outside. The only honest sentence is *last sign of life
N minutes ago*, and that is the only one it is allowed to say. An agent that
reported "3 agents working" while one of them had died an hour ago would be
worse than no agent at all.

**A value it could not read is absent, not zero.** No project recorded is not
the same fact as "no project". Two sessions that both recorded nothing are not
evidence that they share a working tree — that is a fabricated alert, on the one
feature whose entire value is that you trust it.

**It proposes, you dispose.** It writes to your backlog and your calendar
because those are surfaces you already read and edit. It does not run git, does
not commit, does not stop another session. The interesting part of an agent is
not what it can do on its own; it is what it hands you.

## Architecture

```
                    ┌──────────────────────────────────┐
                    │  Watcher  (Strands Agents SDK)   │
                    │  system prompt = the 3 refusals  │
                    └────────────────┬─────────────────┘
                                     │ MCP, stdio
                    ┌────────────────▼─────────────────┐
                    │      @mnemosyne_os/mcp (npm)     │
                    │          23 tools                │
                    └────────────────┬─────────────────┘
                                     │ JSON-RPC, ws://127.0.0.1:7799
                    ┌────────────────▼─────────────────┐
                    │   Mnemosyne OS  (on YOUR machine)│
                    └──┬───────────┬──────────┬────────┘
                       │           │          │
        reads ─────────┘           │          └───────── writes
   transcripts other agents        │             (human review surfaces)
   already write to disk           │
   (Claude Code, Antigravity…)     │        • To-do backlog
                                   │        • Calendar
                            recalls│        • Status card on the canvas
                          decisions│
                      already made │
                   (vault memory)  │
```

Nothing in this repository talks to a cloud service except the model provider.
The transcripts, the memory and the three write surfaces are all local.

## The six tools it uses

| Tool | What it is for |
|---|---|
| `mnemosyne_agents` | what sessions exist, from any installed harness |
| `mnemosyne_agent_collisions` | are two of them live in the same tree and branch |
| `mnemosyne_query` | what the human already decided, so it does not re-propose it |
| `mnemosyne_todo_add` | file the work into the backlog |
| `mnemosyne_agenda_add` | put a dated follow-up in the calendar |
| `mnemosyne_cockpit_update` | its own status card, opened and closed |

## Run it

Requires [Mnemosyne OS](https://mnemosyne-os.io) running (it owns the memory and
the three write surfaces), Node 18+ and Python 3.11+.

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt   # Windows: .venv\Scripts\pip
cp .env.example .env                  # pick ONE provider (or ./setup-key.ps1 on Windows)
python -m watcher                     # the standup
python -m watcher "what did I decide about the updater?"
```

Fastest path on a machine that has no key of any kind: install
[Ollama](https://ollama.com), `ollama pull qwen3:8b`, and set
`MODEL_PROVIDER=ollama` in `.env`. With AWS credentials in the environment,
leaving `.env` out entirely runs on Amazon Bedrock, the default.

The first run downloads `@mnemosyne_os/mcp` through npx (about 20 seconds,
cached afterwards). The three things that can stop a fresh machine are named
on stderr and exit with their own code, before anything else starts:

| Message | Exit | What it means |
|---|---|---|
| `model unavailable: …` | 2 | the declared provider cannot be built (no key, no AWS credentials, unknown name) |
| `mcp unavailable: …` | 3 | Mnemosyne OS is not running, or npx could not fetch the MCP package |
| `run failed: …` | 1 | anything else, with the real exception name |

`setup-key.ps1` reads the key into a SecureString, so it never reaches the
terminal scrollback, the shell history, or a screen recording. It writes the
gitignored `.env`, then calls the endpoint that will actually be used and tells
you which of the two failures you have: a proxy that is not listening and a key
that was refused are different problems with different fixes. On any other
platform, copy `.env.example` to `.env` by hand.

The model provider is one declared variable, never guessed. A provider that
cannot be built says so and stops; it is never silently swapped for another,
because a demo that quietly ran on a different model proves nothing.

```bash
MODEL_PROVIDER=bedrock    # default.   AWS_REGION, BEDROCK_MODEL_ID
MODEL_PROVIDER=anthropic  #            ANTHROPIC_API_KEY
MODEL_PROVIDER=mnemosyne  #            MNEMO_PROXY_KEY
MODEL_PROVIDER=ollama     # offline.   OLLAMA_HOST, OLLAMA_MODEL_ID
```

Two of those are worth a sentence.

`mnemosyne` routes inference through Mnemosyne's own loopback brain proxy, an
OpenAI-compatible endpoint on `127.0.0.1:7439` that serves the inference the
human already pays for, metered and capped by the host. The agent's brain and
its memory then come from the same machine, and **no provider key is ever copied
into this repository** — the key stays sealed in the OS keystore where the app
put it.

`ollama` is not a fallback, it is the end of the argument: with a local model,
nothing about your machine, your repositories or your decisions leaves it.

## Disclosure of pre-existing work

Per the hackathon rules, what is new and what is not:

- **New, written for this hackathon:** everything in this repository — the
  Strands agent, its system prompt, the model selection, the CLI.
- **Pre-existing, used as a dependency:** [Mnemosyne OS](https://mnemosyne-os.io)
  and its MCP server [`@mnemosyne_os/mcp`](https://www.npmjs.com/package/@mnemosyne_os/mcp)
  (MIT, published on npm). Watcher launches the published package; no change was
  made to it for this submission. The transcript readers it exposes were built
  in August 2026.

## Licence

MIT. See [LICENSE](LICENSE).
