---
typ: meta
tags: [meta, zrodla, research, rejestr, inferencex, agentx, strata, tensorfold, magnitude, hipfire, dflash, lucebox]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/01-konkurencja.md … 24b-draft-pelny-slownik.md (nagłówki, TL;DR, werdykty); ~/KERNEL/qwen-opt/research/{PLAN,drafters,algorithms,training,stepcost}.md; ~/KERNEL/qwen-opt/research/{repos,strata,tensorfold,v2,round6}/; ~/KERNEL/wiki/repo/*.md; ~/KERNEL/wiki/ludzie-firmy/*.md; ~/KERNEL/wiki/research/*.md; ~/AGENTS.md:14; ~/KERNEL/product/research/{21n,21o,24e,24g,24t,30}-*.md
status: aktualne
---
# Rejestr źródeł: co już przebadaliśmy (InferenceX, Strata, TensorFold, Magnitude, hipfire, DFlash…)

**Jeden wiersz na każde zewnętrzne źródło, które było przedmiotem badania (repo, silnik, praca, model, strona, wpis – np. InferenceX, Strata, TensorFold, Magnitude, hipfire, DFlash), z wersją, raportem, werdyktem i podpowiedzią, co sprawdzić przy następnym podejściu.**

Zasada (użytkownik 2026-10-19, [[KONWENCJE]]): **nie badamy drugi raz tego samego.** Przed researchem: `kb search <nazwa/URL>` + ten rejestr. Źródło już jest → badamy tylko DELTA od zapisanej wersji/commitu/daty. Po researchu dopisz albo zaktualizuj wiersz. Rekordy wydajności: [[REKORDY]]; podręcznik: [[podrecznik-gpu]].

Legenda: **2×/3×/4×** = źródło badane wielokrotnie; kolumna „delta” mówi, co dodało kolejne podejście (tu widać dublowanie pracy). Daty = data raportu. Raporty: `R21f` = `product/research/21f-*.md`; `Q:` = `qwen-opt/research/`. Zakres: przedmioty badania; linki cytowane tylko jako przypis (newsy, dokumentacja API, fora) zostają w raportach – szukaj ich `kb search <domena>`.

## Badane więcej niż raz (przegląd dublowania)

| źródło | podejścia | co dodało każde kolejne |
|---|---|---|
| Strata | Q:strata (10-13, `a0116b27` v0.1.43.1) → Q:strata/update-v0.1.44 (10-13, `ed4773eb`) → R21d/R21g (10-19, v0.1.44.1 `296b59d2`, v0.1.45 `477ac13c`) + R23e (RE kerneli) + R01/R03/R04 (konkurencja) → R21n (10-19, v0.2.0-beta `3d1fb480`, Gyro-S) | 2.: ścieżka Qwen3.6-35B-A3B, f-latency; 3.: KV na dysku, R9700 ×1.42, bariera LDS #3064, Flash-Next na XTX ~80 t/s; 4.: ISA pętli – nic lepszego niż nasze; 5.: 0.2.0 to w 55% aplikacja, silnik v0.1.45.3 – dla gfx1100 nic nowego (R21g mówił „0.2.0 nie istnieje” – wyszła później) |
| TensorFold | R01/R03 (10-15) → Q:tensorfold (10-13, `0efbd447` v1.0.8) → update-v1.0.11 (10-14, `2984ea01`) → R15c (v1.0.12 `833bbfcb`) → R21g (v1.1.0 `76aafcf2`) → R23e | każde podejście = nowa wersja; od v1.0.11 HIP zamrożony (1.1.0: 6 plików HIP, zero zmian) – dalej sprawdzać tylko NVIDIA + DFlash2 |
| Magnitude | R15c (`1f54d5b7`) → R16d (head-to-head 3090/5060 Ti) → R16i (kod 0.2.9 `954d677d`) → R16j (Vulkan na XTX) → R16k (sprzężone próbkowanie) → R23e | 2.: liczby; 3.: przewaga = sufit DFlash2 + kontroler szerokości; 4.: na AMD ×1.42–×2.24 dla nas; 5.: port próbkowania; 6.: brak przewagi ISA |
| hipfire | R03 (warpfront/hipfire, v0.4.0) → Q:repos/30 (`1ff5182` v0.4.2) → R22-lucebox wzmianka → R23e (RE, 54.3 vs 43.2 t/s) | 3.: przewaga z formatu 4.25 bpw i fuzji, nie z ISA |
| DFlash / DFlash2 (z-lab) | R03 → Q:drafters (10-10) → Q:v2 → R14 (Nemotron) → R15b/R16d/R16i (u Magnitude) → R21a (DSpine vs DFlash2) | każde podejście ponownie opisuje drafter; nowa wiedza: tylko sufit bloku (7.3–7.8 tok/krok u Magnitude) i +4–7% τ DSpine |
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
| TensorFold (github.com/ashhart/TensorFold) **5×** | `0efbd447` v1.0.8 → `2984ea01` v1.0.11 → `833bbfcb` v1.0.12 → `76aafcf2` v1.1.0 (10-18) | Q:tensorfold/*, R15c, R21g, R23e, [[tensorfold]] | Kontrakt „drafted == plain”; HIP zamrożony, AMD nasze. | 1.1.0: 901 commitów, HIP +12/−9 | `git log 76aafcf2..` tylko HIP + Qwen3.8-27B DFlash2 na NVIDIA |
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

## Prace naukowe

| źródło | data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| CPLM, Godey & Artzi (arXiv 2610.19247) | 2026-10-13 | R21c, [[raport-21c-cplm]] | Architektura od pretrainingu; bierzemy tylko regułę AGR. | dekod −1.0…3.8% | – |
| Declarative Attention (arXiv 2609.02737, github itsnamgyu/declarative-attention) | R21m | R21m, [[raport-21m-declarative-attention]] | U nas dekod −25…30%; odrzucone. | −19.6% KV, −2.10 pp | – |
| DSpine (arXiv 2609.36173, github tencent/dspine) | `07f326a` | R21a, [[raport-21a-dspine]] | +4–7% τ vs DFlash2; tylko jako drafter „nowy kod”. | – | wydany checkpoint dla 27B |
| KV między modelami (arXiv 2608.03893, 2411.02820, 2406.11717) | R21e | R21e, [[raport-21e-kv-miedzy-modelami]] | Nie pasuje do hybryd. | – | – |
| RSR (arXiv 2610.02826) + model RSR-27B | HF API 10-19 | R21h, [[rsr-27b]], [[tencent-terminal-rsi]] | Adoptować i zmierzyć RSR-27B; MTP niedopasowane. | 27.78 mld param. | E1: pomiar RSR-27B |
| Terminal-RSI (arXiv 2610.22192) | R21h | R21h, [[raport-21h-rsi]] | Expert iteration + PPO; wynik realny, pokazany korzystnie. | TB 4.0 0 → 19.84% | wydanie Terminal-RSI-27B |
| Single Neuron… Safety (arXiv 2605.08513) | 2026-05-08 | R21f, [[single-neuron-safety-2605-08513]] | Nie o InferenceX (błędny link). | – | nie wracać |
| Star Elastic, Nemotron Nano v3 (arXiv 2605.07182) | R15a | [[star-elastic-2605-07182]] | Niska istotność. | 30B → 23B/12B | – |
| SuffixDecoding (arXiv 2411.04975) **4×** | R02, Q:algorithms, Q:v2, R18 | [[suffixdecoding]] | Lookup bez draftera; u nas realizowane jako ogon lookupu. | ×5.3 agentowe | – |
| Prace o spekulacji/drafterach (EAGLE 2401.15077, Medusa 2401.10774, FastMTP, DSpark 2607.05147, Hydra, Lookahead…) **3×** | Q:drafters, Q:algorithms, Q:training, R10, R18 | [[raport-10-post-training]], [[raport-18-nastepna-fala]] | Dla 27B brak EAGLE-3/Medusa; MTP blisko optimum. | chat AL 2.8–4.1 | nowe drafery dla Qwen3.8-27B na HF |
| Prace o agentach kerneli i autotuningu (R02: METR, Sakana CUDA Engineer, KernelBench, AlphaEvolve…; R15f 2610.18933, 2610.09239) | R02 10-15, R15f | [[raport-02-autotuning]], [[metr-sakana]], [[raport-15f-agentowa-nauka]] | Działają tylko z mocną bramką, w labie. | METR 1.81×; Sakana 3.13 → 1.49× | – |
| Prace o kwantyzacji (GSQ-RCO, QTIP, CSF/QAD, 2604.18556, 2605.00649) | R10, R15e | [[raport-15e-kwantyzacja-nowa]], [[ista-daslab]] | GSQ-RCO SOTA wąsko; NVFP4 poza naszymi kartami. | – | – |
| Prace z R18 (multi-stream, KV jednoprzejściowe, ~40 pozycji arXiv) | R18 10-19 | [[raport-18-nastepna-fala]] | Mnożniki: więcej tokenów na odczyt wag. | plain 57.1 t/s roofline | – |
| Prace z R21b (FlashAttention-2 2307.08691, online softmax 1805.02867, 2512.22219) | R21b | [[raport-21b-gpu-perf-zasoby]] | Większość technik już mamy. | – | – |
| DFloat11 / ZipNN (bezstratna kompresja wag) | 10-20 | [R24t](../product/research/24t-entropia-wag.md), [[raport-24t-entropia-wag]] | Dla K-quant/IQ4 sufit ≈ 5%, kodek ≤ 0.9% – kill. | Q4_K 3.865/4 b, Q5_K 4.864/5 | tylko dla BF16/FP8/NVFP4 |

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
| GSQ-RCO GGUF (ISTA-DASLab, BuffedMod) | R10, R15e | [[ista-daslab]] | Ten sam format K-quant, zysk wąski. | – | – |
| LFM2.5-24B-A2B (+GGUF, FP8, NVFP4, MXFP4 społeczności) | R04, R06, R09-5060ti | [[liquidai]] | Nasz drugi model; NVFP4 tylko prefill. | – | – |
| Nemotron 3.5 Bolt 74B-A9B, Super-VL 120B | R04, R14, R15c | [[raport-14-nemotron-3090]] | Bolt IQ2_XXS mieści się na 3090. | – | – |
| Qwen3.8-Flash-Next (+NVFP4, CSF-QAD) | R04, R06, R15e, R21g | [[raport-21g-nowe-silniki]] | Strata uruchamia na XTX ~80 t/s. | – | czy dla nas MoE offload |
| Gyro-S (Strata, trellis + Hadamard, TQ1_0/TQ2_0/TQ3_0 dla Qwen3.8-Flash-Next) | R21n 2026-10-19 (nagłówki GGUF zakresem bajtów) | [R21n](../product/research/21n-strata-020-gyro.md) | Zły plik dla nas (próg 32 GB); przy 86 GB IQ3_S. | KLD 0.27–0.40; XTX szac. ~50–75 t/s bez MTP | tylko jako test progu „32 GB PC”; najpierw IQ3_S w forku |
| Laya / laya-mlx | R10 | [[laya-mlx]] | Za wolne do decyzji per token. | 322–421M | – |
| Bielik 11B v3 (+DFlash), MiniCPM5, Mistral Small 4, gpt-oss-120b, Kimi K3, GLM-5.2 | R04, R06, R15a, R21f | [[raport-04-sprzet]], [[raport-06-produkt]] | Katalog modeli produktu; bez badania wydajności. | – | – |

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

## Powiązane
- [[KONWENCJE]]
- [[REKORDY]]
- [[podrecznik-gpu]]
- [[repo/_hub|repo/]], [[ludzie-firmy/_hub|ludzie-firmy/]], [[research/_hub|research/]]
- [[index|Strona główna]]
