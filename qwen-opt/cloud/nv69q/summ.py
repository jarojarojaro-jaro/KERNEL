#!/usr/bin/env python3
"""R69b Q1 summary: bench.jsonl -> median decode t/s per engine x block x T, ratio warp/fork; prefill; VRAM peaks.
   summ.py <results dir>"""
import csv
import json
import statistics
import sys
from collections import defaultdict

d = sys.argv[1]
rows = [json.loads(l) for l in open(f"{d}/bench.jsonl")]
med = {}
per = defaultdict(list)
for r in rows:
    if r.get("prompt") == "MEDIAN":
        med[(r["engine"], r["block"], r["temp"])] = (r["tps"], r.get("n_ok"))
    elif r.get("prompt") not in ("PRIME",) and not str(r.get("prompt", "")).startswith("cold") and r.get("tps"):
        per[(r["engine"], r["block"], r["temp"])].append(r)
engines = sorted({k[0] for k in med})
blocks = []
for k in med:
    if k[1] not in blocks:
        blocks.append(k[1])
print("block | T | " + " | ".join(engines) + " | W262k/F262k")
for b in blocks:
    for t in (0.0, 1.0):
        vals = {e: med.get((e, b, t), (None, 0)) for e in engines}
        f, w = vals.get("F262k", (None,))[0], vals.get("W262k", (None,))[0]
        ratio = f"{w / f:.3f}" if f and w else "-"
        cells = " | ".join(f"{v[0]:.1f} ({v[1]})" if v[0] else "-" for v in vals.values())
        print(f"{b} | {t} | {cells} | {ratio}")
print("\nper prompt (tps; tokens n):")
for k, rs in sorted(per.items()):
    print(k, " ".join(f"{r['prompt']}={r['tps']:.1f}/{r['n']}" for r in rs))
print("\nprime / prefill / cached:")
for r in rows:
    if r.get("prompt") == "PRIME" or str(r.get("prompt", "")).startswith("cold"):
        print(r["engine"], r["block"], r["prompt"], "prompt_tokens", r.get("prompt_tokens"), "ttft", r.get("ttft_s"),
              "prefill_tps", r.get("prefill_tps"), "vram", r.get("vram"), r.get("error", ""))
print("\ncached tokens of the depth prompts (first of each block):")
seen = set()
for r in rows:
    k = (r.get("engine"), r.get("block"))
    if str(k[1]).startswith("depth") and r.get("prompt") not in ("PRIME", "MEDIAN") and k not in seen:
        seen.add(k)
        print(k, "prompt_tokens", r.get("prompt_tokens"), "cached", r.get("cached"), "ttft", r.get("ttft_s"))
# VRAM / power per phase from smi.csv + phases.txt
try:
    ph = [l.split() for l in open(f"{d}/phases.txt")]
    spans = {}
    for name, ev, ts in ph:
        spans.setdefault(name, [0, 0])[0 if ev == "start" else 1] = int(ts)
    import datetime
    smi = []
    for row in csv.reader(open(f"{d}/smi.csv")):
        try:
            ts = datetime.datetime.strptime(row[0].strip(), "%Y/%m/%d %H:%M:%S.%f").replace(
                tzinfo=datetime.timezone.utc).timestamp()  # container clock = UTC
            smi.append((ts, float(row[1].split()[0]), float(row[2].split()[0]), row[3].strip(), int(row[5].split()[0])))
        except Exception:
            pass
    print("\nphase: peak VRAM MiB, median power W under load (>150 W samples), power limit, median SM clock under load")
    for name, (a, b) in spans.items():
        s = [x for x in smi if a <= x[0] <= (b or 1e12)]
        load = [x for x in s if x[2] > 150]
        if s:
            print(name, max(x[1] for x in s), statistics.median(x[2] for x in load) if load else "-", s[0][3],
                  statistics.median(x[4] for x in load) if load else "-")
except FileNotFoundError:
    pass
