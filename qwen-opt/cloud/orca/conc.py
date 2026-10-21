#!/usr/bin/env python3
"""Aggregate decode throughput with N concurrent chat requests against one llama-server slot pool.

usage: conc.py --port 18433 --label np2 --requests 2 --tokens 400
Prints one json line: aggregate t/s = total predicted tokens / wall time of the whole burst, plus per-request t/s.
"""
import argparse
import json
import threading
import time
import urllib.request

PROMPT = ("Explain in detail how a B-tree index works in a relational database: node layout, search, insertion "
          "with splits, deletion with merges, and why it suits disks. Use a concrete example with numbers.")


def one(port: int, tokens: int, out: list, idx: int) -> None:
    body = {"messages": [{"role": "user", "content": PROMPT}], "max_tokens": tokens,
            "temperature": 1.0, "seed": idx + 1, "cache_prompt": False}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        t = json.load(r)["timings"]
    out.append({"idx": idx, "wall": time.time() - t0, "n": t["predicted_n"],
                "tps": t["predicted_per_second"], "ms": t["predicted_ms"]})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=18433)
    ap.add_argument("--label", required=True)
    ap.add_argument("--requests", type=int, default=2)
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--out", default="/root/results/conc.jsonl")
    a = ap.parse_args()
    res: list = []
    t0 = time.time()
    th = [threading.Thread(target=one, args=(a.port, a.tokens, res, i)) for i in range(a.requests)]
    [t.start() for t in th]
    [t.join() for t in th]
    wall = time.time() - t0
    total = sum(r["n"] for r in res)
    rec = {"label": a.label, "requests": a.requests, "wall_s": round(wall, 2),
           "total_tokens": total, "aggregate_tps": total / wall if wall else 0,
           "per_request": res}
    with open(a.out, "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"{a.label}: {a.requests} req, aggregate {rec['aggregate_tps']:.1f} t/s, "
          f"per-request {[round(r['tps'], 1) for r in res]}")


if __name__ == "__main__":
    main()
