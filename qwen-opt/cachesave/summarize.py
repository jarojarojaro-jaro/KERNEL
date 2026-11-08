#!/usr/bin/env python3
"""cachesave results: A = production, B = #30137 port, C = B + LLAMA_SERVER_CACHE_HUGE=1 (THP + evicted-buffer reuse).
Kill: switch saving (median save alloc+get + load set) < 50 ms vs A, or any md5 difference."""
import json, statistics, sys
from collections import defaultdict
rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")]
by = defaultdict(list)
for r in rows: by[(r["label"][0], r["item"])].append(r)
med = lambda v: statistics.median(v) if v else float("nan")
for a in "ABC":
    rs = [r for r in by[(a, "switch")] if r["i"] >= 2]
    if not rs: continue
    sv = [r["save"] for r in rs if r["save"]]; ld = [r["load"] for r in rs if r["load"]]
    print(f"{a}: n={len(rs)} wall {med([r['wall_ms'] for r in rs]):.0f} ms, prompt_n {med([r['prompt_n'] for r in rs]):.0f}; "
          f"save alloc {med([s['alloc_ms'] for s in sv]):.1f} (buf {med([s['buf_ms'] for s in sv]):.1f}, ckpt {med([s['ckpt_copy_ms'] for s in sv]):.1f}) "
          f"get tgt {med([s['get_tgt_ms'] for s in sv]):.1f} ms = {med([r['save_gbps'] for r in rs if 'save_gbps' in r]):.2f} GB/s, "
          f"save total {med([s['alloc_ms'] + s['get_tgt_ms'] + s['get_dft_ms'] for s in sv]):.1f} ms; "
          f"load {med([l['set_ms'] for l in ld]):.1f} ms = {med([r['load_gbps'] for r in rs if 'load_gbps' in r]):.2f} GB/s; "
          f"update {med([r['update_ms'] for r in rs if r['update_ms'] is not None]):.1f} ms; tgt {med([s['tgt_mib'] for s in sv]):.0f} MiB")
for a in "ABC":
    print(a, "md5", sorted({(r["label"], r["md5"], r["tps"]) for r in by[(a, "md5")]}), "| sweep", [r["line"] for r in by[(a, "sweep")]])
