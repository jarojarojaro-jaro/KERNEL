---
typ: research
tags: [research, fa, prefill, spill]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24v-prefill-fa.md:7-11,17-19,44-47,61-62
status: aktualne
---
# Raport 24v: FA D=256 w prefillu Qwena – spille usunięte, zysk za mały

**Jeden `sched_barrier(0)` po każdym WMMA w pętli V daje 256 VGPR / 512 B scratch → 232 VGPR / 0 B, bitowo identycznie, ale prefill zyskuje tylko +0.84% (pp512@d32k), +0.40% (pp16384), +0.5% TTFT 29.5k – nie adoptujemy, poniżej progu wyraźnej wygranej (2026-10-20).**

- Udział FA w prefillu: pp4096 2.2%, wypełnienie 32k 13%, ostatni ubatch @32k 24% (`24v:17-19`).
- Spill pochodził z hoistingu ładowań kafli V przez scheduler, nie z akumulatora (`24v:61`).
- md5 JSON z top-5 logprobs przy prompcie 4940 tok.: `4a5d4252` dla cfg 0/1/2 (`24v:37`).
- Przełącznik `GGML_HIP_FA_D256_CFG` zostaje w gałęzi `prefill-fa`. Reguła: [[lekcja-wyrazna-wygrana-albo-nic]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[lekcja-wyrazna-wygrana-albo-nic]]
- [[raport-24f-mmvq-fa]]
- [[raport-15d-prefill-dlugi-kontekst]]
