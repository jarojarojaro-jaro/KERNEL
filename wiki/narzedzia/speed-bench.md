---
typ: narzedzie
tags: [narzedzia, benchmarki, spekulacja, pomiar, produkt]
aktualizacja: 2026-11-24
zrodlo: https://arxiv.org/abs/2604.09557; https://huggingface.co/datasets/nvidia/SPEED-Bench (karta v1.1, 2026-09-17); ~/KERNEL/product/research/21f-inferencex.md:45,91,106; ~/KERNEL/product/research/52-eagle4.md:56; ~/KERNEL/product/research/57e-splash-dflash.md:67; ~/KERNEL/product/research/15b-spekulacja-frontier.md:46; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:82; ~/KERNEL/wiki/REKORDY.md:16; ~/KERNEL/app/engine/src/server/bench.ts:3,65,99
status: aktualne
---
# SPEED-Bench (NVIDIA): wspólny standard pomiaru spekulacji, którym podają liczby wszyscy poza nami

**SPEED-Bench to zestaw danych i harness NVIDIA do mierzenia dekodowania spekulatywnego: 880 zróżnicowanych promptów w 11 kategoriach (akceptacja) i podziały „throughput” 1k–100k tokenów po 3 klasy entropii (prędkość w serwerze); prawie każde liczby draftera, które sprawdzaliśmy (EAGLE-4, Splash, DSpark, ISTA, golden AL AgentX), są podane w nim, a nasze `spec_sweep` (6 promptów PL/EN) nie jest z nimi porównywalne.**

## Co to jest
- **Podział „qualitative”:** 880 promptów, kategorie coding, math, stem, humanities, writing, summarization, roleplay, rag, multilingual, reasoning, qa; 18 źródeł; w każdej kategorii prompty wybrane tak, żeby były jak najbardziej różne (minimalne średnie podobieństwo kosinusowe embeddingów). Mierzy akceptację (AR, AL) per kategoria.
- **Podziały „throughput”:** 1k, 2k, 8k, 16k, 32k, od v1.1 też 100k tokenów wejścia; 3 klasy: low_entropy (kod), mixed, high_entropy (twórcze pisanie); w 16k–100k zadania debugowania kodu z InfiniteBench. Mierzą zysk przy różnej współbieżności.
- **Harness:** `NVIDIA/Model-Optimizer/examples/specdec_bench`, pod vLLM i TensorRT-LLM. Część promptów jest zamaskowana i dociągana ze źródeł przez harness. Licencja danych: NVIDIA evaluation dataset license.
- **Tezy pracy:** syntetyczne wejścia zawyżają zysk; optymalna długość draftu zależy od batcha; dane o małej różnorodności dają stronniczą akceptację; przycinanie słownika draftera ma pułapki.

## Gdzie go spotkaliśmy
- AgentX/InferenceX bierze z niego wymuszoną „golden AL” (coding): Qwen3.8-Flash-Next MTP4 2.47, K3 DSpark 3.78 (`21f-inferencex.md:45,106`).
- EAGLE-4 TokenSpeed 961.6 t/s: 88 rozmów / 117 tur SPEED-Bench (`52-eagle4.md:56`); Splash 27B na M5 Pro: SPEED-Bench kod (`57e-splash-dflash.md:67`); DSpark frontier: AL 3.25/2.90, high_entropy 2.44 (`15b-spekulacja-frontier.md:46`); ISTA MTP 54.2%: „llama.cpp speed-bench, 5 próbek na kategorię” (`15e-kwantyzacja-nowa.md:82`).

## Porównanie z naszym odpowiednikiem
| warstwa | SPEED-Bench | my |
|---|---|---|
| dane do akceptacji | 880 promptów, 11 kategorii, dobór na różnorodność | `spec_sweep`: 6 promptów PL/EN × 3 seedy (`REKORDY.md:16`); zestawy `copy`/`mvs` do lookupu |
| długi kontekst | 1k–100k, 3 klasy entropii | `long_ctx_bench`, T=0, 256 tokenów |
| język polski | multilingual bez skupienia na PL | mamy PL, oni nie — tu jesteśmy lepsi |
| aplikacja Enigma | — | benchmark „przed → po” na jednym syntetycznym tekście narracyjnym (`app/engine/src/server/bench.ts:3,65,99`) |

## Czego uczy i co bierzemy
- Nasze tok/krok i liczby drafterów z rynku są dziś w różnych walutach. Żeby uczciwie porównać MTP z EAGLE-4/DSpark/DFlash, trzeba puścić **ich** podział qualitative (choćby kategorie coding, math, writing, multilingual) przez nasz serwer i podać AL per kategoria obok `spec_sweep`.
- To samo w produkcie: przyrost „przed → po” w Enigmie mierzony na jednym tekście narracyjnym jest właśnie „syntetycznym wejściem o małej różnorodności”, przed którym ostrzega praca. Użytkownik od kodu zobaczy inny przyrost. Raport powinien mówić, na jakim rodzaju tekstu był pomiar.
- Kategoria zamiast średniej: pokazuje, gdzie drafter jest słaby (u nas proza PL i myślenie), zamiast jednej liczby.

## Powiązane
- [[agentx-harness]]
- [[raport-21f-inferencex]]
- [[serve-bench]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
