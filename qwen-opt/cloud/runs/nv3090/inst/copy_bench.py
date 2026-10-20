#!/usr/bin/env python3
"""Decode speed of a running llama-server on the copy/edit prompt set (copy_prompts.json), like spec_sweep.py.

usage: copy_bench.py --label NAME --port P [--set short|long] [--temps 0.0,1.0] [--seeds 1,2,3] [--tokens 512]
          [--out results.jsonl]
Thinking is off (the answer is the copy). The prompt cache is on: a prompt is prefilled once per server.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import statistics
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent


def chat(port: int, prompt: str, tokens: int, temp: float, seed: int) -> dict:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens, "temperature": temp,
            "seed": seed, "cache_prompt": True, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=1200))
    t = d["timings"]
    text = d["choices"][0]["message"].get("content") or ""
    return {"tps": t["predicted_per_second"], "n": t["predicted_n"], "draft": t.get("draft_n", 0),
            "accepted": t.get("draft_n_accepted", 0), "ms": t["predicted_ms"], "prompt_n": t.get("prompt_n", 0),
            "md5": hashlib.md5(text.encode()).hexdigest()[:8]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--set", default="short")
    ap.add_argument("--tokens", type=int, default=512)
    ap.add_argument("--temps", default="0.0,1.0")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(HERE / "copy_bench.jsonl"))
    a = ap.parse_args()

    prompts = json.loads((HERE / "copy_prompts.json").read_text())[a.set]
    if a.only:
        prompts = {k: v for k, v in prompts.items() if k in a.only.split(",")}
    chat(a.port, "Hi", 8, 0.0, 0)  # warmup
    with open(a.out, "a") as log:
        for temp in map(float, a.temps.split(",")):
            per = {}
            for name, p in prompts.items():
                seeds = [1] if temp == 0.0 else list(map(int, a.seeds.split(",")))
                runs = [chat(a.port, p, a.tokens, temp, s) for s in seeds]
                n, ms = sum(r["n"] for r in runs), sum(r["ms"] for r in runs)
                dr, ac = sum(r["draft"] for r in runs), sum(r["accepted"] for r in runs)
                steps = n - ac
                per[name] = {"tps": 1000 * n / ms, "ms_step": ms / steps, "tok_step": n / steps, "n": n,
                             "draft": dr, "acc": ac, "md5": [r["md5"] for r in runs],
                             "prompt_n": runs[0]["prompt_n"]}
            med = statistics.median(r["tps"] for r in per.values())
            cells = "  ".join(f"{k} {r['tps']:5.1f} ({r['tok_step']:.2f}t {r['ms_step']:.2f}ms)" for k, r in per.items())
            print(f"{a.label} T={temp}: median {med:5.1f} t/s | {cells}", flush=True)
            log.write(json.dumps({"label": a.label, "time": time.time(), "set": a.set, "temp": temp,
                                  "median_tps": med, "prompts": per}) + "\n")


if __name__ == "__main__":
    main()
