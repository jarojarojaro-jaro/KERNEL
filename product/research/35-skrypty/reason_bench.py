#!/usr/bin/env python3
"""T=0 decode on the LocalMaxxing canonical prompts (reasoning-v1, code-v1; thinking on, report 32d §6 method without
submission): per prompt 1 warmup + NONCES runs, first line "[LocalMaxxing cache-bust nonce: <hex>]", max_tokens 512.
Server-side timings (predicted_per_second, draft_n, draft_n_accepted). Appends one row to OUT (default
reason_bench.jsonl in the cwd) in the spec_sweep/copy_bench shape plus md5 per nonce.

usage: reason_bench.py --label NAME --port P [--nonces 3] [--tokens 512] [--out FILE]
"""
import argparse
import hashlib
import json
import pathlib
import statistics
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
NONCES = ["3f9a1c2e", "b7d04e51", "5c2e8a9f", "e1a6730b", "9d4b2f68"]


def chat(port, text, tokens, nonce):
    body = {"messages": [{"role": "user", "content": f"[LocalMaxxing cache-bust nonce: {nonce}]\n{text}"}],
            "max_tokens": tokens, "temperature": 0.0, "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": True}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=600))
    m, t = r["choices"][0]["message"], r["timings"]
    out = (m.get("reasoning_content") or "") + (m.get("content") or "")
    return {"tps": t["predicted_per_second"], "n": t["predicted_n"], "ms": t["predicted_ms"],
            "draft": t.get("draft_n", 0), "accepted": t.get("draft_n_accepted", 0),
            "md5": hashlib.md5(out.encode()).hexdigest()[:8]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--nonces", type=int, default=3)
    ap.add_argument("--tokens", type=int, default=512)
    ap.add_argument("--out", default="reason_bench.jsonl")
    a = ap.parse_args()
    per = {}
    for name in ("reasoning-v1", "code-v1"):
        text = (HERE / f"{name}.txt").read_text()
        chat(a.port, text, 64, "00000000")  # warmup
        runs = [chat(a.port, text, a.tokens, n) for n in NONCES[:a.nonces]]
        n, ms = sum(r["n"] for r in runs), sum(r["ms"] for r in runs)
        dr, ac = sum(r["draft"] for r in runs), sum(r["accepted"] for r in runs)
        steps = n - ac
        per[name] = {"tps": 1000 * n / ms, "acc": ac / dr if dr else 0.0, "ms_step": ms / steps,
                     "tok_step": n / steps, "n": n, "md5": [r["md5"] for r in runs],
                     "tps_runs": [round(r["tps"], 2) for r in runs]}
        print(f"{a.label} {name}: {per[name]['tps']:.1f} t/s {per[name]['tok_step']:.2f} tok/step "
              f"{per[name]['ms_step']:.2f} ms/step acc {per[name]['acc']:.3f} md5 {','.join(per[name]['md5'])}",
              flush=True)
    with open(a.out, "a") as f:
        f.write(json.dumps({"label": a.label, "time": time.time(), "set": "lmx", "temp": 0.0,
                            "median_tps": statistics.median(v["tps"] for v in per.values()), "prompts": per}) + "\n")


if __name__ == "__main__":
    main()
