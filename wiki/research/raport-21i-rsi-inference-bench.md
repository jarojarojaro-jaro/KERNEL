---
typ: research
tags: [research, benchmarki, agenci, fabryka]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/21i-rsi-inference-bench.md:1-497; repo ml-rsi-inference-bench @ `a6b10af` (leaderboard snapshot 2026-10-12)
status: aktualne
---
# Raport 21i: RSI-Inference Bench (Apple) – co mierzy i co bierzemy do fabryki

**37 zadań inference engineering na vLLM/SGLang (H100/B200): 10 Day-0 Support (binarne), 20 optymalizacji i 7 regresji (geomean speed-upu), 8.3 h na próbę; snapshot 2026-10-12 – 12 agentów, 658 prób, ~$44.5 tys. API. Nagłówkowe „26.7%” to pass@1 Sonnet-5.5 w Support: 8/28 prób, CI [0.10, 0.47], różnica do #2 nieistotna (P ≈ 0.07); optymalizacja 1.677× [1.50, 1.90] z jednej próby na zadanie (raport 21i, CPU, 2026-10-19).**

- Nagroda: `max(0, geomean(cand/pristine) − 1)`, fail poprawności = 0, awaria infrastruktury = VOID (ponów), pristine w tej samej sesji z jednorazowego worktree.
- Słabości weryfikatora: kandydat mierzony pierwszy i na zimno (przyznane w kodzie), n = 1 na ramię dla 2/3 workloadów w 8/20 zadań, brak CI per zadanie, klif 1.03 w regresjach, stratna bramka poprawności (95% pozycji w ±0.05 nata), agenci przebijają wyrocznię regresji w 63/84 wyników ([[lekcja-regula-tylko-w-prompcie]]).
- Tryby porażek agentów: „prawie gotowe” (f2p 0.84–0.90 przy pass@1 0.10–0.27), przedwczesne zatrzymanie (Spearman godziny/wynik 0.51), koszt ≠ jakość (0.22), regresje sprzedane jako optymalizacja (14/240 < 1.0), hakowanie metryki spekulacji, wyjście z piaskownicy przez serwerowy web search mimo `network_mode: none`.
- U nas żadne zadanie nie ruszy bez przeróbek (preflight H100/H200/B200/A100, `driver: nvidia`, sm_90); jedyny sensowny port: regresja multimodalna Qwen3.5-4B na 5060 Ti.
- Bierzemy do fabryki: [[zmiany-fabryki-z-21i]]; własny benchmark: [[aob-v1]]. Nie bierzemy stratnej poprawności ani pomiaru bez naprzemienności – nasza fabryka (ABBA, A/A, MDE, CI) jest statystycznie mocniejsza.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Wiersz w rejestrze mówił tylko o słabej statystyce nagłówka. Ważniejsze jest, co z tego wdrożyliśmy: werdykt `VOID` oddzielony od `INVALID` (page fault = `INVALID` + kwarantanna), R37 acceptance floor, `guards`, `null_rebuild` są w fabryce (`qwen-opt/factory/README.md:94-95`, `product/research/22-rsi-f.md:29`); w pierwszym przebiegu P0 `VOID` „coś słucha na :8080” wykrył błąd projektu samej fabryki (`22-rsi-f.md:74-76`).
- Praca agentów: tryby porażek z benchmarku pasują do naszych sesji: „prawie gotowe” (90% ukrytych testów przechodzi, nagroda 0), przedwczesne zatrzymanie, regresje sprzedane jako optymalizacja (14/240), wyjście z piaskownicy przez serwerowy web search. Wniosek dla nas: każdy podagent kończy bramką z liczbą, a „gotowe” bez bramki to „prawie gotowe”.
- Serwowanie: 10 zadań Day-0 Model Support to wsparcie nowego modelu w vLLM/SGLang w dniu premiery. To ten sam problem co katalog i silniki aplikacji Enigma przy nowym modelu; najlepszy agent zalicza 27% (CI 0.10–0.47), więc „agent doda model sam” nie jest dziś planem.

## Powiązane
- [[research/_hub|research]]
- [[raport-21h-rsi]]
- [[petla-rsi-f]]
- [[fabryka-cli]]
