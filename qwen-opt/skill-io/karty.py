#!/usr/bin/env python3
"""Sufity ceiling.py (skill-io @ fda968e) dla wielu kart, ten sam model i kwant (Qwen3.8-27B Q4_K_M, KV q4_0, MTP n4)."""
import json
exec(open("ceiling.py").read().split("def main")[0])
base = json.load(open("ceiling-qwen27b-unc-xtx.json"))
K = json.load(open("karty.json"))["karty"]
GB_GPU = 16.13 + 0.40 + 1.0   # wagi na GPU + MTP + bufory obliczeń [INFERENCE ~1 GB]
print("| firma | karta | arch | VRAM | GB/s | FP16 / INT8 T | plain 2k | MTP a=3,2 2k | 128k | prefill 4k FP16 / INT8 | 32k | 256k śr. | mieści 262k? |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for f, n, a, vram, bw, fp16, i8, uw in K:
    m = dict(base, bandwidth_gbs=bw)
    d0 = decode_ceiling(m, 0, 1.0, 2048); d2 = decode_ceiling(m, 4, 3.2, 2048); d128 = decode_ceiling(m, 4, 3.2, 131072)
    p = lambda t, L: prefill_ceiling(dict(m, peak_tflops=t), L)
    kv_fit = (vram * 1.0737 - GB_GPU) / (18432e-9 + 1152e-9)  # GiB->GB, KV celu + warstwy MTP
    fit = "tak" if kv_fit >= 262144 else (f"~{int(kv_fit/1024)}k" if kv_fit > 4096 else "nie (wagi > VRAM)")
    print(f"| {f} | {n} | {a} | {vram} | {bw} | {fp16:g} / {i8:g} | {d0:.0f} | {d2:.0f} | {d128:.0f} | {p(fp16,4096):.0f} / {p(i8,4096):.0f} | {p(i8,32768):.0f} | {p(i8,262144):.0f} | {fit} |")
# zmierzone vs sufit dla kart z naszymi pomiarami (inne kwanty -> własny sufit)
print()
for n, bw, verify_gb, meas, opis in [
    ("RX 7900 XTX", 960, 16.13, 119.3, "Q4_K_M, spec_sweep T=1"),
    ("RTX 3090", 936, 16.84 + 0.30, 79.97, "UD-Q4_K_XL, fork kvqleana, final-recipes"),
    ("RTX 4090", 1008, 16.84 + 0.30, 101.27, "UD-Q4_K_XL, fork kvqlean"),
    ("RTX 5090", 1792, 20.94 + 0.30, 148.57, "UD-Q6_K, fork kvqlean"),
    ("RTX 5060 Ti", 448, 10.04 + 0.30, 49.44, "IQ3_XXS GSQ, fork kvqlean 196k")]:
    m = dict(base, bandwidth_gbs=bw, dense_gb=verify_gb - base["lm_head_gb"])
    c = decode_ceiling(m, 4, 3.2, 2048)
    print(f"{n:12s} sufit a=3,2 {c:6.0f}  zmierzone {meas:6.1f}  {100*meas/c:4.0f}%  ({opis})")
