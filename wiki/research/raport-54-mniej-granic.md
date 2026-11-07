---
typ: research
tags: [research, xtx, pm4]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/54-mniej-granic.md:1-30; ~/KERNEL/product/research/66c-hyperkernel-megakernele.md:104-106; ~/qwen-opt/launchcut/logs/prose.jsonl, copy_bench.jsonl (2026-10-21)
status: aktualne
---
# Raport 54: mniej granic dispatchy w kroku weryfikacji

**Krok = 946 dispatchy (verify 824); fuzje ATTN_PREP_MT (−84 granic/krok) i KVQ_FWHT_GATE (−42) zmierzone w ABBA x54/x54r 2026-10-21: proza +0.24% (szum), `mvs` 0.0% – usuwanie granic poza łańcuchami MMVQ → norma → MMVQ nic nie daje (raport 66c, 2026-11-07).**

- Proza A 78.54 / 78.65 / 78.01 / 78.97 vs B (`ATTN_PREP_MT=1 KVQ_FWHT_GATE=1`) 78.63 / 78.69 / 78.91 / 78.68 t/s; `mvs` 428.49 vs 428.55; akceptacja 0.293 w obu.
- Env ramion potwierdzony w logu kolejki, ale log nie pokazuje, że matcher fuzji zadziałał `[INFERENCE]` ([[lekcja-flaga-bez-dowodu-dzialania]]).
- Wniosek: koszt leży w ogonach i rampach łańcuchów MMVQ → norma → MMVQ (górna granica −2.17 ms/krok). Pozycje „mniej dispatchy” poza tymi łańcuchami schodzą w kolejce ([[budzet-megakernela-qwen-xtx]]).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[pm4-replay]]
- [[fuzje-weryfikacji]]
