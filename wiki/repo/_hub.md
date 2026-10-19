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
## Notatki (67)

- [[a-hamdi-gpu|a-hamdi/GPU (100 dni nauki)]] — Dziennik nauki CUDA „100 days” (HEAD `a9b0a17c`, 2025-04-27) z błędnymi benchmarkami; werdykt: niska.
- [[atrex-kernel-agent|alibaba/atrex-kernel-agent (AKA)]] — Orkiestrator agentów kodujących dla jednego operatora naraz (HEAD `5ad94ff`, 2026-10-14, v0.3.0); bierzemy narzędzia pomiarowe; werdykt: średnia (narzędzia).
- [[deepgemm|deepseek-ai/DeepGEMM]] — Biblioteka kerneli tensor-core DeepSeek (HEAD `1fc9c66`, 2026-10-14); bierzemy harmonogram „Mega MoE” i potok kafli; werdykt: średnia.
- [[auto-gpu-kernel|Dogacel/auto-gpu-kernel (i fork ludoo)]] — Harness agenta do pisania kerneli (upstream `db02153`, 2026-09-12) i fork `ludoo` z GDN o geometrii naszego Qwena; werdykt: średnia.
- [[mixbench|ekondis/mixbench]] — Mikrobenchmark „mixed operational intensity” (master `a8cab0c`, 2026-08-04) jako plan pomiaru sufitu pasma; werdykt: średnia.
- [[exllamav3|ExLlamaV3 (EXL3)]] — Silnik z formatem EXL3 pochodnym od QTIP (trellis), z ROCm in-tree od 2026-10 i obsługą Qwen3.8-27B; w niezależnym teście przy ~140k kontekstu wypadł najlepiej end-to-end.
- [[falkon|FalkonML/falkon]] — Biblioteka regresji z jądrem (Nyström + PCG) liczona blokami, także out-of-core (HEAD `04f168e`, 2026-05-13); werdykt: brak.
- [[flashinfer|flashinfer-ai/flashinfer]] — Biblioteka kerneli do serwowania LLM (HEAD `2895577`, 2026-10-14, v0.7.2), tylko NVIDIA; bierzemy wzorce atencji; werdykt: średnia.
- [[flashinfer-bench-starter-kit|flashinfer-bench-starter-kit i FlashInfer-Bench]] — Szablon zgłoszenia do konkursu MLSys 2026 (commit `75ccd05`, 2026-04-25) i format FlashInfer-Trace; werdykt: średnia (proces).
- [[amd-opt|Gałąź amd-opt (produkcja ROCm)]] — Gałąź produkcyjna dla RX 7900 XTX: 70 commitów (łatki 0001–0070) liniowo na upstream `e60eff95f` z 2026-10-09, HEAD `f61994f58` (2026-10-15, epilog MMQ).
- [[amd-opt-v070|Gałąź amd-opt-v070 (rebase na v0.7.0)]] — Łatki `amd-opt` przeniesione na upstream v0.7.0 (`620d2225c`, 2026-10-15): 70 commitów, HEAD `8c942e5a9` (2026-10-16), worktree `~/wt/rebase070`.
- [[batch-invariant|Gałąź batch-invariant (LLAMA_SPEC_BITEXACT)]] — Gałąź `batch-invariant` @ `6e261fdb4` (2026-10-16) = `cuda-v070` + 4 commity: tryb `LLAMA_SPEC_BITEXACT`, w którym dekod spekulacyjny daje te same bity co zwykły.
- [[cuda-compat-galaz|Gałąź cuda-compat]] — `cuda-compat` @ `7b2680760` to `amd-opt` + 4 commity, które pozwalają zbudować fork dla CUDA bez zmiany kodu gfx1100 (74 commity nad `e60eff95f`).
- [[mtp-train|Gałąź mtp-train (llama-mtp-extract)]] — Gałąź `mtp-train` @ `532fd1057` (2026-10-16) = `cuda-v070` + 1 commit: narzędzie `llama-mtp-extract` do danych treningowych głowicy MTP.
- [[nemotron-3090|Gałąź nemotron-3090]] — Gałąź `nemotron-3090` @ `e46d34e0e` (2026-10-16, worktree `~/wt/nemotron-opt`) = `cuda-3090-opt` (`3da7a02ec`) + 1 commit z przełącznikami pod Nemotron 3.5 Bolt na Ampere.
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
- [[hyperqwen|HyperQwen (syv-ai, dawniej qwen38-27b-rtx3090)]] — vLLM z łatkami dla Qwen3.8-27B na RTX 3090 (250 W): lookup sufiksu z kontekstu (LABD), blok 16, łańcuchy i prefix cache dla hybryd; 381 t/s dotyczy kopiowania dokumentu verbatim, a dla nas to głównie górny pułap dla 3090.
- [[ik-llama-cpp|ik_llama.cpp (ikawrakow)]] — Trwały fork llama.cpp (MIT, od 2024-06) z kwantami IQK/trellis (KT), mocny na CPU i MoE; pełne wsparcie tylko CPU i CUDA, Vulkan i HIP częściowo, port IQK do upstreamu odrzucony.
- [[inferrous|inferrous (bitemyapp): silnik w Ruście z kernelami w Ruście]] — Badawczy silnik (Apache-2.0/MIT, 2 commity, 3 gwiazdki) z 31 kernelami napisanymi w Ruście (cuda-oxide → PTX, sm_120), tylko Qwen3-8B W8A8 na RTX PRO 6000 Max-Q: 182.3 / 178.2 / 170.5 t/s (prompt 5 / 129 / 512) wobec vLLM Humming 144.4 / 143.3 / 142.9 – rzetelne 84% pasma, ale bez porównania z llama.cpp i z własną bramką zgodności z PyTorch, która nie przechodzi (rel. L2 logitów 9–11%) (raport 21g, 2026-10-19).
- [[hipfire|Kaden-Schutt/hipfire]] — Silnik inferencji Rust + HIP tylko pod AMD (HEAD `1ff5182`, 2026-10-14, v0.4.2) z replayem tokenu jako bufor PM4; werdykt: średnia–wysoka.
- [[kernelguard|KernelGuard (GPU MODE)]] — Zestaw 62 deterministycznych detektorów oszustw w zgłoszeniach kerneli, każdy z fixture’em historycznego hacka, plus „physics floor” z roofline’u; odsetek oszukanych zgłoszeń spadł z 3.45% do 0.37% w 32 dni.
- [[kernel-tuner-repo|KernelTuner/kernel_tuner]] — Pythonowy framework autotuningu (commit `8e71bbf`, 2026-10-08, v1.5.0) jako silnik przeszukiwania tablic per kształt; werdykt: średnia.
- [[knlp-lm-head|knlp: certyfikowana głowica LM przy dekodowaniu]] — Metoda: słownik w 256 blokach, offline baza PCA stanów (r ≈ 0.36·d), cień int8 `W_U·B` i normy reszt wierszy; w dekodowaniu górna granica każdego logitu z Cauchy'ego–Schwarza, a bloki otwiera się, aż najlepszy dokładny logit przewyższy granice reszty – bezstratnie. U nich na W7900 (gfx1100) głowica Qwen2.5-7B ×1.97 przy batch 1, ~5× mniej bajtów, batch 4/8 ×1.36/×1.41.
- [[laya-mlx|laya-mlx i Laya (model decyzyjny)]] — Laya (Convai Innovations) to nieautoregresywny encoder decyzyjny 322–421M, a laya-mlx (mizorewww) jego port MLX; za wolne do decyzji per token.
- [[how-to-optimize-in-gpu|Liu-xiandong/How_to_optimize_in_GPU]] — Dydaktyczne „drabiny optymalizacji” CUDA dla V100 (HEAD `5d2def3e`, 2023-07-29); werdykt: niska.
- [[llama-moe-cache-mib|llama.cpp `--moe-cache-mib`: cache ekspertów MoE w VRAM]] — Upstream PR #29887 (scalony 2026-10-07, port z qvac-fabric) dodaje cache LRU ekspertów MoE w VRAM przy modelu w RAM: Flash-Next Q4_0 na 4090 25.0 → 40.7 t/s, na 5090 30.8 → 67.8 t/s; jest w bazie naszego forka (`common/arg.cpp:2795`) (raport 21g, 2026-10-19).
- [[lucebox|Luce-Org/lucebox]] — Serwer inferencji C++ z forkiem ggml i spekulacją DFlash2 (HEAD `54132ca`, 2026-10-14) na tym samym modelu i drafterze co my; werdykt: średnia.
- [[magnitude|Magnitude (silnik Seismic z autotunem 60 s)]] — Własny silnik w Ruście z językiem kerneli „Seismic” (Metal, CUDA, Vulkan, CPU; bez HIP/ROCm), który stroi kernele 60 s przy pierwszym załadowaniu z bramką błędu α = 8 (nie bitową); najbliższy bezpośredni konkurent, ale bez AMD natywnie, bez bitowej bramki i bez MoE offload.
- [[megakernele-prior-art|Megakernele: Hazy, MPK i inne (prior art)]] — Hazy Megakernels (interpreter instrukcji per SM ze stronicowanym SMEM) i MPK/Mirage (kompilator tGraph) osiągają 71–80% pasma przy batch 1, wobec ≤ 50% kernel-per-op; na RDNA3 publicznego megakernela nie ma.
- [[kernelagent|meta-pytorch/KernelAgent]] — Wieloagentowy system Meta zamieniający PyTorch na kernele Triton (HEAD `e0647170`, 2026-07-15); bierzemy strukturę pętli; werdykt: średnia (proces).
- [[smokinggun|morluto/smokinggun: nie stosuje się do naszej pracy]] — Mimo nazwy narzędzie nie szuka przyczyn regresji: to statyczny skaner wzorców złożoności w pętlach kodu CPU (tree-sitter, 13 języków, bez `.cu`/`.cuh`/`.hip`) plus porównanie zaimportowanych wyników benchmarków (hyperfine, pyperf, Google Benchmark, criterion, JMH, pprof, Perfetto) z gate'em eligible/blocked/inconclusive; MIT, TypeScript/Node, ostatni commit 2026-08-29 (raport 21k, 2026-10-19).
- [[mtplx|MTPLX: współbieżny MTP dla wielu agentów]] — Silnik z MTP w kohortach (3/8 strumieni) deklaruje 1.6–2.25× na strumień dla 2 agentów względem zwykłego batchingu AR; wspiera LFM2 (wydanie 2.6.0, stan 2026-10-19).
- [[llama-cpp-fork|Nasz fork llama.cpp: repozytoria, gałęzie i worktree]] — Cała praca kernelowa żyje w jednym repo git `~/llama-master` z worktree w `~/wt/`; gałąź produkcyjna to `amd-opt` (70 commitów na upstream `e60eff95f`), a jej odpowiednik na v0.7.0 to `amd-opt-v070`.
- [[cuda-rust|NVIDIA/cuda-rust]] — Oficjalna platforma NVIDIA „CUDA dla Rusta” (HEAD `bc46b1f`, 2026-10-12); daje tylko liczbę odniesienia; werdykt: brak.
- [[cutile-python|NVIDIA/cutile-python (cuTile)]] — Kafelkowy DSL NVIDIA kompilowany do Tile IR (commit `d9d8520`, 2026-10-13); bierzemy odpowiednik PDL na AMD; werdykt: niska–średnia.
- [[nvidia-open-gpu-kernel-modules|NVIDIA/open-gpu-kernel-modules]] — Otwarte moduły jądra NVIDIA (commit `ca2d03e`, wydanie 615.78.08, 2026-10-07) czytane pod kątem zarządzania VRAM; werdykt: średnia.
- [[tilegym|NVIDIA/TileGym]] — Przykładowe kernele NVIDIA w CUDA Tile (commit `c742afc`, 2026-10-09), z łatkami dla Qwen3.5 i LFM2; werdykt: niska.
- [[blocksparse|openai/blocksparse]] — Biblioteka kerneli blokowo-rzadkich OpenAI (HEAD `89074c5`, 2020-07-13), martwa od 2020; werdykt: niska.
- [[tokamax|openxla/tokamax]] — Kernele Google/DeepMind w JAX + Pallas (HEAD `b500ee4`, 2026-10-14), kod inference tylko pod TPU; werdykt: niska.
- [[pplx-kernels|perplexityai/pplx-kernels i pplx-garden/lily]] — Kernele MoE all-to-all Perplexity (porzucone, HEAD `f70d1eb7`) i następca `lily` (MoE decode na jednym GPU); werdykt: niska.
- [[prism-llama-cpp|PrismML-Eng/llama.cpp (fork pod Bonsai)]] — Fork llama.cpp od PrismML potrzebny do formatów PQ2_0 i PTQ1_0 modelu Ternary Bonsai 2 27B; u nas klon „prism” testowany na RTX 3060.
- [[project-maya|Project Maya (mw00): silnik jednego modelu GLM-5.3-Flash]] — Pochodna Straty (nie fork llama.cpp) uruchamiająca tylko GLM-5.3-Flash (321B, 18B aktywnych) z ekspertami w trzech warstwach VRAM → przypięty RAM → NVMe (O_DIRECT); 81 t/s na RTX PRO 6000 = 41% pasma; liczby z README to najlepsze wiersze z różnych wersji, bez llama.cpp (raport 21g, 2026-10-19).
- [[rsr-27b|RSR-27B (IntelligenceLab): Qwen3.8-27B po RSR + RL]] — Wydany model `IntelligenceLab/RSR-27B` (Apache-2.0, `qwen3_5`, 64 warstwy, 27.78 mld parametrów BF16) to Qwen3.8-27B dostrojony na przepisanych trajektoriach RSR + „dodatkowe RL”; tensory `mtp.*` (15) i `model.visual.*` są skopiowane z bazy (`model-missing-from-origin-*.safetensors`), więc głowica MTP nie pasuje do zmienionego pnia (2026-10-19).
- [[sakana-agentic-scientist|Sakana AI-Scientist-v3 (Agentic Scientist)]] — Orkiestracja agentów do badań, w której kod wymusza izolację ewaluacji (harness, hashe, osobne kontenery), a naukę rozstrzyga LLM; brak jakiejkolwiek statystyki istotności.
- [[kernelbench|ScalingIntelligence/KernelBench]] — Benchmark kerneli pisanych przez LLM (HEAD `423217d9`, 2026-03-05); bierzemy lepszą bramkę poprawności; werdykt: średnia (proces).
- [[strata|Strata (Niko1221/Strata)]] — Silnik C++/CUDA/HIP pod jeden model MoE z offloadem (HEAD `a0116b27`, 2026-10-12, tag v0.1.43.1), studiowany jako wzór metodologii autora.
- [[suffixdecoding|SuffixDecoding / ArcticInference: globalne drzewa sufiksów]] — Spekulacja bez modelu draftującego z drzew sufiksów budowanych z promptów i wcześniejszych wyjść (także między żądaniami); na workloadach agentowych do ×5.3, ×2.8 względem EAGLE-2/3 (arXiv 2411.04975, w vLLM jako „suffix”).
- [[tensara|tensara/tensara]] — Platforma zawodów w pisaniu kerneli (commit `fae96618`, 2026-07-21) z silnikiem oceny na Modal; werdykt: niska.
- [[tensorfold|TensorFold (ashhart/TensorFold)]] — Serwer Zig z kontraktem dokładności („drafted == plain”) dla 7 rodzin modeli (HEAD `0efbd447`, 2026-10-12, v1.0.8; aktualizacja do v1.0.11 2026-10-14).
- [[tilelang|tile-ai/tilelang]] — Python DSL do kafelkowych kerneli (HEAD `19da924`, 2026-10-14); na RDNA3 tylko f16 WMMA, bez iu8; werdykt: niska.
- [[ako4all|TongmingLAIC/AKO4ALL i AKO4X]] — Protokół dla agenta optymalizującego kernele (commit `bbd0e1c`, 2026-09-15), nie kod kerneli; werdykt: średnia (proces).
- [[tqllm|tqLLM (turbo-tan): silnik CUDA dla Qwen3.8]] — Własny silnik C++/CUDA tylko dla Qwen3.5/3.8 na NVIDIA (sm_86/89/120/121) z kwantem TQ3_4S, DFlash2 i dokładną spekulacją greedy; rekord 273.1 t/s na 3090 w LocalMaxxing przy T=0 z prywatnego buildu, a per bajt plain decode ma parytet z nami.
- [[mkernel|uccl-project/mKernel]] — Wielo-GPU trwałe kernele z UC Berkeley (HEAD `97e916b`, 2026-10-01); zostają tylko wzorce synchronizacji; werdykt: niska.
- [[vllm-kimi-k3-specialized-decode|vLLM Kimi K3 „specialized decode” (nie megakernel)]] — Fuzja w CuTe DSL z komunikacją TP na 16×GB300: 23 → 13 kerneli na warstwę i 130 → 69 µs na warstwę, krok B1 bez spekulacji 7.38 → 3.90 ms (1.89×), czyli `[SZACUNEK]` 8% → 15% pasma HBM – reżim latencji i komunikacji, nie pasma (PR #61867, 2026-10).
- [[vllm-monokernel|vLLM MonoKernel (RFC #60904)]] — Jeden trwały kernel na warstwę dekodera bez bariery siatki: siatka 256 CTA × 512 wątków (1 CTA na CU MI355X), zależności przez „tagged pairs”, wagi niezależne od wejścia ładowane przed czekaniem, bounded waits; na razie tylko ROCm.
- [[speculators-specforge|vLLM speculators i SGLang SpecForge]] — Dwa narzędzia do trenowania drafterów (MTP, EAGLE-3); speculators to nasza ścieżka do fine-tune głowicy MTP.
- [[vllm-xpu-kernels|vllm-project/vllm-xpu-kernels]] — Kernele vLLM na Intel GPU w SYCL (HEAD `6b30c9b9`, 2026-10-14); bierzemy pomysł fuzji q/k-norm + RoPE + zapis KV; werdykt: niska.
- [[gpu-kernel-engineer-from-scratch|vukrosic/gpu-kernel-engineer-from-scratch]] — Niedokończony 48-tygodniowy kurs CUDA/Triton dla początkujących (HEAD `ba738db`, 2026-05-07); werdykt: brak.
<!-- AUTO:END -->
