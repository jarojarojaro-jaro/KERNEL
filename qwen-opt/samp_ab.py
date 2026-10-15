#!/usr/bin/env python3
"""A/B helper for the sampler fast paths: sends web-UI / omp style requests to a running llama-server and prints
decode t/s plus an md5 of the seeded output (identical md5 between fast and slow builds = same tokens).

usage: samp_ab.py --port N
"""
import argparse
import hashlib
import json
import urllib.request

PROMPT = "Explain how a CPU cache works, with examples. Be detailed."
UI = {"temperature": 0.8, "top_k": 40, "top_p": 0.95, "min_p": 0.05, "repeat_penalty": 1.05, "seed": 11,
      "samplers": ["penalties", "dry", "top_n_sigma", "top_k", "typ_p", "top_p", "min_p", "xtc", "temperature"]}
TOOLS = [{"type": "function", "function": {"name": "read_file", "description": "Read a file from disk",
          "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]

CASES = {
    "plain": {},
    "reasoning_control": {"reasoning_control": True},
    "budget_2048": {"thinking_budget_tokens": 2048},
    "tools(lazy grammar)": {"tools": TOOLS},
    "logit_bias": {"logit_bias": [[100, -2.0], [200, 1.5]]},
}


def run(port, extra):
    body = {"messages": [{"role": "user", "content": PROMPT}], "max_tokens": 800, **UI, **extra}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    m = d["choices"][0]["message"]
    text = (m.get("reasoning_content") or "") + "|" + (m.get("content") or "") + "|" + json.dumps(m.get("tool_calls"))
    t = d["timings"]
    return t["predicted_per_second"], t["predicted_n"], hashlib.md5(text.encode()).hexdigest()[:10]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    a = ap.parse_args()
    for name, extra in CASES.items():
        tps, n, h = run(a.port, extra)
        print(f"{name:22s} {tps:6.1f} t/s  {n:4d} tok  md5 {h}", flush=True)


if __name__ == "__main__":
    main()
