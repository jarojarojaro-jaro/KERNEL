---
typ: karta
tags: [karty, amd, rdna4]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:7,15,75-84,97,114; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:24,119,137,364; ~/KERNEL/hardware/rx-7900-xtx.md:135,139; ~/KERNEL/product/research/66d-saber-engine-rdna.md:20,43,59,149
status: aktualne
---
# AMD Radeon AI PRO R9700 (do wynajęcia)

**RDNA4 gfx1201 z 32 GB (ten sam Navi48 co RX 9070 XT); jedyny RDNA4 do wynajęcia z root na godziny (Hostkey, €0.471/h), plan na kampanie RDNA4.**

- Pamięć: 32 GB, 640 GB/s (jak 9070 XT); L2 8 MiB, Infinity Cache 64 MiB.
- Benchmarki z raportu AMD: scoreboard Vulkan Llama 2 7B Q4_0 pp512 5908, tg128 152.7 (~91% pasma, „podejrzanie wysoko, niezweryfikowane”); tabela 07/2026: tg Vulkan 138.8 vs ROCm 7.2 98.0. Gęsty Qwen3.6-27B: ROCm 42.8 vs Vulkan 29.1 t/s (runaihome); gęsty Qwen 27B ~29–33 t/s.
- Strata na R9700: `__byte_perm` → `v_perm_b32` +15% decode (46.0 → 53.0 t/s).
- Saber (2026-11-07, R66d): zmierzony szczyt DRAM 635 GB/s; decode GEMM MXFP4 453 GB/s w łańcuchu (~71%); llama.cpp plain na R9700 29.7–30.9 tok/s (~71% pasma, Lucebox). Saber to najlepszy publiczny wzorzec operandów WMMA gfx12 i pułapek (`__syncthreads()` = `s_wait_loadcnt 0`) przy porcie topki ([[saber-engine]]).
- Dostępność: Hostkey (NL) bare metal €0.471/h, GigaGPU ~£199/mies. [INFERENCE raportu], AMD Radeon Test Drive (≤14 dni, bez komercji).
- Budżet MVP (raport 05): 60 h Hostkey ≈ €28.

## Powiązane
- [[karty/_hub|Karty]]
- [[rx-9070-xt]]
- [[chmura/_hub|Chmura]]
- [[saber-engine]]
- strata
- raport-05-chmura
