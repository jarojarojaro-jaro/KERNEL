---
typ: repo
tags: [repo, galezie, sampler]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log -1 opt-samp; ~/KERNEL/wiki/latki/seria-amd-opt.md:26
status: aktualne
---
# Gałąź opt-samp (sampler bez wolnych ścieżek)

**Gałąź `opt-samp` @ `f4f0deae5` (2026-10-15) z łatkami 0065–0069: szybkie kandydatki top-k w samplerze także z gramatyką, wszystko pod wyłącznikami.**

Ostatni commit: „common: fast top-k candidates also with a grammar, unless grammar_first (`LLAMA_SAMPLER_FAST_GRAMMAR`)”. Seria trafiła do `amd-opt` jako 0065–0069 i dotyczy obu modeli (Qwen i LFM). Narzędzie A/B tej rundy to `samp_ab.py` (worktree `~/wt/samp-harness`). Wyniki w notatce eksperymentu sampler.

## Powiązane
- [[repo/_hub|repo]]
- [[galezie-rund]]
- [[amd-opt]]
- [[2026-10-15-sampler]]
- [[samp-ab]]
