---
typ: research
tags: [research, fa, kv, weryfikacja]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24h-kv-jeden-przebieg.md:3,9-14,20-28
status: aktualne
---
# Raport 24h: jeden przebieg KV w `fattn-kvq` dla weryfikacji MTP – nie teraz

**Sufit jednego odczytu KV dla MTP n=4 (W=5) to +3.0…6.6% e2e przy 94k i ≤ 2.3% przy 32k – cel +8% nieosiągalny; sens tylko dla szerokiej weryfikacji lookup (W ≥ 11) (2026-10-19).**

- Mikrobench d98304: n 1/2/3/5/6/8/11/16 = 161/165/293/297/425/428/773/831 µs; koszt ~130 µs na kafel 16 wierszy (`ceil(6·W/16)`) + ~33 µs stałego, prawie szczyt pasma (`24h:11-13`).
- Każdy kafel to osobny pełny odczyt KV (`24h:13-14`).
- Kill dla „+8% MTP @94–113k”; ewentualny następca tylko dla W ≥ 6 po pomiarze udziału kroków lookup (`24h:27-28`).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[koszt-szerokosci-weryfikacji]]
- [[raport-24k-koszt-weryfikacji]]
- [[raport-21m-declarative-attention]]
