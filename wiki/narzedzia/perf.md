---
typ: narzedzie
tags: [narzedzia, pomiar, proces]
aktualizacja: 2026-11-25
zrodlo: ~/KERNEL/tools/perf/ (perf, perf-remote.sh, spill_audit.sh, ledger.py, profiles/bonsai25.env); [[metoda-nib-level-up]]
status: aktualne
---
# tools/perf: pętla optymalizacji jedną komendą (K-161)

**`tools/perf PROFIL WORKTREE BAZA` buduje silnik poza blokadą GPU, robi audyt spillów względem bazy, a w jednym jobie kolejki: test-backend-ops, md5 greedy, KLD 40×512, księgę µs/token z rocprof (delta do bazy) i ABBA czatu + kopii; na końcu jedno podsumowanie.**

- Wzór: Nib (spill audit, księga czasu, oracle w pętli), [[metoda-nib-level-up]].
- `spill_audit.sh BUILD [--out F] [--base F]`: każdy kernel gfx1100 z obiektów ggml-hip; błąd tylko przy nowym albo większym spillu/scratch względem bazy (fork już ma kernele ze spillami).
- `ledger.py STATS N [BASE_STATS N]`: µs/token, udział, wywołania/token, delta per kernel.
- Profile w `tools/perf/profiles/` (model, argumenty serwera i spekulacji, env produkcji, filtry test-backend-ops); pierwszy: `bonsai25.env`.
- Stan 2026-11-25: napisane i sprawdzone składniowo; pierwszy bieg na karcie czeka na włączenie jaroserverai (offline od 04:27). Maya (silnik ik2) potrzebuje osobnego profilu z `ik2_kernels_test` i rep2.

## Powiązane
- [[metoda-nib-level-up]]
- [[kol]]
- [[playbook-optymalizacji]]
