---
typ: lekcja
tags: [lekcje, build, cuda, chmura]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67-nvidia-vast-kampania.md:69,85
status: aktualne
---
# Paczka silnika zbudowana z `-march=native` nie działa na cudzym procesorze

**Nasz fork CUDA (`topka2` z `pkg/`) był zbudowany z `-march=native` i na wynajętej 3090 z Xeonem E3-1245 v2 (bez AVX2) kończył się `Illegal instruction`; zbudowany z `GGML_NATIVE=OFF` (wariant z AVX2 i osobny bez AVX2) działa, a ten sam fork dał tam 80,0 t/s przy 262 144 (2026-11-07).**

Reguła: każda paczka, która ma trafić do użytkownika albo na wynajęty host, jest budowana przenośnie (`GGML_NATIVE=OFF`, lista architektur GPU podana jawnie, np. sm_86;89;120) i ma wariant bez AVX2; `-march=native` tylko dla buildów na własną maszynę. Przed testem: `grep -o avx2 /proc/cpuinfo` na hoście.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[jak-przyspieszylismy-nvidia]]
- [[lekcja-build-cuda-0057-0070]]
- [[lekcja-slaby-cpu-3090]]
