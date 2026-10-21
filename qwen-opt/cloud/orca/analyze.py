#!/usr/bin/env python3
"""Turn a collected orca-3090 results directory into a compact report (markdown on stdout + report.md).

usage: analyze.py <dir-with-probe/sweep/long/lb/greedy>
"""
from __future__ import annotations

import glob
import json
import os
import sys


def rows(path: str) -> list[dict]:
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return out


def tsv(path: str) -> list[list[str]]:
    try:
        return [l.rstrip("\n").split("\t") for l in open(path) if l.strip()]
    except FileNotFoundError:
        return []


def log_rows(path: str) -> list[dict]:
    """spec_sweep medians also appear on stdout (campaign log); recover rows a jsonl write lost."""
    import re
    out = []
    try:
        with open(path) as f:
            for line in f:
                m = re.match(r"^(\S+) T=([0-9.]+): median +([0-9.]+) t/s, +([0-9.]+) ms/step", line.strip())
                if m:
                    out.append({"label": m.group(1), "median_tps": float(m.group(3)),
                                "median_ms_step": float(m.group(4)), "temp": float(m.group(2))})
    except FileNotFoundError:
        pass
    return out


def label_of(r: dict) -> str:
    return str(r.get("label", "")).split("|")[0]


def main() -> None:
    d = sys.argv[1]
    out: list[str] = [f"# OrcaCyber-Nano-1.0 / RTX 3090 — raport\n"]

    srv = rows(os.path.join(d, "servers.jsonl"))
    probe = rows(os.path.join(d, "probe", "servers.jsonl"))
    plong = rows(os.path.join(d, "probe", "long.jsonl"))
    if probe:
        out.append("## 1. Budżet kontekstu (KV q4_0/q8_0/f16, -ngl 999 -fit off)\n")
        out.append("| ctx żądany | kv | tryb | n_ctx | VRAM MiB | load s | głębokość 0.8 | werdykt |")
        out.append("|---|---|---|---|---|---|---|---|")
        srv_by_label = {s.get("label"): s for s in srv}
        for r in probe:
            depth = next((x for x in plong if label_of(x) == label_of(r)), None)
            vram = srv_by_label.get(r.get("label"), {}).get("vram_mib", r.get("vram_mib"))
            if depth is None:
                dep = "-"
            elif depth.get("ok"):
                dep = f"ok, {depth.get('prompt_n')} tok, TTFT {depth.get('ttft_ms', 0)/1000:.1f}s"
            else:
                dep = "OOM/odrzucone"
            out.append(f"| {r.get('requested_ctx')} | {r.get('kv')} | {r.get('mode')} | {r.get('n_ctx')} | "
                       f"{vram} | {r.get('load_s')} | {dep} | {'OK' if r.get('ok') else 'FAIL'} |")
        out.append("")
        ok = [r for r in probe if r.get("ok")]
        if ok:
            best = max(ok, key=lambda r: int(r.get("requested_ctx") or 0))
            kvb = next((x for x in plong if label_of(x) == label_of(best) and x.get("ok")), {})
            out.append(f"**Maksymalny użyteczny kontekst: {best.get('requested_ctx')} tok** "
                       f"(n_ctx {best.get('n_ctx')}, VRAM {best.get('vram_mib')} MiB, "
                       f"VRAM wg servers.jsonl: {srv_by_label.get(best.get('label'), {}).get('vram_mib', '?')} MiB)\n")

    sw = rows(os.path.join(d, "sweep", "spec_sweep.jsonl"))
    logf = os.path.join(d, "campaign.log")
    if os.path.exists(logf):
        have = {label_of(r) for r in sw}
        for r in log_rows(logf):
            if label_of(r) not in have:
                sw.append(r)
    if sw:
        agg: dict[str, list[float]] = {}
        for r in sw:
            agg.setdefault(label_of(r), []).append(r["median_tps"])
        ranked = sorted(((l, sum(v) / len(v), len(v)) for l, v in agg.items()), key=lambda x: -x[1])
        out.append("## 2. Ranking konfiguracji (T=1, 6 promptów × 2 seedy, 400 tok, ctx 32k)\n")
        out.append("| # | konfiguracja | t/s (średnia z rund) | rundy | Δ vs fork.none |")
        out.append("|---|---|---|---|---|")
        base_none = next((x[1] for x in ranked if x[0].endswith("fork.none.q4_0.32k")), None)
        for i, (lab, tps, n) in enumerate(ranked[:20], 1):
            delta = f"{100 * (tps / base_none - 1):+.1f}%" if base_none else "-"
            out.append(f"| {i} | {lab} | {tps:.1f} | {n} | {delta} |")
        out.append("")

        # compared pairs: base vs fork, spec vs none, per switch
        def tps(lab: str) -> float | None:
            return agg.get(lab, [None])[0] if lab in agg else None

        pairs = []
        for a, b in (("base.none.q4_0.32k", "base.mtp4.q4_0.32k"), ("fork.none.q4_0.32k", "fork.mtp4.q4_0.32k"),
                     ("base.mtp4.q4_0.32k", "fork.mtp4.q4_0.32k")):
            if tps(a) and tps(b):
                pairs.append((f"{a} → {b}", tps(a), tps(b)))
        if pairs:
            out.append("### Kluczowe delty\n")
            out.append("| porównanie | przed | po | zysk |")
            out.append("|---|---|---|---|")
            for name, x, y in pairs:
                out.append(f"| {name} | {x:.1f} | {y:.1f} | {100 * (y / x - 1):+.1f}% |")
            out.append("")

        base = tps("fork.mtp4.q4_0.32k")
        if base:
            out.append("### Przełączniki (fork, MTP n=4, q4_0, 32k)\n")
            out.append("| konfiguracja | t/s | Δ vs baza |")
            out.append("|---|---|---|")
            for lab, v in agg.items():
                if lab.startswith("fork.mtp4.") and lab != "fork.mtp4.q4_0.32k":
                    out.append(f"| {lab} | {v[0]:.1f} | {100 * (v[0] / base - 1):+.1f}% |")
            out.append("")

    lg = rows(os.path.join(d, "long", "long.jsonl"))
    if lg:
        out.append("## 3. Długi kontekst (TTFT i decode na głębokości)\n")
        out.append("| konfiguracja | ctx | frakcja | prompt tok | TTFT s | prefill t/s | decode t/s | VRAM MiB |")
        out.append("|---|---|---|---|---|---|---|---|")
        for r in lg:
            out.append(f"| {r.get('label')} | {r.get('ctx')} | {r.get('frac')} | {r.get('prompt_n', '-')} | "
                       f"{(r.get('ttft_ms') or 0)/1000:.2f} | {r.get('prefill_tps', 0):.0f} | "
                       f"{r.get('tps', 0):.1f} | {r.get('peak_vram_mib', '-')} |")
        out.append("")

    lb = []
    for p in sorted(glob.glob(os.path.join(d, "lb", "*.jsonl"))):
        tag = os.path.basename(p)[:-6]
        for r in rows(p):
            lb.append((tag, r))
    if lb:
        out.append("## 4. llama-bench (bez spekulacji, pp512/tg128, r=5)\n")
        out.append("| build | KV | pp512 t/s | tg128 t/s |")
        out.append("|---|---|---|---|")
        by: dict[str, dict] = {}
        for tag, r in lb:
            build, _, kv = tag.partition(".")
            rec = by.setdefault(tag, {})
            if r.get("n_prompt", 0) > 1:
                rec["pp"] = r.get("avg_ts")
            elif r.get("n_gen", 0) > 1:
                rec["tg"] = r.get("avg_ts")
        for tag, v in sorted(by.items()):
            out.append(f"| {tag} | | {v.get('pp', 0):.0f} | {v.get('tg', 0):.1f} |")
        out.append("")

    kvs = rows(os.path.join(d, "long", "kv-slope.jsonl"))
    if kvs:
        out.append("## 6. KV slope (load-only, ten sam config)\n")
        out.append("| ctx | VRAM MiB | ok |")
        out.append("|---|---|---|")
        pts = sorted({(r.get("ctx"), r.get("vram_mib"), r.get("ok")) for r in kvs if r.get("ok") == "yes"})
        for c, v, o in pts:
            out.append(f"| {c} | {v} | {o} |")
        good = [(c, v) for c, v, _ in pts if c and v and c > 0]
        if len(good) >= 2:
            (c1, v1), (c2, v2) = good[0], good[-1]
            slope = (v2 - v1) / (c2 - c1) * 1024
            out.append(f"\n**Slope: {slope:.1f} KiB/token** ({(v2 - v1):.0f} MiB od {c1} do {c2} tok), "
                       f"intercept ~{v1 - slope * c1 / 1024:.0f} MiB\n")
        out.append("")

    md = tsv(os.path.join(d, "greedy", "md5.tsv"))
    if len(md) > 1:
        out.append("## 5. Greedy md5 (determinizm; drafter nie może zmienić tekstu)\n")
        out.append("| konfiguracja | md5 |")
        out.append("|---|---|")
        for row in md[1:]:
            out.append(f"| {row[0]} | {row[1]} |")
        hashes = {row[1] for row in md[1:]}
        out.append("")
        out.append(f"**Werdykt: {'identyczne' if len(hashes) == 1 else 'RÓŻNE — sprawdzić, który drafter zmienia tekst'}**\n")

    text = "\n".join(out)
    with open(os.path.join(d, "report.md"), "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
