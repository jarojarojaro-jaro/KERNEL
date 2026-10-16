---
typ: lekcja
tags: [lekcje, kld, kwanty, pomiar]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:38,85,221-226
status: aktualne
---
# KLD z różnych protokołów nie wolno mieszać

**Ten sam plik ISTA GSQ-RCO IQ3_S ma KLD 0.0519 przy ctx 512 i 0.0665 przy ctx 2048 (+28%), a Swift mierzy KLD do własnego BF16 zamiast do Qwena – liczby z różnych kontekstów, referencji i korpusów nie są porównywalne.**

Protokoły w raporcie 15e: [A] agentionai (wiki, ctx 2048, 60 chunków, ref Qwen BF16), [S] ISTA/Swift (wiki, ctx 512, 100 chunków, ref = własny BF16), [W] wiklif (ctx 4096, kod/proza), [N] nasz (KLD vs Q8_0 albo PPL 64×512).
Reguła: porównywać tylko KLD z tego samego protokołu (ctx, liczba chunków, korpus, referencja, build); przy cudzej tabeli najpierw sprawdzić `report.json` „reference”; w naszych pomiarach zapisywać protokół obok liczby.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-sondy-en-na-polskim]]
- [[bramka-kld-kanarki]]
- [[kwanty-gguf]]
- [[raport-15e-kwantyzacja-nowa]]
