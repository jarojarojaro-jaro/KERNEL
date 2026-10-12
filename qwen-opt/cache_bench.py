#!/usr/bin/env python3
"""Prompt-cache scenarios against a running llama-server: how many prompt tokens get (re)processed.

  S1 follow-up question in the same chat (history = doc + answer)
  S2 new chat, same document, different question (prefix shared up to the question)
  S3 switch to another long chat and back, then follow up in the first one

usage: cache_bench.py --label L [--port 8080] [--doc-tokens 30000]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request

from long_ctx_bench import corpus


def chat(port: int, messages: list[dict]) -> tuple[str, dict]:
    body = {"messages": messages, "max_tokens": 64, "temperature": 0, "cache_prompt": True}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=3600))
    return d["choices"][0]["message"].get("content") or "", d["timings"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--doc-tokens", type=int, default=30000)
    a = ap.parse_args()

    text = corpus(int(a.doc_tokens * 3.3 * 2))
    half = len(text) // 2
    doc_a, doc_b = text[:half], text[half:]

    def user(doc: str, q: str) -> dict:
        return {"role": "user", "content": "Documents:\n\n" + doc + "\n\n" + q}

    rows = []

    def run(name: str, messages: list[dict]) -> str:
        t0 = time.time()
        out, t = chat(a.port, messages)
        rows.append({"step": name, "prompt_n": t["prompt_n"], "cache_n": t.get("cache_n"),
                     "prompt_s": round(t["prompt_ms"] / 1000, 2), "wall_s": round(time.time() - t0, 2)})
        print(json.dumps({"label": a.label, **rows[-1]}), flush=True)
        return out

    q1, q2, q3 = "List the three main topics.", "What is said about performance?", "Summarize the first section."
    ans = run("A turn1 (cold)", [user(doc_a, q1)])
    run("S1 A follow-up", [user(doc_a, q1), {"role": "assistant", "content": ans}, {"role": "user", "content": q2}])
    run("S2 A new chat, other question", [user(doc_a, q3)])
    run("B turn1 (other doc)", [user(doc_b, q1)])
    run("S3 back to A follow-up", [user(doc_a, q1), {"role": "assistant", "content": ans}, {"role": "user", "content": q3}])
    with open("cache_bench.jsonl", "a") as f:
        f.write(json.dumps({"label": a.label, "time": time.time(), "rows": rows}) + "\n")


if __name__ == "__main__":
    main()
