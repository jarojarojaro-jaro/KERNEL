---
typ: model
tags: [modele, qwen, niskobitowe]
aktualizacja: 2026-10-16
zrodlo: ~/qwen-opt/cloud/runs/3060/pre/saluki-README.md; ~/qwen-opt/cloud/runs/3060/pre/saluki-head.json; ~/KERNEL/product/research/10-post-training.md:45,52,139,337,389,453; ~/qwen-opt/cloud/results/3060-20261016/summary.md
status: do-sprawdzenia
---
# Underdog Saluki 27B 1.0 (Qwen3.8-27B w 2 bitach)

**Qwen3.8-27B skwantyzowany do 7.89 GB (IQ2-mix na bazie ISTA GSQ-RCO), strojony tak, żeby zachować wywoływanie narzędzi; testowany na RTX 3060 12 GB.**

- Autor: ConwayResearch / Underdog, Apache-2.0; baza `Qwen/Qwen3.8-27B` i `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF` (nagłówek GGUF: `general.architecture` = `qwen35`, `general.name` = „Qwen3.8-27B GSQ-RCO”).
- Plik `Underdog-Saluki-27B-1.0-IQ2-mix.gguf` 7.89 GB; vision add-on `mmproj` F16 928 MB lub Q8_0 629 MB; działa w zwykłym llama.cpp.
- Deklaracje autora: tool calling (Underdog Bench) 88 vs 84 pełny model, parallel tool calls 42 vs 35, średnia retencja 96% na 9 benchmarkach. Raport 10: BFCL-120 88 vs 84, ale AIME 2025 79.2 vs 96.7.
- Raport 10: niskobitowe odtwarzanie zmienia wyjścia, więc to inna obietnica („Tryb maksymalny”); pomysł głowic MTP per kwant (Saluki IQ2) ~$1–3 każda. Istnieje społeczny wariant z MTP (`Kujira/Underdog-Saluki-27B-1.0-MTP-…`).
- Pomiar RTX 3060 (2026-10-16, w toku): llama-bench A0 pp512 573.37, pp4096 569.90 t/s; perplexity wikitext-2 (64×512) 7.6665 ± 0.15010; greedy fork vs upstream: `DIFF-BUILD`.

## Powiązane
- [[modele/_hub|Modele]]
- [[bonsai]]
- [[qwen3-8-27b]]
- [[rtx-3060]]
- raport-10-post-training
