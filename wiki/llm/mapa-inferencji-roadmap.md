---
typ: llm
tags: [llm, inferencja, nauka, mapa, roadmap]
aktualizacja: 2026-11-15
zrodlo: https://x.com/amitiitbhu/status/2121940257101005072 (Telegram „gpu”, 2026-11-15); https://github.com/amitshekhariitbhu/llm-inference-engineering (README, 21 artykułów); przegląd całej ~/KERNEL/wiki (podagent, grep/odczyt)
status: aktualne
---
# Mapa inżynierii inferencji LLM: 114 tematów roadmapy a nasza wiedza

**Roadmapa „LLM Inference Engineering” (17 części, 114 tematów) zestawiona z naszą bazą. 79 tematów mamy zmierzonych na własnym stosie, 15 tylko opisanych, 20 to luki. Luki skupiają się w wielu GPU (równoległość, dezagregacja), produkcji wielu użytkowników i interferencji prefill–decode (2026-11-15).**

Każdy wiersz: temat → nasza najlepsza notatka → nasza liczba z `plik:linia` → status (Z = zmierzone u nas, O = opis, L = luka). Ranking luk na końcu; luki ważne dla nas trafiły do [[KOLEJKA-TESTOW]] (K-106, K-107).

## 1. Podstawy

| temat | nasze notatki | liczba / fakt (`plik:linia`) | status |
|---|---|---|---|
| trening vs inferencja | [[trening-llm-mapa]], [[2026-10-12-mtp-trening-faza1]] | Trenowaliśmy tylko draftery: 1,7 M tok., A40 3,5 h, $2,14, wynik ±0,2% tok/krok (`llm/trening-llm-mapa.md:14`). Trening jest ograniczony obliczeniami: PyTorch na gfx1100 robi matmul bf16 71 TFLOP/s (`eksperymenty/2026-10-12-mtp-trening-faza1.md:15`). | mamy, zmierzone u nas |
| latencja vs przepustowość | [[raport-24c-wiele-zapytan]], [[REKORDY]] | XTX `-np 2`: pojedyncze żądanie −5…−17%, fan-out omp wall +11% (`research/raport-24c-wiele-zapytan.md:10`). 4090 `-np 2`: agregat 94,35 vs 69,46 t/s (+36%) (`REKORDY.md:193`). | mamy, zmierzone u nas |
| wybór modelu | [[final-modele-per-vram]], [[lekcja-pick-z-kalkulatora]] | 3060: Bonsai 2 + MTP 58,3 t/s vs Saluki 22,2 (2,6×) (`lekcje/lekcja-pick-z-kalkulatora.md:10`). 24 GB: 262 144 z MTP (`produkt/final-modele-per-vram.md:10`). | mamy, zmierzone u nas |
| ewaluacje | [[jakosc-mini]], [[evalplus-jakosc-kodu]] | jakość-mini 255/290 = 87,9% (CI 83,7–91,2) (`eksperymenty/2026-11-09-jakosc-mini-qwen-unc.md:10`). HE+ 92,7 / MBPP+ 80,2 (`llm/trening-llm-mapa.md:23`). | mamy, zmierzone u nas |

