---
typ: rocm
tags: [rocm, hip-graph, launch-overhead]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/v2/rr-hip.md:3-26; ~/KERNEL/qwen-opt/NOTES.md:57,93,101-102,232
status: aktualne
---
# Narzut grafu HIP: ~3 µs na kernel

**Na gfx1100 każda granica kernela w grafie HIP kosztuje ~3.2–3.4 µs bezczynności GPU, niezależnie od typu kernela; przy ~2000 kerneli na krok to 16–19% czasu.**

Analiza trace z 2026-10-12 (rr-hip.md, Qwen MTP n_max=4, ctx 16k): w grafie weryfikacji 2188 kerneli, 36.7–36.9 ms wall, 29.8 ms pracy GPU; przerwy przed kernelami ~3.2–3.3 µs (mmvq 3.27, rms_norm 3.23, quantize_q8_1 3.22…), razem 7.13 ms przerw na weryfikację (19% wall).

Przyczyna (źródło CLR `rocvirtual.cpp`): każdy pakiet AQL kernela ma bit bariery i agent-scope acquire (inwalidacja I, K i L1), więc CP czeka na poprzedni pakiet. Wysyłka z hosta nie jest problemem (graf kopiuje pakiety jednym doorbellem). Dlatego zmienne HIP (graph batch/segment, kernarg, direct dispatch, `DEBUG_HIP_GRAPH_BATCH_SIZE=16`) dały szum. Niezależny pomiar: ROCm issue #6409 (W7900, gfx1100) 3.865 µs/węzeł vs 0.876 µs/dispatch w replay RADV.

Co z tym zrobiliśmy: mniej kerneli (fuzje: weryfikacja 2156 → ~830) i replay PM4 (granica ~0.5–0.9 µs). To też tłumaczyło, czemu Vulkan dekodował szybciej przed fuzjami.

## Powiązane
- [[rocm/_hub|ROCm]]
- [[pm4]]
- [[fuzje-weryfikacji]]
- [[rocm-vs-vulkan]]
- [[mikrobench-granicy-kernela]]
- [[hip-dyn-data-prefetch]]
