#!/usr/bin/env python3
"""Which server event breaks greedy reproducibility? Sends the same uncached greedy request before and after
other kinds of requests and prints where the outputs diverge.

usage: det_probe.py --port N
"""
import argparse
import json
import urllib.request

P = "Explain how a B-tree index works in a database, with an example."


def chat(port, messages, max_tokens, temperature, cache_prompt):
    body = json.dumps({"messages": messages, "max_tokens": max_tokens, "temperature": temperature, "seed": 7,
                       "cache_prompt": cache_prompt}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    m = d["choices"][0]["message"]
    return (m.get("reasoning_content") or "") + "\n" + (m.get("content") or "")


def diverge(a, b):
    n = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return "identical" if a == b else f"differs at char {n}: ...{a[max(0, n - 40):n + 20]!r} vs ...{b[max(0, n - 40):n + 20]!r}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    a = ap.parse_args()
    g = lambda: chat(a.port, [{"role": "user", "content": P}], 256, 0.0, False)
    r0 = g()
    print("repeat right away:      ", diverge(r0, g()))
    chat(a.port, [{"role": "user", "content": "Napisz krótkie opowiadanie o latarniku."}], 600, 0.0, False)
    print("after other greedy req: ", diverge(r0, g()))
    chat(a.port, [{"role": "user", "content": "Napisz krótkie opowiadanie o latarniku."}], 300, 1.0, False)
    print("after sampled req (T=1):", diverge(r0, g()))
    chat(a.port, [{"role": "user", "content": P}, {"role": "assistant", "content": r0[-1500:]},
                  {"role": "user", "content": "Summarize that in one sentence."}], 128, 1.0, True)
    print("after cached follow-up: ", diverge(r0, g()))
    chat(a.port, [{"role": "user", "content": "List 20 countries and capitals."}], 2000, 0.0, False)
    print("after long (2000) req:  ", diverge(r0, g()))


if __name__ == "__main__":
    main()
