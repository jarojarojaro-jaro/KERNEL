---
typ: produkt
tags: [produkt, plan, tuning]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:195-221
status: aktualne
---
# Optymalizacja u użytkownika: kalibracja i noc

**Zawsze szybka kalibracja 1–5 min; opcjonalnie noc za zgodą (zasilacz, bezczynność, limity), z bramką md5 i ABBA; nigdy agentów ani kompilacji na komputerze użytkownika.**

- Kalibracja: naprawy L0, dopasowanie pamięci z testem pełnego kontekstu, wybór backendu i paczki, pomiar kosztu kroku spekulacji (`--spec-synth-len`), self-test logitów 5–30 s, baseline z testem A/A.
- Noc: checkpointy, limit czasu kernela < 2 s (Windows TDR; 5 resetów w 60 s = crash), czarna lista kandydatów; wybór spośród 2–3 prekompilowanych wariantów, MoE offload, `ubatch`, długość draftu na tekstach użytkownika.
- Zysk uznany tylko przy |Δ| > 2σ z testu A/A; zmiany numeryki tylko w „Trybie maksymalnym” z KLD.
- Opt-in: wyniki do bazy profili, nieznana kombinacja do kolejki fabryki.
- Strażnik regresji: re-pomiar po każdej aktualizacji, przy spadku powrót do poprzedniej paczki.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-anatomia-l0-l3]]
- [[produkt-architektura]]
- [[pomiar-abba]]
- [[raport-06-produkt]]
