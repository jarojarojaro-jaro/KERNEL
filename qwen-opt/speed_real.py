#!/usr/bin/env python3
"""Real-use speed from benchmark runs: per-dataset llama-server timings of every answer (<ds>.stats.jsonl rows with
"timings", written by evalplus/gen.py and jakosc-mini/run.py).
  speed_real.py RUN_DIR [RUN_DIR ...] [--md OUT.md]
Per dataset: answers, mean tokens/answer, decode t/s (token-weighted = sum predicted_n / sum predicted_ms, plus median
and p10/p90 of per-answer t/s), MTP/lookup acceptance (accepted/drafted), tokens per verify step
(predicted_n / (predicted_n - accepted)), prompt length, prefill t/s, TTFT median. A dataset reused from another run
(jakosc-mini --reuse-humaneval) is reported where its stats file lives."""
import glob, json, os, statistics, sys


def pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, round(p / 100 * (len(v) - 1))))]


def summarize(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    t = [r["timings"] for r in rows if r.get("timings") and r["timings"].get("predicted_ms")]
    if not t:
        return None
    pn = sum(x["predicted_n"] for x in t); pms = sum(x["predicted_ms"] for x in t)
    dn = sum(x.get("draft_n", 0) for x in t); da = sum(x.get("draft_n_accepted", 0) for x in t)
    tps = [x["predicted_per_second"] for x in t if x["predicted_n"] >= 16]
    return {"n": len(t), "tok_per_answer": round(pn / len(t)), "decode_tps": round(pn / pms * 1000, 1),
            "decode_tps_median": round(statistics.median(tps), 1) if tps else None,
            "decode_tps_p10": round(pct(tps, 10), 1) if tps else None, "decode_tps_p90": round(pct(tps, 90), 1) if tps else None,
            "accept": round(da / dn, 3) if dn else None, "tok_per_step": round(pn / max(1, pn - da), 2),
            "prompt_n_median": round(statistics.median(x["prompt_n"] for x in t)),
            "prefill_tps": round(sum(x["prompt_n"] for x in t) / sum(x["prompt_ms"] for x in t) * 1000, 1),
            "ttft_ms_median": round(statistics.median(x["prompt_ms"] for x in t)),
            "gen_ms": round(pms), "tokens": pn}


def main():
    args = sys.argv[1:]
    md_out = None
    if "--md" in args:
        i = args.index("--md"); md_out = args[i + 1]; del args[i:i + 2]
    res = {}
    for d in args:
        for p in sorted(glob.glob(os.path.join(d, "*.stats.jsonl"))):
            s = summarize(p)
            if s:
                res[f"{os.path.basename(d.rstrip('/'))}/{os.path.basename(p)[:-len('.stats.jsonl')]}"] = s
    if not res:
        sys.exit("no stats with timings")
    allp = [p for d in args for p in glob.glob(os.path.join(d, "*.stats.jsonl"))]
    md = ["| zbiór | odp. | tok/odp. | dekod t/s (ważone) | mediana [p10–p90] | akceptacja | tok/krok | prompt tok (med.) | prefill t/s | TTFT ms (med.) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in res.items():
        md.append(f"| {k} | {s['n']} | {s['tok_per_answer']} | {s['decode_tps']} | {s['decode_tps_median']} "
                  f"[{s['decode_tps_p10']}–{s['decode_tps_p90']}] | {s['accept']} | {s['tok_per_step']} | "
                  f"{s['prompt_n_median']} | {s['prefill_tps']} | {s['ttft_ms_median']} |")
    tot_n = sum(s["n"] for s in res.values())
    tot_tok = sum(s["tokens"] for s in res.values())
    tot_ms = sum(s["gen_ms"] for s in res.values())
    md.append(f"\nRazem {tot_n} odpowiedzi, {tot_tok} tokenów, {round(tot_ms / 3.6e6, 2)} h dekodu, dekod ważony "
              f"{round(tot_tok / tot_ms * 1000, 1)} t/s ({len(allp)} plików stats).")
    text = "\n".join(md) + "\n"
    print(text)
    if md_out:
        open(md_out, "w").write(text)
        json.dump(res, open(os.path.splitext(md_out)[0] + ".json", "w"), indent=1)


if __name__ == "__main__":
    main()
