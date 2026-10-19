---
typ: lekcja
tags: [lekcje, determinizm, kld]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:66-73,183-196
status: aktualne
---
# Bit-exact wobec siebie ≠ wierność modelowi

**inferrous zachowuje w każdej rundzie optymalizacji hashe wszystkich logitów wobec własnego pierwszego buildu, a niezależna bramka z PyTorch nie przechodzi (rel. L2 logitów 9–11%); Maya obiecuje „te same odpowiedzi” tylko przy przypiętym stanie warstw (domyślnie 17/70 restartów) (raport 21g, 2026-10-19).**

Reguła: md5/hash wobec własnej bazy łapie tylko regresje, nie błąd wierności – zawsze w parze z KLD wobec upstreamu albo referencji (BF16/f16 KV) i kanarkami ([[bramka-kld-kanarki]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[zgodnosc-bitowa-md5]]
- [[lekcja-md5-wzgledem-upstreamu]]
- [[inferrous]]
