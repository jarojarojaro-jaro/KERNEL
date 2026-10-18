---
typ: eksperyment
tags: [eksperymenty, konkurencja, vulkan, rdna3]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:7-99; ~/qwen-opt/magnitude-xtx/x/xbench.jsonl; ~/qwen-opt/magnitude-xtx/results.txt; ~/qwen-opt/magnitude-xtx/servers.jsonl
status: aktualne
---
# 2026-10-18: E-X5 – Magnitude przez Vulkan na RX 7900 XTX

**Magnitude 0.2.9 (`954d677d`) działa na gfx1100 przez RADV (Mesa 25.2.8) bez poprawek, ale nasz silnik (ROCm/HIP, MTP) jest ~2× szybszy na Qwen3.8-27B i ×1.42–×2.24 na LFM2.5 przy tych samych plikach wag.**

| model / workload | Magnitude-Vulkan | nasz | × |
|---|---|---|---|
| Qwen sweep T=1 (mediana) | 50.1 t/s | 100.0 t/s | ×2.00 |
| Qwen copy 64k | 63.7 | 141.2 | ×2.22 |
| Qwen code-edit | 87.7 (7.05 tok/krok, 83 ms) | 170.0 (4.92 tok/krok, 29 ms) | ×1.94 |
| Qwen prefill 64k | 117.6 s | 78.4 s | ×1.50 |
| Qwen pl-proza | 36 | 68 | ×1.9 |
| LFM sweep / copy 64k (plain) | 219.6 / 116.7 | 322.9 / 246.4 | ×1.47 / ×2.11 |
| LFM prefill 64k | 32.7 s | 14.6 s | ×2.24 |

Warunki: ten sam harness `xbench.py` co w [[2026-10-16-magnitude-vs-fork]]; Magnitude z DFlash2 Q8_0 i adaptacyjną szerokością, my `run-llm.sh qwen mtp rocm` (ctx 67584); LFM ten sam Q4_K_M. Kolejność Qwena ABAB (przerwana sesja), rozrzut ≤ 4%. Qwen przed restartem (fabryczna krzywa wentylatora), LFM po. VRAM szczyt Qwen 22.9 vs 20.2 GB.

Start: pierwszy 95.6 s (przygotowanie kerneli 70.7 s), z cache 23–26 s; autotune 67/67 (Qwen) i 21/21 (LFM) na kanonicznych defaultach, 0 pomiarów. Zamyka E-X5 z [[raport-16i-magnitude]]: przegrywają z naszym HIP, bez priorytetu dla #5/#6.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-16j-magnitude-vulkan-xtx]]
- [[lekcja-koszt-szerokosci-backendu]]
- [[firma-magnitude]]
- [[rx-7900-xtx]]
