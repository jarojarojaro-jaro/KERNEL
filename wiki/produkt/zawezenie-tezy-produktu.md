---
typ: produkt
tags: [produkt, decyzje-otwarte, konkurencja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:38-44,225-254,395-396; ~/KERNEL/product/PLAN.md:10-15
status: do-sprawdzenia
---
# Do decyzji: zawężenie tezy PLAN §0.1 po Magnitude

**Propozycja raportu 15c (do decyzji użytkownika): teza „żaden produkt nie robi naraz…” zostaje, ale „optymalizacja poza flagami” nie jest już wyróżnikiem; wyróżnikiem jest kombinacja weryfikacji (md5/KLD) + przed → po wobec tuned upstream + AMD natywnie.**

Powód: Magnitude stroi kernele na urządzeniu (60 s przy pobraniu), a tqLLM, Actual i TensorFold mają spekulację dającą to samo co plain. Brakuje im: pomiaru przed → po na maszynie użytkownika, publikowanej bramki md5/KLD i natywnego AMD.

Proponowane zmiany w planie:
- §0.1: zawęzić wyróżnik jak wyżej; baseline zawsze dwa – domyślna Ollama i tuned llama.cpp (A1);
- §2 L2: „szybki lokalny tuning bitowo neutralnych parametrów ≤ 60 s” jako część kalibracji (konkurencja ustawiła oczekiwanie „przy pobraniu, nie w nocy”);
- raporty z dwiema klasami obciążenia (kopia i nie-kopia);
- odpuścić wyścig na Macu i w integracjach agentów, skopiować wzorzec „1 klik dla agenta”.
Status: nie zatwierdzone.

## Powiązane
- [[produkt/_hub|produkt]]
- [[werdykt]]
- [[otwarte-decyzje-produktu]]
- [[magnitude]]
- [[raport-15c-nowe-silniki]]
