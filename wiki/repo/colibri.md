---
typ: repo
tags: [repo, konkurencja, cache, agent]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63b-colibri-maya-delta.md:27-32,85-162; https://github.com/JustVugg/colibri (v2.1.0 `704a3f68`, kod `0a5504a1`, 2026-10-31)
status: aktualne
---
# colibri (JustVugg): silnik w czystym C dla dużych MoE

**CPU/Vulkan/CUDA/Metal, eksperci w VRAM → RAM → NVMe, od v2.1.0 natywny GGUF; Qwen3.8-27B obsługiwany, bez liczb na GPU (2026-10-31).**

- „256k w szybkości 64k” to poprawka planera RAM (bufor wyceniany na segment, nie na cały ctx) i KV f32 → f16, a nie technika atencji. Lekcja dla planera Enigmy: bufor obliczeń na ubatch.
- „Tura agenta 86 → 4.9 s”: snapshot o 1 token za daleko (`<think>`) i „park” stanu przy krótkim zapytaniu bocznym. llama-server ma odpowiedniki; brakuje nam pojemności cache ([[lekcja-cache-ram-za-maly]]).
- Wart skopiowania `COLI_PREFIX_LOG`: przy chybieniu cache log mówi, w którym tokenie i na jakim tekście prompt rozjechał się ze stanem → nasz `LLAMA_SERVER_PREFIX_LOG`.
- MTP Qwen3.6 do 120 t/s (1 draft najlepszy, bramka wartości E(k)/cost(k)) – dla topki nic nowego.
- Praca autora: ABBA i kontrola bitowa przy każdym commicie, współpraca z Claude.

## Powiązane
- [[repo/_hub|repo]]
- [[project-maya]]
- [[wspolny-poczatek-promptu]]
- [[raport-63-synteza]]
