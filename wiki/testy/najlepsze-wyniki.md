---
typ: test
tags: [testy, wyniki, rekordy, tabela]
aktualizacja: 2026-11-22
zrodlo: wiki/tools/tabele.py (pola frontmattera notatek)
status: aktualne
---
# Najlepsze wyniki: model × karta (tabela z notatek)

**Najlepszy zmierzony wynik każdej pary model i karta dla każdej metryki, z warunkami, datą i notatką źródłową; generuje tools/tabele.py.**

<!-- TABELE:START -->
Wygenerowano 2026-11-27 przez `tools/tabele.py` z pól `wynik`/`wyniki` 333 trójek; poprawiaj notatkę źródłową, nie tę tabelę.

## Ternary Bonsai 2 27B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod | **44.75 t/s** | prism PTQ1_0, 6.8 GB VRAM | 2026-10-16 | [[bonsai]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP n1 | **60,02 t/s** | prism PTQ1_0 @64k | 2026-11-07 | [[rtx-3060]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP n2 | **58,31 t/s** | prism PTQ1_0-mtp-lean, ctx 204 800 | 2026-11-07 | [[rtx-3060]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP n2 ctx 204 800 | **58,31 t/s** | prism, fill PASS | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod PTQ1_0 | **44.75 t/s** | fork prism | 2026-10-16 | [[raport-09-chmura-3060]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod Q2_0 | **35.51 t/s** | nasz fork | 2026-10-16 | [[raport-09-chmura-3060]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod T=1 | **35.5 t/s** | Q2_0 repack fork (A1 33.1) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | KLD PL do BF16 | **0.508 KLD** | E1 | 2026-10-18 | [[bonsai]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | PPL | **8.6171 PPL** | Q2_0 upstream/fork | 2026-10-16 | [[bonsai]] |

## Ternary Bonsai 2.5 27B Uncensored: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, prism Q2_0 + MTP n2, KV q4_0 | **77.7 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, topka-bonsai PM4 + env produkcji + MTP n2 + słownik draftu 64k, ctx 262144 | **106.0 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=0,7, topka-k157 PM4 + env produkcji + MTP n2 + słownik 64k, ctx 262144 | **116.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod bez spekulacji, topka-best PM4, ctx 262144 | **70.6 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod bez spekulacji, topka-k157 PM4 | **76.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 (Q4 160 tok.), prism Q2_0 + MTP n2 | **117.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 (Q4), MTP n2 + ngram-mod | **188.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | edycja/kopia kodu T=0 (copy_bench short), topka-k157 | **446.4 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | edycja/kopia kodu T=0 (copy_bench short, mediana), topka-best PM4 + MTP n2 + lookup W16 + słownik 64k | **426.1 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | konfiguracja Dogukana (temp 1,0) na topka-best, MTP n2 | **121.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | llama-bench tg128 bez spekulacji, Q2_0 | **54.9 t/s** |  | 2026-11-25 | [[bonsai-2-5-uncensored]] |

## Drafter DFlash2 dla Qwen3.8-27B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3090 [[rtx-3090]] | dekod pl-kod T=1 | **109.2 t/s** | Magnitude, Q8_0 | 2026-10-16 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod EN | **115.7 t/s** | n=6, cache q8_1 | 2026-10-09 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod EN kod | **104.8 t/s** | n=6, runda 5 | 2026-10-15 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mediana T=0 | **90.6 t/s** | PL/EN, n=6, 285 W | 2026-10-10 | [[drafter-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mediana T=1 | **71.9 t/s** | PL/EN, n=6 | 2026-10-10 | [[drafter-dflash]] |

## Gemma 4: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod | **37,38 t/s** | 12B q8_0 ctx 262 144 | 2026-11-07 | [[rtx-3060]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod mediana | **138.3 t/s** | 26B-A4B Q4_K_XL, LM | 2026-10-21 | [[gemma-4]] |

## Głowica MTP Qwen3.8-27B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | akceptacja held-out | **3.266 tok/krok** | n=4, głowica fabryczna | 2026-10-16 | [[glowica-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | akceptacja offline | **3.04 tok/krok** | n_draft=4, 69 207 tokenów | 2026-10-12 | [[glowica-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=1 | **102.7 t/s** | MTP n=4 | 2026-10-15 | [[glowica-mtp]] |

## Gyro-Coder: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Strix Halo [[strix-halo]] | KLD do Q8_0 | **0.118 KLD** | C++, -c 2048 | 2026-10-24 | [[gyro-coder]] |

## Inkling 2 Mini: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain | **49,5 t/s** | po rundach 1–6 duetu | 2026-11-21 | [[inkling-2-mini]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod tg64 | **26,9 t/s** | AtomicChat AD-Q4_K, stock PR #32695, eco 2200 | 2026-11-21 | [[inkling-2-mini]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp2048 | **1125 t/s** | AD-Q4_K, PR #32695 | 2026-11-21 | [[inkling-2-mini]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp512 | **1333 t/s** | AD-Q4_K, PR #32695 | 2026-11-21 | [[inkling-2-mini]] |

