---
typ: model
tags: [modele, kwanty, qwen]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/10-post-training.md:140,329-331,389; ~/qwen-opt/cloud/runs/3060/pre/bonsai-README.md:44,63-86; ~/KERNEL/product/research/09-chmura-3060.md:30-62,86-107,120-127,177-179,194-223; ~/KERNEL/product/research/16e-kwanty-kld.md:34-46,63
status: aktualne
---
# Ternary Bonsai 2 27B (PrismML)

**Qwen3.8-27B w trytach {−1, 0, +1} od PrismML; najszybszy jest w forku prism jako PTQ1_0 (44.75 t/s na RTX 3060), a PQ2_0 można bezstratnie przepakować do upstreamowego Q2_0 i uruchomić na czystym llama.cpp i naszym forku.**

- Format (raport 10): tryty z FP16 skalą na grupę 128 w obróconej bazie Hadamarda (blok 1024); 98.2% średniej FP16 na 20 benchmarkach; metoda treningu nieujawniona; Apache-2.0.
- Typy prism: `PQ2_0` = ggml type 142, `PTQ1_0` = 143, prywatne dla forka PrismML-Eng/llama.cpp (mierzone wydanie `prism-b10777-e3de715`). Brak MTP i brak draftera DSpark dla Bonsai 2.
- **Repack PQ2_0 → Q2_0 bez strat:** kodek 2-bitowy identyczny, różni się tylko grupa skali (128 vs 64), więc każdy blok 34 B dzielimy na dwa bloki 18 B z tą samą skalą (`pq2_to_q2.py`, 124 s); plik 7.21 → 7.63 GB. PPL prism PQ2_0 8.6154 vs upstream/fork Q2_0 8.6171 – różnica z kerneli. PTQ1_0 nie ma bezstratnego odpowiednika (TQ1_0 ma skalę co 256).
- RTX 3060 (2026-10-16): prism PTQ1_0 **44.75 t/s** (6.8 GB VRAM), prism PQ2_0 36.45, upstream Q2_0 33.15, nasz fork Q2_0 **35.51 t/s** (+7.1% vs upstream, −21% vs PTQ1_0). Narzut Hadamarda w forku ~1.2 ms z 28 ms; prism ma fuzję FWHT+znaki+q8_1 tylko dla PTQ1_0.
- KLD forka 0.000323 vs szum upstreamu 0.000206 – PASS. Po polsku robi błędy językowe.
- Port naszych łatek na fork prism: 9 OK, 65 konfliktów – lepsza droga to repack i nasz fork.

E1 (2026-10-18): KLD do Qwen BF16 wiki 0.352, PL 0.508 (najgorszy, PL/wiki 1.44); nadal najszybszy na 12 GB (PTQ1_0 Prism 44.9 t/s).

Bonsai 2 9B (2026-10-15, geometria Qwen3.5-9B, PQ2_0 + MTP Q8_0 + drafter DFlash2): konkurs cuda.fast / mlx.fast podniósł decode z 85.9 do 576.7 tok/s (DGX Spark, llama.cpp) i z 144.8 do 959.6 tok/s (M5 Max) ([[bonsai-fast-contest]], raport 60b).

## Powiązane
- [[modele/_hub|Modele]]
- [[saluki]]
- [[kwanty-gguf]]
- [[rtx-3060]]
- [[prism-llama-cpp]]
- [[raport-09-chmura-3060]]
- [[bonsai-fast-contest]]
