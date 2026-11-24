---
typ: research
tags: [research, silnik, enigma-turbo, hipfire, llama-cpp, vllm, sglang, exllamav3, tensorrt-llm, gdn, pm4]
aktualizacja: 2026-11-24
zrodlo: 6 agentów Kernela na klonach z 2026-11-20 (~/research/engines, 20 silników); pełne notatki product/research/silniki-2026-11-20/
status: aktualne
---
# Silniki inferencji 2026-11-20: co bierzemy do Enigma Turbo (język zostaje C++/HIP)

**Werdykt: zostajemy przy C++20 + HIP. Żaden DSL (Mojo/MAX, TileLang, HipKittens, Triton, MLC) nie ma na gfx1100 szybszych kerneli Q4_K/Q6_K. Nasze trzy luki do produkcji tłumaczą konkretne techniki, które mają inni.**
- **Długie prompty, 95–99 vs 140–159 t/s.** Nasza attention weryfikacji czyta K/V osobno dla każdego (głowa q, token). SGLang przy 8k czyta K/V raz dla T tokenów × 6 głów: 3,5 → 0,24 ms na warstwę. hipfire #989: +24% przy 39K, +57% przy 101K.
- **Prefill, 848 vs 882–933 t/s.**
  - GDN liczony token po tokenie zajmuje 11% prefillu (zmierzone: 271 z 2480 ms).
  - Chunkowany GDN istnieje w llama.cpp (PR #29353, wyłączony na gfx1100), w vLLM (`rdna35_gdn_chunked.cu`) i w FLA.
  - ExLlamaV3 używa f16 GEMM; port na XTX zgłasza ~1180–1200 t/s.
- **Dekod.** Taśma PM4 zamiast grafu HIP skraca granicę kernela z 3,6 do 0,5–0,9 µs. hipfire na XTX 27B: 53,4 → 62,5 t/s (×1,17); topka: +6,4%.
- **T=0,7, 72 vs 92 t/s.**
  - Spekulacja: cięcie łańcucha kalibrowane online (ExLlamaV3), block verification (TRT-LLM), DFlash2 (H200: MTP 178,5 → 236,1 t/s).
  - Ogon lookup W=16 potwierdzony z zewnątrz: hipfire +40% na kopiach.

## Ranking (pełna tabela 13 dźwigni: product/research/silniki-2026-11-20/RAPORT.md)
1. **Attention weryfikacji GQA**: ten sam kernel dla dekodu i weryfikacji, bit w bit. 3–4 dni.
2. **Szybszy `k_gemv_wide` + ogon W=16**: wzorzec few-row MMQ z llama.cpp #31533 (8 kolumn ×1,17–1,42, spec 3090 Ti +35%).
3. **GDN prefillu**: najpierw więcej bloków (dziś 48 bloków na 96 CU, 4 bariery na token), potem chunk. Szacunek +7–13%.
4. **Taśma PM4** (port `hip-pm4.cu` z topki): +4–7% dekodu, z procedurą bezpieczeństwa z raportu 17.
5. **Polityka spekulacji** liczona kosztem cyklu + autotune (Gemini); prefix cache stanu GDN (vLLM/SGLang).

## Architektury (zakres: wszystkie firmy)
- **AMD RDNA3 (XTX):** wszystkie dźwignie.
  - PM4 i bariera trwałej siatki (ignite: 0,36–0,41 µs) to specyfika AMD.
  - TileLang na gfx11 ma tylko WMMA f16.
- **AMD RDNA3.5/RDNA4 i CDNA:** chunkowany GDN w llama.cpp jest włączony tylko tam (gfx1151 od 2048 tok., CDNA z MFMA). Megakernel Qwen3.8-27B na MI355X osiąga ~1100 tok/s (MXFP4, stratny).
- **NVIDIA:**
  - PDL tylko na sm90+ (z naszych kart wyłącznie 5060 Ti): +2–3% na qwen35 27B (llama.cpp #22522).
  - Few-row MMQ działa na Ampere+.
  - DFlash2 mierzony na H200.
- **Apple, Intel, Tenstorrent:** żaden z badanych silników nie miał dla nich nowych technik batch-1. Wzorce (weryfikacja GQA, chunkowany GDN) są ogólne. [INFERENCE]

## Lekcje
- **Nasza największa luka nie leży w GEMV, tylko w attention weryfikacji.** Koszt T tokenów × 24 głowy rośnie z kontekstem, czego nie widać w profilu krótkiego promptu.
- **Bierzemy gotowe, sprawdzone kernele z produkcji** (MMQ: prefill 624 → 848 t/s w jeden dzień), zamiast pisać od zera.
- **Research przez 6 równoległych agentów na lokalnych klonach zajął 13 min.** Gemini Neon na tym samym zadaniu zużył limit (3,2 mln tokenów) przed zapisem czegokolwiek.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
- **Rama się zmieniła:** ranking był pisany „do Turbo”, a Turbo został odłożony tego samego dnia (`wiki/log.md:580`); dźwignie kernelowe idą teraz do duetu llama.cpp. Zdanie „vLLM i SGLang na RDNA3 są wolniejsze od Turbo (29–47 vs 45,9 t/s)” (RAPORT.md:13) mówi tylko o kernelach; ich przewagą są algorytmy serwera (`vllm-sglang.md:84`), i tego się uczymy.
- **vLLM / SGLang jako serwer (nasz odpowiednik: topka na :8080 i proxy Enigmy):**
  - Cache prefiksu dla hybrydy GDN: vLLM trzyma stan na granicach bloków i dodatkowo **w miejscu, gdzie poprzednie zapytanie z tym prefiksem się skończyło** (`--enable-mamba-shared-prefix-checkpoint`, punkt zapisany w trakcie prefillu bez osobnego przebiegu, `checkpoint.py:21-60`); SGLang robi copy-on-write stanu, pamięta punkt rozwidlenia i co 256 tokenów dekodu zapisuje stan (`mamba_track_interval`) (`vllm-sglang.md:45-48`).
  - U nas: checkpoint stanu Qwena kosztuje ~94–104 ms × 2 na prompt (`STAN-PRAC.md:46`), a obce zapytanie wyrzucało cache agenta, aż dodaliśmy `CACHE_SHARE_MIN=1024` (8,0 → 1,6 s). Punkt rozwidlenia i zapis co 256 tok. to gotowe odpowiedzi na edycję ostatniej wiadomości i retry agenta (TTFT wielu tur).
- **ExLlamaV3 / TensorRT-LLM:** poza kernelami — TRT-LLM ma „overlap scheduler” (host szykuje krok n+1, gdy GPU liczy n), SpeculationGate (wyłącza spekulację, gdy akceptacja spada) i osobne grafy dla greedy / temperatury / pełnego próbkowania (`exllama-tensorrt.md:37-49`). ExLlamaV3 trzyma punkty kontrolne stanu GDN w RAM i na dysku i wyłącza grafy na ROCm (węzeł grafu HIP nie startuje szybciej od zwykłego kernela, +2 MB na każde łatanie, `exllama-tensorrt.md:22-31`) — zgodne z naszym pomiarem ~3 µs na granicę kernela w grafie HIP ([[hip-graph-narzut]]).
- **Sprzeczność do zapamiętania:** port f16 GEMM prefillu ExLlamaV3 na XTX deklaruje ~1180–1200 t/s, a nasz f16 GEMM WMMA w Turbo przegrał o 31% (`wiki/log.md:562`); liczba portu nie jest naszym pomiarem. PR-y RDNA3 #547–549 dalej otwarte (API GitHub, 2026-11-24).
- **hipfire / Strata / TensorFold / Lemonade:** hipfire #989 (weryfikacja WMMA split-K na gfx1100) scalony 2026-10-26, wydanie v0.4.7 (2026-11-15). Lemonade to nie „reszta bez XTX”, tylko najbliższy odpowiednik aplikacji Enigma: tier wsparcia backendów, paczki ROCm per rodzina gfx, nocny dashboard regresji forków ([[lemonade]]). hipfire sprawdza poprawność testem jakości, nie bit w bit — inna polityka niż nasza ([[2026-11-05-tylko-bezstratne]]).
- **Lekcja:** research silników ocenia też serwer, cache, politykę spekulacji i dystrybucję, a nie tylko kernele dla jednej karty.

## Powiązane
- [[enigma-turbo-gemini-2026-11-20]]
- [[ZRODLA]]
