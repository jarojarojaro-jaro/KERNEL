---
typ: metoda
tags: [metody, kolejka, pomiar, vast, wydajnosc]
aktualizacja: 2026-11-26
zrodlo: ~/qwen-opt/queue/logs/queue.log (jaroserverai, okno 2026-11-25 10:00 – 2026-11-26 01:30); ~/qwen-opt/queue/run-jobs.sh; ~/qwen-opt/cloud/nvq/orch.py; phases.txt instancji nvq/nvq2 2026-11-26; panel JARO 2026-11-26 02:31
status: aktualne
---
# Szybsze testowanie: gdzie ucieka czas karty i co naprawione (2026-11-26)

**JARO: „mamy optymalizować też sposoby testowania — wszystko ma być lepsze, szybsze, wydajniejsze”. Pomiar narzutu: na XTX w oknie 12,7 h joby zajęły 11,5 h, 67 restartów/zatrzymań czatu 22 min, przerwy między paczkami 52 min (razem ok. 10% karty); na Vaście 3090 straciła ok. 40 min (45% pracy po starcie) na czekaniu na build obcego silnika, a druga 3090 ok. 20 min na powolnym dysku hosta.**

## Naprawione dziś
- **Kolejka XTX:** zadanie `restore8080` na końcu paczki jest pomijane, gdy w kolejce czeka następna paczka (`run-jobs.sh:83-88`); czat wraca dopiero po ostatniej paczce albo przez keepera, jeśli kolejny runner padnie. Zysk: ok. 20 s × liczba paczek (dziś 67 → kilka restartów).
- **Paczki Vast (`nvq/orch.py:81-94`):** czekamy tylko na build naszego forka; pozycje wymagające drugiego silnika (K-122 llamAmpere) idą na koniec i są pomijane, gdy jego build nie skończył się na czas. Próba na sucho przechodzi.
- **Jeden serwer, wiele ramion:** WE1 obsługuje skale LoRA 0 / 0,5 / 1 / 1,5 w jednym procesie serwera (pole `lora` w żądaniu), zamiast restartu serwera na ramię (oszczędza ok. 30–60 s ładowania na ramię); ta sama zasada co jeden serwer dla W16/W8/W5 w K-046.
- **Paczki od agentów z bramką na wejściu:** każda paczka zaczyna od testu poprawności (test-backend-ops / md5 / parytet), a pomiary ruszają tylko po jej przejściu (marker `GATE_PASS`), więc zepsuty build kosztuje sekundy, nie 15 minut.

## Do zrobienia
- Wybór hosta Vast także po szybkości dysku (dziś tylko moc i zegar pamięci): test zapisu 1 GB w hostguard.
- Build drugiego silnika (llamAmpere, qwen-warp) raz, jako artefakt, a nie na każdej wynajętej maszynie.
- Kolejka: łączenie paczek z tym samym serwerem (ten sam model i binarka) w jedną sesję serwera.
- Skrypty zbierające wynik (`summary.py`) uruchamiane od razu po paczce w kolejce, żeby wynik był gotowy przed raportem.

## Powiązane
- [[metody/_hub|metody]]
- [[stos/topki]]
