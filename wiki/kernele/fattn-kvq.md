---
typ: kernel
tags: [kernele, flash-attention, kv]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:182-204,354,363,366; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:7,86,130,133; ~/KERNEL/product/research/patch-manifest.json (0011, 0055, 0058); ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:8-9,34-41,107; ~/KERNEL/product/research/15b-spekulacja-frontier.md:20,92,179; ~/KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md:54-55; ~/KERNEL/product/research/16c-kvq-cuda.md:7-15,190-198; ~/KERNEL/product/research/16c-kvq-cuda.md:191-221,245-252; ~/qwen-opt/cloud/results/kvq-cuda-20261016/kld-c5/
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

## CUDA (raporty 15b, 15d, 16c)
- Luka upstreamu: vec czyta KV osobno dla każdej głowy Q, przy n ≥ 2 na Ampere MMA_F16 z konwersją do f16 ([[fa-kv-kwantyzowane-cuda]]). Na XTX kvq czyta KV raz na kafel 16 wierszy (`ceil(6·W/16)` kafli).
- Port 16c: `fattn-kvq-mma.cu` (`f08dc78bb`, `GGML_CUDA_KVQ=0` wyłącza), cc ≥ 8.0, ≤ 16 tokenów; 3090 tg64@64k Qwen 28.61 → 39.14 (+36.8%), LFM 159.65 → 208.12 (+30.4%), MTP@59k 70.33 → 89.75 t/s ([[2026-10-16-kvq-cuda]]).
- Wyjątek n=1 (2026-10-18, `678473a27`): decode 1 tokenu D256 q4_0 domyślnie na vec (`GGML_CUDA_KVQ_N1_D256_Q4=1` włącza kvq) po FAIL ogona KLD (99.9% ×2.04, szum ×1.41). tg64@64k off/kvq/wyjątek 27.29 / 36.99 / 27.40, pp5@64k 103.18 / 139.27 / 141.83 t/s ([[2026-10-16-kvq-cuda-zostaje]]).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[prefill-mmq-fa]]
- [[attn-prep-fwht]]
- [[lfm2-5-24b-a2b]]: KV q8_0 z decyzji użytkownika
- [[rdna3-gfx1100]]
- [[fa-kv-kwantyzowane-cuda]]
- [[raport-15d-prefill-dlugi-kontekst]]
