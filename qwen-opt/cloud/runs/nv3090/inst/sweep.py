#!/usr/bin/env python3
"""Per-request decode bench of a running llama-server (nv-3090, 2026-10-20).

Same prompts as spec_sweep.py (chat) and copy_prompts.json (mvs/short), but one JSON row per request
(label, set, prompt, temp, seed, n, ms, draft, accepted, md5) so ABBA pairs can be bootstrapped per (prompt, seed).

usage: sweep.py --label L --port P --set chat|mvs|short --temps 1.0 --seeds 1,2,3 --tokens 400 --out rows.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import time
import urllib.request

from spec_sweep import PROMPTS

HERE = pathlib.Path(__file__).resolve().parent


def chat(port: int, prompt: str, tokens: int, temp: float, seed: int, copy: bool) -> dict:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens, "temperature": temp,
            "seed": seed, "cache_prompt": copy}
    if copy:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=1200))
    m = d["choices"][0]["message"]
    text = (m.get("reasoning_content") or "") + "\x00" + (m.get("content") or "")
    t = d["timings"]
    return {"n": t["predicted_n"], "ms": t["predicted_ms"], "draft": t.get("draft_n", 0),
            "accepted": t.get("draft_n_accepted", 0), "md5": hashlib.md5(text.encode()).hexdigest()[:8]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--set", default="chat")
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--temps", default="1.0")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    copy = a.set != "chat"
    prompts = PROMPTS if not copy else json.loads((HERE / "copy_prompts.json").read_text())[a.set]
    chat(a.port, "Hi", 8, 0.0, 0, copy)  # warmup
    tot_n = tot_ms = tot_ac = 0
    with open(a.out, "a") as log:
        for temp in map(float, a.temps.split(",")):
            seeds = [1] if temp == 0.0 else list(map(int, a.seeds.split(",")))
            for name, p in prompts.items():
                for s in seeds:
                    r = chat(a.port, p, a.tokens, temp, s, copy)
                    row = {"label": a.label, "set": a.set, "prompt": name, "temp": temp, "seed": s, **r,
                           "time": time.time()}
                    log.write(json.dumps(row) + "\n")
                    log.flush()
                    tot_n += r["n"]; tot_ms += r["ms"]; tot_ac += r["accepted"]
    steps = tot_n - tot_ac
    print(f"{a.label} {a.set} T={a.temps}: {1000 * tot_n / tot_ms:.1f} t/s pooled, {tot_ms / steps:.2f} ms/step, "
          f"{tot_n / steps:.2f} tok/step", flush=True)


if __name__ == "__main__":
    main()
