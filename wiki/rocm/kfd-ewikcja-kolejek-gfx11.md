---
typ: rocm
tags: [rocm, kfd, mes, rdna3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:294-331,354-375
status: aktualne
---
# Ewikcja i przywracanie kolejek KFD + MES na gfx11 (Linux 6.8)

**KFD ewikuje wszystkie kolejki procesu przy unieważnieniu SVM lub userptr, ewikcji TTM i suspendzie; MES dostaje REMOVE_QUEUE, a przy restore ADD_QUEUE z tym samym MQD – pola dispatchu (`compute_pgm_*`, `user_data`, `restart`, `cp_hqd_ib_*`) zapisuje i odtwarza wyłącznie zamknięty firmware (raport 17 §9.2, 2026-10-19).**

| trigger | restore po | min. odstęp ewikcji |
|---|---|---|
| userptr | 1 ms (przeplanowanie `'R'`, dopóki pamięć nieważna) | brak |
| SVM | 1 ms | brak |
| TTM | 100 ms | 10 ms |

- Restore: `trap_en = !kfd_dbg_has_cwsr_workaround()` = 0 na gfx1100.
- `hipHostMalloc` i pule fine-grained ROCr to BO userptr na `MAP_SHARED` (w tym nasz IB) – kompakcja/swap ich stron daje ewikcję userptr.
- VM fault → `kfd_dqm_evict_pasid` → REMOVE kolejki z zatrzymanymi falami się nie kończy → timeout MES po 107–128 ms (R3–R10) → mode1 reset.
- Jedyny ślad ewikcji w `journalctl`: „hogged CPU” workerów restore (raport przy potęgach 2 przebiegów > 10 ms). Zdarzenia z czasem: [[kfd-smi-eventy]].
- AMD testuje CWSR (`KFDCWSRTest`, 10–1000 przerwań) i ewikcję TTM (`KFDEvictTest`) w kolejkach PM4 z PRIV=1 – nie DISPATCH_DIRECT w IB kolejki AQL.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[dekodowanie-page-fault-amdgpu]]
- [[gfx11-pm4-dispatch-priv]]
- [[hip-kopie-stronicowane-zostawiaja-svm]]
