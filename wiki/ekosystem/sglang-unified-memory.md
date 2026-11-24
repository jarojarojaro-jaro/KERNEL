---
typ: ekosystem
tags: [ekosystem, pamiec, serwer, gdn, telegram]
aktualizacja: 2026-11-24
zrodlo: https://www.lmsys.org/blog/2026-11-11-unified-memory/ (2026-11-11, SGLang `daa171846f`); https://x.com/ChengWan17/status/2120690586625990822 (Telegram „gpu”, 2026-11-13)
status: aktualne
---
# SGLang Unified Memory: jedna arena VRAM dla KV, okna SWA i stanu rekurencyjnego

**SGLang (`--enable-unified-memory`, eksperymentalne) zastępuje stały podział VRAM między pule (pełne KV, okno SWA, stan Mamby/GDN) jedną areną z kompaktowaniem i układem „jeden wpis na token” (KV celu i draftu razem). Zysk dotyczy tylko serwowania wielu żądań naraz: na jednej H200 przy 64–1024 współbieżnych żądaniach do +26% przepustowości i 1000 zamiast 618 żądań w locie. Przy domyślnych proporcjach różnica to szum: 5830 vs 5880 tok/s (2026-11-13).**

- **Werdykt dla nas: nie warto.** Topka obsługuje jeden slot: KV 262 144 tokenów i stan GDN rozmiaru stałego od startu. Nie ma tu żadnego suwaka proporcji, który dałoby się źle ustawić, więc nie ma pamięci uwięzionej w niewłaściwej puli. Dla decode i prefill pojedynczego strumienia wpływ jest 0%.
- **Do zapamiętania.** Wpis na token pakuje KV draftu obok KV celu. Ten sam pomysł mógłby kiedyś skrócić zarządzanie KV draftu MTP, ale nie przyspiesza. Jeśli kiedyś wróci temat wielu użytkowników na NVIDIA (K-061 w [[KOLEJKA-TESTOW]]), to odpowiednikiem w llama.cpp jest `-kvu` plus stały `n_seq_max`.
- Poprzednie źródło SGLang: [[sglang-hicache]].

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- Stary werdykt „nie warto, topka ma 1 slot” patrzył tylko na dekod jednego strumienia. Nasi agenci przez 37% czasu mają ≥ 2 żądania w locie (średnio 1,97), a serwer ma `-np 1` ([[2026-10-19-workload-omp]]:10). Drugie żądanie czeka w kolejce: K-106 zmierzył +2,6 s TTFT za resztą odpowiedzi A (`KOLEJKA-TESTOW.md:1071`).
- Wiele slotów odrzuciliśmy (K-086, `KOLEJKA-TESTOW.md:1167-1168`): pojedyncze żądanie −5…−17%, fan-out omp +11% ściany i **~2,4 GB stanu na slot**. Ten drugi koszt to dokładnie problem, który rozwiązuje jedna arena: stały podział pamięci na sloty i pule.
- Porównanie warstwa po warstwie: SGLang ma jedną arenę z kompaktowaniem dla KV, okna i stanu rekurencyjnego; llama-server ma `-kvu` (wspólny bufor KV dla sekwencji), ale stan GDN i checkpointy liczy osobno na slot; Enigma uruchamia zawsze `-np 1` (`app/engine/src/server/engine.ts:571`).
- Superfluid (adapter llama.cpp) robi to samo pragmatycznie: dla modeli rekurencyjnych jedna wspólna pula `max-batch × max-context`, ograniczona do 60% pamięci wolnej po wagach, a wyrzucone prefiksy idą do RAM ([[superfluid]], `docs/performance/benchmarks.md` w repo).
- Co bierzemy: przy powrocie K-086/K-061 i przy trybie „agent z subagentami” w Enigmie liczyć budżet pamięci jako jedną pulę, a nie „slot × pełny kontekst”; pierwsza próba to `-kvu` + mniejszy kontekst na slot.
- Czego nie bierzemy: samej areny SGLang (CUDA, Python, serwowanie wsadowe). Dla jednego strumienia na XTX dalej 0%.

## Powiązane
- [[sglang-hicache]]
- [[KOLEJKA-TESTOW]]
- [[2026-10-19-kv-tylko-w-ram]]