## 2. Architektura

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| tokeny / tokenizacja | [[raport-24i-sciezka-agenta]], [[raport-42-safe-io]] | Tokenizacja + szablon: 25,5 ms przy 14k, 137,3 ms przy 91k (`research/raport-24i-sciezka-agenta.md:10`). `TOKENIZE_PAR=8`: 1492 → 329 ms (`research/raport-42-safe-io.md:10`). | mamy, zmierzone u nas |
| embeddingi | [[mtp-draft-graf]], [[lfm2-5-24b-a2b]] | Kopia 64k wierszy `token_embd` dla draftu MTP kosztuje +180 MiB VRAM (`kernele/mtp-draft-graf.md:12`). LFM ma głowicę związaną z `token_embd` (Q6_K, 205 MiB) (`modele/lfm2-5-24b-a2b.md:12`). | mamy, zmierzone u nas |
| kodowanie pozycji (RoPE) | [[akv-cache-agentow]], [[attn-prep-fwht]] | Qwen3.8 używa IMROPE, więc llama.cpp nie przesuwa KV (`get_can_shift()==false`) (`metody/akv-cache-agentow.md:14`). Fuzja q/k-norm + rope + FWHT: 4,043 → 3,907 ms/token (LFM) (`kernele/attn-prep-fwht.md:15`). Samej teorii RoPE/YaRN brak. | mamy, opis |
| transformer (układ warstw) | [[qwen3-8-27b]] | 64 warstwy w układzie 3:1 (48 GDN + 16 atencji), hidden 5120, słownik 248 320, head dim 256 (`modele/qwen3-8-27b.md:12`). | mamy, zmierzone u nas |
| matmul (GEMV/GEMM) | [[mmvq-multikolumnowe]], [[2026-10-13-k1-mmvq]] | Strojenie MMVQ skróciło krok z 35,67 do 33,17 ms (`eksperymenty/2026-10-13-k1-mmvq.md:10`). | mamy, zmierzone u nas |
| atencja, QKV | [[fattn-kvq]], [[para-mmvq]] | `kvq` na 3090, tg64@64k: 28,61 → 39,14 t/s (+36,8%) (`kernele/fattn-kvq.md:29`). | mamy, zmierzone u nas |
| maska przyczynowa | [[maska-kq-host-dlugi-ctx]], [[lekcja-bit-exact-attention]] | Maska KQ na CPU: 0,25 ms na graf przy 199k, czyli ~1,1% kroku (`kernele/maska-kq-host-dlugi-ctx.md:10`). | mamy, zmierzone u nas |
| MHA | [[fa-kv-kwantyzowane-cuda]] | Opisane tylko przez kontrast z GQA. Kernel vec czyta KV 6× przy GQA 6 (`nvidia/fa-kv-kwantyzowane-cuda.md:13`). | mamy, opis |
| FFN | [[qwen3-8-27b]], [[para-mmvq]] | MLP to 10,62 GB (4,96 bpw) z 16,48 GB wag czytanych na krok (`modele/qwen3-8-27b.md:25`). | mamy, zmierzone u nas |
| logity | [[raport-24m-weryfikacja-gpu]], [[sampler-fast-path]] | Top-128 na GPU zamiast kopii 16 MB logitów: `mvs` 410,4 → 420,1 t/s (`research/raport-24m-weryfikacja-gpu.md:10`). Kopia D2H kosztuje 0,045 ms/wiersz (`research/raport-24k-koszt-weryfikacji.md:10`). | mamy, zmierzone u nas |
| MoE | [[lfm2-5-24b-a2b]], [[fuzje-lfm-moe]] | 64 ekspertów, 4 aktywne (`modele/lfm2-5-24b-a2b.md:12`). LFM2.5 daje 293,7 t/s (`eksperymenty/stan-2026-10-15.md:10`). | mamy, zmierzone u nas |
| parametry aktywne vs całkowite | [[model-kosztu-weryfikacji-moe]], [[lfm2-5-24b-a2b]] | LFM 24B/~2B aktywnych czyta ~1,8 GB/token, co daje próg ~500 t/s (`modele/lfm2-5-24b-a2b.md:12`). Model kosztu przewiduje T(1) = 3,42 ms, zmierzone 3,40 (`metody/model-kosztu-weryfikacji-moe.md:10`). | mamy, zmierzone u nas |

## 3. Mechanika inferencji

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| autoregresja (decode bez spekulacji) | [[stan-2026-10-15]], [[podrecznik-gpu]] | tg128 bez spekulacji 43,2 t/s, z MTP 109,0 (`modele/qwen3-8-27b.md:20`). | mamy, zmierzone u nas |
| szablony czatu | [[opoznienia-ttft]], [[optymalizacje/opoznienia-ttft]] | Natywny ChatML: 108,6 → 8,8 ms (`research/raport-45-opoznienia.md:10`). Jinja: 9–11 ms → ~1 ms (`produkt/opoznienia-ttft.md:13`). | mamy, zmierzone u nas |
| okno kontekstu | [[2026-11-06-ctx-262k-fit]], [[raport-65-vram-rezerwa-mtp]] | Natywne 262 144: prompt 254 977 tok. bez OOM (`eksperymenty/2026-11-06-ctx-262k-fit.md:10`). | mamy, zmierzone u nas |
| prefill vs decode | [[2026-10-19-workload-omp]], [[lekcja-agent-prefill-nie-decode]] | Tokeny prefill : decode = 4,9 : 1. Czas modelu: prefill 34,4%, decode 56,6% (`eksperymenty/2026-10-19-workload-omp.md:10`). | mamy, zmierzone u nas |
| KV cache | [[kwanty-gguf]], [[raport-65-vram-rezerwa-mtp]] | KV q4_0 ~19,1 KiB/token, więc 1 GiB to +57k tokenów (`research/raport-65-vram-rezerwa-mtp.md:10`). | mamy, zmierzone u nas |
| próbkowanie | [[sampler-fast-path]], [[lekcja-wolna-sciezka-samplera]] | Bez wolnych ścieżek samplera: LFM ~255 → ~293 t/s (`eksperymenty/2026-10-15-sampler.md:10`). | mamy, zmierzone u nas |
| temperatura | [[2026-10-10-sweep-mtp-dflash]], [[lekcja-szum-t-s-przy-t1]] | MTP n=5: T=1 80,5 / T=0,7 79,5 / T=0 81,9 t/s (`eksperymenty/2026-10-10-sweep-mtp-dflash.md:15`). | mamy, zmierzone u nas |
| top-k / top-p | [[gumbel-max]], [[samp-ab]] | Przy top_k 40, top_p 0,95, min_p 0,05 szybka i wolna ścieżka dają ten sam md5 (`narzedzia/samp-ab.md:12`). | mamy, zmierzone u nas |
| tokeny stopu / specjalne | [[bezpieczenstwo-tokenow-specjalnych]], [[stos/bezpieczenstwo-tokenow-specjalnych]] | `<\|im_end\|>` w treści użytkownika stawał się tokenem sterującym; naprawa to SAFE_SPECIAL (`research/raport-32e-safe-special.md:10`). Dosłowne `</think>` ucinało `reasoning_content` (`research/raport-39c-deepseek-deploy.md:12`). | mamy, zmierzone u nas |
| modele rozumujące | [[lekcja-proza-e0-vs-myslenie]], [[astra-stop]] | Ten sam prompt: 102,1 t/s z myśleniem vs 73,1 bez (`lekcje/lekcja-proza-e0-vs-myslenie.md:10`). Astra-Stop skraca myślenie o −35,5% (`modele/astra-stop.md:10`). | mamy, zmierzone u nas |
| streaming | [[strumien-on-wyrocznia]], [[2026-11-08-l1-tokenizacja-parser]] | Parser O(n²) w wątku HTTP: 0,07 → 0,52 ms/token przy 1k → 12,8k (`metody/strumien-on-wyrocznia.md:10`). | mamy, zmierzone u nas |

