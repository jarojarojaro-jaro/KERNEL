---
typ: research
tags: [research, re, amd, bariery]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/23b2-re-kernele-amd-bariery.md:8-14
status: aktualne
---
# Raport 23b2: RE kerneli AMD (gfx1100) i bariery LDS

**AMD nie ma lepszego GEMV niż nasz; ręczny asm Tensile pokazuje głęboki potok pamięci i bariery bez `buffer_gl0_inv`, a wszystko kompilowane z HIP przez `__syncthreads()` płaci `gl0_inv` jak my (2026-10-19, tylko CPU).**

- rocBLAS `gemvt` to wąskie `global_load_b32`; hipBLASLt dla N≤16 dopełnia do kafla 16 WMMA (`23b2:10`).
- Tensile: 12 `buffer_load_b128` w locie, prefetch PGR2, stopniowy `vmcnt(N)`; 14 574 `s_barrier` i 0 `gl0_inv` (`23b2:11`).
- AMD nigdy nie ustawia nontemporal/glc/slc na operandach GEMM (0/2182 hipBLASLt, 0/7461 rocBLAS) (`23b2:13`).
- AOTriton `attn_fwd` gorszy od naszego `fattn-kvq`: 218 vs 144 VGPR (`23b2:14`).
- Test bariery tylko-LDS na GPU: [[raport-24a-bariera-lds]] (w szumie, odrzucone).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-23b-re-kernele-amd]]
- [[bariera-lds-rdna3]]
- [[raport-24a-bariera-lds]]
