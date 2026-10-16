---
typ: narzedzie
tags: [narzedzia, determinizm]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/det_probe.py:1-25; ~/KERNEL/qwen-opt/NOTES.md:377
status: aktualne
---
# det_probe.py (sonda determinizmu)

**Sprawdza, które zdarzenie serwera psuje powtarzalność greedy: wysyła to samo zapytanie bez cache przed i po innych zapytaniach i pokazuje, gdzie wyjścia się rozjeżdżają.**

Wynik (runda 4 LFM, 2026-10-14): ten sam greedy request bez cache daje inny tekst przy 1. i 2. wywołaniu po starcie serwera (rozjazd po ~270 znakach), tak samo przy PM4=1 i PM4=0, a upstream `e60eff95f` zachowuje się tak samo (nawet częściej). To zachowanie llama.cpp, nie łatek; dlatego porównania greedy robimy zawsze na świeżym serwerze. Uruchomienie: `det_probe.py --port N`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[pm4-soak]]
- [[greedy-check]]
- [[lekcja-ten-sam-serwer-pending-h]]
- [[zgodnosc-bitowa-md5]]
