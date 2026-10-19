---
typ: eksperyment
tags: [eksperymenty, pm4, awarie, rdna3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:210-425; /proc/vmstat (boot 0, 19.10 ~02:30); journalctl -k -b 0
status: do-sprawdzenia
---
# 2026-10-19: przyczyna resetów PM4 – brak PRIV=1 na GFX11 + ewikcje SVM (analiza CPU)

**Agent Pm4Fix (raport 17 §9, tylko CPU) wskazał najbardziej prawdopodobną przyczynę (H1′, `[INFERENCE]`): każdy `DISPATCH_DIRECT` naszej taśmy startuje fale z `COMPUTE_PGM_RSRC1.PRIV=0`, a GFX11 wymaga `PRIV=1` (obejście CWSR DEGFX11_12113, które CP robi sam tylko dla pakietów AQL); w połączeniu z ewikcją kolejek przez KFD w środku taśmy daje to SQC fault @0 i reset.**

Poszlaki (bez dowodu na GPU):
- faulty AQL (`moebench`, 16.10) mają `priv 1`, faulty taśmy `priv 0`;
- MES w R3–R10 za każdym razem nie umie zdjąć tej samej, najnowszej kolejki procesu (`doorbell=0x100a`, „Failed to evict queue 7”) – najpewniej kolejki taśmy;
- w R2 zawiesił się ADD_QUEUE (restore po ewikcji) ~110 ms przed timeoutem, czyli w chwili faultu;
- awarie dopiero po zapełnieniu `--cache-ram` 16 GiB; boot 0: `pgmigrate_success` 7 130 366 stron, `pswpout` 102 898, `restore_userptr_worker` >10 ms 64×.

Wyzwalacz: kopie HIP z pamięci stronicowanej zostawiają trwałe zakresy SVM ([[hip-kopie-stronicowane-zostawiaja-svm]]), kompakcja/swap ich stron ewikuje wszystkie kolejki procesu ([[kfd-ewikcja-kolejek-gfx11]]). Taśma sama w sobie ustawia przed każdym dispatchem wszystkie rejestry, które ten czyta – poprawka „wszystko re-emitować” nic by nie dała; brakuje obejścia GFX11 i detali zgodności z kfdtest/tinygrad (bez ORDERED_APPEND_ENBL, `COMPUTE_RESTART_X/Y/Z=0`, polityka cache IB 0) ([[gfx11-pm4-dispatch-priv]]).

Prototypy (`pm4-guard` @ `b7fb3fe85`, skompilowane, nieuruchomione): `GGML_HIP_PM4_WA=1` (samo PRIV) / `=2` (PRIV + zgodność, +5 dwordów/dispatch); `GGML_HIP_PM4_GUARD` także przy PM4=0 (zdarzenia z czasem, położeniem względem taśmy i przyrostem `/proc/vmstat`; `=2` z `UNMAP_FROM_GPU`); `GGML_HIP_PM4_EVICT_TEST_MS=<n>` – deterministyczna ewikcja SVM przez `madvise(MADV_DONTNEED)` na 2 MiB z `hsa_amd_memory_lock`.

Ranking naprawy: 1) `WA=2`; 2) `HSA_USE_SVM=0` albo `GPU_PINNED_MIN_XFER_SIZE` (usuwa główne źródło ewikcji); 3) `GUARD=1`; 4) IB w VRAM; 5) kolejka PM4 KFD zamiast pakietu vendor (jedyna kombinacja testowana przez AMD); 8) `GGML_HIP_PM4=0` (stan bezpieczny).

Testy GPU (czekają na decyzję użytkownika; build `b7fb3fe85`, jeden blok, `gpu-guard`, stop przy pierwszym faultcie):

| krok | konfiguracja | ryzyko |
|---|---|---|
| S1 | LFM tg128, PM4=0, `GUARD=2`, `EVICT_TEST_MS=100` (+ `HSA_USE_SVM=0`), greedy md5 | niskie |
| S2 | 241 requestów, PM4=0, `GUARD=2` – liczba i przyczyny ewikcji | niskie |
| S3 | S2 + `HSA_USE_SVM=0` / `GPU_PINNED_MIN_XFER_SIZE=1024`, koszt zapisu stanu i TTFT | niskie |
| S4 | LFM tg128, `WA=2`, `COOLDOWN_MS=0`, `EVICT_TEST_MS=50`, 2 min: ≥ 1000 ewikcji w taśmie, 0 faultów | średnie |
| S5 | jak S4 z `WA=0` – dowód przyczynowy H1′, **oczekiwany reset GPU** | wysokie; opcjonalny, osobna zgoda |
| S6 | produkcja, PM4 + `WA=2` + `GUARD=1`, 241 → ≥ 1000 requestów, ABBA | średnie |

Rekomendacja bez zmian: `GGML_HIP_PM4=0` do czasu S4 i S6; po S3 rozważyć `HSA_USE_SVM=0` niezależnie od PM4.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[2026-10-19-page-faulty-gpu-analiza]]
- [[raport-17-gpu-page-fault]]
- [[pm4-replay]]
- [[lekcja-test-wywlaszczenia]]
