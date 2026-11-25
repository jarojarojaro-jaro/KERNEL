#!/usr/bin/env python3
"""K-019 agent replay: the recorded omp agent requests (agentpath/bodies_w13.jsonl: 61 turns of 4 sessions, real system
prompt + tools, T=0, ignore_eos, 174-256 tokens) sent in order to a running llama-server, prompt cache on (each turn
prefills only its new tail). Per request: decode t/s, tok/step, draft stats, md5 of the generated text; one summary
row (sum of tokens / sum of decode ms) appended to --out.

usage: replay.py --port P --label L [--bodies F] [--out F]
"""
import argparse, hashlib, json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def post(port, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=900))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--bodies", default=os.path.expanduser("~/qwen-opt/agentpath/bodies_w13.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "replay.jsonl"))
    a = ap.parse_args()
    rows = []
    t0 = time.time()
    for i, line in enumerate(open(a.bodies)):
        b = json.loads(line)
        b["stream"] = False
        b["cache_prompt"] = True
        r = post(a.port, b)
        t = r["timings"]
        msg = r["choices"][0]["message"]
        text = (msg.get("reasoning_content") or "") + (msg.get("content") or "") + json.dumps(msg.get("tool_calls") or [])
        n, ac = t["predicted_n"], t.get("draft_n_accepted", 0)
        rows.append({"i": i, "n": n, "ms": t["predicted_ms"], "draft": t.get("draft_n", 0), "acc": ac,
                     "prompt_n": t.get("prompt_n", 0), "prompt_ms": t.get("prompt_ms", 0.0),
                     "md5": hashlib.md5(text.encode()).hexdigest()[:8]})
    n = sum(r["n"] for r in rows); ms = sum(r["ms"] for r in rows); ac = sum(r["acc"] for r in rows)
    s = {"label": a.label, "time": time.time(), "requests": len(rows), "tokens": n, "decode_ms": round(ms, 1),
         "tps": round(1000 * n / ms, 2), "tok_step": round(n / max(1, n - ac), 3), "ms_step": round(ms / max(1, n - ac), 3),
         "prefill_tokens": sum(r["prompt_n"] for r in rows), "prefill_ms": round(sum(r["prompt_ms"] for r in rows), 1),
         "wall_s": round(time.time() - t0, 1), "md5_all": hashlib.md5("".join(r["md5"] for r in rows).encode()).hexdigest()[:8],
         "rows": rows}
    with open(a.out, "a") as f:
        f.write(json.dumps(s) + "\n")
    print(f"{a.label}: {len(rows)} requests, {n} tokens, {s['tps']} t/s, {s['tok_step']} tok/step, {s['ms_step']} ms/step, "
          f"prefill {s['prefill_tokens']} tok {s['prefill_ms'] / 1000:.1f} s, wall {s['wall_s']} s, md5 {s['md5_all']}", flush=True)


if __name__ == "__main__":
    main()
