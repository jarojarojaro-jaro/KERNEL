---
typ: decyzja
tags: [decyzje, research, produkt, publikacja]
aktualizacja: 2026-11-09
zrodlo: polecenie użytkownika 2026-11-09 (czat z Main); ~/KERNEL/product/research/69-SYNTEZA.md
status: aktualne
---
# 2026-11-09: decyzje po rundzie 69 (DSpine, Astra-Stop, publikacja, jakość-mini)

**Użytkownik (2026-11-09): DSpine odpuszczamy (nie schodzimy do 64k kontekstu), Astra-Stop na razie odpuszczamy (ciekawy kierunek na przyszłe fine-tuningi i benchmarki), rankingi prędkości dalej tylko czytamy, ale „wkrótce” zaczniemy publikować; robimy porównanie jakości kandydatów 12–16 GB (Bonsai, Saluki, ISTA, LFM) zestawem „jakość-mini”; uruchomione: EvalPlus na naszym Qwenie i qwen-warp vs nasz fork na 3090.**

- **DSpine-27B:** nie jako drafter domyślny ani dla Enigmy — na 24 GB obcina kontekst do ~64k zamiast 245–262k, proza i PL gorzej niż MTP ([[drafter-dspine]], 69a). Test T1 nie jest planowany.
- **Astra-Stop:** nie testujemy teraz (zmienia zachowanie, wyciek `</think>` i zamykających tagów do odpowiedzi). Zostaje jako temat na przyszłe eksperymenty z fine-tuningiem + benchmarkami ([[astra-stop]], 69c).
- **Publikacja wyników prędkości** (LocalMaxxing, llm-bench.io, llamabench.ai, club-3090, Token Atlas): nadal tylko odczyt ([[2026-10-20-bez-publikacji-localmaxxing]]), ale publikacja jest planowana wkrótce — przygotowywać wyniki w formie gotowej do zgłoszenia (warunki, wersja silnika, prompty).
- **Jakość-mini:** zgoda na porównanie kandydatów 12–16 GB jednym zestawem (GSM8K, MMLU-Pro / PL, HumanEval+, BFCL); źródła danych i pobrania modeli — do potwierdzenia przy uruchomieniu.
- Uruchomione tego dnia: EvalPlus (HumanEval+/MBPP+) na produkcyjnym Qwen3.8-27B-Uncensored, qwen-warp vs `enigma-cuda-fork` na wynajętej 3090.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[raport-69-synteza]]
- [[2026-10-20-bez-publikacji-localmaxxing]]
