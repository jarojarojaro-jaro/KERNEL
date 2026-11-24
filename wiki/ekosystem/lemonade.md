---
typ: ekosystem
tags: [ekosystem, serwowanie, produkt, amd, enigma]
aktualizacja: 2026-11-24
zrodlo: klon lemonade-sdk/lemonade @ 41736cb (2026-11-20) w ~/research/engines/lemonade (README.md:1-60; docs/dev/adding-a-backend.md:9-40; docs/dev/backends-reference.md:9-70; docs/dev/router-policy.md:1-50; src/cpp/resources/benchmark_forks.json:1-20); ~/KERNEL/product/research/silniki-2026-11-20/amd-runtimes.md:146-183; ~/KERNEL/product/research/03-silniki-i-stack.md:38,190-197,597,676
status: aktualne
---
# Lemonade (AMD): lokalny serwer z instalatorem, czyli najbliższy odpowiednik aplikacji Enigma

**Lemonade nie ma własnych kerneli: to serwer C++ (instalator Windows 10 MB), który pobiera właściwy silnik po wykryciu sprzętu, wystawia API OpenAI/Anthropic/Ollama i co noc mierzy regresje forków llama.cpp. 2026-11-20 oceniliśmy go zdaniem „reszta bez XTX”, choć robi to samo, co ma robić nasza Enigma.**

## Jak to działa (klon `41736cb`)
- **Backend opisuje się sam:** deskryptor (OS, rodziny GPU, tier, format) + klasa serwera w jednym folderze; router, CLI, `/system-info` i dokumentacja czytają ten sam rejestr (`adding-a-backend.md`). Nowy backend = jeden folder i trzy dopiski.
- **Trzy poziomy wsparcia:** core (opiekun, aktualizacja w tygodniu wydania upstreamu), experimental, guest (fork społeczności, bez gwarancji, w kontenerze/piaskownicy). Tier widać w API i UI. Forki pod Strix Halo (`nathanw`, `halobox`) są gośćmi.
- **Silnik po detekcji:** llama.cpp ROCm per rodzina gfx (gfx110X, gfx1151, gfx120X…), Vulkan, CUDA per sm, CPU; buildy ROCm z TheRock (`lemonade-sdk/llamacpp-rocm`, Windows gfx110X 506 MB).
- **Nocny dashboard regresji forków** (`bench.lemonade-server.ai/regressions`): rejestr forków w JSON, dopisanie forka bez kodu; runnery to Strix Halo. Przykład 2026-11-20, Qwen3.8-27B 4k na gfx1151: ROCm nightly 17,43, Vulkan 16,79, HRX 8,45 t/s.
- **Router modeli** (`collection.router`): reguły „pierwsza pasuje” (słowa kluczowe, długość, metadane typu zgoda), domyślny model, ślad decyzji.
- Testy każdego backendu w CI na prawdziwym sprzęcie (self-hosted runnery AMD).

## Porównanie z Enigmą (`app/engine`)
- Detekcja i katalog: Enigma ma lepszy model pamięci i ocenę (KV, MTP, zmierzone przepisy), Lemonade tylko listę wspieranych rodzin.
- **Dystrybucja:** u nas silnik ROCm gfx1100 ma `distribution: local` (`engine.ts:62,246`), więc użytkownik AMD dostaje zwykłe llama.cpp; Lemonade wysyła gotowe paczki ROCm dla każdej rodziny.
- **Regresje:** my mierzymy ręcznie w kolejce (`run-jobs.sh`), bez stałej serii co noc i bez publicznego wykresu.
- **Uczciwość wsparcia:** tier core/experimental/guest to gotowy język na „sprawdzone na naszej karcie” vs „nie sprawdzone” ([[lekcja-enigma-apu-jako-karta]]).

## Co bierzemy
1. Tier przy każdym silniku i karcie w katalogu Enigmy (zmierzone u nas / tylko teoria).
2. Nocny pomiar produkcji topki i forków na stałym zestawie promptów (kolejka, jeden job) z historią, żeby regresję widać było następnego dnia.
3. Paczka ROCm gfx110X do pobrania zamiast `local` — po bramce md5/KLD.

## Powiązane
- [[inference-stack]]
- [[silniki-inferencji-2026-11-20]]
- [[strata]]
- [[produkt-architektura]]
