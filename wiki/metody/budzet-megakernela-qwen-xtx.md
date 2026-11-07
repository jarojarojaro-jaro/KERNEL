---
typ: metoda
tags: [metody, megakernel, xtx, szacunki]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:89-127,151-161
status: do-sprawdzenia
---
# Budżet megakernela dla Qwen3.8-27B na XTX

**Pula, którą megakernel mógłby odzyskać z kroku MTP ~27.6 ms, to sufit ~4 ms (+12%, poziom Hazy 78% pasma), realnie 1.1–2.4 ms, czyli +4…9.5% (środek +5–6%) przy krótkim kontekście i +2…4% przy 199k, za 40–70 osobodni (raport 66c, 2026-11-07, `[SZACUNEK]`).**

| składnik | sufit | realnie na RDNA3 |
|---|---|---|
| luki hosta (rezydentna pętla MTP) | 0.41 ms | 0.3–0.4 ms (= plan #11) |
| ogony/rampy w łańcuchach MMVQ → norma → MMVQ | 2.17 ms | 0.5–1.0 ms |
| małe operacje nałożone na strumień wag (~2.8 ms pracy) | ~1.5 ms | 0.3–1.0 ms |
| sprawność MMVQ (738–787 → ~900 GB/s) | 1.0–1.5 ms | 0 (to strojenie kerneli) |

- Krok: 946 dispatchy (~320 na token). Same pakiety granic PM4 to 0.43–0.81 ms; zwykły graf HIP dałby ~2.6 ms.
- Pomiar x54 potwierdza, że granice poza łańcuchami MMVQ nic nie kosztują: −126 dispatchy = +0.24% (szum).
- Sesja agenta: decode to ~32% zegara, więc +5% decode ≈ −1.5% zegara.
- Ryzyka: zawieszenia (NVIDIA mega: 2 w 12.5 h), ewikcja kolejki KFD przy kernelu rezydentnym, TDR na Windows (Enigma).
- Krok decyzyjny: PoC-A, hand-off w trwałej siatce 96–192 WG (1–1.5 d); kill przy > 0.3 µs albo < 30% zysku „bez granicy”.

## Powiązane
- [[metody/_hub|metody]]
- [[2026-10-16-budzet-lfm-megakernel]]
- [[lekcja-megakernel-prefetch-nie-granica]]
- [[lekcja-handoff-rdna3]]
- [[pm4-replay]]
- [[hyperkernel]]
- [[raport-66-synteza]]
