#!/usr/bin/env python3
"""Summarise an nsys sqlite export of a llama-server decode capture (nv-3090, 2026-10-20).

Prints: capture span, GPU busy (union of kernel+memcpy intervals) and idle, idle gaps by size, CUDA API call counts and
total times (graph launch/instantiate/update, kernel launch, syncs, memcpy), top kernels by time, and graph launches
per 'step' proxy (cudaStreamSynchronize count).
usage: prof_an.py <file.sqlite> [--top 25]
"""
import sqlite3
import sys
from collections import defaultdict


def main() -> None:
    db = sqlite3.connect(sys.argv[1])
    top = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 25
    q = db.execute
    names = dict(q("select id, value from StringIds"))
    kern = q("select start, end, shortName, demangledName from CUPTI_ACTIVITY_KIND_KERNEL order by start").fetchall()
    try:
        mem = q("select start, end, copyKind, bytes from CUPTI_ACTIVITY_KIND_MEMCPY order by start").fetchall()
    except sqlite3.OperationalError:
        mem = []
    try:
        gr = q("select start, end from CUPTI_ACTIVITY_KIND_GRAPH_TRACE").fetchall()
    except sqlite3.OperationalError:
        gr = []
    print(f"graph executions traced: {len(gr)}, total {sum(e - s for s, e in gr)/1e6:.1f} ms")
    ivs = sorted([(s, e) for s, e, *_ in kern] + [(s, e) for s, e, *_ in mem] + gr)
    t0, t1 = ivs[0][0], max(e for _, e in ivs)
    busy, cur_s, cur_e = 0, ivs[0][0], ivs[0][1]
    gaps = []
    for s, e in ivs[1:]:
        if s > cur_e:
            busy += cur_e - cur_s
            gaps.append(s - cur_e)
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    busy += cur_e - cur_s
    span = t1 - t0
    print(f"span {span/1e6:.1f} ms, GPU busy {busy/1e6:.1f} ms ({100*busy/span:.1f}%), idle {(span-busy)/1e6:.1f} ms")
    bins = [(0, 2e3), (2e3, 5e3), (5e3, 2e4), (2e4, 5e4), (5e4, 2e5), (2e5, 1e6), (1e6, 1e12)]
    for lo, hi in bins:
        g = [x for x in gaps if lo <= x < hi]
        print(f"  gaps {lo/1e3:>6.0f}-{hi/1e3:<8.0f}us: n={len(g):6d} total {sum(g)/1e6:8.2f} ms")
    print(f"kernels {len(kern)}, memcpy {len(mem)}")
    mk = defaultdict(lambda: [0, 0])
    for s, e, kind, b in mem:
        mk[kind][0] += 1; mk[kind][1] += e - s
    for k, (n, t) in mk.items():
        print(f"  memcpy kind {k}: n={n} {t/1e6:.2f} ms")
    api = defaultdict(lambda: [0, 0])
    for s, e, nid in q("select start, end, nameId from CUPTI_ACTIVITY_KIND_RUNTIME"):
        api[names.get(nid, str(nid))][0] += 1
        api[names.get(nid, str(nid))][1] += e - s
    print("CUDA API (count, total ms):")
    for k, (n, t) in sorted(api.items(), key=lambda x: -x[1][1])[:22]:
        print(f"  {k:48s} {n:8d} {t/1e6:10.2f}")
    kt = defaultdict(lambda: [0, 0])
    for s, e, sn, dn in kern:
        nm = names.get(sn, str(sn))
        kt[nm][0] += 1; kt[nm][1] += e - s
    print(f"top kernels by time (of {busy/1e6:.1f} ms busy):")
    for k, (n, t) in sorted(kt.items(), key=lambda x: -x[1][1])[:top]:
        print(f"  {k[:70]:70s} {n:7d} {t/1e6:9.2f} ms {t/n/1e3:8.1f} us")


if __name__ == "__main__":
    main()
