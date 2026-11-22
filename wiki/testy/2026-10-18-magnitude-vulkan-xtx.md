---
typ: test
tags: [testy, konkurencja, vulkan, rdna3]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:7-99; ~/qwen-opt/magnitude-xtx/x/xbench.jsonl; ~/qwen-opt/magnitude-xtx/results.txt; ~/qwen-opt/magnitude-xtx/servers.jsonl; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:1-110
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

## Ze scalonej notatki: Raport 16j: Magnitude przez Vulkan na 7900 XTX (E-X5)

Agent MagnitudeVulkanXtx uruchomił Magnitude na naszej XTX przez Vulkan i zmierzył go tym samym harnessem co 16d: na AMD Magnitude jest konkurentem w łatwości instalacji (jedna binarka, bez ROCm), nie w wydajności (×1.42–×2.24 dla nas).

- Przewaga Magnitude to wyłącznie tok/krok (blok 8 DFlash2 + kontroler); na Vulkanie ich krok 8 wierszy kosztuje ×3.0 kroku 1-wierszowego, a nasz krok prawie nie zależy od szerokości ([[lekcja-koszt-szerokosci-backendu]]).
- Kontroler sam wyłącza draft na pl-proza (1.00 tok/krok, akceptacja 0.04–0.09) – nie tracą względem plain, ale ich plain jest 2× za wolny.
- Do przejęcia: nic z kerneli Vulkan. Szerszy blok (ogon lookupu) ma na XTX lepsze warunki niż u nich: przy 7.88 tok/krok i ~35 ms code-edit dałby ~225 t/s `[INFERENCE]`.
- Ryzyko: strojenie kerneli pod RDNA i skrócenie kroku 8-wierszowego z 83 do < 48 ms zrównałoby ich z nami na code-edit.
- Komunikat produktu poparty pomiarem: „na kartach AMD ~2× szybsi od Magnitude na tym samym modelu i GPU”.

Wyniki: [[2026-10-18-magnitude-vulkan-xtx]].

## Powiązane
- [[testy/2026-10-18-magnitude-vulkan-xtx]]
- [[lekcja-koszt-szerokosci-backendu]]
- [[ekosystem/magnitude]]
- [[rx-7900-xtx]]
