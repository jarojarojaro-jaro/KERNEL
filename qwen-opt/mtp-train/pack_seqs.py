"""gen jsonl -> seqs.bin (mtp_extract input) + seqs.idx.jsonl (id/lang/cat per sequence, same order)."""
import argparse
import json
import struct

ap = argparse.ArgumentParser()
ap.add_argument("gen", nargs="+")
ap.add_argument("--out", required=True)
ap.add_argument("--max-tok", type=int, default=8000)
a = ap.parse_args()

recs = [json.loads(l) for g in a.gen for l in open(g)]
with open(a.out + ".bin", "wb") as fb, open(a.out + ".idx.jsonl", "w") as fi:
    fb.write(struct.pack("<i", len(recs)))
    for r in recs:
        toks = (r["prompt_ids"] + r["resp_ids"])[: a.max_tok]
        fb.write(struct.pack("<ii", len(toks), len(r["prompt_ids"])))
        fb.write(struct.pack(f"<{len(toks)}i", *toks))
        fi.write(json.dumps({"id": r["id"], "lang": r["lang"], "cat": r["cat"], "n_tok": len(toks),
                             "n_prompt": len(r["prompt_ids"])}) + "\n")
print(f"{len(recs)} seqs, {sum(len(r['resp_ids']) for r in recs)} response tokens")
