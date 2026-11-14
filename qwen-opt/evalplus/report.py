#!/usr/bin/env python3
"""Summarise a jakość-mini run dir: pass@1 (base / plus) from *_eval_results.json + generation stats."""
import json, os, sys

R = sys.argv[1]
out = {"run": os.path.basename(R)}
rows = []
for ds, name in (("humaneval", "HumanEval"), ("mbpp", "MBPP")):
    rp = os.path.join(R, f"{ds}_eval_results.json")
    if not os.path.exists(rp):
        continue
    ev = json.load(open(rp))["eval"]
    n = len(ev)
    base = sum(r[0]["base_status"] == "pass" for r in ev.values())
    plus = sum(r[0]["base_status"] == "pass" and r[0]["plus_status"] == "pass" for r in ev.values())
    st = [json.loads(l) for l in open(os.path.join(R, f"{ds}.stats.jsonl"))]
    toks = sum(s["completion_tokens"] or 0 for s in st)
    gen_ms = sum((s["timings"] or {}).get("predicted_ms", 0) for s in st)
    wall = sum(s["wall_s"] for s in st)
    trunc = sum(s["finish"] == "length" for s in st)
    fails = sorted(k for k, r in ev.items() if not (r[0]["base_status"] == "pass" and r[0]["plus_status"] == "pass"))
    d = {"n": n, "base_pass": base, "plus_pass": plus, "pass1_base": round(100 * base / n, 1),
         "pass1_plus": round(100 * plus / n, 1), "answers": len(st), "tokens_per_answer": round(toks / len(st)),
         "reasoning_chars_per_answer": round(sum(s["reasoning_chars"] for s in st) / len(st)),
         "truncated": trunc, "wall_s": round(wall), "decode_tps": round(toks / (gen_ms / 1000), 1) if gen_ms else None,
         "end_to_end_tps": round(toks / wall, 1), "plus_fails": fails}
    out[ds] = d
    rows.append(f"| {name} | {d['pass1_base']} ({base}/{n}) | {d['pass1_plus']} ({plus}/{n}) | {d['tokens_per_answer']} "
                f"| {d['truncated']} | {d['wall_s']} | {d['decode_tps']} |")
md = ["| zbiór | pass@1 base % | pass@1 plus % | tok/odp. | ucięte | wall s | t/s dekod |",
      "|---|---|---|---|---|---|---|"] + rows
open(os.path.join(R, "summary.json"), "w").write(json.dumps(out, indent=1) + "\n")
open(os.path.join(R, "summary.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
