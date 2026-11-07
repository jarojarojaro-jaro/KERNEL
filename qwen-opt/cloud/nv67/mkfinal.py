#!/usr/bin/env python3
"""Final-phase run cards (cards-run/<name>.json) from ModelSelect67's cards-final/<card>.json (not modified here):
same model/ctx/KV/ub, plus the measured lossless knobs (draft ubatch 64, n sweep) and the validation blocks
(ABBA, fill at the recipe ctx, stability, greedy md5); 24 GB also gets the UD-Q4_K_XL 262144 check and, on the 3090,
our fork (report 27, cuda-topka2, sm_86 build) against upstream at the same ctx.
   mkfinal.py <card> [<card> ...]"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
UBD = ["--spec-draft-n-ubatch", "64"]
ENG = {"pin": "b11856", "new": "b12110"}
FORK_ENV = {"LLAMA_SPEC_LOOKUP": "3", "LLAMA_SPEC_LOOKUP_W": "16", "LLAMA_SERVER_CACHE_SHARE_MIN": "1024",
            "LLAMA_GPU_VERIFY": "1", "LLAMA_SERVER_REASONING_CONTROL": "0"}
FORK_ARGS = ["--spec-type", "draft-mtp", "--spec-draft-n-max", "4", "-ctkd", "q4_0", "-ctvd", "q4_0",
             "--spec-draft-vocab", "{nv}/draft_vocab_qwen38.txt", "--spec-draft-vocab-n", "65536",
             "--spec-draft-head-type", "iq4_xs", "--spec-mtp-type", "iq4_xs"]


LEAN = "--lean" in sys.argv  # 16 GB / 12 GB: also run the lean-reserve build with a q4_0 draft KV (fork_arms)


def base(card: str, name: str, src: str = "") -> dict:
    c = json.load(open(src or f"{HERE}/cards-final/{card}.json"))
    c["card"] = name
    c["res"] = f"/root/res-{name}"
    c["engines"] = dict(ENG)
    c["blocks"] = (["perf", "abba", "fill"] + (["ctxprobe"] if c.get("ctx_probe") else []) + ["stab"]
                   + (["moe"] if c.get("moe") else []))
    c.pop("mem_ctx", None)
    if c.get("mtp"):
        c["spec_variants"] = [["u", "new", UBD, c["ub"], c["ctx"]]]
        c["spec_n"] = [1, 2, 3]
        if LEAN:
            c["engines"]["lean"] = "b12110lean"
            c["engine_base"] = {"b12110lean": "b12110"}
            q4d = ["-ctkd", "q4_0", "-ctvd", "q4_0"]
            c["fork_arms"] = [{"label": f"L{n}", "engine": "lean", "extra": ["--spec-type", "draft-mtp",
                               "--spec-draft-n-max", str(n)] + q4d + UBD, "ub": c["ub"], "ctx": c["ctx"]} for n in (1, 2)]
            # the lean build's own context ceiling (ModelSelect67 ctx_probe values) as fill tests
            for p in c.get("ctx_probe", []):
                c["fork_arms"].append({"label": f"L1c{p}", "engine": "lean", "extra": ["--spec-type", "draft-mtp",
                                       "--spec-draft-n-max", "1"] + q4d + UBD, "ub": c["ub"], "ctx": p})
    if c.get("moe"):
        c["moe"]["grid"] = [[1, 0.0], [2, 0.0], [3, 0.0]]
    return c


def write(c: dict) -> str:
    os.makedirs(f"{HERE}/cards-run", exist_ok=True)
    p = f"{HERE}/cards-run/{c['card']}.json"
    json.dump(c, open(p, "w"), indent=1)
    print(p, c["model"]["file"], c["ctx"], c["kv"], c["ub"], c.get("mtp"), c["blocks"],
          [a["label"] for a in c.get("fork_arms", [])])
    return p


for card in [a for a in sys.argv[1:] if not a.startswith("--")]:
    c = base(card, f"{card}f")
    if card in ("3090", "4090"):
        # ModelSelect67: UD-Q4_K_XL MTP1 ub256 ubd64 at 262144 (402 MiB free predicted) vs its UD-Q4_K_M pick
        cat = json.load(open(os.path.expanduser("~/KERNEL/app/engine/data/catalog.json")))
        f = next(q for m in cat["models"] if m["id"] == "qwen38-27b" for q in m["quants"] if q["quant"] == "UD-Q4_K_XL")
        xl = dict(c, card=f"{card}xl", res=f"/root/res-{card}xl", ub=256, blocks=["perf", "abba", "fill", "stab"],
                  model={"file": f["path"], "url": f"https://huggingface.co/{f['repo']}/resolve/main/{f['path']}",
                         "sha": f["sha256"], "size": f["sizeBytes"], "id": "qwen38-27b/UD-Q4_K_XL"},
                  spec_variants=[["u", "new", UBD, 256, c["ctx"]]], spec_n=[1, 2, 3])
        xl.pop("moe", None)
        write(xl)
    if card == "3090":
        c["engines"]["topka2"] = "topka2"
        c["engine_base"] = {"topka2": "b12110"}
        c["fork_arms"] = [
            {"label": "F131k", "engine": "topka2", "env": FORK_ENV, "extra": FORK_ARGS, "ub": 512, "ctx": 131072},
            {"label": "U131k-n3", "engine": "new", "extra": ["--spec-type", "draft-mtp", "--spec-draft-n-max", "3"] + UBD,
             "ub": 512, "ctx": 131072},
            {"label": "F262k", "engine": "topka2", "env": FORK_ENV, "extra": FORK_ARGS, "ub": 512, "ctx": c["ctx"]},
        ]
    write(c)
