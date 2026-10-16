---
typ: firma
tags: [ludzie-firmy, kwanty, nauka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:332-336,416
status: aktualne
---
# ISTA-DASLab

**Grupa z Institute of Science and Technology Austria, autorzy GSQ-RCO: PTQ, która dopracowuje publiczne GGUF K-quanty w tym samym formacie.**

GSQ: inicjalizacja GPTQ, potem Gumbel-Softmax po przypisaniach do siatki i skalach, warstwa po warstwie, optymalizator Lion; format zostaje GGUF K-quant. Przykład: Qwen3-8B Q2_K 50.03 → 56.28. RCO przydziela typ kwantu per tensor pod budżet rozmiaru. Narzędzie testowano na H100. Na tym zbudowano Saluki; Strata też używa GSQ-RCO.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[conway-research]]
- [[unsloth]]
- [[saluki]]
- [[kwanty-gguf]]
