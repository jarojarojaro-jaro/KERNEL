---
typ: llm
tags: [llm, modele, moe, looped-transformer, thinking-machines, unsloth, telegram]
aktualizacja: 2026-11-20
zrodlo: thinkingmachines.ai/news/inkling-2-mini (2026-11-20), HF unsloth/Inkling-2-Mini-GGUF, mainline llama.cpp 5f83714 (src/models/inkling2.cpp); link od właściciela (Telegram 23:29)
status: aktualne
---
# Inkling 2 Mini (Thinking Machines, 2026-11-20): MoE z pętlą warstw, jakość jak Qwen3.8-27B przy ~5× mniejszym odczycie na token

**Prawdziwy i ważny dla nas: według producenta jakość Qwen3.8-27B (AA Index 20,1 vs 20,1) przy ok. 3,3 GB odczytu wag na token zamiast ~16 GB.**

W kodowaniu agentowym jest lepszy (DeepSWE 48,2 vs 42,2%), więc na XTX powinien dekodować kilka razy szybciej [INFERENCE]. Do sprawdzenia na naszej karcie: K-133.

## Mechanizm
- 24 warstwy, 4 bloki po 6. **Dwa środkowe bloki liczą się 3 razy z tymi samymi wagami**, co daje 48 przejść warstw na token z 24 zapisanych.
- „Attention residuals”: każda warstwa sama miesza wyjścia wcześniejszych bloków. Między pętlami płynie „wiadomość” z bramką.
- MoE: 128 ekspertów, 8 aktywnych. 26,4B parametrów, 3,4B aktywnych na przejście, **5,4B efektywnie aktywnych** z pętlami.
- Atencja hybrydowa: lokalna (SWA) + globalna. Kontekst do 1M.
- Trenowany natywnie w NVFP4 (eksperty), 4 ostatnie warstwy w MXFP8, ~20 GB. Multimodalny (obraz → tekst). Apache 2.0.
- Pętla daje te same odpowiedzi przy krótszym rozumowaniu: 3703 → 1731 tokenów myślenia (1 vs 3 przejścia, GPQA).

## Liczby producenta (Inkling 2 Mini vs Qwen3.8-27B)
- AA Index v5: 20,1 vs 20,1. DeepSWE v1.1: 48,2 vs 42,2%. SWE-bench Pro v2 Hard: 77,9 vs 73,8%. SWE-bench Verified: 79,2 vs 77,8%.
- Terminal Bench 2.1: 71,6 vs 73,0%. MCP Atlas: 82,7 vs 77,3%. LongBench v2: 66,9 vs 52,3%.
- Słabszy na czacie wieloturowym (MultiChallenge 50,0%) i w instrukcjach z wieloma warunkami. Wiedza zgodna z rozmiarem (AA-Omniscience −8,6 vs −6,4).
- Mocno ułożony pod bezpieczeństwo („misbehavior” 9,8 vs 57,7%). Nasza produkcja to Qwen Uncensored, więc to inny charakter modelu.
- GGUF od Unsloth: UD-Q4_K_M 16,61 GB, KLD 0,0108 vs Q8, zgodność top-1 97,9%. UD-IQ4_XS 15,73 GB.

## Jabłka do jabłek: XTX i inne karty
- **Odczyt na token** [INFERENCE]: 5,4B × ~0,6 B (Q4_K_M) ≈ 3,3 GB. Środkowe warstwy są czytane 3 razy, bo nie mieszczą się w 96 MB Infinity Cache. Qwen3.8-27B czyta ~16 GB na token.
- **Sufit pasma dekodu:**
  - XTX (960 GB/s): ~290 t/s; realnie MoE na RDNA3 ~50–60% sufitu, czyli ~150–170 t/s. Qwen3.8-27B dziś ma 42 t/s bez spekulacji i 107–126 t/s ze spekulacją.
  - RTX 3090 (936 GB/s): podobnie.
  - 5060 Ti 16 GB (448 GB/s): ~135 t/s sufitu, ale UD-Q4_K_M (16,6 GB) się nie mieści; IQ3_XXS 11,7 GB się mieści.
  - Apple M5 Pro 48 GB: działa (demo producenta).
- **NVFP4 natywnie:** przyspieszenie tensorowe tylko na Blackwell (5060 Ti / 50xx: FP4). Na XTX, Ampere i Apple idzie przez GGUF (Q4_K) z KLD 0,011.
- **Silnik:** mainline llama.cpp ma architekturę `inkling2` (`src/models/inkling2.cpp` w klonie 5f83714 z 2026-11-20). **Topka (baza b11528) jej nie ma**, więc potrzebny rebase (K-056) albo port architektury. Brak głowicy MTP [INFERENCE: nie ma jej w karcie modelu], więc spekulacja tylko z lookupu albo z osobnego draftera.

