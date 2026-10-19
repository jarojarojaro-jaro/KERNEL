---
typ: research
tags: [research, reverse-engineering, mmvq]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23b-re-kernele-amd.md:1-65; ~/KERNEL/product/research/23b2-re-kernele-amd-bariery.md:1-170
status: aktualne
---
# Raport 23b: kernele AMD (gfx1100) vs nasze MMVQ, weryfikacja i atencja

**Kernele producenta dla gfx1100 (hipBLASLt 2182 rozwiązań, rocBLAS, MIOpen CK 1371 kerneli, AOTriton `attn_fwd`) nie mają lepszego GEMV ani skinny-GEMM dla N = 1..16 – nasze MMVQ wielokolumnowe stosuje już ich techniki ładowania (zasób bufora w SGPR + `soffset`, `buffer_load_b128`, `waves_per_eu`, VOPD, DPP); do przeniesienia zostały trzy rzeczy (raport 23b, statyczna analiza ISA, 2026-10-19).**

| # | zmiana | szacunek | kill |
|---|---|---|---|
| 1 | ścieżka n=1 przez loader `mmvq_ld` (b128 + `waves_per_eu`) dla Q4_K/Q5_K/Q6_K i MoE n=1 | MTP +0.5–1.2%, plain +2–5%, LFM +2–5% | – |
| 2 | Q6_K n=2..6 z b128 (dziś n=5: 60 ładowań/iterację, 0 b128, 250 VGPR, occ 5) | −0.26 ms/krok, +0.9% MTP | głowica n=5 już ≥ 820 GB/s albo < +0.5% spec_sweep |
| 3 | bariera tylko LDS w MMQ i fattn-tile ([[bariera-lds-rdna3]]) | prefill 0–2%; dekod ~0 (55 barier kvq poza pętlą KV) | pp4096 < +0.5% |

Liczby: nasza ścieżka n=1 to upstream – 18 ładowań `global_load_b32`/`d16` na iterację, 2.9–3.5 B na instrukcję VMEM, wobec 11–12 B w wielokolumnowej; hipBLASLt skinny używa kroczącego `vmcnt(11)` przy 256 VGPR i occ 5. AMD nie używa bitów cache (nonTemporal = 0 w 2182 rozwiązaniach, glc/slc/dlc = 0 w kodzie), wszystkie kernele wave32; CK-tile `block_sync_lds` = `lgkmcnt(0)` + `s_barrier` bez `buffer_gl0_inv`. Little's law: w locie mamy 31 KB (n=1) i 105 KB (Q4_K n=5) na SIMD wobec ~4.7 KB potrzebnych – wąskim gardłem jest koszt wydawania małych ładowań, nie równoległość ([[lekcja-littles-law-gemv]]).

Odrzucone: bity cache, prefetch PGR2, split-K (łamie bitowość spekulacji), WMMA dla n ≤ 8 (hipBLASLt dopełnia N do 16), wave64, rocBLAS gemv jako wzór, `s_setprio`. Narzędzia: `~/KERNEL/tools/re/` (kpack, fatbin, profil ISA, Tensile, AOTriton).

**Wersja wcześniejsza (23b2, ResVendorAmd):** dodatkowo pętla MMVQ n≥2 bez prefetchu między iteracjami (`vmcnt(0)` co iterację; Tensile PGR2 w 1418/2182 rozwiązań) i bity `glc dlc` na wagach (AMD: 0 w 2182 + 7461 + CK) jako tani A/B; bariery z `gl0_inv` u nas: `fattn-kvq` 55/55 (poza pętlą KV), `fattn-vec` 39/40, `fattn-tile` 115/129, `mmq` 122/196 z 4 barierami + 4 `gl0_inv` w każdej iteracji K; AOTriton `attn_fwd` (218 VGPR, 11 barier/iterację, P przez LDS) gorszy od naszego kvq (144 VGPR, 0 barier w pętli, `v_permlanex16`).

## Powiązane
- [[research/_hub|research]]
- [[raport-21l-re-gpu]]
- [[mmvq-multikolumnowe]]
- [[mmvq-n1-wiersze]]
