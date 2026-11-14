#!/usr/bin/env python3
"""K-103 summary: spec_sweep medians per arm, llama-bench pp576 per ub, VRAM.  usage: summ.py <results dir>"""
import json, sys, pathlib, statistics
d = pathlib.Path(sys.argv[1])
rows = [json.loads(l) for l in (d / "spec_sweep.jsonl").read_text().splitlines() if l.strip()]
for r in rows:
    acc = statistics.median(p["acc"] for p in r["prompts"].values())
    print(f"{r['label']:20s} median {r['median_tps']:6.2f} t/s  ms/step {r['median_ms_step']:6.2f}  acc {acc:.3f}  "
          + " ".join(f"{k} {p['tps']:.1f}" for k, p in r["prompts"].items()))
for t in ("b11856", "v1.0.0"):
    f = d / f"bench-{t}.jsonl"
    if f.exists():
        for l in f.read_text().splitlines():
            j = json.loads(l)
            print(f"bench {t:7s} ub {j['n_ubatch']:3d} pp{j['n_prompt']} {j['avg_ts']:8.2f} ± {j['stddev_ts']:.2f} t/s  build {j.get('build_commit')} {j.get('build_number')}")
print((d / "vram.txt").read_text())
