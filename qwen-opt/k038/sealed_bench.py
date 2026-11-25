#!/usr/bin/env python3
"""K-038 holdout: decode t/s of a running llama-server on the sealed prompt set (factory/sealed/prompts.jsonl, 10 prompts:
5 new-writing / 5 copy-edit, PL+EN, multi-turn as stored), the same request body as spec_sweep.py (cache_prompt false).
Per temperature: median t/s over prompts, tok/step, ms/step; one row per temperature appended to --out.

usage: sealed_bench.py --port P --label L [--temps 1.0] [--seeds 1,2,3] [--tokens 400] [--out F]
"""
import argparse, json, os, statistics, time, urllib.request

SEALED = os.path.expanduser("~/qwen-opt/factory/sealed/prompts.jsonl")


def chat(port, messages, tokens, temp, seed):
    body = {"messages": messages, "max_tokens": tokens, "temperature": temp, "seed": seed, "cache_prompt": False}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=600))["timings"]
    return t["predicted_n"], t["predicted_ms"], t.get("draft_n_accepted", 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--temps", default="1.0")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sealed.jsonl"))
    a = ap.parse_args()
    entries = [json.loads(l) for l in open(SEALED)]
    chat(a.port, [{"role": "user", "content": "Hi"}], 16, 0.0, 0)  # warmup
    for temp in map(float, a.temps.split(",")):
        seeds = [1] if temp == 0.0 else list(map(int, a.seeds.split(",")))
        per = {}
        for e in entries:
            runs = [chat(a.port, e["messages"], a.tokens, temp, s) for s in seeds]
            n, ms, ac = (sum(r[i] for r in runs) for i in range(3))
            per[e["id"]] = {"tps": 1000 * n / ms, "tok_step": n / max(1, n - ac), "ms_step": ms / max(1, n - ac)}
        med = statistics.median(r["tps"] for r in per.values())
        mss = statistics.median(r["ms_step"] for r in per.values())
        tks = statistics.median(r["tok_step"] for r in per.values())
        print(f"{a.label} sealed T={temp}: median {med:6.2f} t/s, {tks:.3f} tok/step, {mss:.2f} ms/step", flush=True)
        with open(a.out, "a") as f:
            f.write(json.dumps({"label": a.label, "time": time.time(), "temp": temp, "median_tps": med,
                                "median_tok_step": tks, "median_ms_step": mss, "prompts": per}) + "\n")


if __name__ == "__main__":
    main()
