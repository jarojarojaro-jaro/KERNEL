---
typ: decyzja
tags: [decyzje, kontekst, produkcja, testy]
aktualizacja: 2026-11-27
zrodlo: panel JARO 2026-11-27 21:40
status: aktualne
---
# 2026-11-27: zawsze pełny kontekst — tyle, ile się mieści (słowa JARO)

**JARO (2026-11-27 21:40): „Zawsze full ctx kurwa to była reguła — zawsze tyle contextu ile się mieści”; po tym, jak okazało się, że Maya (Inkling) w produkcji i we wszystkich testach od 21.11 stała na `--max-context 16384`.**

## Co to znaczy
- Każda topka (każdy model, każda karta) startuje z największym kontekstem, który mieści się w VRAM z drafterem i przechodzi test igieł; nowy silnik albo model dostaje pomiar maksimum przed pierwszym wdrożeniem.
- Benchmarki prędkości (wall, xbench) uruchamiamy na konfiguracji produkcyjnej z pełnym kontekstem, nie na skróconej.
- Wyjątek tylko z powodem zapisanym wprost (np. test celowo krótszy), nigdy po cichu.
- Qwen na :8080 już tak działa (262 144, [[2026-11-06-ctx-262k-fit]]); Maya: K-202 (ok. 488k z drafterem, 2026-11-27).

## Powiązane
- [[topki]]
- [[lekcja-maya-16k-kontekstu]]
