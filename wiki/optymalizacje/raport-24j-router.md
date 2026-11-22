---
typ: optymalizacja
tags: [optymalizacje, spekulacja, lookup, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24j-router-edycja.md:3-14
status: aktualne
technika: router ogon lookupu / DFlash2 / MTP
werdykt: odrzucone
zysk: sufit wyroczni +1,1% (T=0) / +2,0% (T=1), próg +8%
dowod: raport-24j-router
wyniki:
  - qwen3-8-27b | rtx-3090 | 64 ms | krok DFlash2 | 2026-10-19
  - qwen3-8-27b | rtx-3090 | 46.5 ms | krok MTP | 2026-10-19
---
# Raport 24j: router ogon lookupu / DFlash2 / MTP na code-edit – kill bez GPU

**Sufit wyroczni routera na `mvs` to +1.1% (T=0) / +2.0% (T=1), daleko pod progiem +8%: ogon W16 daje już 14.5 z 16 możliwych tok/krok, a kroki bez ogona MTP przyjmuje zwykle 4/4 (2026-10-19).**

- T=0: 283 kroki, 14.46 tok/krok, 15 kroków (5.3%) bez trafienia ogona (`24j:7`).
- Na 3090 krok DFlash2 kosztuje 64 vs 46.5 ms MTP i +1.14 GB VRAM (`24j:10`).
- Router `LLAMA_SPEC_ROUTER` nie powstaje; przewagi szukać w koszcie kroku W16 (`24j:14`) → [[raport-24k-koszt-weryfikacji]]. Drafter: [[drafter-dflash]].

## Powiązane
- [[raporty-2026-10-19-20]]
- [[drafter-dflash]]
- [[raport-24k-koszt-weryfikacji]]
- [[testy/2026-10-18-lookup-ogon]]
