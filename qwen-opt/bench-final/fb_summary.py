#!/usr/bin/env python3
"""Summary of the final XTX before/after runs (~/qwen-opt/bench-final/logs): one table per model, arms U0 / U1 / T,
every value the mean over passes/rounds with the per-pass values in brackets.

usage: fb_summary.py [LOGDIR]
"""
from __future__ import annotations

import collections
import glob
import json
import os
import statistics
import sys

D = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/qwen-opt/bench-final/logs")
MODELS = ["qwen", "uncensored", "lfm", "lfm-uncensored"]
ARMS = ["U0", "U1", "T"]


def rows(name: str) -> list[dict]:
    p = os.path.join(D, name)
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def fmt(v: list[float], nd: int = 1) -> str:
    if not v:
        return "—"
    m = statistics.mean(v)
    return f"{m:.{nd}f} [{' / '.join(f'{x:.{nd}f}' for x in v)}]" if len(v) > 1 else f"{m:.{nd}f}"


cell: dict[tuple, list] = collections.defaultdict(list)
for f in sorted(glob.glob(os.path.join(D, "lb.*.jsonl"))):
    _, model, arm, _r = os.path.basename(f)[:-len(".jsonl")].split(".")   # lb.<model>.<U|T>.r<i>.jsonl
    for l in open(f):
        try:
            r = json.loads(l)
        except ValueError:
            continue
        test = f"pp{r['n_prompt']}" if r["n_prompt"] else f"tg{r['n_gen']}"
        cell[(model, "lb-" + arm, test)].append(r["avg_ts"])
for r in rows("spec_sweep.jsonl"):
    model, arm, _ = r["label"].split(".")
    cell[(model, arm, "sweep_tps")].append(r["median_tps"])
    cell[(model, arm, "sweep_ms")].append(r["median_ms_step"])
    cell[(model, arm, "sweep_tok")].append(statistics.median(p["tok_step"] for p in r["prompts"].values()))
for r in rows("copy_bench.jsonl"):
    model, arm, _ = r["label"].split(".")
    s = r["set"]
    cell[(model, arm, f"{s}_tps")].append(r["median_tps"])
    cell[(model, arm, f"{s}_ms")].append(statistics.median(p["ms_step"] for p in r["prompts"].values()))
    cell[(model, arm, f"{s}_md5")].append(",".join(m for p in r["prompts"].values() for m in p["md5"]))
for r in rows("long.jsonl"):
    model, arm, _ = r["label"].split(".")
    for k in ("prompt_tokens", "prefill_tps", "ttft_s", "decode_tps", "draft_acceptance"):
        if r.get(k) is not None:
            cell[(model, arm, "long_" + k)].append(r[k])
for r in rows("vram.jsonl"):
    model, arm, _ = r["label"].split(".")
    if r.get("vram_loaded_mb") is not None:
        cell[(model, arm, "vram_mb")].append(r["vram_loaded_mb"])
        cell[(model, arm, "vram_delta_mb")].append(r["vram_loaded_mb"] - (r.get("vram_before_mb") or 0))
    cell[(model, arm, "n_ctx")].append(r.get("n_ctx"))

METRICS = [("lb", "pp512", "pp512 (llama-bench)", 1), ("lb", "pp4096", "pp4096", 1), ("lb", "tg128", "tg128", 2),
           ("srv", "sweep_tps", "czat spec_sweep T=1 t/s", 1), ("srv", "sweep_ms", "ms/krok", 2),
           ("srv", "sweep_tok", "tok/krok", 2), ("srv", "mvs_tps", "code-edit mvs T=0 t/s", 1),
           ("srv", "mvs_ms", "mvs ms/krok", 2), ("srv", "short_tps", "copy T=0 t/s", 1),
           ("srv", "long_prompt_tokens", "~32k: tokeny promptu", 0), ("srv", "long_prefill_tps", "~32k prefill t/s", 1),
           ("srv", "long_ttft_s", "~32k TTFT s", 2), ("srv", "long_decode_tps", "~32k decode t/s", 1),
           ("srv", "long_draft_acceptance", "~32k akceptacja draftu", 3),
           ("srv", "vram_mb", "VRAM po załadowaniu MiB (karta)", 0), ("srv", "vram_delta_mb", "VRAM serwera MiB", 0)]
for model in MODELS:
    print(f"\n## {model}\n| metryka | U0 upstream domyślny | U1 upstream + flagi prod. | T topka |\n|---|---|---|---|")
    for kind, key, name, nd in METRICS:
        if kind == "lb":
            vals = [fmt(cell.get((model, "lb-U", key), []), nd), "(= U0)", fmt(cell.get((model, "lb-T", key), []), nd)]
        else:
            vals = [fmt(cell.get((model, a, key), []), nd) for a in ARMS]
        if any(v not in ("—", "(= U0)") for v in vals):
            print(f"| {name} | " + " | ".join(vals) + " |")
    print("| n_ctx | " + " | ".join(str(cell.get((model, a, "n_ctx"), "—")) for a in ARMS) + " |")
    for s in ("mvs_md5", "short_md5"):
        m = {a: cell.get((model, a, s)) for a in ARMS if cell.get((model, a, s))}
        if m:
            print(f"<!-- {s}: {json.dumps(m)} -->")
