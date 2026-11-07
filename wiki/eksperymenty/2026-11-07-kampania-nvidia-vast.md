---
typ: eksperyment
tags: [eksperymenty, nvidia, cuda, vast, enigma, mtp]
aktualizacja: 2026-11-07
zrodlo: ~/qwen-opt/cloud/results/nv67-*; ~/qwen-opt/cloud/runs/nv67 (kopiowane do ~/KERNEL/qwen-opt/cloud/nv67); product/research/67-nvidia-vast-kampania.md
status: aktualne
---
# Kampania NVIDIA na Vast: 17 kart, 262 144 z MTP na 24 i 32 GB (2026-11-07)

**Na 24 GB (4090) pełny kontekst 262 144 z MTP n=3 daje 79,1 t/s wobec 47,2 bez spekulacji (+67,6%), a na 32 GB (5090) 86,9 t/s (+44,7%); na 16 GB warianty 27B z MTP wywalają się przy pierwszym 4096-tokenowym prompcie, bo brakuje zapasu na doładowanie kerneli CUDA (≥0,7 GiB ponad załadowany model).**

Warunki: upstream llama.cpp b11856 (pin Enigmy) i b12110, KV q4_0, `-fa`, mediana `spec_sweep` (6 promptów PL/EN × seedy 1–3, T=1). Każda para z pełnym wypełnieniem kontekstu i 30-minutowym soaken długich zapytań (poza oznaczonymi).

| Karta | Model | ctx | dziś → teraz | Weryfikacja |
|---|---|---|---|---|
| 5090 32 GB | Qwen3.8-27B **UD-Q6_K**, MTP n=2 | **262 144** | 60,0 → **86,9 t/s** (+44,7%) | fill 261 504 tok. (dec 14,3 → 49,9), soak, szczyt 28 446/32 109 MiB |
| 5090 32 GB | **Qwen3.6-35B-A3B** Q5_K_XL MoE, MTP n=2 | **262 144** | 244,6 → **319,5 t/s** (+30,6%) | fill (prefill 3 060 t/s, dec 145,5), soak |
| 4090 24 GB | Qwen3.8-27B **UD-Q4_K_XL**, MTP n=3, ub 256 | **262 144** | 47,2 → **79,1 t/s** (+67,6%) | fill 261 504 tok., soak, szczyt 24 036/24 082 MiB |
| 4090 24 GB | UD-Q4_K_M, MTP n=2–4, ub 512 | **262 144** | 49,8 → 78,0–79,5 t/s | load 23 598 MiB (1,1 GiB zapasu) |
| 5060 Ti 16 GB | ISTA GSQ IQ3_XXS-mtp, bez MTP | 200 704 | 33,3 t/s | fill 200 064 tok. (prefill 470 t/s) |
| 4060 Ti 16 GB | ISTA GSQ IQ3_XXS-mtp, bez MTP | 217 088 | 23,7 t/s | fill 216 448 tok. (prefill 259 t/s) |
| 5080 16 GB | ISTA GSQ IQ3_XXS-mtp | 208 896 | 62,7 (pin) → 63,0–63,8 | – |
| 4070 12 GB | Underdog Saluki 27B + MTP n=1 | **151 552** | 39,8 t/s | fill 135 168 i 151 552 OK, soak |
| 3060 12 GB (105 W) | Saluki-MTP | 135 168 | 19,6 t/s | tylko prędkość |
| 3080 10 GB | LFM2.5-24B Q4_K_M, KV q8_0, `--n-cpu-moe` | 131 072 | 20,1 → 20,4 t/s | ABBA |
| 3070 8 GB | LFM2.5-24B Q4_K_M, eksperci w RAM | 131 072 | 7,1 t/s | – |

**MTP n:** 27B na 24 GB → n=3 (n1 67,0 / n2 76,8 / n3 79,1); na 32 GB → n=2 (n1 80,6 / n2 86,8 / n3 83,8 / n4 79,5). Enigma ma dziś sztywne n=4.

**Silnik b11856 → b12110:** 3060 +0,2%, 3080 +1,9%, 4070 +1,2%, 4090 +0,5%, 5060 Ti +0,1%, 5080 +0,6%, 5090 0%, **3070 −8%** (prefill 1 809 → 1 618). md5 greedy zmienia się między buildami.

**Wyniki negatywne:** `p-min` 0,5/0,8 wolniejsze wszędzie (5080 MoE 83,4 → 80,9 / 76,4; 3080 120,2 → 113,5 / 109,9; 4070 101,5 → 101,3 / 96,4). `-ctkd q4_0` bez portu lean dodaje 0,9–1,5 GiB kopii f16.

**Błąd planera (naprawiony):** 16 GB z MTP przy 135 168 nie ładuje się; przy IQ3_XXS-mtp 200–217k ładuje się z 0,5–0,66 GiB wolnym i wywala przy pierwszym prefillu 4 096 tok. (`launch_mul_mat_q`). W Enigmie: dokładny odstęp `nvidia-smi`→CUDA per karta (447–498 MiB), zapas 300 MiB na doładowanie kerneli, zmierzone plany 262 144 dla 4090 i 5090, batch 256, MTP n=3 + `--spec-draft-n-ubatch 64`.

**Nie dokończone:** Bonsai 2 (silnik PrismML + doszczep MTP gotowe, nieuruchomione), 3090 + fork cuda-topka2, kernel `kvq` na CUDA, port lean na kartach, 2080 Ti (obcy proces na karcie).

**Koszt:** $3,47 z $10,51 kredytu (17 maszyn, od $0,056 do $0,48/h), wszystkie skasowane.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[raport-67-kampania-nvidia]]
- [[2026-11-06-final-mode]]
- [[glowica-mtp]]