## LFM2.5-24B-A2B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod | **102,47 t/s** | UD-IQ3_XXS ctx 131 072 | 2026-11-07 | [[rtx-3060]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod | **263.9 t/s** | nasz silnik (A0 180.2) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod T=1 | **263.9 t/s** | Q5_K_M fork (A1 176.0) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 3090 [[rtx-3090]] | serwer A2p | **263.9 t/s** | profil Ampere | 2026-10-16 | [[raport-09-chmura-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | sweep fork | **291.6 t/s** | (Magnitude 209.0) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64 64k | **208.12 t/s** | kvq CUDA, q8_0 (bez 159.65) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64@64k | **208,12 t/s** | kvq-mma f08dc78bb | 2026-10-16 | [[fattn-kvq]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod | **149.4 t/s** | QAD-Q4_0 | 2026-10-20 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | serwer | **149.4 t/s** | QAD-Q4_0 | 2026-10-20 | [[raport-29-4060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[rtx-5060-ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod serwer | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[lfm2-5-24b-a2b]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod T=1 | **207.86 t/s** | Q4_K_M fork (A1 144.47) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | serwer | **226.8 t/s** | QAD-Q4_0 | 2026-10-16 | [[raport-09-chmura-5060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | sweep 32k fork | **205.1 t/s** | (Magnitude 157.8) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | tg64 64k | **155.77 t/s** | kvq CUDA, Q4_K_M (bez 119.82) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy bez lookup | **288.2 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy lookup W16 | **312.4 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy lookup W8 | **334.7 t/s** | T=0 | 2026-10-19 | [[raport-24d-lfm-lookup]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat | **274.1 t/s** | topka (upstream 146.8) | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 | **173 t/s** | Q5_K_M, KV q4_0, bez MTP | 2026-10-14 | [[lfm-baza]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod | **293.7 t/s** | amd-opt | 2026-10-15 | [[rx-7900-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod budżet myślenia | **292.9 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod narzędzia omp | **294.3 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain PM4 off | **259.3 t/s** |  | 2026-10-19 | [[trwala-siatka-bez-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain PM4 on | **293.7 t/s** |  | 2026-10-19 | [[trwala-siatka-bez-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain tg128 | **292,1 t/s** | PM4 replay | 2026-10-14 | [[pm4-replay]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod reasoning_control | **292.9 t/s** | sampler fast (było 256.9) | 2026-10-15 | [[2026-10-15-sampler]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod spec_sweep | **293.7 t/s** | Q5_K_M, 3404 µs/token | 2026-10-16 | [[2026-10-16-budzet-lfm-megakernel]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MoE down Q5_K produkcja | **11.64 µs** | moebench | 2026-10-18 | [[2026-10-18-lfm-moe-negatywne]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | odczyt sesji 53k z SSD | **0,53 s** | slot-save-path | 2026-10-18 | [[cache-sesji-na-dysku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 | **6180 t/s** | fork | 2026-10-14 | [[lfm-baza]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 64k | **14.6 s** | (Magnitude 32.7 s) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp16384 | **6680 t/s** | ub 2048 (ub 512 5654) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **7148 t/s** | ub 2048 (ub 512 6108) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | serwer lfm none | **218.6 t/s** | łatki 0048–0052 | 2026-10-14 | [[lfm-runda-1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep | **293.7 t/s** | KV q8_0 | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep lfm none T=1 | **293.75 t/s** | PM4 replay | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **293.7 t/s** | Q5_K_M, KV q8_0 | 2026-10-15 | [[stan-2026-10-15]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | start sesji agenta | **230 ms** | CACHE_SHARE_MIN=1024 (było 1357) | 2026-10-18 | [[2026-10-18-cache-promptu-agenta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | sweep plain | **322.9 t/s** | Q4_K_M (Magnitude 219.6) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 | **292.22 t/s** | MOE_GU_BLOCK 7c5b2a116 (=0 291.26) | 2026-10-18 | [[2026-10-18-lfm-moe-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 98k | **191.4 t/s** | KV q8_0, kvq q8 (baza 152.4) | 2026-10-14 | [[lfm-runda-3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 górna granica | **323.97 t/s** | PM4_UB down,mmvq1 bez synchronizacji | 2026-10-18 | [[2026-10-18-pm4-ub-lfm]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 głębokość 0 | **262.1 t/s** | KV q8_0, łatki 0055–0059 | 2026-10-14 | [[lfm-runda-3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 głębokość 98304 | **212.95 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 KV q8_0 | **294.84 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | token 98k | **5,462 ms** | KV q8_0, kvq 0055 | 2026-10-14 | [[fattn-kvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | token tg | **3,402 ms** | po 0062 CONV_ROWS4 | 2026-10-14 | [[lfm-shortconv]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | TTFT 32k | **5690 ms** | ub 2048 (ub 512 6676) | 2026-10-18 | [[2026-10-18-lfm-ubatch-2048]] |

