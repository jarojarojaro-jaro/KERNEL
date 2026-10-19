---
typ: lekcja
tags: [lekcje, spekulacja, pomiar]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:119-130; ~/qwen-opt/lookup/logs/e3_summary.txt:43-49; ~/qwen-opt/lookup/logs/e4_summary.txt:43-49
status: aktualne
---
# Szeroki blok zmienia tekst T=1 nawet przy 0.3% kroków

**Ogon lookupu odpalił na czacie tylko 8–15 razy na 2258–4500 kroków, a mimo to t/s `spec_sweep` przy T=1 zmienił się o −1.1% (seedy 1–3) i +0.7% (seedy 4–9) przy stałym ms/krok (29.06 → 29.13, 28.74 → 28.73) (2026-10-18).**

Mechanizm: szerszy blok weryfikacji liczy logity inną ścieżką kerneli, więc przy remisach losowanie wybiera inny token i dalej powstaje inny tekst z innym tok/krok (pl-proza 2.74 → 2.61, pl-kod 3.35 → 3.52).

Reguła: regresję czatu od zmiany spekulacji oceniać po ms/krok i tok/krok poza promptami ze zmienionym tekstem, na wielu seedach; sam t/s przy T=1 może przekroczyć próg 0.5% w dowolną stronę.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[lekcja-szum-t-s-przy-t1]]
- [[lekcja-ustalony-seed-to-nie-powtorzenie]]
