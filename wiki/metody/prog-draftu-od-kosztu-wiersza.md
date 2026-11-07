---
typ: metoda
tags: [metody, spekulacja, enigma, moe]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66a-strata-maya.md:355-365,389; Strata `strata_control/drafting.py:257-276,334-347` (klon 146df3c4)
status: do-sprawdzenia
---
# Próg draftu zależny od kosztu wiersza weryfikacji

**Strata zmierzyła, że optymalny próg pewności draftu rośnie z kosztem wiersza weryfikacji: przy 1383 slotach ekspertów na karcie najlepsze jest 0.8 (+9.3%), przy 15 766 slotach 0.35–0.5 (+4.9…5.6%), a 0.8 już −0.6%; na kartach 12 GB z MoE strumieniowanym z RAM MTP bije DFlash2 o 12–44% (raport 66a, 2026-11-07).**

| sloty ekspertów | 0.35 | 0.5 | 0.65 | 0.8 | 0.9 |
|---|---|---|---|---|---|
| 1 383 | −4.2% | +3.1% | +7.1% | **+9.3%** | +8.7% |
| 15 766 | +4.9% | **+5.6%** | +3.5% | −0.6% | −6.5% |

DFlash2 vs MTP przy równym VRAM, IQ3_S, czat 6 tur + 4 zimne prompty, 3 rundy. Reguła wdrożona: `CONF_STEPS = ((12000, 0.35), (7500, 0.5), (3000, 0.7), (0, 0.8))`, backend SYCL 0.6, Metal 0.5.

- Enigma dziś: jeden kandydat `--spec-type draft-mtp --spec-draft-n-max 4`, bez `p_min` (`optimize.ts:108-111`).
- Pomysł: siatka `--spec-draft-p-min` {0, 0.5, 0.8} × n {1,2,4} dla MoE z `--n-cpu-moe` i kart ≤ 16 GB; 0…+15% `[INFERENCE]`. Rozszerza plan #4 z 63.
- Test na XTX: Qwen3.6-35B-A3B z `--n-cpu-moe 20/30/40` emuluje klasę „streaming”. XTX z modelem rezydentnym: ~0.
- Bezstratne co do rozkładu; md5 greedy może się zmienić przez szerokość ([[lekcja-glebokosc-zmienia-tekst]]).

## Powiązane
- [[metody/_hub|metody]]
- [[koszt-szerokosci-weryfikacji]]
- [[glowica-mtp]]
- [[strata]]
- [[enigma-uczciwy-benchmark]]
- [[raport-66-synteza]]
