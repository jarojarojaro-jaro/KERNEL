#!/usr/bin/env python3
"""md5 gate client: the 6 spec_sweep chat prompts at T=0 and at T=1 seed 1 (400 tokens, server-default thinking),
md5 of reasoning + content per prompt. One JSON row per (prompt, temp) appended to --out.

usage: gate_chat.py --label L --port P --out gate.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request

from spec_sweep import PROMPTS


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    with open(a.out, "a") as log:
        for temp in (0.0, 1.0):
            for name, p in PROMPTS.items():
                body = {"messages": [{"role": "user", "content": p}], "max_tokens": 400, "temperature": temp,
                        "seed": 1, "cache_prompt": False}
                req = urllib.request.Request(f"http://127.0.0.1:{a.port}/v1/chat/completions",
                                             data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
                d = json.load(urllib.request.urlopen(req, timeout=600))
                m = d["choices"][0]["message"]
                text = (m.get("reasoning_content") or "") + "\x00" + (m.get("content") or "")
                t = d["timings"]
                row = {"label": a.label, "prompt": name, "temp": temp, "md5": hashlib.md5(text.encode()).hexdigest()[:8],
                       "n": t["predicted_n"], "draft": t.get("draft_n", 0), "accepted": t.get("draft_n_accepted", 0)}
                print(json.dumps(row), flush=True)
                log.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
