#!/usr/bin/env python3
"""VRAM fill test (nv-3090, 2026-10-20): one T=0 request whose prompt is n_ctx - MARGIN tokens (corpus60k.txt
repeated with part markers, sized via /tokenize), 256 generated tokens, thinking off. Optional --frac to size the
prompt as a fraction of n_ctx (e.g. 0.5) for a decode-at-depth number. One JSON row appended to --out.

usage: long_prompt.py --label L --port P --out long.jsonl [--margin 700] [--frac 1.0]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
Q = "\n\nWrite a structured summary of the documents above: the main topics, and for each one two or three key points."


def post(port: int, path: str, body: dict, timeout: int = 3600) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--margin", type=int, default=700)
    ap.add_argument("--frac", type=float, default=1.0)
    a = ap.parse_args()
    props = json.load(urllib.request.urlopen(f"http://127.0.0.1:{a.port}/props"))
    n_ctx = int(props.get("default_generation_settings", {}).get("n_ctx") or props["n_ctx"])
    target = int(n_ctx * a.frac) - a.margin
    corpus = (HERE / "corpus60k.txt").read_text()
    parts, i = ["Below is a long collection of documents."], 0
    while True:
        parts.append(f"\n\n### Part {i + 1}\n\n" + corpus)
        i += 1
        text = "".join(parts)
        n = len(post(a.port, "/tokenize", {"content": text})["tokens"])
        if n >= target:
            break
    lo, hi = 0, len(text)
    while hi - lo > 200:  # trim to the target token count
        mid = (lo + hi) // 2
        n = len(post(a.port, "/tokenize", {"content": text[:mid]})["tokens"])
        lo, hi = (mid, hi) if n < target else (lo, mid)
    text = text[:lo] + Q
    body = {"messages": [{"role": "user", "content": text}], "max_tokens": 256, "temperature": 0.0, "seed": 1,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.time()
    row = {"label": a.label, "n_ctx": n_ctx, "frac": a.frac}
    try:
        t = post(a.port, "/v1/chat/completions", body)["timings"]
        n, ac = t["predicted_n"], t.get("draft_n_accepted", 0)
        row.update({"prompt_tokens": t["prompt_n"], "prefill_tps": round(t["prompt_per_second"], 1),
                    "decode_tps": round(t["predicted_per_second"], 2), "gen": n,
                    "ms_step": round(t["predicted_ms"] / max(1, n - ac), 3), "wall_s": round(time.time() - t0, 1)})
    except Exception as e:  # noqa: BLE001 - record the failure (OOM aborts the server)
        row["error"] = str(e)[:300]
    print(json.dumps(row), flush=True)
    with open(a.out, "a") as f:
        f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
