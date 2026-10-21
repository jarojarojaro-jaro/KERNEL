---
typ: kernel
tags: [kernele, pm4, rocr]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:6-14,18-57,81-99; ~/KERNEL/qwen-opt/NOTES.md:372-376; ~/KERNEL/product/research/08-analiza-platformy-latek.md:14-21; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:135-136,473; ~/KERNEL/product/research/15a-monokernel.md:179-183,196,233-242; ~/KERNEL/product/research/16a-pm4-pdl.md:145-150; ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:142-150; komunikat Main do WikiIngest 2026-10-19; ~/KERNEL/product/research/17-gpu-page-fault.md:104-153; ~/KERNEL/product/research/17-gpu-page-fault.md:210-425; ~/KERNEL/product/research/37-proza-100.md:13-24; ~/KERNEL/product/research/54-mniej-granic.md:8-27
status: aktualne
---
# Replay grafu dekodowania jako bufor PM4 (0060, 0061, 0063)

**Przechwycony graf HIP jest przebudowany w jeden bufor poleceń PM4 wysyłany jednym pakietem AQL na własnej kolejce ROCr; granica między kernelami spada z ~2.75 µs do ~0.46–0.86 µs.**

Mechanizm (`ggml/src/ggml-cuda/hip-pm4.{cu,cuh}`, runda 4, 2026-10-14): węzły grafu stają się taśmą: deskryptory kerneli z loadera ROCr, kernargi z metadanych code object (własny czytnik msgpack), ukryte argumenty jak w ROCclr (reszta „fail closed”); kernargi w VRAM, IB w pamięci wykonywalnej. Kolejność ze strumieniem HIP po stronie hosta. Grafy z innymi węzłami idą starą drogą (`cudaGraphLaunch`). Te same kernele i argumenty, więc wynik bitowo identyczny.

Wynik (przeplatane):
- LFM llama-bench tg128: 3.887 → 3.424 ms/token (257.3 → 292.1 t/s); spec_sweep 259.3 → 293.6 t/s;
- Qwen MTP: 29.16 → 27.80 ms/krok, 103.7 → 108.8 t/s; Uncensored MTP 109.9 → 115.3;
- taśma LFM: 304 dispatche na token.

Bezpieczeństwo: 20 przebiegów testu, soak `pm4_soak.py` (~4 min na model) bez zawieszeń; pierwsza próba dała odwracalny page fault (IB musi być w pamięci wykonywalnej).

Wyłączniki: `GGML_HIP_PM4=0`; diagnostyka `GGML_HIP_PM4_DEBUG=1/2/3` (0061), bo rocprofv3 nie widzi dispatchy PM4. Ograniczenia: zależy od wnętrzności ROCr; **nie działa na Windows** (HIP na PAL), a bezwarunkowe `find_package(hsa-runtime64)` może łamać tam build.

## Następny krok: PM4-PDL (raport 15a, 2026-10-16)
Pomysł: taśma PM4 bez pakietów granicy (`CS_PARTIAL_FLUSH` + `ACQUIRE_MEM`) między parą producent → konsument; konsument (MMVQ n=1) najpierw ładuje wagi do VGPR, potem czeka na flagę `gen` ustawianą z release przez ostatni blok producenta (tickety już są w 0051/0053/0054/0056/0057). Zmierzony overlap bez granicy 0.24–0.35 µs (runda 4). Szacunek +5…+15% LFM przy ~1/4 kosztu megakernela, bitowo z definicji; ryzyko zakleszczenia, jeśli dispatcher nie wydaje grup roboczych po kolei – rozstrzyga mikrobench X1 (wymaga zgody na GPU). Zob. [[raport-15a-monokernel]].

PM4-PDL (16a, 2026-10-18): zamknięte – synchronizacja przez pamięć kosztuje prawie tyle co granica ([[lekcja-handoff-rdna3]]); `GGML_HIP_PM4_UB` (gałąź `pm4-pdl`) daje szybką górną granicę dla pomysłów „mniej granic”.

**Awarie (16–19.10, raport 17):** 8 resetów GPU w serwerze Qwen MTP (SQC fault @0 w taśmie, potem mode1 reset), kandydat: brak `PRIV=1` (obejście GFX11) przy ewikcji kolejki w środku taśmy `[INFERENCE]`; prototypy `GGML_HIP_PM4_WA`, `GUARD`, `EVICT_TEST_MS` (`b7fb3fe85`), testy S1–S6 ([[2026-10-19-pm4-priv-analiza]]); rekomendacja `GGML_HIP_PM4=0` w serwerach do czasu testu – decyzja użytkownika ([[2026-10-19-page-faulty-gpu-analiza]]).

## Aktualizacja 2026-10-21
- [[raport-37-proza-100]], [[raport-54-mniej-granic]], [[lekcja-nie-zabijaj-pm4-w-trakcie]].

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mikrobench-granicy-kernela]]
- [[pm4]]
- [[pm4-niewidoczne-w-rocprof]]
- [[lfm-runda-4-pm4]]
