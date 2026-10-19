---
typ: lekcja
tags: [lekcje, architektura, pasmo]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21c-copy-paste-lm.md:27-60; ~/KERNEL/product/research/15a-monokernel.md:121,154
status: aktualne
---
# „LM head bottleneck” w pracach treningowych ≠ koszt LM head w dekodowaniu

**W pracach treningowych (np. CPLM) „LM head bottleneck” znaczy utratę gradientu przy rzutowaniu V logitów do D wymiarów (> 99% normy przy V ≫ D) i niski rząd softmaksu – nie koszt czytania LM head przy dekodowaniu, którego te metody nie zmniejszają (CPLM dokłada 1–4%) (raport 21c, 2026-10-19).**

Nasz koszt LM head przy dekodowaniu: Qwen3.8-27B `output.weight` Q6_K 1042.94 MB = 6.2% z 16.83 GB/krok (~4% czasu kroku MTP4); LFM2.5 tied head Q6_K 215 MB = 12.1% z 1.777 GB/token. Ten koszt skraca u nas słownik draftu 64k (178 MB w IQ4_XS na przebieg draftu), ortogonalny do CPLM.

Reguła: przy hasłach „bottleneck” w pracy sprawdzić, czy chodzi o trening, czy o bajty na krok dekodowania, zanim oceni się przydatność dla silnika.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-bledny-roofline]]
- [[raport-21c-cplm]]
- [[latki-spekulacji]]
