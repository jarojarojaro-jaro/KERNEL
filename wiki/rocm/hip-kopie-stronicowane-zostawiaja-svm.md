---
typ: rocm
tags: [rocm, hip, svm, pamiec]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:333-375
status: aktualne
---
# Kopie HIP z pamięci stronicowanej zostawiają zmapowane zakresy SVM

**CLR kopiuje pamięć stronicowaną ≥ 64 KiB (develop) / 1 MiB (ROCm 7.0.0) przez „pin” w kawałkach po 32 MiB; libhsakmt rejestruje to przez SVM API (`HSA_USE_SVM` domyślnie, `ACCESS_IN_PLACE`), a unlock zakresu nie usuwa – każdy bufor stanu `--cache-ram` (520 MiB) zostaje zmapowany na GPU do `munmap` (raport 17 §9.3, 2026-10-19).**

Skutek: migracja przez kompakcję, swap, split THP albo madvise tych stron idzie przez `svm_range_evict` → `kgd2kfd_quiesce_mm` (XNACK off) i ewikuje wszystkie kolejki procesu asynchronicznie, w środku taśmy. Boot 0 (18.10 20:27 → 19.10 ~02:30): `pgmigrate_success` 7 130 366 stron (~27 GiB), `compact_daemon_wake` 57, `pswpout` 102 898, `thp_split_pmd` 441; RAM 62 GiB, swap 7 GiB.

Obejścia: `HSA_USE_SVM=0` (rejestracja przez BO userptr zwalniane przy unlock) albo `GPU_PINNED_MIN_XFER_SIZE=<MiB>` (kopie przez staging, koszt czasu zapisu stanu – do zmierzenia, S3); w kodzie stały bufor pośredni. `mlock` nie pomaga (kompakcja i tak przenosi strony), mniejsze `--cache-ram` tylko zmniejsza ryzyko.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[kfd-ewikcja-kolejek-gfx11]]
- [[2026-10-18-cache-promptu-agenta]]
- [[2026-10-19-pm4-priv-analiza]]
