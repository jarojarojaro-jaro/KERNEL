#!/usr/bin/env python3
"""Summary of l1tok results.jsonl: A (production) vs B (TOK_CACHE+PARSE_INC+STREAM_STEP), C = check mode.
Kill criteria (see NOTE.md): replay tokenize gain < 10 ms/turn at 90k+; stream decode tail slower than A by > 0.5%;
spec_sweep ms/step or greedy t/s worse beyond noise; any md5 / text difference; any MISMATCH in C."""
import json, statistics, sys
from collections import defaultdict

rows = [json.loads(l) for l in open(sys.argv[1] if len(sys.argv) > 1 else "results.jsonl")]
arm = lambda r: r["label"][0]
by = defaultdict(list)
for r in rows:
    by[(arm(r), r["item"])].append(r)
med = lambda v: statistics.median(v) if v else float("nan")

print("== replay (warm turns: cache_n > 0), 2 threads, 75-120k")
for a in "ABC":
    rs = [r for r in by[(a, "replay")] if (r.get("cache_n") or 0) > 0 and r.get("tokenize_ms") is not None]
    big = [r for r in rs if r["prompt_tokens"] >= 90000]
    if rs:
        print(f"  {a}: {len(rs)} turns, tokenize median {med([r['tokenize_ms'] for r in rs]):.1f} ms (90k+: {med([r['tokenize_ms'] for r in big]):.1f} ms, {len(big)} turns), "
              f"template {med([r['template_ms'] or 0 for r in rs]):.1f} ms, wall {med([r['wall_ms'] for r in rs]):.0f} ms, mismatch {sum(r['tok_mismatch'] for r in rs)}")
print("== stream 12k (tail = last 2k tokens)")
for a in "ABC":
    for s in (False, True):
        rs = [r for r in by[(a, "stream")] if r["stream"] == s]
        if rs:
            print(f"  {a} stream={s!s:5}: tail {med([r['tail_ms_per_token'] or 0 for r in rs]):.4f} ms/token, ms/step {med([r['ms_per_step'] or 0 for r in rs]):.3f}, "
                  f"server CPU {med([r['server_cpu_s'] for r in rs]):.1f} s, chunks {med([r['chunks'] for r in rs]):.0f}, text md5 {sorted({r['text_md5'] for r in rs})}")
print("== md5 / spec_sweep")
for a in "ABC":
    m = by[(a, "md5")]
    if m:
        print(f"  {a}: md5 {sorted({r['md5'] for r in m})}, greedy t/s {[r['tps'] for r in m]}")
    for r in by[(a, "sweep")]:
        print(f"  {r['label']}: {r['line']}")
