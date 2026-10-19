---
typ: eksperyment
tags: [eksperymenty, agenci, workload]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:56-90; ~/.omp/agent/sessions (458 plików, usage API)
status: aktualne
---
# 2026-10-19: workload agentów omp – prefill, dekod, współbieżność (CPU)

**21 673 unikalne tury asystenta z 458 sesji omp (34 h aktywności, deduplikacja 24 878 kopii): prefill : dekod = 4.9 : 1 tokenów, a w tempie Qwena na XTX czas modelu to prefill 34.4%, dekod 56.6%, narzędzia 8.9%; przez 37% czasu w locie są ≥ 2 żądania (średnio 1.97), a nasz serwer ma `-np 1`.**

| wielkość | p10 | mediana | p90 | średnia |
|---|---|---|---|---|
| nowe tokeny wejścia na turę | 431 | 1 476 | 6 743 | 4 352 |
| tokeny wyjścia na turę | 124 | 404 | 1 779 | 885 |
| kontekst na turę | 64k | 219k | 484k | 250k |
| czas narzędzia (ms) | 0 | 0 | 820 | 1 143 |

Współbieżność (udział czasu): 1 żądanie 63.1%, 2 – 14.5%, 3 – 7.2%, 4 – 5.9%, 5 – 4.1%, 6 – 2.2%, 7 – 1.1%, ≥ 8 – 1.8%. 15% tur wywołuje ≥ 2 narzędzia naraz.

Model czasu: prefill 850 t/s, dekod 105 t/s (Qwen MTP przy długim kontekście); dla LFM prefill tylko ~17% `[SZACUNEK]`. Zastrzeżenie: tokeny z tokenizera Claude (proporcje, nie tokeny Qwena), sesje obsługiwał równoległy dostawca. Wnioski: wielostrumieniowość to realny mnożnik, długi kontekst przesuwa wagę na atencję, prefill to ~⅓ czasu Qwena.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-18-nastepna-fala]]
- [[2026-10-18-cache-promptu-agenta]]
- [[mtplx]]
