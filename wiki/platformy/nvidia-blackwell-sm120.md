---
typ: platforma
tags: [platformy, nvidia, blackwell, sm120, playbook]
aktualizacja: 2026-11-28
zrodlo: qwen-opt/skill-io/karty.json:144-163,353-366; qwen-opt/cloud/hostguard.sh:1-8; ~/qwen-opt/cloud/nvq3/runk204.sh:92-101; wiki/produkt/final-recipes-nvidia.md; wiki/testy/2026-11-17-k114-nvidia-sufit.md; wiki/testy/2026-11-27-k204-enigma-16gb-inkling.md; wiki/testy/2026-11-28-k207-ablacja-zamiast-lora.md; wiki/testy/2026-11-27-nvq4.md; wiki/testy/2026-11-27-nvq5.md; wiki/KOLEJKA-TESTOW.md:223,252; wiki/REKORDY.md:178,189,194; wiki/stos/sm-86-89-120.md; wiki/optymalizacje/latki-na-nvidia.md
status: aktualne
---
# NVIDIA Blackwell sm_120 (RTX 5060 Ti, 5070, 5080, 5090): playbook topki

**Na sm_120 topki to 5090 Qwen3.8-27B fork+kvq+lean 148,57 t/s przy 262 144 (2026-11-07) i 5060 Ti Inkling 2 Mini + DSpark 66,45 / 61,97 t/s przy 262 144 na upstreamie, a z naszym `--ablate-lora` 88,45 / 90,78 t/s (2026-11-28); PDL i FP4 są, ale dekod zysku z nich nie dał.**

## Dzień pierwszy
- **Sterownik i CUDA:** 580.173.02 na 5060 Ti, CUDA 12.8 ([[cuda-stos]]); `hostguard.sh` wymaga `cuda_max_good>=12.8`. Profilowanie: nsys 2025.3 (2024.6 nic nie śledzi na sm_120, [[2026-11-27-nvq4]]).
- **Bramka pełnej mocy** (`hostguard.sh hg_check`): moc ≥ 85% domyślnej, `clocks.max.mem` ≥ 85% z `karty.json:353-366` (5060 Ti i 5070 14001, 5080 15001, 5090 14001 MHz), < 80 °C. Odrzucona w K-118: 5070 175/250 W.
- **Bramka CPU:** `runk204.sh` (llama-bench tg256, użycie GPU ≥ 85%) nie łapie EPYC Zen2: 5060 Ti na EPYC 7402 99% w llama-bench, tg256 74,9 vs 78,0, a serwer z DSpark 2,1–2,6× wolniejszy niż na Ryzenie 9700X ([[2026-11-28-k207-ablacja-zamiast-lora]]); EPYC 7502 28,4 vs Ryzen 7600 66,5 t/s (K-204). Zen2 odrzucać, CPU zapisywać przy wyniku.
- **Build:** tylko `-DCMAKE_CUDA_ARCHITECTURES=120` (CMake robi `120a`, potrzebne dla FP4 `mma.sync`); 5060 Ti fork 503 s ([[cuda-stos]]).
- **Sufit pasma:** t/s ≤ pasmo ÷ bajty na token, ze spekulacją × tok./krok. 5060 Ti 448 GB/s (`karty.json:144`) ÷ 10,34 GB ≈ 43,3 t/s; 5090 1792 GB/s (`karty.json:154`). 5070 i 5080: pasma brak w `karty.json`.
- **Sanity:** 5060 Ti GSQ IQ3_XXS bez spekulacji 31,9 t/s (74% pasma), prefill ~11k 828 t/s ([[2026-11-17-k114-nvidia-sufit]]); 5090 UD-Q6_K bez MTP 62,49 t/s przy 262 144; Inkling IQ3_S bez draftera 75,6 t/s przy 16k ([[2026-11-27-nvq5]]).

