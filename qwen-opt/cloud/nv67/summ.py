#!/usr/bin/env python3
"""Summary of campaign-67 results: summ.py <results dir> [...] (dirs from camp.sh collect: arms.jsonl, hw/system.txt)."""
import json
import sys


def buf(b: dict, key: str, draft: bool | None = None) -> str:
    v = [x["mib"] for x in b.get(key, []) if x.get("dev", "").startswith("CUDA") and (draft is None or x.get("draft") == draft)]
    return "+".join(f"{x:.0f}" for x in v) or "-"


for d in sys.argv[1:]:
    print(f"# {d}")
    try:
        print("  " + " | ".join(l.strip() for l in open(f"{d}/hw/system.txt").readlines()[1:3]))
    except OSError:
        pass
    for line in open(f"{d}/arms.jsonl"):
        r = json.loads(line)
        sw, pp, g, f = r.get("sweep") or {}, r.get("prefill") or {}, r.get("greedy") or {}, r.get("fill") or {}
        st = r.get("stab") or {}
        b = r.get("buffers") or {}
        extra = " ".join(x for x in r["extra"] if x not in ("-lv", "4")).replace("--spec-type draft-mtp ", "").replace(
            "--spec-draft-n-max", "n").replace("--spec-draft-n-ubatch", "ubd").replace("--spec-draft-p-min", "pmin")
        extra = " ".join(p for p in extra.split() if not p.endswith(".gguf") and p != "-md")
        s = (f"  {r['arm']:<26} {r['engine']} ub{r['ub']} c{r['ctx_req']} ok={int(bool(r['ok']))} nctx={r.get('n_ctx')} "
             f"load={r.get('vram_load_mib')} peak={r.get('vram_peak_mib')} [{extra}]")
        if sw:
            s += f" T1={sw['median_tps']:.2f} acc={sw['acc']:.2f}"
        if pp:
            s += f" pp={pp['tps']:.0f}"
        if g:
            s += f" md5={g['md5']}"
        if f:
            s += (f" FILL pn={f['prompt_n']} pp={f['prompt_tps']:.0f} dec={f['decode_tps']:.1f} after={f['vram_after_mib']} "
                  f"ok={f['ok']}")
        if st:
            s += f" STAB {st['tps']} err={st['errors']} ok={st['ok']} temps={st['temps']}"
        if r["arm"].startswith("mem"):
            s += (f" | compute tgt={buf(b, 'compute', False)} dft={buf(b, 'compute', True)} kv={buf(b, 'kv')} rs={buf(b, 'rs')} "
                  f"model={buf(b, 'model')}")
        if not r["ok"] and r.get("error"):
            err = [l for l in r["error"].splitlines() if " E " in l or "Error" in l][:1]
            s += f" ERR {err[0][-110:] if err else r['error'].splitlines()[-1][-110:]}"
        print(s)
