---
typ: kernel
tags: [kernele, rdna3, bariery]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:291-297,316-322; ~/KERNEL/product/research/21g-notatki/k.s:27-29; ~/KERNEL/product/research/21g-notatki/k2.s:33-34
status: do-sprawdzenia
---
# Bariera tylko LDS na RDNA3 (bez `buffer_gl0_inv`)

**Na gfx1100 `__syncthreads()` kompiluje się do `s_waitcnt lgkmcnt(0); s_barrier; buffer_gl0_inv`, a bariera z płotami `__builtin_amdgcn_fence(…, "workgroup", "local")` wokół `__builtin_amdgcn_s_barrier()` do samego `s_waitcnt lgkmcnt(0); s_barrier` – bez unieważniania L0, więc load globalny za barierą nie czeka; Strata #3064 zmierzyła −1.3…−5% czasu weryfikacji GDN na R9700, bitowo (raport 21g, ISA sprawdzone `hipcc -S`, 2026-10-19).**

Wersja z płotem „local” jest poprawna względem modelu pamięci (goła `s_barrier` z ręcznym `s_waitcnt` pozwala kompilatorowi przenosić dostępy LDS przez barierę). Warunek: między barierami brak komunikacji przez pamięć globalną – każdą barierę przejrzeć osobno.

Kandydaci u nas (`amd-opt`): `fattn-kvq.cu` 5 barier, `fattn-tile.cuh` 8, `fattn-vec.cuh` 6, `mmq.cuh` 12; `gated_delta_net.cu` 0 (same redukcje warpowe). Plan: makro `GGML_LDS_BARRIER()` z wyłącznikiem env, rocprof per kernel + test-backend-ops + md5; oczekiwanie 1–3% kroku przy długim kontekście, MMQ prefill 0–2% `[INFERENCE]`.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[fattn-kvq]]
- [[prefill-mmq-fa]]
- [[strata]]
