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

## Powiązane
- [[inkling-2-mini]]
- [[project-maya]]
- [[uncensored-ablacja-kierunku]]
