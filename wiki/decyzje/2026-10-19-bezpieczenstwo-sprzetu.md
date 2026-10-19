---
typ: decyzja
tags: [decyzje, gpu, bezpieczenstwo]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/AGENTS.md:5; komunikat Main do WikiIngest 2026-10-19
status: aktualne
---
# 2026-10-19: maksymalna optymalizacja, ale nigdy kosztem bezpieczeństwa sprzętu

**Twarda zasada użytkownika (2026-10-19, `AGENTS.md` wiersz 5): optymalizujemy maksymalnie, ale nigdy kosztem bezpieczeństwa sprzętu.**

- Pierwszy page fault, timeout ringu albo reset GPU wywołany przez build = natychmiastowy stop tego builda na GPU; żadnego „odrzuć blok i powtórz”. Dalej debug na CPU, poprawka, krótki nadzorowany test.
- Nowy build eksperymentalny: `test-backend-ops` dotkniętych operacji i krótki smoke przed długimi pomiarami.
- Strażnik [[gpu-guard]] pilnuje limitów i zabija procesy GPU poza produkcją na :8080.

Tło: E-X4 przez kilka resetów stosował odrzucanie i powtarzanie bloków ([[2026-10-18-sprzezone-probkowanie-mtp]]); pamięć GPU doszła do 90 °C, zanim agent główny zareagował ([[lekcja-agent-nie-patrzyl-na-temperatury]]). Analiza page faultów: [[raport-17-gpu-page-fault]].

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-16-nie-placimy-za-przestoj]]
- [[2026-10-19-wentylator-100-przy-pracy]]
- [[rx-7900-xtx]]
