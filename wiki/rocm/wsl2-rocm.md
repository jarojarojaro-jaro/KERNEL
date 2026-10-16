---
typ: rocm
tags: [rocm, wsl2, windows]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/13-rocm-10.1.md:24,33,217-260; ~/KERNEL/product/PLAN.md:258; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:23,136
status: aktualne
---
# ROCm w WSL2 (tech preview 10.1)

**ROCm 10.1 działa w WSL2 przez ROCr + `librocdxg` → `/dev/dxg` → sterownik Adrenalin (WDDM), bez `/dev/kfd`; RX 7900 XTX jest na liście, ale nasz PM4 byłby tam po cichu pomijany.**

Fakty (raport 13 §6, z kodu `dxg/wddm/queue.cpp`):
- „Profiling, debugging, and KFD-dependent tooling are not supported in WSL2”; liczniki `hsaKmtPmc*` zwracają NOT_SUPPORTED;
- znany problem: zawieszenia przy asercjach po stronie urządzenia, wprost na RX 7900 XTX (TheRock#8791);
- pakiet vendor `AMD_AQL_FORMAT_PM4_IB` jest domyślnie pomijany, a sygnał zakończenia i tak dostaje 0 (dopiero `WSLKMT_VENDOR_PACKET=1` go przetwarza, i to tylko do ograniczonego rozmiaru). Taśma PM4 „kończy się sukcesem” bez wykonania kernela.

Wniosek dla łatki 0060: `pm4_enabled()` powinno wymagać `/dev/kfd` (predykat manifestu `runtime: rocr-kfd`); naniesione w PLAN §4.5. AMD w ROCm CLI wybiera w WSL2 Vulkan dla llama.cpp. Dla produktu: niski priorytet, tryb dla entuzjastów.

Chmura: SaladCloud udostępnia Radeony (7800 XT … 9070 XT) tylko jako kontener w WSL2, bez `/dev/kfd` i SSH; nadaje się do walidacji „czy działa u gracza”, nie do strojenia kerneli.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rocr]]
- [[hip-na-windows]]
- [[salad]]
- [[pm4-replay]]
