---
typ: lekcja
tags: [lekcje, rocm, lds, occupancy]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63c-amd-rocm-llamacpp.md:18-20,275-287,397-402; https://github.com/serrynaimo/RDNA-FAST/commit/b462181
status: do-sprawdzenia
---
# Runtime ROCm 10 raportuje 128 KB LDS na „multiprocessor”

**Runtime HIP z ROCm 10 zwraca `maxSharedMemoryPerMultiProcessor` = 128 KB, więc `cudaOccupancyMaxActiveBlocksPerMultiprocessor` daje 2–3× za dużo bloków; u RDNA-FAST atencja D=256 GQA6 zwolniła o 13–15%, a prompty 512 przy D=128 o 29% (2026-11-05).**

- Topka woła to API w `launch_fattn` (`fattn-common.cuh:1147`), czyli w prefill FA; jesteśmy na runtime 10.0.
- Poprawka (RDNA-FAST `b462181`): ograniczyć `max_blocks_per_sm` do `sharedMemPerBlock / nbytes_shared`. Zmiana dotyczy tylko launchu, więc md5 bez zmian.
- Najpierw odczytać właściwość urządzenia na naszym runtime; przy 65536 eksperyment odpada.
- Pokrewny przypadek (wafer field guide): kernel z LDS 65 792 B (> 64 KiB) uruchomiony przez ROCm 6.x bez błędu czytał śmieci.
- Stan: w toku (TopkaQuick63), wynik do wpisania.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[rocm-10-1]]
- [[rdna-fast]]
- [[bariera-lds-rdna3]]
- [[hip]]
