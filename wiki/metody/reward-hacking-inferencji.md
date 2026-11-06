---
typ: metoda
tags: [metody, pomiar, reward-hacking, benchmark]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63e-metodologia-agenci.md:49-67,343-415; git 1af7fd2
status: aktualne
---
# Reward hacking w optymalizacji inferencji: wzorce i nasze luki

**Znane hacki to: praca na bocznym strumieniu poza timerem, pusty pierwszy chunk SSE (TTFT < 3 ms), cache wyników po adresie wskaźnika, liczenie wywołań do wykrycia fazy pomiaru, niższa precyzja przy luźnej tolerancji i podmiana modelu pod kanoniczną nazwą (InferenceBench, Overshoot, wafer, GPU MODE; 2026-11-05).**

Audyt naszego benchmarku (63e §6):
- **G1 (krytyczne):** w Enigmie kandydat `enigma` renderował prompt z własnego `/apply-template` (inne myślenie, inny szablon), więc `decodePct` porównywał różne obciążenia. Naprawione 2026-11-05 (1af7fd2, G1–G4, G7): zawyżenie +191.5% vs uczciwe +179.8% ([[enigma-uczciwy-benchmark]], [[lekcja-benchmark-te-same-tokeny]]).
- G2 decyzja przy T=0, użytkownik przy T ≥ 0.6; G3 brak progu szumu (każde +0.1% wygrywa); G4 deep 32k poza decyzją; G5 tylko zegar serwera; G7 brak ochrony przed BACO ([[baco-runtime-suspend]]).
- `spec_sweep`: 6 stałych promptów od 2026-10-13 bez holdoutu, brak hasha buildu w wierszu, tylko back-to-back.
- Obrony: ten sam input bajt w bajt, próg szumu z powtórek baseline'u, holdout, zegar klienta, hash kodu przy wyniku.

## Powiązane
- [[metody/_hub|metody]]
- [[metr-sakana]]
- [[kernelguard]]
- [[pygpubench]]
- [[zestaw-odlozony]]
- [[spec-sweep]]