## 4. Metryki

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| TTFT | [[opoznienia-ttft]], [[raport-38-ckpt-vram]] | Produkcja, TTFT 2k/8k/32k = 366/1473/6676 ms (`REKORDY.md:65`). Świeże 2k: 2160 ms (−22%) (`REKORDY.md:132`). | mamy, zmierzone u nas |
| TPOT (u nas ms/krok) | [[ms-na-krok]], [[metryka-prozy-e0]] | E0: 27,34 ms/krok, 2,158 tok/krok, 78,93 t/s (`metody/metryka-prozy-e0.md:10`). | mamy, zmierzone u nas |
| przepustowość | [[raport-wyniki-xtx-2026-10-19]], [[REKORDY]] | Czat T=1: 35,8 → 114,8 t/s (`research/raport-wyniki-xtx-2026-10-19.md:10`). Prawdziwa sesja: 120,8 t/s (`REKORDY.md:166`). | mamy, zmierzone u nas |
| latencja E2E | [[2026-11-09-wdrozenie-topka-q70]], [[2026-10-12-rocm-vs-vulkan]] | Mediana tury agenta przy 76–112k: 13 413 → 12 029 ms (`eksperymenty/2026-11-09-wdrozenie-topka-q70.md:10`). | mamy, zmierzone u nas |
| P50/P90/P99 | [[2026-11-09-evalplus-qwen-uncensored]], [[ksztalt-ruchu-agentowego]] | Narzut na żądanie: mediana 75 ms, p90 98 (`eksperymenty/2026-11-09-evalplus-qwen-uncensored.md:37`). `speed_real.py` liczy p10/p90 (`eksperymenty/2026-11-09-wdrozenie-topka-q70.md:52`). **P99 nie mierzymy nigdzie.** | mamy, zmierzone u nas (bez P99) |
| koszt na token | [[2026-11-06-eco-sweep-sclk]], [[raport-05-chmura]] | 2,27 J/token na stock, 2,07 przy eco 2200 (`eksperymenty/2026-11-06-eco-sweep-sclk.md:16-17`). **Brak $/Mtok.** | mamy, zmierzone u nas (tylko energia) |

## 5. Wąskie gardła

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| obliczenia vs pasmo | [[podrecznik-gpu]], [[raport-24r-mmvq-pasmo]] | Zmierzony sufit odczytu XTX to 926 GB/s (96,5% z 960). Weryfikacja n=5 osiąga 762 GB/s (`research/raport-24r-mmvq-pasmo.md:10`). | mamy, zmierzone u nas |
| intensywność arytmetyczna | [[raport-18-nastepna-fala]], [[lekcja-rzadkosc-vs-weryfikacja]] | Temat jest tylko pośrednio, jako „więcej tokenów na odczyt wag” (`research/raport-18-nastepna-fala.md:10`). Brak jawnego rachunku grzbietu XTX. Z danych w `karty/rx-7900-xtx.md:12` (~123 TFLOPS / 960 GB/s) wychodzi ≈ 128 FLOP/B `[INFERENCE]`. | mamy, opis |
| roofline | [[sufit-pasma-i-mapa-czasu]], [[lekcja-bledny-roofline]] | Roofline plain 57,1 t/s przy 960 GB/s; zmierzone 43,2 = 75,7% (`modele/qwen3-8-27b.md:25`). | mamy, zmierzone u nas |
| compute-bound vs memory-bound | [[raport-41-re-kerneli]], [[prefill-mmq-fa]] | MMVQ n=5 spędza 70–82% czasu w `wait vmcnt` (`research/raport-41-re-kerneli.md:10`). FA MMA D=256: 40,2 → 49,0 TFLOPS (`kernele/prefill-mmq-fa.md:16`). | mamy, zmierzone u nas |
| wąskie gardło prefillu vs decode | [[raport-18-nastepna-fala]], [[2026-11-08-kvq-once-profil]] | Prefill osiąga 49% szczytu WMMA iu8 (`research/raport-18-nastepna-fala.md:28`). Przy 199k cały przyrost kroku decode to FA: +10,6 ms, 30% czasu GPU (`eksperymenty/2026-11-08-kvq-once-profil.md:10`). | mamy, zmierzone u nas |
| zajętość pamięci | [[2026-11-06-ctx-262k-fit]], [[raport-65-vram-rezerwa-mtp]] | Szczyt 23 367 MiB przy 255k, zapas 1193 MiB (`eksperymenty/2026-11-06-ctx-262k-fit.md:18`). | mamy, zmierzone u nas |
| rachunek pamięci KV | [[raport-56-orca-3090]], [[qwen3-8-27b]] | Zmierzone nachylenie 29,1 KiB/token wobec teoretycznych 18,4. Około 10,7 KiB/token jest niewyjaśnione (`research/raport-56-orca-3090.md:15-16`), test w K-034 (`KOLEJKA-TESTOW.md:296`). | mamy, zmierzone u nas |
| batching a intensywność | [[koszt-szerokosci-weryfikacji]], [[lekcja-rzadkosc-vs-weryfikacja]] | V16 − V5 = 6,40 ms przy 2k, 12,45 ms przy 64k (`metody/koszt-szerokosci-weryfikacji.md:10`). | mamy, zmierzone u nas |

