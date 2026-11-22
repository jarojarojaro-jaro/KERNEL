---
typ: test
tags: [testy, rocm, vulkan]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:172-191
status: aktualne
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 78.6 t/s | dekod 1.7k; ROCm MTP T=0 | 2026-10-12
  - qwen3-8-27b | rx-7900-xtx | 92.4 t/s | dekod 1.7k; Vulkan MTP T=0 | 2026-10-12
  - qwen3-8-27b | rx-7900-xtx | 666 t/s | prefill 94k; ROCm | 2026-10-12
  - qwen3-8-27b | rx-7900-xtx | 397 t/s | prefill 94k; Vulkan | 2026-10-12
  - qwen3-8-27b | rx-7900-xtx | 165 s | prompt 94k + 1000 tok.; ROCm (Vulkan 260 s) | 2026-10-12
---
# 2026-10-12: ROCm vs Vulkan — cały czas odpowiedzi i długi kontekst

**Pomiar całego czasu odpowiedzi (prefill + 1000 tokenów) pokazał, że ROCm wygrywa wszędzie poza krótkimi promptami; po nim ROCm został stałym backendem.**

Warunki: serwer, ctx 204800, KV q4_0, MTP + słownik 64k, T=0, 256 tokenów.

| prompt | ROCm prefill | ROCm decode | Vulkan prefill | Vulkan decode | prompt + 1000 tok. ROCm / Vulkan |
|---|---|---|---|---|---|
| 1.7k | 750 t/s | 78.6 | 683 | 92.4 | 15.0 / 13.3 s |
| 6.6k | 924 | 75.5 | 746 | 80.9 | 20.3 / 21.2 s |
| 29.5k | 863 | 62.4 | 624 | 66.1 | 50.2 / 62.4 s |
| 94k | 666 | 43.0 | 397 | 43.9 | 165 / 260 s |

Dodatkowo (ROCm, 6 promptów × 3 seedy, T=1): MTP n=4 41.8 ms/krok 74.5 t/s; n=5 44.5 ms 73.8 t/s; n=3 38.4 ms 74.4 t/s (Vulkan n=5: 41.5 ms, ~80 t/s). rocprof: GPU bezczynne 15.5% czasu w przerwach <5 µs między ~1200 kernelami na krok.

Diagnoza długiego kontekstu: decode spada ~2× (92 → 44 przy 94k) na obu backendach, bo przy KV q4_0 i 5 tokenach wybierany był kernel FA tile, który co krok konwertuje cały K/V do F16 → powstał kernel `kvq`.

Decyzja (NOTES, 2026-10-12): ROCm stałym backendem domyślnym, Vulkan tylko opcją.

## Powiązane
- [[rocm-vs-vulkan]]
- [[fattn-kvq]]
- [[2026-10-12-rocm-domyslny]]
- [[hip-graph-narzut]]
