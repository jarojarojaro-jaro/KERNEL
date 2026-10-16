---
typ: metoda
tags: [metody, fabryka, agenci, bramki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15f-agentowa-nauka.md:44-47,87-97,233-345; ~/KERNEL/product/research/16h-fabryka-v1.md:9-60,138-158,207-240
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

## Powiązane
- [[metody/_hub|Metody]]
- [[produkt-fabryka]]
- [[zestaw-odlozony]]
- [[playbook-optymalizacji]]
- [[raport-15f-agentowa-nauka]]
- [[kernelguard]]
