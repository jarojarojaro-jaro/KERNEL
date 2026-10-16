---
typ: research
tags: [research, fabryka, agenci]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16h-fabryka-v1.md:1-277
status: aktualne
---
# Raport 16h: fabryka v1 zbudowana

**Rdzeń fabryki z raportu 15f (działanie nr 1 z syntezy 15) zbudowany na CPU za $0: karta, ledger, weryfikator G0–G5, zestaw zapieczętowany, 36 reguł z fixture'ami z prawdziwych incydentów; brak walidacji na GPU.**

- Odmowa jest strukturalna: weryfikator odmawia przy diffie dotykającym pomiaru, zmienionej/niezarejestrowanej karcie, innym harnessie, naruszonej pieczęci, innych sha256 binarek/modelu.
- Reguła werdyktu: MDE = max(próg, 2 × mediana |A/A|, `mde_pct`); progi 0.2% ms, 0.3% pp/tg, 0.5% t/s i tok/krok (z A/A 15f: 0.09% ms/krok, 0.16% t/s). REFUTED = cały CI poniżej `kill`; NEEDS-HUMAN zastępuje CONFIRMED dla KLD/NEAR-TIE i reguł R11/R26/R28/R29.
- Ograniczenia: izolacja to konwencja i hashe, nie piaskownica; near-tie z logprob serwera, nie logitów FP32; Qwen MTP ~45 min GPU na twierdzenie `[SZACUNEK]`; R14 (junction ≥ 90°C) może być za ostra. Nie zbudowano: `claimcheck`, `plot.py`, `queue.py`, backfill 70 łatek, integracji z `cloud/bench.sh`, G6/G7.
- Propozycja: kopiować sha256 `ledger.head` do [[log]] przy wpisach (zewnętrzna kotwica).

Szczegóły: [[fabryka-cli]], [[2026-10-16-backtest-regul-fabryki]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15f-agentowa-nauka]]
- [[raport-15-synteza]]
- [[fabryka-v1]]
