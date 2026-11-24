#!/usr/bin/env python3
"""K-059: LocalMaxxing conditions (canonical reasoning-v1 / code-v1 from /api/agent-context, saved 2026-11-24 in
K-059-prompts.json; T=0, max 320 tokens, thinking on, batch 1, a nonce first line, no prompt cache) on a running
llama-server. One JSON line per run; at the end the median t/s per prompt.
usage: K-059.py --port P --out F.jsonl --arm LABEL --reps 3"""
import argparse, hashlib, json, os, statistics, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def post(port, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=600))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--reps", type=int, default=3)
    a = ap.parse_args()
    prompts = json.load(open(os.path.join(HERE, "K-059-prompts.json")))
    res_all = {}
    for p in prompts:
        assert hashlib.sha256(p["text"].encode()).hexdigest() == p["sha256"], p["id"]
        for i in range(a.reps):
            text = f"nonce: kq-{a.arm}-{i}-{time.time_ns()}\n" + p["text"]
            t0 = time.time()
            r = post(a.port, {"messages": [{"role": "user", "content": text}], "max_tokens": 320,
                              "temperature": 0, "seed": 1, "cache_prompt": False})
            t = r["timings"]
            out = r["choices"][0]["message"]
            n = t["predicted_n"]
            dn, da = t.get("draft_n"), t.get("draft_n_accepted")
            res = {"arm": a.arm, "id": p["id"], "rep": i, "prompt_n": t["prompt_n"], "tokens": n,
                   "finish": r["choices"][0]["finish_reason"], "decode_tps": round(t["predicted_per_second"], 1),
                   "prefill_tps": round(t["prompt_per_second"], 1), "wall_s": round(time.time() - t0, 1),
                   "draft_n": dn, "draft_acc": da,
                   "md5": hashlib.md5(((out.get("reasoning_content") or "") + (out.get("content") or "")).encode()).hexdigest()[:8]}
            print(json.dumps(res), flush=True)
            with open(a.out, "a") as f:
                f.write(json.dumps(res) + "\n")
            res_all.setdefault(p["id"], []).append(res["decode_tps"])
    for k, v in res_all.items():
        print(f"RESULT K-059 {a.arm} {k}: median {statistics.median(v):.1f} t/s (runs {v}, tokens >= 256 required)")


if __name__ == "__main__":
    main()