## 6. Sprzęt

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| CPU vs GPU | [[baco-runtime-suspend]], [[final-modele-per-vram]] | Model czytany przez PCIe: 4,4 zamiast 92 t/s (`lekcje/baco-runtime-suspend.md:10`). 3080 LFM z `--n-cpu-moe 20`: 40,83 t/s (`REKORDY.md:203`). Brak bazy dla czystego CPU. | mamy, zmierzone u nas |
| architektura GPU | [[rdna3-gfx1100]], [[karty-nvidia-parametry]], [[lekcja-siatka-pelna-fala]] | 96 CU / 48 WGP, wave32, LDS 128 KiB/WGP, L2 6 MiB + IC 96 MiB (`karty/rx-7900-xtx.md:12`). | mamy, zmierzone u nas |
| tensor cores (WMMA na RDNA3) | [[wmma-small-n]], [[rdna3-gfx1100]] | Teoretycznie ~123 TFLOPS FP16 (`rocm/rdna3-gfx1100.md:16`). Zmierzone 71 TFLOP/s bf16 w PyTorch (`eksperymenty/2026-10-12-mtp-trening-faza1.md:15`). | mamy, zmierzone u nas |
| HBM / GDDR | [[rx-7900-xtx]], [[karty-nvidia-parametry]] | GDDR6: 960 GB/s nominalnie, 926 GB/s zmierzone (`research/raport-24r-mmvq-pasmo.md:10`). | mamy, zmierzone u nas |
| DRAM vs SRAM | [[lekcja-littles-law-gemv]], [[lekcja-prefetch-mall-xtx]] | Potrzeba ~6,0 KB w locie na CU (`lekcje/lekcja-littles-law-gemv.md:10`). Prefetch do MALL dał +0,2…0,6%, czyli szum (`lekcje/lekcja-prefetch-mall-xtx.md:10`). | mamy, zmierzone u nas |
| NVLink | [[wafer-gpu-perf-lista]], [[pplx-kernels]] | Tylko wzmianki (`research/wafer-gpu-perf-lista.md:10`, `repo/pplx-kernels.md:12`). | luka |
| InfiniBand | — | Zero trafień. | luka |
| Groq LPU | — | Zero trafień. | luka |
| TPU | [[raport-39e-torchtpu]], [[tokamax]] | TorchTPU nie ma znaczenia dla XTX (`research/raport-39e-torchtpu.md:10`). | mamy, opis |
| inferencja na brzegu (edge) | [[modele-telefon]], [[nemotron-3-5-bolt-e4b]], [[strix-halo]] | EmbeddingGemma Q8_0: 87 tok/s na telefonie (`modele/modele-telefon.md:14`). LLM na brzegu niezmierzone. | mamy, opis |
| chmura vs urządzenie | [[raport-05-chmura]], [[produkt-platformy-i-lab]] | Vast: 3090 0,23 $/h, 4090 0,51 $/h, 5090 0,73 $/h (`research/raport-05-chmura.md:12`). Brak TCO lokalnie vs API. | mamy, opis |

