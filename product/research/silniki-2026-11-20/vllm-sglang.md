# vLLM i SGLang: co z nich brać do Turbo (hybryda GDN, AMD, batch 1)

Data: 2026-11-20. Autor: agent VllmSglang. Tylko odczyt kodu (CPU) i źródła w sieci, bez pomiarów na GPU.

## 1. Co to jest

- **vLLM** — serwer inferencji w Pythonie (PyTorch + własne kernele C++/HIP/CUDA + Triton). Klon `~/research/engines/vllm`, commit `6c6e159 2026-11-20`.
- **SGLang** — konkurencyjny serwer (radix cache, nakładanie CPU/GPU, dużo wariantów spekulacji). Klon `~/research/engines/sglang`, commit `dc8f1c3 2026-11-20`.

Oba celują w duże partie na serwerach (H100/H200/B200, MI300X/MI355X). Batch 1 na karcie konsumenckiej AMD to dla nich sprawa poboczna, ale na RDNA3/3.5 w ostatnich miesiącach pojawiło się dużo kodu (głównie gfx1151 / Strix Halo i gfx1100). Ta notatka opisuje tylko to, czego nie ma w `03-silniki-i-stack.md` i `60d-serving-kernels-cache.md`.

## 2. Architektura (w skrócie, z naciskiem na hybrydę Qwen3.5/3.8)

