---
typ: firma
tags: [ludzie-firmy, kwanty, nauka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:332-336,416; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:82,99-128,237
status: aktualne
---
# ISTA-DASLab

**Grupa z Institute of Science and Technology Austria, autorzy GSQ-RCO: PTQ, która dopracowuje publiczne GGUF K-quanty w tym samym formacie.**

GSQ: inicjalizacja GPTQ, potem Gumbel-Softmax po przypisaniach do siatki i skalach, warstwa po warstwie, optymalizator Lion; format zostaje GGUF K-quant. Przykład: Qwen3-8B Q2_K 50.03 → 56.28. RCO przydziela typ kwantu per tensor pod budżet rozmiaru. Narzędzie testowano na H100. Na tym zbudowano Saluki; Strata też używa GSQ-RCO.

Uzupełnienie (raport 15e): kod refinementu typów IQ nie jest na `main` – na gałęzi z GSVQ dla IQ-quantów MSE wag spadł o 2.6–2.7%, a KL end-to-end wzrósł o 1.9–4.2%; produkcyjna ścieżka dla Qwen3.8-27B GSQ-RCO jest nieopublikowana. RCO: softmax po typach kwantu, rzut gradientu na ograniczenie budżetu i DP plecakowe (`round_with_budget_dp`), wynik jako plik alokacji. Przy ~3.5 bpw KLD gorszy niż UD: IQ3_S 0.0519 (ctx 512) / 0.0665 (ctx 2048) vs UD-IQ3_S 0.0470. Wykres MTP ISTA (akceptacja 54.2%, ~100–118 t/s) bez ujawnionego GPU.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[conway-research]]
- [[unsloth]]
- [[saluki]]
- [[kwanty-gguf]]
- [[raport-15e-kwantyzacja-nowa]]
- [[swift-1-5]]