## 7. Oprogramowanie

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| CUDA / HIP | [[hip]], [[cuda-stos]], [[latki-na-nvidia]] | Fork buduje się dla CUDA: 579/579 kroków w 835 s (`lekcje/lekcja-build-cuda-0057-0070.md:10`). | mamy, zmierzone u nas |
| kernele | [[mmvq-multikolumnowe]], [[fattn-kvq]], [[podrecznik-gpu]] | Decode plain wykorzystuje 75,7% pasma XTX (`metody/podrecznik-gpu.md:10`). | mamy, zmierzone u nas |
| grafy CUDA/HIP, replay PM4 | [[hip-graph-narzut]], [[pm4-replay]] | Granica kernela w grafie HIP: 3,2–3,4 µs, czyli 16–19% kroku (`rocm/hip-graph-narzut.md:10`). PM4: LFM 259,3 → 293,6 t/s, Qwen MTP 103,7 → 108,8 (`eksperymenty/lfm-runda-4-pm4.md:10`). 3090 bez grafów CUDA: −5,3% (`eksperymenty/2026-11-07-kampania-nvidia-vast.md:50`). | mamy, zmierzone u nas |
| fuzja kerneli | [[fuzje-weryfikacji]], [[fuzje-lfm-moe]] | 2156 → 972 kerneli, krok 41,7 → 36,38 ms (`kernele/fuzje-weryfikacji.md:10`). | mamy, zmierzone u nas |
| PyTorch | [[2026-10-12-mtp-trening-faza1]] | Używany tylko do treningu i lustra grafu. Lustro MTP zgadza się z llama.cpp w top-1 na 98,4% (`eksperymenty/2026-10-12-mtp-trening-faza1.md:18`). | mamy, zmierzone u nas |
| vLLM | [[1cat-vllm]], [[vllm-rocm-octave]], [[hyperqwen]] | Nigdy nie uruchomiony u nas. KV k3v3 vLLM na gfx1100 = 75% naszego q4_0 (`repo/vllm-rocm-octave.md:10`). | mamy, opis |
| SGLang | [[sglang-hicache]], [[sglang-unified-memory]] | Tylko cudze liczby. | mamy, opis |
| TensorRT-LLM | [[firma-nvidia]] | Tylko wzmianka o TensorRT for RTX (`ludzie-firmy/firma-nvidia.md:12`). | luka |
| llama.cpp | [[llama-cpp-fork]], [[ggml-org]] | Upstream → topka: ×3,21 na czacie (`research/raport-wyniki-xtx-2026-10-19.md:10`). | mamy, zmierzone u nas |
| Ollama | [[ollama]] | 3090: Qwen 39,0 / LFM 180,5 t/s, czyli tyle co A0 (`ludzie-firmy/ollama.md:12`). Na XTX brak pomiaru. | mamy, zmierzone u nas |
| GGUF | [[kwanty-gguf]], [[raport-24t-entropia-wag]] | Q4_K ma 3,86 z 4 bitów entropii, kompresja nic nie da (`research/raport-24t-entropia-wag.md:10`). | mamy, zmierzone u nas |
| serwer zgodny z OpenAI | [[produkt-stack]], [[jakosc-mini]] | HTTP + szablon + tokenizacja razem < 3 ms. Stały koszt krótkiego żądania ~139 ms (`eksperymenty/2026-11-14-k002-k003-k013-xtx.md:10`). | mamy, zmierzone u nas |

## 8. Benchmarking

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| benchmarking | [[spec-sweep]], [[xtxbench-szybki-ab]], [[pomiar-abba]] | Szum A/A: 0,02–0,15% decode (`metody/xtxbench-szybki-ab.md:10`). | mamy, zmierzone u nas |
| symulacja ruchu | [[ksztalt-ruchu-agentowego]], [[agentx-harness]], [[lekcja-agent-prefill-nie-decode]] | AgentX: wejście p50 88 768 / p90 204 288 tok. (`metody/ksztalt-ruchu-agentowego.md:10`). Prefill zajmuje 58% zegara sesji `[SZACUNEK]` (`lekcje/lekcja-agent-prefill-nie-decode.md:10`). | mamy, zmierzone u nas |
| testy obciążeniowe | [[pm4-soak]], [[raport-26-kolejka-gpu]] | 1205 zapytań bez błędu (`research/raport-26-kolejka-gpu.md:10`). | mamy, zmierzone u nas |
| profilowanie | [[rocprof]], [[att-gfx1100]], [[dowod-z-profilu]] | Profil kroku przy 199k (`eksperymenty/2026-11-08-kvq-once-profil.md:10`). | mamy, zmierzone u nas |

## 9. Optymalizacje atencji

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| FlashAttention | [[fattn-kvq]], [[2026-11-08-fa-d256-prefill]] | Fill 255k: 466,3 → 493,4 t/s (+5,8%) (`eksperymenty/2026-11-08-fa-d256-prefill.md:10`). | mamy, zmierzone u nas |
| PagedAttention | — | Brak. Jedyna wzmianka o „block table” jest w [[raport-21m-declarative-attention]]. | luka |
| MQA / GQA | [[fattn-kvq]], [[fa-kv-kwantyzowane-cuda]], [[lfm-runda-2]] | KV q8_0 bez kernela czytającego grupę GQA raz: przy 98k 187 → 144 t/s (`eksperymenty/lfm-runda-2.md:12`). | mamy, zmierzone u nas |
| okno przesuwne (SWA) | [[gemma-4]], [[drafter-dspine]] | Gemma 4 ma iSWA z oknem 1024 (`modele/gemma-4.md:10`). DSpine ma SWA 8192, więc KV draftu to ~47 MB (`modele/drafter-dspine.md:18`). | mamy, opis |
| attention sinks | — | Brak. Jest tylko `<sink>` w CPLM (`research/raport-21c-cplm.md:10`). | luka |
| kompresja KV | [[kwanty-gguf]], [[vllm-rocm-octave]], [[raport-24g-hipfire]] | Stan GDN w int8: KLD 0,0234 przy progu 0,005, odrzucony (`research/raport-24g-hipfire.md:10`). | mamy, zmierzone u nas |

