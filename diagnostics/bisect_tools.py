"""Find which MCP tool schema the brain proxy's OpenAI->Gemini bridge rejects.

Sends the real tool list to the proxy, then bisects on failure. Prints only
tool names and HTTP verdicts; no key and no memory content ever reach stdout.
"""

from __future__ import annotations

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


def as_openai(spec: dict) -> dict:
    """MCP tool spec -> OpenAI function spec, the way Strands sends it."""
    return {
        "type": "function",
        "function": {
            "name": spec["name"],
            "description": (spec.get("description") or "")[:1024],
            # Strands nests the real JSON Schema under "json"; sending the
            # wrapper makes every call malformed and every verdict worthless.
            "parameters": (spec.get("inputSchema") or {}).get("json")
            or {"type": "object", "properties": {}},
        },
    }


def try_tools(tools: list[dict]) -> tuple[int, str]:
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
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:  # noqa: BLE001
        return -1, str(e)[:200]


def main() -> None:
    client = mnemosyne_client()
    with client:
        specs = [t.tool_spec for t in client.list_tools_sync()]
    tools = [as_openai(s) for s in specs]
    print(f"{len(tools)} outils reels\n")

    code, err = try_tools(tools)
    print(f"les {len(tools)} ensemble : HTTP {code} {err}\n")
    if code == 200:
        print("tout passe — la panne n'est donc pas le simple fait de les envoyer")
        return

    # Bisect down to the smallest failing set.
    current = tools
    while len(current) > 1:
        half = len(current) // 2
        left, right = current[:half], current[half:]
        lc, _ = try_tools(left)
        print(f"  moitie gauche ({len(left):2d}) : HTTP {lc}")
        if lc != 200:
            current = left
            continue
        rc, _ = try_tools(right)
        print(f"  moitie droite ({len(right):2d}) : HTTP {rc}")
        if rc != 200:
            current = right
            continue
        print("  les deux moities passent seules — la panne vient de la TAILLE, "
              f"pas d'un outil ({len(current)} ensemble echouent)")
        return

    name = current[0]["function"]["name"]
    print(f"\nCOUPABLE : {name}")
    print(json.dumps(current[0]["function"]["parameters"], indent=2)[:1200])


if __name__ == "__main__":
    main()
