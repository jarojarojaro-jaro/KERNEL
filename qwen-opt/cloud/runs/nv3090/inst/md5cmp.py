#!/usr/bin/env python3
"""Compare the md5 gate rows of two labels (nv-3090, 2026-10-20).

gate.jsonl (gate_chat.py: 6 chat prompts x T=0/T=1 s1) + copy_gate.jsonl (sweep.py mvs 4 + short 6 at T=0).
usage: md5cmp.py <dir> <labelA> <labelB>   -> prints rows, identical count, exit 0 iff all identical and >= 22 rows
"""
import json
import pathlib
import sys


def rows(d: pathlib.Path, label: str) -> dict:
    out = {}
    for f in ("gate.jsonl", "copy_gate.jsonl"):
        p = d / f
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("label") != label:
                continue
            key = (r.get("set", "chat"), r["prompt"], r["temp"], r.get("seed", 1))
            out[key] = r["md5"]
    return out


d = pathlib.Path(sys.argv[1])
a, b = rows(d, sys.argv[2]), rows(d, sys.argv[3])
keys = sorted(set(a) | set(b), key=str)
same = sum(1 for k in keys if a.get(k) == b.get(k) and a.get(k) is not None)
for k in keys:
    print(f"{'=' if a.get(k) == b.get(k) else 'X'} {k} {a.get(k)} {b.get(k)}")
print(f"{sys.argv[2]} vs {sys.argv[3]}: {same}/{len(keys)} identical")
sys.exit(0 if same == len(keys) and len(keys) >= 22 else 1)
