---
typ: research
tags: [research, xtx, ttft]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/38-checkpointy-vram.md:1-30; ~/KERNEL/product/research/43-integracja-2026-10-20.md:5-6
status: aktualne
---
# Raport 38: checkpointy GDN bez wolnej kopii hosta (LLAMA_CKPT_VRAM)

**`LLAMA_CKPT_VRAM=2` (pinned staging) skraca TTFT świeżego 2k o 22% i turę agenta S2-turn2 z 687/579 do 197 ms, md5 bez zmian; przyjęte, w produkcji od 481254bd3 (2026-10-20).**

- Utworzenie checkpointu 148–174 ms → 14.9 ms; VRAM +35 MiB (=1: +321 MiB).

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-20-21]]
- [[opoznienia-ttft]]
- [[pamiec-stanu-gdn]]
