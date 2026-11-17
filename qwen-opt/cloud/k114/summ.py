#!/usr/bin/env python3
"""K-114 summary per card dir (res/<card>): decode medians per arm/T, tokens per step (draft accepted / steps),
step ms = tok_per_step / tps, target pass ms from the plain arm, prefill t/s, power and clocks under load.
   summ.py res/3090 res/3060 res/5060ti"""
import csv, json, statistics as st, sys

GB = 10.04 + 0.30  # GSQ IQ3_XXS target bytes per pass (catalog bTokGB + GDN state rw)
BW = {"3090": 936, "3060": 360, "5060ti": 448}
INT8 = {"3090": 284.7, "3060": 101.9, "5060ti": 189.8}  # dense INT8 tensor TOPS (skill-io karty.json)
DRAFT_GB = 0.40  # MTP layer + 64k IQ4_XS head per draft step [INFERENCE, as in skill-io-sufity]
for d in sys.argv[1:]:
    card = d.rstrip("/").split("/")[-1].rstrip("abc")
    rows = [json.loads(l) for l in open(f"{d}/bench.jsonl") if l.strip()]
    print(f"\n== {card}  ({open(f'{d}/gpu.csv').read().splitlines()[-1]})")
    arms = {}
    for r in rows:
        if r.get("prompt") in (None, "MEDIAN") or not r.get("tps"):
            continue
        arms.setdefault((r["engine"], r["temp"]), []).append(r)
    plain_ms = None
    for (eng, t), rs in sorted(arms.items()):
        tps = st.median(x["tps"] for x in rs)
        srv = st.median(x.get("srv_tps") or x["tps"] for x in rs)
        dn = sum(x.get("draft") or 0 for x in rs); da = sum(x.get("acc") or 0 for x in rs); n = sum(x["n"] for x in rs)
        steps = n - da if dn else n  # each verify step emits accepted + 1
        tok_step = n / steps if steps else 1
        step_ms = 1000 * tok_step / srv
        if eng == "plain":
            plain_ms = 1000 / srv
        nd = {"n4-a": 4, "n4-b": 4, "n2": 2}.get(eng, 0)
        ceil = BW[card] / ((GB + nd * DRAFT_GB) / tok_step)
        print(f"  {eng:6s} T={t:.0f}  ceiling {ceil:5.1f}  -> {100 * srv / ceil:3.0f}%  tps {tps:6.1f} (srv {srv:6.1f})  tok/step {tok_step:4.2f}  step {step_ms:5.1f} ms"
              + (f"  acc {da}/{dn} = {da / dn:.2f}" if dn else ""))
    if plain_ms:
        print(f"  target pass (plain) {plain_ms:.1f} ms -> {GB / plain_ms * 1000:.0f} GB/s = {100 * GB / plain_ms * 1000 / BW[card]:.0f}% of spec {BW[card]} GB/s")
    try:
        pf = [json.loads(l) for l in open(f"{d}/prefill.jsonl")]
        for w in sorted({p["words"] for p in pf}):
            xs = [p for p in pf if p["words"] == w]
            L = xs[0]['prompt_n']; pc = 0.5 * INT8[card] * 1e12 / (2 * 25.6e9 + 4 * 16 * 24 * 256 * L / 2)
            v = st.median(p['pp_tps'] for p in xs)
            print(f"  prefill ~{L} tok: {v:.0f} t/s  ceiling {pc:.0f} -> {100 * v / pc:.0f}%")
    except FileNotFoundError:
        pass
    smi = [r for r in csv.reader(open(f"{d}/smi.csv")) if len(r) > 6 and "%" in r[6] and int(r[6].strip(" %")) > 80]
    if smi:
        p = [float(r[1].split()[0]) for r in smi]; c = [int(r[4].split()[0]) for r in smi]
        m = st.median(int(r[5].split()[0]) for r in smi)
        g = open(f"{d}/gpu.csv").read().splitlines()[-1].split(",")
        pl, pdl, mmax = float(g[3].split()[0]), float(g[4].split()[0]), int(g[6].split()[0])
        lim = [w for w, bad in ((f"power {pl:.0f}/{pdl:.0f} W", pl < 0.95 * pdl), (f"mem under load {m}/{mmax} MHz", m < 0.95 * mmax)) if bad]
        print(f"  under load (util>80%, n={len(smi)}): power median {st.median(p):.0f} W / limit {smi[0][2].strip()}, sm clock median {st.median(c)} MHz, mem {m} MHz"
              + (f"\n  ** LIMITED HOST ({'; '.join(lim)}): lower bound, not a card result" if lim else ""))
