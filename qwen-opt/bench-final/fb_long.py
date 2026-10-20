#!/usr/bin/env python3
"""Long-context run against a running llama-server: the frozen ~32k-token prompt (prompt32k.txt, built once from
long_ctx_bench.corpus(32000*3.3) so every arm gets the same bytes), T=0, 256 tokens, thinking off, no prompt cache.
Streams the answer: TTFT = client time from sending the request to the first generated text; prefill and decode t/s
come from the server's timings. One JSON row per run is appended to --out.

usage: fb_long.py --label L --port P [--prompt prompt32k.txt] [--out long.jsonl]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--prompt", default=str(HERE / "prompt32k.txt"))
    ap.add_argument("--out", default=str(HERE / "logs" / "long.jsonl"))
    a = ap.parse_args()
    q = pathlib.Path(a.prompt).read_text()
    body = {"messages": [{"role": "user", "content": q}], "max_tokens": 256, "temperature": 0, "stream": True,
            "cache_prompt": False, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://127.0.0.1:{a.port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    ttft = None
    timings = None
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
                timings = d["timings"]
    t = timings or {}
    acc = t["draft_n_accepted"] / t["draft_n"] if t.get("draft_n") else None
    res = {"label": a.label, "prompt_tokens": t.get("prompt_n"), "prefill_tps": round(t.get("prompt_per_second", 0), 1),
           "prefill_s": round(t.get("prompt_ms", 0) / 1000, 2), "ttft_s": round(ttft, 2) if ttft else None,
           "decode_tps": round(t.get("predicted_per_second", 0), 2), "gen_tokens": t.get("predicted_n"),
           "draft_acceptance": round(acc, 3) if acc is not None else None}
    print(json.dumps(res), flush=True)
    with open(a.out, "a") as f:
        f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()
