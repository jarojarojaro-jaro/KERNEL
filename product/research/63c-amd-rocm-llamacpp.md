# 63c — AMD / ROCm / nasza karta: RDNA-FAST, QSA (tweet pentacoxian), LithosAI, llama.cpp v0.9.0, vLLM 0.33 ROCm, KV q5_1

Data: 2026-11-05. Research wyłącznie CPU: bez GPU, bez pobierania wag. Klony kodu (tylko kod): `~/src/research63/{RDNA-FAST,qsa,llama.cpp}`.
Oznaczenia: `[SZACUNEK]` to mój rachunek, nie pomiar; `[INFERENCE]` to wniosek z kodu lub tekstu, którego nie uruchamiałem.

Rejestr źródeł (`~/KERNEL/wiki/ZRODLA.md`) i grep po `wiki/` oraz `product/research/`: RDNA-FAST, pentacoxian/QSA, LithosAI, llama.cpp v0.9.0, cheaptokens i ROCM_OCTAVE **nie były badane**. Wcześniej był tylko wpis z cudzego repo: „review the serrynaimo ROCmFPX fork (not adopted)” (`product/research/watch/2026-10-20.md:270`). vLLM MonoKernel jest w 15a (RFC #60904, PR #60397/#60889), więc dla niego podaję tylko **deltę**. Bazy porównania: topka `~/wt/topka`, gałąź `topka` @ `d5839abfb`, zainstalowana `f9b84bcfa` (`~/llama-topka/COMMIT`), upstream merge-base **b11528** (`e60eff95f`, 2026-10-09). Enigma ma przypięte **b11856** (`3642238`, 2026-10-24; `~/KERNEL/app/engine/README.md:110`).

## 0. Najważniejsze (TL;DR)

1. **Przełom na długi kontekst: QSA dla Qwen3.8-27B.** Tweet pentacoxian to wątek o forku [pentaCoxian/Qwen-QSA-llama.cpp](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp/tree/fe08b167477a8eb651dc71ded753542d72c46cd0). Fork dokleja do 16 warstw pełnej atencji **wyuczone indeksery** (52.4M parametrów FP32, backbone zamrożony, 300 kroków treningu). Każde zapytanie czyta tylko 2048 tokenów (bloki po 4) zamiast całego KV. Wynik na RTX 4090 przy 255K kontekstu: decode **114.7 vs 40.6 t/s** (dense), prefill **2375 vs 1345 t/s**, 262K kontekstu z wizją w 22.8 GiB ([README:13-20](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp/blob/fe08b167477a8eb651dc71ded753542d72c46cd0/README.md)). U nas decode spada z 136.5 t/s (1.7k) do 74.5 t/s (199k) (`wiki/REKORDY.md`, WYNIKI-XTX). Tę różnicę QSA prawie likwiduje `[SZACUNEK]`. **Jakości przy długim kontekście nikt nie zmierzył** (KL sparse vs dense „Not tested”).
2. **RDNA-FAST** ([serrynaimo/RDNA-FAST](https://github.com/serrynaimo/RDNA-FAST/tree/4426ca35c4d2a1b57b37e661152f52972a3777b5)) to fork llama.cpp/ROCmFPX dla RX 7900 **XT** na Windows i ROCm 10.1. Większość ich decode-owych trików mamy w topce, często mocniejszych: kvq WMMA, rollback przez replay, residual w MMVQ, reuse q8_1, fuzja conv+snapshot. Liczą się 4 rzeczy, których nie mamy:
   - prefill przez **f16 WMMA GEMM** (`rocm_wmma_gemm`);
   - **chunked GDN** dla RDNA3;
   - **dynamiczny słownik draftu** (12k stałych + 12k topu celu);
   - **MTP lean reserve** (784 → 80 MiB), dzięki któremu `-ub 2048` mieści się w pamięci.

   Do tego **lista pułapek ROCm 10.x** (clang 24 i runtime): LDS bez wyrównania 16 B, rozbite szerokie store'y, spille MMQ przy occupancy 2 oraz runtime raportujący 128 KB LDS na „multiprocessor”, co psuje heurystyki FA.
3. **Runtime ROCm 10 i LDS** ([b462181](https://github.com/serrynaimo/RDNA-FAST/commit/b462181)). Runtime HIP z ROCm 10 zwraca 128 KB jako `maxSharedMemoryPerMultiProcessor`, więc `cudaOccupancyMaxActiveBlocksPerMultiprocessor` daje 2–3× za dużo bloków. Skutek u nich: atencja D=256 GQA6 wolniejsza o 13–15%, prompty 512 przy D=128 wolniejsze o 29%.
   - My jesteśmy na runtime 10.0 pre4 (`13-rocm-10.1.md:5`). Topka wywołuje to API w `launch_fattn` (`~/wt/topka/ggml/src/ggml-cuda/fattn-common.cuh:1147`), czyli w prefill FA.
   - Najtańszy eksperyment w tym raporcie: najpierw odczytać właściwość urządzenia, potem założyć cap.
4. **vLLM 0.33: `ROCM_OCTAVE`**. To natywny 3-bitowy KV na **gfx1100** dla Qwen3.8-27B (head 256): 216 B na slot (token, głowica KV), czyli **75% naszego q4_0**. Przy 380k NLL rośnie o +0.00125 nata względem fp16; produkcyjnie na 7900 XTX od 2.10.2026 ([PR #59774](https://github.com/vllm-project/vllm/pull/59774)).
   - Mechanizm: losowe znaki + Walsh-Hadamard, kodebook Lloyd-Max N(0,1) na 3 bitach, skala zachowująca normę, `v_perm_b32` jako LUT.
   - Dla nas: −1.1 GiB KV przy 262k. To droga do **262k na 24 GB** bez QSA.
5. **llama.cpp v0.9.0** to wydanie semver (taka numeracja istnieje od sierpnia 2026, [ggml#1579](https://github.com/ggml-org/ggml/discussions/1579)). Tag `cd959ba` = nightly **b12110**, ggml 0.29.0. Od pinu Enigmy b11856 jest **254 commity**, od bazy topki b11528 **582**.
   - Dla Enigmy (CUDA/Vulkan): fuzja gate/up+GLU w MMQ (+4.6…7.4% pp Qwen 27B na GB10), MoE MMQ fuzja (+5.7…17%), split-K dla małych N na Vulkan RDNA3 (MTP z draftem 8: **+13%** decode).
   - Dla topki: poprawki stanu MTP/rollbacku (#30141, #31350, #31368) i **zapis stanu draftu w pliku slotu** (#30574; akceptacja Qwen MTP po restore 37% → 49%). Topka tego nie ma.
6. **LithosAI MI355X: „2116 t/s/user” nie jest zmierzonym tokens/s.** To `6 / czas_kroku` przy **założonej** akceptacji 75% z 8 (2.83 ms → 2116). Silnik zamknięty. Techniki (megakernel, programowy PDL, komunikacja w kernelu) znamy z 15a/16a. U nas programowy PDL dał realnie ≈ +3% (16a).
7. **cheaptokens / q5_1.** Ścieżka „FA po cichu na CPU” z bloga dotyczy buildu **10791** (wrzesień). Od #28079 (9.09) CUDA przy brakującej instancji konwertuje K/V do f16 na GPU (`fattn.cu` b11856:495-511).
   - Enigma zawsze daje K = V ∈ {q4_0, q8_0, f16} (`catalog/data.ts:5`, `server/engine.ts:478`), a te pary są w domyślnym buildzie (`GGML_CUDA_FA_QUANTS="q4_0-q4_0;q8_0-q8_0;f16-f16;bf16-bf16"`). **Bezpieczne na CUDA/HIP/Metal/CPU.**
   - Ryzyko resztkowe: **Vulkan bez `subgroup_shuffle`/`subgroup_vote`** oraz nietypowe head dim. Wtedy FA idzie na CPU, a przy kwantyzowanym V i `-fa on/auto` nie ma żadnego probe'a. Proponuję strażnika „`splits =` w logu > 3 → alarm i fallback”.

## 1. Punkt odniesienia (nasze liczby)

| metryka (XTX, Qwen3.8-27B UD-Q4_K_XL, topka) | wartość | źródło |
|---|---|---|
| spec_sweep T=1 | 114.8 t/s (host-gap 117.9) | `~/KERNEL/wiki/REKORDY.md` (WYNIKI-XTX-2026-10-19:44-45) |
| proza E0 T=1 | 78.93 t/s | `37-proza-100.md:13` |
| code-edit `mvs` T=0 | 433.8 t/s | `43-integracja-2026-10-20.md:24` |
| decode long_ctx 1.7k / 94k / 199k (T=0, MTP4+W16) | 136.5 / 105.6 / 74.5 t/s | `WYNIKI-XTX-2026-10-19.md:82-86` |
| pp4096 / TTFT 94k | 1123 t/s / 123 s | `NOTES.md:397`, `NOTES.md:322` |
| profil pp4096 | MMQ 81.3%, GDN 4.0%, FA 2.2% (przy d32k FA 13–24%) | `24v-prefill-fa.md:15-19` |
| konfiguracja | ctx 204800, KV q4_0, `-ub 512` (Qwen), MTP n=4 + słownik 64k, lookup W16, PM4 | `~/qwen-opt/run-topka.sh`, `run-llm.sh:118` |

## 2. RDNA-FAST (serrynaimo) — przeskanowane w całości

**Co to jest.** Publiczny downstream llama.cpp i ROCmFPX z formatami wag ROCmFP2/3/4/6/8 autorstwa Charlie12345 ([README:587-617](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/README.md)). Na nim zbudowano serwer agentowy „RDNA-FAST”. Sprzęt: **RX 7900 XT 20 GB**, Windows 11, ROCm 10.1. Model: Swift 1.5 IQ4_XS (fine-tune Qwen3.8-27B). Autor pisze wprost: „Nothing here has been measured on an XTX” ([README:55-59](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/README.md)). Upstream zmergowany do 2026-11-03 (`2860e45`, `bbcf2df`, `17a0484`). HEAD `4426ca3`, 2026-11-05.

### 2.1 Twierdzenia i ich warunki

| twierdzenie | warunki | źródło |
|---|---|---|
| sesja 2 agentów 130 s → 93 s vs LM Studio | ta sama kwanta i ctx, 14 requestów, „best of four runs” | [README:65-87](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/README.md) |
| decode z MTP: proza 59.8, kod 95.8 t/s (peak, T=1); bez MTP 36.8 | 450 tok., best of 4 | README:106-113 |
| zimny prefill 17k/41k/69k: 988 / 881 / 770 t/s | ub 2048, WMMA GEMM | README:115-121 |
| copy boost (ngram-map-k4v) do 315 t/s | najlepsza z 12 edycji | README:78, 214 |
| WMMA GEMM: int8 MMQ 40–44 TFLOPS → f16 WMMA 76–92 TFLOPS (FP4); stock quants @512: 39–48 → 45–48 | kernel-level | README:382-397 |
| 17k cold IQ4_XS 781 → 864 t/s (+10.6%), KLD vs int8 0.0024, PPL 6.5080 vs 6.5077 | | README:398-408 |
| `GGML_HIP_FA_GQA6`: decode +10–12% @41k, +2–6% @17k | vs stock (f16 kopia KV) | README:255 |
| `GDN_CONV_SNAP` + `MMVQ_FUSE_VERIFY`: decode +2.3–3.9%, krótkie prompty +9–17% | | README:261-262 |
| `ROCMFPX_DRAFT_VOCAB=24576`: decode +9% krótki ctx, +3–5% @41k | | README:248 |
| rollback przez replay: −0.8 GB VRAM przy 2 slotach, decode bez zmian, T=0 identyczne | | README:554-583 |
| `ROCMFPX_MTP_LEAN_RESERVE`: 784 → 80 MiB, dzięki temu `-ub 2048` przy `-c 98304` | | README:265 |
| shared pass 2 slotów: łącznie 46 → 66.7 t/s, logity bit w bit jak osobno | | README:525-545 |
| ROCm 10.1 z poprawkami: prompt-sized przypadki 3.1% szybciej niż ROCm 7.2 | | [22261fa](https://github.com/serrynaimo/RDNA-FAST/commit/22261fa) |

**Wiarygodność.**
- Raportują „best of N runs”, czyli maksimum, nie medianę. Porównują ze słabą bazą (LM Studio 2.69).
- Porównania między buildami są w porządku: przeplatane „best of two interleaved rounds”, KLD/PPL przy zmianach numeryki, test-backend-ops przy każdym kernelu.
- Ujemne wyniki są uczciwie opisane:
  - `MMVQ_FUSE_VERIFY_GLU`: 2.2× wolniej;
  - `ROCMFPX_MMQ_FUSION` na RDNA3: −3…16%;
  - `GGML_CUDA_DQ_MMV` na 7900 XT: −6…24% per kernel;
  - FP8 GEMM „napisany bez karty RDNA4” ([README:275-279](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/README.md)).
- Commity współtworzone z Claude Opus 5.5 (np. [d1d2c74](https://github.com/serrynaimo/RDNA-FAST/commit/d1d2c74)). Ten sam styl pracy co u nas: tag na każdą zmianę, przełącznik env, pomiar przed i po.

**Proces myślowy autorów** (z commitów):
1. Najpierw profil, potem fuzja. Kopie f16 całego KV na każde wywołanie kosztowały 0.49 ms z 0.99 ms ([fattn-tile.cuh:532-536](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/ggml/src/ggml-cuda/fattn-tile.cuh)), więc powstał kernel czytający q4_0 bezpośrednio.
2. Przy migracji kompilatora szukali spilli w ISA **każdej** instancji MMQ dla gfx1100/1151/1201. Wzięli tylko te wiersze, gdzie occupancy 1 likwiduje scratch i nigdzie nie rośnie ([d1d2c74](https://github.com/serrynaimo/RDNA-FAST/commit/d1d2c74)).
3. Tuner GEMM przestawili z „kształtów biblioteki” na **kształty chunków, które ggml naprawdę wysyła** (6400/6144/4608/1024 × K 5120, …): +5…16% na kernelu ([22261fa](https://github.com/serrynaimo/RDNA-FAST/commit/22261fa)).

### 2.2 RDNA-FAST vs topka — mapa funkcji

| RDNA-FAST | topka (odpowiednik) | ocena |
|---|---|---|
| `FA_Q4_TILE` + `FA_GQA6`: kernel tile (FMA) czyta q4_0, blok na głowicę KV z 6·n kolumnami (n=1..5), 2× nsm bloków ([fattn-tile.cuh:1445-1496](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/ggml/src/ggml-cuda/fattn-tile.cuh)) | **kvq**: WMMA, q4_0/q8_0, kolumny = tokeny×GQA w kafelkach **po 16** (`fattn-kvq.cu:6-31`), 2 bloki/WGP (`:625-632`) | nasze szybsze (WMMA). **Delta:** weryfikacja 3–5 tokenów = 18–30 kolumn = **2 kafelki, czyli KV czytany 2×**. Oni czytają raz. Patrz E7 |
| `GDN_CONV_SNAP` (concat+conv+SILU+snapshoty w 1 kernelu) | `92b14b8b2` (concat, snapshoty i gather w SSM_CONV), `849b69978` (conv+alpha/beta) | mamy |
| `MMVQ_FUSE_VERIFY` (residual w MMVQ dla 2–8 tok.) | `6da87d000` (bias/residual ADD epilog multi-col MMVQ) | mamy |
| `ROCMFPX_RS_REPLAY` (stan bazowy + wejścia k,v,g,beta i replay) | `3f8c8ddff` GATED_DELTA_NET_LAG + `b9b476c87` conv lag + GDN bank | mamy (od października) |
| `MMVQ_Q8_CACHE` | `3a05006a0` reuse q8_1 | mamy |
| `MM_SKINNY` (F32 GEMV dla 9–256 wierszy; bramki GDN w F32 w GGUF IQ4_XS/K) | u nas alpha/beta skwantowane (MMVQ templated, `ca4cccedb`) | nie dotyczy |
| **`ROCMFPX_WMMA_GEMM`** (unpack do f16 w chunkach 64 MB + `rocm_wmma_gemm`, ub ≥ 512) | MMQ int8 WMMA (EPI `f61994f58`, wąskie kafle `6aacfea49`) | **brak**: E3 |
| **`GGML_CUDA_GDN_CHUNKED`** (chunk 16, stan w akumulatorach WMMA F32, hi+lo f16; [gated_delta_net.cu:484-497](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/ggml/src/ggml-cuda/gated_delta_net.cu)) | brak (`gated_delta_net.cu:377` „TODO: chunked”) | GDN to 4% pp4096, więc ≤ 3% (zgodnie z 15d F9). Niski priorytet |
| **`ROCMFPX_DRAFT_VOCAB`**: 12 288 stałych ID (0..k/2) + 12 288 z topu **logitów celu na poprzedniej pozycji**, per sekwencja ([rocmfpx-draft-select.h:17-79](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/src/rocmfpx-draft-select.h)) | statyczny słownik 64k (`--spec-draft-vocab`, `3b15c2b6d`) | **nowy pomysł**: E5 |
| **`ROCMFPX_MTP_LEAN_RESERVE`**: draft ctx rezerwuje tylko 2 kształty, 784 → 80 MiB ([llama-context.cpp:228-244](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/src/llama-context.cpp)) | brak (pełna rezerwa) | **E6**: VRAM na `-ub` lub ctx |
| `ngram-map-k4v` z rampą i shadow probes (do 48 tok. po 6 trafionych sondach) | lookup W16 (16b); kontroler 5/8/16 = stałe W16 | my 433 t/s na XTX vs ich 315 na XT. Pomysł W32–48 z bramką sond: niski priorytet |
| shared pass slotów, slot ranges, SSD cache, priorytety, `--reasoning-preserve` | CACHE_SHARE_MIN, ckpt-vram, slot save/restore | produktowe (Enigma multi-agent); osobny temat |
| MMQ occupancy 1 dla J32 (Q4_0/IQ4_XS/IQ4_NL) pod clang 24 | u nas clang 23; Q4_K MMQ bez spilli VGPR w v100 i v101 (`~/opt/isa101/stats.txt`, sekcja mmq-instance-q4_k) | przy migracji na 10.1 sprawdzić IQ4_XS i Q8_0 |

**Porównanie wyników (z zastrzeżeniami).** XT ma 800 GB/s i 84 CU, XTX 960 GB/s i 96 CU (`~/KERNEL/hardware/rx-7900-xtx.md:11-16`; [AMD RX 7900 XT](https://www.amd.com/en/products/graphics/desktops/radeon/7000-series/amd-radeon-rx-7900xt.html)).
- Ich proza 59.8 t/s (peak) przeskalowana pasmem daje ~72 t/s na XTX. Nasze E0 to 78.9 t/s (mediana 64 próbek), przy ~10% mniejszych wagach po ich stronie (IQ4_XS 15.5 GB vs UD-Q4_K_XL). **Decode mamy lepszy** `[INFERENCE]`.
- Prefill: ich zimne 17k to 988 t/s na XT, czyli ~1130 t/s po przeskalowaniu na CU. Nasz serwer przy 6.6k/29.5k robi 985/945 t/s. **W prefillu są ~15% przed nami** `[SZACUNEK]`: WMMA GEMM + ub 2048 + chunked GDN.

## 3. Tweet pentacoxian_dev/2118071912882712590 → Qwen-QSA-llama.cpp

**Treść** (odczytana przez `api.fxtwitter.com`; xcancel jest zawieszony, nitter offline). Wątek z 2026-11-04 20:04 UTC:
- (1) „Based on @_ryu15_'s QSA model, made a Qwen3.8 27B QSA GSQ-RCO IQ3_S quant… ~115 tok/s decode at 255K, 2,375 tok/s cold prefill, and only 22.8 GiB peak… speed doesn't degrade over depth” (tweet 2118071903789428927; 75 polubień, 7.9k wyświetleń);
- (2) prefill trzyma > 2300 t/s na głębokości;
- (3) „Even on a 24GB card, DFlash2 and vision fits with 256k… almost x3 decode speed”;
- (4) **badany tweet**: „Engine: github.com/pentaCoxian/Qwen-QSA-llama.cpp, Model: huggingface.co/pentacoxian-dev/Qwen3.8-27B-QSA-GSQ-RCO-GGUF”.

4 wykresy obejrzane: RTX 4090, „2.8x greedy, 3.1x sampled”, 2.7–3.1× na 4 zadaniach.

**Mechanizm.** QSA (Qwen Sparse Attention) pochodzi z architektury Qwen3.8-Next ([arXiv 2608.30320](https://arxiv.org/abs/2608.30320)). higa2515 dołożył do Qwen3.8-27B **16 indekserów** (52 434 944 parametrów FP32) tylko w warstwach pełnej atencji:
- 300 kroków treningu przy 16 384 tokenach, backbone, wizja i MTP **niezmienione**;
- wybór **K = 2048 tokenów w blokach po 4 + bieżący blok**;
- cały KV zostaje, więc to **nie jest kompresja KV** ([model card BF16](https://huggingface.co/higa2515/Qwen3.8-27B-QSA-BF16)).

W silniku (`src/models/qwen35.cpp:336-355, 839-897` w forku):
- indekser liczy punkty bloków;
- `ggml_top_k` wybiera bloki;
- `build_attn_qsa_blk` woła **block-sparse FA nad KV Q8_0** (`ggml/src/ggml-cuda/qsa-attn.cu:1-13`; wariant dp4a w `qsa-attn-kernels.cuh:281`). „Cost follows the selected budget instead of the context length”.

Plik modelu to wagi GSQ-RCO IQ3_S (ISTA-DASLab; badane w 57a) z 80 doklejonymi tensorami indekserów. Pozostałe 866 tensorów jest bajt w bajt identycznych ([model card](https://huggingface.co/pentacoxian-dev/Qwen3.8-27B-QSA-GSQ-RCO-GGUF)).

**Wyniki** ([README:7-79](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp/blob/fe08b167477a8eb651dc71ded753542d72c46cd0/README.md)):

| RTX 4090, DFlash2 IQ4_XS, 4 drafty | QSA | dense (te same wagi) |
|---|---|---|
| greedy decode, pusty ctx | 140.9 | 128.3 |
| 64K / 128K / 255K | 132.5 / 123.8 / **114.7** | 81.8 / 63.7 / 40.6 |
| sampled 255K | 113.0 | 35.9 |
| zimny prefill 255K | **2375 t/s (108 s)** | 1345 t/s (190 s) |
| RTX 5090 255K | 141.8 greedy / 2756 pp | — |

Konfiguracja ([serve.sh](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp/blob/fe08b167477a8eb651dc71ded753542d72c46cd0/deploy/qsa27b-24gb/serve.sh)): `-c 262144 -ub 256 -ctk q8_0 -ctv q8_0`, `LLAMA_QSA_RAW_RING=8192` (surowe klucze indeksera tylko dla ostatnich 8192 wierszy, −2 GiB). Prompt cache jest przez to wyłączony (`--cache-ram 0`).

**Jakość i wiarygodność.**
- Recall 24/24 (dense 24/24); two-hop **11/16 vs 12/16**; wizja 14/14.
- KLD vs BF16 przy ubatch 8: proza 0.039, kod 0.152. To głównie koszt kwantyzacji IQ3_S, nie QSA.
- **„Not tested: sparse against dense KL at long context”** ([README:139](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp/blob/fe08b167477a8eb651dc71ded753542d72c46cd0/README.md)).
- Na BF16 przy 32k: PPL QSA/dense = 0.99978. Na UD-Q4_K_M przy 64k: proza PPL **+2.44%**, przechwycona masa atencji 73.8% ([model card BF16](https://huggingface.co/higa2515/Qwen3.8-27B-QSA-BF16)).
- Około 7% odpowiedzi kończy się po ≤ 16 tokenach na jednym zadaniu, z niewyjaśnionej przyczyny (README:136).
- Brak oszustwa w metodzie: to samo zadanie, te same wagi i drafter, dense mierzony na 6 głębokościach. Ale jedna karta, 4 zadania, „harmonic mean”.

R63dAttention dorzucił: w pracy LSA (arXiv 2610.42147, Tab. 3) baseline QSA-like na Qwen3.8-27B ma przy 512k TTFT 1.61×, a D-LSA tylko 1.03×. Do ~512k QSA wygrywa z LSA (szczegóły w 63d).

**Dla nas.** Nasza gęsta atencja jest już dobra: 74.5 t/s przy 199k na XTX vs ich dense 40.6 przy 255k na 4090. Kosztu długiego kontekstu to jednak nie usuwa: między 94k a 199k tracimy ~3.95 ms na token (`1/74.5 − 1/105.6`). QSA ogranicza atencję do 2048 tokenów plus skan indeksera.

Skala zysku `[SZACUNEK]`: na 4090 QSA traci 18.6% między 0 a 255K (140.9 → 114.7). U nas byłoby to ≈ **199k: 74.5 → 105–115 t/s (+40…55%)**, **94k: 105.6 → 120–126 (+15…20%)**, prefill ≥ 94k **+25…40%**.

Upstream ma już infrastrukturę QSA dla qwen4exp: fused QSA mask op [#30640](https://github.com/ggml-org/llama.cpp/pull/30640), selekcję k-pool bez kq_mask [#31243](https://github.com/ggml-org/llama.cpp/pull/31243). Kod 27B pochodzi jednak z forka opartego o v0.5.0 (`6209237` + patche V100), więc port do topki to praca ręczna. Kernel sparse czyta Q8_0; u nas trzeba go podpiąć pod kvq (q4_0) z listą bloków. Wymaga pobrania `qsa-indexers.safetensors` (~210 MB FP32), więc **potrzebna zgoda użytkownika**.

## 4. LithosAI: MI355X, 2100+ t/s/user ([blog, 2026-10-27](https://www.lithosai.com/blog/ultra-fast-inference-2100-tokens-per-second-amd-mi355x))

- **Liczby.** DeepSeek V4.1 Flash na 8× MI355X: krok 2.83 ms vs 6.47–9.53 ms w OSS. Kimi K3: 9.20 ms vs 16.07–23.42 ms. Krok rośnie z 2.84 ms (1K) do 3.27 ms (1M).
- **Metodologia.** „Every engine is credited the same speculative acceptance, 75% of speculated tokens”. Tokens/s = 6 tokenów / czas kroku (2116 × 2.83 ms = 5.99). **To nie jest zmierzona przepustowość end-to-end**, tylko czas kroku przeliczony przy założonej akceptacji. Porównanie czasów kroku między silnikami jest uczciwe (ta sama szerokość weryfikacji, „official formats”). Nagłówkowe t/s to konstrukt marketingowy. Silnik zamknięty, kodu brak.
- **Techniki.**
  1. Trwałe megakernele: link do OSDI'26, prawdopodobnie MPK/Mirage `[INFERENCE]`.
  2. „Doing in software what PDL does in hardware”: następny megakernel robi setup, gdy bieżący się kończy.
  3. Komunikacja wewnątrz kernela (TP8).
  4. Duży register file (512 KB/CU) do prefetchu wejść następnego zadania.
  5. „Recursive, self-improving kernel harness” (bez szczegółów).
- **Co przenosi się na RDNA3 (1 GPU, bez TP):**
  - (1) i (2) mieliśmy: 15a (MonoKernel, dataflow +12…28% `[SZACUNEK]` dla LFM) i 16a (PM4-PDL, realnie ≈ +3%, X1/X3 kill). Lekcja „jedna flaga pollowana przez cały grid jest wolniejsza od granicy” (`wiki/lekcje/lekcja-handoff-rdna3.md`) nadal obowiązuje.
  - (4) to dokładnie nasze „wagi do VGPR przed czekaniem” w PM4-replay (`wiki/kernele/pm4-replay.md`). RDNA3 ma 192 KB VGPR na SIMD pair, czyli mniej niż MI355X, ale ten sam mechanizm `[INFERENCE]`.
  - (3) nie dotyczy (1 GPU).
  - **Nic nowego do zrobienia.** Wzmacnia priorytet „dataflow-megakernel dla LFM” z 15a, jeśli kiedyś wrócimy.

## 5. llama.cpp release v0.9.0 — co to jest i co nowego

**Co to za tag.** Semver dla llama.cpp ogłoszono 2026-08-07 ([ggml#1579](https://github.com/ggml-org/ggml/discussions/1579)).
- Nightly to nadal `bNNNN`.
- Tagi `vX.Y.Z` powstają tylko wtedy, gdy wewnętrzna kopia ggml jest identyczna z wydanym ggml. Gwarantuje to zgodność z systemowym ggml (Debian, Homebrew).
- v0.9.0 = commit `cd959ba` = **nightly b12110**, ggml v0.29.0, 2026-11-04 ([release](https://github.com/ggml-org/llama.cpp/releases/tag/v0.9.0)). Binarki leżą przy nightly b12110.
- Kolejne tagi: v0.7.0 = b11669 (`620d222`, 15.10), v0.8.0 = `8642541` (28.10).
- Liczba commitów (`git rev-list --count`): b11856 → v0.8.0: 104; b11856 → v0.9.0: **254**; b11528 (baza topki) → v0.9.0: **582**; v0.8.0 → v0.9.0: 150.
- **Dla Enigmy:** warto przejść z pinu `bNNNN` na „tag vX.Y.Z + jego nightly”. Ten sam bajt-kod, ale wydania są nazwane i zgodne z ggml.

**Zmiany istotne dla szybkości** (sprawdzone `git merge-base --is-ancestor`; „≤b11856” = Enigma już ma, „topka nie” = po b11528):

| zmiana | backend | twierdzenie (PR) | Enigma (b11856) | topka (b11528) |
|---|---|---|---|---|
| CUDA: szybszy MMVQ dla low-bit [#30517](https://github.com/ggml-org/llama.cpp/pull/30517) | CUDA | kernel q2_K ×1.59, q3_K ×1.67 na 3090; q6_K ×1.06 | ma | nie (CUDA-topka2 też nie) |
| cap MMQ Stream-K [#30553](https://github.com/ggml-org/llama.cpp/pull/30553) | CUDA | TG przy P=6–8 (weryfikacja!) +4.2…4.5% na 5090 | ma | nie |
| chunked CUDA graphs [#30804](https://github.com/ggml-org/llama.cpp/pull/30804) | CUDA | TG +1–2% | ma | nie |
| GDN chunked (MMA) [#29353](https://github.com/ggml-org/llama.cpp/pull/29353) | CUDA (Ampere/Ada/Blackwell), HIP tylko RDNA3.5 i ≥ 2048 tok. (`gated-delta-net-mma.cu:393-417`) | pp dense 27B +3…6%, 35B-A3B +11…21% | ma | nie |
| rms_norm float4 [#29720](https://github.com/ggml-org/llama.cpp/pull/29720) | CUDA/HIP | MI100 ub1–8 +7…13% | ma | nie (mamy własne NORM_FAST) |
| Vulkan: kopia strided f16 KV na AMD [#27703](https://github.com/ggml-org/llama.cpp/pull/27703) | Vulkan AMD | wiersze KV Qwen3.8 (4×256 f16, 2048 B) angażowały 2 z 16 kanałów pamięci | ma | — |
| zapis stanu draftu w pliku slotu [#30574](https://github.com/ggml-org/llama.cpp/pull/30574) | wszystkie | **Qwen3.8 MTP: akceptacja po restore 37% → 49%** | ma | **nie** (topka zapisuje tylko `ctx_tgt` + checkpointy, `server-context.cpp:2960-2970`) |
| `--spec-draft-n-ubatch` [#30459](https://github.com/ggml-org/llama.cpp/pull/30459) | wszystkie | mniej VRAM draftu | ma | nie |
| **fuzja FFN gate/up+GLU w MMQ** [#29948](https://github.com/ggml-org/llama.cpp/pull/29948) | CUDA | Qwen3.8-27B pp16384 na GB10: Q4_K_M +7.1%, IQ4_XS +7.4%, Q6_K +4.6% | **nie** (v0.8.0) | nie |
| **fuzja MoE gate/up+GLU w MMQ** [#31188](https://github.com/ggml-org/llama.cpp/pull/31188) | CUDA (na RDNA3 wg RDNA-FAST −3…16%) | pp MoE +5.7…17.2% | **nie** (v0.9.0) | nie |
| **Vulkan: split-K dla małych N na RDNA3/4** [#30146](https://github.com/ggml-org/llama.cpp/pull/30146) | Vulkan (W7800 gfx1100) | ub 13–32 +12…20%; Qwen3.8-27B MTP draft-max 8: **+13.0%**, 16: +13.9%, 3: szum | **nie** | — |
| Vulkan rms_norm przez subgroup [#29882](https://github.com/ggml-org/llama.cpp/pull/29882) | Vulkan | +~1% pp | nie | — |
| zapis/odtworzenie ukrytego stanu MTP w checkpointach [#30141](https://github.com/ggml-org/llama.cpp/pull/30141) | wszystkie | poprawność draftu po restore | nie | ma odpowiednik (boundary stash, `speculative.cpp:940-975`) |
| restore spec-checkpointu dla draftów > n_rs_seq [#31350](https://github.com/ggml-org/llama.cpp/pull/31350); refuse rollbacks past snapshots [#31368](https://github.com/ggml-org/llama.cpp/pull/31368) | wszystkie | poprawność hybryd | nie | do przeglądu względem naszego LAG/bank |
| stałe rotacji KV na GPU [#31073](https://github.com/ggml-org/llama.cpp/pull/31073) | wszystkie (KV z rotacją Hadamarda) | tg128 +8.7% (3090, PCIe 2.0) | nie | nasz FWHT jest złożony w kernele (`b1f8c19ac`, `3a1279f95`) |
| `flash_attn_ext_rows` [#29510](https://github.com/ggml-org/llama.cpp/pull/29510) | CUDA | multi-seq unified KV: PP 2982 → 8626 t/s | nie | — (dla multi-slot) |
| batched reads do mapped host [#31391](https://github.com/ggml-org/llama.cpp/pull/31391) | CUDA | serwer wielostrumieniowy +30.6%, TTFT −61% | nie | — |

**Pułapka wersjonowania** (nie dotyczy szybkości): v0.9.0 dodaje typ FP8 E4M3 (`LLAMA_FTYPE_MOSTLY_F8_E4M3`). Katalog Enigmy nie powinien proponować takich GGUF bez buildu ≥ v0.9.0 `[INFERENCE]`.

## 6. vLLM v0.33.0: części ROCm

Tag `v0.33.0` = `4ba787e` (2026-11-01). Release na GitHubie nie ma jeszcze treści, notatki są w [v0.33.0rc3](https://github.com/vllm-project/vllm/releases/tag/v0.33.0rc3) (2026-11-02).
- **ROCm 10.0 domyślnie** w obrazie i kołach, ROCm 7.2 jako `-rocm72` (#58761). Koła ROCm budują się 4–7× szybciej (#63105).
- **MonoKernel, delta względem 15a:**
  - port DSv4.1 na gfx942 [#60731](https://github.com/vllm-project/vllm/pull/60731): MI325X TP4 + DSpark 5; AgentX conc 1, P50 216.85 → 503.53 t/s/user (2.32×); warstwa 320 → 115 µs; 32 → 2 kernele na warstwę; GSM8K bez istotnej różnicy (p 0.49); kernele kwantyzują aktywacje do **MXFP8** (gfx942 trzymał bf16);
  - całe warstwy MI355X (#61082), MiniMax-M3 −16.6% TPOT (#62712, #62994);
  - flaga `--monokernel` zastępuje `VLLM_ROCM_MONO_DECODE`;
  - dla RDNA nic.
- **`ROCM_OCTAVE`** [#59774](https://github.com/vllm-project/vllm/pull/59774) (RFC [#59773](https://github.com/vllm-project/vllm/issues/59773)): natywny KV 3/4-bit dla gfx1100 i gfx942.

  | dtype | K | V | B/slot (head 256) |
  |---|---|---|---|
  | `k3v3_compact` | cała głowica 3-bit | 3-bit | 196 |
  | `k3v3` | 4 bloki po 64, blok RoPE 4-bit | 3-bit | 216 |
  | `k3v4` | jak wyżej | 4-bit | 248 |

  - Na 4× XTX z Qwen3.8-27B: 4.6× więcej tokenów KV niż fp16. NLL przy 380k: +0.00086…0.0015 nata vs fp16. TurboQuant k3v4: +0.00155.
  - Atencja per warstwa przy 380k (shard TP4): decode 563–614 µs (fp16 2370 µs). Weryfikacja MTP 4 tokenów 0.58–0.62 ms (fp16 48.8 ms!).
  - Kernel RDNA3: QK w prefillu jako int8 WMMA ze skalą per blok 64; w decode fp16 WMMA ze stałym offsetem usuwanym w softmaksie; PV fp16 WMMA ze skalą V w prawdopodobieństwach.
  - „Least-squares scale was clearly worse… NLL 2–3× higher”: wyuczona lekcja przy wyborze skali.
- **GDN MTP fused decode** na ROCm [#61855](https://github.com/vllm-project/vllm/pull/61855): MI350X, Qwen3.5-35B-A3B MTP k=3: 2.39 → 2.08 ms/tok (−13%), głównie przez usunięcie kopii (1.56 → 0.31 ms na krok). Potwierdza nasz kierunek (GDN bank, fuzje prologu), nie wnosi nic nowego.
- **TRITON_ATTN na RDNA3 +18%** przez przywrócenie **32-bitowego adresowania buforów** ([#60084](https://github.com/vllm-project/vllm/pull/60084), W7900). Lekcja dla nas: kvq, FA MMA i MMQ w topce **nie używają** buffer-resource loads (0 wystąpień w `fattn-kvq.cu`, `fattn-mma-f16.cuh`, `mmq.cuh`; MMVQ używa, `mmvq.cu`). Mikro-eksperyment E11.
- **Quantized draft lm_head** [#59973](https://github.com/vllm-project/vllm/pull/59973): +18% decode przy conc 1 na GB10. Mamy to od 343c2fbbb (głowica IQ4_XS).
- **FLy** [#53987](https://github.com/vllm-project/vllm/pull/53987): stratna weryfikacja. Izolowane odrzucenie przyjmowane, gdy entropia top-3 celu ≥ próg i kolejne W draftów przechodzą. 1.055–1.31× na MI355X, retencja jakości ≥ 96.3%. **Zmienia rozkład.** Sprzeczne z naszą linią „bit-exact / ten sam rozkład” (raport 12, 24p). Tylko jako przełącznik produktowy, za zgodą.

## 7. cheaptokens: KV q5_1 + FA → atencja na CPU. Audyt Enigmy i topki

**Twierdzenie** ([blog, 2026-10-30](https://cheaptokens.dev/en/blog/llama-cpp-slow-prompt-quantized-kv-cache/)): prefill 38 vs 1348 t/s (RTX 4080, 27B). Źródłem jest [issue #28455](https://github.com/ggml-org/llama.cpp/issues/28455) z 5.09, build **10791**, zamknięte jako „known issue”.

**Stan dziś.**
- [#28079](https://github.com/ggml-org/llama.cpp/pull/28079) (9.09) zastąpił `FA_ALL_QUANTS` listą `GGML_CUDA_FA_QUANTS` (domyślnie `q4_0-q4_0;q8_0-q8_0;f16-f16;bf16-bf16`, `ggml/CMakeLists.txt:208` w b11856).
- `ggml_cuda_fattn_kv_type_supported` przyjmuje Q4_0/Q4_1/Q5_0/Q5_1/Q8_0/F16/BF16 (`fattn.cu` b11856:524-538). Brak instancji vec kończy się **konwersją K/V do f16 na GPU** z ostrzeżeniem „(slow)” (`fattn.cu` b11856:495-511). To samo jest w b11528, czyli w topce (`~/wt/topka/ggml/src/ggml-cuda/fattn.cu:506`).
- Wniosek: na CUDA/HIP q5_1 nie spada już na CPU. Nadal jest jednak wolne, bo kopia f16 całego KV idzie przy każdym wywołaniu. Blog opisuje stan sprzed 2 miesięcy.

**Enigma** (`~/KERNEL/app/engine`):
- `KvType = 'q4_0' | 'q8_0' | 'f16'` (`src/server/catalog/data.ts:5`);
- `plan()` wybiera tylko z tych trzech (`catalog/index.ts:150-161`);
- serwer zawsze dostaje `-fa on -ctk X -ctv X` z tym samym X (`src/server/engine.ts:477-478`), a profil topki `-ctkd {kv} -ctvd {kv}` (`data/engines.json:300-303`).

| backend (b11856 / topka) | FA dla q4_0/q8_0/f16, K = V | ryzyko |
|---|---|---|
| CUDA | instancje domyślne (CMake:208) | brak. Head dim spoza {40,…,256} bez gqa_opt (np. 192/320/512/576 z maską bez paddingu) → `BEST_FATTN_KERNEL_NONE` → **CPU** (`fattn.cu` b11856:574-629) |
| HIP (upstream, topka) | ten sam kod + kvq (q4_0/q8_0 na RDNA3) | brak |
| Vulkan | `fa_kv_ok`: F32/F16/BF16/Q8_0/Q5_1/Q5_0/Q4_1/Q4_0/IQ4_NL, ale **wymaga `subgroup_shuffle && subgroup_vote` albo coopmat2** (`ggml-vulkan.cpp` b11856:15613-15659) | **tak**: urządzenie bez tych rozszerzeń → FA na CPU |
| Metal | K = V, q4_0/q8_0/f16/q4_1/q5_0/q5_1, wymaga `has_simdgroup_mm` (`ggml-metal-device.m` b11856:1727-1773) | brak na M1+ |
| CPU | wszystko | — |

**Dlaczego nikt tego nie zauważy.** Probe FA (`resolve_fused_ops`) działa tylko przy `-fa auto` (`llama-context.cpp` b11856:659-662). Przy kwantyzowanym V `auto` zamienia się w `ENABLED` **przed** probe'em (`:4079-4088`), więc **przy q4_0/q8_0 nie ma żadnego ostrzeżenia**.

Twardy sygnał istnieje: log `sched_reserve: graph: nodes = …, splits = N`. W pełnym offloadzie topki N = 2 (`~/qwen-opt/queue/logs`). FA na CPU w 16 warstwach dałoby ~34 `[INFERENCE]`.

**Odpowiedź na pytanie z zadania.** Enigma i topka są bezpieczne dla par, które dziś wybierają. Katalog nie może wybrać q5_1 ani par mieszanych, bo typ to unia 3 wartości i K = V. Może jednak trafić na **(a)** Vulkan bez subgroup ops albo **(b)** model z niewspieranym head dim lub GQA. Wtedy dostaje cichy CPU-fallback 10–35× wolniejszego prefillu. Rozwiązanie w E10.

## 8. Co z tego dla nas (ranking: oczekiwany zysk / nakład)

| # | eksperyment | zysk `[SZACUNEK]` | nakład | ryzyko |
|---|---|---|---|---|
| E4 | Cap occupancy FA na 64 KB LDS (ROCm 10 runtime) | TTFT 32k: −0…5%; LFM prefill możliwe więcej | 1 h kodu + 30 min GPU | niskie |
| E8 | Cherry-pick #30574 (stan draftu w pliku slotu) | akceptacja po wznowieniu z SSD: 37 → 49% (upstream) | 0.5 dnia | niskie |
| E10 | Enigma: strażnik `splits` + bramka Vulkan | chroni przed spadkiem prefillu ×10–35 | 0.5 dnia | brak |
| E9 | Enigma: pin b11856 → b12110 (v0.9.0) | CUDA pp Qwen 27B +5…7%; MoE pp +6…17%; Vulkan RDNA3 MTP z dużym draftem do +13% | 1 dzień + e2e (61) | niskie |
| **E1** | **QSA dla Qwen3.8-27B w topce** | decode 199k **+40…55%**, 94k +15…20%; prefill ≥ 94k +25…40% | 2–3 tygodnie + zgoda na indeksery (~210 MB) | średnio-wysokie (jakość) |
| E6 | MTP lean reserve + `-ub 1024/2048` dla Qwena | TTFT +3…8%; albo +~0.7 GB na ctx | 1 dzień | niskie |
| E7 | kvq: kafel 32 kolumn dla weryfikacji 3–5 tok. | decode ≥ 94k +2…4% | 2–3 dni | niskie |
| E2 | KV 3-bit à la Octave w kvq | **262k na 24 GB** (−1.1 GiB); decode 199k +3…7% | 1–2 tygodnie | średnie (jakość) |
| E5 | Dynamiczny słownik draftu (stałe + top celu) | +1…3% t/s czat | sym CPU 0.5 dnia, potem 2–3 dni | niskie |
| E3 | f16 WMMA GEMM w prefillu zamiast MMQ | pp: −5…+10% (niepewne) | microbench 1 dzień, potem tydzień | średnie |
| E11 | buffer-resource loads w kvq / FA MMA | +0…3% atencji | 1–2 dni | niskie |

### Projekty eksperymentów (baseline → teraz → przyrost %)

**E4: cap occupancy FA (RDNA-FAST `TAG_FATTN_OCC_LDS64`).**
- Krok 0 (GPU, przez kolejkę): `hipGetDeviceProperties` na naszym runtime. Jeśli `maxSharedMemoryPerMultiProcessor = 131072`, przejdź dalej. Jeśli 65536, eksperyment odpada (kill).
- Łatka: w `launch_fattn` (`fattn-common.cuh:1147`) ograniczyć `max_blocks_per_sm` do `sharedMemPerBlock / nbytes_shared`, tak jak w [b462181](https://github.com/serrynaimo/RDNA-FAST/commit/b462181) (`fattn-common.cuh:1569-1571` u nich).
- Pomiar ABBA, `GGML_HIP_PM4=0`:

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | pp512@d32768 Qwen | wartość z 24v | ? | cel ≥ +3% |
  | TTFT 29.5k | 945 t/s | ? | ? |
  | LFM pp4096 (ub 2048) | 7148 | ? | ? |

- md5 greedy (c4708318/6f14e814/894e56e4) musi zostać bez zmian; to zmiana tylko launchu.
- Kill: < +1% na pp512@d32k.

**E8: stan draftu w pliku slotu (#30574).**
- Scenariusz: rozmowa 30k → `slot save` → erase → `restore` → następna tura 400 tok., T=0.

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | tok/krok | ? | ? | ? |
  | t/s tury po restore | ? | ? | cel: równe slotowi nigdy niezapisanemu (upstream: 37 → 49%) |

- md5 tekstu bez zmian. Dotyczy tylko SSD/`--slot-save-path`; RAM prompt cache już zapisuje draft (`server-context.cpp:318`).

**E10: Enigma, strażnik CPU-fallbacku.**
- Po starcie serwera parsować `graph: nodes = …, splits = N`. Jeśli `-ngl 999` i N > 3: log `fa_cpu_fallback`, automatyczny restart z `-fa off -ctk f16 -ctv f16` (Vulkan) albo zmiana backendu.
- Katalog: dla `backend=vulkan` + KV q4_0/q8_0 sprawdzić w skanie sprzętu (vulkaninfo) `subgroup shuffle/vote`.
- Test: CPU-only build z `-fa on -ctk q4_0` i wymuszonym brakiem wsparcia (np. `GGML_VK_DISABLE_*`, jeśli istnieje) → oczekiwane N > 3.

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | prefill w przypadku awaryjnym | ~38 t/s (scenariusz bloga) | ~1300 t/s | ×35 |

**E9: Enigma b11856 → b12110.**
- Powtórka e2e z 61 na 3090 i 5060 Ti (Vast) plus Vulkan na XTX.

  | metryka | baseline (b11856) | teraz | przyrost |
  |---|---|---|---|
  | pp4096 Qwen UD-Q4_K_XL 3090 | z 61 | ? | oczekiwane +5…7% |
  | LFM pp | z 61 | ? | oczekiwane +6…17% |
  | Vulkan XTX MTP n=8 decode | ? | ? | do +13% |

- Bramki: md5 greedy, testy katalogu, `catalog.measured.json` (fit VRAM może się zmienić przez nowe bufory).

**E1: QSA (najwiekszy zysk).**
- Kroki:
  0. CPU: przeczytać arXiv 2608.30320 §QSA oraz `qwen35.cpp` w forku; spisać tensory indeksera (80 tensorów, shape, `indexer_head_size`, `indexer_n_head`).
  1. Po zgodzie: pobrać tylko `qsa-indexers.safetensors` @ `d61281f4626729e4cf138476a704c7fedc08f891` (~210 MB) i doszczepić do **naszego** UD-Q4_K_XL przez [`gguf_qsa_graft.py`](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp/blob/fe08b167477a8eb651dc71ded753542d72c46cd0/deploy/qsa27b-24gb/gguf_qsa_graft.py). Wagi zostają bajt w bajt.
  2. Port grafu do topki: indekser, top-k bloków (K=2048/4), sparse FA. Kernel: kvq z listą bloków, bo czyta q4_0 i MTP verify dzieli kafle.
  3. Bramka jakości przed pomiarami: KLD dense vs QSA przy 32k/64k/128k na naszym korpusie PL+kod (to, czego autorzy nie zrobili), needle 24 faktów, two-hop. Kill: KLD p99 > 2× kontrola szumu albo two-hop gorsze o > 1/16.
- Pomiar ABBA long_ctx_bench (MTP4 + W16, T=0) i spec_sweep:

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | decode 1.7k | 136.5 t/s | ~136 | 0 (QSA nieaktywne < 2048) |
  | decode 94k | 105.6 t/s | 120–126 | +15…20% |
  | decode 199k | 74.5 t/s | 105–115 | +40…55% |
  | TTFT 94k | 123 s | 85–95 s | −25…30% |

- VRAM: +~0.3 GB (indeksery w F32 lub F16) + surowe klucze indeksera (ring 8192 jak u nich, −2 GiB vs pełne).

**E6: MTP lean reserve + większy ub dla Qwena.**
- Port `TAG_MTP_LEAN_RESERVE` ([llama-context.cpp:228-244](https://github.com/serrynaimo/RDNA-FAST/blob/4426ca35c4d2a1b57b37e661152f52972a3777b5/src/llama-context.cpp)).

  | metryka | baseline (ub 512, ctx 204800) | teraz (ub 1024 i 2048) | przyrost |
  |---|---|---|---|
  | VRAM po załadowaniu | z logu | ? | cel −0.7 GB |
  | TTFT 6.6k | 985 t/s | ? | cel ≥ +3% |
  | TTFT 29.5k | 945 t/s | ? | ? |
  | pp4096 | 1123 t/s | ? | ? |

- KLD ub-vs-ub jak w 16f (każdy podział ubatcha zmienia numerykę). Kill: < +2% TTFT.

**E7: kvq 32 kolumny.**
- `fattn_kvq_ncols` jako parametr szablonu {16, 32}; 32 dla tokenów×GQA ∈ (16, 32]. Weryfikacja n=4: 5×6 = 30 kolumn, czyli **jeden** odczyt KV zamiast dwóch.

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | test-backend-ops perf FA hsk=256, n=5 @ 94k/199k | ? | ? | ? |
  | long_ctx_bench 94k | 105.6 t/s | ? | cel +2…4% |
  | long_ctx_bench 199k | 74.5 t/s | ? | cel +2…4% |

- md5 może się zmienić (kolejność redukcji). Wtedy bramka KLD vs kvq16.

**E2: 3-bit KV (Octave-like) w kvq.**
- Format k3v3 (216 B/slot): rotacja WHT ze znakami (mamy FWHT, `3a1279f95`), Lloyd-Max N(0,1) 8 poziomów, skala `x·x̂ = |x|²`, blok RoPE 4-bit.

  | metryka | baseline (q4_0) | teraz (k3v3) | przyrost |
  |---|---|---|---|
  | KV przy 262144 | 4.5 GiB | 3.375 GiB | −25% |
  | max ctx w produkcyjnym fit | 204800 | 262144? | +28% |
  | decode 199k | 74.5 t/s | ? | cel +3…7% |

- Bramka KLD vs q4_0 przy 32k/128k (Octave: +0.00125 nata vs fp16 przy 380k, na W4A16). Kill: KLD gorsze od q4_0 o > 1.5× przy tej samej długości.

**E5: dynamiczny słownik draftu.**
- Najpierw CPU, na logach z 24b (`~/qwen-opt/re/oov_draft_analysis.md`, dane OOV): policzyć pokrycie następnego tokenu dla {ID < 12k} ∪ {top-12k celu} vs statyczne 64k.
- Jeśli pokrycie jest ≥ statycznemu: E2E. Głowica 24k wierszy zamiast 64k, czyli −62% bajtów głowicy na token draftu.

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | spec_sweep T=1 | 114.8 | ? | cel +1…3% |
  | proza E0 | 78.93 | ? | ? |

- Ograniczenie: dynamiczna część wymaga topu pełnego wiersza logitów celu. Z `LLAMA_GPU_VERIFY=1` kopiujemy tylko top-128. Wariant tani: 24k stałych + top-128 z GPU verify.

**E3: f16 WMMA GEMM w prefillu.**
- Krok 1 (1 dzień, GPU 30 min): test-backend-ops perf MUL_MAT na naszych kształtach (5120×17408, 17408×5120, 5120×6144, Q4_K/Q5_K/Q6_K/IQ4_XS, n = 512/1024/2048). Porównać build RDNA-FAST (`ROCMFPX_WMMA_GEMM=1/0`) z topką.
- Nasze MMQ robi już ~70 TFLOPS `[SZACUNEK: 209 TFLOP na pp4096 / (3.67 s × 0.813)]`, a ich ścieżka int8 tylko 39–48 na XT. Zysk istnieje tylko wtedy, gdy unpack + GEMM > 70 TFLOPS na naszych kształtach.

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | pp4096 | 1123 t/s | ? | ? |

- Kill: < +3% na kernelu.

**E11: buffer-resource loads w kvq / FA MMA** (wniosek z vLLM #60084).

  | metryka | baseline | teraz | przyrost |
  |---|---|---|---|
  | test-backend-ops perf FA hsk=256, n=1/5 @ 94k | ? | ? | kill < +2% kernel |

### Na migrację na ROCm 10.1 (checklista z RDNA-FAST, uzupełnia 13-rocm-10.1)
- `__align__(16)` na `__shared__` w MMQ, normach, softmaksie i top-k ([aecf11d](https://github.com/serrynaimo/RDNA-FAST/commit/aecf11d)).
- Jawne szerokie store'y w unpackach ([f84c0bc](https://github.com/serrynaimo/RDNA-FAST/commit/f84c0bc)).
- Occupancy 1 dla kafli J32 4-bitowych i wierszy fallback ([5c90b10](https://github.com/serrynaimo/RDNA-FAST/commit/5c90b10), [d1d2c74](https://github.com/serrynaimo/RDNA-FAST/commit/d1d2c74)). U nas sprawdzić IQ4_XS (głowica MTP) i Q8_0 (KV q8_0 LFM).
- Cap LDS w occupancy FA (E4).
- Ich bilans: 10.1 z poprawkami = +3.1% vs 7.2 na kształtach promptowych. Bez poprawek IQ4_XS prompty były 1–3% wolniejsze.

### Odrzucone lub do obserwacji
- FLy: stratna weryfikacja, tylko za zgodą produktu.
- LithosAI: nic nowego, closed.
- MonoKernel: brak ścieżki RDNA; 15a w mocy.
- ROCmFPX FP4/FP6: KLD 0.026 vs IQ4_XS 0.021 przy +2–5% promptów. Nie dla nas.
- GDN chunked na RDNA3: ≤ 3% pp, dopiero po E3 i E6.
- `ngram` rampa W48: nasze W16 już szybsze.

## 9. Źródła (do ZRODLA)

| źródło | wersja / commit / data | co studiowane |
|---|---|---|
| [serrynaimo/RDNA-FAST](https://github.com/serrynaimo/RDNA-FAST) | HEAD `4426ca35c4d2` (2026-11-05), 50 ostatnich commitów (od `c0abed9`, 2026-10-29) | README całe; `fattn-tile.cuh`, `fattn.cu`, `gated_delta_net.cu`, `gdn-conv.cu`, `wmma-gemm.cu`, `mmvf.cu`, `llama-context.cpp`, `llama-memory-recurrent.cpp`, `rocmfpx-draft-{vocab,select}`; commity clang 24 / ROCm 10.1 |
| [rocm_wmma_gemm (adelj88)](https://github.com/adelj88/rocm_wmma_gemm) | vendored w RDNA-FAST | tylko jako zależność (README RDNA-FAST) |
| tweet [pentacoxian_dev/2118071912882712590](https://x.com/pentacoxian_dev/status/2118071912882712590) + wątek (…903789428927, …906985443479, …909883736384) | 2026-11-04 20:04 UTC | treść przez api.fxtwitter.com; 4 obrazy |
| [pentaCoxian/Qwen-QSA-llama.cpp](https://github.com/pentaCoxian/Qwen-QSA-llama.cpp) | HEAD `fe08b167477a` (2026-11-05); baza Qwen-V100-llama.cpp `6209237` (llama.cpp v0.5.0) | README, `serve.sh`, `qsa27b/RUNTIME.md`, `qwen35.cpp` (QSA), `qsa-attn.cu` |
| [HF pentacoxian-dev/Qwen3.8-27B-QSA-GSQ-RCO-GGUF](https://huggingface.co/pentacoxian-dev/Qwen3.8-27B-QSA-GSQ-RCO-GGUF), [HF higa2515/Qwen3.8-27B-QSA-BF16](https://huggingface.co/higa2515/Qwen3.8-27B-QSA-BF16) | stan 2026-11-05 (indeksery @ `d61281f4…`) | model cards (bez pobierania wag) |
| [arXiv 2608.30320](https://arxiv.org/abs/2608.30320) (QSA, architektura Qwen3.8-Next) | — | tylko odwołanie z model card; **nie czytane**, krok 0 w E1 |
| [LithosAI blog](https://www.lithosai.com/blog/ultra-fast-inference-2100-tokens-per-second-amd-mi355x) | 2026-10-27 | cały |
| [llama.cpp v0.9.0](https://github.com/ggml-org/llama.cpp/releases/tag/v0.9.0) | `cd959ba` = b12110, 2026-11-04; v0.8.0 `8642541`; v0.7.0 `620d222` = b11669; b11856 `3642238`; b11528 `e60eff9` | release notes; `git log` b11528..v0.9.0 dla ggml-cuda/ggml-vulkan/spec/server; PR #29353, #29510, #29720, #29882, #29948, #30141, #30146, #30459, #30517, #30553, #30574, #30804, #31073, #31188, #31350, #31391, #27703, #28079 |
| [ggml discussion #1579](https://github.com/ggml-org/ggml/discussions/1579) | 2026-08-07 | zasady wersjonowania |
| [vLLM v0.33.0](https://github.com/vllm-project/vllm/releases/tag/v0.33.0) | tag `4ba787e` (2026-11-01); notatki z v0.33.0rc3 (2026-11-02) | sekcje ROCm i spec; PR #59774 (+ RFC #59773), #60731, #61855, #60084, #59973, #53987 |
| [cheaptokens: q5_1 KV](https://cheaptokens.dev/en/blog/llama-cpp-slow-prompt-quantized-kv-cache/) | 2026-10-30 (issue #28455, build 10791) | cały + weryfikacja w kodzie b11856 i topki |
| Enigma `~/KERNEL/app/engine` | stan 2026-11-05 | `catalog/{data,index,memory}.ts`, `server/engine.ts`, `data/engines.json` |
