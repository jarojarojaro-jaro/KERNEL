---
typ: rocm
tags: [rocm, hip, kompilator]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/reports/Optymalizacja kerneli na AMD.md:27,35; ~/KERNEL/qwen-opt/NOTES.md:243,249,256,261; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:262; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:71,130-132; ~/KERNEL/hardware/rx-7900-xtx.md:10
status: aktualne
---
# HIP: jak piszemy kernele pod gfx1100

**HIP to CUDA-podobny C++ kompilowany przez AMD clang; llama.cpp kompiluje swój backend CUDA jako HIP, a nasze kernele siedzą w tych samych plikach `ggml-cuda/*.cu`.**

Praktyka z naszych łatek:
- **Target:** zawsze `gfx1100`, nie `gfx11-generic` (generic nie pozwala użyć wszystkich VGPR).
- **`amdgpu_waves_per_eu` zamiast `__launch_bounds__`:** HIP-owe `__launch_bounds__(n,1)` blokowało ustawienie fal na EU; same 32-bitowe offsety bez `waves_per_eu` dały −5…−40% (K1, 2026-10-13).
- **Intrynsyki:** `__builtin_amdgcn_wmma_*`, DPP (`row_xmask`, `permlanex16`), buffer resource, bity cache GLC/DLC; `__builtin_amdgcn_sudot4` → `v_dot4_i32_iu8`.
- **Kontrakcja FMA:** kompilator sam łączy mnożenie i dodawanie w FMA, co zmienia bity. Dla zgodności bitowej: jawny łańcuch `__builtin_fmaf`, `#pragma clang fp contract(off)` albo `ggml_cuda_no_contract` (determinizm-fma).
- **Rejestry:** HIP-owe kopie `float4` potrafią zostawić tablicę w scratch; `ext_vector_type(4)` pomogło (GDN fast, 131 → ≤128 VGPR).
- **Podgląd ISA:** `--save-temps` i `-Rpass-analysis=kernel-resource-usage`; nasz `isa.sh` kompiluje jeden TU z flagami builda.
- **Liczniki PMC w rocprofv3 zwracały 0** na tym setupie (NOTES K1); prawdopodobna przyczyna w [[rocprof]].

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rdna3-gfx1100]]
- [[hip-graph-narzut]]
- [[mmvq-multikolumnowe]]
- [[emulator-isa]]
