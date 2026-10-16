---
typ: eksperyment
tags: [eksperymenty, qwen, negatywne]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/qwen-round5.md:1-29,30-85; ~/KERNEL/qwen-opt/STATUS-NEXT.md:23-29
status: aktualne
---
# 2026-10-15: Qwen runda 5 (gałąź opt-qwen5) — same wyniki negatywne

**Runda 5 nie dała łatki: GDN fast nie był bitowy, podwójny bufor MMQ zwalniał, szeroki blok DFlash był wolniejszy; za to ablacja MMQ wskazała epilog jako prawdziwe ograniczenie prefillu.**

Worktree `~/wt/qwen5`, baza `~/llama-opt` (c36fd2c87). Ok. 00:45 użytkownik zakazał pracy na GPU, ok. 02:00 pozwolił znowu.

| próba | wynik | werdykt |
|---|---|---|
| GDN fast (58e578967) | plain md5 0b7b073b zamiast c4708318 (94 vs 83 FMA w ISA) | wycofane (5b1fdbc2f) |
| MMQ y-double-buffer (a6f218d0e) | pp4096 YDB=0 1097 / 1091 vs YDB=2 1066 / 1065 (−2.6%; 3 → 2 bloki/WGP) | wycofane (2aa6999ed) |
| ablacja MMQ (`-DGGML_MMQ_ABLATION`) | vec_dot (WMMA + epilog) ~66% prefillu, ładowania ~11%, bariery ~7% | → runda 6 (0070) |
| DFlash2 n=15 vs n=6 (T=0, EN kod / PL proza) | 89.7 / 38.3 vs 104.8 / 44.2 t/s, te same zaakceptowane tokeny, 2.5× więcej draftu | wolniej |
| maska w kernelu FA | koszt hosta offline: 94k 56 µs + H2D; zysk ≤ ~0.3% | niezaimplementowane |

Wynik hipfire (318 t/s na DFlash) wymaga ich draftera MQ4V2 i promptu bez myślenia; u nas niepowtórzony. Niezmierzone zostały: tryb „draft 16, verify k” (`LLAMA_DFLASH_BLOCK`) i słownik draftu dla DFlash (bbac7d7ae).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[ablacja]]
- [[gdn-fast]]
- [[runda-6]]
- [[latki-oczekujace]]
