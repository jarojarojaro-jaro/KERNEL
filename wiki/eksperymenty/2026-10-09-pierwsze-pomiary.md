---
typ: eksperyment
tags: [eksperymenty, qwen, baza]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/benchmarks/2026-10-09-rx7900xtx-qwen38-27b.md; ~/KERNEL/qwen-opt/NOTES.md:3-16,38-50; ~/KERNEL/qwen-opt/SPEC-QWEN27B.md:50-77
status: aktualne
---
# 2026-10-09: pierwsze pomiary Qwen3.8-27B (59 → 92 t/s)

**Pierwszy dzień: od starego buildu użytkownika (59.2 t/s) do 85.5 t/s na ROCm i 91.8 t/s na Vulkanie dzięki aktualizacji llama.cpp, wielokolumnowemu MMVQ, cache q8_1 i słownikowi draftu 64k.**

Warunki: RX 7900 XTX, ROCm 10.0.0 pre4, Mesa RADV 25.2.8 w przestrzeni użytkownika; `serve_bench.py`: chat, T=0, 256 tokenów, 3 prompty EN + 3 PL × 3 przebiegi, mediana; ctx 204800, KV q4_0, FA.

| konfiguracja | t/s | proza PL | VRAM |
|---|---|---|---|
| stary build b356fa262 (1 wrz), ROCm, MTP n=3 | 59.2 | 47.4 | 22.8 GB |
| ROCm + kernele + cache q8_1 + słownik 64k, MTP n=4 | 85.5 | 60.2 | 23.2 GB |
| Vulkan RADV + słownik 64k, MTP n=5 | 91.8 | 59.4 | 22.3 GB |
| DFlash2 n=6, kod EN (ctx 131072) | 116–127 | — | 22.0 GB |

Co dało przyspieszenie: aktualizacja llama.cpp (MTP 58 → 69 t/s, prompty EN), MMVQ 2–8 kolumn (Q5_K 8 kol. 296 → 621 GB/s), cache q8_1 (+2–4%), słownik draftu 64k (+7.5%, bezstratnie). Prefill: ROCm pp4096 1044 vs Vulkan 850 t/s.

Wniosek dnia: Vulkan +9% w dekodowaniu, ROCm +23–43% w prefillu; DFlash2 słabo przewiduje polski (proza PL ~40 t/s).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[2026-10-10-sweep-mtp-dflash]]
- [[mmvq-multikolumnowe]]
- [[qwen3-8-27b]]
- [[rocm-vs-vulkan]]
