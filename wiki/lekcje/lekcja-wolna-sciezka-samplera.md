---
typ: lekcja
tags: [lekcje, sampler, wydajnosc]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:266; ~/KERNEL/qwen-opt/NOTES.md:381-392; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:4380
status: aktualne
---
# Wolna ścieżka samplera wyzwalana przez klienta

**Ustawienia klienta (`reasoning_control` z web UI, budżet myślenia, `repeat_penalty` 1.05 w GGUF LFM, gramatyka narzędzi, `logit_bias`, `n_probs`) włączały pełną tablicę 128k/248k kandydatów: LFM 293 → ~255 t/s.**

Pomiar 2026-10-15 (odtworzone zapytanie z przeglądarki użytkownika na LFM): `reasoning_control: false` 291.4 t/s vs `true` 255.6 t/s; poziomy Low/Medium/High w UI to twarde limity myślenia 512/2048/8192 tokenów i też szły wolną ścieżką. Naprawa: łatki 0048 i 0065–0069 (szybkie top-k także z budżetem, `n_probs`, `logit_bias`, gramatyką), te same tokeny. Przeglądarka ma własne zapisane ustawienia, które wygrywają z `--ui-config` serwera.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-szum-t-s-przy-t1]]
- [[lekcja-zombie-serwery]]
- [[sampler-fast-path]]
- [[2026-10-15-reasoning-control-off]]
