---
typ: optymalizacja
tags: [optymalizacje, xtx, ttft]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/38-checkpointy-vram.md:1-30; ~/KERNEL/product/research/43-integracja-2026-10-20.md:5-6
status: aktualne
technika: checkpointy GDN w VRAM (LLAMA_CKPT_VRAM=2)
werdykt: przyjete
zysk: TTFT 2k −22%, S2-turn2 687 → 197 ms
dowod: raport-38-ckpt-vram
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 197 ms | tura agenta S2-turn2; CKPT_VRAM=2 | 2026-10-20
  - qwen3-8-27b | rx-7900-xtx | 14.9 ms | utworzenie checkpointu; CKPT_VRAM=2 | 2026-10-20
---
# Raport 38: checkpointy GDN bez wolnej kopii hosta (LLAMA_CKPT_VRAM)

**`LLAMA_CKPT_VRAM=2` (pinned staging) skraca TTFT świeżego 2k o 22% i turę agenta S2-turn2 z 687/579 do 197 ms, md5 bez zmian; przyjęte, w produkcji od 481254bd3 (2026-10-20).**

- Utworzenie checkpointu 148–174 ms → 14.9 ms; VRAM +35 MiB (=1: +321 MiB).

## Powiązane
- [[raporty-2026-10-20-21]]
- [[opoznienia-ttft]]
- [[pamiec-stanu-gdn]]
