---
typ: ekosystem
tags: [ekosystem, konkurencja, deepseek]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/32b-deepinfer-deepseek-recipe.md:1-24; ~/KERNEL/product/research/39c-deepseek-v41-deployment.md:1-12; ~/KERNEL/product/research/32b-deepinfer-deepseek-recipe.md:1-24
status: aktualne
---
# DeepInfer i deepseek-recipe (deepseek-ai)

**DeepInfer `774ce24` działa tylko na sm_100/Ascend 950 z DeepSeek-V4.1-Flash; deepseek-recipe `935817c` dało nam wzorzec tokenizacji po zakresach i parsera z rodzajem tokenu (SAFE_SPECIAL/SAFE_TOOLS).**



## Ze scalonej notatki: Raport 32b: DeepInfer i deepseek-recipe

DeepInfer (`774ce24`) to serwer klastrowy tylko na sm_100 i Ascend 950 dla jednego modelu (DeepSeek-V4.1-Flash) – dla nas nic do uruchomienia; z recipe bierzemy tokenizację po zakresach specjalnych (→ 32e).

- Batch-invariance to przepis Thinking Machines (stały split-K 16).
- DeepGEMM przypięty na `1fc9c66`, już w KB – brak delty.

## Powiązane
- [[ekosystem/deepinfer]]
- [[raport-39c-deepseek-deploy]]
- [[deepgemm]]