## GGUF i wersje bez cenzury (stan 2026-11-21 03:00)
- **Oficjalnego GGUF od Thinking Machines nie ma.** Producent wydał tylko safetensors (NVFP4 + MXFP8, ~20 GB). Najbliżej oficjalnego jest `ggml-org/Inkling-2-Mini-GGUF` od zespołu llama.cpp (IQ4_NL 17,6 GB, Q8_0 27,8 GB, BF16). Najwięcej kwantów ma `unsloth/Inkling-2-Mini-GGUF` (od UD-IQ1_S 7,8 GB do UD-Q8_K_XL 22,9 GB) razem z drafterem **DSpark** (`dspark-Inkling-2-Mini-Q8_0.gguf`, 0,40 GB) do spekulacji.
- **Wersje bez cenzury:**
  - `AtomicChat/Inkling-2-Mini-Uncensored-GGUF`: AD-Q4_K 16,53 GB (KLD 0,0115 do BF16, top-1 95,6%) i AD-IQ3_S 13,34 GB, plus LoRA rank-1 (44 MB) na dowolny GGUF ich bazy. Według autorów 0/8 i 0/104 odmów, perpleksja +0,3%, ale KL pierwszego tokenu nie przeszło ich progu (0,375 > 0,10).
  - `OpenUncensored/Inkling-2-Mini-Uncensored`: abliteracja tylko wyjść atencji, MMLU 78,95 → 79,47%. Tylko safetensors, bez GGUF.
  - Do tego `JoaoZaokk/Inkling-2-Mini-Heretic-GGUF` i `IndrasMirror/...-XQ-Uncensored` (bez opisu, nie sprawdzone).
