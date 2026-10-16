---
typ: research
tags: [research, platforma, windows]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/08-analiza-platformy-latek.md:12-45
status: aktualne
---
# Raport 08: analiza platformy 70 łatek

**HIP na Windows działa na PAL, nie na ROCr, więc PM4 replay (0060, 0061) tam nie działa; z zysku XTX na NVIDIA pewne jest 25% (host), realnie do testu ok. +14–16%.**

- 0060 dodaje bezwarunkowe `find_package(hsa-runtime64 REQUIRED)`, co prawdopodobnie łamie build HIP na Windows – trzeba owinąć w `if (NOT WIN32)` / `GGML_HIP_PM4`.
- Korekty raportu 07: kod 0001/0002/0021/0025/0026 bez strażnika arch działa też na NVIDIA; 0054 na każdym RDNA; 0042 też na RDNA4; 0022/0040/0060/0070 obejmują RDNA3.5.
- Przenoszalność (suma Δ: Qwen 14.14 ms/krok, LFM 1.736 ms/token): Linux RDNA2/4 Qwen 73% pewne; Windows AMD HIP 25%; macOS/Vulkan 7%.
- Sampler i UI (0048, 0065–0069) przenoszą się wszędzie: +6–8% Qwen MTP, +13–15% LFM.
- `GGML_HIP_*` sterują też buildem CUDA i domyślnie są włączone – rekomendacja zmiany nazw na `GGML_CUDA_*`.

## Powiązane
- [[research/_hub|research]]
- [[raport-07-metody]]
- [[raport-13-rocm-10-1]]
- [[analiza-platformy]]
- [[hip-na-windows]]
