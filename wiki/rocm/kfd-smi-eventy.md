---
typ: rocm
tags: [rocm, kfd, diagnostyka]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:131-148,206; ~/KERNEL/product/research/17-gpu-page-fault.md:384-393
status: aktualne
---
# Zdarzenia KFD SMI (`AMDKFD_IOC_SMI_EVENTS`) bez roota

**Proces może otworzyć własny `/dev/kfd` i przez `AMDKFD_IOC_SMI_EVENTS` dostawać zdarzenia swoich kolejek (bez roota): `QUEUE_EVICTION` z przyczyną (SVM, userptr, TTM, suspend), `QUEUE_RESTORE`, plus globalne `VMFAULT` i `GPU_PRE_RESET` (raport 17, 2026-10-19).**

- Maska przez `KFD_SMI_EVENT_MASK_FROM_INDEX`, zdarzenia jako linie tekstowe `"%x %lld -%d %x %d"`.
- Zastosowanie: strażnik `GGML_HIP_PM4_GUARD` (`7cd12f993`) omija taśmę PM4 przez 3000 ms po każdym eviction/restore i loguje evictiony trafiające w trwającą taśmę – dane do rozstrzygnięcia hipotezy H1 ([[raport-17-gpu-page-fault]]).

Formaty (Linux 6.8): `9 <boottime_ns> -<pid> <node> <trigger>` (eviction), `a <ts> -<pid> <node> [R]` (restore, `R` = przeplanowany), `b <ts> -<pid> @<page>(<pages>) <node> <trigger 0/1/2>` (UNMAP_FROM_GPU, tylko SVM); czas z `CLOCK_BOOTTIME`, emitowany przed ewikcją. Prototyp `b7fb3fe85` obserwuje je także przy `GGML_HIP_PM4=0` ([[kfd-ewikcja-kolejek-gfx11]]).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[dekodowanie-page-fault-amdgpu]]
- [[pm4-replay]]
