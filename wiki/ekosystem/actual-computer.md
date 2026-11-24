---
typ: ekosystem
tags: [ekosystem, konkurencja, nvidia]
aktualizacja: 2026-11-24
zrodlo: ~/KERNEL/product/research/15c-nowe-silniki.md:28-33,82-91,188-208,382
status: do-sprawdzenia
---
# Actual Computer (silnik „e”, relay)

**Firma z silnikiem „e” (host w asemblerze AArch64 + cubiny sm_103a, tylko DGX Station GB300) i relayem na AWS Nitro; na sprzęcie konsumenckim uruchamia vendored llama.cpp albo silnik „malibu”.**

- Deklaracje (własny `e bench`, warunki nieopublikowane): Nemotron 3.5 Super VL FP8 455 t/s przy 1 strumieniu i 8,046 t/s przy 128; sufit bez spekulacji ~452 / 4,469 t/s przy 7.1 TB/s, więc wynik wymaga MTP.
- Darmowo 100M tokenów/dzień przez relay (= 1,157 t/s non-stop).
- Do przejęcia: „output bitwise spec off” (batch-invariance jako wymaganie), `--spec-copy` (kopia z kontekstu wpięta w MTP), budżet czasu kroku i wycena kolejki, relay z atestacją TEE.
- Antywzorce: device-code login autoryzujący kod bez kliknięcia, instalatory `curl|bash` i `irm|iex` bez sumy i podpisu, telemetria OTLP domyślnie włączona.
- Zamknięty kod, ~3 osoby.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
aci-cpp (blog 2026-11-18, https://actual.inc/blog/in-search-of-perfection; kod: github.com/actual-computer/llama.cpp) to fork llama.cpp wewnątrz klienta Actual na Mac, DGX Spark i RTX. Werdykt 23.11 „nic bez kodu i liczb per technika” był zbyt wąski: kod jest publiczny, a lekcja dotyczy produktu i pomiaru.
- **Miara, którą wybrali: TTFT następnej tury** przy 8K–250K kontekstu (DGX Spark: 64K 0,97 → 0,78 s, 250K 2,10 → 1,79 s; ich poprzedni build 5,2 s). Nasz benchmark w Enigmie mierzy prefill 4096, dekod 256 i głęboki 32k (`app/engine/src/server/bench.ts:1-8`), ale nie tury z trafieniem w cache — a to główny czas agenta. U nas serwer topki: E4 8,0 → 1,6 s dopiero po `LLAMA_SERVER_CACHE_SHARE_MIN`.
- **Tabela „gdzie stoimy”**: każda platforma × obciążenie vs upstream, średnia geometryczna z min/max, buildy na zmianę na tej samej maszynie. Wzór na stronę Enigmy zamiast jednej liczby t/s.
- Zmiany w serwowaniu: prefill dzielony budżetem tokenów między sloty, równoległe próbkowanie, szybszy zapis cache promptu; spekulacja: weryfikacja kilku draftów za koszt jednego (ich MTP +4–38% nad MTP upstream).
- **Dystrybucja:** fork jedzie do użytkowników na 3 platformach. Enigma ma nasz silnik ROCm `enigma-rocm-gfx1100` z `distribution: local` (`app/engine/data/engines.json`), więc użytkownik AMD dostaje upstream — dokładnie to, czego Actual nie robi.
- Nadal antywzorzec: instalacja `curl | bash` i autoryzacja urządzenia linkiem.

## Powiązane
- [[magnitude]]
- [[firma-nvidia]]
- [[raport-15c-nowe-silniki]]
- [[app-prototyp-desktop]]