## 10. Batching

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| batching statyczny | — | Brak. | luka |
| batching ciągły (`-np`) | [[raport-24c-wiele-zapytan]], [[mtplx]] | 4090: +36% agregatu (`REKORDY.md:193`). Na XTX odrzucone (`research/raport-24c-wiele-zapytan.md:10`). | mamy, zmierzone u nas |
| rozmiar batcha vs latencja | [[raport-24c-wiele-zapytan]], [[raport-56-orca-3090]] | 3090 `-np 2`: agregat 82,1 vs 64,4 t/s (+27%) (`research/raport-56-orca-3090.md:52-53`). | mamy, zmierzone u nas |
| chunked prefill (ubatch) | [[2026-10-18-lfm-ubatch-2048]], [[2026-11-14-k104-krotki-ogon-promptu]] | ub 2048: pp4096 6108 → 7148 t/s (`eksperymenty/2026-10-18-lfm-ubatch-2048.md:10`). Ogon promptu jednym batchem: 0 ms zysku, odrzucone (`eksperymenty/2026-11-14-k104-krotki-ogon-promptu.md:10`). | mamy, zmierzone u nas |
| interferencja prefill–decode | [[2026-10-19-workload-omp]] (tylko kontekst) | Brak pomiaru, choć przez 37% czasu w locie są ≥ 2 żądania (`eksperymenty/2026-10-19-workload-omp.md:10`). | luka |

## 11. Cache

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| cache prefiksów | [[2026-10-18-cache-promptu-agenta]], [[lekcja-cache-ram-za-maly]] | Start sesji: 8019 → 1612 ms (`eksperymenty/2026-10-18-cache-promptu-agenta.md:10`). 74% prefillu to ponowne czytanie (`lekcje/lekcja-cache-ram-za-maly.md:10`). | mamy, zmierzone u nas |
| prompty przyjazne dla cache | [[wspolny-poczatek-promptu]], [[akv-cache-agentow]] | Tylko cudze liczby (Maya: 19×) (`metody/wspolny-poczatek-promptu.md:10`). | mamy, opis |
| prompt caching (zapis/odczyt slotu) | [[cache-sesji-na-dysku]], [[2026-11-08-cachesave-30137]] | Sesja 53k: restore 2,51 s zamiast ~61,5 s prefillu (`produkt/cache-sesji-na-dysku.md:10`). | mamy, zmierzone u nas |
| offloading KV | [[decyzje/2026-10-19-kv-tylko-w-ram]], [[2026-10-19-kv-tylko-w-ram]], [[sglang-hicache]] | Przywracanie z `--cache-ram`: ~2,1 GB/s (`metody/ksztalt-ruchu-agentowego.md:12`). Decyzja: KV tylko w RAM. | mamy, zmierzone u nas |
| routing świadomy cache | [[ksztalt-ruchu-agentowego]], [[sglang-hicache]] | Polityki radix/lane/cram badaliśmy tylko w symulacji (`metody/ksztalt-ruchu-agentowego.md:12`). | mamy, opis |
| długi kontekst | [[2026-11-06-sesja-uzytkownika-final-mode]], [[2026-11-08-kvq-once-profil]] | 120,8 t/s do 139k; przy 128–160k spada do 95,8 (`eksperymenty/2026-11-06-sesja-uzytkownika-final-mode.md:10`). | mamy, zmierzone u nas |

## 12. Dekodowanie spekulacyjne

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| draft–target | [[glowica-mtp]], [[drafter-dflash]] | T=1: MTP 81,1 vs DFlash 71,9 t/s (`eksperymenty/2026-10-10-sweep-mtp-dflash.md:26-27`). | mamy, zmierzone u nas |
| rejection sampling | [[sprzezone-probkowanie-draftu]], [[fly-stratna-weryfikacja]] | Sprzężony Gumbel przy T=1: 107,6 → 111,4 t/s (+3,5%) (`metody/sprzezone-probkowanie-draftu.md:18`). DFlash nie ma rejection sampling (`eksperymenty/2026-10-10-sweep-mtp-dflash.md:29`). | mamy, zmierzone u nas |
| akceptacja | [[raport-40-akceptacja-prozy]], [[glowica-mtp]] | Warunkowa akceptacja na kolejnych pozycjach: 0,655/0,503/0,407/0,382 (`research/raport-40-akceptacja-prozy.md:10`). | mamy, zmierzone u nas |
| n-gram (lookup) | [[2026-10-18-lookup-ogon]], [[suffixdecoding]] | `mvs`: 166,2 → 400,9 t/s (×2,41) (`eksperymenty/2026-10-18-lookup-ogon.md:10`). | mamy, zmierzone u nas |
| Medusa | [[glowica-mtp]] | Jedna linia: dla Qwen3.8-27B nie ma Medusy (`modele/glowica-mtp.md:24`). | luka |
| EAGLE | [[eagle-4]], [[ekosystem/eagle-4]] | Tylko szacunek: proza PL +3…6% `[INFERENCE]` (`research/raport-52-eagle4.md:10`). | mamy, opis |
| spekulacja vs rozmiar batcha | [[lekcja-akceptacja-h100-nie-przenosi-sie]], [[mtplx]] | V16/V1 = 1,34 przy 2k, 1,61 przy 64k (`lekcje/lekcja-akceptacja-h100-nie-przenosi-sie.md:10`). `-np 4` z MTP w ogóle nie startuje (`research/raport-56-orca-3090.md:94`). | mamy, zmierzone u nas (bez wielu strumieni) |

