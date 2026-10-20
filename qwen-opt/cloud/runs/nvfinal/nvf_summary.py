#!/usr/bin/env python3
"""Tables of the final 3090 before/after run (runs/nvfinal, report 27): one table per results dir (= one model).
Rows: speculation first, then prefill/TTFT, llama-bench, VRAM. Values: mean over passes p1/p2 (ABBA) with the per-pass
values in brackets; T vs U0 / T vs U1 as % change of the mean (for ms and s: negative = faster).

usage: nvf_summary.py RESULTS_DIR [RESULTS_DIR ...]      (dir = .../nv-final-3090-<model>-<date>)
"""
from __future__ import annotations

import collections
import glob
import json
import os
import statistics
import sys

ARMS = ["U0", "U1", "T"]


def rows(p: str) -> list[dict]:
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def fmt(v: list[float], nd: int) -> str:
    if not v:
        return "—"
    m = statistics.mean(v)
    return f"{m:.{nd}f} [{' / '.join(f'{x:.{nd}f}' for x in v)}]" if len(v) > 1 else f"{m:.{nd}f}"


def pct(t: list[float], u: list[float]) -> str:
    if not t or not u:
        return "—"
    return f"{100 * (statistics.mean(t) / statistics.mean(u) - 1):+.1f}%"


