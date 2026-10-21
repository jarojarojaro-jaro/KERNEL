---
typ: research
tags: [research, konkurencja, nvidia]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/39f-nvidia-flare.md:1-15
status: aktualne
---
# Raport 39f: NVIDIA Flare (flare-local-inference)

**Flare przechwytuje cały krok w graf CUDA (2 kroki w locie przy decode, 1 przy spekulacji); Qwen3.8-27B tylko jako NVFP4 20.15 GB bez spekulacji, na 16 GB nic się nie mieści; dla nas brak dźwigni ≥ +5%.**

- Do przeniesienia: token zwrotny na GPU (sufit +1.8% XTX), metryka „serwis vs podłoga replay”.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[nvidia-flare]]
- [[firma-nvidia]]
