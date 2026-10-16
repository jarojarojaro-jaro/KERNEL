---
typ: produkt
tags: [produkt, plan, werdykt]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:1-30
status: aktualne
---
# Werdykt planu produktu

**Produkt da się zrobić, a luka jest realna, ale duży skok (np. Qwen 40 → 109 t/s) daje konfiguracja i przepisy z naszego labu, nie „noc u użytkownika” (PLAN, stan 2026-10-15).**

- Żaden z 30+ sprawdzonych produktów nie robi naraz: baseline'u na komputerze użytkownika, optymalizacji poza flagami, weryfikacji „te same odpowiedzi”, raportu przed → po i pełnej obsługi AMD.
- Źródła skoku: (a) konfiguracja – ×1.5–2.2 w minutach; (b) przepisy z labu per (arch × rodzina modelu) – kolejne +30–70%. Noc u użytkownika: typowo 0–15%.
- Produkt = aplikacja + fabryka przepisów. Fosa: baza zweryfikowanych profili per (GPU, sterownik, silnik, model, kwant) i tempo fabryki; warstwa konfiguracji stanie się towarem w 6–12 miesięcy.
- Platformy: rozwój na Linuksie, obowiązkowa analiza platformy dla każdej optymalizacji (decyzja 2026-10-15).
- Kolejność: dowód (faza 0) → silnik + CLI/TUI → GUI i noc → płatna edycja i macOS. Nie zaczynamy od GUI.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-anatomia-l0-l3]]
- [[produkt-fabryka]]
- [[raport-01-konkurencja]]
- [[2026-10-15-linux-i-analiza-platformy]]
