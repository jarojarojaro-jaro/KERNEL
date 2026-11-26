---
typ: test
tags: [testy, edycja-wag, nib, inkling, nvfp4, ablacja, xtx]
aktualizacja: 2026-11-26
zrodlo: ~/qwen-opt/we2/out/we2.txt (jaroserverai); narzędzie ~/wt/nib-we2/tests/lora_merge.cpp, Nib `--weights-patch` (gałąź nib-we2 32fe977); sidecary ~/models/nib/we2/unc-{proj,nearest}.patch.gguf
status: aktualne
---
# 2026-11-26 WE2: odmowy wycięte na stałe w wagach Niba zamiast LoRA w locie

**Scalenie LoRA AtomicChat (to dokładnie W' = (I − r rᵀ)W z jednym wspólnym kierunkiem r) w wagi NVFP4/Q8_0 Niba daje to samo zachowanie (odmowy 0/5, jak LoRA w locie; baza z cenzurą 5/5) przy +5,2% (T=0) i +5,7% (T=0,7) prędkości wobec LoRA w locie. Oba warianty requantyzacji (proj i nearest) zdjęły odmowy; proj zachowuje edycję wzdłuż r w 99,5%, nearest gubi ok. 75% na tensorach NVFP4, ale na 5 promptach to nie wyszło.**

| ramię | odmowy | wall T=0 mediana | wall T=0,7 mediana | pl T=0 / T=0,7 |
|---|---|---|---|---|
| Nib bez LoRA (z cenzurą) | 5/5 | 102,9 | 101,2 | – |
| Nib + LoRA w locie (K-165) | 0/5 | 157,0 | 147,3 | – |
| **Nib, wagi scalone (proj)** | **0/5** | **165,2 (+5,2%)** | **155,7 (+5,7%)** | 86,5 / 79,0 |
| Nib, wagi scalone (nearest) | 0/5 | 166,3 (+5,9%) | 159,1 (+8,0%) | 84,5 / 76,4 |

- Bazowe ramię bez LoRA jest wolniejsze, bo odmowy mają inną długość i treść (krótkie odpowiedzi szablonowe) — porównujemy wersje bez cenzury między sobą.
- PPL nie zapisało się (pusty wynik `nib ppl`); HumanEval+ wygenerowany (164 próbki na ramię), ocena na CPU do zrobienia (`jakosc-mini.sh --tag qe-we2-<ramię>`).
- Sidecar 5,94 GB zamiast kopii 17,6 GB. Polski dalej wolniejszy niż Maya (86,5 vs ok. 113), więc Nib nie zastępuje Mai; to dowód, że edycja kierunku daje się wpiec bez kosztu prędkości.

## Powiązane
- [[nib-chromadera]]
- [[edycja-wag-backlog-2026-11-26]]
- [[uncensored-ablacja-kierunku]]
