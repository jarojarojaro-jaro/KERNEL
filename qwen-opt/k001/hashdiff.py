#!/usr/bin/env python3
"""K-001: diff the GGML_CUDA_HASHDUMP node hashes of consecutive matching graph evaluations in a server log
(R1 then R2 of k001d.py). Prints, per pair of evaluations with the same node count, the first nodes that differ."""
import re, sys
evals, cur = [], None
for line in open(sys.argv[1], errors="replace"):
    if "HASH graph begin" in line:
        cur = []; evals.append(cur)
    elif "HASH graph skip" in line:
        cur = None
    elif cur is not None:
        m = re.search(r"HASH (\d+) (\S+) (.+?) \[(\S+) (\S+) (\S+)\] ([0-9a-f]{16})", line)
        if m:
            cur.append((int(m.group(1)), m.group(2), m.group(3), m.group(4, 5, 6), m.group(7)))
print(f"{len(evals)} evaluations: node counts {[len(e) for e in evals]}")
for a in range(len(evals)):
    for b in range(a + 1, len(evals)):
        A, B = evals[a], evals[b]
        if len(A) != len(B) or [x[1] for x in A] != [x[1] for x in B]:
            continue
        diff = [(x, y) for x, y in zip(A, B) if x[4] != y[4]]
        print(f"eval {a} vs {b}: {len(diff)} of {len(A)} nodes differ")
        for x, y in diff[:12]:
            print(f"   node {x[0]} {x[1]} {x[2]} {x[3]}: {x[4]} vs {y[4]}")
