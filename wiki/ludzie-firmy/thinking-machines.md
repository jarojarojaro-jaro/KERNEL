---
typ: firma
tags: [ludzie-firmy, determinizm, nauka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/02-autotuning-i-agenci-kerneli.md:225,452; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:16
status: aktualne
---
# Thinking Machines (batch invariance)

**Laboratorium AI, autor wpisu „Defeating Nondeterminism in LLM Inference” (10.09.2025) o niezależności wyniku od wielkości wsadu (batch invariance).**

Raport 02: w vLLM przy 1000 prośbach dominująca odpowiedź tylko 78×; naprawa kosztuje 34–60% przepustowości. To punkt wyjścia raportu 12 i gałęzi `batch-invariant` (`LLAMA_SPEC_BITEXACT`), gdzie koszt dla MTP ma być ~0, bo zmienia się tylko ścieżka N=1.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[metr-sakana]]
- [[batch-invariant]]
- [[raport-12-bit-exact]]
- [[determinizm-fma]]
