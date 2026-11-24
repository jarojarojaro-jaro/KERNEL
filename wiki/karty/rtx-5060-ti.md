---
typ: karta
tags: [karty, nvidia, sm-120]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/hardware/rx-7900-xtx.md:36-46,105; ~/KERNEL/product/PLAN.md:287; ~/KERNEL/product/research/09-chmura-5060ti.md:1-20,59-89,119-124,166-186,191; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:17,104,305; ~/qwen-opt/cloud/results/quantkld-20261016/5060ti/speed.md:3-5; ~/qwen-opt/cloud/results/nv67c-summary.txt
status: aktualne
karta: rtx-5060-ti
vram: 16 GB
pasmo: 448 GB/s
gdzie: jaroserverai / Vast
stan: zmierzona (09, E1, 67c)
wyniki:
  - qwen3-8-27b | rtx-5060-ti | 54,33 t/s | dekod MTP; fork+kvq+lean UD-Q3_K_XL ctx 98 304 | 2026-11-07
  - qwen3-8-27b | rtx-5060-ti | 51.66 t/s | dekod MTP; Q3_K_XL, profil NVIDIA | 2026-10-16
  - qwen3-8-27b | rtx-5060-ti | 49,44 t/s | dekod MTP; fork+kvq+lean ISTA ctx 196 608 | 2026-11-07
  - lfm2-5-24b-a2b | rtx-5060-ti | 226.8 t/s | dekod; QAD-Q4_0 | 2026-10-16
  - lfm2-5-24b-a2b | rtx-5060-ti | 139,48 t/s | dekod; Q4_K_M ctx 131 072 q8_0 | 2026-11-07
---
# NVIDIA RTX 5060 Ti 16 GB (lokalnie + wynajem)

**Blackwell sm_120 z 16 GB, #3 w Steam i druga karta w naszym serwerze; w kampanii 2026-10-16 nasz silnik dał Qwen3.8-27B (Q3_K_XL) 28 → 51.7 t/s i LFM2.5 (Q4_K_M) 148 → 208 t/s.**

