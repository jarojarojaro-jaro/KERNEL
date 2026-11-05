# 63 — rejestr wątków (każdy wątek z pakietu 2026-11-03 osobno)

Każdy wątek dostaje osobny werdykt i osobną akcję. Stan: ✅ zbadany i ujęty w syntezie ([63-SYNTEZA.md](63-SYNTEZA.md), sekcja 2 = werdykty, sekcja 3 = plan „#N”). 🚫 = akcja odpada przez regułę „tylko bezstratne” (2026-11-05).

| # | Wątek | Raport | Stan | Akcja |
|---|---|---|---|---|
| 1 | gpu.nz: tabela VRAM Qwen3.8 vs Qwen3 32B (16/64 warstw z KV) | 63a | ✅ | przyciąć nadmiar KV 10.7 KiB/token; estymator Enigmy na 29.1 KiB/token (plan #9, #17) |
| 2 | Open Kernel Challenge (+110 miejsc, triki, człowiek-koordynator) | 63e | ✅ | holdout promptów w `spec_sweep` (plan #13) |
| 3 | Auto-research-agent PR #6 (harness, prompty CUDA) | 63e | ✅ | hash buildu/env w wierszach `spec_sweep` (plan #13) |
| 4 | getsupers „experiments” (H200 per sekunda) | 63e | ✅ | nic |
| 5 | NVIDIA Qwen3.8-Flash-Next-NVFP4 | 63d | ✅ | nic (🚫 inny kwant) |
| 6 | LithosAI MI355X 2100 t/s/user | 63c | ✅ | nic (liczba przy założonej akceptacji) |
| 7 | Strata PR #4366 (DeepSeek prefill 5090 +39%) | 63a | ✅ | lekcja „ciepły vs zimny” w wiki (zrobione) |
| 8 | Strata 0.2.7 KVA | 63d | ✅ | 🚫 odrzucone (stratne); lekcja „needle to nie bramka” |
| 9 | wafer-ai gpu-perf-engineering-resources (PTX/SASS) | 63e | ✅ | nic (delta zero od R21b) |
| 10 | gau-nernst QR na B200 | 63e | ✅ | `klab isa`: stan GDN w VGPR (wejście do plan #21) |
| 11 | elpis (262k na 3090) | 63a | ✅ | „bramka przed danymi” do fabryki; kernel: plan #8 |
| 12 | MTP w llama.cpp: głębokość zależna od karty (closedcircuit) | 63d | ✅ | kandydaci MTP n=1…4 w Enigmie (plan #4) |
| 13 | CUDA-and-Kernels (navaneethkrishnansuresh) | 63e | ✅ | nic |
| 14 | Soft-MTP | 63d | ✅ | nic |
| 15 | Alibaba RTP-LLM / MNN-LLM | 63b | ✅ | chude checkpointy wg RTP #1574 (plan #6) |
| 16 | cheaptokens: KV q5_1 → atencja na CPU | 63c | ✅ | strażnik `splits` w Enigmie (plan #12) |
| 17 | basalt vs Strata (5090) | 63a | ✅ | typ głowicy LFM, ew. sito Q8_0 (plan #23) |
| 18 | colibri v2.1.0 | 63b | ✅ | `LLAMA_SERVER_PREFIX_LOG` (plan #12); planer na ubatch (plan #17) |
| 19 | TensorFold + mlx.fast / cuda.fast (przyspiesz Qwen 27B) | 63a | ✅ | watch `plan.hip` #1932 |
| 20 | skyzh/tiny-llm | 63e | ✅ | ledger 6 pytań w `patch-manifest.json` (plan #13) |
| 21 | Experiments / harness: CUDA best practices | 63e | ✅ | nic (mamy) |
| 22 | Maya v1.1.39 + wszystkie release'y | 63b | ✅ | port #607 „wspólny początek” (plan #7); `agent_bench.py` (plan #6) |
| 23 | delta-inference-engine | 63b | ✅ | diagnostyka Windows w Enigmie (plan #24) |
| 24 | 100-days-of-inference-engineering | 63e | ✅ | watch |
| 25 | rapidmlx: LSA prefill + gęsta atencja/MTP w decode | 63d | ✅ | nic (🚫 rzadki prefill) |
| 26 | Latent Sparse Attention (paper, kod, wagi) | 63d | ✅ | 🚫 odrzucone |
| 27 | RDNA-FAST (nasza karta) | 63c | ✅ | lean reserve + cap LDS (plan #5, w toku); słownik dynamiczny (plan #18) |
| 28 | pentacoxian tweet → Qwen-QSA-llama.cpp | 63c | ✅ | 🚫 port QSAPort zaparkowany (liczby z 4090, zmienia wyjście) |
| 29 | benchlab: silniki 27B na 3090, HyperQwen | 63a | ✅ | profil kod/T=0 MTP n=6–7 (plan #15); punkt wspólny 3090 (plan #25) |
| 30 | llama.cpp v0.9.0 | 63c | ✅ | poprawki MTP w topce (plan #5, w toku TopkaQuick63); pin Enigmy → b12110 (plan #16) |
| 31 | Together Compiler / TKCC (Simran Arora) | 63e | ✅ | flagi bez restartu serwera (plan #20) |
| 32 | Baseten: DeepSeek V4.1 Flash (fuzje, PDL, host loop) | 63e | ✅ | koszt kroku od `n_ctx` vs długości (w plan #3) |
| 33 | Anthropic FlashProve | 63e | ✅ | „rachunek modelu” w Enigmie (plan #12) |
| 34 | sf-tensor: PTX w Lean | 63e | ✅ | nic |
| 35 | 10 papierów GPU (FA1–3, Stream-K, Paged, MARLIN, Ring, FlashInfer…) | 63e | ✅ | profil kroku przy 199k (plan #3) |
| 36 | vLLM v0.33.0 (FLy, XPress, DSpark, ROCm 10, MonoKernel) | 63c + 63d | ✅ | buffer loads w `kvq` (plan #22); LFM DSpark (plan #10); 🚫 FLy, Octave |
| 37 | YASAKANI 1220 t/s na 5090 | 63a | ✅ | watch; zestaw zadań na XTX (plan #25) |
| 38 | Reward hacking w optymalizacji inferencji (Overshoot i źródła) | 63e | ✅ | G1 w toku (EngineBenchFair), potem G2–G9 (plan #2) |
| 39 | LSA: wersja chińska (port na Qwen 27B, 72,4×) | 63d | ✅ | nic |
| 40 | Soft-MTP („MTP Done Right”, alphaxiv) | 63d | ✅ | nic |
| 41 | LLM Compressor 0.15 (HIGGS, QAD, REAP) | 63d | ✅ | 🚫 odrzucone (zmienia wagi) |
| 42 | Strata v0.2.10 (Flash-Next na 8 GB) | 63a | ✅ | drabina degradacji pamięci w Enigmie (plan #17) |
| 43 | MegaCapybara / NInfer / ignis / mkyt (rekordy z porównania YASAKANI) | 63a | ✅ | test równoległych tool-calli w bramce (plan #13); `kvq` plan #8 |
| 44 | Termika: cap GPU/CPU (0xwhitemage, NullBurn, Blackfold) — dopisane 2026-11-05 | synteza + decyzja 2026-11-05 | ✅ (źródła niebadane; test zatwierdzony) | test „eco”: cap taktowania rdzenia GPU, pamięć bez zmian, bez undervoltu (plan #26) |
