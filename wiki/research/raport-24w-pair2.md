---
typ: research
tags: [research, mmvq, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24w-pair2.md:5-19,33-43; ~/KERNEL/product/research/24r-mmvq-pasmo.md:14
status: aktualne
---
# Raport 24w: PAIR2 (para MMVQ dla mieszanych typów) na topce – zbudowane, niezmierzone

**PAIR2 przeniesiony na topkę (`pair2-topka`, commity `7555f1d21`, `d7f1b7d37`, `5ac5a69b3`) i zbudowany przez `rbuild`, ale bez pomiaru – kolejkę anulowano, bo użytkownik zakazał testów na XTX tej nocy (2026-10-20).**

- Oczekiwany zysk −40 uruchomień/krok, szac. 0.3–0.5 ms/krok ([[raport-24r-mmvq-pasmo]]).
- Joby gotowe: `~/qwen-opt/queue/p2.jobs` (md5, potem ABBA sweep T=1, seedy 1–3, po 600 s) (`24w:19`). Adopcja tylko przy wyraźnie niższym ms/krok i `MD5 OK`.
- PAIR2 wymaga commitu RPB (parametr `rows`); runtime’owy switch RPB usunięty (`24w:42`).
- Pierwszy build świeżego `build-hip` na farmie trwał > 50 min – puszczać bez limitu czasu (`24w:43`).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24r-mmvq-pasmo]]
- [[raport-24n-mmvq-n5]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
