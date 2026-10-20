#!/usr/bin/env python3
"""Prefill / TTFT / decode-with-speculation at increasing context against a running llama-server.

Prompt of size S = "Below is a long collection of documents.\n\n" + corpus60k.txt[:chars(S)] + summary question, the
same construction as bench-final/prompt32k.txt (the 32k size is byte-identical to it; corpus60k.txt is
long_ctx_bench.corpus(198000), frozen). Per size: one T=0 request and one T=1 seed 1 request, 256 tokens, thinking
off, cache_prompt false (both cold prefills). Streams: TTFT = client time to the first generated text; prefill and
decode t/s, ms/step and tok/step from the server's timings. One JSON row per request appended to --out.

usage: long_bench.py --label L --port P --out long.jsonl [--sizes 512,2048,16k,32k,60k]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
HEAD = "Below is a long collection of documents.\n\n"
Q = "\n\nWrite a structured summary of the documents above: the main topics, and for each one two or three key points."
CHARS = {"512": 1690, "2048": 6758, "16k": 54067, "32k": 105600, "60k": 198000}


def run(port: int, text: str, temp: float) -> dict:
    body = {"messages": [{"role": "user", "content": text}], "max_tokens": 256, "temperature": temp, "seed": 1,
            "stream": True, "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft = None
    t = {}
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode().strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            d = json.loads(line[6:])
            for c in d.get("choices", []):
                delta = c.get("delta", {})
                if ttft is None and (delta.get("content") or delta.get("reasoning_content")):
                    ttft = time.perf_counter() - t0
            if "timings" in d:
                t = d["timings"]
    n, ac, dr = t.get("predicted_n", 0), t.get("draft_n_accepted", 0), t.get("draft_n", 0)
    steps = n - ac
    return {"prompt_tokens": t.get("prompt_n"), "prefill_tps": round(t.get("prompt_per_second", 0), 1),
            "prefill_s": round(t.get("prompt_ms", 0) / 1000, 2), "ttft_s": round(ttft, 3) if ttft else None,
            "decode_tps": round(t.get("predicted_per_second", 0), 2), "gen_tokens": n,
            "ms_step": round(t.get("predicted_ms", 0) / steps, 3) if steps else None,
            "tok_step": round(n / steps, 3) if steps else None, "draft_acceptance": round(ac / dr, 3) if dr else None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sizes", default="512,2048,16k,32k,60k")
    a = ap.parse_args()
    corpus = (HERE / "corpus60k.txt").read_text()
    for size in a.sizes.split(","):
        text = HEAD + corpus[:CHARS[size] if size in CHARS else int(size[1:])] + Q  # "c<N>" = first N chars
        for temp in (0.0, 1.0):
            row = {"label": a.label, "size": size, "temp": temp}
            try:
                row.update(run(a.port, text, temp))
            except (urllib.error.URLError, OSError, ValueError) as e:
                row["error"] = str(e)[:300]
            print(json.dumps(row), flush=True)
            with open(a.out, "a") as f:
                f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
