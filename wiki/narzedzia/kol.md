---
typ: narzedzie
tags: [narzedzia, kolejka, gpu, tokeny]
aktualizacja: 2026-11-24
zrodlo: tools/kol; pomiar operatora ~/jarvo-testy/badania/cli-zamiast-tokenow/kernel.md (17–24.11: 411 ssh, 179 odczytów queue.log, 59 pętli czekania, 623 wait; średnio 434 tys. tokenów wejścia na wywołanie)
status: aktualne
---
# `tools/kol`: kolejka GPU na jaroserverai jednym poleceniem z krótkim wynikiem

**Jedno wywołanie zastępuje serię ssh + tail/grep queue.log + pętlę czekania + czytanie logów zadania; czekanie dzieje się na pudle (jedno połączenie ssh, sprawdzanie co 15 s), a wynik to END, błędy na górze i ogon logu bez szumu.**

- `kol stan` — runnery, trwające zadanie, ostatnie END / GPU FAULT / done, :8080, temperatura, kompilacje, znaczniki `~/k134/build-all.done`, liczba gfxhub od startu.
- `kol pusc <plik.jobs> [--czekaj] [--limit S]` — lokalny plik kopiuje do `~/qwen-opt/queue/up/`, startuje `run-jobs.sh` (setsid), z `--czekaj` czeka na „done” i wypisuje END i wynik każdego zadania.
- `kol czekaj <zadanie|plik.jobs> [limit_s]` — czeka na END zadania (zakończone odpowiada od razu) albo „done” pliku; przerywa przy GPU FAULT / GUARD i martwym runnerze.
- `kol czekaj-plik <plik> <regex> [limit_s]` — np. `kol czekaj-plik '~/k134/build-all.done' 'kr1 rc='`.
- `kol wynik <zadanie> [n]`, `kol log [n]`.
- Kody wyjścia: 0 ok, 1 rc≠0, 3 GPU fault/guard, 4 limit, 5 pudło nie odpowiada. `KOL_HOST=local` uruchamia stronę pudła lokalnie (testy na skopiowanych logach).
- Zasada dla mnie: kolejkę obsługuję tylko przez `kol`; w omp wołać z `timeout` ≥ limit, długie czekanie w tle (wynik przychodzi sam), bez pętli `sleep` i bez `wait` w kółko.
- Sprawdzone 24.11 na odtworzonym queue.log z 24.11 (k13x: rc=1 z FAIL na górze, k137-a, plik jobs), na żywym dopisywaniu END (15 s) i na sztucznym run-jobs.sh (`pusc --czekaj`); na żywym XTX przy najbliższej kolejce.

## Powiązane
- [[KOLEJKA-TESTOW]]
- [[kernel-od-a-do-z]]
