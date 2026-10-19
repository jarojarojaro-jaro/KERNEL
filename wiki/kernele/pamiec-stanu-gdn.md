---
typ: kernel
tags: [kernele, gdn, stan]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:23-27,164-186; ~/KERNEL/product/research/21e-skrypty/gdn_decay.py
status: aktualne
---
# Pamięć stanu GDN w Qwen3.8-27B

**Połówkowy czas zaniku stanu GDN przy zerowym wejściu (2304 głowice = 48 warstw × 48): p50 25 tokenów, p90 1 010, p99 2 574, maksimum 18 132 – stan ma pamięć wykładniczą z długim ogonem (raport 21e, analiza wag na CPU, 2026-10-19).**

Skutek: KV/stan nie da się tanio „zagoić” krótkim re-prefillem ogona po przeniesieniu z innego modelu (w przeciwieństwie do LFM, gdzie stan shortconv ma pole recepcyjne ≤ 60 tokenów); trzeba mapować sam stan albo przeliczać okno rzędu tysięcy tokenów. Dotyczy też checkpointów i cofania stanu ([[gdn-replay]]).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[gdn-replay]]
- [[qwen3-8-27b]]
- [[raport-21e-kv-miedzy-modelami]]