## Kolejność optymalizacji
1. **MTP upstream n3, pin b11856:** 5090 62,49 → 102,19 (+63,5%); pin vs b12110 ABBA 99,8 vs 91,7; n4 −10% vs n3 ([[REKORDY]]:194).
2. **Fit:** `--spec-draft-n-ubatch 64`, ub 1024 na 32 GB, ub 256 na 16 GB, ub 128 dla Inklinga + DSpark (216 064 → 262 144 wobec ub 512).
3. **Lean:** 5080 58,81 → 81,62 t/s (+38,8%) przy 217 088.
4. **Fork + `kvq` + lean, słownik 64k:** 5090 100,90 → 148,57 (+47,4%, ten sam host). `kvq` sam: czat ±2%, kopia +12,2% ([[KOLEJKA-TESTOW]]:252).
5. **Długość draftu:** n2 (5060 Ti T=1 49,4 → 51,0, +3,2%), profil kopii n3 (+14,6%).
6. **DSpark dla Inklinga:** n2 64,2 vs bez draftera 51,4 t/s (+25%); n3 58,4, n4 52,9 ([[2026-11-27-k204-enigma-16gb-inkling]]).
7. **`--ablate-lora` (K-207) zamiast `--lora`:** +15,5% / +27,5%, odmowy 0/5, KL 0,00865 (podłoga 0,00859); wymaga naszego builda.
8. **Sampler (`LLAMA_SAMPLER_FAST_TOPK`/`_PENALTIES`):** LFM 165,5 → 207,7 t/s ([[latki-na-nvidia]]).
9. **Przełączniki:** na sm_120 off `GGML_HIP_Q8_IDS`, `GATE_UP_Q8`, `MMVQ_N1_ROWS` (−1,7…−2,7%); FP4 tensor tylko w prefillu ([[sm-86-89-120]]).
- Odrzucone: DSpine-b16 (pl −50%, K-197), `p-min` > 0, graf pętli draftu (K-116).

## Testy
- `hostguard.sh` → `runk204.sh` → `k204.py <karta>`; ramiona ablacji `~/qwen-opt/cloud/nvq3/k207.py`.
- `qwen-opt/nib/wall.py` (kod, tech, pl, json × T=0 / 0,7), `spec_sweep.py` + `copy_prompts.json` (`mvs`), `qwen-opt/cloud/ink1/xbench.py`.
- `qwen-opt/long_ctx_bench.py --depths`, igła `qwen-opt/cloud/needle.py` / `~/k134/k202srv.py` przy 95%.
- `md5cmp.py`, `qwen-opt/tools/kld_gate.py compare` (Inkling: zawsze z ramieniem podłogi), `qwen-opt/nib/refusal.py`.

## Kiedy topka jest gotowa
Pełny stos na hoście po obu bramkach; największy `-c` przechodzi igłę 5/5 przy 95% + 700 tok. odpowiedzi; md5 / `kld_gate` PASS, odmowy 0/5 dla wersji bez cenzury; wall, szczyt VRAM, CPU i W zapisane; wiersz w [[TOPKI]]. Brakuje: 5070 (brak pomiaru), Inkling na 5080 (brak pomiaru), `--ablate-lora` przy pełnym 262 144 z igłą.

## Pułapki
- 16 GB: ładuje się z 0,5–0,66 GiB wolnego i pada przy pierwszym długim prefillu; liczy się fill.
- `-ctkd/-ctvd q4_0` dla DSpark: 18,7 vs 17,3 MiB/1k, pada przy 270k na pierwszym zapytaniu; `p_min` ≥ 0,1 wyłącza DSpark; LoRA −17–33%.
- PDL: kernele bez `cudaGridDependencySynchronize()` ścigają się na sm_120; obejście `GGML_CUDA_PDL=0`.
- 5090 na hoście 450 W zamiast 575 W wyglądało jak gorszy silnik ([[lekcja-limit-mocy-hosta]]); reaper zabił pracującą instancję po jednym „offline”.

## Rodzaje modeli
- **Dense 27B GDN (Qwen3.8):** MTP → fit → lean → fork/kvq → n2; 32 GB UD-Q6_K, 16 GB GSQ IQ3_XXS.
- **MoE A2B/A3B:** całość w VRAM, potem MTP: 5090 Qwen3.6-35B-A3B 244,6 → 319,5 t/s (+30,6%); 5080 z 12 warstwami ekspertów w RAM tylko +12%; LFM 5060 Ti 139,48 t/s przy 131 072.
- **Ternarny (Bonsai):** prism PTQ1_0 + MTP na 12 GB (5070: brak pomiaru).
- **Inkling (pętlowe MoE):** na 16 GB to dziś domyślny model: IQ3_S + DSpark n2 + ablacja, ub 128; GDN-owe łatki forka go nie dotyczą.

## Powiązane
- [[TOPKI]]
- [[final-recipes-nvidia]]
- [[2026-11-28-k207-ablacja-zamiast-lora]]
- [[rtx-5060-ti]]
- [[inkling-2-mini]]
