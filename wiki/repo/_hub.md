---
typ: hub
tags: [repo, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Repozytoria

**Repozytoria i projekty, które przestudiowaliśmy, oraz nasze własne gałęzie i worktree.**

Cudze projekty: co robią i co od nich wzięliśmy. Nasze: fork `~/llama.cpp`, gałęzie `amd-opt*`, `cuda-*`, `opt-*`, worktree w `~/wt/`.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (49)

- [[a-hamdi-gpu|a-hamdi/GPU (100 dni nauki)]] — Dziennik nauki CUDA „100 days” (HEAD `a9b0a17c`, 2025-04-27) z błędnymi benchmarkami; werdykt: niska.
- [[atrex-kernel-agent|alibaba/atrex-kernel-agent (AKA)]] — Orkiestrator agentów kodujących dla jednego operatora naraz (HEAD `5ad94ff`, 2026-10-14, v0.3.0); bierzemy narzędzia pomiarowe; werdykt: średnia (narzędzia).
- [[deepgemm|deepseek-ai/DeepGEMM]] — Biblioteka kerneli tensor-core DeepSeek (HEAD `1fc9c66`, 2026-10-14); bierzemy harmonogram „Mega MoE” i potok kafli; werdykt: średnia.
- [[auto-gpu-kernel|Dogacel/auto-gpu-kernel (i fork ludoo)]] — Harness agenta do pisania kerneli (upstream `db02153`, 2026-09-12) i fork `ludoo` z GDN o geometrii naszego Qwena; werdykt: średnia.
- [[mixbench|ekondis/mixbench]] — Mikrobenchmark „mixed operational intensity” (master `a8cab0c`, 2026-08-04) jako plan pomiaru sufitu pasma; werdykt: średnia.
- [[falkon|FalkonML/falkon]] — Biblioteka regresji z jądrem (Nyström + PCG) liczona blokami, także out-of-core (HEAD `04f168e`, 2026-05-13); werdykt: brak.
- [[flashinfer|flashinfer-ai/flashinfer]] — Biblioteka kerneli do serwowania LLM (HEAD `2895577`, 2026-10-14, v0.7.2), tylko NVIDIA; bierzemy wzorce atencji; werdykt: średnia.
- [[flashinfer-bench-starter-kit|flashinfer-bench-starter-kit i FlashInfer-Bench]] — Szablon zgłoszenia do konkursu MLSys 2026 (commit `75ccd05`, 2026-04-25) i format FlashInfer-Trace; werdykt: średnia (proces).
- [[amd-opt|Gałąź amd-opt (produkcja ROCm)]] — Gałąź produkcyjna dla RX 7900 XTX: 70 commitów (łatki 0001–0070) liniowo na upstream `e60eff95f` z 2026-10-09, HEAD `f61994f58` (2026-10-15, epilog MMQ).
- [[amd-opt-v070|Gałąź amd-opt-v070 (rebase na v0.7.0)]] — Łatki `amd-opt` przeniesione na upstream v0.7.0 (`620d2225c`, 2026-10-15): 70 commitów, HEAD `8c942e5a9` (2026-10-16), worktree `~/wt/rebase070`.
- [[batch-invariant|Gałąź batch-invariant (LLAMA_SPEC_BITEXACT)]] — Gałąź `batch-invariant` @ `6e261fdb4` (2026-10-16) = `cuda-v070` + 4 commity: tryb `LLAMA_SPEC_BITEXACT`, w którym dekod spekulacyjny daje te same bity co zwykły.
- [[cuda-compat-galaz|Gałąź cuda-compat]] — `cuda-compat` @ `7b2680760` to `amd-opt` + 4 commity, które pozwalają zbudować fork dla CUDA bez zmiany kodu gfx1100 (74 commity nad `e60eff95f`).
- [[mtp-train|Gałąź mtp-train (llama-mtp-extract)]] — Gałąź `mtp-train` @ `532fd1057` (2026-10-16) = `cuda-v070` + 1 commit: narzędzie `llama-mtp-extract` do danych treningowych głowicy MTP.
- [[opt-gdn6|Gałąź opt-gdn6 (szybki kernel GDN, bitowy z konstrukcji)]] — Gałąź `opt-gdn6` @ `0d89ce56c` (2026-10-15): osobny szybki kernel GDN dla RDNA, zbudowany tak, by był bitowo identyczny; oba commity NIEZMIERZONE (brak GPU w tej rundzie).
- [[opt-mmq6|Gałąź opt-mmq6 (epilog MMQ, łatka 0070)]] — Gałąź `opt-mmq6` @ `ae1ef6a97` (2026-10-15): epilog skal Q4_K/Q5_K w MMQ RDNA3 w operacjach f32 parowalnych w VOPD, bitowo te same sumy; w raporcie oznaczone jako NIEZMIERZONE.
- [[opt-qwen5|Gałąź opt-qwen5 (runda 5 Qwena)]] — Gałąź `opt-qwen5` @ `2aa6999ed` (2026-10-15) z `c36fd2c87`: próby GDN fast i podwójnego bufora y w MMQ, obie wycofane, plus ablacja P0 prefillu MMQ.
- [[opt-samp|Gałąź opt-samp (sampler bez wolnych ścieżek)]] — Gałąź `opt-samp` @ `f4f0deae5` (2026-10-15) z łatkami 0065–0069: szybkie kandydatki top-k w samplerze także z gramatyką, wszystko pod wyłącznikami.
- [[tools6|Gałąź tools6 (LOO, kanarki KLD, Kernel Tuner)]] — Gałąź `tools6` @ `4db68c6ab` (2026-10-15) dodaje tylko hak kompilacji `MMVQ_TUNE_NWARPS_N1` dla Kernel Tunera; reszta rundy to narzędzia w `~/qwen-opt/tools/`.
- [[cuda-v070|Gałęzie cuda-v070, cuda-3090-opt, cuda-v070-5060ti, 3060-opt]] — Nasze łatki na v0.7.0 z poprawkami dla NVIDIA: `cuda-v070` @ `7a538d96f` = `amd-opt-v070` + 4 commity cuda-compat; z niej wychodzą gałęzie kampanii chmurowej na RTX 3090, 5060 Ti i 3060.
- [[galezie-rund|Gałęzie rund optymalizacji (opt-*)]] — Każda runda agentów pracowała w osobnym worktree i gałęzi `opt-*`; zwycięskie commity trafiały do `amd-opt`, reszta zostaje jako zapis eksperymentu.
- [[keops|getkeops/keops]] — Biblioteka symbolicznych redukcji map-reduce na GPU (HEAD `ef72bc90`, 2026-06-24), prekursor online-LSE; werdykt: niska.
- [[pygpubench|gpu-mode/pygpubench]] — Biblioteka do mierzenia krótkich kerneli niezaufanego kodu (HEAD `286841bf`, 2026-08-18); daje eksperyment z bitem DLC na RDNA3; werdykt: średnia.
- [[gpu-mode-reference-kernels|gpu-mode/reference-kernels]] — Definicje zadań i harness KernelBota GPU MODE (commit `f3295bb6`, 2026-09-17); ranking 2026 to nie źródło technik; werdykt: niska.
- [[ik-llama-cpp|ik_llama.cpp (ikawrakow)]] — Trwały fork llama.cpp (MIT, od 2024-06) z kwantami IQK/trellis, mocny na CPU i MoE, ale bez ROCm, Vulkan i Metal.
- [[hipfire|Kaden-Schutt/hipfire]] — Silnik inferencji Rust + HIP tylko pod AMD (HEAD `1ff5182`, 2026-10-14, v0.4.2) z replayem tokenu jako bufor PM4; werdykt: średnia–wysoka.
- [[kernel-tuner-repo|KernelTuner/kernel_tuner]] — Pythonowy framework autotuningu (commit `8e71bbf`, 2026-10-08, v1.5.0) jako silnik przeszukiwania tablic per kształt; werdykt: średnia.
- [[laya-mlx|laya-mlx i Laya (model decyzyjny)]] — Laya (Convai Innovations) to nieautoregresywny encoder decyzyjny 322–421M, a laya-mlx (mizorewww) jego port MLX; za wolne do decyzji per token.
- [[how-to-optimize-in-gpu|Liu-xiandong/How_to_optimize_in_GPU]] — Dydaktyczne „drabiny optymalizacji” CUDA dla V100 (HEAD `5d2def3e`, 2023-07-29); werdykt: niska.
- [[lucebox|Luce-Org/lucebox]] — Serwer inferencji C++ z forkiem ggml i spekulacją DFlash2 (HEAD `54132ca`, 2026-10-14) na tym samym modelu i drafterze co my; werdykt: średnia.
- [[kernelagent|meta-pytorch/KernelAgent]] — Wieloagentowy system Meta zamieniający PyTorch na kernele Triton (HEAD `e0647170`, 2026-07-15); bierzemy strukturę pętli; werdykt: średnia (proces).
- [[llama-cpp-fork|Nasz fork llama.cpp: repozytoria, gałęzie i worktree]] — Cała praca kernelowa żyje w jednym repo git `~/llama-master` z worktree w `~/wt/`; gałąź produkcyjna to `amd-opt` (70 commitów na upstream `e60eff95f`), a jej odpowiednik na v0.7.0 to `amd-opt-v070`.
- [[cuda-rust|NVIDIA/cuda-rust]] — Oficjalna platforma NVIDIA „CUDA dla Rusta” (HEAD `bc46b1f`, 2026-10-12); daje tylko liczbę odniesienia; werdykt: brak.
- [[cutile-python|NVIDIA/cutile-python (cuTile)]] — Kafelkowy DSL NVIDIA kompilowany do Tile IR (commit `d9d8520`, 2026-10-13); bierzemy odpowiednik PDL na AMD; werdykt: niska–średnia.
- [[nvidia-open-gpu-kernel-modules|NVIDIA/open-gpu-kernel-modules]] — Otwarte moduły jądra NVIDIA (commit `ca2d03e`, wydanie 615.78.08, 2026-10-07) czytane pod kątem zarządzania VRAM; werdykt: średnia.
- [[tilegym|NVIDIA/TileGym]] — Przykładowe kernele NVIDIA w CUDA Tile (commit `c742afc`, 2026-10-09), z łatkami dla Qwen3.5 i LFM2; werdykt: niska.
- [[blocksparse|openai/blocksparse]] — Biblioteka kerneli blokowo-rzadkich OpenAI (HEAD `89074c5`, 2020-07-13), martwa od 2020; werdykt: niska.
- [[tokamax|openxla/tokamax]] — Kernele Google/DeepMind w JAX + Pallas (HEAD `b500ee4`, 2026-10-14), kod inference tylko pod TPU; werdykt: niska.
- [[pplx-kernels|perplexityai/pplx-kernels i pplx-garden/lily]] — Kernele MoE all-to-all Perplexity (porzucone, HEAD `f70d1eb7`) i następca `lily` (MoE decode na jednym GPU); werdykt: niska.
- [[prism-llama-cpp|PrismML-Eng/llama.cpp (fork pod Bonsai)]] — Fork llama.cpp od PrismML potrzebny do formatów PQ2_0 i PTQ1_0 modelu Ternary Bonsai 2 27B; u nas klon „prism” testowany na RTX 3060.
- [[kernelbench|ScalingIntelligence/KernelBench]] — Benchmark kerneli pisanych przez LLM (HEAD `423217d9`, 2026-03-05); bierzemy lepszą bramkę poprawności; werdykt: średnia (proces).
- [[strata|Strata (Niko1221/Strata)]] — Silnik C++/CUDA/HIP pod jeden model MoE z offloadem (HEAD `a0116b27`, 2026-10-12, tag v0.1.43.1), studiowany jako wzór metodologii autora.
- [[tensara|tensara/tensara]] — Platforma zawodów w pisaniu kerneli (commit `fae96618`, 2026-07-21) z silnikiem oceny na Modal; werdykt: niska.
- [[tensorfold|TensorFold (ashhart/TensorFold)]] — Serwer Zig z kontraktem dokładności („drafted == plain”) dla 7 rodzin modeli (HEAD `0efbd447`, 2026-10-12, v1.0.8; aktualizacja do v1.0.11 2026-10-14).
- [[tilelang|tile-ai/tilelang]] — Python DSL do kafelkowych kerneli (HEAD `19da924`, 2026-10-14); na RDNA3 tylko f16 WMMA, bez iu8; werdykt: niska.
- [[ako4all|TongmingLAIC/AKO4ALL i AKO4X]] — Protokół dla agenta optymalizującego kernele (commit `bbd0e1c`, 2026-09-15), nie kod kerneli; werdykt: średnia (proces).
- [[mkernel|uccl-project/mKernel]] — Wielo-GPU trwałe kernele z UC Berkeley (HEAD `97e916b`, 2026-10-01); zostają tylko wzorce synchronizacji; werdykt: niska.
- [[speculators-specforge|vLLM speculators i SGLang SpecForge]] — Dwa narzędzia do trenowania drafterów (MTP, EAGLE-3); speculators to nasza ścieżka do fine-tune głowicy MTP.
- [[vllm-xpu-kernels|vllm-project/vllm-xpu-kernels]] — Kernele vLLM na Intel GPU w SYCL (HEAD `6b30c9b9`, 2026-10-14); bierzemy pomysł fuzji q/k-norm + RoPE + zapis KV; werdykt: niska.
- [[gpu-kernel-engineer-from-scratch|vukrosic/gpu-kernel-engineer-from-scratch]] — Niedokończony 48-tygodniowy kurs CUDA/Triton dla początkujących (HEAD `ba738db`, 2026-05-07); werdykt: brak.
<!-- AUTO:END -->
