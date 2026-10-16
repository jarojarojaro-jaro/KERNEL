---
typ: eksperyment
tags: [eksperymenty, lfm, pm4, budzet]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:118-152; ~/KERNEL/product/research/15a-lfm-budget.py
status: aktualne
---
# 2026-10-16: budżet tokenu LFM pod megakernel (offline)

**Rachunek z nagłówka GGUF i taśmy PM4 (bez GPU): LFM2.5 Q5_K_M na XTX czyta 1.777 GB/token, a 3404 µs/token dzieli się na strumień 1953 µs, narzut matvec 698 µs, małe kernele 534 µs i host ~220 µs.**

| składnik | µs/token |
|---|---|
| wall (spec_sweep, 293.7 t/s) | 3404 |
| host | ~220 |
| taśma GPU (305 dispatchy) | 3184 |
| matvec (181 dispatchy, 1.758 GB, 663 GB/s z granicami) | 2650 |
| czysty strumień przy 900 GB/s | 1953 |
| narzut matvec ponad strumień | 698 |
| nie-matvec (124 dispatchy) | 534 |
| pula „DRAM prawie bezczynny” | 1231 (36%) |
| granice PM4 | 140–260 |

Bajty aktywne (`15a-gguf-active-bytes.py`): eksperci 4/64 1016.3 MB, shortconv 346.5, głowica 215.0, gęste FFN 105.9, atencja 72.7, router 19.8. Efektywne pasmo 522 GB/s = 54% z 960 GB/s. Scenariusze: S1 PM4-PDL 3.117 ms (+9%), S2 megakernel 3.035–2.665 ms (+12…+28%), podłoga 2.564 ms (+33%). Kontrola: 72% pasma (Lucebox) dałoby +22%, 78% (Hazy) +31%.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-15a-monokernel]]
- [[lfm-runda-4-pm4]]
- [[sufit-pasma-i-mapa-czasu]]
- [[lekcja-megakernel-prefetch-nie-granica]]
