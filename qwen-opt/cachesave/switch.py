#!/usr/bin/env python3
"""Agent thread switch: 2 real omp threads (75-120k, ~/qwen-opt/l1tok convs/plan) alternate, 16 requests, so every
request after the first two restores its thread from --cache-ram and saves the other one. Per request: wall, prompt_n,
and the AP_TIMING lines: ap save (alloc/buf/ckpt copy/get tgt), ap load best (set+free), ap cache update."""
import argparse, json, os, re, time, urllib.request
L1 = os.path.expanduser("~/qwen-opt/l1tok")

def post(port, body):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=1800))

def f(rx, txt):
    m = re.search(rx, txt)
    return [float(x) for x in m.groups()] if m else None

ap = argparse.ArgumentParser()
for k in ("label", "log", "out"): ap.add_argument("--" + k, required=True)
ap.add_argument("--port", type=int, required=True)
a = ap.parse_args()
convs = {c["name"]: c for c in json.load(open(f"{L1}/convs.json"))}
plan = json.load(open(f"{L1}/plan.json"))
seq = [(t["name"], t["turns"][i]) for i in range(8) for t in plan["threads"]]
for idx, (name, k) in enumerate(seq):
    c = convs[name]
    off = os.path.getsize(a.log)
    t0 = time.perf_counter()
    r = post(a.port, {"messages": c["messages"][:k], "tools": c["tools"], "max_tokens": 16, "temperature": 0, "seed": 1})
    wall = 1000 * (time.perf_counter() - t0)
    time.sleep(0.5)
    with open(a.log, errors="replace") as fh:
        fh.seek(off); txt = fh.read()
    sv = f(r"ap save: n_tokens \d+, tgt ([0-9.]+) MiB, dft ([0-9.]+) MiB, ckpt \d+ / ([0-9.]+) MiB, alloc ([0-9.]+) ms \(buf ([0-9.]+), ckpt copy ([0-9.]+)\), get tgt ([0-9.]+) ms, get dft ([0-9.]+) ms", txt)
    ld = f(r"ap load best: n_tokens \d+, tgt ([0-9.]+) MiB, dft ([0-9.]+) MiB, ckpt \d+, set\+free ([0-9.]+) ms", txt)
    up = f(r"ap cache update: ([0-9.]+) ms", txt)
    t = r["timings"]
    row = {"label": a.label, "item": "switch", "i": idx, "thread": name[:24], "turn": k,
           "prompt_n": t["prompt_n"], "cache_n": t.get("cache_n"), "prompt_ms": round(t["prompt_ms"], 1), "wall_ms": round(wall, 1),
           "save": dict(zip(["tgt_mib", "dft_mib", "ckpt_mib", "alloc_ms", "buf_ms", "ckpt_copy_ms", "get_tgt_ms", "get_dft_ms"], sv)) if sv else None,
           "load": dict(zip(["tgt_mib", "dft_mib", "set_ms"], ld)) if ld else None,
           "update_ms": up[0] if up else None}
    if sv and sv[6] > 0: row["save_gbps"] = round(sv[0] / 1024 / (sv[6] / 1000), 2)
    if ld and ld[2] > 0: row["load_gbps"] = round((ld[0] + ld[1]) / 1024 / (ld[2] / 1000), 2)
    print(json.dumps(row), flush=True)
    with open(a.out, "a") as fo: fo.write(json.dumps(row) + "\n")
