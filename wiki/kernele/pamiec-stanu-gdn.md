---
typ: kernel
tags: [kernele, gdn, stan]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/21e-kv-miedzy-modelami.md:23-27,164-186; ~/KERNEL/product/research/21e-skrypty/gdn_decay.py; ~/KERNEL/product/research/38-checkpointy-vram.md:1-30; ~/KERNEL/product/research/48-norma-n4-gdn-bank.md:20-58
status: aktualne
---
# Pamięć stanu GDN w Qwen3.8-27B

**Połówkowy czas zaniku stanu GDN przy zerowym wejściu (2304 głowice = 48 warstw × 48): p50 25 tokenów, p90 1 010, p99 2 574, maksimum 18 132 – stan ma pamięć wykładniczą z długim ogonem (raport 21e, analiza wag na CPU, 2026-10-19).**

Skutek: KV/stan nie da się tanio „zagoić” krótkim re-prefillem ogona po przeniesieniu z innego modelu (w przeciwieństwie do LFM, gdzie stan shortconv ma pole recepcyjne ≤ 60 tokenów); trzeba mapować sam stan albo przeliczać okno rzędu tysięcy tokenów. Dotyczy też checkpointów i cofania stanu ([[gdn-replay]]).

## Aktualizacja 2026-10-21
- Checkpointy w pinned host (`LLAMA_CKPT_VRAM=2`): utworzenie 148–174 → 14.9 ms, w produkcji ([[raport-38-ckpt-vram]]).
- Drugi bank stanu: v1/v2 bitowo zgodne, E0 −0.4% → nie; v3 nierozstrzygnięty ([[raport-48-norma-gdn-bank]]); GDN ≤0.06 ms/krok sufitu ([[raport-51-male-kernele]]).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[gdn-replay]]
- [[qwen3-8-27b]]
- [[raport-21e-kv-miedzy-modelami]]
