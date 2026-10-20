#!/usr/bin/env python3
"""Report 40: mtp_extract input from the E0 per-step log. Prompt ids = chat template (thinking off) tokenized by
bpe.py, checked against the prompt length in the log; response ids = exactly what the server generated (accepted
drafts + the next step's id), checked against the response text. Writes seqs.bin (mtp_extract / read_seqs_bin format)
and idx.jsonl (analyze.load meta: id, lang, cat = prose for T=1 / prose0 for T=0, n_tok, n_prompt).
usage: pa_extract_prep.py LABEL --out DIR [--seeds 1,2,3,4] (T=1 seeds kept; T=0 always kept)
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path.home() / "qwen-opt/xtxroadmap"))
from bpe import Tok, chat_prompt  # noqa: E402
from prose_bench import PROMPTS  # noqa: E402
import tokclass  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seeds", default="1,2,3,4")
    a = ap.parse_args()
    ld = HERE / "logs"
    rows = [r for r in map(json.loads, open(ld / "pa.jsonl")) if r["label"] == a.label]
    steps, begins = defaultdict(list), {}
    for l in open(ld / f"{a.label}.lk.jsonl"):
        o = json.loads(l)
        if "b" in o:
            begins[o["b"]] = o["n"]
        else:
            steps[o["r"]].append(o)
    reqs = sorted(begins)
    tok = Tok()
    strs = tokclass.token_strings()
    keep = set(map(int, a.seeds.split(",")))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seqs, idx = [], []
    n_txt_ok = 0
    for rq, row in zip(reqs[1:], rows):
        if row["temp"] > 0 and row["seed"] not in keep:
            continue
        pr = tok.encode(chat_prompt(PROMPTS[row["prompt"]]))
        assert len(pr) == begins[rq], (row["prompt"], len(pr), begins[rq])
        st = steps[rq]
        resp = []
        for i, s in enumerate(st):
            assert s["p"] == len(pr) + len(resp), (rq, i, s["p"], len(pr) + len(resp))
            resp.append(s["id"])
            resp.extend(s["d"][: s["a"]])
        txt = "".join(strs[t] for t in resp)
        n_txt_ok += row["text"].startswith(txt.rstrip()[: len(txt) - 8]) or txt.startswith(row["text"][:200])
        cat = "prose" if row["temp"] > 0 else "prose0"
        seqs.append(pr + resp)
        idx.append({"id": f"{row['prompt']}-s{row['seed']}-T{row['temp']:g}", "lang": row["prompt"][:2], "cat": cat,
                    "seed": row["seed"], "temp": row["temp"], "n_tok": len(pr) + len(resp), "n_prompt": len(pr)})
    with open(out / "seqs.bin", "wb") as f:
        f.write(struct.pack("<i", len(seqs)))
        for s, m in zip(seqs, idx):
            f.write(struct.pack("<ii", len(s), m["n_prompt"]))
            f.write(struct.pack(f"<{len(s)}i", *s))
    (out / "idx.jsonl").write_text("".join(json.dumps(m) + "\n" for m in idx))
    print(f"{len(seqs)} seqs, {sum(len(s) for s in seqs)} tokens, text check {n_txt_ok}/{len(seqs)} -> {out}")


if __name__ == "__main__":
    main()
