---
typ: nvidia
tags: [nvidia, cuda, testy, backlog]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67c-nvidia-backlog-testow.md; 66-SYNTEZA; 63-SYNTEZA; ~/KERNEL/qwen-opt/cloud/CUDA-AUDIT.md
status: aktualne
---
# Backlog testów NVIDIA (z całej bazy wiedzy), stan 2026-11-07

**15 tematów uszeregowanych zyskiem, wyciągniętych z wiki, raportów 15d/16c/24e/27/29/56/57/60/63/65/66/67 i łatkach; ⚑ = poprawia domyślne ustawienia Enigmy.**

| # | Temat | Zysk (szacunek) | Stan |
|---|---|---|---|
| 0 | **kernel `kvq` na CUDA** (`GGML_CUDA_KVQ=1`) | **+25–37% decode przy 64k** (3090, 5060 Ti) | **B1 zrobione (67c):** 4090 @64k KVQ=0 97,41 → KVQ=1 100,56 (+3,3%); 5080 93,94 → 89,85 (−4,4%); 3090 82,72 → 78,80 (fill-decode +9,5%, −1 GiB); bez kvq fork @204 800 crash, z kvq PASS |
| 1 ⚑ | typ KV q4_0 / q8_0 / f16 przy 64k | q8_0 na CUDA −13% vs q4_0 | **A1 zrobione:** 4090 q4_0/q8_0/f16 76,13/77,62/75,40, 5080 79,44/77,22/81,55 – szum; q4_0 zostaje (najmniej VRAM) |
| 2 ⚑ | topka2 vs upstream na każdej klasie | 93,3 t/s (3090, 19.10) vs 79,1 (4090, dziś, upstream) | **B2 zrobione:** 5090 fork+kvq+lean 148,57 vs pick 100,90 (+47%); 4090 fork 97,41 vs upstream MTP n3 76,13 (+28%); fork+kvq+lean 262 144 **101,27** (+32,5% vs pick); 3090 fork+kvq+lean UD-Q4_K_XL 262 144 79,97 vs pick 61,49 (+30%) |
| 3 ⚑ | MTP n=1–4 per klasa | 4090 n3 79,1 vs n4 76,4; 5090 n2 86,9 | **wdrożone: n=3**; **D1 zrobione:** 5090 pin b11856 n3 99,81 vs b12110 n3 91,58 / n2 93,50 → pin zostaje |
| 4 | `LLAMA_GPU_VERIFY` 0/1 | sm_89/sm_120 | **B3 zrobione:** 4090 GV=0 97,77 vs 97,41, 5080 92,88 vs 93,94, 3090 81,78 vs 82,72 – bez zysku |
| 5 | `GGML_CUDA_MMVQ_N1_ROWS=2` | sm_89 otwarte, sm_120 potwierdzić off | **B4 zrobione:** 4090 rows1/2 98,16/97,37, 5080 93,80/93,54 – szum |
| 6–7 | grafy CUDA (`DISABLE_GRAPHS`, `GRAPH_OPT`) | sm_120 | **A5/A6 zrobione:** graphs off 76,92 (4090) / 78,42 (5080), GRAPH_OPT 77,60 / 78,30 – szum, md5 bez zmian; 3090 graphs off **−5,3%** → grafy zostają |
| 8 ⚑ | ub 256/512/1024 | 262 144 na 24 GB wymaga 256 | **wdrożone** |
| 9 | port lean vs b12110 przy maks. ctx | −1,3 GiB + KV draftu 1024→288 MiB | **D3 zrobione:** 16 GB ISTA MTP n2 5080 217 088 81,62, 5060 Ti / 4060 Ti 229 376 43,40 / 36,30; 4090 262 144 ub 512 PASS 77,54. **B14:** topka-q63 0002 nałożona na fork (`kvqlean`): 4090 262 144 PASS 101,27, 3090 262 144 PASS 79,97 (bez lean crash) |
| 10 | lookup W8/W16/off na kodzie | topka2 | – |
| 11 | `-np 2` agregat | Enigma ma `-np 1` | **A13 zrobione:** +36% (4090 94,35 vs 69,46), +33% (5080 86,73 vs 65,31), +30% (3090 71,52 vs 54,98) |
| 12 | prism vs b12110 (Bonsai Q2_0) | 44,9 vs 35,1 t/s (3060, stary build) | **D4 zrobione:** 4070 Q2_0 49,43 → prism 53,75 → PTQ1_0 66,34 → +MTP n2 94,81; 2080 Ti PTQ1_0 n2 155 648 PASS 77,96 |
| 13 | `GGML_CUDA_PDL=0` | sm_120 | **A7 zrobione:** 5080 plain −1,4%, MTP −3,1% → PDL zostaje włączone |
| 14 | limit mocy, perf/W | tylko wynajęte karty | **E2 zrobione** (odcisk mocy przy każdym wyniku, np. 4090 250/450 W); E1 sweep nie |
| 15 ⚑ | `-t` z limitu cgroup + `--no-mmap` | llama.cpp bierze `nproc` (32 vs kwota 7.7) | **A11 zrobione:** `-t` z kwoty 77,36 (4090) / 79,82 (5080) – szum |

Wyniki kampanii 2026-11-07 i 67c (ID A/B/D/E jak w raporcie 67c): [[2026-11-07-kampania-nvidia-vast]]; przepisy: [[final-recipes-nvidia]].

## Powiązane
- [[nvidia/_hub|nvidia]]
- [[raport-67-kampania-nvidia]]
- [[kv-raz-na-weryfikacje]]
- [[glowica-mtp]]
- [[llama-moe-cache-mib]]
