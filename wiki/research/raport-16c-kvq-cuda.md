---
typ: research
tags: [research, flash-attention, cuda]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16c-kvq-cuda.md:1-211; ~/KERNEL/product/research/16c-kvq-cuda.md:191-221,245-252; ~/qwen-opt/cloud/results/kvq-cuda-20261016/kld-c5/
status: aktualne
---
# Raport 16c: kvq na CUDA (E1)

**Agent CudaKvq przeniósł kernel `kvq` na NVIDIA Ampere+ (mma.sync m16n8k16, jedno przejście KV dla całej grupy GQA): +24.6…+36.8% tg przy 64k na 3090 i 5060 Ti, MTP@64k +27.6%, jeden graniczny FAIL KLD.**

- Konstrukcja: kolumny Q (tokeny × głowy) jako wymiar N, dekwant K/V ze smem prosto do fragmentów A, softmax online w log2, `movmatrix` do transpozycji, pierścień cp.async per warp (2–4 etapy), podział KV z occupancy (`GGML_CUDA_KVQ_BPSM` do strojenia; domyślny w ≤3% od optimum). D256 q4_0: 173 rejestry, 0 spilli, ~41 KB smem.
- Jądro FA 64k na 3090: Qwen q4_0 nb1 705.0 → 116.5 µs (6.05×), nb5 1053.9 → 231.1 µs; LFM q8_0 nb1 286.0 → 119.4 µs. 5060 Ti Qwen q8_0 nb1 895 → 347 µs (~92% z 448 GB/s).
- Korekta raportu 15d: MTP@64k na 3090 bez kvq to już 70.3 t/s, nie szacowane 52–55 t/s.
- Wyniki: [[2026-10-16-kvq-cuda]]; decyzja: [[2026-10-16-kvq-cuda-zostaje]].
- Dalej: rozdzielić D między warpy dla ≥ 32 kolumn, 8 warpów dla LFM D64.

- **§9 (2026-10-18):** powtórka KLD Qwena na 40 960 tokenach – FAIL ogona, wyjątek `678473a27` dla decode 1 tokenu D256 q4_0 ([[2026-10-16-kvq-cuda-zostaje]]).

## Powiązane
- [[research/_hub|research]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[fattn-kvq]]
- [[lekcja-kld-szum-kolejnosci]]
