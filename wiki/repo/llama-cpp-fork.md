---
typ: repo
tags: [repo, llama-cpp, galezie, worktree]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master branch; git -C ~/llama-master worktree list; git -C ~/llama-master log e60eff95f..amd-opt (70), 620d2225c..amd-opt-v070 (70)
status: aktualne
---
# Nasz fork llama.cpp: repozytoria, gałęzie i worktree

**Cała praca kernelowa żyje w jednym repo git `~/llama-master` z worktree w `~/wt/`; gałąź produkcyjna to `amd-opt` (70 commitów na upstream `e60eff95f`), a jej odpowiednik na v0.7.0 to `amd-opt-v070`.**

Stan 2026-10-16 (`git worktree list`):
- `~/llama.cpp` (`master` @ `b356fa262`): czysty upstream do porównań;
- `~/llama-base` i `~/wt/cuda-base` (detached `e60eff95f`, upstream z 2026-10-09): baza serii łatek;
- `~/llama-master` (`amd-opt` @ `f61994f58`): produkcja, instalacja w `~/llama-opt`;
- `~/wt/v070-base` (detached `620d2225c` = v0.7.0 z 2026-10-15) i `~/wt/rebase070` (`amd-opt-v070`);
- gałęzie NVIDIA: `cuda-compat`, `cuda-v070`, `cuda-3090-opt`, `cuda-v070-5060ti`, `3060-opt`;
- gałęzie eksperymentalne rund: `opt-k1`…`opt-k5`, `opt-s2/s3t1/s4`, `opt-t2`, `opt-lfm`…`opt-lfm4`, `opt-samp`, `opt-gdn6`, `opt-mmq6`, `opt-qwen5`, `tools6`, `batch-invariant`, `mtp-train` oraz starsze `opt-dflash/fattn/fusion/gdn/mmvq/mtpgraph` (2026-10-12).
Reguła: każda runda dostaje osobny worktree od aktualnego `amd-opt`, a do `amd-opt` trafiają tylko zmierzone, bitowe commity z wyłącznikiem env.

## Powiązane
- [[repo/_hub|repo]]
- [[amd-opt]]
- [[amd-opt-v070]]
- [[galezie-rund]]
- [[seria-amd-opt]]
