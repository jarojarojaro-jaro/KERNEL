---
typ: research
tags: [research, linki, bonsai, cpu, gemma, kv, cortheon, test-time-compute]
aktualizacja: 2026-11-28
zrodlo: panel JARO 2026-11-28 22:15 (5 linków X); github opensetlabs/openset-llm v0.3.4 (README, kernels/ptq1-vbmi.inc); RustingStudio/RustingStrata docs/BENCHMARKS.md; arXiv 2611.23035v2; llama.cpp b12811 src/models/gemma4.cpp:300-420; github ashhart/Cortheon v2.3.1 results/*.json
status: aktualne
---
# Linki 2026-11-28 wieczór: Bonsai na CPU 19,7 t/s, Gemma 4 K=V, Cortheon, V100 OC, „matematyka LLM”

**Żadna topka się nie zmienia: Bonsai na CPU (openset-llm) i RustingStrata dotyczą maszyn bez karty lub z za małym VRAM, Gemma 4 K=V nie jest bezstratne i nasze modele nie mają tej redundancji, podkręcanie pamięci V100 łamie zasadę fabrycznych ustawień, Cortheon to jakość przez wiele wywołań (bez zysku nad uczciwym best-of-4), a strona z matematyką to materiał edukacyjny bez liczb.**

| link | co naprawdę jest (liczby, warunki) | werdykt dla nas |
|---|---|---|
| swarogan: openset-llm (Bonsai-2-27B na CPU) | Ice Lake 8 vCPU / 8 GB, 24 prompty × 256 tok.: PrismML llama.cpp 3,16, ik_llama 4,58, openset 10,01, z MTP 19,67 t/s; EPYC 9354P 21,10 vs ik 7,74; bez AVX-512 tylko 6,1–7,7 i spekulacja ×1,27. Kernel PTQ1_0 (1,684 bpw) rozpakowany w rejestrach `vpmultishiftqb`+`vpermb`+`vpdpbusd`. Ich spekulacja nie jest bitowo zgodna (17/24 promptów identycznych) | lekcja dla Enigmy na samym CPU (Bonsai + AVX-512); na GPU nic nowego: PTQ1_0 vs Q2_0 na XTX już mierzone (prism bez MTP 53,2 vs 53,8, [[bonsai-2-5-uncensored]]) |
| swarogan (cytat): RustingStrata | 3060 12 GB, Qwen3.6-35B-A3B Q2_K_XL: 113,4 vs llama.cpp 66,5 (`-ncmoe 12`), z MTP do 160; eksperci równolegle na CPU i GPU, rozmieszczenie wg routingu; prefill remis | delta do [[rustingstrata]]: tylko gdy MoE nie mieści się w VRAM (przepisy 8–12 GB z dużym MoE) |
| yuvrajinfer: Gemma 4 K=V (arXiv 2611.23035) | vLLM, A100, Gemma 4 31B: bajty KV warstw globalnych 8192 → 5461 na token, zajętość przy 64k ×1,40, przepustowość przy 32k ×1,24 (więcej żądań), przy 64k ×0,96; krok +4,3…8,7%; tekst różni się w 20,4% generacji (2/432 odpowiedzi) | nie bezstratne; llama.cpp b12811 tylko pomija `wv`, KV trzyma podwójnie; Qwen3.8, Bonsai i Inkling mają osobne V, więc nic do odzyskania |
| unbug: V100 HBM 877 → 1053 MHz | narzędzie omija sterownik i podnosi zegar pamięci (+20% pasma) | odrzucone: zasada „karta fabrycznie, bez OC” ([[2026-10-20-karta-fabrycznie]]); lekcja tylko taka, że dekod rośnie z pasmem |
| ashxhart: Cortheon v2.3.1 | 4 implementacje równolegle + weryfikacja wykonaniem w piaskownicy; LCB v6 Hard 32 zadania: 12/32 → 23/32 (p=0,0034), ale best-of-4 z wyborem po testach publicznych 18/32 i różnica +5/−0 (p=0,0625, nieistotna); 6–8 wywołań zamiast 1; Mac + TensorFold, nie llama.cpp; zysk tylko tam, gdzie jest weryfikator (proza: gorzej) | wzorzec do harnessu agentów (testy repo jako wyrocznia), nie do silnika; nagłówek przesadzony |
| av1dlive: „entire math behind LLMs” | strona edukacyjna avidlive.ai/llm-math, bez pomiarów | bzdura dla nas: nauka podstaw, zero liczb |

## Na później
- Enigma na samym CPU z AVX-512: Bonsai PTQ1_0 przez openset-llm (MIT) jako tryb „bez karty”.
- Harness omp: best-of-N z wyborem po testach repo dla trudnych zadań kodowania (Cortheon bez przewagi nad uczciwym best-of-4).

## Test u nas
Nie da się dziś: nasze topki są na GPU w całości w VRAM (openset i RustingStrata celują w CPU / brak VRAM), Gemma 4 K=V nie dotyczy naszych modeli i nie jest bezstratne, OC wykluczone decyzją, Cortheon nie jest pomiarem silnika.

## Powiązane
- [[linki-2026-11-28-gdn-spekulacja]]
- [[bonsai-2-5-uncensored]]
- [[gemma-4]]
