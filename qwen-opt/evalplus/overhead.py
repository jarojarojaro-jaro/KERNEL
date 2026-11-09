#!/usr/bin/env python3
"""Per-request overhead from <ds>.stats.jsonl: wall - prompt_ms - predicted_ms (median, p90), linear fit
prompt_ms = a + b * prompt_n (fixed TTFT cost), decode t/s for short (<400) vs long (>1500) answers.
  overhead.py RUN_DIR"""
import json, statistics, sys


def pct(v, p):
    v = sorted(v); return v[min(len(v) - 1, round(p / 100 * (len(v) - 1)))]


for ds in ("humaneval", "mbpp"):
    try:
        rows = [json.loads(l) for l in open(f"{sys.argv[1]}/{ds}.stats.jsonl") if l.strip()]
    except FileNotFoundError:
        continue
    t = [(r["wall_s"] * 1000, r["timings"]) for r in rows if r.get("timings")]
    ov = [w - x["prompt_ms"] - x["predicted_ms"] for w, x in t]
    xs = [x["prompt_n"] for _, x in t]; ys = [x["prompt_ms"] for _, x in t]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    b = sum((a - mx) * (c - my) for a, c in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    a = my - b * mx
    def tps(sel):
        s = [x for _, x in t if sel(x["predicted_n"])]
        return round(sum(x["predicted_n"] for x in s) / sum(x["predicted_ms"] for x in s) * 1000, 1) if s else None, len(s)
    wall = statistics.mean(w for w, _ in t)
    fixed = a + statistics.median(ov)
    print(f"{ds}: n={len(t)} overhead median {statistics.median(ov):.0f} ms p90 {pct(ov, 90):.0f} ms; "
          f"prompt_ms = {a:.0f} ms + {b:.2f} ms/tok; decode <400 tok {tps(lambda n: n < 400)}, >1500 tok {tps(lambda n: n > 1500)}; "
          f"fixed ~{fixed:.0f} ms = {100 * fixed / wall:.1f}% of mean answer {wall / 1000:.2f} s")
