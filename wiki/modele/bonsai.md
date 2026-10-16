---
typ: model
tags: [modele, qwen, ternarne]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/10-post-training.md:140,329-331,389; ~/qwen-opt/cloud/runs/3060/pre/bonsai-README.md:44,63-86; ~/qwen-opt/cloud/runs/3060/pre/demo-KV-CACHE.md, demo-SPECULATIVE.md; ~/qwen-opt/cloud/runs/3060/inst/bonsai.sh:1-20; git -C ~/qwen-opt/cloud/runs/3060/prism.git remote -v; ~/qwen-opt/cloud/results/3060-20261016/summary.md
status: do-sprawdzenia
---
# Ternary Bonsai 2 27B (PrismML)

**Qwen3.8-27B w trytach {−1, 0, +1} od PrismML (PTQ1_0 ~1.75 bpw, ~5.95 GB); wymaga ich forka llama.cpp, a upstream czyta wersję Q2_0; testowany na RTX 3060.**

- Format (raport 10): tryty z FP16 skalą na grupę 128 w obróconej bazie Hadamarda (blok 1024); 98.2% średniej FP16 na 20 benchmarkach (IQ2_XXS 7.3 GB: 88.4%). Metoda treningu nie jest ujawniona. Licencja Apache-2.0.
- Pliki (README PrismML): `PTQ1_0` (gęste tryty, 1.75 bpw, 5.95 GB) i `PQ2_0` (tryt w 2-bitowym slocie, 2.13 bpw, 7.21 GB); raport 10 podaje 1.76 bpw i 5.93 GB. Potrzebny fork PrismML-Eng/llama.cpp (u nas klon „prism”); upstream od b11555 obsługuje `Q2_0`; nasz `pq2_to_q2.py` robi bezstratny repack PQ2_0 → Q2_0.
- Bonsai: `BONSAI_KV4=1` trzyma KV w Q4_0 (64 → ~18 KiB/token); brak oficjalnego draftera DSpark dla Bonsai 2 (jest społeczny dla v1).
- Pomiar RTX 3060 (2026-10-16, w toku): perplexity wikitext-2 (64×512): upstream Q2_0 8.6171 ± 0.17553, nasz fork Q2_0 8.6171 ± 0.17552, prism PQ2_0 i PTQ1_0 8.6154 ± 0.17549; greedy fork vs upstream: `DIFF-BUILD`.
- Raport 10: QAT i tryty zmieniają wyjścia — poza obietnicą „ten sam model”.

## Powiązane
- [[modele/_hub|Modele]]
- [[saluki]]
- [[kwanty-gguf]]
- [[rtx-3060]]
- raport-10-post-training
