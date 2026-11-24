---
typ: ekosystem
tags: [ekosystem, maya, inkling, spekulacja, hip]
aktualizacja: 2026-11-23
zrodlo: kod Maya 1.1.73 na jaroserverai `~/k134/maya/src` (src/ik2/ik2_main.cu, ik2_kernels.cu, ik2_rdna.inc, src/spec/suffix_drafter.cpp, INKLING2.md); logi `~/k134/*` (K-134); analiza podagentów MayaT07 i MayaQ4K 2026-11-23
status: aktualne
---
# Maya `ik2`: jak silnik Inkling 2 Mini jest 3× szybszy od nas przy T=0,7 na XTX

**Maya (`maya-ik2`, @alesha-pro i in.) na XTX z plikiem unsloth: kopie 111,6, T=0,7 80,6, długi 2k 77,8 t/s, prefill 3398 t/s (K-134, 2026-11-23); przewaga przy T=0,7 to nie lepsza spekulacja, tylko kontroler, który wyłącza zgadywanie, gdy się nie opłaca (~2,3×), i szybszy dekod (~1,33×: 82 vs nasze ~61,6 t/s).**

## Mechanizmy (plik:wiersz w `~/k134/maya/src/src/ik2/`)
- **Kontroler `SpecCtl`** (`ik2_main.cu:3142-3221`): co krok porównuje oczekiwane tokeny / zmierzony czas dla zwykłego tokenu, okna lookupu i okna draftera (`(1−a^B)/(1−a)/c[B]` vs `1/c_plain`, akceptacja z zanikiem 0,85, próba co 8 tokenów). U nas DSpark przy T=0,7 zbija 61,6 → 26,8 t/s, bo zawsze zgaduje.
- **`--drafting on` bez pliku draftera = tylko prompt lookup** (trigramy, dopasowanie 3–32, `src/spec/suffix_drafter.cpp:63-87`); metryki `"speculation":["Lookup"]`. Drafter Mayi tylko `mtp.safetensors` (`ik2_draft.cu:56,74`).
- **Weryfikacja przy T>0:** point-mass speculative sampling, rozkład = celu (`ik2_main.cu:3243-3252,3300-3328`); kandydaci top-1000 liczeni na GPU, bo „200k logitów + sort = 0,8 ms/token” (`ik2_kernels.cu:2392-2440`).
- **Dekod:** jeden graf na token na całą sesję (pozycja w buforze GPU, stałe splity atencji, `ik2_main.cu:2659-2687`), graf na szerokość okna weryfikacji; **~757 uruchomień/token** (u nas ~2101), ~12 na wizytę warstwy, bez kerneli trwałych.
- **Prefill:** cały prompt 2048 w jednym przebiegu, MoE na WMMA z kafelkami 32 wierszy jednego eksperta (`ik2_rdna.inc:78-130,437-462`), hipBLASLt strojony per kształt, flash attention WMMA z bias/sink/oknem.
- **Ograniczenie:** eksperci tylko NVFP4, Q8_0, Q5_K, Q6_K, IQ3_XXS, IQ4_XS (`ik2_kernels.cuh:427`); plik AtomicChat (Q4_K/Q5_0) odrzucany (`ik2_main.cu:5011`).

## Do przeniesienia do naszego silnika (ranking)
1. Kontroler spekulacji w serwerze (koszt × akceptacja, próba co 8) — T=0,7 26,8 → ≥ dekod bez zgadywania.
2. Prefill: `-ub 2048` od razu; potem grupowany MUL_MAT_ID na WMMA.
3. Kandydaci próbkowania na GPU przy T>0.
4. Stały graf na szerokość okna (u nas kroki DSpark idą bez grafu: captures_skipped 595).
5. Fuzje do ~16 uruchomień na wizytę.

## Wersja bez cenzury w Mayi
LoRA AtomicChat (rank 1, 44 MB) to w praktyce rzut y ← y − r(r·y) na wyjściu atencji, na sumie MoE i na embeddingu (sprawdzone na danych GGUF, cos 0,999998). Zamiast kernela Q4_K (3–5 dni) wdrożyliśmy rzut w czasie działania w `ik2` (`IK2_ABLATE`, łatka `qwen-opt/inkling/maya-ik2-ablate.patch`, 2026-11-23): bez zmiennej wynik bit w bit jak przed (md5 f83b4c50), z nią odmowy 7/8 → 0/8, dekod −2…−5%, prefill −1%; działa jako czat :18796.

## Nasze przyspieszenie na gfx1100 (2026-11-23)
- Profil: 825 uruchomień/token, 11,34 ms kerneli; Q8_0 GEMV 23%, eksperci 30%, małe iloczyny FP16 (router, sinki) 8,6%.
- `IK2_HIP_MVF16=1`: pętla „jedna fala na wiersz” rozwinięta z loadami na początku — router 14,8 → 2,9 µs, sinki 15,3 → 3,0 µs (te same bity).
- `IK2_HIP_EXPV=1`: eksperci NVFP4 jeden wiersz na falę, x w rejestrach, wskaźniki w przestrzeni globalnej + `sched_barrier` — gate_up 567 → 650 GB/s.
- Razem: dekod bez draftera Q6 77,6 → 91,2 t/s (+17,5%), długi 2k 75,0 → 86,2; prefill bez zmian; md5 logitów identyczne.

