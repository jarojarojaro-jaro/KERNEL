---
typ: meta
tags: [meta, zrodla, research, rejestr, inferencex, agentx, strata, tensorfold, magnitude, hipfire, dflash, lucebox]
aktualizacja: 2026-11-14
zrodlo: ~/KERNEL/product/research/01-konkurencja.md … 24b-draft-pelny-slownik.md (nagłówki, TL;DR, werdykty); ~/KERNEL/qwen-opt/research/{PLAN,drafters,algorithms,training,stepcost}.md; ~/KERNEL/qwen-opt/research/{repos,strata,tensorfold,v2,round6}/; ~/KERNEL/wiki/repo/*.md; ~/KERNEL/wiki/ludzie-firmy/*.md; ~/KERNEL/wiki/research/*.md; ~/AGENTS.md:14; ~/KERNEL/product/research/{21n,21o,24e,24g,24t,30}-*.md
status: aktualne
---
# Rejestr źródeł: co już przebadaliśmy (InferenceX, Strata, TensorFold, Magnitude, hipfire, DFlash…)

**Jeden wiersz na każde zewnętrzne źródło, które było przedmiotem badania (repo, silnik, praca, model, strona, wpis – np. InferenceX, Strata, TensorFold, Magnitude, hipfire, DFlash), z wersją, raportem, werdyktem i podpowiedzią, co sprawdzić przy następnym podejściu.**

Zasada (użytkownik 2026-10-19, [[KONWENCJE]]): **nie badamy drugi raz tego samego.** Przed researchem: `kb search <nazwa/URL>` + ten rejestr. Źródło już jest → badamy tylko DELTA od zapisanej wersji/commitu/daty. Po researchu dopisz albo zaktualizuj wiersz. Pomysły warte pomiaru na karcie trafiają jako pozycje `K-…` do [[KOLEJKA-TESTOW]]. Rekordy wydajności: [[REKORDY]]; podręcznik: [[podrecznik-gpu]].

Legenda: **2×/3×/4×** = źródło badane wielokrotnie; kolumna „delta” mówi, co dodało kolejne podejście (tu widać dublowanie pracy). Daty = data raportu. Raporty: `R21f` = `product/research/21f-*.md`; `Q:` = `qwen-opt/research/`. Zakres: przedmioty badania; linki cytowane tylko jako przypis (newsy, dokumentacja API, fora) zostają w raportach – szukaj ich `kb search <domena>`.

## Badane więcej niż raz (przegląd dublowania)

| źródło | podejścia | co dodało każde kolejne |
|---|---|---|
| Strata | Q:strata (10-13, `a0116b27` v0.1.43.1) → Q:strata/update-v0.1.44 (10-13, `ed4773eb`) → R21d/R21g (10-19, v0.1.44.1 `296b59d2`, v0.1.45 `477ac13c`) + R23e (RE kerneli) + R01/R03/R04 (konkurencja) → R21n (10-19, v0.2.0-beta `3d1fb480`, Gyro-S) | 2.: ścieżka Qwen3.6-35B-A3B, f-latency; 3.: KV na dysku, R9700 ×1.42, bariera LDS #3064, Flash-Next na XTX ~80 t/s; 4.: ISA pętli – nic lepszego niż nasze; 5.: 0.2.0 to w 55% aplikacja, silnik v0.1.45.3 – dla gfx1100 nic nowego (R21g mówił „0.2.0 nie istnieje” – wyszła później) |
| TensorFold | R01/R03 (10-15) → Q:tensorfold (10-13, `0efbd447` v1.0.8) → update-v1.0.11 (10-14, `2984ea01`) → R15c (v1.0.12 `833bbfcb`) → R21g (v1.1.0 `76aafcf2`) → R23e → R63a (`cde4fe7`) → R69b (`abc39af1` v1.2.5+) | każde podejście = nowa wersja; od v1.0.11 HIP zamrożony (1.1.0: 6 plików HIP, zero zmian) – dalej sprawdzać tylko NVIDIA + DFlash2; R63a/R69b: HIP tylko gfx1151/gfx1201, gfx1100 dalej brak |
| Magnitude | R15c (`1f54d5b7`) → R16d (head-to-head 3090/5060 Ti) → R16i (kod 0.2.9 `954d677d`) → R16j (Vulkan na XTX) → R16k (sprzężone próbkowanie) → R23e | 2.: liczby; 3.: przewaga = sufit DFlash2 + kontroler szerokości; 4.: na AMD ×1.42–×2.24 dla nas; 5.: port próbkowania; 6.: brak przewagi ISA |
| hipfire | R03 (warpfront/hipfire, v0.4.0) → Q:repos/30 (`1ff5182` v0.4.2) → R22-lucebox wzmianka → R23e (RE, 54.3 vs 43.2 t/s) | 3.: przewaga z formatu 4.25 bpw i fuzji, nie z ISA |
| DFlash / DFlash2 (z-lab) | R03 → Q:drafters (10-10) → Q:v2 → R14 (Nemotron) → R15b/R16d/R16i (u Magnitude) → R21a (DSpine vs DFlash2) | każde podejście ponownie opisuje drafter; nowa wiedza: tylko sufit bloku (7.3–7.8 tok/krok u Magnitude) i +4–7% τ DSpine |
| DSpine (Tencent) | R21a (8B, `07f326a`) → R67b (wydanie 27B, 11-07) → R69a (27B config, port Ajay9o9 `d493f84`) | 2.: tylko data i τ z karty; 3.: SWA 8192, port 323 linie, model XTX per klasa, krytyka liczb portu |
| qwen-warp | R63a §14 (`146a654`) → R69b (`689901c` v0.8.0) | 2.: DFlash2 w grafie, multiuser, agent z kopiowaniem −31% |
| lucebox | R01/R03 → Q:repos/22 (`54132ca`) → R15d (`6f2b179`, PFlash) | 3.: PFlash v2 stratny, KVFlash odrzucony |
| HyperQwen | R15b (`95ee3b6`) → R15d | 2.: prefill/łańcuchy; wynik ten sam |
| tqLLM | R15b → R15c (`23af3c9`) → R15f → R23e | 2.: audyt rekordu 273.1 t/s; 4.: ISA |
| SuffixDecoding (arXiv 2411.04975) | R02 → Q:algorithms → Q:v2 → R18 | każde podejście cytuje te same liczby (×5.3 agentowe) |
| ik_llama.cpp / exllamav3 | R03 → Q:algorithms/v2 → R15e → R18 → R23c (exllamav3 SASS) | 2.–4.: kwanty trellis; 5.: tylko hinty `LDG.E.EF` |
| vLLM | R03 → R15a (monokernel) → R21b → R21f (Kimi K3 PR #61867) | każdy raport inna część repo – OK, nie dublowanie |
| llama.cpp upstream | prawie każdy raport | baza; delta = `git log e60eff95f..` / od v0.7.0 `620d2225c..` |

## Silniki i serwery inferencji

| źródło | wersja / data | raport, notatka | werdykt (≤12 słów) | kluczowe liczby | następnym razem sprawdź |
|---|---|---|---|---|---|
| Actual Computer, silnik „e” (actual.computer) | R15c 10-16 | R15c, [[actual-computer]] | Tylko DGX Station GB300; na konsumenckich vendored llama.cpp. | – | czy wyszedł silnik na RTX/AMD |
| exllamav3 (github.com/turboderp-org/exllamav3) **3×** | R03, R15e, R18, R23c | [[exllamav3]] | EXL3 (QTIP trellis); ROCm in-tree od 2026-10. | najlepszy e2e ~140k kontekstu (test niezależny) | wydajność ROCm na gfx1100 |
| hipfire (github.com/Kaden-Schutt/hipfire, dawn. warpfront) **4×** | v0.4.0 (R03) → `1ff5182` v0.4.2 2026-10-14 | Q:repos/30, R23e, [[hipfire]] | Średnia–wysoka: replay PM4; przewaga z bajtów, nie ISA. | XTX plain 54.3 vs nasze 43.2 t/s; ~14.3 vs 16.83 GB/token | `git log 1ff5182..`; format MQ4G256V2 |
| HyperQwen (github.com/syv-ai/HyperQwen) **2×** | `95ee3b6` 2026-10-11 | R15b, R15d, [[hyperqwen]] | Lookup i szeroki blok dają nam mało. | 381 t/s (kopiowanie verbatim, 3090) | nowe łatki po `95ee3b6` |
| ik_llama.cpp (github.com/ikawrakow/ik_llama.cpp) **3×** | R03, R15e, R18 | [[ik-llama-cpp]] | Kwanty IQK/KT mocne na CPU/CUDA; HIP częściowo. | – | wsparcie HIP, kwanty KT |
| InferenceX / AgentX (SemiAnalysis; github.com/SemiAnalysisAI/InferenceX, InferenceX-app, inferencex.semianalysis.com) | `b9c6fc30` 2026-10-18; korpus AgentX v1.0 256k | R21f, [[raport-21f-inferencex]], [[qwen38-27b-inferencex]], [[agentx-harness]], [[ksztalt-ruchu-agentowego]] | Cenny kształt ruchu agenta, nie wyniki (syntetyczna treść, wymuszona AL). | 393 sesje Claude Code; Kimi K3 c=1: 1554 tok/s/GPU (10.1 wyjścia); Qwen3.8-27B H100 DSpark c=1 86.1 tok/s | `git log b9c6fc30..`; nowy korpus, prawdziwa AL; praca (2605.08513 to NIE ona) |
| inferrous (github.com/bitemyapp/inferrous) | `405bfd3` | R21g, [[inferrous]] | Badawczy, Rust→PTX, bez porównania z llama.cpp. | 182.3 t/s Qwen3-8B W8A8, 84% pasma | – (niski priorytet) |
| llama.cpp upstream (github.com/ggml-org/llama.cpp) | `e60eff95f` 10-09; v0.7.0 `620d2225c`; `f336359` 10-16 | prawie wszystkie, [[ggml-org]], [[llama-cpp-fork]] | Baza; cienki overlay łatek, nie twardy fork. | ~24 buildy/dzień | `git log` od ostatniego rebase; PR #29887 `--moe-cache-mib` już mamy |
| llama.cpp PR #29887 `--moe-cache-mib` | scalony 2026-10-07 | R21g, [[llama-moe-cache-mib]] | Jest w naszej bazie. | 5090 Flash-Next 30.8 → 67.8 t/s | – |
| lucebox (github.com/Luce-Org/lucebox) **3×** | `54132ca` 10-14 → `6f2b179` 10-15 | Q:repos/22, R15d, [[lucebox]] | Średnia: ten sam model i DFlash2; PFlash stratny. | PR #746 +27645/−2997 | `git log 6f2b179..` |
| Magnitude (github.com/magnitudedev/magnitude) **6×** | `1f54d5b7` (R15c) → 0.2.9 `954d677d` (R16i/j) | R15c, R16d, R16i, R16j, R16k, R23e, [[magnitude]], [[firma-magnitude]] | Najbliższy konkurent; wygrywa kopią/edycją dzięki DFlash2. | code-edit 1.35–1.56× dla nich; XTX Vulkan ×1.42–×2.24 dla nas | wersja >0.2.9: HIP? bramka bitowa? |
| MTPLX (mtplx.com, github.com/youssofal/MTPLX) **2×** | 2.6.0 (R18) | R01, R18, [[mtplx]] | MTP w kohortach; obsługuje LFM2. | 1.6–2.25× na strumień (2 agenci) | czy jest linux/ROCm |
| Project Maya (github.com/mw00/project-maya) **2×** | `a4e1ff0` 1.1.14–1.1.15 → `abc09c7` v1.1.16 (10-19, release notes) | R21g, [[project-maya]] | Pochodna Straty; 1.1.16 = DeepSeek-V4.1-Flash 748B z SSD/RAM offload, nic dla naszych modeli. | 81 t/s RTX PRO 6000 = 41% pasma; Maya-S 178 GB, top-1 92.6%, KL 0.12 (stratny) | tylko jeśli dodadzą gęsty 27B lub pomiar XTX |
| Strata (github.com/Niko1221/Strata) **6×** | `a0116b27` v0.1.43.1 → `ed4773eb` v0.1.44 → `296b59d2` v0.1.44.1 → `477ac13c` v0.1.45 (10-17) → `3d1fb480` v0.2.0-beta (silnik v0.1.45.3) → `e88ee39d` (10-19, +12 commitów: CI, dokumentacja, instalatory RX 7000/Strix Halo) | Q:strata/*, R21d, R21g, R23e, [R21n](../product/research/21n-strata-020-gyro.md), [[strata]] | Wzór metodologii; 0.2.0 = aplikacja (konkurent UX), dla gfx1100 nic; tylko Qwen3.8-Flash-Next (125B), DeepSeek nie obsługuje. | R9700 83.2 → 117.8 t/s; 0.2.0: +219k linii, silnik 6% | `git log e88ee39d..`; tylko HIP/gfx1100, KV, nowe modele; do sprawdzenia u nas: wątki = rdzenie fizyczne, rozgrzewka hipBLAS (TTFT) |
| TensorFold (github.com/ashhart/TensorFold) **7×** | `0efbd447` v1.0.8 → `2984ea01` v1.0.11 → `833bbfcb` v1.0.12 → `76aafcf2` v1.1.0 (10-18) → `cde4fe7` (11-05) → `abc39af1` v1.2.5+ (11-08) | Q:tensorfold/*, R15c, R21g, R23e, R63a, R69b, [[tensorfold]] | Kontrakt „drafted == plain”; HIP zamrożony, AMD nasze. | 1.1.0: 901 commitów, HIP +12/−9 | `git log abc39af1..` tylko HIP gfx1100 + Qwen3.8-27B DFlash2 na NVIDIA |
| tqLLM (github.com/turbo-tan/tqllm, tqllm.com) **4×** | `23af3c9` (R15c), `8c12e1a` | R15b, R15c, R15f, R23e, [[tqllm]] | Per bajt parytet z nami; rekord z prywatnego buildu. | 273.1 t/s na 3090 (T=0) | publiczny build rekordu |
| TideLM (github.com/raspy135/tideLM; przodek 0xBakeer/deepseek-v41-flash-spark `45a0caff`) | `92e1b186` (10-19) | [R28](../product/research/28-moe-offload-silniki.md) | Stratne podstawianie ekspertów; dla nas tylko dynamiczna głębokość MTP. | DS-V4.1 25.9/42.8 t/s na 2× Spark; GLM KL 0.11–0.17, top-1 ~89% | docs/gotchas.md (odrzucone), spec_depth.py |
| Xolotl (github.com/Indras-Mirror/Xolotl, fork Strata) | `c3324f89` (10-19) | [R28](../product/research/28-moe-offload-silniki.md) | 27 t/s = bias routingu + 2.4 bpw; stratne. | 552B 26.8 t/s 4090; dokładny routing 3.5 t/s; ppl 2.38→2.87 | tylko jeśli opublikują pomiar przy dokładnym routingu |
| vLLM (github.com/vllm-project/vllm) **4×** | R03, R15a, R21b, R21f | [[vllm-monokernel]], [[vllm-kimi-k3-specialized-decode]] | Monokernel tylko ROCm MI355X; Kimi K3 to reżim komunikacji. | K3: 7.38 → 3.90 ms/krok (1.89×) | monokernel na RDNA? |
| Inne silniki z R03 (mlc-llm, mistral.rs, candle, ktransformers, PowerInfer, onnxruntime-genai, LiteRT-LM, MNN, executorch, exllamav2, tabbyAPI, llamafile, koboldcpp, sglang-radeon, hipEngine, braidinfer) | R03 10-15; Q:v2 10-12 | R03, Q:v2/rr-engines-drafters, [[raport-03-silniki]] | Bazą zostaje llama.cpp; żaden nie bije na AMD. | – | tylko jeśli ktoś ogłosi gfx1100 |
| Forki llama.cpp pod RDNA (llama-cpp-rdna-boosts, llama.cpp-qwen35-rocm, nasone32 RDNA3-7900xtx-opt, QingYis llama-7900xtx, salvatoretrimarchi) | Q:v2 10-12, R01 | Q:v2/roadmap, Q:v2/rr-engines-drafters | rdna-boosts: adaptacyjne MTP (RDNA4) – pomysł, nie kod. | rdna-boosts code +28%, recall +61% | nowe commity w rdna-boosts |
| prism llama.cpp (github.com/PrismML-Eng/llama.cpp) | R09-3060, R10 | [[prism-llama-cpp]] | Potrzebny tylko dla PQ2_0/PTQ1_0 (Bonsai). | PQ2_0 → Q2_0 bezstratny repack | – |
| agentionai/llama.cpp (gitlab, `9aa51ce4`) + HF `agentionai/Qwen3.8-Flash-Next-Gyro-GGUF` (`aa0a0c3e`) + Strata issue #2938 (XTX IQ3_S) | 10-19 | [R21n](../product/research/21n-strata-020-gyro.md), [[raport-21n-strata-gyro]] | Gyro-S to próg 32 GB; nie testujemy teraz. | Gyro-S 1.708 bpw, plik 58.48 GB; #2938 82.5 t/s zawyżone (T=0, powtarzany akapit) | IQ3_S w naszym forku; kill < 50 t/s |
| TensorFold 1.1.0 na RTX 3090 (headless, MLX-4bit + DFlash2) | 10-19 | [R24e](../product/research/24e-nvidia-runda.md), [[raport-24e-nvidia-runda]] | Przegrywa z topką: kopia ×2.3, prefill 64k ×4.6 wolniej. | czat 73.9 vs 77.3; edycja 309 vs 317 t/s | DELTA nowej wersji tylko dla NVIDIA |

## Repozytoria kerneli, DSL i narzędzia

Przegląd 30 repo: Q:repos/*, [[repos-30-przeglad]] (2026-10-14). Każde repo ma notatkę w [[repo/_hub|repo/]].

| źródło | wersja | raport, notatka | werdykt | następnym razem |
|---|---|---|---|---|
| a-hamdi/GPU | `a9b0a17c` 2025-04-27 | Q:repos/02, [[a-hamdi-gpu]] | Niska: dziennik nauki, błędne benchmarki. | nie wracać |
| AKO4ALL (TongmingLAIC) | `bbd0e1c` 2026-09-15 | Q:repos/21, [[ako4all]] | Średnia: protokół agenta, nie kod. | – |
| atrex-kernel-agent (alibaba) | `5ad94ff` v0.3.0 10-14 | Q:repos/25, [[atrex-kernel-agent]] | Średnia: bierzemy narzędzia pomiarowe. | nowe wydania |
| auto-gpu-kernel (Dogacel) + fork ludoo | `db02153` 09-12 | R02, Q:repos/14, [[auto-gpu-kernel]] | Średnia; fork z GDN o naszej geometrii. | fork ludoo |
| awesome-reverse-engineering (morluto) | R21l 10-19 | R21l, [[raport-21l-re-gpu]] | Zero pozycji GPU; działają narzędzia producentów i LLVM. | – |
| blocksparse (OpenAI) | `89074c5` 2020 | Q:repos/12, [[blocksparse]] | Niska, martwe od 2020. | nie wracać |
| CUDA dla Rusta (NVIDIA, cuda-oxide) | `bc46b1f` 10-12 | Q:repos/29, [[cuda-rust]] | Brak; tylko liczba odniesienia. | – |
| cuTile Python (NVIDIA) | `d9d8520` 10-13 | Q:repos/13, [[cutile-python]] | Niska–średnia; odpowiednik PDL. | – |
| DeepGEMM (deepseek-ai) | `1fc9c66` 10-14 | Q:repos/03, [[deepgemm]] | Średnia: harmonogram Mega MoE, potok kafli. | – |
| falkon | `04f168e` 05-13 | Q:repos/24, [[falkon]] | Brak. | nie wracać |
| flameox (morluto) | `c7ea167` 0.2.9 10-11 | R21j, [[flameox]] | Dla AMD prawie bezużyteczny (≤1000 slice'ów, bez agregacji). | wsparcie rocprofv3 per kernel |
| FlashInfer (+ bench-starter-kit) | `2895577` v0.7.2; kit `75ccd05` | Q:repos/07, Q:repos/27, [[flashinfer]], [[flashinfer-bench-starter-kit]] | Średnia: wzorce atencji, tylko NVIDIA. | – |
| GPU MODE reference-kernels, kernelboard, lectures | `f3295bb6` 09-17 | R02, Q:repos/09, R21b, [[gpu-mode-reference-kernels]] | Niska: ranking to nie źródło technik. | – |
| gpu-kernel-engineer-from-scratch | `ba738db` | Q:repos/19, [[gpu-kernel-engineer-from-scratch]] | Brak. | nie wracać |
| How_to_optimize_in_GPU | `5d2def3e` 2023 | Q:repos/08, [[how-to-optimize-in-gpu]] | Niska (V100). | nie wracać |
| KeOps | `ef72bc90` 06-24 | Q:repos/20, [[keops]] | Niska; prekursor online-LSE. | – |
| Kernel Tuner | `8e71bbf` v1.5.0 | R02, Q:repos/26, [[kernel-tuner-repo]] | Średnia: przeszukiwanie tablic per kształt. | – |
| KernelAgent (meta-pytorch) | `e0647170` 07-15 | Q:repos/06, [[kernelagent]] | Średnia (proces). | – |
| KernelBench | `423217d9` 03-05 | R02, Q:repos/04, [[kernelbench]] | Średnia: lepsza bramka poprawności. | – |
| kernelguard (gpu-mode) | R15f | R15f, [[kernelguard]] | Wzór reguł z fixture'ami dla fabryki; oszustwa 3.45% → 0.37%. | nowe detektory |
| knlp lm_head (mcgrof) | R18 | R18, [[knlp-lm-head]] | Bezstratne przycinanie głowicy; W7900 ×1.97. | – |
| Megakernels (Hazy), Mirage/MPK, TileRT, FlyDSL, ATOM | R15a | R15a, [[megakernele-prior-art]] | 71–80% pasma; na RDNA3 brak publicznego. | megakernel na RDNA |
| mixbench | `a8cab0c` 08-04 | Q:repos/23, [[mixbench]] | Średnia: pomiar sufitu pasma. | – |
| mKernel (UC Berkeley) | `97e916b` 10-01 | Q:repos/16, [[mkernel]] | Niska. | – |
| NVIDIA open-gpu-kernel-modules | `ca2d03e` 615.78.08 | Q:repos/01, [[nvidia-open-gpu-kernel-modules]] | Średnia: zarządzanie VRAM. | – |
| pplx-kernels (+ lily) | `f70d1eb7` | Q:repos/05, [[pplx-kernels]] | Niska. | lily (MoE na 1 GPU) |
| pygpubench | `286841bf` 08-18 | Q:repos/28, [[pygpubench]] | Średnia: eksperyment z bitem DLC. | – |
| rea (rea-agents) | 6.7.0 | R23a, [[raport-23a-rea]] | Brak GPU: nie zna EM_AMDGPU/EM_CUDA. | czy dodali AMDGPU |
| smokinggun (morluto) | `cf3a387` 08-29 | R21k, [[smokinggun]] | Skaner pętli CPU, bez `.cu`/`.hip`. | – |
| Tensara | `fae96618` | Q:repos/18, [[tensara]] | Niska. | – |
| TileGym (NVIDIA) | `c742afc` 10-09 | Q:repos/17, [[tilegym]] | Niska. | – |
| TileLang | `19da924` 10-14 | Q:repos/10, [[tilelang]] | Niska: RDNA3 tylko f16 WMMA. | iu8 na RDNA3 |
| Tokamax (Google) | `b500ee4` 10-14 | Q:repos/15, [[tokamax]] | Niska (TPU). | – |
| vllm-xpu-kernels (Intel) | `6b30c9b9` 10-14 | Q:repos/11, [[vllm-xpu-kernels]] | Niska; pomysł fuzji qk-norm+RoPE+KV. | – |
| batch_invariant_ops (thinking-machines-lab) + wpis „Defeating Nondeterminism” | 2025-09-10 | R02, R12, [[thinking-machines]] | Podstawa naszego trybu bitowego. | – |
| speculators (vllm), SpecForge | R10 | R10, [[speculators-specforge]] | Ścieżka do fine-tune głowicy MTP. | – |
| sakana AI-Scientist-v3 | R15f | R15f, [[sakana-agentic-scientist]] | Izolacja ewaluacji tak, statystyki brak. | – |
| wafer-ai gpu-perf-engineering-resources | R21b 10-19 | R21b, [[wafer-gpu-perf-lista]] | Spis lektur o serwerach; o RDNA3 nic. | – |
| hipfire – lista fuzji i stan GDN int8 (R24g) | 10-19 | [R24g](../product/research/24g-hipfire-pomysly.md), [[raport-24g-hipfire]] | GDN int8 KLD 0.0234 – kill; fuzja norm górna granica +4.6% (808 kerneli/token, normy 0.69 ms). | fuzja norm bez spin-waitu |

## Benchmarki i rankingi

| źródło | wersja | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| LocalMaxxing (localmaxxing.com) **3×** | R04, R06, R15b, R15c | [[tqllm]] | Ranking T=0, rekordy z prywatnych buildów. | tqLLM 273.1 t/s 3090 | nowe rekordy dla 3090/XTX |
| LocalScore (Mozilla) | R01, R04, R05 | [[raport-01-konkurencja]] | Wzór publicznego pomiaru, nie konkurent. | – | – |
| ml-rsi-inference-bench (Apple) | `a6b10af` | R21i, [[raport-21i-rsi-inference-bench]] | 37 zadań vLLM/SGLang; nagłówkowe 26.7% statystycznie słabe. | 658 prób, ~$44.5 tys. | publikacja pracy |
| SPEED-Bench (arXiv 2604.09557) | R21f | R21f | Źródło „golden AL” AgentX. | – | – |
| Terminal-Bench (tbench.ai) | R21h | R21h | Benchmark RSI; TB 2.1 51.7 → 86.5%. | – | – |
| sol-execbench (nvidia), ncu-report-skill-rtx-5090, kekzl/imp | R21b | R21b | Materiały pomocnicze do 5090. | – | – |
| HF openai/gsm8k (`main`, test) | `740312ad` (11-09) | [[jakosc-mini]] | 50 zadań w jakość-mini (seed 20261109). | test 1319 | – |
| HF TIGER-Lab/MMLU-Pro (test) | `b189ec76` (11-09) | [[jakosc-mini]] | 10 pytań × 14 dziedzin w jakość-mini, zero-shot CoT. | test 12 032, do 10 opcji | – |
| HF CohereLabs/Global-MMLU (`pl`, test) | `0e619dbe` (11-09) | [[jakosc-mini]] | `pl` istnieje (MT + poprawki społeczności), więc zadania SpeakLeash niepotrzebne. | test 14 042; Lite bez `pl` | ludzkie PL MCQ (SpeakLeash) |
| evalplus HumanEval+ (pakiet evalplus 0.3.1) | HumanEvalPlus v0.1.10 | [[jakosc-mini]], [[evalplus-jakosc-kodu]] | 30 z 164 zadań w jakość-mini, ta sama piaskownica. | – | – |
| HF gorilla-llm/Berkeley-Function-Calling-Leaderboard (v3 simple/multiple/parallel) + checker AST gorilla | `61fc0608` (11-09); gorilla `6ea57973` | [[jakosc-mini]] | 8+6+6 przypadków FC, checker AST skopiowany bez zmian logiki. | simple 400, multiple 200, parallel 200 | BFCL v4 / live |

## Prace naukowe

| źródło | data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| CPLM, Godey & Artzi (arXiv 2610.19247) | 2026-10-13 | R21c, [[raport-21c-cplm]] | Architektura od pretrainingu; bierzemy tylko regułę AGR. | dekod −1.0…3.8% | – |
| Declarative Attention (arXiv 2609.02737, github itsnamgyu/declarative-attention) | R21m | R21m, [[raport-21m-declarative-attention]] | U nas dekod −25…30%; odrzucone. | −19.6% KV, −2.10 pp | – |
| DSpine (arXiv 2609.36173, github tencent/dspine) | `07f326a` → `0cc92d8` (11-08) | R21a, R69a, [[raport-21a-dspine]], [[drafter-dspine]] | +4–7% τ vs DFlash2; tylko jako drafter „nowy kod”. | – | 27B wydany 11-07 → R69a |
| KV między modelami (arXiv 2608.03893, 2411.02820, 2406.11717) | R21e | R21e, [[raport-21e-kv-miedzy-modelami]] | Nie pasuje do hybryd. | – | – |
| RSR (arXiv 2610.02826) + model RSR-27B | HF API 10-19 | R21h, [[rsr-27b]], [[tencent-terminal-rsi]] | Adoptować i zmierzyć RSR-27B; MTP niedopasowane. | 27.78 mld param. | E1: pomiar RSR-27B |
| Terminal-RSI (arXiv 2610.22192) | R21h | R21h, [[raport-21h-rsi]] | Expert iteration + PPO; wynik realny, pokazany korzystnie. | TB 4.0 0 → 19.84% | wydanie Terminal-RSI-27B |
| Single Neuron… Safety (arXiv 2605.08513) | 2026-05-08 | R21f, [[single-neuron-safety-2605-08513]] | Nie o InferenceX (błędny link). | – | nie wracać |
| Star Elastic, Nemotron Nano v3 (arXiv 2605.07182) | R15a | [[star-elastic-2605-07182]] | Niska istotność. | 30B → 23B/12B | – |
| SuffixDecoding (arXiv 2411.04975) **4×** | R02, Q:algorithms, Q:v2, R18 | [[suffixdecoding]] | Lookup bez draftera; u nas realizowane jako ogon lookupu. | ×5.3 agentowe | – |
| Prace o spekulacji/drafterach (EAGLE 2401.15077, Medusa 2401.10774, FastMTP, DSpark 2607.05147, Hydra, Lookahead…) **3×** | Q:drafters, Q:algorithms, Q:training, R10, R18 | [[raport-10-post-training]], [[raport-18-nastepna-fala]] | Dla 27B brak EAGLE-3/Medusa; MTP blisko optimum. | chat AL 2.8–4.1 | nowe drafery dla Qwen3.8-27B na HF |
| Prace o agentach kerneli i autotuningu (R02: METR, Sakana CUDA Engineer, KernelBench, AlphaEvolve…; R15f 2610.18933, 2610.09239) | R02 10-15, R15f | [[raport-02-autotuning]], [[metr-sakana]], [[raport-15f-agentowa-nauka]] | Działają tylko z mocną bramką, w labie. | METR 1.81×; Sakana 3.13 → 1.49× | – |
| Prace o kwantyzacji (GSQ-RCO, QTIP, CSF/QAD, 2604.18556, 2605.00649; R57a: SLQ 2605.02404, DQ 2609.26333; github.com/IST-DASLab/GSQ, github.com/IST-DASLab/RCO, github.com/IST-DASLab/SLQ, github.com/IST-DASLab/gptq-gguf-toolkit) **2×** | R10, R15e → R57a 10-21: GSQ `03fc164`, RCO `9a1e09c`, SLQ `eb9f1f2`, toolkit `7a38bc5` | [[raport-15e-kwantyzacja-nowa]], [R57a](../product/research/57a-gsq-rco.md), [[ista-daslab]] | GSQ-RCO SOTA wąsko (≤ 3 bpw); przy 4 bit RCO = EvoPress; kod GGUF nieopublikowany. Dla nas tylko metryka EAR i ewentualnie własna alokacja. | RCO 4 bit PPL 11.16 = EvoPress; GSQ Q3_K_M +1.09 pkt | kod K-quant/IQ w GSQ; tier ≥ 4 bpw |
| Prace z R18 (multi-stream, KV jednoprzejściowe, ~40 pozycji arXiv) | R18 10-19 | [[raport-18-nastepna-fala]] | Mnożniki: więcej tokenów na odczyt wag. | plain 57.1 t/s roofline | – |
| Prace z R21b (FlashAttention-2 2307.08691, online softmax 1805.02867, 2512.22219) | R21b | [[raport-21b-gpu-perf-zasoby]] | Większość technik już mamy. | – | – |
| DFloat11 / ZipNN (bezstratna kompresja wag) | 10-20 | [R24t](../product/research/24t-entropia-wag.md), [[raport-24t-entropia-wag]] | Dla K-quant/IQ4 sufit ≈ 5%, kodek ≤ 0.9% – kill. | Q4_K 3.865/4 b, Q5_K 4.864/5 | tylko dla BF16/FP8/NVFP4 |
| EAGLE-4 (paper `EAGLE4_Paper.pdf`, github eagle-hq/EAGLE-4 `7b7b5a5`, blog.eagle.ai/blog/introducing-eagle-4) | 2026-10-20 | [R52](../product/research/52-eagle4.md) | Bierzemy pomysły (głowica low-rank + dokładne przeliczenie, koszt/pewność); kod i wagi tylko do ewaluacji (licencja). | 863.8 t/s (B300 TP4, T=0), MTP 534.5; Nemotron łańcuch vs łańcuch MTP ×1.14 | publiczny PR #3 TokenSpeed (961.6), dane treningowe, drafter Gemma/fork llama.cpp |

## Modele, kwanty i drafery (Hugging Face)

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| DFlash2 drafter (huggingface.co/z-lab/Qwen3.8-27B-DFlash2, github z-lab/dflash; magnitudedev GGUF) **6×** | Q:drafters 10-10 | R03, Q:drafters, Q:v2, R16d, R16i, R21a, [[firma-magnitude]] | Najlepszy drafter na kopię/edycję; u nas ogon lookupu wystarcza. | MT-Bench AL 4.10 vs MTP 3.74 | nowa wersja draftera |
| DFlash dla Nemotron 3.5 Bolt | R14 10-16 | R14, [[raport-14-nemotron-3090]] | Działa na 3090; KLD niezmierzone. | 87.2 → 141.1 t/s | KLD |
| DSpark (RadixArk, RedHatAI, DimInfer, Doopeworld) | Q:drafters 10-10 | Q:drafters | Na czacie nie lepsze niż MTP. | MT-Bench 3.01 | – |
| KaedeTai/Qwen3.8-27B-MTP-zh | Q:v2 | Q:v2/rr-engines-drafters | Douczona głowica zh: +5.8 pp akceptacji. | – | – |
| Qwen3.8-27B (+FP8, NVFP4 nvidia/unsloth, GGUF unsloth UD, ubergarm, APEX, KTopt, AutoRound) | R04, R09, R15e, R16e | [[qwen-alibaba]], [[unsloth]], [[raport-16e-kwanty-kld]] | Zostajemy przy UD-Q4_K_XL (nie zmieniamy kwantów). | KLD 12 ramion | – |
| Swift 1.0/1.5 (ukisai) | R15e, R16e | [[ukisai]] | Fine-tune, niedouczona głowica MTP; licencja <US$1M. | – | – |
| Underdog Saluki 27B (ConwayResearch) | R09-3060, R10, R15e, R16e | [[conway-research]] | IQ2-mix 7.89 GB na 12 GB. | 3060: 22.3 → 23.4 t/s | – |
| Ternary Bonsai 2 27B (PrismML) | R09-3060, R10 | [[prismml]] | Działa na 3060 przez prism fork. | Q2_0 33.15 → 35.51 t/s | – |
| GSQ-RCO GGUF (ISTA-DASLab, BuffedMod) **2×** | R10, R15e → R57a (alokacja IQ3_S, 3Bit-GSQ vLLM) | [[ista-daslab]], [R57a](../product/research/57a-gsq-rco.md) | Ten sam format GGUF, zysk wąski; na 24 GB nie dotyczy (U4 KLD 4.8× niższy). | – | nowy tier ≥ 4 bpw (CompWatch hf: ISTA-DASLab) |
| LFM2.5-24B-A2B (+GGUF, FP8, NVFP4, MXFP4 społeczności) | R04, R06, R09-5060ti | [[liquidai]] | Nasz drugi model; NVFP4 tylko prefill. | – | – |
| Nemotron 3.5 Bolt 74B-A9B, Super-VL 120B | R04, R14, R15c | [[raport-14-nemotron-3090]] | Bolt IQ2_XXS mieści się na 3090. | – | – |
| Qwen3.8-Flash-Next (+NVFP4, CSF-QAD) | R04, R06, R15e, R21g | [[raport-21g-nowe-silniki]] | Strata uruchamia na XTX ~80 t/s. | – | czy dla nas MoE offload |
| Gyro-S (Strata, trellis + Hadamard, TQ1_0/TQ2_0/TQ3_0 dla Qwen3.8-Flash-Next) | R21n 2026-10-19 (nagłówki GGUF zakresem bajtów) | [R21n](../product/research/21n-strata-020-gyro.md) | Zły plik dla nas (próg 32 GB); przy 86 GB IQ3_S. | KLD 0.27–0.40; XTX szac. ~50–75 t/s bez MTP | tylko jako test progu „32 GB PC”; najpierw IQ3_S w forku |
| Laya / laya-mlx | R10 | [[laya-mlx]] | Za wolne do decyzji per token. | 322–421M | – |
| Bielik 11B v3 (+DFlash), MiniCPM5, Mistral Small 4, gpt-oss-120b, Kimi K3, GLM-5.2 | R04, R06, R15a, R21f | [[raport-04-sprzet]], [[raport-06-produkt]] | Katalog modeli produktu; bez badania wydajności. | – | – |
| EAGLE-Corp/Qwen3.8-27B-EAGLE4 (drafter EAGLE-4) | HF 2026-10-19 (nagłówek safetensors zakresem bajtów) | [R52](../product/research/52-eagle4.md) | Jedyny EAGLE dla 27B; EAGLE-3.1 + low-rank r=128, pełny słownik 248k. Licencja eagle-4: produkt = Competing Offering. | 6.18 GB BF16, 3.09 mld param. (warstwa 0.435 mld, lm_head własny 1.27 mld, embed = embed celu) | akceptacja w lustrze na E0 (R52 §5) |

## Dokumentacja producentów, runtime i RE

| źródło | wersja | raport, notatka | werdykt | następnym razem |
|---|---|---|---|---|
| ROCm 10.1 (rocm.docs.amd.com, TheRock, rocm-systems, amd/skills) **3×** | 10.1 vs 10.0 | R13, R08, R17, [[raport-13-rocm-10-1]] | Nic istotnego na gfx1100; zostajemy na 10.0. | ROCm 10.2 release notes |
| rocm-systems CLR/ROCr + Linux v6.8 + tinygrad + firmware MEC | `55754a0` develop | R17, [R23d](../product/research/23d-re-runtime-amd.md), [[raport-17-gpu-page-fault]] | Firmware potwierdza H1′ (PRIV z flagi kolejki). | nowy firmware MEC |
| Kernele AMD gfx1100 (hipBLASLt, rocBLAS, MIOpen CK, AOTriton) **2×** | ROCm 10.0.0 | R23b, [R23b2](../product/research/23b2-re-kernele-amd-bariery.md), [[raport-23b-re-kernele-amd]] | Nie mają lepszego GEMV dla N=1..16. | 2. podejście dodało tylko bariery LDS |
| cuBLASLt / SASS sm_86/sm_120 (CUDA) | R23c | R23c, [[raport-23c-re-kernele-nvidia]] | Trzy różnice: PDL, `LDG.E.EF`, ładowanie 128-bit. | nowe CUDA |
| Blackwell Tuning Guide | v13.4 | R21b, [[raport-21b-gpu-perf-zasoby]] | Głównie B200/GB200; dla sm_120 mało. | nowa wersja |
| Narzędzia RE: RGA 2.15, umr, ATT, llvm-objdump, cuobjdump/nvdisasm, radare2, Ghidra | R21l | [[raport-21l-re-gpu]] | Działa zestaw producentów i LLVM. | – |
| NVIDIA/AMD/Intel/Apple/Microsoft API detekcji sprzętu (NVML, ADLX, DXGI, Metal) | R04 | [[raport-04-sprzet]] | Dwuwarstwowa detekcja. | – |
| Windows HIP (PAL) | R08 | [[raport-08-platforma]] | PM4 replay nie działa na Windows. | HIP na ROCr dla Windows |
| gemma.ai (99 URL mapy strony; `capabilities/mtp`, `qat`, `visual-guides/{mtp,gemma-4}`, `diffusiongemma/*`, `deployment/*`) | 10-19 | [R21o](../product/research/21o-gemma-ai.md), [[raport-21o-gemma]] | Klastrowa głowica nie dla Qwena (d1 −4…−11%); ogon OOV offline +0.92% tok/krok, na GPU −1.5%. | tokenizer Gemmy (PL tok/słowo) po zgodzie na pobranie |
| Apple macOS SLA §3A (leasing ≥ 24 h), llama.cpp issue #26129 (limit Metal 2/3 RAM), `ivanopcode/devnote-override-macos-metal-vram-cap`, instances.vantage.sh (ceny EC2 Mac) | 10-20 | [R30](../product/research/30-intel-apple-dostep.md), [[raport-30-intel-apple]] | Apple w chmurze min. 24 h (m4max $6.25/h, m3ultra $12.50/h); M1 Pro 16 GB = 10.67 GiB dla GPU. | zmiana zasad Enverge; macOS 27 limit |

## Aplikacje, firmy i chmury (konkurencja, rynek)

| źródło | raport, notatka | werdykt | następnym razem |
|---|---|---|---|
| Ollama, LM Studio, Jan, Lemonade, llamafile, koboldcpp, GPT4All, Foundry Local, AnythingLLM, Open WebUI, LocalAI, llama-swap, Msty, Pinokio, AI Playground, ramalama, osaurus, omlx, pocketpal, GenieX | R01, R03, R06, [[ollama]], [[lm-studio]], [[jan]], [[lemonade]] | Nikt nie łączy pomiaru, optymalizacji i bitowej weryfikacji. | nowe funkcje „auto-tune” |
| TurboLLM, llmfit, llama-optimus, local-llm-autotune, ggrun, gguf-parser-go | R01, R04, [[turbollm]] | Flag-tunery; nie optymalizują kerneli. | – |
| Tauri 2, velopack, llama-cpp-rs, Textual | R03, R06 | Wybrany stos produktu. | – |
| Vast.ai, RunPod, Salad, HOSTKEY, GigaGPU, Scaleway, TensorDock, Thunder Compute | R05, R09, [[firma-vast-ai]], [[firma-runpod]], [[firma-salad]], [[hostkey]], [[gigagpu]], [[scaleway]] | NVIDIA tanio u Vast; Radeonów z rootem prawie brak. | ceny i nowe Radeony |
| Intel Arc do wynajęcia: GigaGPU Arc Pro B60/B70, Zed Up (karta B60), Intel Tiber AI Cloud, Vast.ai (CLI live), TensorDock, Hetzner/OVH/Scaleway GPU **2×** | R05 (10-15) → [R30](../product/research/30-intel-apple-dostep.md) (10-20) | Godzinowego Arc nie ma (Vast: 5039 ofert, 0 Intel/AMD); GigaGPU B60 £129/mies. = krzem B580, 24 GB, 456 GB/s, root. | nowe oferty Arc na Vast (`gpu_arch=intel`), Tiber z Arc |
| Apple Silicon do wynajęcia: Scaleway (M1…M4 Pro), AWS EC2 Mac (M4/M4 Pro/M4 Max/M3 Ultra), MyRemoteMac, MacStadium, MacinCloud, RentAMac, MacRent, RoundFleet, HostMyApple **2×** | R05 (10-15) → [R30](../product/research/30-intel-apple-dostep.md) (10-20) | Karta M4: Scaleway M4-M 32 GB €0.29/h, 24 h min. (€6.96); AWS m4max $6.25/h, m3ultra $12.50/h, wszędzie 24 h min. (licencja Apple). | nowe M5/M6 w Scaleway; ceny |
| Enverge (enverge.ai, mac-studio.enverge.ai) | [R30](../product/research/30-intel-apple-dostep.md) 10-20 | Najtańszy krótki test Apple: Mac Studio M5 Ultra 256 GB $2.50/h, co minutę, admin+sudo, kolejka FIFO; też DGX Spark $0.75/h, RTX Pro 6000 $1.95/h. | dostępność Mac Studio (portal za logowaniem); 512 GB i cena |
| Darkbloom (darkbloom.dev, Eigen Labs, `Layr-Labs/d-inference`) | [R30](../product/research/30-intel-apple-dostep.md) 10-20 | Nie wynajem: API inferencji (OpenAI) na cudzych Makach, bez SSH; public alpha od 2026-04-15. | tylko jako konkurencja (prywatna inferencja Apple) |
| AMD, NVIDIA, Hugging Face, Liquid AI, Unsloth, Thinking Machines | [[firma-amd]], [[firma-nvidia]], [[hugging-face]], [[liquidai]], [[unsloth]], [[thinking-machines]] | Profile firm. | – |
| AI Act, licencje, prawo (eur-lex, twobirds) | R06, [[raport-06-produkt]] | Jesteśmy providerem aplikacji czatu. | – |

## Nowe źródła 2026-10-20/21 (raporty 32–52)

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| Project Maya | v1.1.17 `8d9a9b5`, v1.1.19 `3bf6867` (10-20) | R32a, R39a, [[project-maya]] | Bez kerneli dla nas; rozgrzewka przed READY. | #318 ×1.5 DeepSeek | v1.1.20+ |
| Strata | `cbfd5b92` v0.2.1.3 | R32a, [[raport-32a-maya-strata-gyro]] | Delta bez dźwigni. | – | >v0.2.1.3 |
| DeepInfer / deepseek-recipe | `774ce24` / `935817c` (10-20) | R32b, R39c, [[deepinfer]] | Klaster sm_100; bierzemy tokenizację i parser. | 91k 64.8 → 9.6 ms | nowe commity |
| SAGE-EXL3, cuteafd | `c852150e`, v3.0.1 `9098781` | R32c, [[raport-32c-sage-exl3]] | Metoda nieopublikowana, metryki zawyżone. | ~1.6 bita | publikacja metody |
| LocalMaxxing API (delta) | 10-20, 1 864 wiersze | R32d, [[raport-32d-localmaxxing]] | Verified = spójność, XTX 0 verified. | 318.2 t/s XTX | verified na XTX |
| NInfer, tqLLM | `a928f899`, `d617986` | R32f, [[ninfer]], [[tqllm]] | Wiarygodne, nieporównywalne (T=0 reasoning-v1). | 273.1 t/s 3090 | nowe rekordy |
| llm-speed, llm-bench.io, llamabench.ai, club-3090, Token Atlas | 10-20 | R34, [[raport-34-zrodla-benchmarkow]] | Nowe półki rankingów; w compwatch. | XTX mediana 73.3 | dane XTX |
| FlashMap (arXiv 2610.24365) | `cd5b45b` (10-20) | R39b, [[raport-39b-flashmap]] | Bezstratny, dla prozy PL na minusie. | czat 2.28–2.44× | drafter PL |
| REA-Prompts | `390f0c1` (10-20) | R39d, [[raport-39d-rea-prompts]] | Sterowniki, nie GPU; 6 wskazówek metody. | – | – |
| TorchTPU | PyPI 0.2.0 | R39e, [[raport-39e-torchtpu]] | Bez znaczenia dla decode. | – | TRC |
| NVIDIA Flare | `47581cc` (10-20) | R39f, [[nvidia-flare]] | Tylko NVIDIA, bez spekulacji dla 27B. | 27B NVFP4 20.15 GB | N1X Windows |
| Strata 0.2.2 + Qwen3.8-Flash (API) vs Flash-Next | `011c9e60` v0.2.2 (10-21, silnik 0.1.47) | [R57b](../product/research/57b-strata-qwen38-flash.md), [[strata]] | Dla gfx1100 nic; lekcja: flaga hosta przed graphLaunch (deadlock HIP). Flash = API, wag brak. | XTX IQ3_S 62.3 t/s (społ.); prefill 128K 926 → 1687 (hipBLASLt) | >v0.2.2: tylko HIP/gfx1100, obsługa 27B |
| Gyro-Coder (HF agentionai) + `agention-gyro` (spec, Apache-2.0) | karta 10-22/24; `587a526` (10-24); fork `9aa51ce` | [R60c](../product/research/60c-quant-and-3090-engines.md), [[gyro-coder]] | 256/512 ekspertów, TQ2_T, 19.92 GiB; tylko fork Vulkan; dla 24 GB nie dotyczy. | Python KLD 0.165, 13/16 zadań | Strata/HIP obsługa, produkcyjny enkoder |
| tqLLM 1.2.0–1.2.3 | `c2163c2` v1.2.3 (10-22) | R60c, [[tqllm]] | Kod otwarty, tylko CUDA; Flash-Next 3090 ≈ nasz czat 27B; „32 GB RAM” nieprawda (≥ 64 GB). | 77.1 vs 47.2 t/s po 128K | ROCm, nowy plik Flash-Next |
| DCQ (HF Akahsizrr, MiMo-V2.6-Distill-Qwen-9B) | 10-2x, bez wersji | R60c, [[dcq-kotwica-stanu-gdn]] | Pomysł (stan GDN w stracie) przenośny; dowody słabe (n=20, JSON ≠ karta). | qkv stan 25× wyjście | artykuł / większa ewaluacja |
| @superalesha (X 2111885825218838905, 2113131231168831637), @fraserpricee 2112111199454454169 | 10-18/19/22 | R60c, [[hyperqwen]] | 4.6× = cytowanie 25K (czat 1.6×); 574 t/s DeepSeek: źródło mówi 500+, 4× RTX Pro 6000. | 82 → 382 t/s | przepis megakernela Frasera |
| Nemotron-3.5-Bolt-E4B (NVIDIA, unsloth GGUF) | HF 10-23 | R60c, [[nemotron-3-5-bolt-e4b]] | Telefon/edge; nie drafter Qwena (słownik 262 144). | Q4_K_M 6.18 GB | katalog 6–8 GB |
| Humming (vllm-project/humming, vLLM + Ant Group) | `db930af` (10-22), blog 10-21 | [R60d](../product/research/60d-serving-kernels-cache.md), [[humming]] | Tylko CUDA, bez GGUF; batch 1 ≈ Marlin, poniżej naszego MMVQ. | 4090 W4A16 M=1 610 GB/s (60%); E2E +14…43% (8× H20) | port HIP, ścieżka GEMV małego M |
| SGLang HiCache + Unified Radix Cache (blogi, PR #21259 #30393 #33639 #34798) | blog 10-2x; PR do 2026-08-19 | R60d, [[sglang-hicache]] | Wzorce dla cache sesji: pinned I/O, snapshot GDN na granicy prefiksu, session_id. | L3 9.4K → 145.5K tok/s; odzysk 1/10 → 10/10 | write-back dla snapshotów, nowe PR hybryd |
| SGLang Unified Memory (blog LMSYS + wpis @ChengWan17, Telegram „gpu”) | blog 2026-11-11, SGLang `daa171846f` | [[sglang-unified-memory]] | Nie dla nas: jedna arena zamiast podziału pul KV/SWA/stan liczy się tylko przy wielu żądaniach; topka ma 1 slot. | H200: 1000 vs 618 żądań w locie, do +26% przepustowości; domyślnie 5830 vs 5880 tok/s | wsparcie poza CUDA, tryb domyślny |
| Baseten deepseek-ultrafast (Rust + CUDA, DeepSeek-V4.1-Flash; @saltyph, @waterloo_intern, Telegram „gpu”) | wpisy 2026-11-13 | [[telegram-2026-11-14-silniki-agenci]] | Silnik pod jeden model; dla nas tylko potwierdza K-014 (krok spec-dec w jednym grafie CUDA). | 4× B300 ~1740 TPS, 8× B300 2060; +15% vs SGLang; 1M prefill ~12 s | kod grafu spec-dec (weryfikacja 7 tok.) |
| InferenceForge (@kaiwei_chang, Telegram „gpu”) | wpis 2026-11-13; pracy/repo nie znaleziono | [[telegram-2026-11-14-silniki-agenci]] | Agent stroi serwer pod AgentX; przepustowość wielu sesji, nie nasz przypadek. | +43% przepustowości przy tym samym SLA | praca / repo |
| vstack (hao-ai-lab/vstack, Telegram „gpu”) | README 2026-11-14 | [[telegram-2026-11-14-silniki-agenci]] | Weryfikacja formalna (TLA+/Z3) dla agentów; 17 błędów w vLLM/SGLang. Dla nas opcja przy K-001. | 17 błędów, VeriServe +0,18% p50 TPOT | spec cyklu życia slotu, jeśli K-001 utknie |
| AKV (arXiv 2610.28577, thu-nics/AKV) | `c567a42` (10-21), v1 10-20 | R60d, [[akv-cache-agentow]] | Repos odpada przy IMROPE; drop tylko w atencji, drogi. | −27.7% kosztu (centy API); 1.18× wyjścia | wsparcie modeli liniowych/hybryd |
| dphnAI/sonar PR #1788 (all-reduce PCIe) | `f653ba4e` (OPEN, 10-21) | R60d | Tylko sm_120, TP=4, P2P; nie dotyczy. | 290.4 → 327.2 t/s (4× RTX PRO 6000) | scalenie, sm_86 bez P2P |
| Project Maya | v1.1.21 `451f9cb` … v1.1.26 `f26d8ba` (10-21…23) | R60d, [[project-maya]] | Tylko DeepSeek; nic dla gfx1100/Qwena; #382 na 2× XTX bez zysku. | prefill AMD 2.35–2.53×; FAT_ROWS 1.3–1.56× (V100) | >v1.1.26: gęsty 27B, pomiar XTX |
| oMLX (jundot/omlx) 0.7.2 | `c4bb311e` (10-24), release 10-21 | [R60b](../product/research/60b-apple-engines-bonsai.md), [[omlx]] | Lightning MTP = MTP głębokości k z adaptacją z pomiaru; CED = Causal Encoder-Decoder DS-V4.1; nie dotyczy 27B/XTX. | Qwen3.6-27B 42.8 → 55.1 tok/s (M3 Ultra) | >0.7.2: zmiany w weryfikacji GDN |
| Locals (Generated-Computers) + arXiv 2610.09139 | `c0f9baa` (10-24) | R60b, [[locals]] | „Przełom” dotyczy gramatyki, nie DeltaNet; kernel GDN 1 launch (+1.9%) już mamy. | 8 żądań 87 → 271 tok/s (M2 Pro) | gramatyka na GPU dla agentów (produkt) |
| Konkurs cuda.fast / mlx.fast Bonsai 2 9B (Layr-Labs, PrismML) | CUDA `759629b`, MLX `8cee3ef`; zamknięty 10-22 | R60b, [[bonsai-fast-contest]] | Potwierdza naszą ścieżkę; nowe: sito głowicy draftu, L2 evict_first (3090), taśma delt GDN, drzewo W16. | CUDA 85.9 → 576.7, MLX 144.8 → 959.6 tok/s | nowy konkurs Nemotron 3.5 Lightning (te same repo-wzorce) |
| Flapping Airplanes | strona 10-24, seria A 10-21 | R60b, [[flapping-airplanes]] | Megakernele, brak kodu. | $180M seed, $1B seria A | publikacja frameworka |
| Blog thelastone07 „Making CUDA less overwhelming” | 10-20 | R60b | Wstęp dla początkujących, nic nowego. | – | – |

## Raport 63 (2026-11-05, pakiet linków 2026-11-03)

Synteza: [[raport-63-synteza]]; reguła [[2026-11-05-tylko-bezstratne]] (stratne pomysły odrzucone bez rankingu). Raporty: R63a–R63e = `product/research/63{a..e}-*.md`.

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| Strata (delta) | v0.2.3–v0.2.11, silnik 0.1.48 → 0.1.57, klon `9f7d977d` (11-05) | R63a §2–5, R63d §3, [[strata]], [[strata-kva]] | Dla gfx1100 i gęstego 27B nic; KVA stratny (odrzucony). | R9700 KVA prompt +28%, decode −11% | `git log 9f7d977d..` tylko HIP/gfx1100 i gęsty 27B |
| Strata PR #4366 (`DS4_FAT_ROWS`) | zamknięty, w 0.2.8 opt-in | R63a §4, [[lekcja-higiena-pomiaru]] | +39% to ciepły vs zimny; realnie +2–6%. | 1400 → 1950 t/s (ogłoszone) | – |
| basalt (jesdga95/basalt) | `dc047a7` (11-04), v0.2.1 | R63a §6 | Głowica Q8_0 w płaszczyznach dokładna; liczby z wejścia nieznalezione w repo. | 5090 IQ3_S 374.8 t/s | typ głowicy LFM (Q8_0?) |
| elpis (gildrb/elpis) | `13e8b59` (10-29, finished) | R63a §7 | Najlepsza metoda (bramki przed danymi, lista porażek). | 262K 45.6 ms/rundę; geomean 125.7 t/s | – |
| benchlab engines-27b-3090 | post 11-03, rerun 11-05 | R63a §8 | Rzetelny; turboderp MTP-7 ≈ DFlash2 na greedy. | 180 / 170 / 146 / 97 t/s | nowe silniki w zestawieniu |
| HyperQwen (delta) | `6ab9bd0` (11-03), 163 commity od `95ee3b6` | R63a §8, [[hyperqwen]] | KV int8/fp8 dla długiego kontekstu tylko NVIDIA; port LSA. | +12.2% / +14.0% przy 66k/100k | >`6ab9bd0` |
| YASAKANI (x.com/yasakani_dev 2117521489885090271, 2117529802844610956) | 11-03, bez kodu | R63a §9, [[yasakani]] | Klasa kopii/struktury; po normalizacji parytet na edycji. | 1220 t/s ≈ 11–12 tok/krok | publikacja kodu formatu |
| MegaCapybara (perkel666) | v1.40 `bdfc1b8` (11-04), v1.39 (11-01), binarki | R63a §10 | Rekord z +20% OC pamięci; „draft forest”. | 540 (OC) vs 466 (stock) | kod źródłowy |
| NInfer (delta) | master `a754fcf3` (11-02) | R63a §11, [[ninfer]] | Dla 27B nic (GLM, Spark). | – | `docs/performance/qwen3.8-27b.md` |
| ignis (gpillon/ignis) | `df69a68` (11-05) | R63a §12 | Top-k draftera 3145 → 44 µs (+21%); trellis 12.5 GiB. | 5090 kod 367, proza 167 t/s | – |
| mkyt (qwen3-27b-5090) | `eea3cbc` (11-03) | R63a §13 | Wzór decisions.md; pełne NVFP4 psuje równoległe tool-calle. | BFCL parallel 79 → 65.5% | – |
| qwen-warp (tuan3w) | `146a654` (11-05) | R63a §14, [[qwen-warp]] | 262k na 3090; potwierdza jedno przejście KV. | 102 / 94 t/s przy 190k/262k | – |
| TensorFold (delta) | v1.1.1–v1.2.2, HEAD `cde4fe7` (11-05) | R63a §15, [[tensorfold]] | HIP na gfx1151/1201, gfx1100 nie. | gfx1151 +7.5–18.9% (#1932) | `plan.hip` na gfx1100 |
| Konkurs cuda.fast / mlx.fast Qwen3.8-27B TF (Layr-Labs) | CUDA `1af264e`, MLX `28c5b13` (11-05) | R63a §15 | Prompt = kopia; techniki znane. | 2.759 / 1.810 | – |
| gpu.nz llm-vram-table | 10-20 | R63a §16 | f16 zgodne; pomija MTP i nasze +10.7 KiB/token. | 64 KiB/token f16 | – |
| LocalMaxxing API (5090, Qwen3.8-27B, since 10-21) | 11-05, 1 GET | R63a §11 | tqLLM TQ_L 414/354 (10-27); NInfer bez nowych. | – | – |
| colibri (JustVugg) | v2.1.0 `704a3f68` (10-31), kod `0a5504a1` | R63b §1, [[colibri]] | „256k w szybkości 64k” = planer + KV f16; `COLI_PREFIX_LOG` do skopiowania. | tura 86 → 4.9 s | wyniki 27B na GPU |
| Project Maya (delta) | v1.1.27 `f027308` … v1.1.54 `c167004` (10-24…11-05) | R63b §2, [[project-maya]], [[wspolny-poczatek-promptu]] | #607 wspólny początek do portu; nic dla gfx1100. | nowa rozmowa 19× | >v1.1.54, gęsty 27B |
| Delta Inference Engine (musicurgy) | `307437f` (11-04), release 0.9–0.92 | R63b §3 | Opakowanie DeepSeek na Windows; `REWIND_GAP` łapią nasze checkpointy. | Windows +12% (zasilanie, HAGS) | – |
| RTP-LLM (alibaba) | HEAD `26711bad2`/`f81f777a1` (11-03/04), PR #1574 #1460 #1423 | R63b §4 | Wzorzec chudych checkpointów (ogon), CRC32C w oknie kopii. | – | – |
| MNN (alibaba) | 3.6.2 `498882a27` (10-29) | R63b §5 | Mobile; dla topki nic. | DFlash 2.09× (M5) | Android/iPad w produkcie |
| RDNA-FAST (serrynaimo) | `4426ca3` (11-05) | R63c §2, [[rdna-fast]] | Lean reserve, słownik dynamiczny, pułapki ROCm 10. | lean reserve 784 → 80 MiB | `git log 4426ca3..` |
| pentacoxian_dev 2118071912882712590 + Qwen-QSA-llama.cpp | tweet 11-04; repo `fe08b16` (11-05) | R63c §3, [[qwen-qsa-llama-cpp]] | Przełom na 4090, zmienia wyjście → zaparkowane. | 255K 114.7 vs 40.6 t/s (4090) | KL długiego kontekstu |
| HF higa2515/Qwen3.8-27B-QSA-BF16, pentacoxian-dev/…-QSA-GSQ-RCO-GGUF | 11-05 (indeksery `d61281f4…`) | R63c §3 | Karty modeli, bez pobierania. | 52.4M parametrów indekserów | – |
| LithosAI blog (MI355X) | 10-27 | R63c §4 | 2116 t/s = 6 / krok przy założonej akceptacji. | 2.83 ms/krok | – |
| llama.cpp v0.9.0 | `cd959ba` = b12110 (11-04) | R63c §5 | #30574 stan draftu w slocie; fuzje MMQ CUDA; Vulkan split-K. | 254 commity od pinu Enigmy | v0.10 / delta od b12110 |
| vLLM v0.33.0 (ROCm, spec) | `4ba787e` (11-01), notatki rc3 (11-02) | R63c §6, R63d §6, [[vllm-rocm-octave]], [[fly-stratna-weryfikacja]] | Octave i FLy stratne; TRITON_ATTN +18% z adresowania buforów. | k3v3 216 B/slot | – |
| cheaptokens: q5_1 KV | 10-30 (issue #28455, build 10791) | R63c §7 | Nieaktualne od #28079; Enigma bezpieczna poza Vulkanem bez subgroup ops. | 38 vs 1348 t/s (stary build) | – |
| LSA (arXiv 2610.42147, Prefrontal-AI/latent-sparse-attention) | v2 11-03; `5ebea73` (11-04); wagi `d-lsa-weights-v1` (11-02) | R63d §1, [[latent-sparse-attention]] | 72.4× tylko przy 10M; ≤512k ~1×; odrzucone. | 512k TTFT 1.03× / 0.68× | – |
| rapidmlx (X 2118074173323141191), Rapid-MLX | `e2114cf` (11-04), PR #3055 | R63d §2 | Kodu LSA brak; QSA prefill na Macu. | 64K −31.1% TTFT | – |
| closedcircuit „MTP speculative decoding” | 10-28 | R63d §4 | Najlepsze n zależy od karty. | 4060: n=3 32 vs n=1 46 t/s | – |
| Soft-MTP (arXiv 2610.38331, JaydenTeoh/Soft-MTP) | v1 10-28; `4e1cf66` (10-30) | R63d §5 | Dla zamrożonego pnia = nasza samodestylacja. | +1.4…1.5% | – |
| LiquidAI/LFM2.5-24B-A2B-DSpark(-GGUF) | `9222226` (10-21), bf16 `e052e5b` | R63d §6.3 | Drafter LFM wyszedł; topka obsługuje; do zmierzenia. | 664 MB, 5.16 tok/krok (B300) | pomiar t(K) na XTX |
| Anbeeld/Qwen3.8-27B-DSpark-GGUF (RadixArk v2) | `77843de` (09-06) | R63d §6.3 | Na czacie nie lepsze niż MTP. | AL 3.23–3.29 | – |
| nvidia/Qwen3.8-Flash-Next-NVFP4 | `fc694b54` (09-05) | R63d §7 | Tylko B200/B300; nie dla nas. | 132.7 GB | – |
| llm-compressor 0.15.0 | 10-29 | R63d §8 | HIGGS/QAD/REAP zmieniają wagi; odrzucone. | – | – |
| Open Kernel Challenge llms.txt | 11-05 | R63e §2.1 | Lekcja dopasowania do sędziego. | >300 000 zgłoszeń | finał serwingu |
| rohanarun/Auto-research-agent | `0230468` (11-04); PR #6 `7a14f0d`, PR #9 `b94e66e` | R63e §2.2–2.3 | Wiersze Gemini to nie pomiary agenta; PR #9 dobre reguły. | baseline 100.0 µs (syntetyczny) | – |
| EAT (arXiv 2610.36848, caoshiyi/EAT) | v1 10-27; `0a90500` (11-02) | R63e §2.6 | Wzorzec zespołu + audytor pomiaru. | KDA MI350X 3.01× | – |
| Together Compiler (TKCC) blog + paper | 11-04 | R63e §3, [[lekcja-gorzka-lekcja-tkcc]] | Gorzka lekcja; megakernel nie płaci. | −25–31% z bazą wiedzy | – |
| Baseten X article (DeepSeek V4.1 Flash 1017) | 11-04 | R63e §4 | Nieczytelny; „1017” to wersja modelu. | – | treść artykułu |
| SGLang „Beyond Day-0” i Low-Latency Mode | 09-28, 10-18 | R63e §4 | Liczba GB300 przy symulowanej akceptacji 5.4. | 1193 tok/s/user | – |
| InferenceBench (arXiv 2607.20468), Overshoot, wafer field guide, GPU MODE NVFP4 hack, Decagon | 05-20 … 11-04 | R63e §5, [[reward-hacking-inferencji]] | Katalog hacków i obron. | prosta wyszukiwarka 11.53× vs agent 8.08× | – |
| sf-tensor „Formalizing PTX” | 11-02 | R63e §7 | Brak AMD. | – | model AMDGPU |
| Anthropic FlashProve | `9e2bdd8f` v0.16.0 (10-30), post 11-02 | R63e §8 | Lokalnie bez sensu (narzut ~70–95×). | dowód 18.8 MB / 1024 tok. | – |
| gau-nernst B200 QR | 09-27, kod `fb291890` | R63e §9 | Zasady przenośne na RDNA3. | 1239 µs (2. miejsce) | – |
| skyzh/tiny-llm | `17a8cc6` (10-31) | R63e §10.2 | Ledger 6 pytań. | – | – |
| pavelsimo/100-days-of-inference-engineering | `18eef29` (11-04, dzień 7) | R63e §10.2 | Wstępne. | – | rozdziały o spekulacji |
| navaneethkrishnansuresh/CUDA-and-Kernels | `7045333` (11-03) | R63e §10.2 | Puste tematy. | – | rozdziały 13–18 |
| getsupers experiments | 11-05 | R63e §2.5 | Tylko H200. | – | – |
| wafer-ai/gpu-perf-engineering-resources | `6aa00fc` (10-17) | R63e §1 | Bez zmian od R21b. | – | – |

## Raport 64 (2026-11-05, termika XTX)

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| Linux commit 6027db7db773 + 44d0d3031e47 (drm/amd#3625) | mainline v7.4-rc1; brak w Ubuntu 6.8.0-138/-149 | R64 §3.2, [[lekcja-od-commit-gubi-krzywa]] | Potwierdzony błąd maski OD na SMU 13.0.0. | – | czy backport trafi do Ubuntu 6.8.0-1xx |
| smu_v13_0_0_ppt.c / amdgpu_pm.c @ Ubuntu-6.8.0-138.138 | 2026-11-05 | R64 §1–3, [[raport-64-termika]] | Limit sclk to czysta górna granica DPM. | OD 140 B | – |

## Raport 66 (2026-11-06/07: Strata, Maya, 1Cat, TokenSpeed, Hyperkernel, Saber, tqLLM, Flash-Next)

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| Strata (delta), github.com/Niko1221/Strata/releases/tag/v0.2.12 | tag `123bad4a` (11-07), klon `146df3c4`, silnik 0.1.58 | R66a §0–3, [[strata]], [[prog-draftu-od-kosztu-wiersza]], [[qwen38-flash-next]] | Dostrojony DFlash2 tylko dla Flash-Next; Strix ×2 = stratny prefill F16; dla gfx1100 i 27B nic. | Mac +10.3…12.7%; drafty +11.4% | `git log 146df3c4..` tylko HIP/gfx1100, wynik RX 7900 z 0.2.12 |
| Tweet x.com/coldniko/status/2118994582054559808 | 11-07 (snippet web_search, X bez logowania) | R66a §2.1 | Nagłówki nie zgadzają się z release notes (31%, „3× Linux”). | – | – |
| HF incoai/Qwen3.8-Flash-Next-DFlash2; nazeshinjite/Qwen3.8-Flash-Next-DFlash2-GGUF | rev `a22a1744` | R66a §2.1, §3.2 | Drafter Flash-Next, z 27B nieużywalny. | 603 M | – |
| Project Maya (delta), github.com/mw00/project-maya/releases/tag/v1.1.55, /v1.1.56 | `c4effee6` (11-05), `22fc101f` (11-06), klon `7645ddd5` | R66a §2.2, [[project-maya]] | #864 lekcja WMMA (bitowo); MEMO domyślnie; nic do portu dla 27B. | #864 −39% (XTX) | >v1.1.56, gęsty 27B |
| github.com/mw00/project-maya/pull/864 | `4da0b6cc` (11-06) | R66a §3.4, [[mmq-q6k-skale-lds]] | Podawanie operandów WMMA, 108/108 bitowo; u nas audyt Q6_K MMQ. | −38.9…−39.7% | – |
| llama.cpp PR #29761, #28243, #27836, #27742 | #29761 `c061df198` (10-01, b11330); #28243 zamknięty, HEAD `6fcaa16f` | R66a §0.3, [[qwen38-flash-next]] | MTP `qwen4exp` w master; gałąź danielhanchen martwa. | – | DFlash2 dla Flash-Next w llama.cpp |
| 1Cat-vLLM, github.com/1CatAI/1Cat-vLLM (release v1.5.2) | main `c98a8d6` (11-06), wheel `9f970d628`, tag `2bb8c2b9` | R66b, [[1cat-vllm]], [[kv-raz-na-weryfikacje]], [[siatka-checkpointow-gdn]] | −18% przy 250K = rzadka QSA + host KV FP8; Pack-GQA48 bezstratny wzorzec dla planu #8. | 27B 501 → 268 (−47%); operator −20…21% | port Pack-GQA poza V100 |
| TokenSpeed, github.com/lightseekorg/tokenspeed | `b941508` (11-07) | R66b §2.2, §3.8, [[tokenspeed]] | Brak gfx11; lekcja: obcinanie po stop-tokenie na GPU przy overlapie. | monokernel „580 vs 377”, CI 443 | gfx11/gfx1151 w backendzie |
| Blogi TokenSpeed (lightseek.org, pytorch.org) | cytowane w README | R66b §7 | Nieczytane, liczby z CI w repo. | – | – |
| Hyperkernel, github.com/Hyperstitioncc/Hyperkernel | `7048c586` (11-06) | R66c, [[hyperkernel]] | Tylko binaria B300, generatora brak, AMD brak. | +36.7% vs baza NVIDIA (nieporównywalne) | wydanie generatora, backend AMD |
| Wątek x.com/hyperstition_cc/status/2118432349352595528 | 11-05 (mirror r.jina.ai) | R66c §2.1 | Twierdzenia producenta, baza przepisana z NVIDIA. | 1129.6 vs 826.5 tok/s/user | – |
| Mirage MPK HIP, github.com/mirage-project/mirage/pull/820 | gałąź `mpk-amd-mi355x` @ `b6ef312b` (11-02) | R66c §5, [[megakernele-prior-art]] | Pierwszy otwarty megakernel w HIP, tylko gfx950. | Kimi K3 2.02× przy bs1 | backend RDNA |
| NVIDIA mega na B200, github.com/caiovicentino/deepseek-v4.1-flash-megakernel-4x-b200; sgl-project/sgl-nvidia-mega | `8315e890` (10-21); plugin `7b6ff0e2c5` (11-07) | R66c §5, [[megakernele-prior-art]] | Działa, ale 2 zawieszenia w 12.5 h. | +40…56% przy 1–8 użytk.; KL 0.0044 | – |
| Fleet arXiv 2604.15379; Ada-MK arXiv 2605.11581; Event Tensor (MLSys 2026) | 2026-04-15; 2026-05-12; tylko tytuł | R66c §5, [[megakernele-prior-art]] | Prior art megakerneli; dla RDNA3 tylko idee. | MI350 1.3–1.5×; L20 +23.6% | Event Tensor (nieczytane) |
| Saber, github.com/GGZ14/saber-engine | `c8a1e84` (11-06) | R66d, [[saber-engine]], [[kv-raz-na-weryfikacje]], [[glowica-draftu-rerank]], [[drzewo-weryfikacji-gdn-wy]] | Tylko gfx1201, numeryka stratna; 4 przenośne projekty. | TP=1 67 / 148 / 231 tok/s (deklaracja) | wynik niezależny, port gfx11 |
| Reddit r/LocalLLaMA 1xpicjz (Saber) | 11-07 | R66d §2 | Treść nieczytelna, tylko tytuł. | 6 645 pp / 316 decode (tytuł) | – |
| lucebox.com/blog/qwen38-r9700 | 2026-08-21 | R66d §2, [[radeon-ai-pro-r9700]] | Punkt odniesienia R9700. | llama.cpp plain 29.7–30.9 tok/s | – |
| github.com/GGZ14/vllm-mxfp4 | 2026-11 | R66d §2 | Stos referencyjny autora Sabera `[INFERENCE]`, nieczytany w głąb. | – | jeśli Saber zyska niezależny pomiar |
| Kumar, „Anatomy of an LLM Serving Engine” (hiraditya.github.io) | 10-28 / 11-01; vLLM `5df63a7`, SGLang `baa9bef` | R66e §2.1, [[strumien-on-wyrocznia]] | Mapa 5 warstw; u nas IPC na krok = 0. | – | części 3–10 serii |
| Kumar, „A Request's Life in vLLM V1” | 11-02 | R66e §2.1 | Sufit frontu vLLM. | 27 µs/token (Python), ~12 µs (Rust) | – |
| vllm.ai/blog/2024-09-05-perf-update | 2024-09-05 | R66e §2.1 | Profil sprzed rozdzielenia procesów. | HTTP 33% / sched 29% / GPU 38% | – |
| tqLLM 1.4.4, github.com/turbo-tan/tqllm, tqllm.com, /performance.html | `9a9e7e5` (11-07) | R66e §2.2, §3.5, [[tqllm]] | `--exact on` domyślnie; T(x) bitexact na Metalu; O(n) strumień; MRU-other. | cache ekspertów 0.5 → 77% trafień | ROCm |
| HF unsloth/Qwen3.8-Flash-Next-GGUF; unsloth.ai/docs/models/qwen3.8-next | API tree 11-06 | R66f, [[qwen38-flash-next]] | Rozmiary v3.1; tabela KLD z poradnika ma inne rozmiary (inny protokół). | UD-IQ3_XXS 83.6 GB | – |
| unsloth.ai/docs/basics/dynamic-3.0-ggufs/dynamic-3.1-ggufs.md + wykresy „final key 4.png”, „fully final.png” | odczyt 11-06 | R66f, [[qwen38-flash-next]] | Porównanie z GSQ-RCO przy równym rozmiarze (producent, stronnicze). | 83.6 GB: KLD ~0.052 vs ~0.065; odzysk 99.9 vs 99.0% | wspólny protokół KLD (nasz) |
| HF ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF; ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF | README 11-06 | R66f, [[qwen38-flash-next]], [[ista-daslab]] | „Task-lossless” przy 3.5 bpw; nasze E1 i 15e temu przeczą. | IQ3_S 93.26 vs BF16 93.12 | tier ≥ 4 bpw |

## Raport 67b (2026-11-07, modele per klasa VRAM NVIDIA)

Raport: `product/research/67b-wybor-modeli-nvidia.md`, notatka [[final-modele-per-vram]]. Delta od R33 (2026-10-20); dane VRAM z `arms.jsonl` kampanii 67 (b11856/b12110, `-lv 4`).

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| HF API (sortowanie trending / createdAt; autorzy Qwen, unsloth, google, mistralai, nvidia, LiquidAI, ISTA-DASLab, bartowski i in.) | 11-07 | R67b §2 | Nowe ≤ 35B: Nanbeige4.3-33B, Arete-27B, Apex-35B, DSpine-b16; bez unsloth v3.1 dla 27B. | – | `createdAt` > 11-07 |
| artificialanalysis.ai (artykuł Nanbeige 11-05, strony modeli, JSON `intelligenceIndex`) | AA v5.0.1, 11-07 | R67b §2 | Nanbeige 20.4 = Qwen3.8-27B 20.1; Qwen3.6 i Gemma 12B/26B bez v5. | Gemma 4 31B 4.4; Mistral Small 4 4.3 | v5 dla Qwen3.6-35B-A3B |
| HF Nanbeige/Nanbeige4.3-33B (+ bartowski GGUF) | 10-24 / 10-28 | R67b §2 | Gęsty, 58.5 KB/token q4_0; na 5090 tylko 184k. | TB 4.0 30% vs 6% | nasze zadania agentowe |
| HF NousResearch/Arete-27B | 11-06 | R67b §2 | SFT wartości Qwena; głowica MTP wyłączona przy treningu. | propaganda 22% → 0.9% | akceptacja MTP |
| HF Apexintelligence-AI/Apex-35B-V1.0 | 10-28 | R67b §2 | Fine-tune Qwen3.6, liczby vendora. | GPQA 83.3 vs 75.8 | KLD / zadania |
| HF tencent/Qwen3.8-27B-DSpine-b16 | 11-07 | R67b §2 | Tylko SGLang. | akceptacja 4.5–7.2 vs DFlash2 4.1–5.7 | port GGUF / llama.cpp |
| HF ConwayResearch/Underdog-Saluki-27B-1.0 | commit 11-05 | R67b §2, [[saluki]] | **Licencja zmieniona na CC BY-NC 4.0.** | – | warunki licencji komercyjnej |
| HF prism-ml/Ternary-Bonsai-2-27B-gguf | tree 11-07 | R67b §2, [[bonsai]] | Oficjalny upstream Q2_0 (repack zbędny). | 7 626 008 928 B | KLD oficjalnego Q2_0 vs nasz repack |
| HF speakleash/Bielik-11B-v3.0-Instruct-GGUF | 11-05 | R67b §2 | ctx 32 768, więc nie spełnia 131k. | – | Bielik z długim ctx |

## Raport 69 (2026-11-09: DSpine-27B, qwen-warp, TensorFold, Astra-Stop, AMD Adrenalin)

[[raport-69-synteza]]; raporty `product/research/69a…69d`.

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| HF tencent/Qwen3.8-27B-DSpine-b16 + github Tencent/DSpine | HF `ea909c0` (11-07), repo `0cc92d8` (11-08) | R69a, [[drafter-dspine]] | SWA 8192, b16 vs DFlash2 b8; SGLang c=8; dane 27B nieujawnione. | τ T=1 vs DFlash2: MT-Bench +3.6%, kod +8.5…+12.9% | dane treningu / wersja PL |
| Ajay9o9/llama.cpp `dspine` + HF aj9o9/Qwen3.8-27B-DSpine-b16-GGUF | `d493f84` na upstream `a691b23`; HF `62e9241` | R69a, [[drafter-dspine]] | 323 linie, tylko graf; baza bez MTP, AR 3090 zaniżone. | 3090: AR 28.2, DFlash2 50.6, DSpine 80.4 (T=1) / 90.1 (T=0); krok 1.68× AR | PR do upstreamu; wynik T1 na HIP |
| llama.cpp PR #31533 (few-row MMQ, CUDA) | otwarty (11-09) | R69a | Weryfikacja 8–16 kolumn na NVIDIA tańsza. | 3090 Ti DFlash2 58.87 → 43.81 ms/krok | merge → przeliczyć przepisy Enigmy |
| SpecForge PR #1038 (trening DSpine) | 11-09 (odwołanie z README) | R69a | Kod treningu jest; treści PR nie czytano. | – | PL-fine-tune DSpine |
| qwen-warp (tuan3w) **2×** | `689901c` v0.8.0 (11-07) | R69b, [[qwen-warp]] | DFlash2 w grafie: czat ×1.34, agent/kopia −31%; 262k się nie mieści. | 3090 350 W: kod 276.7, czat MTP 155; multiuser 441 t/s | ring buffer draftera, router kopii |
| TensorFold (delta) | `abc39af1` v1.2.5+ (11-08) | R69b, [[tensorfold]] | gfx1100 dalej brak; HIP DFlash2 ładowany, nieużywany. | gfx1151 27B 16 strumieni 51 → 75 t/s | gfx1100 / `--drafter` na HIP |
| HF incoai/Qwen3.8-27B-DFlash2 | 11-09 (API) | R69b | Drafter używany przez qwen-warp i HyperQwen. | 3.85 GB | port GGUF |
| HF ukisai/Swift-1.5-Qwen3.8-27b-INT4 + qwen-warp `689901c` (pomiar) | rev `81a28ee` (09-24); 11-09 | [[2026-11-09-qwen-warp-vs-fork-3090]], [[qwen-warp]] | AWQ+GPTQ W4A16 g128, 19.45 GB; zmierzone na 3090 obok forka: ×1.34–×1.81, kill nie zachodzi. | 16k 114.0/121.0 vs 76.8/66.7; 262k 68.3/68.6 vs 51.1/45.1 | fork z lżejszym GGUF (IQ4_XS/Q4_0) + KLD; próbkowanie spekulacyjne T=1 |
| HF jarrodwatts/Qwen3.8-27B-Astra-Stop | rev `27c08370` (11-04) | R69c, [[astra-stop]] | Rank-1 ×2 na `blk.63.ffn_down`; zmiana zachowania, nie bezstratna. | −37% mediany (bf16, n=16); 694 zadania −3% tokenów | wynik przy effort low, przeciek `</think>` |
| notwitcheer/llm-bench-rig (astra-stop) | `f732402` (11-08) | R69c, [[astra-stop]] | Preregistrowana replikacja Q4_K_M bez MTP; `</think>` w treści 11/32. | 26 254 → 16 930 (−35.5%); SVG 32 → 31/32 | surowe ślady, test z MTP |
| honnibal.dev „Astra read/write misleading” | 11-03 | R69c | Krytyka WSP: agent używał Pythona i przebiegów modelu. | – | – |
| AMD Adrenalin `atieclxx.exe` (wccftech, windowsforum/Comss, Neowin, forum AMD) | 11-08 | R69d, [[amd-adrenalin-zapisy-ssd]] | Tylko Windows; serwer nie dotyczy; UX ostrzeżenie Enigmy. | 0.3–1.5 MB/s typowo; wersje 26.6.4–26.10.2 | release notes z poprawką (numer) |

## EvalPlus (2026-11-09, bramka jakość-mini)

| źródło | wersja / data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| evalplus (PyPI) + HumanEvalPlus v0.1.10 / MbppPlus v0.2.0 | 0.3.1 (11-09) | [[evalplus-jakosc-kodu]] | Harness przyjęty; backend openai ma 100 s alarm z nieskończonym retry → własny dekoder na pętli evalplus. | 164 / 378 zadań | nowa wersja danych / EvalPerf |
| EvalPlus leaderboard `results.json` | 11-09 | [[2026-11-09-evalplus-qwen-uncensored]] | Brak Qwen3.x. | Qwen2.5-Coder-32B-Instruct 92,1/87,2/90,5/77,0 | wpis Qwen3.8 |
| LocalMaxxing HumanEval+ | 11-09 | [[2026-11-09-evalplus-qwen-uncensored]] | Inny harness (shardy), orientacyjnie. | Qwen3.8-27B Q4_K_XL 90,9, Q6_K_XL 92,1, Q4_K_M 91,0 (100/164) | MBPP+ / uncensored |

## Powiązane
- [[KONWENCJE]]
- [[REKORDY]]
- [[podrecznik-gpu]]
- [[repo/_hub|repo/]], [[ludzie-firmy/_hub|ludzie-firmy/]], [[research/_hub|research/]]
- [[index|Strona główna]]
