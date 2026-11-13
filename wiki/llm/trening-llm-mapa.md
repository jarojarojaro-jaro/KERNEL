---
typ: llm
tags: [llm, trening, fine-tuning, lora, mtp, jakosc]
aktualizacja: 2026-11-13
zrodlo: wiki/eksperymenty/2026-10-12-mtp-trening-faza1.md; wiki/eksperymenty/2026-10-16-mtp-pl-pilot.md; wiki/research/raport-10-post-training.md; wiki/research/raport-11-mtp-pl-pilot.md; wiki/modele/astra-stop.md; wiki/modele/uncensored-ablacja-kierunku.md; ~/KERNEL/product/research/62-weight-space-programming.md; ~/KERNEL/qwen-opt/research/training.md; ~/KERNEL/qwen-opt/research/tensorfold/qwen27.md:399; wiki/metody/jakosc-mini.md; wiki/metody/evalplus-jakosc-kodu.md
status: aktualne
---
# Mapa: co już trenowaliśmy i dostrajaliśmy

**Do 2026-11-13 trenowaliśmy tylko draftery (głowica MTP, DFlash2), żaden nie dał zysku. Model zmienialiśmy wyłącznie edycjami wag bez treningu (Uncensored, Astra-Stop). Jakość mierzą EvalPlus i jakość-mini: Qwen3.8-27B-Uncensored HE+ 92,7%, jakość-mini 87,9%.**

| Temat | Wynik | Notatki |
|---|---|---|
| Douczanie głowicy MTP Qwen3.8-27B (self-distillation na trunku Q4, PL) | negatywny: 1,7 M tok., A40 3,5 h, $2,14 → ±0,2% tok/krok offline (szacunek był +10–17%); głowica jest na optimum | [[2026-10-12-mtp-trening-faza1]], [[2026-10-16-mtp-pl-pilot]], [[raport-10-post-training]], [[raport-11-mtp-pl-pilot]], [[lekcja-mtp-glowica-optimum]], [[mtp-train]], [[glowica-mtp]] |
| Fine-tune DFlash2 (372k tokenów celu) | bez zysku (TensorFold) | [[drafter-dflash]], [[tensorfold]], `qwen-opt/research/training.md` |
| Narzędzia do treningu drafterów | speculators (nasza ścieżka dla MTP), SpecForge (trening DSpine) | [[speculators-specforge]], [[drafter-dspine]] |
| Uncensored = edycja wag bez treningu | Qwen: jeden globalny kierunek odmowy rzutowany ze strumienia; LFM: kierunek per warstwa | [[uncensored-ablacja-kierunku]], [[single-neuron-safety-2605-08513]] |
| Astra-Stop: LoRA rank-1 skracająca myślenie | myślenie −35,5%, ale przeciek `</think>` 11/32; odłożone jako temat przyszłych fine-tuningów | [[astra-stop]], [[2026-11-09-decyzje-runda-69]] |
| Weight-space programming / Neuron Tuning (raport 62) | to fine-tuning Adamem kilku kolumn `down_proj`, nie „bez gradientów” | `product/research/62-weight-space-programming.md` |
| Kwantyzacja z treningiem (DCQ, Bonsai, Swift) | zmiana kwantu, poza produkcją | [[dcq-kotwica-stanu-gdn]], [[bonsai]], [[swift-1-5]] |
| Inne modele po post-trainingu (RSR-27B, Star Elastic) | RSR-27B: plan porównania czeka na zgodę ($40–70) | [[2026-10-19-plan-e1-rsr27b]], [[tencent-terminal-rsi]], [[star-elastic-2605-07182]] |
| Jakość (bramka każdego treningu) | EvalPlus HE+ 92,7 / MBPP+ 80,2; jakość-mini 255/290 | [[evalplus-jakosc-kodu]], [[jakosc-mini]], [[2026-11-09-evalplus-qwen-uncensored]], [[2026-11-09-jakosc-mini-qwen-unc]] |

Otwarte tematy na przyszłość: Astra-Stop jako fine-tune z benchmarkiem, polski fine-tune DSpine, porównanie RSR-27B. Pozycje testowe są w [[KOLEJKA-TESTOW]] (K-074, K-076, K-077, K-098). Starsze notatki zostają w swoich folderach; nowe notatki o treningu trafiają tutaj, do `llm/`.

## Powiązane
- [[llm/_hub|llm]]
- [[glowica-mtp]]
- [[astra-stop]]
- [[raport-10-post-training]]
- [[jakosc-mini]]
