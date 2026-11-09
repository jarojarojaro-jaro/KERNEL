#!/usr/bin/env python3
"""Long-context decode on a running llama-server: per depth one fresh prompt of exactly DEPTH tokens of real text
(long_ctx_bench.py corpus) + a summary request, T=0, 256 tokens, thinking off, no prompt cache.
Per depth one JSON line (appended to --out): prefill/decode t/s, draft acceptance, verify steps, md5 of the text and
the CLOCK_MONOTONIC window of the request (to cut a rocprofv3 trace, see prof_step.py).

usage: lc.py --port P --label L --out lc.jsonl [--depths 1700,94000,199000] [--tokens 256]
"""
import argparse, hashlib, json, os, sys, time, urllib.request

sys.path.insert(0, os.path.expanduser("~/qwen-opt"))
from long_ctx_bench import corpus  # noqa: E402


def post(port, path, body):
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=3600))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--depths", default="1700,94000,199000")
    ap.add_argument("--tokens", type=int, default=256)
    a = ap.parse_args()
    depths = [int(x) for x in a.depths.split(",")]
    toks = post(a.port, "/tokenize", {"content": corpus(int(max(depths) * 4.2))})["tokens"]
    if len(toks) < max(depths):
        sys.exit(f"corpus too short: {len(toks)} tokens")
    for depth in depths:
        doc = post(a.port, "/detokenize", {"tokens": toks[:depth]})["content"]
        t0 = time.monotonic_ns()
        r = post(a.port, "/v1/chat/completions", {
            "messages": [{"role": "user", "content": "Below is a long collection of documents.\n\n" + doc +
                          "\n\nWrite a structured summary of the documents above: the main topics, and for each one "
                          "two or three key points."}],
            "max_tokens": a.tokens, "temperature": 0, "seed": 1, "cache_prompt": False,
            "chat_template_kwargs": {"enable_thinking": False}})
        t1 = time.monotonic_ns()
        m = r["choices"][0]["message"]
        text = (m.get("reasoning_content") or "") + (m.get("content") or "")
        t = r["timings"]
        acc = t.get("draft_n_accepted", 0)
        res = {"label": a.label, "depth": depth, "prompt_n": t["prompt_n"], "prefill_tps": round(t["prompt_per_second"], 1),
               "decode_tps": round(t["predicted_per_second"], 2), "gen": t["predicted_n"],
               "draft_n": t.get("draft_n", 0), "accepted": acc, "steps": t["predicted_n"] - acc,
               "ms_step": round(t["predicted_ms"] / max(1, t["predicted_n"] - acc), 3),
               "md5": hashlib.md5(text.encode()).hexdigest()[:8], "t0_ns": t0, "t1_ns": t1,
               "prompt_ms": t["prompt_ms"], "predicted_ms": t["predicted_ms"]}
        print(json.dumps(res), flush=True)
        with open(a.out, "a") as f:
            f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
