---
typ: repo
tags: [repo, llama-cpp, galezie, worktree]
aktualizacja: 2026-10-16
zrodlo: git -C ~/llama-master branch --format=%(refname:short)\ %(objectname:short)\ %(committerdate:short)\ %(subject)
status: aktualne
---
# Gałęzie rund optymalizacji (opt-*)

**Każda runda agentów pracowała w osobnym worktree i gałęzi `opt-*`; zwycięskie commity trafiały do `amd-opt`, reszta zostaje jako zapis eksperymentu.**

Stan gałęzi (HEAD, data ostatniego commitu):
- 2026-10-12: `opt-mmvq` `6c7801bf6`, `opt-gdn` `ce934a304`, `opt-dflash` `68e163cf4` (Vulkan), `opt-fattn` `40c9bacdc` (FA kvq q4_0), `opt-fusion` `b1f8c19ac`, `opt-mtpgraph` `c90db29c6` (draft MTP jednym grafem);
- 2026-10-13: `opt-k1` `9f83f1f81` (MMVQ GLC|DLC), `opt-k2` `849b69978` (GDN conv+AB), `opt-k3` `35d04b446` (host top-k), `opt-k4` `d3a0973ae` (WMMA 9–16), `opt-s2` `343c2fbbb`, `opt-s4` `b1a203959`;
- 2026-10-14: `opt-k5` `575e3d893`, `opt-s3t1` `e84abb808`, `opt-t2` `7e9c73d8b`, `opt-lfm` `3b053e5e2`, `opt-lfm2` `5909da1f1`, `opt-lfm3` `9d493cf6e`, `opt-lfm4` `e41c2330e`;
- 2026-10-15: `opt-samp` `f4f0deae5`, `opt-gdn6` `0d89ce56c`, `opt-mmq6` `ae1ef6a97`, `opt-qwen5` `2aa6999ed`, `tools6` `4db68c6ab`.

## Powiązane
- [[repo/_hub|repo]]
- [[llama-cpp-fork]]
- [[opt-gdn6]]
- [[opt-mmq6]]
- [[opt-qwen5]]
- [[opt-samp]]
- [[tools6]]
- [[playbook-optymalizacji]]
