---
typ: lekcja
tags: [lekcje, mtp, trening, wynik-negatywny]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/11-mtp-pl-pilot.md:3-9,82-93,179-183; ~/KERNEL/product/research/10-post-training.md:29-33
status: aktualne
---
# Fabryczna głowica MTP jest już blisko optimum

**Douczanie głowicy MTP Qwen3.8-27B na 1.7 M tokenów dało ±0.2% tok/krok offline (online ±2%): głowica była trenowana wielokrokowo na dużo większym korpusie, a zapas widoczny u wyroczni (+21–33%) nie jest osiągalny tą drogą.**

- Strata TV/CE spadała (0.317 → 0.307), ale akceptacja greedy prawie się nie ruszała – spadek straty nie gwarantuje zysku tok/krok.
- Dane off-policy (odpowiedzi z datasetów bez bloku myślenia) szkodzą: 3.281 → 3.235 tok/krok na starcie.
- Bramka offline (zapas wyroczni ≥ +5%) była warunkiem koniecznym, nie wystarczającym; lepszy test to krótki przebieg on-policy z pomiarem na held-out.
- Raport 10 szacował +10–17% tok/krok; wynik pokazuje, że szacunki z literatury (Red Hat, FastMTP) nie przenoszą się na głowicę już dobrze wytrenowaną.
Reguła: przed płatnym treningiem draftera sprawdzić na małym przebiegu, czy model w ogóle się ruszy; większy zapas leży raczej w probabilistycznym drafcie przy T=1.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-commity-bez-pomiaru]]
- [[lekcja-jeden-prompt]]
- [[glowica-mtp]]
- [[2026-10-16-mtp-pl-pilot]]
