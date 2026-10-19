---
typ: metoda
tags: [metody, agenci, workload]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21f-inferencex.md:4,109-155; ~/KERNEL/product/research/21f-agentx-stats-out.txt; ~/KERNEL/product/research/21f-agentx-stats.py
status: aktualne
---
# Kształt ruchu agentowego wg śladów AgentX

**Korpus AgentX v1.0 256k (393 sesje Claude Code, 06-2026): wejście p50 88 768 / p90 204 288 tokenów, wyjście p50 376 / p90 1845 – stosunek 117:1; limit kontekstu 128k zostawia 66.3% zapytań, 64k 35.3%; przy współdzieleniu prefiksów nietrafionych w cache jest radix 3.8%, lane 8.5%, single 20.6% wejścia (2026-10-19).**

Polityki cache: **radix** (dowolne wcześniejsze zapytanie sesji, jak APC w vLLM), **lane** (poprzednie zapytanie tego samego toru agent/subagent), **single** (`-np 1` bez cache RAM), **cram** (lane + przywracanie z `--cache-ram`, nasza produkcja, ~2.1 GB/s). Subagenci w 44% sesji.

Model czasu na XTX (krzywe z `long_ctx.jsonl`; Qwen prefill krańcowo 584 t/s przy 100k, 405 przy 200k `[SZACUNEK]`): skrypt `21f-agentx-stats.py` liczy udział prefillu, decode i narzędzi (≤ 10 s) per polityka – wyniki w [[lekcja-agent-prefill-nie-decode]]. Zastrzeżenia: ruch Claude Code (nie omp), tokeny Claude'a, ekstrapolacja poza 94k, wykonanie sekwencyjne, pojemność `--cache-ram` niemodelowana.

## Powiązane
- [[metody/_hub|Metody]]
- [[2026-10-19-workload-omp]]
- [[2026-10-18-cache-promptu-agenta]]
- [[raport-21f-inferencex]]
