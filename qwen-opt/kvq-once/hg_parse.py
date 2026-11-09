#!/usr/bin/env python3
"""LLAMA_HOSTGAP_TRACE=N server stderr -> per request the decode-phase host timeline: the periodic reports (every N
steps) of a request after its last prefill window (>= 200 ms/step wall) and the following transition window are decode
windows, their pairs and values are summed weighted by steps. Prints, per request (labelled by --depths in order),
ms/step wall and the top pairs in us/step.

usage: hg_parse.py SERVER_STDERR [--depths 1700,94000,199000] [--top 14]
"""
import argparse, re
from collections import defaultdict

HDR = re.compile(r"hostgap\[(\w+)\]: (\d+) steps, ([\d.]+) ms/step wall")
ROW = re.compile(r"hostgap  (?:value )?(.+?)\s+n\s+(\d+) mean\s+([\d.]+) us max\s+([\d.]+) us\s+([\d.]+) us/step")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--depths", default="1700,94000,199000")
    ap.add_argument("--top", type=int, default=14)
    a = ap.parse_args()
    blocks, cur = [], None
    for line in open(a.log, errors="ignore"):
        m = HDR.search(line)
        if m:
            cur = {"tag": m[1], "steps": int(m[2]), "ms": float(m[3]), "rows": {}}
            blocks.append(cur)
            continue
        m = ROW.search(line)
        if m and cur is not None:
            cur["rows"][re.sub(r"\s+", " ", m[1].strip())] = float(m[5])
    # a request = its prefill windows (>= 200 ms/step) and the decode windows after them; the "request" report is not
    # printed when a request ends on a periodic boundary, so the requests are cut at the prefill windows instead
    reqs = []
    for b in blocks:
        if b["tag"] == "request":
            continue  # the tail of a request: holds the idle time until its report, not a decode window
        pre = b["ms"] >= 200
        if pre and (not reqs or reqs[-1]["dec"]):
            reqs.append({"pre": 0, "dec": []})
        if not reqs:
            continue
        if pre:
            reqs[-1]["pre"] += 1
        else:
            reqs[-1]["dec"].append(b)
    depths = a.depths.split(",")
    for d, rq in zip(depths, reqs[-len(depths):]):
        dec = rq["dec"][1:]  # the first window after the prefill mixes in its last ubatches
        steps = sum(b["steps"] for b in dec)
        if not steps:
            print(f"depth {d}: no decode windows")
            continue
        wall = sum(b["ms"] * b["steps"] for b in dec) / steps
        acc = defaultdict(float)
        for b in dec:
            for k, v in b["rows"].items():
                acc[k] += v * b["steps"] / steps
        print(f"depth {d}: {steps} decode steps in {len(dec)} windows, {wall:.2f} ms/step wall")
        for k, v in sorted(acc.items(), key=lambda kv: -kv[1])[:a.top]:
            print(f"    {k:<60} {v:9.1f} us/step")


if __name__ == "__main__":
    main()
