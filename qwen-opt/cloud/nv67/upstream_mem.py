#!/usr/bin/env python3
"""upstream_mem.py — VRAM of stock llama.cpp CUDA (b11856/b12110) llama-server, fitted on campaign-67 `-lv 4` buffers
(arms.jsonl `buffers`, 2026-11-07; error -3..+23 MiB on 19 points: Qwen3.8-27B Q3/Q4/Q6 plain + MTP n1/n3, ub 256/512/1024,
ubd 64; Gemma 12B plain + drafter; Qwen3.5-9B). Report: ~/KERNEL/product/research/67b-wybor-modeli-nvidia.md §1.

VRAM(MiB) = W + KV + RS + C_main [+ MTP: KVd + Cd] [+ drafter: Wd + Cd] + ovh(card);  fits iff VRAM + 128 <= CUDA total
  W      = all tensors - token_embd (host unless the head is tied) - nextn layer (plain arm does not load it; +335 MiB on
           Qwen3.8-27B with MTP) - experts of the first N layers with --n-cpu-moe N
  KV     = fitcalc.kv_bytes (iSWA-aware), at -ctk/-ctv type
  RS     = recurrent state (GDN/Mamba, f32) x (n_max + 1) with --spec-type draft-mtp (n_rs_seq), x1 plain
           (Qwen3.8-27B: 149.6 / 299.2 / 598.5 / 748.1 MiB at n = 0 / 1 / 3 / 4)
  C_main = ctx x (f16 K+V bytes of one full-attention layer + 2*ub) + act(ub);  act = ub x n_embd x 40 (27B: 100.29/512 ub)
           (FA f16 copy + f16 KQ mask are in the reserved compute buffer; prompt growth afterwards is +2..+28 MiB)
  MTP (nextn in the file): KVd = ctx x nextn K+V x 2 B (draft KV stays f16 by default: 1024 MiB @262k on 27B)
           Cd  = ctx x 2*ubd + ubd x 32 x n_embd  (ubd = --spec-draft-n-ubatch, default ub; ubd 64 -> ~40 MiB @262k)
                 with -ctkd/-ctvd q4_0 add ctx x f16 K+V of the nextn layer (the MMA f16 copy) -> worse, not better
           lean (our port, q4_0 draft KV): Cd ~ 40 MiB, KVd at q4_0
  drafter (Gemma 4 mtp-*.gguf, shares target KV): Wd = its W (429 MiB), Cd = ctx x (f16 K+V of a full layer + 2*ubd) + act
  ovh    = CUDA context/cuBLAS/pools at load, fitted per card (MiB); 5060ti host had a display (339 MiB idle) in it
Usage: python3 upstream_mem.py <gguf|repo:file> <card> <ctx> [kv] [ub] [mtp_n] [ubd]
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/qwen-opt/cloud"))
import fitcalc as F  # noqa: E402

MiB = 1048576.0
OVH = {"3060": 150, "4070": 196, "3070": 195, "3080": 276, "3090": 336, "4060ti": 173, "5060ti": 500, "5080": 309,
       "4090": 465, "5090": 579}
CUDA_TOTAL = {"3060": 11909, "4070": 11955, "3070": 7842, "3080": 9927, "3090": 24126, "4060ti": 15947, "5060ti": 15846,
              "5080": 15837, "4090": 24082, "5090": 32109, "2080ti": 10817}
MARGIN = 128


def f16_layer(d: dict, mtp: bool = False) -> int:
    full = [x for x in d["layers"] if x["mtp"] == mtp and not x["swa"]]
    return max(((x["k"] + x["v"]) * 2 for x in full), default=0)


def act(d: dict, ub: int, draft: bool = False) -> float:
    if d["arch"] == "qwen35" and d["n_embd"] == 5120:
        return ub * (80.28 if draft else 100.29) / 512 * MiB
    a = ub * d["n_embd"] * (32 if draft else 40)
    if d["n_exp"]:
        a += ub * d["k_exp"] * 2048 * 4
    return a


def mem(d: dict, card: str, ctx: int, kv: str = "q4_0", ub: int = 512, mtp: int = 0, ubd: int | None = None,
        dkv: str = "f16", drafter: dict | None = None, ncmoe: int = 0, lean: bool = False) -> tuple[float, dict]:
    p = {}
    nextn = mtp and d["nextn"] > 0
    p["W"] = (d["W_gpu"] - (0 if nextn else d["mtp_bytes"]) - F.offloaded_bytes(d, ncmoe)) / MiB
    p["KV"] = F.kv_bytes(d, kv, ctx, ub) / MiB
    p["RS"] = F.rs_mib(d) * ((mtp + 1) if mtp else 1)
    p["C"] = (ctx * (f16_layer(d) + 2 * ub) + act(d, ub)) / MiB
    u = ubd or ub
    if nextn:
        p["KVd"] = ctx * F.kv_per_tok(d, "f16", True) * (F.BPE[dkv] / 2) / MiB
        p["Cd"] = (40.0 * ctx / 262144 + 8) if lean else \
            (ctx * (2 * u + (f16_layer(d, True) if dkv != "f16" else 0)) + act(d, u, True)) / MiB
    if mtp and drafter is not None:
        p["Wd"] = drafter["W_gpu"] / MiB
        p["Cd"] = 48.0 if lean else (ctx * (f16_layer(d) + 2 * u) + act(d, u, True)) / MiB
    p["ovh"] = OVH[card]
    return sum(p.values()), p


if __name__ == "__main__":
    a = sys.argv[1:]
    d = F.describe(a[0])
    card, ctx = a[1], int(a[2])
    kv = a[3] if len(a) > 3 else "q4_0"
    ub = int(a[4]) if len(a) > 4 else 512
    n = int(a[5]) if len(a) > 5 else 0
    ubd = int(a[6]) if len(a) > 6 else None
    t, p = mem(d, card, ctx, kv, ub, n, ubd)
    print(f"{t:.0f} MiB, free {CUDA_TOTAL[card] - t:.0f} (need >= {MARGIN}):", {k: round(v) for k, v in p.items()})