- **Silnik:** pliki Unsloth i AtomicChat wymagają PR [#32695](https://github.com/ggml-org/llama.cpp/pull/32695) (Unsloth, „looped arch”, otwarty, commit `6196d98`). Master ma #32694 dla plików ggml-org.
- **Wybór na XTX (24 GB):** AtomicChat AD-Q4_K 16,5 GB (bez cenzury, zostaje ~6 GB na KV i draft) plus DSpark Q8_0. Alternatywa z najlepszą jakością w 24 GB: UD-Q4_K_XL 17,6 GB (KLD 0,0107). UD-Q8_K_XL 22,9 GB zostawia za mało miejsca na kontekst. Pobieranie AD-Q4_K i DSpark trwa (~75 min), build PR #32695 dla gfx1100 też.

## Lekcje
- Pętla warstw to nowy wymiar kompromisu jakość / pasmo: mniej wag, więcej obliczeń na wagę. Dla dekodu ograniczonego pasmem (batch 1) oznacza to więcej jakości na GB/s, dopóki pętla nie mieści się w cache.
- ~~Kernel MoE, który trzyma wagi w LDS/L2 przez 3 przejścia~~ — **nie działa** (Gemini ink-r1, 2026-11-21). Jedno przejście 12 warstw rdzenia czyta ~550–600 MB, więc przy następnym przejściu tych wag już nie ma ani w 96 MB Infinity Cache, ani w L2. Przejścia idą po kolei przez wszystkie 12 warstw, a nie po 3 razy ta sama warstwa.
- **Dekod przy batch 1 ogranicza liczba kerneli, a nie pasmo.** Według mapy kosztów Gemini graf ma ~7550 uruchomień kerneli na token. Na samych granicach kerneli to 12–19 ms, a odczyt wag to tylko ~4,4 ms, więc wychodzi ~41–56 t/s. Pierwszy pomiar społeczności na XTX daje 33,9 t/s (LocalMaxxing, Q3_K_XL, llama.cpp, bez spekulacji), co pasuje do tego szacunku. Dźwignie: taśma PM4 (granica kernela 3,6 → 0,5–0,9 µs) i fuzje w stylu vLLM (niżej).

## Pierwszy pomiar na XTX (2026-11-21, eco 2200)
- **AtomicChat AD-Q4_K, stock PR #32695:** tg64 **26,9 t/s**, pp512 1333, pp2048 1125. Czat: dekod ~26 t/s, prefill 887 t/s przy 2k. Qwen3.8-27B ma dziś 42 t/s bez spekulacji i 107–126 t/s z nią.
- **Mimo ~5× mniejszego odczytu na token Inkling jest dziś wolniejszy od Qwen.** Liczba kerneli (~7700 na token) zjada wszystko, co daje małe MoE. To lekcja dla każdej karty: przy małych, głębokich modelach wąskim gardłem przy batch 1 jest narzut uruchomień i synchronizacji, nie pasmo. Na GB200 ten sam model ma 3,85 ms/krok, a jego sufit pasma to ~0,4 ms.
- Pierwsze dźwignie (duet Kernel + Gemini, `DUO-INKLING.md`):
  - INK_FUSE: +14,5% (zmienia tekst, KLD w toku);
  - PM4: tapa odrzucona przez kernel rocBLAS w grafie;
  - DSpark: niezgodny rozmiar słownika z plikiem AtomicChat.

## Punkty odniesienia społeczności (zwiad 2026-11-22)
- **XTX bez spekulacji: 93,6 t/s** (Maya v1.1.73, UD-Q4_K_XL, LocalMaxxing verified). My: 49,5 t/s po rundach 1–6 duetu, czyli Maya jest 1,9× szybsza. To realny cel i wzór (K-134).
- **Z DSpark:**
  - RTX 3090: 290,8 t/s (vLLM, NVFP4, n=7, verified);
  - RTX 5090: 440,5 t/s (sglang, n=8, średnio 3,74 tokenu na krok, verified);
  - R9700: 81,8 t/s (llama.cpp unsloth, n=7, niezweryfikowane).
- Lekcja: 250–300 t/s ze spekulacją na karcie klasy 3090/XTX jest osiągalne, ale tylko z silnikiem, który ma mało uruchomień kerneli na token.

## Delta 2026-11-21 (zwiad): vLLM day-0
- **Źródło:** [blog vLLM](https://vllm.ai/blog/2026-11-20-inkling2-mini) (Inferact, Thinking Machines, NVIDIA).
- **Szczegóły modelu:**
  - prelude: warstwy 0–5, rdzeń: 6–17 (×3), coda: 18–23;
  - **każde przejście startuje z wyjścia prelude**, a poprzednie przejście widzi tylko przez „wiadomości”: 48 odczytów na token, każdy ze sterownikiem rank-64 (`out = (1−tanh(W_f·h))·in + tanh(W_g·h)·msg`);
  - **48 cache KV i 48 cache stanu konwolucji**: każde przejście ma własny;
  - 20 warstw SWA i 4 pełne, 24 głowy Q i 8 głów KV, hidden 2304, 128 ekspertów (top-8) w NVFP4, w ostatnich 4 warstwach MXFP8;
  - DSpark (3 warstwy) czyta stany z 4 wizyt: prelude, przejście 2, przejście 3 i wyjście. vLLM używa 7 tokenów draftu z próbkowaniem probabilistycznym.
- **Fuzje vLLM** (wzór dla nas na każdej karcie):
  1. 4 odczyty wiadomości warstwy w jednym kernelu attention-residual;
  2. wagi 4 sterowników ułożone w stos, więc down i gain/forget idą jako batched GEMM;
  3. normy RMS sterowników w jednym kernelu;
  4. scalanie z bramką połączone z RMSNorm następnej podwarstwy, w FP32 bez FMA;
  5. konwolucja, residual, attn-res mix i RMSNorm podwarstwy w jednym kernelu.
- **Liczby (GB200, TP1, kontekst 4K, sam forward):**
  - krok dekodu przy batch 1: 1 przejście 1,51 ms, 2 przejścia 2,67 ms, 3 przejścia 3,85 ms (≈ 260 t/s bez spekulacji);
  - przy batch 32: 3,81 / 5,92 / 8,11 ms;
  - każde przejście kosztuje ~1,17 ms, czyli rdzeń to ~90% kroku.
- **Jabłka do jabłek:**
  - GB200 ma ~8 TB/s, a XTX 0,96 TB/s;
  - na GB200 krok 3,85 ms też jest daleko od sufitu pasma (~0,4 ms), więc nawet vLLM ze wszystkimi fuzjami jest ograniczony liczbą kerneli i synchronizacją;
  - dla XTX realny cel to ~6–8 ms na krok (125–165 t/s) [INFERENCE], przy dziś szacowanych ~20–25 ms;
  - na Apple to samo: oMLX 0.8.2 dodał Inkling 2 Mini, liczb brak.
- **Checkpoint `TML-d24-varloop-research`:** liczbę przejść można ustawić (1–3+). To inny model, nie produkcja, ale dobry do nauki o kompromisie jakość/prędkość (dział `llm/`).

## Powiązane
- [[KOLEJKA-TESTOW]] (K-133)
- [[ZRODLA]]
