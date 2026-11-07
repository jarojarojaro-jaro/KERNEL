#!/usr/bin/env python3
"""cards/<card>.json for campaign 67: Enigma's current recommendation per card class (app/engine recommend(), Linux,
2026-11-07) -> model file, ctx, KV type, ubatch; MTP mode; engines (pin b11856 = data/engines.json, new b12110 = v0.9.0)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(os.path.expanduser("~/KERNEL/app/engine/data/catalog.json")))


def q(model: str, quant: str) -> dict:
    m = next(x for x in CAT["models"] if x["id"] == model)
    f = next(x for x in m["quants"] if x["quant"] == quant)
    return {"file": f["path"], "url": f"https://huggingface.co/{f['repo']}/resolve/main/{f['path']}", "sha": f["sha256"],
            "size": f["sizeBytes"], "id": f"{model}/{quant}"}


GEMMA_DRAFT = {"file": "mtp-gemma-4-12b-it.gguf",
               "url": "https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/resolve/main/mtp-gemma-4-12b-it.gguf",
               "sha": "145db9094bc0f85f1701e255a2ed216dcc9800fc8bc8631ad00905b456bd451b", "size": 465109248}
QWEN36_MTP = {"file": "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf",
              "url": "https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF/resolve/5bc3e238d916f48a861bac2f8a1990a0e9b7e98d/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf",
              "sha": "df27a780435b7b45c2597536112ea3cb091f8544c3d0c3318d9f4258b31f7adf", "size": 18209036576,
              "ctx": 131072, "kv": "q4_0", "ub": 512, "vram_limit_mib": 15400, "ncmoe_try": [6, 8, 10, 12, 14, 16, 20, 24]}
ENG = {"pin": "b11856", "new": "b12110"}

G8 = dict(model=q("qwen35-9b", "Q4_K_M"), ctx=184320, kv="q4_0", ub=512, mtp=None)
G10 = dict(model=q("gemma4-12b", "UD-Q4_K_XL"), ctx=262144, kv="q4_0", ub=1024, mtp="drafter", draft=GEMMA_DRAFT)
G12 = dict(model=q("gemma4-12b", "UD-Q4_K_XL"), ctx=262144, kv="q8_0", ub=1024, mtp="drafter", draft=GEMMA_DRAFT)
G12Q6 = dict(model=q("gemma4-12b", "Q6_K"), ctx=262144, kv="q4_0", ub=512, mtp="drafter", draft=GEMMA_DRAFT)
G16 = dict(model=q("qwen38-27b", "UD-Q3_K_XL"), ctx=135168, kv="q4_0", ub=1024, mtp="self", ctx_probe=[163840, 196608],
           mem_ctx=[131072])
G24 = dict(model=q("qwen38-27b", "UD-Q4_K_XL"), ctx=159744, kv="q4_0", ub=512, mtp="self", ctx_probe=[196608, 262144],
           mem_ctx=[262144])
G32 = dict(model=q("qwen38-27b", "UD-Q6_K"), ctx=237568, kv="q4_0", ub=1024, mtp="self", ctx_probe=[262144], mem_ctx=[262144])

CARDS = {
    "3060ti": G8, "3070": G8,
    # 2080 Ti: Enigma's ub 1024 plan OOMs at load (compute 1153 MiB, run 1); -ub 512 is the lossless fix to measure
    "2080ti": dict(G10, ub=512), "3080": G10,
    "3060": G12, "4070": G12, "4070ti": G12, "5070": G12,
    "3080-12": G12Q6,
    "4060ti": G16, "4070tis": G16, "4080": G16, "5060ti": G16, "5070ti": G16, "5080": G16,
    "3090": G24, "4090": G24,
    "5090": G32,
}
os.makedirs(f"{HERE}/cards", exist_ok=True)
for card, g in CARDS.items():
    c = {"card": card, "engines": ENG, "blocks": ["mem", "perf", "pmin", "abba", "fill", "ctxprobe", "stab"], **g}
    if card == "5080":  # free-traffic 16 GB host: the 18 GB MoE pull costs nothing
        c["moe"] = QWEN36_MTP
        c["blocks"] = c["blocks"] + ["moe"]
    json.dump(c, open(f"{HERE}/cards/{card}.json", "w"), indent=1)
    dl = (c["model"]["size"] + (c.get("draft") or {}).get("size", 0) + (c.get("moe") or {}).get("size", 0)) / 1e9 + 1.6
    print(f"{card:8} {c['model']['id']:24} ctx={c['ctx']:6} kv={c['kv']} ub={c['ub']} mtp={c['mtp']} download~{dl:.1f} GB")
