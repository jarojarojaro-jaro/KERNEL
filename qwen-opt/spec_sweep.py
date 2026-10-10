#!/usr/bin/env python3
"""Measure decode t/s and draft acceptance of a running llama-server on a fixed EN/PL prompt set.

Speculative settings (draft length, p_min) are server-level: restart the server per config
(`DRAFT_N=.. P_MIN=.. run-llm.sh`) and pass a --label. Rows are appended to spec_sweep.jsonl.

usage: spec_sweep.py --label NAME [--port 8080] [--tokens 400] [--temps 1.0] [--seeds 1,2]
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request

PROMPTS = {
    "pl-proza": "Napisz opowiadanie (około 800 słów) o starym latarniku, który pewnej sztormowej nocy dostaje sygnał z okrętu, który zatonął 50 lat temu. Opisz dokładnie miejsce, pogodę, jego wspomnienia i zakończ zaskakującym zwrotem akcji.",
    "pl-tech": "Wyjaśnij krok po kroku, jak działa protokół TCP: nawiązywanie połączenia, numery sekwencyjne, okno przesuwne, kontrola przeciążenia i zamykanie połączenia. Do każdego etapu podaj przykład z liczbami.",
    "pl-kod": "Napisz w Pythonie klasę LRUCache z metodami get i put (O(1)), z type hintami, docstringami i testami w pytest.",
    "en-chat": "Hey! How are you doing today? Tell me a bit about what you like to talk about.",
    "en-tech": "Explain how a B-tree index works in a relational database: node layout, search, insertion with splits, deletion with merges, and why it suits disks. Use a concrete example with numbers.",
    "en-code": "Write a complete Python module implementing a thread-safe LRU cache with TTL expiry: type hints, docstrings, and a full pytest test suite. Write all the code, no placeholders.",
}


def chat(port: int, prompt: str, tokens: int, temp: float, seed: int) -> dict:
    body = {"messages": [{"role": "user", "content": prompt}], "max_tokens": tokens, "temperature": temp,
            "seed": seed, "cache_prompt": False}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(req, timeout=600))["timings"]
    return {"tps": t["predicted_per_second"], "n": t["predicted_n"],
            "draft": t.get("draft_n", 0), "accepted": t.get("draft_n_accepted", 0), "ms": t["predicted_ms"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--tokens", type=int, default=400)
    ap.add_argument("--temps", default="1.0")
    ap.add_argument("--seeds", default="1,2")
    a = ap.parse_args()

    chat(a.port, "Hi", 16, 0.0, 0)  # warmup
    with open("spec_sweep.jsonl", "a") as log:
        for temp in map(float, a.temps.split(",")):
            per = {}
            for name, p in PROMPTS.items():
                runs = [chat(a.port, p, a.tokens, temp, s) for s in map(int, a.seeds.split(","))]
                n, ms = sum(r["n"] for r in runs), sum(r["ms"] for r in runs)
                dr, ac = sum(r["draft"] for r in runs), sum(r["accepted"] for r in runs)
                per[name] = {"tps": 1000 * n / ms, "acc": ac / dr if dr else 0.0}
            med = statistics.median(r["tps"] for r in per.values())
            cells = "  ".join(f"{k} {r['tps']:5.1f} ({r['acc']:.2f})" for k, r in per.items())
            print(f"{a.label} T={temp}: median {med:5.1f} | {cells}", flush=True)
            log.write(json.dumps({"label": a.label, "time": time.time(), "temp": temp, "median_tps": med,
                                  "prompts": per}) + "\n")


if __name__ == "__main__":
    main()
