---
typ: lekcja
tags: [lekcje, metodyka, optymalizacja, progi]
aktualizacja: 2026-10-20
zrodlo: ~/AGENTS.md:19; ~/KERNEL/product/research/24v-prefill-fa.md:7; ~/KERNEL/product/research/24r-mmvq-pasmo.md:7-9; ~/KERNEL/product/research/24s-proza-drzewa.md:16; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:10-12; ~/KERNEL/product/research/24n-mmvq-n5.md:10; ~/KERNEL/product/research/24t-entropia-wag.md:8; ~/KERNEL/product/research/24u-norm-quant.md:7; ~/KERNEL/product/research/24w-pair2.md:5
status: aktualne
---
# Wyraźna wygrana albo nic: pomysły poniżej ~1–2% odpadają, nawet bitowe

**Zasada użytkownika z 2026-10-20: pomysł, który nie wygrywa wyraźnie w krótkim A/B, odrzucamy – nawet gdy jest bit-exact; przed kodem liczymy sufit, żeby nie budować rzeczy, które z definicji nie przekroczą progu.**

Odrzucone mimo poprawności (2026-10-19/20):
- 24v FA D=256 bez spilli: +0.4–0.8% prefill, bitowo identyczne ([[raport-24v-prefill-fa]]);
- 24a bariera LDS i 24f MMVQ n=1 wide: w szumie / −1.0% (`26:10-11`);
- 24w PAIR2: −40 uruchomień/krok, md5 OK, a czat tylko +0.4% (115.1 → 115.6 t/s) ([[raport-24w-pair2]]);
- 24n obłożenie n=5: −0.5%; 24j router: sufit +1.1%; 24t entropia wag: ≤ 0.9%; 24u norma+q8_1: ≤ 0.012 ms/krok.

Najpierw sufit (analiza CPU, minuty):
- 24r: sufit odczytu XTX 926 GB/s, weryfikacja n=5 na 82%, strata to ~2.4 ms/krok stałego kosztu uruchomień – nie pętla kernela ([[raport-24r-mmvq-pasmo]]);
- 24s: drzewa draftu dają ≥ +6% dopiero, gdy dodatkowy wiersz weryfikacji kosztuje ≤ 0.57 ms (dziś 0.85) ([[raport-24s-drzewa-proza]]).

Budżet: [[2026-10-20-szybkie-iteracje]].

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[2026-10-20-szybkie-iteracje]]
- [[raport-24r-mmvq-pasmo]]
- [[raport-24s-drzewa-proza]]
- [[raport-24v-prefill-fa]]
- [[wyniki-negatywne]]
- [[raport-24w-pair2]]
