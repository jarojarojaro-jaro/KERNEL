---
typ: produkt
tags: [produkt, plan, roadmapa]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:418-460
status: aktualne
---
# Roadmapa: fazy 0–4 z kryteriami wyjścia

**Faza 0 dowód (3–4 tyg., E1–E7), faza 1 silnik + CLI/TUI alfa (6–8 tyg.), faza 2 GUI + noc beta (8–12 tyg.), faza 3 launch + Turbo + macOS (od ~6.–9. miesiąca), faza 4 rozszerzenia.**

- Faza 0: E1 Ollama/LM Studio vs nasz build na XTX; E2 tylko L1 na v0.7.0 vs pełny stack na 3–5 modelach; E3 analiza platformy 70 łatek + build Windows w CI; E4 NVIDIA 5060 Ti i 3060 (md5 + zysk); E5 kampania L3 na nowym modelu z mierzonym kosztem; E6 rebase na v0.7.0 + `loo.py run` + `kld_canary.sh`; E7 prototyp detekcji w Rust. Wyjście: `product/F0-WYNIKI.md`.
- Faza 1 – wyjście: na ≥8 kartach MVP ≥1.3× wobec Ollamy, zero błędów md5, pierwsza rozmowa < 10 min.
- Faza 2 – wyjście: publiczna beta, ≥500 instalacji, crash rate nocy < 1%.
- Faza 3: Paddle jako MoR, macOS, Arc, Strix Halo; przepis ≤ 7 dni na top-3 arch.
- Faza 4: turbo-silnik (wzór hipfire / Lucebox), telefon, Business.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-budzet]]
- [[produkt-ryzyka]]
- [[2026-10-16-rebase-v070]]
- [[2026-10-16-kampania-nvidia]]
