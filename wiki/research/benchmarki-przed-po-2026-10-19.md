---
typ: research
tags: [research, benchmarki, rekordy]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/BENCHMARKI-PRZED-PO-2026-10-19.md:1-131
status: aktualne
---
# Benchmarki przed → po (stan 2026-10-19)

**Zestawienie wszystkich zmierzonych liczb całej optymalizacji – upstream, wcześniejszy fork i produkcja – dla XTX (Qwen, Uncensored, LFM), nowych zmian poza produkcją, kart NVIDIA i Magnitude, każda ze źródłem `plik:wiersz` i oceną porównywalności (P / O / brak).**

Dokument: [BENCHMARKI-PRZED-PO-2026-10-19.md](../../product/BENCHMARKI-PRZED-PO-2026-10-19.md). Najlepsze liczby z niego i z wiki: [[REKORDY]].

Najważniejsze (przed → produkcja, ten sam skrypt):
- Qwen XTX spec_sweep: fork 2026-10-12 74.5 → **109.0 t/s** (×1.46); Uncensored 78.5 → 115.5 (×1.47).
- Qwen decode MTP przy 94k (T=0): 43.0 → 100.6 t/s (×2.34); prefill 94k 142 → 123 s.
- LFM spec_sweep: 173 (KV q4_0) → **293.7 t/s** (KV q8_0, ×1.70); llama-bench 98k 144 → 213.0.
- NVIDIA (A0 → nasz): 3090 Qwen 38.9 → 78.0 (×2.00), 3090 LFM 180.2 → 263.9, 5060 Ti Qwen 28.07 → 51.66, Nemotron 87.2 → 141.1.
- Bez PM4 (zalecenie raportu 17): Qwen 103.7, Uncensored 109.9, LFM 259.3 t/s.

Braki: upstream i Ollama przez `spec_sweep` na XTX, Qwen decode 64k/128k, maks. kontekst, VRAM przy 204800 po S2/S4, LFM długi kontekst przez serwer, pełne A/B sprzężonego próbkowania i PM4 ze strażnikiem.

## Powiązane
- [[research/_hub|research]]
- [[stan-2026-10-15]]
- [[nvidia-wyniki-2026-10-16]]
- [[raport-17-gpu-page-fault]]
