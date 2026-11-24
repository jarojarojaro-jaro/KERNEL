---
typ: ekosystem
tags: [ekosystem, serwowanie, harmonogram, agenci, produkt, enigma]
aktualizacja: 2026-11-24
zrodlo: https://github.com/basecompute/superfluid (`3240988`, 2026-11-20; README.md, docs/features/scheduling.md, docs/features/sessions.md, docs/performance/benchmarks.md, crates/superfluid-daemon/src/scheduler.rs); arXiv 2611.17753 (v1 2026-11-13); zwiad [[zwiad-2026-11-14]] (delta 2026-11-16)
status: aktualne
---
# Superfluid (basecompute): lokalny serwer nad llama.cpp/MLX, który robi to, czego nie robi ani topka, ani Enigma

**To ten sam produkt co aplikacja Enigma (lokalny serwer, instalacja silnika przy pierwszym użyciu, API OpenAI/Anthropic/Ollama, uruchamianie agentów), ale cały wysiłek poszedł w zachowanie pod obciążeniem agentów: czat za 8 pracującymi agentami dostaje pierwszy token po 1,47 s, a goły llama-server po 291 s (README.md:148).**

## Jak to działa
- Trzy procesy: demon (API, szablony, tokenizer, harmonogram, dziennik sesji), worker na model (wagi, KV, próbkowanie), węzeł na innej maszynie. Silniki llama.cpp/MLX instalowane z ich własnych wydań, nic nie jest wbudowane (README.md:173-175).
- **Harmonogram z klasami:** `interactive` > `completion` > `agent` > `background`; czat wywłaszcza najniższy dekodujący pas, ten odkłada KV i wraca na początek kolejki, strumień klienta tylko pauzuje (docs/features/scheduling.md:43-45). Prefill pocięty tak, by jeden takt trwał ~0,5 s, gdy ktoś czeka na wejście (scheduling.md:60-64).
- **Wspólny prefiks:** żądanie, które dzieli ≥ 1024 tokeny z prawie skończonym żądaniem, czeka na nie i startuje z jego cache (`scheduler.rs:118-126`). 32 żądania z jednym promptem 4k: 56 s vs 171 s llama-server (README.md:149).
- **Trwałość:** każdy token trafia do dziennika (fsync) przed wysłaniem klientowi; worker po awarii jest restartowany, sesja wraca z dziennika: 1,75 s, llama-server „does not recover” (README.md:150, docs/features/sessions.md:5-15).
- **Pamięć:** jedna pula KV, przy 85% zajętości wyrzuca prefiksy z cache do 70%, a dla llama.cpp wyrzucone prefiksy trzyma w RAM; czyta też presję pamięci systemu (`/proc/pressure/memory`) (scheduling.md:69-75).
- **Pas „batch-invariant”:** żądanie może dostać pas liczony samotnie, żeby wynik nie zależał od innych żądań (scheduling.md:47-49).
- **Flota:** każda maszyna trzyma pełną kopię modelu, głowa wysyła sesje według zmierzonej prędkości i obciążenia; maszyna, która padnie w trakcie odpowiedzi, jest zastępowana i strumień biegnie dalej (README.md:109, 173).
- Uczciwy pomiar: zestaw 8 scenariuszy z warunkiem zaliczenia (zabicie workera, restart demona, agenci + czat, wyczerpanie KV, 200 tur narzędzi, rozłączenie klienta, wspólny prefiks), porównany z llama-server, Ollama i mlx_lm.server na tej samej maszynie (docs/performance/benchmarks.md:44-66). Warstwa serwera nie kosztuje: 76,7 vs 76,8 t/s przy 1 żądaniu.

## Porównanie z naszymi odpowiednikami
| warstwa | Superfluid | u nas |
|---|---|---|
| wiele żądań naraz | 8 pasów, klasy, wywłaszczenie | topka `-np 1` (K-086 odrzucone); Enigma `-np 1` (`app/engine/src/server/engine.ts:571`); drugie żądanie czeka za całą odpowiedzią (K-106: +2,6 s) |
| wspólny prefiks | czekanie na prawie gotowy wpis ≥ 1024 tok. | `LLAMA_SERVER_CACHE_SHARE_MIN=1024` (STAN-PRAC.md:47), ten sam próg; rozwiązuje inny przypadek (obce zapytanie wyrzucało cache) |
| awaria silnika | restart workera, sesja z dziennika | Enigma: po `ready` nikt nie pilnuje, proxy zwraca 502 (`api.ts:117`); topka: `topka-keeper.sh` uruchamia serwer ponownie ([[2026-10-19-topka-tylko-keeper]]), przerwana odpowiedź przepada |
| odtwarzalność | pas „batch-invariant” na życzenie | K-001: wynik zależał od historii serwera (stare komórki K/V w FA), poprawka zmierzona 20.11, wdrożenie czeka na decyzję |
| wiele maszyn | jeden endpoint, praca według prędkości | XTX, 3090, flota, każda osobno; kolejka `run-jobs.sh` na jednej maszynie |
| pomiar | scenariusze awarii z warunkiem zaliczenia | xtxbench: dekod 1,7k i prefill, bez scenariuszy obciążenia |

## Co bierzemy
1. Do Enigmy: scenariusze „agenci + czat”, „zabicie silnika”, „wspólny prefiks” jako testy z warunkiem zaliczenia, przed kolejnymi optymalizacjami t/s (to samo wskazała analiza [[inference-stack]]).
2. Watchdog silnika w Enigmie z restartem i odtworzeniem rozmowy, zamiast 502.
3. Klasy priorytetu na naszym proxy: czat użytkownika przed subagentami, nawet przy `-np 1` (kolejka przed llama-server, bez zmiany silnika).
4. Lab: jeden endpoint dla kilku maszyn z tym samym modelem to wzór do rozważenia dla floty, nie pilny.

Czego nie bierzemy: dziennika z fsync każdego tokenu (u nas sesje agentów trzyma omp), BaseRT (tylko Apple, NVIDIA arm64, Strix).

## Powiązane
- [[inference-stack]]
- [[sglang-unified-memory]]
- [[zwiad-2026-11-14]]
- [[KOLEJKA-TESTOW]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
