#!/usr/bin/env python3
"""Short-document summaries on a running llama-server (fb-lcb17 style of long_ctx_bench.py: real documents, T=0,
256 tokens, thinking off) at ~1k / ~1.7k / ~3.4k prompt tokens (depth 1200 / 2000 / 4000), all below 8k context.
Appends one row in the spec_sweep shape (+ md5 per prompt) to OUT (default doc_bench.jsonl in the cwd).

usage: doc_bench.py --label NAME --port P [--out FILE]
"""
import argparse
import hashlib
import json
import os
import statistics
import sys
import time
import urllib.request

sys.path.insert(0, os.path.expanduser("~/qwen-opt"))
import long_ctx_bench as L  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", default="doc_bench.jsonl")
    a = ap.parse_args()

    def post(body):
        req = urllib.request.Request(f"http://127.0.0.1:{a.port}/v1/chat/completions", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=900))

    post({"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 16})  # warmup
    per = {}
    for depth in (1200, 2000, 4000):
        q = ("Below is a long collection of documents.\n\n" + L.corpus(int(depth * 3.3)) +
             "\n\nWrite a structured summary of the documents above: the main topics, and for each one "
             "two or three key points.")
        r = post({"messages": [{"role": "user", "content": q}], "max_tokens": 256, "temperature": 0,
                  "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}})
        t, m = r["timings"], r["choices"][0]["message"]
        n, ac, dr = t["predicted_n"], t.get("draft_n_accepted", 0), t.get("draft_n", 0)
        steps = n - ac
        per[f"doc{depth}"] = {"tps": t["predicted_per_second"], "tok_step": n / steps, "ms_step": t["predicted_ms"] / steps,
                              "acc": ac / dr if dr else 0.0, "prompt_n": t["prompt_n"],
                              "md5": [hashlib.md5(((m.get("reasoning_content") or "") + (m.get("content") or "")).encode()).hexdigest()[:8]]}
        v = per[f"doc{depth}"]
        print(f"{a.label} doc{depth} ({t['prompt_n']} tok): {v['tps']:.1f} t/s {v['tok_step']:.2f} tok/step "
              f"{v['ms_step']:.2f} ms/step md5 {v['md5'][0]}", flush=True)
    with open(a.out, "a") as f:
        f.write(json.dumps({"label": a.label, "time": time.time(), "set": "doc", "temp": 0.0,
                            "median_tps": statistics.median(v["tps"] for v in per.values()), "prompts": per}) + "\n")


if __name__ == "__main__":
    main()
