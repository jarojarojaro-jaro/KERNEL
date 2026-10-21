---
typ: research
tags: [research, konkurencja, deepseek]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/32b-deepinfer-deepseek-recipe.md:1-24
status: aktualne
---
# Raport 32b: DeepInfer i deepseek-recipe

**DeepInfer (`774ce24`) to serwer klastrowy tylko na sm_100 i Ascend 950 dla jednego modelu (DeepSeek-V4.1-Flash) – dla nas nic do uruchomienia; z recipe bierzemy tokenizację po zakresach specjalnych (→ 32e).**

- Batch-invariance to przepis Thinking Machines (stały split-K 16).
- DeepGEMM przypięty na `1fc9c66`, już w KB – brak delty.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[deepinfer]]
- [[bezpieczenstwo-tokenow-specjalnych]]
