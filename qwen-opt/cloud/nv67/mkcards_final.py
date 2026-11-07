#!/usr/bin/env python3
"""cards-final/<card>.json (+ cards-final/alt/<card>-<variant>.json) for campaign 67, final phase: the per-class picks of
report 67b (~/KERNEL/product/research/67b-wybor-modeli-nvidia.md), same schema as mkcards.py / cards/.

Direction (user, 2026-11-07): default for every class >= 8 GB = Qwen3.8-27B family in small quants + LFM2.5; no Gemma.
Memory model behind every ctx (upstream CUDA b12110, calibrated on the live nv67 `-lv 4` buffers, error <= 23 MiB on
19 points): VRAM = W (+ nextn layer with MTP) + KV + RS x (n_max + 1 with MTP) + ctx x (f16 K+V of one full layer + 2 x ub)
+ act(ub) [+ draft KV f16 + ctx x 2 x ubd] + ovh(card); fits when VRAM + 128 MiB <= CUDA total (not nvidia-smi total).

- "model"/"ctx"/"kv"/"ub"/"mtp": the class pick. "main_extra" (LFM on <= 10 GB): extra server flags for EVERY main arm
  (`--n-cpu-moe N`); nv67.py does not read it yet: the harness owner adds it to base_args or runs these by hand.
- "moe": Qwen3.6-35B-A3B (MTP GGUF) at 262144 as the MoE option (experts in RAM on <= 16 GB, all in VRAM on 24/32 GB).
- alt/: second candidates of the same class (same schema), run if the instance has time.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = f"{HERE}/cards-final"
ENG = {"pin": "b11856", "new": "b12110"}
BLOCKS = ["mem", "perf", "pmin", "abba", "fill", "ctxprobe", "stab", "moe"]
REV36 = "5bc3e238d916f48a861bac2f8a1990a0e9b7e98d"


def hf(repo: str, file: str, sha: str, size: int, mid: str, rev: str = "main") -> dict:
    return {"file": file, "url": f"https://huggingface.co/{repo}/resolve/{rev}/{file}", "sha": sha, "size": size, "id": mid}


R27 = "unsloth/Qwen3.8-27B-GGUF"
Q27_Q6K = hf(R27, "Qwen3.8-27B-UD-Q6_K.gguf", "c9c206812fbe4ac7b76a729e25928b63f2ae89d37f69da7a71c20aec763cd436",
             21983677344, "qwen38-27b/UD-Q6_K")
Q27_Q4KM = hf(R27, "Qwen3.8-27B-UD-Q4_K_M.gguf", "322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482",
              16464440224, "qwen38-27b/UD-Q4_K_M")
Q27_Q3 = hf(R27, "Qwen3.8-27B-UD-Q3_K_XL.gguf", "8c2a45ff85e7674ca185ec8eb6cdeab0e617ed9d8018caed0b64380eb2a67a5e",
            13146393504, "qwen38-27b/UD-Q3_K_XL")
GSQ_IQ3XXS = hf("ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF", "Qwen3.8-27B-GSQ-RCO-IQ3_XXS-mtp.gguf",
                "63f29a2189a6b4cc31f81e093d3856ad293a5583114439f41ae1ed7af4093262", 10442827840, "qwen38-27b-gsq/IQ3_XXS-mtp")
SALUKI_MTP = hf("Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF", "Underdog-Saluki-27B-1.0-IQ2-mix-MTP.gguf",
                "98f6ebb527917a2541df8e667d51c3ec8a8bb135b44c606d40cc6ed924e89e52", 8349689920, "saluki-27b-mtp/IQ2-mix")
BONSAI_Q2 = hf("prism-ml/Ternary-Bonsai-2-27B-gguf", "Ternary-Bonsai-2-27B-Q2_0.gguf",
               "4f99aed01b8a877e153f9aa6569a4440fe17c59701cc0953e36d7f460549e70e", 7626008928, "bonsai2-27b/Q2_0")
LFM_Q4KM = hf("LiquidAI/LFM2.5-24B-A2B-GGUF", "LFM2.5-24B-A2B-Q4_K_M.gguf",
              "d3334405b96228eb9908cdebb5c6194908f2da64282bda852afc3a3910c64e7d", 14526258464, "lfm25-24b-a2b/Q4_K_M")
M36 = {
    "UD-IQ4_XS": ("df27a780435b7b45c2597536112ea3cb091f8544c3d0c3318d9f4258b31f7adf", 18209036576),
    "UD-Q4_K_XL": ("55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1", 22853663008),
    "UD-Q5_K_XL": ("9de9a9420f61a0bb59bb2ca1ea170a6a57f6821fa1deec915bcaef523730a919", 27159116064),
}
# CUDA-visible total (llama.cpp device_info / cudaMemGetInfo), MiB: measured on the nv67 hosts, class value otherwise
CUDA_TOTAL = {"2080ti": 10817, "3060": 11909, "3060ti": 7842, "3070": 7842, "3080-12": 11909, "3080": 9927, "3090": 24126,
              "4060ti": 15947, "4070": 11955, "4070ti": 11955, "4070tis": 15837, "4080": 15837, "4090": 24082,
              "5060ti": 15846, "5070": 11955, "5070ti": 15837, "5080": 15837, "5090": 32109}


def moe(quant: str, kv: str, ncm: list[int], card: str) -> dict:
    sha, size = M36[quant]
    m = hf("unsloth/Qwen3.6-35B-A3B-MTP-GGUF", f"Qwen3.6-35B-A3B-{quant}.gguf", sha, size, f"qwen36-35b-a3b-mtp/{quant}", REV36)
    return {**m, "ctx": 262144, "kv": kv, "ub": 512, "vram_limit_mib": CUDA_TOTAL[card] - 128, "ncmoe_try": ncm}


# class picks (ctx = largest multiple of 4096 that fits with the stock MTP flags at the class's worst card)
LFM8 = dict(model=LFM_Q4KM, ctx=131072, kv="q8_0", ub=512, mtp=None, main_extra=["--n-cpu-moe", "26"])
LFM10 = dict(model=LFM_Q4KM, ctx=131072, kv="q8_0", ub=512, mtp=None, main_extra=["--n-cpu-moe", "20"])
BON11 = dict(model=BONSAI_Q2, ctx=163840, kv="q4_0", ub=256, mtp=None)
SAL12 = dict(model=SALUKI_MTP, kv="q4_0", ub=256, mtp="self")
GSQ16 = dict(model=GSQ_IQ3XXS, kv="q4_0", ub=256, mtp="self")
G24 = dict(model=Q27_Q4KM, ctx=262144, kv="q4_0", ub=512, mtp="self", mem_ctx=[262144])
G32 = dict(model=Q27_Q6K, ctx=262144, kv="q4_0", ub=1024, mtp="self", mem_ctx=[262144])

CARDS = {
    "3060ti": {**LFM8, "moe": ("UD-IQ4_XS", "q4_0", [34, 35, 36, 37, 38, 40])},
    "3070": {**LFM8, "moe": ("UD-IQ4_XS", "q4_0", [34, 35, 36, 37, 38, 40])},
    "3080": {**LFM10, "moe": ("UD-Q4_K_XL", "q4_0", [31, 32, 33, 34, 35, 37])},
    "2080ti": {**BON11, "moe": ("UD-Q4_K_XL", "q4_0", [29, 30, 31, 32, 33, 35])},
    "3060": {**SAL12, "ctx": 135168, "ctx_probe": [151552], "moe": ("UD-Q4_K_XL", "q4_0", [27, 28, 29, 30, 31, 33])},
    "4070": {**SAL12, "ctx": 135168, "ctx_probe": [151552], "moe": ("UD-Q4_K_XL", "q4_0", [27, 28, 29, 30, 31, 33])},
    **{c: {**SAL12, "ctx": 131072, "ctx_probe": [147456], "moe": ("UD-Q4_K_XL", "q4_0", [27, 28, 29, 30, 31, 33])}
       for c in ("3080-12", "4070ti", "5070")},
    "4060ti": {**GSQ16, "ctx": 217088, "ctx_probe": [245760, 262144], "moe": ("UD-Q4_K_XL", "q4_0", [18, 19, 20, 21, 22, 24])},
    "5060ti": {**GSQ16, "ctx": 200704, "ctx_probe": [225280, 262144], "moe": ("UD-Q4_K_XL", "q4_0", [19, 20, 21, 22, 23, 25])},
    **{c: {**GSQ16, "ctx": 208896, "ctx_probe": [233472, 262144], "moe": ("UD-Q4_K_XL", "q4_0", [19, 20, 21, 22, 23, 25])}
       for c in ("4070tis", "4080", "5070ti", "5080")},
    "3090": {**G24, "moe": ("UD-IQ4_XS", "q8_0", [0, 1, 2])},
    "4090": {**G24, "moe": ("UD-IQ4_XS", "q8_0", [0, 1, 2])},
    "5090": {**G32, "moe": ("UD-Q5_K_XL", "q8_0", [0, 1, 2])},
}
# second candidates (alt/): same schema, no moe block
NOMOE = [b for b in BLOCKS if b != "moe"]
ALT = {
    "3060-bonsai": ("3060", dict(model=BONSAI_Q2, ctx=217088, kv="q4_0", ub=256, mtp=None, ctx_probe=[221184])),
    "3060-lfm": ("3060", dict(model=LFM_Q4KM, ctx=131072, kv="q8_0", ub=512, mtp=None, main_extra=["--n-cpu-moe", "14"])),
    "4060ti-gsq-262k": ("4060ti", dict(model=GSQ_IQ3XXS, ctx=262144, kv="q4_0", ub=256, mtp=None)),
    "4060ti-q3kxl": ("4060ti", dict(model=Q27_Q3, ctx=167936, kv="q4_0", ub=256, mtp="self", ctx_probe=[172032])),
    "4060ti-lfm": ("4060ti", dict(model=LFM_Q4KM, ctx=131072, kv="q8_0", ub=512, mtp=None)),
    "4060ti-saluki-262k": ("4060ti", dict(model=SALUKI_MTP, ctx=262144, kv="q4_0", ub=256, mtp="self")),
}
os.makedirs(f"{OUT}/alt", exist_ok=True)


def dump(path: str, c: dict) -> None:
    json.dump(c, open(path, "w"), indent=1)
    dl = (c["model"]["size"] + (c.get("moe") or {}).get("size", 0)) / 1e9 + 1.6
    print(f"{os.path.basename(path)[:-5]:20} {c['model']['id']:28} ctx={c['ctx']:6} kv={c['kv']} ub={c['ub']} mtp={c['mtp']} "
          f"{' '.join(c.get('main_extra', []))} | moe {(c.get('moe') or {}).get('id', '-')} {(c.get('moe') or {}).get('ncmoe_try', '')} "
          f"| download~{dl:.1f} GB")


for card, g in CARDS.items():
    mq, mkv, ncm = g.pop("moe")
    dump(f"{OUT}/{card}.json", {"card": card, "engines": ENG, "blocks": BLOCKS, **g, "moe": moe(mq, mkv, ncm, card)})
for name, (card, g) in ALT.items():
    dump(f"{OUT}/alt/{name}.json", {"card": card, "engines": ENG, "blocks": NOMOE, **g})
