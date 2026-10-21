---
typ: research
tags: [research, bezpieczenstwo, tokenizacja]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/39c-deepseek-v41-deployment.md:14-30
status: aktualne
---
# Raport 39c: DeepSeek V4.1 Flash – praktyka wdrożenia

**Parser wyjścia topki działał na tekście: znacznik `<tool_call>` złożony ze zwykłych tokenów dawał prawdziwe wywołanie narzędzia (potwierdzone na CPU) → `LLAMA_SERVER_SAFE_TOOLS` (raport 42); tokenizacja segmentowa 91k 64.8 → 9.6 ms, 148/148 promptów bitowo zgodnych.**

- Dosłowne `</think>` ucinało `reasoning_content` (Qwen3.8 i LFM2.5).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[bezpieczenstwo-tokenow-specjalnych]]
- [[raport-42-safe-io]]
