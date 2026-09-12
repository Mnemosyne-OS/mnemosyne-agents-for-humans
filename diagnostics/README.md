# Diagnostics

Three scripts kept because they are the evidence behind a design decision in
`watcher/agent.py`, not because the agent needs them.

| Script | What it establishes |
|---|---|
| `check_wiring.py` | Python -> Strands -> npx -> the published MCP server, with no model and no credentials. 23 tools reachable. |
| `bisect_tools.py` | Which tool schema a model provider rejects. Bisects the real tool list, and **refuses to bisect when the endpoint is unreachable** — a network failure is not a verdict on a schema, and bisecting through one names a culprit at random. |
| `confirm_union.py` | The four-arm confirmation: one tool as-is (502) vs flattened (200), and all 23 as-is (502) vs flattened (200). |

The finding: Gemini's function-calling schema has no union types, so a single
tool declaring `"type": ["string", "null"]` fails the **whole** request. Two of
the 23 tools do — `mnemosyne_todo_update` and `mnemosyne_agenda_update` — and
`_sanitise()` flattens them before the agent is built.

Run them from the repository root with the venv's interpreter, with a `.env` in
place.
