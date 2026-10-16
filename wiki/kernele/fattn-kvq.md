---
typ: kernel
tags: [kernele, flash-attention, kv]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:182-204,354,363,366; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:7,86,130,133; ~/KERNEL/product/research/patch-manifest.json (0011, 0055, 0058); ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:8-9,34-41,107; ~/KERNEL/product/research/15b-spekulacja-frontier.md:20,92,179; ~/KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md:54-55; ~/KERNEL/product/research/16c-kvq-cuda.md:7-15,190-198
status: aktualne
---
# FA `kvq`: atencja dekodowania na skwantyzowanym KV

**Kernel flash attention (RDNA3, WMMA), który czyta KV q4_0 lub q8_0 bez konwersji do F16 i liczy całą grupę GQA oraz do 8 tokenów w jednym przejściu; od 2026-10-16 także port CUDA (Ampere+).**

Problem (2026-10-12): przy KV q4_0 i 5 tokenach llama.cpp wybierał kernel tile, który co krok konwertował cały K/V do F16; kernel vec czytał KV osobno dla każdej z 6 głów Q w grupie (d32768 n5: 120.6 ms).

| łatka | co | wynik |
|---|---|---|
| 0011 (40c9bacdc, 2026-10-12) | kvq dla q4_0 | llama-bench d98304 n5 68.2 → 36.7 ms; serwer 94k decode 43.0 → 70.9 t/s (+65%) |
| 0055 (2026-10-14) | kvq czyta też q8_0 (D 64/128) | LFM 98k 6.561 → 5.462 ms/token; atencja 223.5 → 128.7 µs/warstwę |
| 0058 | combine robi FWHT wyjścia + q8_1 | 3.928 → 3.879 ms |

Poprawność:
- 0011 zmienia tekst greedy Qwena, a **KLD dla Qwena nigdy nie zmierzono** (luka wg raportu 07);
- 0055: KLD vs f16 KV 0.044196 wobec 0.044171 starego kernela q8_0, PASS bramki ([[bramka-kld-kanarki]]);
- 0058 bitowa.

Wyłączniki: 0011 brak (build), `GGML_HIP_KVQ_Q8`, `GGML_HIP_KVQ_FWHT`. Tylko gfx110x; RDNA4 wymaga portu (inny układ WMMA gfx12).

## Luka na CUDA (raporty 15b, 15d) – zamknięta przez 16c
- Upstream CUDA: vec czyta KV osobno dla każdej głowy Q, przy n ≥ 2 na Ampere MMA_F16 z konwersją K/V do f16 ([[fa-kv-kwantyzowane-cuda]]). 3090 tg64 base / fork przy 0 → 64k: Qwen 39.3 → 27.2, LFM 251.9 → 147.7 t/s.
- XTX: kvq czyta KV raz na kafel 16 wierszy, `ceil(6·W/16)` kafli (W5 = 2, W8 = 3, W16 = 6); d32768 n1 28.1 vs n5 33.8 ms.

## Port CUDA 16c (2026-10-16)
- `fattn-kvq-mma.cu` (`f08dc78bb`, gałąź `kvq-cuda`, `GGML_CUDA_KVQ=0` wyłącza), cc ≥ 8.0, q4_0/q8_0, D 64/128/256, ≤ 16 tokenów.
- 3090 tg64@64k: Qwen 28.61 → 39.14 (+36.8%), LFM 159.65 → 208.12 t/s (+30.4%); MTP@59k 70.33 → 89.75 t/s (+27.6%).
- Jądro 64k: Qwen q4_0 705 → 116.5 µs, LFM q8_0 286 → 119.4 µs. Szczegóły: [[2026-10-16-kvq-cuda]], decyzja KLD: [[2026-10-16-kvq-cuda-zostaje]].

## Powiązane
- [[kernele/_hub|Kernele]]
- [[prefill-mmq-fa]]
- [[attn-prep-fwht]]
- [[lfm2-5-24b-a2b]]: KV q8_0 z decyzji użytkownika
- [[rdna3-gfx1100]]
- [[fa-kv-kwantyzowane-cuda]]
- [[raport-15d-prefill-dlugi-kontekst]]
