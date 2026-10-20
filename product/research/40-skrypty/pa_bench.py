#!/usr/bin/env python3
"""Report 40: the E0 prose set (prose_bench.PROMPTS, thinking off, 400 tok, no prompt cache) at a given temperature,
on a running llama-server started with LLAMA_SPEC_LOOKUP_LOG (per-step drafts + accepted count, one line per step).
Request order = log order: warmup "Hi" first, then seeds x prompts, exactly as below; pa_analyze.py relies on it.
One JSON row per request to --out: label, temp, prompt, seed, n, ms, draft, accepted, md5, text.

usage: pa_bench.py --label NAME --port P --temp T [--seeds 1,...,8] [--tokens 400] [--out pa.jsonl]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path.home() / "qwen-opt/xtxroadmap"))
from prose_bench import PROMPTS  # noqa: E402


def chat(port: int, prompt: str, tokens: int, seed: int, temp: float) -> dict:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens, "temperature": temp,
            "seed": seed, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=600))
    t = d["timings"]
    text = d["choices"][0]["message"].get("content") or ""
    return {"n": t["predicted_n"], "ms": t["predicted_ms"], "draft": t.get("draft_n", 0),
            "accepted": t.get("draft_n_accepted", 0), "md5": hashlib.md5(text.encode()).hexdigest()[:8], "text": text}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--temp", type=float, required=True)
    ap.add_argument("--seeds", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--out", default="pa.jsonl")
    ap.add_argument("--warmup", type=int, default=1)
    a = ap.parse_args()
    if a.warmup:
        chat(a.port, "Hi", 16, 0, a.temp)
    n = ms = 0.0
    with open(a.out, "a") as log:
        for seed in map(int, a.seeds.split(",")):
            for name, p in PROMPTS.items():
                r = chat(a.port, p, a.tokens, seed, a.temp)
                n += r["n"]; ms += r["ms"]
                log.write(json.dumps({"label": a.label, "temp": a.temp, "time": time.time(), "prompt": name,
                                      "seed": seed, **r}, ensure_ascii=False) + "\n")
                log.flush()
    print(f"{a.label} T={a.temp}: {1000 * n / ms:.2f} t/s over {int(n)} tokens", flush=True)


if __name__ == "__main__":
    main()