## 13. Kwantyzacja

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| formaty | [[kwanty-gguf]], [[nvfp4]] | NVFP4 RTN jest o 12–17% gorszy od Q4_0 przy tych samych 4,5 bpw (`eksperymenty/2026-10-16-nvfp4-skala-globalna-sim.md:10`). | mamy, zmierzone u nas |
| PTQ | [[raport-57a-gsq-rco]], [[2026-10-18-e1-kwanty-27b-kld]] | Te same bajty: AP vs UD Q3_K_XL, KLD czat −12%, kod −23% (`eksperymenty/2026-10-18-e1-kwanty-27b-kld.md:10`). | mamy, zmierzone u nas |
| W4A16 | [[humming]], [[2026-11-09-qwen-warp-vs-fork-3090]] | Wagi W4 g128 ~13,2 vs ~16,4 GB/krok, czyli ×1,24 `[SZACUNEK]` (`eksperymenty/2026-11-09-qwen-warp-vs-fork-3090.md:29`). | mamy, opis |
| W8A8 | [[humming]], [[inferrous]], [[cache-q8-1]] | Opis. Nasze MMVQ to w praktyce wagi K-quant × aktywacje q8_1 (`kernele/cache-q8-1.md:10`). | mamy, opis |
| kwantyzacja KV | [[kwanty-gguf]], [[lfm-runda-2]], [[2026-10-16-kvq-cuda]] | KV q8_0 jest wolniejsze od q4_0 o +30,1% przy 98k (`eksperymenty/lfm-runda-2.md:12`). | mamy, zmierzone u nas |
| pomiar wpływu na jakość (KLD, PPL, ewaluacje) | [[bramka-kld-kanarki]], [[kld-po-polsku]], [[jakosc-mini]] | Bramka 2σ (`metody/bramka-kld-kanarki.md:10`). Ten sam plik: KLD 0,0519 przy ctx 512 vs 0,0665 przy 2048 (`lekcje/lekcja-kld-protokoly.md:10`). | mamy, zmierzone u nas |

## 14. Poziom modelu

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| rozmiar vs szybkość | [[final-modele-per-vram]], [[raport-33-modele-na-karty]] | LFM2.5 293,7 vs Qwen 27B 109,0 t/s (`eksperymenty/stan-2026-10-15.md:10`). | mamy, zmierzone u nas |
| routing LLM | [[laya-mlx]] | Jedno zdanie o routerze „mały ↔ duży” (`repo/laya-mlx.md:12`). | luka |
| SLM | [[nemotron-3-5-bolt-e4b]], [[modele-telefon]] | E4B Q4_K_M ma 6,18 GB, niezmierzony (`modele/nemotron-3-5-bolt-e4b.md:10`). | mamy, opis |
| destylacja | [[raport-10-post-training]], [[2026-10-16-mtp-pl-pilot]], [[liquidai]] | Samodestylacja MTP: −0,2 / +0,21 / +0,02% (`eksperymenty/2026-10-16-mtp-pl-pilot.md:14`). QAD-Q4_0: 164,5 → 226,8 t/s (`modele/lfm2-5-24b-a2b.md:20`). | mamy, zmierzone u nas |

## 15. Równoległość

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| po co wiele GPU | — | W naszym serwerze są XTX i 5060 Ti ([[rx-7900-xtx]], [[rtx-5060-ti]]), ale nigdy nie dzieliliśmy modelu między nie. | luka |
| równoległość modelu / potokowa | [[project-maya]] (cudze) | Tylko cudze liczby: TP bez P2P na 9 GPU, 42,9 → 66,8 t/s (`repo/project-maya.md:24`). | luka |
| narzut komunikacji | [[pplx-kernels]] (cudze) | NVLink EP8 dispatch 41,6 µs (`repo/pplx-kernels.md:12`). Na PCIe nic. | luka |
| równoległość danych | — | Brak. | luka |
| równoległość tensorowa | [[tensorfold]], [[saber-engine]] (cudze) | TP=2 == TP=1 bitowo (`repo/tensorfold.md:16`). Sami nie mierzyliśmy. | luka |

## 16. Dezagregacja

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| dezagregacja prefill–decode | [[wafer-gpu-perf-lista]], [[ista-daslab]] | Tylko wzmianki (`research/wafer-gpu-perf-lista.md:10`, `ludzie-firmy/ista-daslab.md:21`). | luka |
| transfer KV | [[przelaczanie-main-uncensored]] (pokrewne) | Pokrewny pomiar: slot z drugiego modelu przywraca się w 2,51 s (`produkt/przelaczanie-main-uncensored.md:10`). Transferu między węzłami brak. | luka |
| kiedy dezagregować | — | Brak. | luka |