def table(res: str) -> None:
    L = os.path.join(res, "logs")
    model = os.path.basename(res.rstrip("/")).split("-")[3]
    c: dict[tuple, list] = collections.defaultdict(list)
    for r in rows(os.path.join(L, "spec_sweep.jsonl")):
        _, arm, _ = r["label"].split(".")
        k = "chat1" if r["temp"] == 1.0 else "chat0"
        c[(arm, k + "_tps")].append(r["median_tps"])
        c[(arm, k + "_ms")].append(r["median_ms_step"])
        c[(arm, k + "_tok")].append(statistics.median(p["tok_step"] for p in r["prompts"].values()))
    for r in rows(os.path.join(L, "copy_bench.jsonl")):
        _, arm, _ = r["label"].split(".")
        s = r["set"]
        c[(arm, s + "_tps")].append(r["median_tps"])
        c[(arm, s + "_ms")].append(statistics.median(p["ms_step"] for p in r["prompts"].values()))
        c[(arm, s + "_tok")].append(statistics.median(p["tok_step"] for p in r["prompts"].values()))
    for r in rows(os.path.join(L, "long.jsonl")):
        _, arm, p = r["label"].split(".")
        if "error" in r or not r.get("gen_tokens"):
            c[(arm, f"err_{r['size']}")].append(1)
            continue
        t = "t0" if r["temp"] == 0.0 else "t1"
        for k in ("decode_tps", "ms_step", "tok_step"):
            c[(arm, f"L{r['size']}_{t}_{k}")].append(r[k])
        # prefill / TTFT: per pass the mean of its two cold requests (T=0, T=1)
        c[(arm, f"L{r['size']}_{p}_pre")].append(r["prefill_tps"])
        c[(arm, f"L{r['size']}_{p}_ttft")].append(r["ttft_s"])
        c[(arm, f"L{r['size']}_ntok")].append(r["prompt_tokens"])
    for arm in ARMS:
        for size in ("512", "2048", "16k", "32k", "60k"):
            for k in ("pre", "ttft"):
                for p in ("p1", "p2"):
                    v = c.pop((arm, f"L{size}_{p}_{k}"), [])
                    if v:
                        c[(arm, f"L{size}_{k}")].append(statistics.mean(v))
    for f in sorted(glob.glob(os.path.join(L, "lb*.jsonl"))):
        kind, _, a, _ = os.path.basename(f)[:-6].split(".")
        arm = "U0" if a == "U" else "T"
        for l in open(f):
            try:
                r = json.loads(l)
            except ValueError:
                continue
            d = r.get("n_depth", 0)
            test = (f"pp{r['n_prompt']}" if r["n_prompt"] else f"tg{r['n_gen']}") + (f"@{d // 1024}k" if d else "")
            c[(arm, "lb_" + test)].append(r["avg_ts"])
    for r in rows(os.path.join(L, "vram.jsonl")):
        _, arm, _ = r["label"].split(".")
        if "vram_loaded_mb" in r:
            c[(arm, "vram")].append(r["vram_loaded_mb"])
            c[(arm, "nctx")].append(float(r["n_ctx"]) if str(r["n_ctx"]).isdigit() else float("nan"))

    lg = {"chat": "logs/spec_sweep.jsonl", "cb": "logs/copy_bench.jsonl", "long": "logs/long.jsonl",
          "lb": f"logs/lb.{model}.U.r1,r4 / lb.{model}.T.r2,r3.jsonl",
          "lbd": f"logs/lbd.{model}.U.r1,r4 / lbd.{model}.T.r2,r3.jsonl", "vram": "logs/vram.jsonl"}
    M = [("chat T=1 (spec_sweep 6×3) t/s", "chat1_tps", 1, "chat"), ("chat T=1 ms/krok", "chat1_ms", 2, "chat"),
         ("chat T=1 tok/krok", "chat1_tok", 2, "chat"),
         ("chat T=0 greedy (6×1) t/s", "chat0_tps", 1, "chat"), ("chat T=0 ms/krok", "chat0_ms", 2, "chat"),
         ("chat T=0 tok/krok", "chat0_tok", 2, "chat"),
         ("code-edit mvs T=0 t/s", "mvs_tps", 1, "cb"), ("mvs ms/krok", "mvs_ms", 2, "cb"), ("mvs tok/krok", "mvs_tok", 2, "cb"),
         ("copy T=0 t/s", "short_tps", 1, "cb"), ("copy ms/krok", "short_ms", 2, "cb"), ("copy tok/krok", "short_tok", 2, "cb")]
    for size in ("512", "16k", "32k", "60k"):
        for t, tn in (("t0", "T=0"), ("t1", "T=1")):
            M.append((f"decode po {size} kontekstu {tn} t/s", f"L{size}_{t}_decode_tps", 1, "long"))
            M.append((f"decode po {size} {tn} ms/krok", f"L{size}_{t}_ms_step", 2, "long"))
    for size in ("512", "2048", "16k", "32k", "60k"):
        M.append((f"prefill {size} t/s", f"L{size}_pre", 1, "long"))
        M.append((f"TTFT {size} s", f"L{size}_ttft", 2, "long"))
    M.append(("tokeny promptu 512/2k/16k/32k/60k", None, 0, "long"))
    for test, src in (("pp512", "lb"), ("pp4096", "lb"), ("tg128", "lb"), ("tg128@16k", "lbd"), ("tg128@32k", "lbd"),
                      ("tg128@64k", "lbd")):
        M.append((f"llama-bench {test} t/s (diagn.)", "lb_" + test, 1, src))
    M += [("VRAM po załadowaniu MiB", "vram", 0, "vram"), ("n_ctx", "nctx", 0, "vram")]

    print(f"\n### {model}  (`{res}`)\n")
    print("| metryka | U0 | U1 | T | T vs U0 | T vs U1 | log |\n|---|---|---|---|---|---|---|")
    for name, key, nd, src in M:
        if key is None:
            vals = [", ".join(str(int(statistics.mean(c[(a, f'L{s}_ntok')]))) if c.get((a, f"L{s}_ntok")) else "—"
                              for s in ("512", "2048", "16k", "32k", "60k")) for a in ARMS]
            print(f"| {name} | " + " | ".join(vals) + f" | | | `{lg[src]}` |")
            continue
        v = {a: c.get((a, key), []) for a in ARMS}
        if key.startswith("lb_"):
            v["U1"] = []
        if not any(v.values()):
            continue
        cells = [fmt(v[a], nd) for a in ARMS]
        if key.startswith("lb_"):
            cells[1] = "(= U0)"
        print(f"| {name} | " + " | ".join(cells) + f" | {pct(v['T'], v['U0'])} | "
              f"{pct(v['T'], v['U1']) if not key.startswith('lb_') else '(= vs U0)'} | `{lg[src]}` |")
    errs = {k: len(v) for k, v in c.items() if k[1].startswith("err_")}
    if errs:
        print(f"\nBłędy long_bench (np. kontekst za mały): {errs}")


for d in sys.argv[1:]:
    table(d)
