#!/usr/bin/env python3
"""GPU busy/idle breakdown from an nsys sqlite export (kernels + memcpy/memset on the device timeline).
usage: gaps.py FILE.sqlite [--from-s S]   (skips the first S seconds of GPU activity: model load / warmup)
Prints: span, busy, idle split by gap size; top kernels by total time (short names) with count and mean us;
MMVQ (mul_mat_vec_q*) grouped by grid size (≈ matrix rows) as a proxy for the launch shape.
"""
import collections
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
skip = float(sys.argv[sys.argv.index("--from-s") + 1]) * 1e9 if "--from-s" in sys.argv else 0.0
names = dict(db.execute("select id, value from StringIds"))
ev = []
for s, e, n, dn, gx, gy, gz, bx, by in db.execute(
        "select start, end, shortName, demangledName, gridX, gridY, gridZ, blockX, blockY from CUPTI_ACTIVITY_KIND_KERNEL"):
    short = names.get(n, str(n))
    if short.startswith("mul_mat_vec_q"):  # keep the template args (type, ncols, ...) for MMVQ
        d = names.get(dn, short)
        short = d[d.find("mul_mat_vec_q"):d.find("(", d.find(">"))] if ">" in d else short
    ev.append((s, e, short, (gx, gy, gz, bx, by)))
for tbl in ("CUPTI_ACTIVITY_KIND_MEMCPY", "CUPTI_ACTIVITY_KIND_MEMSET", "CUPTI_ACTIVITY_KIND_GRAPH_TRACE"):
    try:
        for s, e in db.execute(f"select start, end from {tbl}"):
            ev.append((s, e, tbl.split("_")[-1].lower(), None))
    except sqlite3.OperationalError:
        pass
ev.sort()
t0 = ev[0][0] + skip
ev = [x for x in ev if x[0] >= t0]
span = ev[-1][1] - ev[0][0]
busy = 0; cur_s, cur_e = ev[0][0], ev[0][1]
gaps = collections.Counter(); gapn = collections.Counter()
bins = [(2e3, "<2us"), (10e3, "2-10us"), (50e3, "10-50us"), (200e3, "50-200us"), (1e6, "0.2-1ms"), (1e12, ">1ms")]
for s, e, _, _ in ev[1:]:
    if s > cur_e:
        busy += cur_e - cur_s
        g = s - cur_e
        for lim, lab in bins:
            if g < lim:
                gaps[lab] += g; gapn[lab] += 1; break
        cur_s, cur_e = s, e
    else:
        cur_e = max(cur_e, e)
busy += cur_e - cur_s
print(f"span {span/1e6:.1f} ms, busy {busy/1e6:.1f} ms ({100*busy/span:.1f}%), events {len(ev)}")
for _, lab in bins:
    print(f"  idle {lab:>9}: {gaps[lab]/1e6:8.1f} ms in {gapn[lab]} gaps")
tot = collections.defaultdict(lambda: [0, 0])
mm = collections.defaultdict(lambda: [0, 0])
for s, e, n, g in ev:
    tot[n][0] += e - s; tot[n][1] += 1
    if g and n.startswith("mul_mat_vec_q"):
        mm[(n, g)][0] += e - s; mm[(n, g)][1] += 1
print("top kernels (total ms, count, mean us):")
for n, (t, c) in sorted(tot.items(), key=lambda x: -x[1][0])[:25]:
    print(f"  {t/1e6:9.2f} {c:7d} {t/c/1e3:9.2f}  {n}")
print("mmvq by launch shape (grid, block):")
for (n, g), (t, c) in sorted(mm.items(), key=lambda x: -x[1][0])[:25]:
    print(f"  {t/1e6:9.2f} {c:7d} {t/c/1e3:9.2f}  {n} grid={g[:3]} block={g[3:]}")
