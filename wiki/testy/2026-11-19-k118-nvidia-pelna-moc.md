---
typ: test
tags: [testy, nvidia, vast, mtp, sufit, enigma, k118, k116, k127]
aktualizacja: 2026-11-19
zrodlo: qwen-opt/cloud/k114/{run.sh,run2.sh,run3.sh,lp.py,summ.py,launch.sh,fetch.sh}; wyniki qwen-opt/cloud/k114/res/k118-{3090,3060,4080s}/ (bench.jsonl, up-vn.jsonl, up-tg.jsonl, long.jsonl, prefill.jsonl, smi.csv, gpu.csv, start_s.txt); `python3 summ.py res/k118-3090 res/k118-3060 res/k118-4080s`
status: aktualne
model: qwen3-8-27b
karta: rtx-3090
wyniki:
  - qwen3-8-27b | rtx-3090 | 89,5 t/s | dekod MTP n2 T=0; GSQ IQ3_XXS-mtp, kvqlean, 418 W | 2026-11-19
  - qwen3-8-27b | rtx-3090 | 1386 t/s | prefill ~11k; kvqlean | 2026-11-19
  - qwen3-8-27b | rtx-3060 | 34,0 t/s | dekod MTP n2 T=0; GSQ IQ3_XXS-mtp, kvqlean, 144 W | 2026-11-19
  - qwen3-8-27b | rtx-4080-super | 107,3 t/s | dekod MTP n4 T=0; GSQ IQ3_XXS-mtp, kvqlean, 278 W | 2026-11-19
  - qwen3-8-27b | rtx-4080-super | 1862 t/s | prefill ~11k; kvqlean | 2026-11-19
  - qwen3-8-27b | rtx-3090 | 71,8 t/s | dekod MTP n2 T=0 przy 95,6k; ctx 139 264 | 2026-11-19
k: K-118, K-116, K-127
---
# 2026-11-19 K-118 / K-116a / K-127: fork CUDA Enigmy na 3090, 3060 i 4080 SUPER z pełną mocą

**Na hostach z pełną mocą 3090 robi 86,6 t/s przy n4 T=0, dwa razy więcej niż dolna granica z K-114 (47,1, +84%). Krok spekulacji zjada weryfikacja, nie drafty: sprawdzenie 5 tokenów kosztuje 1,26–1,64 × pojedynczego przebiegu, a draft ≈ swoje bajty (0,5–0,9 ms). Wniosek K-114 „draft kosztuje 4–15 × bajty” był błędny, a K-116 (graf pętli draftu) odpada. Dźwignią na NVIDIA jest tańsza weryfikacja kilku wierszy (K-013), a od zaraz `DRAFT_N=2` na Ampere.**

Warunki:
- Vast, 19.11, budżet właściciela $2, wydane $1,11 (w tym ~$0,8 na bezczynne instancje, zob. lekcję niżej);
- model Qwen3.8-27B GSQ-RCO IQ3_XXS-mtp (10,44 GB), fork `kvqlean` z wydania `enigma-engines-cuda-2026-11-07`, flagi przepisu Enigmy jak w K-114;
- `bench.py` 6 promptów × T 0/1, 400 tok., zegar serwera;
- V(n): upstream `llama-bench` b12110 (`-p 1,2,3,5 -ub 5 -n 0 -r 5`, KV q4_0, FA);
- hosty sprawdzone `hostguard` przed pobraniem. Odrzucone: 3090 250/420 W, 5070 175/250 W. Host 5060 Ti odmówił SSH, druga 5060 Ti nie ruszyła.

| karta (moc pod obciążeniem) | plain t/s (% pasma) | n2 T=0 / T=1 | n4 T=0 / T=1 | prefill ~3,2k / ~11k t/s | K-114 dolna granica n4 T=0 |
|---|---|---|---|---|---|
| RTX 3090 (418 z 420 W, pamięć 9501 MHz) | 52,2 (58%) | **89,5 / 79,6** | 86,6 / 73,8 | 1349 / 1386 | 47,1 → **86,6 (+84%)** |
| RTX 3060 (144 z 160 W, 7301 MHz) | 20,8 (60%) | **34,0 / 31,8** | 33,0 / 30,5 | 479 / 484 | 30,9 → 33,0 (+7%) |
| RTX 4080 SUPER (278 z 280 W, 11 251 MHz) — nowa | 55,7 (78%) | 105,5 / **92,3** | **107,3** / 91,2 | 1554 / 1862 | – |

## K-116a: koszt weryfikacji V(n) i draftu

