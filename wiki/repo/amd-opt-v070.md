---
typ: repo
tags: [repo, llama-cpp, galezie, rebase]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master log --oneline 620d2225c..amd-opt-v070 (70); ~/wt/rebase070/REBASE.md; ~/KERNEL/wiki/eksperymenty/2026-10-16-rebase-v070.md:10-20
status: do-sprawdzenia
---
# Gałąź amd-opt-v070 (rebase na v0.7.0)

**Łatki `amd-opt` przeniesione na upstream v0.7.0 (`620d2225c`, 2026-10-15): 70 commitów, HEAD `8c942e5a9` (2026-10-16), worktree `~/wt/rebase070`.**

Rebase: 69 łatek przeniesionych (60 czysto, 9 z konfliktami), 0018 porzucona, bo jest już w upstreamie. Ostatni commit naprawia crash: upstream #30257 przeniósł stan ukryty MTP do `embd_state`, a dwa nasze wywołania zostały na `set_embd`, więc Qwen MTP ze słownikiem draftu przerywał serwer. Pełna weryfikacja na GPU (greedy md5, test-backend-ops, spec_sweep) była w planie; stąd status do sprawdzenia. Na tej bazie (v0.7.0) stoją `cuda-v070`, `batch-invariant` i `mtp-train`.

## Powiązane
- [[repo/_hub|repo]]
- [[amd-opt]]
- [[cuda-v070]]
- [[2026-10-16-rebase-v070]]
- [[lekcja-mtp-embd-state]]
