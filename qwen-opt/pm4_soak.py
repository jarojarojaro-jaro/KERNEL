#!/usr/bin/env python3
"""Soak test of a running llama-server: many chat requests of mixed length, repeated greedy requests must match,
multi-turn follow-ups exercise the prompt cache. Stops after --seconds. Exit code 1 on any error or mismatch.
Greedy requests are sent with cache_prompt=false: a prompt restored from the cache is not bit-reproducible
(different prefill chunking), so only uncached repeats are compared.

usage: pm4_soak.py --port N [--seconds 240]
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.request

PROMPTS = [
    "Explain how a B-tree index works in a database, with an example.",
    "Napisz krótkie opowiadanie o latarniku i sztormie.",
    "Write a Python class implementing an LRU cache with type hints.",
    "Wyjaśnij różnicę między TCP a UDP w trzech akapitach.",
    "List 20 countries and their capitals as a markdown table.",
]


def chat(port, messages, max_tokens, temperature, cache_prompt=True):
    body = json.dumps({"messages": messages, "max_tokens": max_tokens, "temperature": temperature, "seed": 7,
                       "cache_prompt": cache_prompt}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    msg = d["choices"][0]["message"]
    text = (msg.get("reasoning_content") or "") + "\n" + (msg.get("content") or "")
    return text, d["timings"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--seconds", type=int, default=240)
    a = ap.parse_args()
    t_end = time.time() + a.seconds
    ref = {}
    n_req = n_tok = n_cmp = 0
    i = 0
    while time.time() < t_end:
        p = PROMPTS[i % len(PROMPTS)]
        max_tokens = [256, 1024, 2048][i % 3]
        # greedy request without the prompt cache: must be identical every time it repeats
        text, tm = chat(a.port, [{"role": "user", "content": p}], max_tokens, 0.0, cache_prompt=False)
        h = hashlib.md5(text.encode()).hexdigest()
        key = (p, max_tokens)
        if key in ref:
            n_cmp += 1
            if ref[key] != h:
                print(f"MISMATCH on repeat: {key}", flush=True)
                sys.exit(1)
        ref.setdefault(key, h)
        # follow-up turn reuses the cached prompt
        text2, tm2 = chat(a.port, [{"role": "user", "content": p}, {"role": "assistant", "content": text[-2000:]},
                                   {"role": "user", "content": "Summarize that in one sentence."}], 128, 1.0)
        n_req += 2
        n_tok += tm["predicted_n"] + tm2["predicted_n"]
        print(f"req {n_req}: {tm['predicted_n']} tok {tm['predicted_per_second']:.1f} t/s, follow-up prompt "
              f"{tm2['prompt_n']} new tok", flush=True)
        i += 1
    print(f"OK: {n_req} requests, {n_tok} generated tokens, {n_cmp} greedy repeats compared, no mismatch")


if __name__ == "__main__":
    main()
