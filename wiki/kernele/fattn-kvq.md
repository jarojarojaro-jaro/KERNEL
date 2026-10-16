---
typ: kernel
tags: [kernele, flash-attention, kv]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:182-204,354,363,366; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:7,86,130,133; ~/KERNEL/product/research/patch-manifest.json (0011, 0055, 0058)
status: aktualne
---
# FA `kvq`: atencja dekodowania na skwantyzowanym KV

**Kernel flash attention (RDNA3, WMMA), który czyta KV q4_0 lub q8_0 bez konwersji do F16 i liczy całą grupę GQA oraz do 8 tokenów w jednym przejściu.**

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

## Powiązane
- [[kernele/_hub|Kernele]]
- [[prefill-mmq-fa]]
- [[attn-prep-fwht]]
- [[lfm2-5-24b-a2b]]: KV q8_0 z decyzji użytkownika
- [[rdna3-gfx1100]]