## LFM2.5-24B-A2B-Uncensored: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod | **267.3 t/s** | amd-opt | 2026-10-15 | [[rx-7900-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod llama-bench | **268.27 t/s** | GGML_HIP_MOE_GU_BLOCK | 2026-10-18 | [[lfm2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **6291 t/s** |  | 2026-10-15 | [[lfm2-5-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **267.3 t/s** | AD-Q5_K_M, KV q8_0 | 2026-10-15 | [[stan-2026-10-15]] |

## NVIDIA Nemotron 3.5 Bolt 74B-A9B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3090 [[rtx-3090]] | dekod DFlash | **141.1 t/s** | IQ2_XXS | 2026-10-16 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod DFlash T=1 | **141.1 t/s** | tuned fork, IQ2_XXS n_max 5 | 2026-10-16 | [[2026-10-16-nemotron-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod plain | **87.2 t/s** | A0 | 2026-10-16 | [[nemotron-3-5-bolt-74b-a9b]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg128 | **96.7 t/s** | fork nowe łatki (było 91.1) | 2026-10-16 | [[2026-10-16-nemotron-3090]] |

## Qwen3.5-9B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | code-edit | **239.0 t/s** | fork CUDA gałąź cuda-v070-5060ti, 1 runda | 2026-10-16 | [[qwen3-5-9b]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | prefill 64k | **2343 t/s** | fork CUDA | 2026-10-16 | [[qwen3-5-9b]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | sweep | **121.0 t/s** | fork CUDA, 1 runda | 2026-10-16 | [[qwen3-5-9b]] |

## Qwen3.6-35B-A3B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod mediana | **115.9 t/s** | LM | 2026-10-20 | [[qwen3-6-35b-a3b]] |

