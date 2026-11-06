---
typ: research
tags: [research, vram, kontekst, mtp]
aktualizacja: 2026-11-06
zrodlo: product/research/65-vram-rezerwa-mtp-kontekst.md
status: aktualne
---
# Raport 65: 1 GiB VRAM z rezerwy MTP → kontekst 262 144

**Rezerwa grafu kontekstu draftu MTP alokowała ~1068 MiB (kopia f16 KV draftu 800 + maska 200 + aktywacje) na graf, który nigdy się nie wykonuje; chuda rezerwa (40 MiB) zwolniła 1,0 GiB, co przy ~19,1 KiB/token KV q4_0 daje +57k tokenów: czat ma natywne 262 144 (+28%) bez zmian prędkości i odpowiedzi.**

- Bufor MTP ROCm0 1081,23 → 40,28 MiB; VRAM przy 204 800: 23 360 → 22 319 MB.
- Przy 255k wypełnionych: szczyt 23 367 MiB, zapas 1193 MiB (jak wcześniej przy 204 800).
- Następne: to samo w upstream (Enigma, karty NVIDIA z MTP) – do sprawdzenia; nadmiar ~10 KiB/token (63a).

Pełny opis: [65-vram-rezerwa-mtp-kontekst.md](../../product/research/65-vram-rezerwa-mtp-kontekst.md).

## Powiązane
- [[research/_hub|research]]
- [[lekcja-rezerwa-mtp-kopia-f16]]
- [[2026-11-06-ctx-262k-fit]]
- [[2026-11-05-q63-topka]]
- [[qwen3-8-27b]]
