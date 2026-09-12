"""Confirm that union types (`"type": ["string","null"]`) are what the bridge rejects.

Three arms on the same tool: as-is, unions flattened to their first non-null
type, and nothing else changed. If flattening alone turns 502 into 200, the
cause is the union and not the tool.
"""

from __future__ import annotations

import copy
import json
import pathlib
import re
import urllib.error
import urllib.request

from watcher.agent import mnemosyne_client

URL = "http://127.0.0.1:7439/v1/chat/completions"
KEY = re.search(
    r"^MNEMO_PROXY_KEY=(.+)$", pathlib.Path(".env").read_text(encoding="utf-8"), re.M
).group(1).strip()


def flatten_unions(node):
    """Replace every `type: [a, b]` with its first non-null member."""
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "type" and isinstance(v, list):
                keep = [t for t in v if t != "null"]
                out[k] = keep[0] if keep else "string"
            else:
                out[k] = flatten_unions(v)
        return out
    if isinstance(node, list):
        return [flatten_unions(v) for v in node]
    return node


def has_union(node) -> bool:
    if isinstance(node, dict):
        if isinstance(node.get("type"), list):
            return True
        return any(has_union(v) for v in node.values())
    if isinstance(node, list):
        return any(has_union(v) for v in node)
    return False


def call(tools) -> int:
    body = {
        "model": "mnemosyne",
        "messages": [{"role": "user", "content": "Say OK."}],
        "tools": tools,
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return -1


def as_openai(spec, schema):
    return {
        "type": "function",
        "function": {
            "name": spec["name"],
            "description": (spec.get("description") or "")[:1024],
            "parameters": schema,
        },
    }


def main() -> None:
    client = mnemosyne_client()
    with client:
        specs = [t.tool_spec for t in client.list_tools_sync()]

    schemas = {s["name"]: (s.get("inputSchema") or {}).get("json") or {} for s in specs}
    by_name = {s["name"]: s for s in specs}

    offenders = sorted(n for n, sc in schemas.items() if has_union(sc))
    print("outils portant un type union :", offenders or "aucun")
    print()

    target = "mnemosyne_todo_update"
    raw = schemas[target]
    print("A. %-24s tel quel  : HTTP %d" % (target, call([as_openai(by_name[target], raw)])))
    flat = flatten_unions(copy.deepcopy(raw))
    print("B. %-24s aplati    : HTTP %d" % (target, call([as_openai(by_name[target], flat)])))
    print()

    all_raw = [as_openai(by_name[n], schemas[n]) for n in schemas]
    all_flat = [as_openai(by_name[n], flatten_unions(copy.deepcopy(schemas[n]))) for n in schemas]
    print("C. les 23 tels quels : HTTP %d" % call(all_raw))
    print("D. les 23 aplatis    : HTTP %d" % call(all_flat))


if __name__ == "__main__":
    main()
