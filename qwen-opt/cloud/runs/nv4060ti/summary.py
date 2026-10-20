#!/usr/bin/env python3
"""Report 31 summary table from /root/res/logs (final.sh): arms U0 U1 T X(=T'). Markdown to stdout."""
import glob
import json
import statistics
import sys

L = sys.argv[1] if len(sys.argv) > 1 else "/root/res/logs"
ARMS = [("U0", "U0"), ("U1", "U1"), ("T", "T"), ("X", "T'")]


def jl(path):
    out = []
    for f in glob.glob(path):
        out += [json.loads(x) for x in open(f) if x.strip()]
    return out


ss = {r["label"]: r for r in jl(f"{L}/spec_sweep.jsonl")}
cb = {r["label"]: r for r in jl(f"{L}/copy_bench.jsonl") if r.get("set") == "mvs"}
lg = jl(f"{L}/long.jsonl")
vr = jl(f"{L}/vram.jsonl")


def chat(a, key):
    v = [ss[f"qwen.{a}.p{p}"][key] for p in (1, 2) if f"qwen.{a}.p{p}" in ss]
    return (statistics.mean(v), v) if v else (None, [])


def tok_step(a):
    v = []
    for p in (1, 2):
        r = ss.get(f"qwen.{a}.p{p}")
        if r:
            v.append(statistics.median(x["tok_step"] for x in r["prompts"].values()))
    return statistics.mean(v) if v else None


def mvs(a, key):
    r = cb.get(f"qwen.{a}.p1")
    if not r:
        return None
    return r["median_tps"] if key == "tps" else statistics.median(x[key] for x in r["prompts"].values())


def long(a, size, temp, key):
    for r in lg:
        if r["label"] == f"qwen.{a}.p1" and r["size"] == size and r["temp"] == temp:
            return r.get(key)
    return None


def lb(a, n_prompt, n_gen):
    v = []
    for r in jl(f"{L}/lb.final.{a}.r*.jsonl"):
        if r["n_prompt"] == n_prompt and r["n_gen"] == n_gen:
            v.append(r["avg_ts"])
    return statistics.mean(v) if v else None


def vram(a, what):
    for r in vr:
        if r.get("label") == f"qwen.{a}.p1.{what}":
            return r["vram_mb"]
    return None


def fmt(x, d=1):
    return "–" if x is None else f"{x:.{d}f}"


def rel(x, y):
    return "" if x is None or y is None or y == 0 else f"{100 * (x / y - 1):+.1f}%"


rows = []
c = {a: chat(a, "median_tps") for a, _ in ARMS}
rows.append(("czat T=1 (spec_sweep 6×3) t/s", {a: f"{fmt(c[a][0])} [{' / '.join(fmt(x) for x in c[a][1])}]" for a, _ in ARMS},
             {a: c[a][0] for a, _ in ARMS}))
m = {a: chat(a, "median_ms_step")[0] for a, _ in ARMS}
rows.append(("czat T=1 ms/krok", {a: fmt(m[a], 2) for a, _ in ARMS}, m))
t = {a: tok_step(a) for a, _ in ARMS}
rows.append(("czat T=1 tok/krok", {a: fmt(t[a], 2) for a, _ in ARMS}, t))
mv = {a: mvs(a, "tps") for a, _ in ARMS}
rows.append(("code-edit mvs T=0 t/s", {a: fmt(mv[a]) for a, _ in ARMS}, mv))
mt = {a: mvs(a, "tok_step") for a, _ in ARMS}
rows.append(("mvs tok/krok", {a: fmt(mt[a], 2) for a, _ in ARMS}, mt))
for size in ("512", "16k"):
    d0 = {a: long(a, size, 0.0, "decode_tps") for a, _ in ARMS}
    d1 = {a: long(a, size, 1.0, "decode_tps") for a, _ in ARMS}
    rows.append((f"decode po {size} T=0 / T=1 t/s", {a: f"{fmt(d0[a])} / {fmt(d1[a])}" for a, _ in ARMS}, d0))
pf = {a: long(a, "16k", 0.0, "prefill_tps") for a, _ in ARMS}
rows.append(("prefill 16k (14 393 tok) t/s", {a: fmt(pf[a]) for a, _ in ARMS}, pf))
tt = {a: long(a, "16k", 0.0, "ttft_s") for a, _ in ARMS}
rows.append(("TTFT 16k s", {a: fmt(tt[a], 2) for a, _ in ARMS}, tt))
lbmap = {"U0": "U", "U1": "U", "T": "T", "X": "X"}
for (np_, ng, name) in ((512, 0, "pp512"), (4096, 0, "pp4096"), (0, 128, "tg128")):
    v = {a: lb(lbmap[a], np_, ng) for a, _ in ARMS}
    rows.append((f"llama-bench {name} t/s", {a: fmt(v[a]) for a, _ in ARMS}, v))
vl = {a: vram(a, "loaded") for a, _ in ARMS}
rows.append(("VRAM po załadowaniu MiB", {a: fmt(vl[a], 0) for a, _ in ARMS}, vl))
ve = {a: vram(a, "end") for a, _ in ARMS}
rows.append(("VRAM na końcu ramienia MiB", {a: fmt(ve[a], 0) for a, _ in ARMS}, ve))

print("| metryka | " + " | ".join(n for _, n in ARMS) + " | T' vs U0 | T' vs U1 | T' vs T |")
print("|---|" + "---|" * (len(ARMS) + 3))
for name, cells, num in rows:
    print(f"| {name} | " + " | ".join(cells[a] for a, _ in ARMS) +
          f" | {rel(num['X'], num['U0'])} | {rel(num['X'], num['U1'])} | {rel(num['X'], num['T'])} |")
