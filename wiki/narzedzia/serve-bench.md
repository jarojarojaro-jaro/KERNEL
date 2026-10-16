---
typ: narzedzie
tags: [narzedzia, pomiar, historia]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/serve_bench.py:1-10; ~/KERNEL/qwen-opt/quick_quality.py:1-4; ~/KERNEL/qwen-opt/NOTES.md:3-4,29-36; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:241
status: aktualne
---
# serve_bench.py i quick_quality.py — pierwsze narzędzia (2026-10-09)

**Pierwszy benchmark end-to-end projektu i szybki test jakości; dziś zastąpione przez spec_sweep, ale ich wyniki (59.2 → 92 t/s) są punktem startowym.**

- `serve_bench.py --label … --bin …/llama-server [--lang en|pl|all]`: sam uruchamia świeży serwer, rozgrzewa, puszcza stałe prompty przez chat (T=0, stałe `max_tokens`), raportuje decode t/s (`predicted_per_second`), prefill t/s i akceptację draftu MTP; dopisuje linię JSON do `results.jsonl` (49 wpisów z 2026-10-09).
- Metoda NOTES: 256 tokenów, 3 przebiegi na prompt, mediana, z rozgrzewką.
- `quick_quality.py PORT LABEL`: 10 krótkich pytań EN/PL ze sprawdzalnymi odpowiedziami, greedy, bez myślenia — szybka kontrola, czy zmiana nie zepsuła modelu.
- Różnica do spec_sweep: T=0 zamiast T=1 i jeden seed, więc liczby nie są wprost porównywalne (raport 07 §2.4).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[spec-sweep]]
- [[2026-10-09-pierwsze-pomiary]]
- [[greedy-check]]
- [[pomiar-abba]]
