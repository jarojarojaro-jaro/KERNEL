---
typ: eksperyment
tags: [eksperymenty, nvidia, rtx-5060-ti, enigma, mtp, upstream, kolejka]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/qwen-opt/cloud/k103/{run.sh,summ.py,collect.sh,res/*}; Vast instancja 60693822 (RTX 5060 Ti 16 GB, Tajwan, limit mocy 150 W z 180 W fabrycznych), 2026-11-14 20:36–21:20 UTC
status: aktualne
---
# 2026-11-14: K-103 — llama.cpp v1.0.0 vs pin Enigmy b11856 na RTX 5060 Ti (Qwen3.8-27B ISTA IQ3_XXS-mtp, MTP n2)

**v1.0.0 nie ma regresji MTP, którą miał b12110 (−9% na sm_120). W ABBA spec_sweep T=1 jest +3,5%: 43,95 → 45,6 t/s (mediana z dwóch par ramion). Few-row MMQ #31533 przyspiesza przebieg weryfikacji o +12,1% przy 8 kolumnach i +9,8% przy 16, ale przy 4 tylko +2,8%. Przy MTP n2, czyli 3 kolumnach, krok się nie skraca: 45,95 → 46,2 ms. Zysk w czacie pochodzi z wyższej akceptacji na pl-kod (2,01 → 2,52 tok/krok), a nie z kernela.**

| pomiar (5060 Ti, 150 W, KV q4_0, ub 256, ctx 65 536) | b11856 | v1.0.0 | zmiana |
|---|---|---|---|
| spec_sweep T=1 mediana, MTP n2 (A1/A2 vs B1/B2) | 44,21 / 43,68 | 45,74 / 45,51 | **+3,5%** |
| ms na krok | 45,65 / 46,25 | 46,07 / 46,36 | +0,6% |
| akceptacja | 0,515 | 0,559 | +8,5% |
| pl-kod | 44,1 / 43,5 | 54,5 / 54,2 | +24% |
| en-code | 44,3 / 43,8 | 41,2 / 40,8 | −7% |
| pp576, ub 4 | 96,05 t/s | 98,77 | +2,8% |
| pp576, ub 8 | 136,33 | 152,88 | **+12,1%** |
| pp576, ub 16 | 278,98 | 306,41 | **+9,8%** |
| VRAM po załadowaniu / szczyt | 13 281 / 13 509 MiB | 13 329 / 13 557 | +48 MiB |

**Wnioski i rekomendacja dla Enigmy:**
- Pin b11856 można podnieść do v1.0.0 na 16 GB: działa szybciej, a regresja z b12110 zniknęła. Przed zmianą trzeba jeszcze sprawdzić 24/32 GB z MTP n3 (tam pin wygrywał z b12110) i nasz silnik lean.
- Pełny zysk #31533 (+10…12% na przebieg) pojawi się dopiero przy szerszej weryfikacji: MTP n ≥ 4, lookup W16 albo fork. To następny test, kartą 3090/4090 albo 5060 Ti w jaroserverai.
- Zastrzeżenia: limit mocy karty z wynajmu 150 W (fabrycznie 180 W) jest ten sam w obu ramionach; jeden seed × 6 promptów; tok/krok pl-kod różni się między wersjami, czyli zmieniła się polityka draftu, nie tylko kernel.
- **Koszt Vast:** ~0,10 USD (kredyt 0,65 → 0,55), instancja zniszczona o 21:20 UTC, 0 instancji. Pierwsza próba zostawiła instancję pustą na ~15 min, bo podagenci skończyli razem z turą.

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[final-recipes-nvidia]]
- [[telegram-2026-11-14-pearlquant-llamacpp-v1]]
- [[2026-11-07-kampania-nvidia-vast]]
- [[rtx-5060-ti]]