- Parametry: GB206, 16 GB GDDR7 128-bit, 448 GB/s, tensor core'y z FP8 i FP4; na wynajętej instancji 180 W, PCIe gen4 ×8, sterownik 580.173.02, host z limitem cgroup 7.68 CPU.
- Rynek: Steam 4.06% (#3), Vast ~$0.165/h, nowa ~$474–680; pozycja 1 na liście zakupów (PLAN §5.2).
- Build sm_120 (`120a`) 503 s; test-backend-ops 19251/19253 (2 FAIL tolerancji prologu GDN). PDL wymagał poprawki w `cuda-compat` (0053, 0057).
- Wyniki: Qwen A0 28.07 → **51.66 t/s** (profil NVIDIA, MTP), LFM A0 147.69 → **207.86 t/s**; MTP n=3 ≥ n=4.
- Profil Blackwell: `GATE_UP_Q8=0`, `Q8_IDS=0`; `GGML_CUDA_MMVQ_N1_ROWS=2` tu szkodzi (LFM −2.7%).
- Na 16 GB: nie używać upstreamowego `-fit on` z MTP (7.7 t/s); LFM Q5_K_M się nie mieści (offload −43%), najlepszy LFM to oficjalny QAD-Q4_0 (226.8 t/s, md5 = upstream).
- NVFP4: prefill +65–81%, decode bez zysku. Koszt instancji ≈ $1.05.

E1 (2026-10-18, ctx 32k): U3 MTP 51.7 vs I4/W4 50.0 t/s, plain 29.1 vs 30.3; U3 wygrywa z MTP wyższą akceptacją (0.59 vs 0.55).

Kampania 67c (2026-11-07, host 160/180 W): stary pick UD-Q3_K_XL 135 168 PASS 27,48; nowy ISTA IQ3_XXS-mtp 200 704 plain PASS **31,42** (14 230 MiB; pin MTP n3 ładuje się, 39,68, bez filla). Lean MTP n2 **229 376 PASS 43,40 t/s** (15 762 MiB). Fork+kvq+lean ISTA: 196 608 PASS **49,44** (15 416 MiB; 229 376 crash, 262 144 OOM); UD-Q3_K_XL 98 304 PASS 54,33. LFM2.5 Q4_K_M w VRAM 131 072 q8_0: **139,48 t/s**, peak 15 820. Przepisy: [[final-recipes-nvidia]].

<!-- TABELE:START -->
## Wyniki z notatek (26)

Najlepszy wynik na metrykę z pól `wynik` notatek testów (tools/tabele.py, 2026-11-24); pełna tabela: [[najlepsze-wyniki]].

| model | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[rtx-5060-ti]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod serwer | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[lfm2-5-24b-a2b]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | dekod T=1 | **207.86 t/s** | Q4_K_M fork (A1 144.47) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | serwer | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[raport-09-chmura-5060ti]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | sweep 32k fork | **205.1 t/s** | (Magnitude 157.8) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| LFM2.5-24B-A2B [[lfm2-5-24b-a2b]] | tg64 64k | **155.77 t/s** | kvq CUDA, Q4_K_M (bez 119.82) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| Qwen3.5-9B [[qwen3-5-9b]] | code-edit | **239.0 t/s** | fork CUDA gałąź cuda-v070-5060ti, 1 runda | 2026-10-16 | [[qwen3-5-9b]] |
| Qwen3.5-9B [[qwen3-5-9b]] | prefill 64k | **2343 t/s** | fork CUDA | 2026-10-16 | [[qwen3-5-9b]] |
| Qwen3.5-9B [[qwen3-5-9b]] | sweep | **121.0 t/s** | fork CUDA, 1 runda | 2026-10-16 | [[qwen3-5-9b]] |
| Qwen3.6-35B-A3B [[qwen3-6-35b-a3b]] | dekod mediana | **115.9 t/s** | LM | 2026-10-20 | [[qwen3-6-35b-a3b]] |
| Qwen3.8-27B [[qwen3-8-27b]] | czat T=1 T | **62.6 t/s** | UD-IQ4_XS 32k, 150 W | 2026-10-20 | [[raport-31-5060ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod | **51.66 t/s** | nasz silnik (A0 28.07) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP | **54,33 t/s** | fork+kvq+lean UD-Q3_K_XL ctx 98 304 | 2026-11-07 | [[rtx-5060-ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP ctx 196 608 | **49,44 t/s** | ISTA IQ3_XXS-mtp, fork+kvq+lean | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n2 T=0 | **54,2 t/s** | GSQ IQ3_XXS-mtp, kvqlean, ctx 8192, 180 W | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n2 T=1 | **51,0 t/s** | GSQ IQ3_XXS-mtp, kvqlean, ctx 8192 | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP n=2 | **51.7 t/s** | UD-Q3_K_XL 32k | 2026-10-18 | [[2026-10-18-e1-kwanty-27b-kld]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod MTP T=1 | **51.66 t/s** | UD-Q3_K_XL fork (A1 37.32) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| Qwen3.8-27B [[qwen3-8-27b]] | dekod plain | **31,9 t/s** | GSQ IQ3_XXS-mtp, kvqlean | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| Qwen3.8-27B [[qwen3-8-27b]] | mvs | **244.2 t/s** | UD-IQ4_XS | 2026-10-20 | [[raport-31-5060ti]] |
| Qwen3.8-27B [[qwen3-8-27b]] | pp576 ub 16 | **306,41 t/s** | v1.0.0 (b11856 278,98) | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| Qwen3.8-27B [[qwen3-8-27b]] | prefill ~11k | **828 t/s** | GSQ IQ3_XXS-mtp, kvqlean | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep T=1 MTP n2 | **45,62 t/s** | ISTA IQ3_XXS-mtp, v1.0.0, 150 W | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| Qwen3.8-27B [[qwen3-8-27b]] | spec_sweep T=1 MTP n3 | **40,32 t/s** | b12359, 160 W | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| Qwen3.8-27B [[qwen3-8-27b]] | sweep fork | **58.0 t/s** | Q3_K_XL (upstream 43.5) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| Qwen3.8-27B [[qwen3-8-27b]] | tg64 64k | **25.69 t/s** | kvq CUDA, Q3_K_XL q8_0 (bez 20.61) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |

Optymalizacje na tej karcie ([[bilans-optymalizacji]]): [[fa-kv-kwantyzowane-cuda|kvq-mma (FA na KV q4_0/q8_0, CUDA)]] (przyjete, 5060 Ti tg@64k Qwen +24.6%, LFM +30.0%); [[pdl-mmvq-trigger|PDL trigger w MMVQ (CUDA sm_90+)]] (w-toku, niezmierzone (szacunek)).
<!-- TABELE:END -->

## Powiązane
- [[karty/_hub|Karty]]
- [[testy/2026-10-16-kampania-nvidia]]
- [[raport-09-chmura-5060ti]]
- [[sm-86-89-120]]
- [[nvfp4]]
- [[lekcja-fit-mtp-16gb]]