1. **Harmonogram i grafy.** vLLM: graf „full” dla jednolitego dekodu, kluczem jest (liczba zapytań, długość zapytania). Weryfikacja spekulacji (1+k tokenów na zapytanie) też jest „jednolitym dekodem”, więc dostaje własny graf (`docs/design/cuda_graphs.md:90`, `:99-101`). SGLang: grafy per faza (`decode` full, `prefill` „breakable”). GDN w prefillu jest łapany do grafu przez statyczne tabele kubełków (`python/sglang/srt/layers/attention/linear/gdn_prefill_graph.py:1-20`: bez tego ~10 uruchomień Tritona i ~1 ms czasu hosta **na warstwę GDN**). **Na gfx1100 SGLang działa bez grafów**: przechwycenie grafu HIP się wiesza ([AMD-AIM/sglang-radeon](https://github.com/AMD-AIM/sglang-radeon), sglang#30245).
2. **Skąd kernele GDN.** vLLM ma kopię FLA (Triton) w `vllm/third_party/flash_linear_attention/ops/` i wybiera backend prefillu GDN per architektura (`vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py:195-356`): MI300/MI355 → AITER FlyDSL, **gfx1151 → jeden kernel HIP `rdna35_gdn_chunked`**, Hopper → FlashInfer/CuTe-DSL, reszta (w tym gfx1100) → Triton FLA. Dekod GDN: Triton `fused_recurrent` albo fused kernel AITER (gfx950) albo CUDA `csrc/gdn/fused_gdn_decode_kernel.cu` (conv już zrobiony, L2-norm + bramki + rekurencja + gated RMSNorm w jednym kernelu, do 9 tokenów MTP, `:95`, `:159-197`). SGLang: `--linear-attn-{decode,prefill,verify}-backend` = triton / cutedsl / flashinfer / aiter (`python/sglang/srt/arg_groups/fields/exec_.py:660-690`).
3. **Kwantyzacja na RDNA3.** vLLM nie ma już GGUF w drzewie (brak `csrc/quantization/gguf`, brak `gguf` w `vllm/model_executor/layers/quantization/`). Na gfx1100 jedyna szybka ścieżka to W4A16 GPTQ/AutoRound: `csrc/rocm/q_gemm_rdna3.cu` (skalarny dekod, dot2) + `csrc/rocm/q_gemm_rdna3_wmma.cu` (WMMA od M ≥ 12). Dla gfx115x jest `skinny_gemms_int4_n1..n8.cu` (GEMV na 1–8 kolumn). W SGLang na gfx1151: W4A16 w Gluon dla M ≤ 16 (`python/sglang/kernels/ops/quantization/w4a16_small_m_gfx1151.py:1-20`). FP8 na gfx11 jest emulowane i wolne (vllm#56992, niżej).
4. **KV i atencja na RDNA.** vLLM na gfx1100 preferuje `TRITON_ATTN` (`vllm/platforms/rocm.py:735-750`). Nowy backend **Octave KV** (3–4 bity, HIP, WMMA na gfx1100) jest zrobiony dokładnie pod kształt atencji Qwen3.5/3.8 (head 256, 64 wymiary rotacji) i traktuje weryfikację MTP jako przypadek podstawowy (`docs/design/rocm_octave.md:20-35`, `:108-115`). Jest stratny, więc dla nas tylko jako opcja dla długiego kontekstu. Pomiary szybkości w dokumencie to wciąż „TBD” (`:177-181`).
5. **Stan rekurencji przy spekulacji.** vLLM i domyślny SGLang trzymają **osobny slot stanu na każdy token weryfikacji**: kernel czyta stan ze slotu `num_accepted-1` z poprzedniego kroku i zapisuje stan po każdym tokenie (`vllm/third_party/flash_linear_attention/ops/fused_recurrent.py:104-117`, `:150-160`; `csrc/gdn/fused_gdn_decode_kernel.cu:194-197`). Cofnięcie = wybór slotu, bez powtórki. Koszt: zapis pełnego stanu (~150 MB dla 27B) na każdy token weryfikacji. Alokator rezerwuje `1 + num_speculative_blocks` slotów na zapytanie (`vllm/v1/core/single_type_kv_cache_manager.py:1892-1894`). SGLang ma **weryfikację drzewa dla GDN**: każdy węzeł ładuje stan rodzica z bufora stanów pośrednich (`python/sglang/kernels/ops/attention/linear/fused_sigmoid_gating_recurrent.py:343-372`).
6. **ReplaySSM (obie gałęzie).** Zamiast pisać stan co krok trzymają pierścień ostatnich L wejść (d, k, g) i punkt kontrolny S0. Stan zapisują co L kroków, a cofnięcie to przesunięcie wskaźnika (`python/sglang/kernels/ops/attention/linear/gdn_replayssm_spec_decode.py:1-37`, `fused_recurrent_linear_replayssm.py:14-21`; vLLM `docs/features/automatic_prefix_caching.md:33-37`). „Fold” przy zatwierdzeniu jest **bitowym klonem** zwykłej rekurencji (`gdn_replayssm_spec_fold.py:6-9`, `gdn_replayssm_spec_decode.py:543-556`). To ten sam pomysł, co nasza taśma w `accept()`.
7. **Prefix cache dla hybrydy.** vLLM: stan GDN trzymany tylko na granicach bloków (blok atencji jest wymuszony na 1568 tokenów, żeby strona KV ≥ strona stanu, vllm#56992). Do tego punkty kontrolne w środku prefillu w miejscach wyrównanych do kawałka kernela (`vllm/model_executor/layers/mamba/checkpoint.py:21-60`, `vllm/v1/kv_cache_interface.py:603-624`) i opcjonalnie punkt kontrolny w miejscu rozwidlenia wspólnego prefiksu (`--enable-mamba-shared-prefix-checkpoint`, `docs/features/automatic_prefix_caching.md:16-31`). SGLang: jeden radix tree dla Full/SWA/Mamba. Stan GDN jest w węźle (copy-on-write przy trafieniu), przy dopasowaniu zapamiętuje `mamba_branching_seqlen`, w dekodzie co `mamba_track_interval = 256` tokenów (`exec_.py:650-653`) i opcjonalnie trzyma stany w int8 (`mem_cache/mamba_checkpoint_pool.py:15-40`, stratne).
8. **Spekulacja.** vLLM: ngram, ngram_gpu, suffix, draft_model, eagle/eagle3, MTP (wiele rodzin), DFlash, DSpark, „dfly”, plus próbkowanie odrzucające „standard/synthetic/block/fly” (`vllm/config/speculative.py:106-121`). „fly” jest stratne (odracza odrzucenia przy dużej entropii, `vllm/v1/worker/gpu/spec_decode/fly.py:1-7`). SGLang: EAGLE/MTP (v2 z nakładaniem), DFlash/DFlash2, DSpark, ngram w C++, adaptacyjna liczba kroków (`python/sglang/srt/speculative/adaptive_spec_params.py:17-23`, `:145-151`).
9. **AMD consumer.** W głównych drzewach gfx1100 to wciąż ścieżka drugiej kategorii: vLLM ma kernele W4A16 i Octave dla gfx1100, ale chunked GDN i int4 skinny GEMV tylko dla gfx115x. SGLang oficjalnie nie wspiera RDNA3 ([sglang-radeon](https://github.com/AMD-AIM/sglang-radeon), [sglang#46900](https://github.com/sgl-project/sglang/issues/46900)); działa tylko przez fork albo wtyczkę.

## 3. Techniki z liczbami

### 3.1 GDN — prefill jednym kernelem HIP (vLLM, RDNA3.5)
- `csrc/rocm/rdna35_gdn_chunked.cu` (637 linii) zastępuje cumsum + transformację WY + rekurencję + wyjście **jednym uruchomieniem** (`vllm/model_executor/layers/mamba/ops/hip_gdn_chunk.py:3-7`).
- Algorytm (`rdna35_gdn_chunked.cu:7-35`): kawałki po 32 tokeny. W kawałku liczy `A = β·KKᵀ·exp(Δg)`, `Tinv = (I+A)⁻¹`, potem `v_new = Tinv·(Vβ − Kβe^g·S)` w miejscu, w jednym buforze LDS. U i W nigdy nie są materializowane. Przy kawałku 64 samo U, W i qk zajęłyby 80 KB LDS, więc kawałek ma 32 tokeny (`:29-31`).
- Jeden blok 1024 wątków na (głowa, sekwencja), stan w rejestrach (`:9-11`, `:612-613`). Redukcja 16 linii przez DPP `row_shl` bez LDS (`:82-104`). Zanik liczony od razu jako `v_exp_f32` w podstawie 2 (`:107-116`).
- Strojenie zajętości: gfx1151 ma 1536 VGPR/SIMD i mieści 2 bloki na WGP. Na częściach z 1024 VGPR żądanie 8 fal daje 100 VGPR bez spilla (`:167-180`). Tryb CU zamiast WGP daje ~10%, gdy bloków jest więcej niż WGP; poniżej tej liczby kosztuje ~¼ czasu operacji (`:616-621`).
- Ograniczenia: head_dim = 128 (u nas GDN ma 128), HV % HK == 0 (u nas 48/16), q/k/v w bf16/f16, stan f32 (`hip_gdn_chunk.py:35-55`). W `auto` włączony tylko na gfx1151, na gfx1100 jawnie zablokowany (`:16-32`, `qwen_gdn_linear_attn.py:296-314`).
- Nie znalazłem liczb przyspieszenia w drzewie (jest benchmark `benchmarks/kernels/benchmark_gdn_chunk.py` z presetem HV 48 / HG 16).

### 3.2 GDN — stan przy spekulacji: trzy szkoły
| Podejście | Kto | Ruch pamięci na krok weryfikacji k+1 | Bit w bit ze zwykłym dekodem? |
|---|---|---|---|
| Migawka stanu po każdym tokenie | vLLM, SGLang domyślnie | odczyt S + (k+1) × zapis S | tak, jeśli kernel ten sam co w dekodzie |
| Pierścień wejść + rekonstrukcja wyjścia przez (I+A)⁻¹ | ReplaySSM spec (SGLang/vLLM) | odczyt S0 + mały pierścień; zapis S co L | **wyjścia nie** (inna kolejność sum w transformacji UT), stan zatwierdzony tak (bitowy fold) |
| Ping-pong + powtórka zaakceptowanych z taśmy | **Turbo** (`COLLAB.md:125`, `:266`) | odczyt S + zapis S + powtórka n_keep | tak |

- Stan jednego slotu dla Qwen3.8-27B: **153,9 MB w f32, 78,4 MB w bf16** ([SGLang cookbook Qwen3.8-27B](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B)); u nas 149,6 MiB (`COLLAB.md:226-231`).
- ReplaySSM: kernel 1,43–1,64×, end-to-end 1,20–1,27× na Qwen3.5 ([Dao AI Lab](http://dao-lab.ai/blog/2026/replayssm)). SGLang podaje 1,2–1,5× przy batch ≥ 64 (`exec_.py:692-700`). Mechanizm: ruch stanu na krok spada z odczyt+zapis do samego odczytu, czyli ~½ (`fused_recurrent_linear_replayssm.py:14-21`).
- Wniosek dla nas `[INFERENCE]`: przy batch 1 GDN zajmuje 0,47 ms z 21,7 ms tokenu (CONTEXT), więc połowa ruchu stanu to ≤ 0,15–0,2 ms (≤ 1%). Nasz `accept()` to już „bitowy fold”. ReplaySSM nic nowego nam nie da, ale potwierdza, że nasz projekt jest tym, do czego oni doszli.

### 3.3 Prefix cache ze stanem hybrydy
- vLLM: trafienie wznawia tylko na granicy bloku stanu. Wyszukiwanie od prawej, pierwszy znaleziony hash wygrywa (`single_type_kv_cache_manager.py:1964-2014`). Opcja `--prefix-match-unit 64` + `--enable-mamba-shared-prefix-checkpoint` zapisuje stan **w miejscu, gdzie poprzednie zapytanie z tym samym prefiksem się kończyło** (`docs/features/automatic_prefix_caching.md:16-31`).
- vLLM eksportuje punkt kontrolny **w trakcie prefillu**, bez osobnego przebiegu: kernel chunked zapisuje stan na wyrównanym offsecie, jeśli ten offset jest wielokrotnością `checkpoint_alignment` (`checkpoint.py:21-60`, `kv_cache_interface.py:603-624`).
- SGLang: copy-on-write stanu przy trafieniu, „branching seqlen” zapamiętany przy dopasowaniu, śledzenie stanu w dekodzie co 256 tokenów (`exec_.py:650-653`), strategie `no_buffer` / `extra_buffer` / `extra_buffer_lazy` (`exec_.py:623-630`). Sloty na zapytanie: 5 / 4 / 3 ([cookbook](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B)). Int8 dla stanów w cache daje ~2× pojemności, ale jest stratne (`mamba_checkpoint_pool.py:15-40`), więc nie dla nas.

### 3.4 Spekulacja — liczby akceptacji dla Qwen3.5/3.8-27B
- **vLLM, MI300X/MI355X, Qwen3.5-27B, natywne MTP** (średnia długość akceptacji MAL / akceptacja na pozycjach) ([blog vLLM AMD](https://vllm.ai/blog/2026-08-23-speculative-decoding-amd-gpus), appendix): GSM8K N=3 MAL 3,65 (96/89/80%), N=5 4,89, N=7 5,77. HumanEval N=3 3,63, N=7 5,73. MBPP N=3 3,46, N=7 5,02. Najlepsza przepustowość przy N=4–5. Pomiar przy współbieżności > 1 (bazowo 1555 tok/s), więc zyski ×1,5–1,7 nie przenoszą się na batch 1.
- **AMD ROCm blog, MI355X, Qwen3.5-27B bf16, concurrency 1** ([DFlash on MI355X](https://rocm.blogs.amd.com/artificial-intelligence/dflash-on-MI355x/README.html)): MAL MTP 3 / 7 / 15 kroków = 3,68 / 6,03 / 8,02 (HumanEval). DFlash blok 4 / 8 / 16 = 3,76 / 6,63 / 10,38. Przepustowość: MTP stoi na ~245 tok/s od budżetu 8, DFlash b16 396 tok/s, z celem mxfp4 460 tok/s, maks. 5,02× na MATH500.
- **SGLang, H200, Qwen3.8-27B, concurrency 1, T=1,0, 7 tokenów draftu** ([karta z-lab/Qwen3.8-27B-DFlash2](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/blob/main/README.md)): AR 68,9 tok/s, MTP 178,5 (2,59×), DSpark 185,3, **DFlash2 236,1 (3,43×)** na GSM8K. HumanEval: 69,0 / 151,9 / 159,9 / 214,6. MAL MTP vs DFlash2: GSM8K 5,02 vs 5,46, HumanEval 3,91 vs 4,39, MT-Bench 3,74 vs 4,10. Draft DFlash2: 1,92 mld parametrów, 5 warstw SWA, hidden 5120 ([Akicou GGUF](https://huggingface.co/Akicou/Qwen3.8-27B-DFlash2-GGUF/blob/main/README.md)); jest też oficjalny GGUF ([z-lab/Qwen3.8-27B-DFlash2-GGUF](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2-GGUF)).
- Adaptacja głębokości w SGLang: `target_steps = clamp(round(ema_accept_len)+1)`, kandydaci {1,3,5,7} przy BS 1, EMA α=0,2, zmiana co 5 partii (`adaptive_spec_params.py:17-23`, `:145-160`). vLLM: online regresja logistyczna na log-odds prawdopodobieństwa draftu (`vllm/v1/worker/gpu/spec_decode/acceptance_estimator.py:1-15`, `:345`).
- vLLM suffix decoding na GPU: dopasowanie najdłuższego sufiksu + korpus odpowiedzi z zakończonych zapytań, bez synchronizacji z hostem (`vllm/v1/worker/gpu/spec_decode/suffix/speculator.py:3-20`).
- Kwantyzacja tylko głowicy draftu (`draft_lm_head_quantization: fp8|nvfp4`; weryfikacja na własnej głowicy celu, więc zmienia się tylko akceptacja) (`vllm/config/speculative.py:573-578`). U nas to samo robi `TURBO_DRAFT_Q4` (`COLLAB.md:270`).

### 3.5 Atencja weryfikacji na długim kontekście
- SGLang gfx1151, kształt Qwen3.8 (24 q / 4 kv / D 256), T ≤ 8 tokenów draftu: jeden program na (zapytanie, głowa kv, grupa 6 głów q, split) czyta prefiks **raz dla wszystkich T × 6 wierszy**, QK i PV na macierzach. **0,10 / 0,24 / 1,0 ms na warstwę przy 1k / 8k / 39k** wobec 0,43 / 3,5 / 16 ms dla ogólnego kernela extend (`python/sglang/kernels/ops/attention/verify_attention_gfx1151.py:1-15`). 20 splitów na głowę kv (`:24-26`).
- vLLM `csrc/rocm/rdna_decode_attn.cu:1-10`: jedna grupa robocza na (głowa kv, grupa wierszy, segment KV) obsługuje wszystkie wiersze zapytań tej głowy kv, KV czytane raz, oba iloczyny na WMMA 16×16×16. Octave: „kolejne tokeny zapytania dzielą każdy odczyt K/V” (`docs/design/rocm_octave.md:110`).
- U nas `k_attn_w` to jeden blok na (głowa q, token) (`src/gpu/gpu_forward.hip:1136-1140`), więc przy weryfikacji T tokenów K/V jest czytane 24·T razy na warstwę (z L2/MALL, nie zawsze z DRAM). GQA współdzielimy tylko w prefillu (`k_attn_gqa`, `:1231`).
- Liczba z pola: w vLLM na 2× XTX atencja Triton przy 16k to 24–27 ms na wiersz zapytania, a ggml FA 4–5 ms; MTP przy 16k spada do 13,8 tok/s wobec 45,7 bez MTP ([lcz.me/topic/1252](https://lcz.me/topic/1252)).

### 3.6 Kwantowany GEMM na RDNA3 (vLLM)
- Zwrotnica skalar/WMMA zmierzona na gfx1100 dla W4A16: WMMA wygrywa lub remisuje od **M ≥ 12** we wszystkich kształtach. Przy M=1 skalar jest 1,5–3× szybszy, przy M=4 0,5–1× (tabela w `csrc/rocm/q_gemm_rdna3.cu:940-965`). To się zgadza z naszym wynikiem, że GEMV na 16 kolumnach jest ograniczony obliczeniami (`COLLAB.md:198`, `:325`).
- `BLOCK_KN_SIZE=512` dawało +5–10% przy dużym M, ale dekod fp16 przy M=1 zwalniał z 32 do 45 µs, bo tylko ~8 z 96 CU miało pracę (`q_gemm_rdna3.cu:66-78`).
- WMMA prefill: kafel 64×32 na 4 fale, plateau ~22 TFLOPS efektywnie (`q_gemm_rdna3_wmma.cu:1262-1271`). Dekwantyzacja precyzyjna: najpierw odejmij (1024+zero) jako liczbę całkowitą, potem mnóż przez skalę. Stara FMA traciła do 0,025 na komórkę (`q_gemm_rdna3_wmma.cu:72-87`).
- Trik dekwantyzacji do bf16 dla WMMA: `((w >> 4i) & 0x000F000F) | 0x43004300` daje dwa dokładne bf16 `128+q` w jednym rejestrze. Przy M=8 na gfx1151 to 165–190 GB/s wobec 40–70 GB/s dla Tritona (`w4a16_small_m_gfx1151.py:8-20`).
- Brak natywnego `global_atomic_pk_add_f16/bf16` na gfx11, więc split-K idzie przez bufor f32 i deterministyczną redukcję (`q_gemm_rdna3_wmma.cu:27-35`).

### 3.7 Opublikowane liczby batch 1 dla modeli ~27–32B
| Sprzęt | Silnik / konfiguracja | Model | Dekod tok/s | Źródło |
|---|---|---|---|---|
| 1× 7900 XTX | vLLM 0.27.1, W4A16, 8 sekwencji | Qwen3.8-27B | TPOT 73,7 ms @1k / 104,6 ms @2k (bf16 KV); fp8 KV 2,2× wolniejszy nachylenie | [vllm#56992](https://github.com/vllm-project/vllm/issues/56992) |
| 1× W7900 (gfx1100) | SGLang + sglang-radeon, INT4, bez grafów | Qwen3.8-27B | 47,3 | [AMD-AIM/sglang-radeon](https://github.com/AMD-AIM/sglang-radeon) |
| 1× 7900 XTX | SGLang fork gfx1100, bez MTP | Qwen3.8-27B | ~35 | [lcz.me/topic/1567](https://lcz.me/topic/1567) |
| 1× 7900 XTX | llama.cpp Vulkan + MTP (dla porównania) | Qwen3.8-27B | kod 73 / proza 33 | jw. |
| 2× 7900 XTX TP2 | vLLM 0.27.1 W4A16 | Qwen3.8-27B | 52–64 krótki kontekst; 48 @16k; 42 @32k; MTP 70,2 vs 53,2; MTP @16k 13,8 | [lcz.me/topic/1252](https://lcz.me/topic/1252) |
| 2× 7900 XTX TP2 | SGLang fork + MTP-3 | Qwen3.8-27B | 97–116 (zgłoszone przez autora) | [lcz.me/topic/1567](https://lcz.me/topic/1567) (cytuje topic 1532) |
| 4× 7900 XTX TP4 | vLLM PR #57925 (niescalony), MTP k=3 | Qwen3.8-27B | 113–119 do 167k | [zestawienie victoralcazardev](https://github.com/victoralcazardev/rx7900xtx-local-llm/blob/main/docs/SOURCES-alternatives.md) |
| MI355X | vLLM bf16, c=1 | Qwen3.5-27B | MTP ~245, DFlash b16 396, mxfp4+DFlash 460 | [ROCm blog](https://rocm.blogs.amd.com/artificial-intelligence/dflash-on-MI355x/README.html) |
| H200 | SGLang bf16, c=1, T=1 | Qwen3.8-27B | AR 68,9; MTP 178,5; DFlash2 236,1 | [z-lab karta](https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/blob/main/README.md) |

Porównanie z nami: Turbo na **jednej** XTX ma 45,9 tok/s bez spekulacji, 190–222 na kopiach, 72 przy T=0,7 (CONTEXT). Żaden z tych silników na jednej karcie RDNA3 nie zbliża się do tego (29–47 tok/s bez spekulacji). Ich przewaga to algorytmy (DFlash2, cache stanu, weryfikacja drzewa), nie kernele dla gfx1100.

## 4. Co bierzemy do Turbo

Kolejność według zysku do kosztu.

1. **Atencja weryfikacji „KV czytane raz na T×G wierszy” (WMMA)** — wzór: `verify_attention_gfx1151.py`, `csrc/rocm/rdna_decode_attn.cu`.
   - Gdzie: nowy wariant `k_attn_w` w `src/gpu/gpu_forward.hip` dla N ≤ 8 (i N=1, żeby dekod i weryfikacja liczyły tak samo). Blok = (głowa kv, split), 6 głów q × T tokenów jako wiersze 16×16, online softmax per wiersz.
   - Zysk `[INFERENCE]`: dziś przy T tokenach K/V czytamy 24·T razy na warstwę. U SGLang ten sam kształt dał 3,5 → 0,24 ms na warstwę przy 8k. To jest najbardziej prawdopodobna przyczyna naszego „długie prompty: 95–99 vs produkcja 140–159”. Cel: 120–140 t/s na długich promptach.
   - Koszt: 3–4 dni.
   - Ryzyko dla bezstratności: średnie. Dekod musi iść tym samym kernelem (N=1 dopełnione do 16 wierszy), a podział na splity nie może zależeć od T. Mamy już wzór z `k_gemv_wide` i z decyzji split per token (`COLLAB.md:140`).
2. **Chunked GDN w prefillu (port `rdna35_gdn_chunked.cu` na gfx1100)**.
   - Gdzie: zamiast sekwencyjnego `k_gdn` w prefillu (dziś 9–12% czasu prefillu).
   - Zysk `[INFERENCE]`: jeśli GDN przyspieszy 3–5×, prefill rośnie o ~7–9% (844 → ~910–920 t/s przy 2k).
   - Koszt: 3–5 dni. Stała GDN_HEAD_DIM 128 i proporcja 48/16 pasują wprost. Do zrobienia: wejścia f32 zamiast bf16 (LDS: dziś 57,25 KB/blok przy 16 bitach, f32 nie zmieści się w 64 KB bez przeróbki), wybór `GDN_MIN_WAVES_PER_SIMD` dla gfx1100 (Navi31 ma, jak sądzę, 1536 VGPR/SIMD jak gfx1151 `[INFERENCE]`), test DPP `row_shl` na gfx11.
   - Ryzyko: niskie. Prefill jest ten sam w trybie spec i bez spec, więc spec == plain zostaje. Zmieni się tylko tekst względem obecnej wersji (inna kolejność sum, jak przy MMQ).
3. **Prefix cache ze stanem GDN: dokończenie naszego projektu (`COLLAB.md:224-242`) z trzema pomysłami od nich.**
   - (a) Migawka w trakcie prefillu bez osobnego przebiegu: po kawałku kończącym się na wielokrotności N (vLLM: offset wyrównany do kawałka kernela) asynchroniczna kopia D2H 150 MB, nakładana na następny kawałek.
   - (b) Migawka na „punkcie rozwidlenia”: koniec poprzedniej tury oraz `branching_seqlen` przy częściowym trafieniu, czyli następny retry z tym samym prefiksem trafia (vLLM `shared-prefix-checkpoint`, SGLang `mamba_branching_seqlen`).
   - (c) Migawka w dekodzie co 256 tokenów (SGLang `mamba_track_interval`), żeby edycja końca odpowiedzi nie wymagała pełnego prefillu.
   - Zysk: TTFT przy częściowym trafieniu z 3,4 s (2k) / dziesiątek s (32k) do ~6 ms kopii + prefill końcówki (`COLLAB.md:231`, `:257`).
   - Koszt: 3–4 dni.
   - Ryzyko: niskie, jeśli migawka jest w f32 bajt w bajt. **Nie bierzemy int8 z SGLang** (stratne).
4. **DFlash2 jako drugi drafter (obok MTP).**
   - Liczby: na H200, c=1, T=1,0, DFlash2 dał 236 vs 178,5 tok/s dla MTP (+32%), przy MAL 5,46 vs 5,02 (GSM8K) i 4,39 vs 3,91 (HumanEval). Draft ma 1,92 mld parametrów i 5 warstw; jeden przebieg na cały blok 8 tokenów, a nie 7 przebiegów MTP.
   - Zysk dla nas `[INFERENCE]`: najwięcej przy T=0,7 i prozie (dziś 72 t/s, produkcja 92). Na kopiach lookup i tak wygrywa. Draft w Q4/Q8 to ~1,1–2 GB na przebieg wobec ~532 MB × k dla MTP (`COLLAB.md:197`), więc opłaca się dopiero przy k ≥ 4–5.
   - Koszt: 7–10 dni (nowa architektura: wstrzykiwanie KV z ukrytych stanów celu, blok dyfuzyjny, selektor przez głowicę celu).
   - Ryzyko dla bezstratności: niskie, bo weryfikacja jest ta sama co dla MTP. Draft można przekwantować (CONTEXT pozwala).
5. **Weryfikacja drzewa dla GDN (SGLang `retrieve_parent_token`).**
   - Zamiast migawki per węzeł (150 MB × węzeł) użyć naszego podejścia: rekurencja w porządku DFS ze stosem stanów per głowa w scratchu (48 × 64 KB = 3 MB na poziom na warstwę, mieści się w MALL 96 MB) `[INFERENCE]`, a `accept()` powtarza zaakceptowaną ścieżkę z taśmy jak dziś.
   - Zysk `[INFERENCE]`: +10–25% MAL przy T>0.
   - Koszt: 5–7 dni.
   - Ryzyko: średnie (kolejność operacji na ścieżce musi być identyczna jak w łańcuchu).
6. **Drobne, tanie rzeczy (po 0,5–1 dnia):**
   - adaptacja głębokości draftu jak w SGLang (EMA akceptacji + 1, kandydaci {1,3,5,7}), obok naszego `draft_p_min`;
   - korpus odpowiedzi z poprzednich zapytań do lookup/suffix (vLLM suffix decoding: najdłuższy sufiks + pamięć między zapytaniami). W pętlach agentowych odpowiedzi się powtarzają.
   - Zysk po kilka procent, bezstratne.

Czego **nie** bierzemy:
- ReplaySSM spec: wyjścia weryfikacji przez (I+A)⁻¹ nie są bit w bit z dekodem, a „fold” już mamy.
- Int8 / bf16 stanu GDN, Octave KV 3-bit i FLy: wszystkie stratne.
- FP8 KV na gfx11 (2,2× wolniejszy, vllm#56992).
- Kernele GEMM W4A16 vLLM: nasz GEMV ma 89% pasma, a ich format wag to GPTQ, nie GGUF.
- Fused kernel dekodu GDN: mamy już `k_gdn_conv_norm` (`src/gpu/gpu_forward.hip:1653`).

## 5. Werdykt

vLLM i SGLang na jednej karcie RDNA3 są 1,5–2× wolniejsze od Turbo, ale mają trzy rzeczy warte przeniesienia: atencję weryfikacji czytającą KV raz dla wszystkich tokenów draftu, jednokernelowy chunked GDN dla prefillu i dojrzały cache prefiksu ze stanem GDN (migawki w trakcie prefillu, na rozwidleniu i w dekodzie). DFlash2 i weryfikacja drzewa to następny krok dla T>0.
