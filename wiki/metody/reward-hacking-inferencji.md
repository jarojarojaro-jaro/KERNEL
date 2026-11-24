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

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Wiersze [[ZRODLA]] o tych źródłach mówiły tylko „katalog hacków i obron” i „lekcja dopasowania do sędziego”. Brakowało porównania z naszymi narzędziami i stanu po trzech tygodniach:
- **Enigma (`app/engine/src/server`), stan 2026-11-24:** G1 naprawione (prompt renderowany raz na baseline'ie, `bench.ts:2-4`), G2 naprawione (decyduje ramię T=1, `bench.ts:6-7`), G3 naprawione (próg = max(2 × szum A/A, podłoga) i potwierdzenie zwycięzcy nowym pomiarem, `optimize.ts:240-253`), G4 naprawione (strażnik deep 32k, `optimize.ts:288-291`). **Otwarte:** G5, czyli tylko zegar serwera (`stream: false`, TTFT = `prompt_ms`, `bench.ts:203,264`), więc TTFT nie obejmuje szablonu, HTTP ani proxy Bun.
- **Lab:** `spec_sweep.py:18-25` to nadal te same 6 promptów, bez holdoutu i bez hasha buildu w wierszu (jest tylko md5 tekstu, `:46`). Open Kernel Challenge broni się ukrytym rankingiem, „nearby shapes”, medianami powtórzeń i oceną maintainerów, czy patch da się scalić (63e:100-120). U nas odpowiednikiem tej ostatniej oceny są bramki review w [[metody/_hub|metodach]], ale held-outu dalej nie mamy.
- **InferenceBench:** prosta wyszukiwarka hiperparametrów dała 11.53×, a najlepszy agent 8.08× (63e:347). Optimize w Enigmie to właśnie taka wyszukiwarka po gotowych flagach, a Enigma Turbo, czyli agent piszący silnik od zera, dała 0,7 t/s i bełkot ([[enigma-turbo-gemini-2026-11-20]]). Wniosek: najpierw przeszukać istniejące przełączniki, a własny kod pisać dopiero tam, gdzie wyszukiwarka utknęła.
- **Decagon** opisuje proces, nie hack: powtórka ruchu produkcyjnego, najpierw kilka powtórek baseline'u jako próg szumu, propozycja w formacie Explanation / Intervention / Prediction / Falsification, człowiek zatwierdza merge i pamięć „ta zmiana już raz dała zero”. Nasze odpowiedniki to `agent_bench`/replay `bodies_huge.jsonl`, A/A w Optimize, review JARO i [[wyniki-negatywne]]. Brakuje nam tylko formatu „Prediction / Falsification” zapisywanego przed pomiarem.
- Wafer (ROCm uruchomił kernel z LDS > 64 KiB bez błędu, „1.7 PFLOPS”) i GPU MODE (odcisk bajtów wyjścia po synchronizacji): obie obrony pasują do naszej bramki md5/KLD i do [[physics-floor-check]].

## Powiązane
- [[metody/_hub|metody]]
- [[metr-sakana]]
- [[kernelguard]]
- [[pygpubench]]
- [[zestaw-odlozony]]
- [[spec-sweep]]
