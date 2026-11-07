---
typ: produkt
tags: [produkt, nvidia, modele, vram, kontekst]
aktualizacja: 2026-11-07
zrodlo: product/research/67b-wybor-modeli-nvidia.md; ~/qwen-opt/cloud/runs/nv67/mkcards_final.py; arms.jsonl kampanii 67 (b11856/b12110, -lv 4, 2026-11-07)
status: do-sprawdzenia
---
# Ostateczne modele per klasa VRAM (NVIDIA, Enigma)

**Na upstream llama.cpp b12110 Qwen3.8-27B mieści 262 144 z MTP na 24 GB (UD-Q4_K_M) i 32 GB (UD-Q6_K). Na 16 GB 262k mieści tylko IQ3_XXS bez MTP, a z MTP 200–217k. Na 12 GB 27B osiąga ≥ 131k tylko w 2 bitach. Na 8–10 GB wybór to LFM2.5 z `--n-cpu-moe`.**

| klasa | wybór | ctx | uwaga |
|---|---|---|---|
| 32 GB | 27B UD-Q6_K, KV q4_0, MTP 3 | 262 144 | 2.9 GiB wolne (zmierz. load 29 158 MiB) |
| 24 GB | 27B UD-Q4_K_M, MTP 2, ubd 64 | 262 144 | 1.1–1.3 GiB wolne; UD-Q4_K_XL MTP 1: 402 MiB |
| 16 GB | GSQ IQ3_XXS-mtp (ISTA), MTP 1 | 200–217k (plain 262k) | KLD 0.119 vs 0.039 dla UD-Q3_K_XL (164k plain) |
| 12 GB | Saluki-MTP 135k / Bonsai Q2_0 221k | – | Saluki od 2026-11-05 na CC BY-NC 4.0 |
| 11 GB | Bonsai Q2_0 | 163 840 | – |
| 8–10 GB | LFM2.5 Q4_K_M, KV q8_0, ncm 26 / 20 | 131 072 | licencja < US$10M |

Gemma 4 12B odrzucona przez użytkownika. Qwen3.6-35B-A3B to opcja MoE (262k, RAM ≥ 32 GB).

Model pamięci (błąd ≤ 23 MiB na 19 punktach):
- RS × (n_max+1);
- KV draftu f16;
- `--spec-draft-n-ubatch 64` zmniejsza rezerwę draftu do 40 MiB;
- limit to suma CUDA, a nie nvidia-smi;
- upstream rośnie przy wypełnieniu tylko o +2…+28 MiB.

Aplikacja dawała 160k, bo `memory.ts` liczy wzrost forka (3.77 × warstwa f16).

Rezerwa MTP w upstream CUDA (punkt z DO-ZAPISANIA z 11-06): bufor draftu to ctx × 2·ub (648 MiB przy 262k i ub 1024, 5090). Stockowe `--spec-draft-n-ubatch 64` zmniejsza go do 40 MiB. Zostaje KV draftu f16 (1024 MiB przy 262k), a `-ctkd q4_0` dokłada kopię f16; port lean na b12110 robi LeanPort67 (~0.7 GiB).

## Powiązane
- [[produkt/_hub|Produkt]]
- [[raport-33-modele-na-karty]]
- [[raport-65-vram-rezerwa-mtp]]
- [[qwen3-8-27b]]
- [[saluki]]
- [[bonsai]]
- [[lfm2-5-24b-a2b]]
- [[rtx-3090]]