| karta | V(1) ms | V(2) | V(3) | V(5) | V(5)/V(1) | krok n4 − V(5) = 4 drafty | krok n2 − V(3) = 2 drafty | bajty 1 draftu (0,4 GB) |
|---|---|---|---|---|---|---|---|---|
| 3090 | 19,1 | 22,0 | 25,0 | 30,4 | **1,59** | 2,0 ms (0,5/draft) | 0,8 ms | 0,43 ms |
| 3060 | 50,1 | 56,5 | 65,2 | 82,3 | **1,64** | 3,6 ms (0,9/draft) | 0,7 ms | 1,1 ms |
| 4080 SUPER | 19,0 | 20,2 | 21,4 | 23,9 | **1,26** | 2,3 ms (0,6/draft) | 1,7 ms | 0,54 ms |

- **Draft kosztuje tyle, ile jego bajty.** K-114 przypisał draftom całą różnicę krok − V(1). Brakowało V(5), bo archiwum forka nie ma `llama-bench`. Audyt z 19.11 ostrzegał przed tym błędem, a ten pomiar go potwierdza. K-116 (graf CUDA na pętlę draftu) odpada: do odzyskania jest najwyżej 0,5–0,9 ms na draft.
- **Weryfikacja 5 tokenów na Ampere kosztuje 1,6 × pojedynczego przebiegu.** Przy kernelu ograniczonym pasmem powinno być ~1,0–1,1. Na Adzie (4080 SUPER) jest 1,26. To jest dźwignia K-013, kernel MMVQ/MMQ dla kilku wierszy. Na 3090 ~11 ms z 32 ms kroku [INFERENCE: zysk przy V(5)/V(1) = 1,15: krok 32,4 → ~24 ms, ~+35% dekodu n4].
- **`DRAFT_N=2` zamiast 4 na Ampere i 5060 Ti:** 3090 T=1 73,8 → 79,6 (+7,9%), T=0 +3,3%; 3060 T=1 +4,3%, T=0 +3,0%; 5060 Ti (K-114) T=1 49,4 → 51,0 (+3,2%). Na 4080 SUPER bez różnicy (−1,7 / +1,2%). Powód: droga weryfikacja; przy n4 akceptacja trzeciego i czwartego draftu nie spłaca kosztu V(5) − V(3). Zmiana przepisu Enigmy to K-129.

## K-127: kvqlean (AVX2) vs kvqleana (bez AVX2)

Ten sam host z AVX2, n4, ABBA (n4-a, n4-b, n4-c = AVX2, n4-noavx2 = bez):

| karta | AVX2 n4 T=0 / T=1 (mediana a/b/c) | bez AVX2 | start do /health (s) AVX2 → bez |
|---|---|---|---|
| 3090 | 86,3 / 73,4 | 86,6 / 73,7 | 11 → 10 |
| 3060 | 32,9 / 30,4 | 32,9 / 30,4 | 18 → 19 |
| 4080 SUPER | 105,4 / 91,2 | 106,9 / 91,3 | 22 → 26 |

Różnica mieści się w szumie (≤ 1,4%). **Zostaje `kvqleana` dla wszystkich.** Pobieracz nie musi wybierać wariantu po flagach CPU. K-127 zamknięte.

## Długi kontekst (ctx 139 264, prompt 95 569 tokenów, karty ≥ 16 GB)

| karta | prefill 95,6k t/s | dekod plain → MTP n2 (T=0, 256 tok.) | VRAM |
|---|---|---|---|
| 3090 | 925 | 30,2 → 71,8 (+138%) | 14,2 GB |
| 4080 SUPER | 1338 | 35,4 → 73,7 (+108%) | 14,2 GB |

- Prompt wyszedł 95,6k, a nie zakładane 122k: ~1,04 tokenu na słowo, a nie 1,33.
- Przy 96k spekulacja daje 2,1–2,4 × względem plain, więcej niż przy krótkim kontekście (1,7 ×). Przebieg celu jest wtedy droższy (atencja), a koszt draftu się nie zmienia.

## Lekcja z przebiegu

Procesy odpalone `setsid nohup` z sesji narzędzia agenta zginęły razem z nią: `fetch.sh`, lokalne watchdogi i jeden `launch.sh`. Instancje skończyły pracę o 18:31–18:40, a stały do 19:45, kiedy usunąłem je ręcznie. Strata to ~$0,8. Poprawka (wdrożona i przetestowana 19.11 wieczorem):
- timer systemowy `vast-reaper` co 2 min zbiera wyniki, usuwa instancję i zostawia raport w skrzynce Kernela;
- strażnik na samej instancji usuwa ją, gdy jest bezczynna;
- `launch.sh` bez działającego timera odmawia wynajmu.

Zob. [[lekcja-tlo-z-sesji-agenta-ginie]].

## Powiązane
- [[2026-11-17-k114-nvidia-sufit]]
- [[KOLEJKA-TESTOW]]
- [[lekcja-vast-tylko-pelna-moc]]
- [[skill-io-sufity]]
