---
typ: ekosystem
tags: [ekosystem, moe]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/qwen-opt/research/repos/05-pplx-kernels.md:1-22; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:15
status: aktualne
---
# perplexityai/pplx-kernels i pplx-garden/lily

**Kernele MoE all-to-all Perplexity (porzucone, HEAD `f70d1eb7`) i następca `lily` (MoE decode na jednym GPU); werdykt: niska.**

pplx-kernels: kooperacyjny launch z barierą gridu, flagi acquire/release z kodowaniem `count+1`, combine w stałej kolejności (deterministyczny). Liczby autorów: EP8 NVLink dispatch 41.6 µs i combine 41.7 µs przy 1 tokenie/GPU. `lily` (Rust+Metal, Qwen3.6-35B-A3B): 194.7 t/s przy kontekście 256 na M5 Max, 1.31x względem MLX. Dla nas tylko potwierdzenie ticketów/barier i pomysł rozgrzewania Infinity Cache między kernelami.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- `lily` to dokładnie to, czym miał być nasz Enigma Turbo: mały własny silnik pod jeden model. Różnica jest w dyscyplinie, nie w kernelach (README: https://github.com/perplexityai/pplx-garden/tree/main/lily):
  - przy ładowaniu ściśle sprawdza architekturę i kwantyzację, inny plik odrzuca; Enigma Turbo po cichu podstawiał stałe za brakujące tensory i dawał bełkot ([[enigma-turbo-gemini-2026-11-20]]);
  - test „golden” na prawdziwym checkpoincie 35B z przypiętą rewizją HF; Turbo miał testy tylko na syntetycznym modelu 256 × 4 warstwy;
  - API celowo wąskie: nieobsługiwane parametry (sampling, stream, narzędzia) są odrzucane, a nie ignorowane;
  - raport wydajności z „measurement contract” i krokami odtworzenia, porównanie z MLX 0.32.2 (1.31×, ich pomiar).
- Serwowanie: cache prefiksu to stałe LRU na 2 stany, użyte tylko przy ścisłej równości prefiksu tokenów, a odpowiedź podaje `cached_tokens`. U nas ten sam problem to polityka slotów topki (E4 w [[inference-stack]]); zwracanie liczby tokenów z cache klientowi warto przejąć w proxy aplikacji.
- Silnik: decode z wyprzedzeniem 2 kroków (token nie wraca do hosta) i concurrent dispatch (`qwen-opt/research/repos/05-pplx-kernels.md:31-32`) potwierdzają nasze kierunki P4/P5.
- Werdykt: pplx-kernels (EP między GPU) dla nas niska; `lily` średnia–wysoka jako wzór, jak budować własny silnik, jeśli kiedyś wrócimy do tego pomysłu.

## Powiązane
- [[deepgemm]]
- [[mkernel]]
- [[fuzje-lfm-moe]]
- [[repos-30-przeglad]]
