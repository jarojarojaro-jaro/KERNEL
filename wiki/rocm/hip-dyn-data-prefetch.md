---
typ: rocm
tags: [rocm, hip, prefetch]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15a-monokernel.md:28,91,265; /opt/rocm/include/hip/hip_runtime_api.h:605,1670-1700,2116
status: aktualne
---
# HIP DynDataPrefetch (prefetch L2 przed kernelem)

**`hipLaunchAttributeExtDynDataPrefetch` (prefetch regionów do L2 przed startem kernela) jest w HIP 7.15 u nas, ale ROCr zwraca 0 regionów dla wszystkiego poniżej gfx12.5, więc na gfx1100 nie działa.**

- Nagłówek: `hipExtDynDataPrefetchRegion`, `hipExtDynDataPrefetchTemporal`, atrybut urządzenia `hipDeviceAttributeMaxDynDataPrefetchRegions`.
- ROCr (`amd_gpu_agent.cpp:2734-2740`, rocm-systems): 0 regionów poniżej gfx12.5 – sprzętowa odpowiedź AMD na „bańki” omija RDNA3.
- PDL w ROCm nadal istnieje tylko jako enum (`hipGraphDependencyTypeProgrammatic`), bez triggera.
- Jest za to `hipLaunchAttributeCooperative` („Valid for graph nodes, launches”).
Dla nas zamiennik: dispatch „touch” bez granicy w taśmie PM4, który ściąga wagi następnej warstwy do MALL (pomysł B w raporcie 15a).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[pm4]]
- [[rocr]]
- [[raport-15a-monokernel]]
- [[hip]]
