---
typ: test
tags: [testy, nvidia, rtx-5060-ti, enigma, mtp, upstream, kolejka]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/qwen-opt/cloud/k103/{run.sh,run2.sh,summ.py,collect.sh,collect2.sh,res/*,res2/*}; Vast instancja 60693822 (RTX 5060 Ti 16 GB, Tajwan, limit mocy 150 W z 180 W fabrycznych), 2026-11-14 20:36–21:20 UTC
status: aktualne
model: qwen3-8-27b
karta: rtx-5060-ti
wyniki:
  - qwen3-8-27b | rtx-5060-ti | 45,62 t/s | spec_sweep T=1 MTP n2; ISTA IQ3_XXS-mtp, v1.0.0, 150 W | 2026-11-14
  - qwen3-8-27b | rtx-5060-ti | 43,95 t/s | spec_sweep T=1 MTP n2; ISTA IQ3_XXS-mtp, b11856, 150 W | 2026-11-14
  - qwen3-8-27b | rtx-5060-ti | 40,32 t/s | spec_sweep T=1 MTP n3; b12359, 160 W | 2026-11-14
  - qwen3-8-27b | rtx-5060-ti | 306,41 t/s | pp576 ub 16; v1.0.0 (b11856 278,98) | 2026-11-14
k: K-103
---
# 2026-11-14: K-103 — llama.cpp v1.0.0 vs pin Enigmy b11856 na RTX 5060 Ti (Qwen3.8-27B ISTA IQ3_XXS-mtp, MTP n2)

**v1.0.0 nie ma regresji MTP, którą miał b12110 (−9% na sm_120). W ABBA spec_sweep T=1 jest +3,8%: 43,95 → 45,62 t/s (mediana z dwóch par ramion; parami A1→B1 +3,5%, A2→B2 +4,2%). Few-row MMQ #31533 przyspiesza przebieg weryfikacji o +12,1% przy 8 kolumnach i +9,8% przy 16, ale przy 4 tylko +2,8%. Przy MTP n2, czyli 3 kolumnach, krok się nie skraca: 45,95 → 46,2 ms. Zysk w czacie pochodzi z wyższej akceptacji na pl-kod (2,01 → 2,52 tok/krok), a nie z kernela.**

| pomiar (5060 Ti, 150 W, KV q4_0, ub 256, ctx 65 536) | b11856 | v1.0.0 | zmiana |
|---|---|---|---|
| spec_sweep T=1 mediana, MTP n2 (A1/A2 vs B1/B2) | 44,21 / 43,68 | 45,74 / 45,51 | **+3,8%** (mediany 43,95 → 45,62; parami +3,5 / +4,2%) |
| ms na krok | 45,65 / 46,25 | 46,07 / 46,36 | +0,6% |
| akceptacja | 0,515 | 0,559 | +8,5% |
| pl-kod | 44,1 / 43,5 | 54,5 / 54,2 | +24% |
| en-code | 44,3 / 43,8 | 41,2 / 40,8 | −7% |
| pp576, ub 4 | 96,05 t/s | 98,77 | +2,8% |
| pp576, ub 8 | 136,33 | 152,88 | **+12,1%** |
| pp576, ub 16 | 278,98 | 306,41 | **+9,8%** |
| VRAM po załadowaniu / szczyt | 13 281 / 13 509 MiB | 13 329 / 13 557 | +48 MiB |

**Wnioski (pierwsza instancja):**
- Regresja z b12110 zniknęła, a przy n2 jest +3,8%. Bramka niżej rozstrzyga jednak, że pin zostaje.
- Pełny zysk #31533 (+10…12% na przebieg) pojawi się dopiero przy szerszej weryfikacji: MTP n ≥ 4, lookup W16 albo fork. To następny test, kartą 3090/4090 albo 5060 Ti w jaroserverai.
- Zastrzeżenia: limit mocy karty z wynajmu 150 W (fabrycznie 180 W) jest ten sam w obu ramionach; jeden seed × 6 promptów; tok/krok pl-kod różni się między wersjami, czyli zmieniła się polityka draftu, nie tylko kernel.
- **Koszt Vast:** ~0,10 USD (kredyt 0,65 → 0,55), instancja zniszczona o 21:20 UTC, 0 instancji. Pierwsza próba zostawiła instancję pustą na ~15 min, bo podagenci skończyli razem z turą.

## Bramka przed zmianą pinu (2026-11-14 21:33–21:45 UTC, druga instancja 60698445, 5060 Ti 160 W)

Oficjalne binarki z wydań (to, co pobiera Enigma): b11856 vs b12359 (= v1.0.0). Model ten sam, KV q4_0.

| pomiar | b11856 | b12359 (v1.0.0) | werdykt |
|---|---|---|---|
| KLD vs logity b11856 ub 512 (wikitext-2, 20 × 512) | ub 256: 0,000569; ub 8: 0,000615 (szum podziału batcha) | ub 512: **0,000700 ± 0,000026**; ub 8: 0,000693 | ~2σ **ponad** szumem; KLD ≠ 0, md5 ≠ |
| ta sama najlepsza pozycja | 98,88 / 98,67% | 98,53 / 98,63% | – |
| spec_sweep T=1, MTP n3 (przepis 24/32 GB), A B B A | 39,92 / 39,96 t/s | 40,02 / 40,32 | **+0,6%**, poniżej progu |
| ms na krok | 56,06 / 56,01 | 55,55 / 55,38 | −1,0% |

**Decyzja: pinu Enigmy nie zmieniamy (zostaje b11856).** Cztery powody:
1. v1.0.0 nie jest bezstratny względem pinu. KLD przekracza szum samego upstreamu, czyli nie spełnia reguły „md5 albo KLD = 0”, nawet w luźnej wersji z kampanii 67 („w szumie upstreamu”).
2. Zysk przy MTP n3 (24/32 GB) to tylko +0,6%. Przy n2 (16 GB) +3,8%, ale prawie w całości z pl-kod: zmieniła się polityka draftu, nie kernel.
3. VRAM +48 MiB przy załadowaniu. Plan 4090 upstream 262 144 z MTP n3 miał szczyt 24 036 z 24 082 MiB (46 MiB zapasu), więc na Windows grozi OOM bez nowego pomiaru wypełnienia.
4. Pin jest wspólny dla CPU, Vulkan, ROCm i macOS. Tych backendów nie mierzyliśmy.

Koszt obu instancji: 0,65 → 0,50 USD (~0,15 USD), 0 instancji. Kontynuacja w K-105 w [[KOLEJKA-TESTOW]].

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[final-recipes-nvidia]]
- [[telegram-2026-11-14-pearlquant-llamacpp-v1]]
- [[2026-11-07-kampania-nvidia-vast]]
- [[rtx-5060-ti]]
