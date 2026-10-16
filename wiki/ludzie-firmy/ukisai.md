---
typ: firma
tags: [ludzie-firmy, modele, licencje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:130-150,547
status: aktualne
---
# UkisAI (autor Swift)

**Autor Swift 1.0/1.5 – fine-tune’ów Qwen3.8-27B na krótsze myślenie – z licencją Swift Open License v1.0, która dopuszcza użycie komercyjne tylko poniżej US$1M przychodu rocznie.**

- Swift 1.5: RL + OPD z karą za „pathological overthinking”, dane `ukisai/Qwen3.8-27B-multi-turn-agent-sft`.
- Kwanty GSQ-RCO budowane przepisem ISTA (alokacja `llama-quantize --tensor-type-file`) + własny imatrix V1MIX + nieopublikowany skrypt `refine_gguf_fast.py`.
- Jest też `ukisai/Swift-Bonsai-2-GGUF` (PTQ1_0 5.95 GB, Apache-2.0).
- Licencja: §5 „Commercial Use Limitation” (< US$1M brutto łącznie z podmiotami powiązanymi, powyżej „Swift Enterprise License”), §12 automatyczne wygaśnięcie.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[ista-daslab]]
- [[prismml]]
- [[swift-1-5]]
- [[raport-15e-kwantyzacja-nowa]]