- Runda 2 (2026-11-23): `IK2_HIP_COMB` (combine atencji 32 odczyty naraz), `PCONV` (loady najpierw w proj_conv), `FUSE` (router + wybór ekspertów w jednym launchu, „ostatni blok robi resztę”, 825 → 777 launchy), `LGD` (loop gates load-first) → czat T=0,7 91,3 → 94,5, długi 2k 86,4 → 93,5; dalej bez 100. Lekcje: przerwa między kernelami w grafie na gfx1100 ~2 µs i zmienne CLR jej nie skracają; ręczne rozwinięcie z akumulatorem 0 zmienia fma (pomaga `asm volatile("" : "+v"(acc))`).

- Runda 3 (2026-11-23): **wagi czytane nietemporalnie** (`__builtin_nontemporal_load`, `IK2_HIP_NT=15`) — ~3,7 GB wag na token przestało wypychać z cache małe wektory wejścia; dekod +9%, atencja 0,85 → 0,54 ms/token (choć sama wag nie czyta). Czat T=0,7 94,5 → **104,3**, długi 2k 93,5 → **100,8 t/s**, bit w bit. Lekcja na każdą kartę: przy n=1 wagi czytane raz na token streamować z pominięciem cache.

## Maya v1.1.75 (2026-11-23, PR #1154 @needmorevram, `4d4371c`)
- Drafter DSpark wczytywany z GGUF (`dspark-Inkling-2-Mini-Q8_0.gguf`, który mamy), krok draftera jako jeden graf CUDA, okno weryfikacji z gęstymi iloczynami na kilka tokenów naraz (`mv_q8p_cols`) i atencją czytającą klucze raz dla całego okna (`attn_decode_mma_win`): krok z oknem 5 na 3090 25,5 → 17,6 ms (drafty 2,5 → 1,7, okno 22,2 → 15,7), logity bit w bit jak ścieżka jednego tokenu (`docs/INKLING2.md`).
- Próbkowanie Gumbel-max: szum zależy tylko od zapytania, pozycji i tokenu, drafter losuje z tym samym szumem → rozkład celu dokładnie, a akceptacja przy T=1 (nowy kod) 58 → 68%. Te same tokeny z draftingiem i bez.
- 3090, greedy, z / bez: nowy kod 201 / 124, edycja 210 / 124, proza 135 / 124 t/s; serwer nowy kod 207, T=0,7 209. `--drafting auto` mierzy raz, co szybsze.
- Dla nas: w 1.1.73 oficjalny drafter na XTX przegrywał przy T=0,7 (79 vs 94); w 1.1.75 tańsze okno i wspólny szum mogą to odwrócić → K-136 (stock 1.1.75 vs nasza produkcja, potem hipx14 przeniesione na 1.1.75).
- AtomicChat AD-Q4_K (eksperci Q4_K + Q5_0) dalej nieobsługiwany w 1.1.75 (`block_values`) → K-137, nasze kernele.

## Wyścig Kernel vs Gemini, runda 1 Kernela (2026-11-24, gałąź `kern-maya`, AtomicChat AD-Q4_K, XTX)
- 4 podagentów, 16 przełączników `IK2_K_*` (domyślnie wył.), test kerneli 487 ok; `IK2_K_WEXP` dla Q8_0 nie daje tych samych bitów na gfx1100 (fuzja FMA zależy od otoczenia kodu) → Q8_0 wyłączone z WEXP.
- **Czat T=0,7 (rep2, mediana 5):** lookup bez przełączników 112,9; + kernele gęste `IK2_K_DMV` 113,0; + fuzje `IK2_K_L*` 112,9–113,0; L+D 113,6 (+0,6%, w szumie). DSpark wymuszony: 102,2 → 106,7 ze wszystkimi przełącznikami okna (+4,4%), ale dalej poniżej lookupu.
- **Profil (rocprofv3, 56 tokenów, bez zgadywania):** 705 → 547 uruchomień/token (−22%), ale kernele zajęte 7572 → 7786 µs (scalone kernele liczą więcej), a bez profilera prędkość 112,0 → 112,1 t/s. **Lekcja: w grafie na gfx1100 mniej uruchomień nie przyspiesza, gdy scalony kernel liczy coś ponownie; przerwy w profilerze są większe niż w zwykłym biegu.**
- Gdzie idzie czas tokenu (bez L/D): eksperci gate_up Q4_K 32 µs × 48 = 1,53 ms (~750 GB/s, 78% pasma), down Q5_0 19 µs × 48 = 0,91 ms (~770 GB/s), q|k|v|r|gate Q8_0 27 µs × 40 = 1,08 ms (~780 GB/s), głowica 545 µs (~900 GB/s), atencja 12 µs × 40 = 0,50 ms, małe kernele (norma, bramki pętli, splot) ~1,5 ms; zajętość kerneli 74% czasu w profilerze. Odczyt wag ~3,8 GB/token = 3,96 ms przy 960 GB/s, czyli dziś ~44% sufitu.

## Powiązane
- [[inkling-2-mini]]
- [[project-maya]]
- [[uncensored-ablacja-kierunku]]
