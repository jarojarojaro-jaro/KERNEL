#!/usr/bin/env python3
"""Quality gate for a kernel that changes numerics: capture the top-N next-token distributions of a running
llama-server for a fixed text, then compare two captures (e.g. GGML_CUDA_KVQ=0 vs 1).

usage:
  kl.py capture --port P --out FILE [--tokens 64] [--nprobs 20]
  kl.py compare --a FILE --b FILE

Captures come from /completion with echo+logprobs so every prompt position yields the top-N distribution of the
next token. compare reports the truncated KL (both renormalised over the union of the two top-N sets), the top-1
agreement and the perplexity of the *reference* text under each capture (mass assigned to the actual next token is
not in the top-N; we therefore report KL and top-1 agreement, which is what a quantised-KV kernel can disturb).

Texts are the same as spec_sweep so the results are comparable with the throughput runs.
"""
from __future__ import annotations

import argparse
import json
import math
import urllib.request

PROMPTS = [
    "The harbour master logged every ship that entered the bay: its flag, its draught, the hour it crossed the bar.",
    "Explain how a B-tree index works in a relational database: node layout, search, insertion with splits.",
    "Napisz krotkie opowiadanie o latarniku i sztormie, ktory zniszczyl stary pomost w porcie.",
    "def lru_cache(capacity): return lambda f: f  # a fragment of Python source used as a fixed reference text",
]


def completion(port: int, prompt: str, tokens: int, nprobs: int) -> dict:
    # copied text is generated token by token, so every position yields the top-N distribution of the next token
    body = {"prompt": prompt, "n_predict": tokens, "temperature": 0.0, "n_probs": nprobs,
            "cache_prompt": False, "top_k": 0, "top_p": 1.0}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def capture(port: int, tokens: int, nprobs: int) -> list[dict]:
    out = []
    for p in PROMPTS:
        resp = completion(port, p, tokens, nprobs)
        pos = [{"tok": cp.get("token_id"),
                "top": [(t["id"], t["logprob"]) for t in cp.get("top_logprobs", [])]}
               for cp in resp.get("completion_probabilities", [])
               if cp.get("top_logprobs")]
        out.append({"prompt": p, "positions": pos})
    return out


def norm(top: list[tuple[int, float]]) -> dict[int, float]:
    m = max(lp for _, lp in top) if top else 0.0
    w = {i: math.exp(lp - m) for i, lp in top}
    s = sum(w.values()) or 1.0
    return {i: v / s for i, v in w.items()}


def compare(a: list[dict], b: list[dict]) -> tuple[float, float, int, int, list[int]]:
    """Distributions are compared only up to the first top-1 divergence: after it the two runs see different
    contexts, so a per-position KL would be comparing different inputs."""
    kls, hits, n = [], 0, 0
    divs: list[int] = []
    for ca, cb in zip(a, b):
        div = -1
        for i, (pa, pb) in enumerate(zip(ca["positions"], cb["positions"])):
            da, db = norm(pa["top"]), norm(pb["top"])
            if not da or not db:
                continue
            keys = set(da) | set(db)
            # renormalise both over the union: truncated KL, unbiased for the top-N head
            sa = sum(da.get(k, 0.0) for k in keys) or 1.0
            sb = sum(db.get(k, 0.0) for k in keys) or 1.0
            kl = 0.0
            for k in keys:
                p = da.get(k, 0.0) / sa
                q = db.get(k, 0.0) / sb
                if p > 0 and q > 0:
                    kl += p * math.log(p / q)
            kls.append(kl)
            n += 1
            if not (pa["top"] and pb["top"] and pa["top"][0][0] == pb["top"][0][0]):
                div = i
                break
            hits += 1
        divs.append(div)
    mean_kl = sum(kls) / len(kls) if kls else float("nan")
    return mean_kl, hits / n if n else float("nan"), hits, n, divs


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--port", type=int, default=18440)
    c.add_argument("--out", required=True)
    c.add_argument("--tokens", type=int, default=64)
    c.add_argument("--nprobs", type=int, default=20)
    m = sub.add_parser("compare")
    m.add_argument("--a", required=True)
    m.add_argument("--b", required=True)
    a = ap.parse_args()
    if a.cmd == "capture":
        data = capture(a.port, a.tokens, a.nprobs)
        with open(a.out, "w") as f:
            json.dump(data, f)
        print(f"captured {sum(len(x['positions']) for x in data)} positions -> {a.out}")
    else:
        A = json.load(open(a.a))
        B = json.load(open(a.b))
        kl, agree, hits, n, divs = compare(A, B)
        print(f"compared positions {n}, truncated KL(vec||kvq) = {kl:.5f}, top-1 agreement = {agree*100:.2f}% "
              f"({hits}/{n}), top-1 divergence per prompt: {divs} (-1 = none in 64 positions)")


if __name__ == "__main__":
    main()