## Qwen3.8-27B: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | czat T=1 T' | **38.6 t/s** | UD-Q2_K_XL, c 36864, COUPLED=1 | 2026-10-20 | [[raport-31-3060-3080]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP n2 T=0 | **34,0 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 144 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | code-edit | **348.9 t/s** | cuda-topka2 | 2026-10-20 | [[raport-27-3090-final]] |
| NVIDIA RTX 3090 [[rtx-3090]] | code-edit fork | **105.3 t/s** | 4.91 tok/krok, 46.6 ms/krok (Magnitude 141.9) | 2026-10-16 | [[2026-10-16-magnitude-rozklad-wygranej]] |
| NVIDIA RTX 3090 [[rtx-3090]] | copy 64k fork | **69.7 t/s** | 4.51 tok/krok (Magnitude 80.2) | 2026-10-16 | [[2026-10-16-magnitude-rozklad-wygranej]] |
| NVIDIA RTX 3090 [[rtx-3090]] | czat T=1 | **93.3 t/s** | cuda-topka2 lookup W16 + verify | 2026-10-20 | [[raport-27-3090-final]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod | **78.0 t/s** | nasz silnik (A0 38.9) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod 262k T=0 | **51.1 t/s** | fork kvqleana, UD-Q4_K_XL | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod krótki T=0 | **82.9 t/s** | fork kvqleana, UD-Q4_K_XL, 350 W | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP | **78.0 t/s** | A2 | 2026-10-16 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP 59k | **89.75 t/s** | kvq CUDA (bez 70.33) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP ctx 262 144 | **79,97 t/s** | UD-Q4_K_XL, fork+kvq+lean, fill PASS | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP n2 T=0 | **89,5 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 418 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP n2 T=0 przy 95,6k | **71,8 t/s** | ctx 139 264 | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP T1 | **79,97 t/s** | fork+kvq+lean UD-Q4_K_XL 262 144 | 2026-11-07 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP T=1 | **93.3 t/s** | topka czat | 2026-10-19 | [[rtx-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod MTP@59k | **89,75 t/s** | kvq-mma | 2026-10-16 | [[fattn-kvq]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod pick Enigmy ctx 245 760 | **61,49 t/s** | pin b11856 | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 3090 [[rtx-3090]] | kopia 64k | **245 t/s** | topka CUDA | 2026-10-19 | [[raport-24e-nvidia-runda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | krok DFlash2 | **64 ms** |  | 2026-10-19 | [[raport-24j-router]] |
| NVIDIA RTX 3090 [[rtx-3090]] | krok MTP | **46.5 ms** |  | 2026-10-19 | [[raport-24j-router]] |
| NVIDIA RTX 3090 [[rtx-3090]] | mvs | **300.5 t/s** | UD-Q6_K_M | 2026-10-20 | [[raport-31-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | prefill 130k → 262k | **420 t/s** | fork kvqleana | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | prefill 64k fork | **888 t/s** | (Magnitude 744) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 3090 [[rtx-3090]] | prefill ~11k | **1386 t/s** | kvqlean | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 3090 [[rtx-3090]] | spec_sweep A2 | **78.0 t/s** | fork + słownik draftu, 300 W | 2026-10-16 | [[raport-09-chmura-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | sweep T=1 fork | **65.7 t/s** | cuda-3090-opt (Magnitude 65.7, upstream 49.2) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64 64k | **39.14 t/s** | kvq CUDA f08dc78bb, q4_0 (bez 28.61) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| NVIDIA RTX 3090 [[rtx-3090]] | tg64@64k | **39,14 t/s** | kvq-mma f08dc78bb | 2026-10-16 | [[fattn-kvq]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | code-edit | **170.9 t/s** | cuda-topka2 | 2026-10-20 | [[raport-29-4060ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | czat T=1 | **35.4 t/s** | Q3_K_XL, cuda-topka2, 100 W | 2026-10-20 | [[raport-29-4060ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | czat T=1 T' | **50.8 t/s** | UD-IQ4_XS, KV q4_0, 32k | 2026-10-20 | [[raport-31-4060ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod czat T=1 | **35.4 t/s** | UD-Q3_K_XL | 2026-10-20 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod MTP n2 | **36,30 t/s** | ISTA IQ3_XXS-mtp lean, ctx 229 376 | 2026-11-07 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod MTP n2 ctx 229 376 | **36,30 t/s** | ISTA IQ3_XXS-mtp, b12110lean, fill PASS | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | dekod plain | **24,02 t/s** | ISTA ctx 217 088 | 2026-11-07 | [[rtx-4060-ti]] |
| NVIDIA RTX 4060 Ti 16 GB [[rtx-4060-ti]] | mvs T' | **188.6 t/s** | UD-IQ4_XS | 2026-10-20 | [[raport-31-4060ti]] |
| NVIDIA RTX 4080 SUPER [[rtx-4080-super]] | dekod MTP n4 T=0 | **107,3 t/s** | GSQ IQ3_XXS-mtp, kvqlean, 278 W | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 4080 SUPER [[rtx-4080-super]] | prefill ~11k | **1862 t/s** | kvqlean | 2026-11-19 | [[2026-11-19-k118-nvidia-pelna-moc]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | czat T=1 T | **62.6 t/s** | UD-IQ4_XS 32k, 150 W | 2026-10-20 | [[raport-31-5060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod | **51.66 t/s** | nasz silnik (A0 28.07) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP | **54,33 t/s** | fork+kvq+lean UD-Q3_K_XL ctx 98 304 | 2026-11-07 | [[rtx-5060-ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP ctx 196 608 | **49,44 t/s** | ISTA IQ3_XXS-mtp, fork+kvq+lean | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP n2 T=0 | **54,2 t/s** | GSQ IQ3_XXS-mtp, kvqlean, ctx 8192, 180 W | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP n2 T=1 | **51,0 t/s** | GSQ IQ3_XXS-mtp, kvqlean, ctx 8192 | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP n=2 | **51.7 t/s** | UD-Q3_K_XL 32k | 2026-10-18 | [[2026-10-18-e1-kwanty-27b-kld]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod MTP T=1 | **51.66 t/s** | UD-Q3_K_XL fork (A1 37.32) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | dekod plain | **31,9 t/s** | GSQ IQ3_XXS-mtp, kvqlean | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | mvs | **244.2 t/s** | UD-IQ4_XS | 2026-10-20 | [[raport-31-5060ti]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | pp576 ub 16 | **306,41 t/s** | v1.0.0 (b11856 278,98) | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | prefill ~11k | **828 t/s** | GSQ IQ3_XXS-mtp, kvqlean | 2026-11-17 | [[2026-11-17-k114-nvidia-sufit]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | spec_sweep T=1 MTP n2 | **45,62 t/s** | ISTA IQ3_XXS-mtp, v1.0.0, 150 W | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | spec_sweep T=1 MTP n3 | **40,32 t/s** | b12359, 160 W | 2026-11-14 | [[2026-11-14-k103-llamacpp-v1-nvidia]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | sweep fork | **58.0 t/s** | Q3_K_XL (upstream 43.5) | 2026-10-16 | [[2026-10-16-magnitude-vs-fork]] |
| NVIDIA RTX 5060 Ti 16 GB [[rtx-5060-ti]] | tg64 64k | **25.69 t/s** | kvq CUDA, Q3_K_XL q8_0 (bez 20.61) | 2026-10-16 | [[2026-10-16-kvq-cuda]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | akceptacja głowicy MTP | **3.04 tok/krok** | UD-Q4_K_XL, amd-opt c90db29c6 | 2026-10-12 | [[2026-10-12-mtp-trening-faza1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | bufor MTP ROCm0 | **40.28 MiB** |  | 2026-11-06 | [[raport-65-vram-rezerwa-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | code-edit | **419.9 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | copy 64k | **141.2 t/s** | ROCm MTP (Magnitude 63.7) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat | **115.8 t/s** | PM4 WA=2 + GUARD (baza 110.8) | 2026-10-19 | [[raport-26-kolejka-gpu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 | **115.6 t/s** | PAIR2 (było 115.1) | 2026-10-20 | [[2026-10-20-podsumowanie-nocy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 baza | **115.1 t/s** |  | 2026-10-20 | [[raport-24w-pair2]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | czat T=1 PAIR2=1 | **115.6 t/s** |  | 2026-10-20 | [[raport-24w-pair2]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1.7k | **136.5 t/s** | sam MTP, LOOKUP=0 | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1.7k T=0 | **126.0 t/s** | K3 | 2026-10-13 | [[2026-10-13-k3-host]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 94k | **70.9 t/s** | po kvq, MTP n=4 T=0 | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 94k T=0 | **100.6 t/s** | KV draftu q4_0 | 2026-10-14 | [[2026-10-14-prefill-k5-t3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod copy T=0 | **355.0 t/s** | W16 (MTP4 163.4) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod deep 32630 tok. | **111.3 t/s** | Enigma | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod DFlash n=6 T=0 | **90.6 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod DFlash n=6 T=1 | **71.9 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod Enigma uczciwy bench | **97.8 t/s** | effort low (baseline 35.0) | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod long 30k T=0 | **373.5 t/s** | W16 (MTP4 156.7) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP | **113,2 t/s** | blok MTP IQ4_XS, 28.14 ms/krok | 2026-10-18 | [[latki-spekulacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP 27k bitexact | **102.66 t/s** | (prod 111.77) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP budżet myślenia | **107.0 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=4 | **101.7 t/s** | K4 WMMA d3a0973ae | 2026-10-13 | [[2026-10-13-k4-i-hw-queues]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=4 T=1 | **102.6 t/s** | po T1, 29.36 ms/krok | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 | **105.4 t/s** | K4 WMMA d3a0973ae | 2026-10-13 | [[2026-10-13-k4-i-hw-queues]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 T=0 | **86.3 t/s** | Vulkan 285 W | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 T=1 | **81.1 t/s** | Vulkan | 2026-10-10 | [[2026-10-10-sweep-mtp-dflash]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP narzędzia omp | **113.2 t/s** | sampler fast | 2026-10-15 | [[sampler-fast-path]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP reasoning_control | **109.5 t/s** | sampler fast (było 101.6) | 2026-10-15 | [[2026-10-15-sampler]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=0 | **91.8 t/s** | Vulkan RADV + słownik 64k, n=5 | 2026-10-09 | [[2026-10-09-pierwsze-pomiary]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=0.7 | **118.3 t/s** | COUPLED=1 (off 112.7) | 2026-10-18 | [[2026-10-18-sprzezone-probkowanie-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 | **120.54 t/s** | spec_sweep, topka-q63 | 2026-11-05 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 bez sprzężenia | **107.6 t/s** |  | 2026-10-20 | [[raport-24p-sprzezone-t1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 SPEC_COUPLED=1 | **111.4 t/s** |  | 2026-10-20 | [[raport-24p-sprzezone-t1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mvs T=0 | **433.0 t/s** | topka-next coupled=1 + host-gap (było 420.2) | 2026-10-20 | [[2026-10-20-podsumowanie-nocy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mvs T=1 | **375.8 t/s** | W16 (MTP4 166.1) | 2026-10-18 | [[2026-10-18-lookup-ogon]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain tg128 | **43.2 t/s** | amd-opt | 2026-10-15 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod po odtworzeniu slotu | **116.1 t/s** | topka-q63 | 2026-11-05 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod serwer 94k | **70,9 t/s** | KV q4_0, kvq 0011 | 2026-10-12 | [[fattn-kvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod spec_sweep T=1 | **123,6 t/s** | stock, topka-q63 UD-Q4_K_XL | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod ~32k | **111.6 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | energia | **2,07 J/token** | sclk 2200 (stock 2,27) | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | fill 255k | **492.5 t/s** | topka-q70, Uncensored | 2026-11-09 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | koszt haka MTP prefill 32k | **768 ms** | 2.2% TTFT | 2026-10-18 | [[2026-10-18-hak-mtp-i-checkpointy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok B | **27.40 ms** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok MTP4 mvs | **29.62 ms** |  | 2026-10-19 | [[raport-24k-koszt-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok prozy T=1 | **27.38 ms** | 2.63 tok/krok, stara metryka | 2026-10-20 | [[raport-36-xtx-roadmap]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok spec_sweep RPB=1 | **28.80 ms** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok Vulkan 0007–0010 | **41.46 ms** | Qwen UD | 2026-10-12 | [[vulkan-mmvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok W16 mvs | **35.61 ms** |  | 2026-10-19 | [[raport-24k-koszt-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | ms/krok MTP T=1 | **41.46 ms** | Vulkan łatki MMVQ | 2026-10-12 | [[2026-10-12-vulkan-krok-po-kroku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs | **433.8 t/s** | topka f9b84bcfa | 2026-10-21 | [[raport-43-integracja]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs A | **428.49 t/s** |  | 2026-10-21 | [[raport-54-mniej-granic]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs B ATTN_PREP_MT+KVQ_FWHT_GATE | **428.55 t/s** |  | 2026-10-21 | [[raport-54-mniej-granic]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs bez GPU verify | **410.4 t/s** |  | 2026-10-19 | [[raport-24m-weryfikacja-gpu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs GPU verify | **420.1 t/s** | f2217bac7 | 2026-10-19 | [[raport-24m-weryfikacja-gpu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | odczyt sesji 53k z SSD | **2,51 s** | slot-save-path, MTP | 2026-10-18 | [[cache-sesji-na-dysku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pasmo weryfikacji n=5 | **762 GB/s** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 | **1123.2 t/s** | epilog MMQ 0070 (baza 1099.5) | 2026-10-15 | [[runda-6]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 MMQ YDB=2 (wycofane, YDB=0 1097) | **1066 t/s** |  | 2026-10-15 | [[qwen-runda-5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp5 d32768 bitexact | **133.8 t/s** | (prod 152.1) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 128k | **708 t/s** | q63 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 12k | **940 t/s** | sclk 2200 (stock 1030) | 2026-11-06 | [[2026-11-06-eco-sweep-sclk]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 29.5k | **943 t/s** | K5+T3 | 2026-10-14 | [[2026-10-14-prefill-k5-t3]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 32k | **969 t/s** | q63 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 94k | **767 t/s** | K5+T3 0040-0045 | 2026-10-14 | [[prefill-mmq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill Enigma | **1041 t/s** | kandydat enigma | 2026-11-05 | [[enigma-uczciwy-benchmark]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **1123,2 t/s** | MMQ epilog 0070 | 2026-10-15 | [[mmq-epilog]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill zimny 27k | **31.9 s** | cache promptu domyślny | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prompt 94k + 1000 tok. | **165 s** | ROCm (Vulkan 260 s) | 2026-10-12 | [[2026-10-12-rocm-vs-vulkan]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | proza E0 | **78.93 t/s** |  | 2026-10-21 | [[qwen3-8-27b]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | proza E0 T=1 | **78.93 t/s** | produkcja, thinking off | 2026-10-20 | [[metryka-prozy-e0]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pytanie uzupełniające 27k | **0.7 s** | cache promptu | 2026-10-12 | [[2026-10-12-cache-promptu-i-a7]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec blok MTP IQ4_XS | **113.2 t/s** | 5 seedów (Q6_K 109.4) | 2026-10-18 | [[raport-16f-xtx-szybkie]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep | **109.0 t/s** | produkcja (fork 74.5) | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep baza | **111.4 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep bitexact | **108.3 t/s** | 365af3e5e (prod 107.7) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep MMVQ_OCC | **110.8 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep MMVQ_OCC serializacja | **104.3 t/s** |  | 2026-10-20 | [[raport-24n-mmvq-n5]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep qwen mtp T=1 | **108.82 t/s** | PM4 | 2026-10-14 | [[lfm-runda-4-pm4]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **120.50 t/s** | topka-q63 c0576e3e8 | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 1 seed | **105.1 t/s** | topka | 2026-10-19 | [[2026-10-19-build-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 A | **113.8 t/s** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 B przełączniki hosta | **117.9 t/s** |  | 2026-10-20 | [[raport-24o-luki-hosta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | start serwera | **6.5 s** | topka f9b84bcfa (baza 39.8) | 2026-10-21 | [[raport-43-integracja]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | start sesji agenta | **1612 ms** | CACHE_SHARE_MIN=1024 (było 8019) | 2026-10-18 | [[2026-10-18-cache-promptu-agenta]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | sufit odczytu | **926 GB/s** |  | 2026-10-20 | [[raport-24r-mmvq-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | sweep T=1 | **100.0 t/s** | ROCm MTP (Magnitude Vulkan 50.1) | 2026-10-18 | [[2026-10-18-magnitude-vulkan-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | szczyt VRAM fill 255k | **23367 MiB** |  | 2026-11-06 | [[raport-65-vram-rezerwa-mtp]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | T=0 reasoning | **154.2 t/s** | DRAFT_N=5 (baza 144.4) | 2026-10-20 | [[raport-35-xtx-eksperymenty]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 bitexact | **41.79 t/s** | 365af3e5e (prod 43.17) | 2026-10-16 | [[2026-10-16-bit-exact]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 wide off | **40.86 t/s** |  | 2026-10-20 | [[raport-24f-mmvq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 wide=2 | **40.41 t/s** |  | 2026-10-20 | [[raport-24f-mmvq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | trening MTP | **2.3 k tok/s** | bf16 K=4 T=2048, szczyt 12.1 GiB | 2026-10-12 | [[2026-10-12-mtp-trening-faza1]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | TTFT 32k MTP | **35050 ms** | (bez spekulacji 33619) | 2026-10-18 | [[2026-10-18-hak-mtp-i-checkpointy]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura agenta S2-turn2 | **197 ms** | CKPT_VRAM=2 | 2026-10-20 | [[raport-38-ckpt-vram]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | utworzenie checkpointu | **14.9 ms** | CKPT_VRAM=2 | 2026-10-20 | [[raport-38-ckpt-vram]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 2k | **6.40 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 32k | **9.50 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 64k | **12.45 ms** | llama-bench KV q4_0 | 2026-10-18 | [[koszt-szerokosci-weryfikacji]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | VRAM | **22319 MB** | lean reserve MTP (było 23360) | 2026-11-05 | [[2026-11-05-q63-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | weryfikacja n=16 | **35.0 ms** | WMMA 0037 | 2026-10-13 | [[wmma-small-n]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | weryfikacja n=9 | **32.1 ms** | WMMA 0037 | 2026-10-13 | [[wmma-small-n]] |

## Qwen3.8-27B-Uncensored: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3090 [[rtx-3090]] | czat | **75.3 t/s** | cuda-topka2 | 2026-10-20 | [[raport-27-3090-final]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | bench.py skill-io c1 | **110,3 t/s** | T 0,6, 6 × 512 tok. | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1,7k | **128,0 t/s** | SHORT_TAIL=32 (KILL, produkcja 135,4) | 2026-11-14 | [[2026-11-14-k104-krotki-ogon-promptu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 1,7k T=0 | **129,23 t/s** | xtxbench A/A, produkcja | 2026-11-09 | [[xtxbench-szybki-ab]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 199k T=0 | **95.81 t/s** | KVQ_ONCE=1 (KILL, baza 94.12) | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 255k | **78,7 t/s** | MTP n=4 eco 2200 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod 94k T=0 | **122.04 t/s** | KVQ_ONCE=1 (baza 120.97) | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod HumanEval+ ważony | **174,2 t/s** | T=0, MTP n4 + lookup | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP | **115,3 t/s** | PM4 replay | 2026-10-14 | [[pm4-replay]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=4 T=1 | **105.0 t/s** | po T1, 28.28 ms/krok | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP n=5 T=1 | **108.4 t/s** | po T1 | 2026-10-14 | [[2026-10-14-t1-t2-draft]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod MTP T=1 | **115.5 t/s** | amd-opt spec_sweep | 2026-10-15 | [[rx-7900-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod mvs T=0 | **414.8 t/s** | topka lookup W16, PM4=0 | 2026-10-19 | [[2026-10-19-build-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod plain tg128 | **44.0 t/s** |  | 2026-10-15 | [[qwen3-8-27b-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod po fillu 222k | **86,3 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod po fillu 255k | **73,6 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod sesja omp 0–32k | **127,2 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod sesja omp 128–160k | **95,8 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod sesja omp ważone | **120,8 t/s** | final mode, do 139k | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod spec_sweep T=1 mediana | **118,3 t/s** | final mode | 2026-11-06 | [[2026-11-06-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod T=0 1,7k | **131,2 t/s** | LLAMA_SPEC_LOOKUP=0 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod ważony evalplus | **162,0 t/s** | T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | dekod ważony jakość-mini | **142.4 t/s** | T=0 | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | FA na krok przy 199k | **11.32 ms** | rocprofv3, ONCE=0 | 2026-11-08 | [[2026-11-08-kvq-once-profil]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | fill 255k | **493,4 t/s** | FA D256 VAR 83, Q4_K_M, KV q4_0 (baza 466,3) | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | greedy 256 tok. | **106,4 t/s** | final mode | 2026-11-06 | [[2026-11-06-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | HumanEval pass@1 | **97,6 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | HumanEval+ pass@1 | **92,7 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | jakość-mini 255/290 | **87.9 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | krok Vulkan 0007–0010 | **39.92 ms** |  | 2026-10-12 | [[vulkan-mmvq]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | llama-bench pp d128k | **486,3 t/s** | VAR 83 (baza 459,5) | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MBPP+ pass@1 | **80,2 %** | topka-q70, effort low, T=0 | 2026-11-09 | [[2026-11-09-evalplus-qwen-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MMLU-Pro 140 pytań | **82.1 %** | effort low | 2026-11-09 | [[2026-11-09-jakosc-mini-qwen-unc]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MMVQ draftów na krok 1,7k | **1,93 ms** | ślad rocprofv3 | 2026-11-07 | [[2026-11-19-k111-k123-krok-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | MMVQ weryfikacji na krok 1,7k | **20,16 ms** | ślad rocprofv3, PM4 off, topka-q63 | 2026-11-07 | [[2026-11-19-k111-k123-krok-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | ms/krok MTP T=1 | **39.92 ms** | Vulkan łatki MMVQ | 2026-10-12 | [[2026-10-12-vulkan-krok-po-kroku]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | ms/krok spec_sweep T=1 | **26,86 ms** | eco 2200 (stock 26,32) | 2026-11-06 | [[2026-11-06-eco-szybki-bench]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | mvs | **434.9 t/s** | topka | 2026-10-20 | [[raport-wyniki-xtx-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pierwszy dekod K-001 | **130,7 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | pp4096 Q6K_WIDE (KILL, −0,01%) | **1000,6 t/s** | Q4_K_M, topka-q63, ABBA | 2026-11-07 | [[2026-11-07-q6k-mmq-skale]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 12k | **916,0 t/s** | eco 2200 (stock 1036,8) | 2026-11-06 | [[2026-11-06-eco-szybki-bench]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 130k | **650,8 t/s** | igły 3/3 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 222k | **527,0 t/s** | igły 3/3, topka-q70, KV q4_0 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 255k | **465,1 t/s** | topka-q63 eco 2200, KV q4_0 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 32k | **865,61 t/s** | xtxbench A/A | 2026-11-09 | [[xtxbench-szybki-ab]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 4242 tok. przy 103k | **498,6 t/s** | final mode | 2026-11-06 | [[2026-11-06-sesja-uzytkownika-final-mode]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill 94k | **762 t/s** | K5+T3 0040-0045 | 2026-10-14 | [[prefill-mmq-fa]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill long 32k | **859,1 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill pp4096 | **1109 t/s** |  | 2026-10-15 | [[qwen3-8-27b-uncensored]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prefill ~16k bench.py | **932,9 t/s** | topka-q70 | 2026-11-19 | [[2026-11-19-k109-k110-k106-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prompt krótkiego żądania mediana | **139,1 ms** | AP_TIMING | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | prompt krótkiej tury mediana | **148,5 ms** | SHORT_TAIL=32 (produkcja 148,7) | 2026-11-14 | [[2026-11-14-k104-krotki-ogon-promptu]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep | **115.5 t/s** | produkcja | 2026-10-19 | [[benchmarki-przed-po-2026-10-19]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 | **119,2 t/s** | VAR 83 | 2026-11-09 | [[2026-11-08-fa-d256-prefill]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 1 seed | **106.9 t/s** | topka | 2026-10-19 | [[2026-10-19-build-topka]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | spec_sweep T=1 mediana | **119,3 t/s** | topka-q70 | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tg128 | **268.27 t/s** | MOE_GU_BLOCK (=0 264.60) | 2026-10-18 | [[2026-10-18-lfm-moe-pasmo]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tokenizacja mediana 82–119k | **6,6 ms** | TOK_CACHE+PARSE_INC (baza 14,0) | 2026-11-08 | [[2026-11-08-l1-tokenizacja-parser]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | top-1 zgodny kvq vs f16 | **97,595 %** | topka-q70 | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura agenta mediana | **12 441 ms** | #30137 + huge pages (A 13 413 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura agenta mediana 76–112k | **12 029 ms** | topka-q70 (baza 13 413) | 2026-11-09 | [[2026-11-09-wdrozenie-topka-q70]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | tura poza prefillem | **1 619 ms** | TOK_CACHE+PARSE_INC (baza 1 704) | 2026-11-08 | [[2026-11-08-l1-tokenizacja-parser]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | update cache | **437,9 ms** | #30137 + huge pages (A 1 321,7 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 2k | **7,1 ms** | llama-bench, PM4, VAR 83 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | V16 − V5 przy 32k | **10,1 ms** | llama-bench, PM4, VAR 83 | 2026-11-14 | [[2026-11-14-k002-k003-k013-xtx]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | VRAM szczyt 255k | **23367 MiB** | ctx 262144 | 2026-11-06 | [[2026-11-06-ctx-262k-fit]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | zapis wpisu cache | **266,6 ms** | #30137 + huge pages (A 1 055,5 ms) | 2026-11-09 | [[2026-11-08-cachesave-30137]] |
| AMD Radeon RX 7900 XTX [[rx-7900-xtx]] | średnie KLD kvq vs f16 | **0,003862 KLD** | wikitext-2 c 8192, ub 5 (standard 0,004522) | 2026-11-19 | [[2026-11-19-k125-k001-xtx]] |

## Underdog Saluki 27B 1.0: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod | **38.2 t/s** | topka (baza 24.0) | 2026-10-20 | [[raport-27-3090-final]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP | **33.1 t/s** | 170 W (bez MTP 23.0) | 2026-10-18 | [[2026-10-18-e1-kwanty-27b-kld]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod pick Enigmy ctx 135 168 | **22,23 t/s** | pin b11856 | 2026-11-07 | [[2026-11-07-kampania-nvidia-vast]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod plain | **23.4 t/s** | nasz silnik, bez MTP | 2026-10-16 | [[saluki]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod T=1 | **23.4 t/s** | IQ2-mix fork (A1 22.3) | 2026-10-16 | [[2026-10-16-kampania-nvidia]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | KLD PL do BF16 | **0.320 KLD** | E1 | 2026-10-18 | [[saluki]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | PPL wikitext-2 | **7.6665 PPL** | 64×512 | 2026-10-16 | [[saluki]] |

## Swift 1.5: najlepsze wyniki na kartach

| karta | metryka | najlepszy | warunki | data | źródło |
|---|---|---|---|---|---|
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | akceptacja MTP | **0.55 akceptacja** | głowica Qwena, E1 | 2026-10-18 | [[swift-1-5]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | dekod MTP | **25.15 t/s** | Swift IQ3_XXS W3, 120 W, 16k | 2026-10-18 | [[2026-10-18-e1-kwanty-27b-kld]] |
| NVIDIA RTX 3060 12 GB [[rtx-3060]] | KLD PL do Qwen-Q8 | **0.0019 KLD** | Swift-Q8, E1 | 2026-10-18 | [[swift-1-5]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod 262k T=0 | **68.3 t/s** | qwen-warp v0.8.0 INT4 | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
| NVIDIA RTX 3090 [[rtx-3090]] | dekod krótki T=0 | **121.2 t/s** | qwen-warp v0.8.0 INT4 | 2026-11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]] |
<!-- TABELE:END -->

## Powiązane
- [[testy/_hub|Testy i pomiary]]
- [[REKORDY]]
- [[KOLEJKA-TESTOW]]
