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
LoRA AtomicChat (rank 1, 44 MB) to w praktyce rzut y ← y − r(r·y) na wyjściu atencji, na sumie MoE i na embeddingu (sprawdzone na danych GGUF, cos 0,999998). Zamiast kernela Q4_K (3–5 dni) wdrażamy rzut w czasie działania w `ik2` (`IK2_ABLATE`) na pliku unsloth.

## Powiązane
- [[inkling-2-mini]]
- [[project-maya]]
- [[uncensored-ablacja-kierunku]]
