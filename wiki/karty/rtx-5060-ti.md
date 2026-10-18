---
typ: karta
tags: [karty, nvidia, sm-120]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:36-46,105; ~/KERNEL/product/PLAN.md:287; ~/KERNEL/product/research/09-chmura-5060ti.md:1-20,59-89,119-124,166-186,191; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:17,104,305; ~/qwen-opt/cloud/results/quantkld-20261016/5060ti/speed.md:3-5
status: aktualne
---
# NVIDIA RTX 5060 Ti 16 GB (lokalnie + wynajem)

**Blackwell sm_120 z 16 GB, #3 w Steam i druga karta w naszym serwerze; w kampanii 2026-10-16 nasz silnik dał Qwen3.8-27B (Q3_K_XL) 28 → 51.7 t/s i LFM2.5 (Q4_K_M) 148 → 208 t/s.**

- Parametry: GB206, 16 GB GDDR7 128-bit, 448 GB/s, tensor core'y z FP8 i FP4; na wynajętej instancji 180 W, PCIe gen4 ×8, sterownik 580.173.02, host z limitem cgroup 7.68 CPU.
- Rynek: Steam 4.06% (#3), Vast ~$0.165/h, nowa ~$474–680; pozycja 1 na liście zakupów (PLAN §5.2).
- Build sm_120 (`120a`) 503 s; test-backend-ops 19251/19253 (2 FAIL tolerancji prologu GDN). PDL wymagał poprawki w `cuda-compat` (0053, 0057).
- Wyniki: Qwen A0 28.07 → **51.66 t/s** (profil NVIDIA, MTP), LFM A0 147.69 → **207.86 t/s**; MTP n=3 ≥ n=4.
- Profil Blackwell: `GATE_UP_Q8=0`, `Q8_IDS=0`; `GGML_CUDA_MMVQ_N1_ROWS=2` tu szkodzi (LFM −2.7%).
- Na 16 GB: nie używać upstreamowego `-fit on` z MTP (7.7 t/s); LFM Q5_K_M się nie mieści (offload −43%), najlepszy LFM to oficjalny QAD-Q4_0 (226.8 t/s, md5 = upstream).
- NVFP4: prefill +65–81%, decode bez zysku. Koszt instancji ≈ $1.05.

E1 (2026-10-18, ctx 32k): U3 MTP 51.7 vs I4/W4 50.0 t/s, plain 29.1 vs 30.3; U3 wygrywa z MTP wyższą akceptacją (0.59 vs 0.55).

## Powiązane
- [[karty/_hub|Karty]]
- [[nvidia-wyniki-2026-10-16]]
- [[raport-09-chmura-5060ti]]
- [[sm-86-89-120]]
- [[nvfp4]]
- [[lekcja-fit-mtp-16gb]]
