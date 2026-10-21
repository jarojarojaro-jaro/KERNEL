---
typ: research
tags: [research, bezpieczenstwo, topka]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/32e-safe-special-tokens.md:1-20
status: aktualne
---
# Raport 32e: wstrzykiwanie tokenów specjalnych, LLAMA_SERVER_SAFE_SPECIAL

**Topka tokenizowała cały prompt z `parse_special=true`, więc `<|im_end|>`, `<tool_call>` itp. w treści użytkownika lub wyniku narzędzia stawały się tokenami sterującymi; naprawa `LLAMA_SERVER_SAFE_SPECIAL=1` (commit `b659634fd`), w produkcji od f9b84bcfa.**

- Rozmowa bez znaczników w treści daje token w token to samo co przedtem.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[bezpieczenstwo-tokenow-specjalnych]]
- [[raport-43-integracja]]
