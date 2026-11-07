---
typ: notatka
tags: [nvidia, cuda, testy, backlog]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/67c-nvidia-backlog-testow.md; 66-SYNTEZA; 63-SYNTEZA; ~/KERNEL/qwen-opt/cloud/CUDA-AUDIT.md
status: aktualne
---
# Backlog testów NVIDIA (z całej bazy wiedzy), stan 2026-11-07

**15 tematów uszeregowanych zyskiem, wyciągniętych z wiki, raportów 15d/16c/24e/27/29/56/57/60/63/65/66/67 i łatkach; ⚑ = poprawia domyślne ustawienia Enigmy.**

| # | Temat | Zysk (szacunek) | Stan |
|---|---|---|---|
| 0 | **kernel `kvq` na CUDA** (`GGML_CUDA_KVQ=1`) | **+25–37% decode przy 64k** (3090, 5060 Ti) | build `~/wt/nv-4060ti-kvq @ 007a6f813`; sm_89/sm_120 niezbudowane |
| 1 ⚑ | typ KV q4_0 / q8_0 / f16 przy 64k | q8_0 na CUDA −13% vs q4_0 | planer woli f16 > q8_0 > q4_0 (`catalog/index.ts`) |
| 2 ⚑ | topka2 vs upstream na każdej klasie | 93,3 vs 79 t/s (3090, 4090) | tylko pomiar 3090 z 2026-10-19 |
| 3 ⚑ | MTP n=1–4 per klasa | 4090 n3 79,1 vs n4 76,4; 5090 n2 86,9 | **wdrożone: n=3** |
| 4 | `LLAMA_GPU_VERIFY` 0/1 | sm_89/sm_120 | – |
| 5 | `GGML_CUDA_MMVQ_N1_ROWS=2` | sm_89 otwarte, sm_120 potwierdzić off | – |
| 6–7 | grafy CUDA (`DISABLE_GRAPHS`, `GRAPH_OPT`) | sm_120 | – |
| 8 ⚑ | ub 256/512/1024 | 262 144 na 24 GB wymaga 256 | **wdrożone** |
| 9 | port lean vs b12110 przy maks. ctx | −1,3 GiB + KV draftu 1024→288 MiB | patch gotowy, nieuruchomiony |
| 10 | lookup W8/W16/off na kodzie | topka2 | – |
| 11 | `-np 2` agregat | Enigma ma `-np 1` | – |
| 12 | prism vs b12110 (Bonsai Q2_0) | 44,9 vs 35,1 t/s (3060, stary build) | paczka gotowa |
| 13 | `GGML_CUDA_PDL=0` | sm_120 | – |
| 14 | limit mocy, perf/W | tylko wynajęte karty | – |
| 15 ⚑ | `-t` z limitu cgroup + `--no-mmap` | llama.cpp bierze `nproc` (32 vs kwota 7.7) | – |

Wyniki kampanii 2026-11-07: [[2026-11-07-kampania-nvidia-vast]].

## Powiązane
- [[nvidia/_hub|nvidia]]
- [[raport-67-kampania-nvidia]]
- [[kv-raz-na-weryfikacje]]
- [[glowica-mtp]]
- [[llama-moe-cache-mib]]
