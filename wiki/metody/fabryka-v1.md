---
typ: metoda
tags: [metody, fabryka, agenci, bramki]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:44-47,87-97,233-345; ~/KERNEL/product/research/16h-fabryka-v1.md:9-60,138-158,207-240; ~/KERNEL/product/research/16h-fabryka-v1.md:1-277
status: aktualne
---
# Fabryka v1: role, ledger, kaskada bramek

**Propozycja raportu 15f: fabryka przepisów jako role z rozdzielonymi uprawnieniami, karta twierdzenia zapisywana przed pomiarem, `ledger.jsonl` z łańcuchem hashy pisany tylko przez deterministyczny weryfikator i kaskada bramek G0–G7.**

- **Role:** Planista (rodzic), Implementer (podagent na hipotezę), **Weryfikator** (`factory verify`, skrypt – jedyny zapisuje werdykty), Audytor liczb (`factory claimcheck`), Kronikarz (szkice wiki), Człowiek (zgody na GPU, $, numerykę, scalanie).
- **Kaskada:** G0 statyczna (denylist ścieżek pomiaru, wyłącznik, karta) → G1 build + test-backend-ops → G2 poprawność (BIT / SAME-TOK / KLD) → G3 „czy zmiana się wykonała” → G4 ABBA + A/A + zestaw odłożony → G5 Amdahl/fizyka → G6 platforma → G7 zgoda człowieka.
- **Werdykty:** CONFIRMED (CI wyklucza 0 i |Δ| ≥ MDE), NULL, REFUTED, REGRESSION, INVALID, UNMEASURED, NEEDS-HUMAN.
- **Koszt `[SZACUNEK]`:** pełna weryfikacja twierdzenia BIT ~27 min GPU, KLD +~40 min; wszystkie 70 łatek ≈ 32 GPU-h, ze wspólną bazą ABBA (~8 min/przełącznik) ≈ 9 GPU-h – stąd kaskada.
- **Narzędzia:** `claim.py`, `verify.py`, `ledger.py`, `rules/`, `claimcheck.py`, `plot.py`, `queue.py`, backfill 70 łatek – razem ≈ 8–9 osobodni.
- **Nie teraz:** AutoIllustrate, > 2 implementerów na jedno GPU, recenzent AI, promocja bez CI.

**Stan 2026-10-16 (raport 16h):** rdzeń zbudowany – [[fabryka-cli]] (G0–G5, ledger, `sealed-v1`, 36 reguł, 57 testów). Reguła werdyktu z REFUTED przez `kill` z karty. Niezbudowane: `claimcheck`, `plot.py`, `queue.py`, backfill 70 łatek, G6, formalny G7.

## Ze scalonej notatki: Raport 16h: fabryka v1 zbudowana

Rdzeń fabryki z raportu 15f (działanie nr 1 z syntezy 15) zbudowany na CPU za $0: karta, ledger, weryfikator G0–G5, zestaw zapieczętowany, 36 reguł z fixture'ami z prawdziwych incydentów; brak walidacji na GPU.

- Odmowa jest strukturalna: weryfikator odmawia przy diffie dotykającym pomiaru, zmienionej/niezarejestrowanej karcie, innym harnessie, naruszonej pieczęci, innych sha256 binarek/modelu.
- Reguła werdyktu: MDE = max(próg, 2 × mediana |A/A|, `mde_pct`); progi 0.2% ms, 0.3% pp/tg, 0.5% t/s i tok/krok (z A/A 15f: 0.09% ms/krok, 0.16% t/s). REFUTED = cały CI poniżej `kill`; NEEDS-HUMAN zastępuje CONFIRMED dla KLD/NEAR-TIE i reguł R11/R26/R28/R29.
- Ograniczenia: izolacja to konwencja i hashe, nie piaskownica; near-tie z logprob serwera, nie logitów FP32; Qwen MTP ~45 min GPU na twierdzenie `[SZACUNEK]`; R14 (junction ≥ 90°C) może być za ostra. Nie zbudowano: `claimcheck`, `plot.py`, `queue.py`, backfill 70 łatek, integracji z `cloud/bench.sh`, G6/G7.
- Propozycja: kopiować sha256 `ledger.head` do [[log]] przy wpisach (zewnętrzna kotwica).

Szczegóły: [[fabryka-cli]], [[2026-10-16-backtest-regul-fabryki]].

## Powiązane
- [[metody/_hub|Metody]]
- [[produkt-fabryka]]
- [[zestaw-odlozony]]
- [[playbook-optymalizacji]]
- [[raport-15f-agentowa-nauka]]
- [[kernelguard]]
