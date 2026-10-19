---
typ: rocm
tags: [rocm, rdna3, isa]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:6-19; ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:7-27; ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:20-21,60-61; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:60,332-333; ~/KERNEL/product/research/23f-podrecznik-optymalizacji-gpu.md:71; ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:40
status: aktualne
---
# RDNA3 / gfx1100: architektura, pod którą piszemy

**gfx1100 (Navi31) to RX 7900 XTX/XT/GRE i W7900/W7800: 96 CU w 48 WGP, natywnie wave32, WMMA bez osobnych tensor core'ów, DPP i VOPD; od tych cech zależy każdy nasz kernel.**

Liczby dla 7900 XTX (hardware/rx-7900-xtx.md, raport AMD):
- 96 CU = 48 WGP, CU = 2× SIMD32; wave32 natywnie, wave64 opcjonalnie;
- VGPR 192 KiB na SIMD (1536 VGPR × 32 lane × 4 B); reguła occupancy (poprawiona 2026-10-19, zweryfikowana z `; Occupancy` kompilatora): fale/SIMD = min(16, ⌊1536 / roundup(VGPR, 24)⌋) – ≤ 96 → 16, ≤ 120 → 12, ≤ 144 → 10, ≤ 168 → 9, ≤ 192 → 8, ≤ 216 → 7, ≤ 240 → 6, 241–256 → **5** (wcześniej błędnie 256 → 6); `__syncthreads` = `s_barrier` + `buffer_gl0_inv`;
- LDS 128 KiB na WGP; L2 6 MiB, Infinity Cache 96 MiB; VRAM 24 GB GDDR6 384-bit, 960 GB/s (wartość standardowa, oznaczona „do weryfikacji”);
- WMMA 16×16×16 (FP16/BF16/IU8/IU4): ta sama teoretyczna przepustowość co VALU dual-issue, dane A/B trzeba duplikować między połówkami fali; ~123 TFLOPS FP16 (wyliczone);
- brak FP8, FP4 i sparsity.

Instrukcje, których używamy: `v_dot4_i32_iu8`, `v_wmma_i32_16x16x16_iu8`, DPP (`row_xmask`, `permlanex16`) do redukcji bez LDS, VOPD (`v_dual_*`, dwie operacje VALU w jednej instrukcji; `v_fma_mix` i `v_cvt` nie mogą iść w parze), buffer resource, bity cache GLC/DLC.

Pokrewne targety: gfx1101 (7800 XT/7700 XT), gfx1102 (7600, VGPR 512 KiB), RDNA3.5 gfx1150/1151; RDNA4 gfx1200/1201 ma inny układ operandów WMMA, więc nasze kernele WMMA trzeba tam portować.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rx-7900-xtx]]
- [[hip]]
- [[mmq-epilog]]
- [[kernel-tuner]]