## 17. Produkcja

| temat | nasze notatki | liczba / fakt | status |
|---|---|---|---|
| repliki | — | Brak. | luka |
| autoskalowanie | — | Brak. | luka |
| zimny start | [[opoznienia-ttft]], [[baco-runtime-suspend]] | Start Qwena: 38,5 → 6,55 s (`research/raport-45-opoznienia.md:10`). Z `--no-mmap` pierwszy prompt idzie 0,39–1,07 t/s (`KOLEJKA-TESTOW.md:554`). | mamy, zmierzone u nas |
| obserwowalność | [[reactor-monitor]], [[gpu-guard]], [[kfd-smi-eventy]] | Telemetria: 6567 wierszy, junction śr. 78 / maks. 89 °C (`eksperymenty/2026-11-06-xtx-eco-instalacja.md:14`). Brak metryk na żądanie, np. Prometheus. | mamy, zmierzone u nas |

---

## Luki według przydatności dla nas

Kryteria: jeden użytkownik lokalnie, agenci, XTX i konsumenckie NVIDIA, Enigma.

1. **Interferencja prefill–decode.** Agenci z subagentami mają przez 37% czasu ≥ 2 żądania w locie, a prefill to 58% zegara sesji. Przy `-np 1` nikt nie zmierzył, ile decode traci na cudzym prefillu.
2. **Routing LLM.** Mamy dwa modele (LFM2.5 ~294 t/s, Qwen 27B ~120 t/s), a Enigma ma klasy VRAM. Wybór modelu per żądanie może dać więcej niż kolejna łatka kernela.
3. **Równoległość modelu / potokowa** (`-sm layer`). Nasz serwer ma XTX + 5060 Ti (40 GB), a użytkownicy Enigmy mają po dwie karty. Podziału warstw, także AMD+NVIDIA, nigdy nie mierzyliśmy.
4. **Po co wiele GPU** (pojemność vs prędkość). Enigma potrzebuje reguły, kiedy druga karta pomaga przy 262k, a kiedy szkodzi.
5. **Równoległość tensorowa** (`-sm row`). Jedyna droga, by dwie konsumenckie karty przyspieszyły decode. Brak danych na RDNA3 i Ampere.
6. **Narzut komunikacji po PCIe** (karty konsumenckie bez P2P). To on decyduje o 3 i 5; mamy tylko cudze liczby z NVLink.
7. **PagedAttention / stronicowane KV.** Warunek wielu slotów agentów przy 262k na 24 GB: slot to ~2,4 GB stanu (`KOLEJKA-TESTOW.md:705`), a `-np 4` z MTP nie startuje.
8. **Attention sinks / StreamingLLM.** Brak polityki na sesje agenta ponad 262k; p90 wejścia AgentX to już 204k.
9. **TensorRT-LLM / TensorRT for RTX.** To realny punkt odniesienia konkurencji NVIDIA dla Enigmy, a nie mamy żadnej liczby.
10. **Równoległość danych.** XTX + 5060 Ti jako dwa niezależne serwery dla roju agentów to tani zysk, niezmierzony.
11. **Medusa.** Praktycznie zbędna: MTP jest wbudowane, a głowic Medusy dla Qwen3.8 brak. Tylko teoria do kompletu.
12. **NVLink.** Dotyczy jedynie 2×3090 z mostkiem, czyli niszy wśród użytkowników Enigmy.
13. **Batching statyczny.** Sama teoria; llama-server i tak robi batching ciągły.
14. **Kiedy dezagregować.** Odpowiedź „nie przy jednej karcie” warto zapisać z progiem.
15. **Transfer KV.** W sensie dezagregacji brak; pokrewny restore slotu już zmierzyliśmy.
16. **Dezagregacja prefill–decode.** Centra danych; u nas co najwyżej egzotyka typu „XTX robi prefill, druga karta decode”.
17. **Repliki.** Nie dotyczy produktu lokalnego, najwyżej Enigmy Business.
18. **Autoskalowanie.** Nie dotyczy lokalnej inferencji.
19. **Groq LPU.** Tylko wiedza o konkurencji w chmurze.
20. **InfiniBand.** Tylko centra danych.

### Półluki (status „opis” albo pomiar częściowy), warte uwagi

- **P99** nigdzie nie mierzymy.
- **$/Mtok** brak; mamy tylko J/token.
- **Spekulacja przy wielu strumieniach** niezmierzona.
- **vLLM i SGLang** nigdy nie uruchomione na naszych kartach.
- **EAGLE** tylko szacowany.
- **Port W4A16** (qwen-warp, ×1,24) niewykonany.
- **Rachunek intensywności arytmetycznej XTX** nigdzie nie zapisany.
- **Ollama na XTX** niezmierzona.
- **Baza dla czystego CPU** brak.

## Powiązane
- [[llm/_hub|llm]]
- [[trening-llm-mapa]]
- [[KOLEJKA-TESTOW]]
- [[sufit-pasma-i-mapa-czasu]]
- [[podrecznik-gpu]]
