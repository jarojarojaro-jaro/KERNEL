---
typ: eksperyment
tags: [eksperymenty, nvfp4, kwanty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:47-51,186-200,320-332
status: aktualne
---
# 2026-10-16: NVFP4 ze skalą globalną i bez (symulacja CPU)

**Symulacja na prawdziwych wagach BF16 Qwen3.8-27B: dodanie skali globalnej per tensor do kwantyzatora NVFP4 ggml obniża błąd wag o 22–35%, ale nawet wtedy NVFP4 RTN jest o 12–17% gorszy od Q4_0 RTN przy tych samych 4.5 bpw.**

`nvfp4_global_scale_sim.py`, 512 wierszy na tensor (rel-MSE wag):

| tensor | ggml (bez skali globalnej) | + skala globalna | skala float | Q4_0 RTN | % subnormalnych |
|---|---|---|---|---|---|
| L29 `linear_attn.in_proj_qkv` | 0.0114 | 0.0089 | 0.0087 | 0.0079 | 99.9% |
| L31 `self_attn.q_proj` | 0.0130 | 0.0089 | 0.0087 | 0.0080 | 99.9% |
| L30 `mlp.up_proj` | 0.0138 | 0.0090 | 0.0088 | 0.0077 | 100% |
| L60 `mlp.down_proj` | 0.0131 | 0.0090 | 0.0088 | 0.0075 | 100% |
| L5 `linear_attn.out_proj` | 0.0116 | 0.0090 | 0.0088 | 0.0076 | 99.9% |

Przyczyna: `quantize_row_nvfp4_ref` liczy `UE4M3(amax/6)` bez skali per tensor, a `quantize_nvfp4` ignoruje imatrix; przy wagach std ≈ 0.011–0.016 skale lądują w 3–5 kodach subnormalnych. W pliku esatapedico tensory przekwantyzowane przez `llama-quantize` mają 99.8–100% subnormalnych skal i 6–14 wartości. Poprawka (E2) to 1–2 osobodni; jedynym argumentem za NVFP4 zostaje prefill na sm_120.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[nvfp4]]
- [[raport-15e-kwantyzacja-nowa]]
- [[2026-10-16-kompresja-skal-offline]]
- [[rtx-5060-ti]]
