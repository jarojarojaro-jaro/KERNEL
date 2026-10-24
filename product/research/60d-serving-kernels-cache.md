# 60d. Serving, kernele i cache: Humming, SGLang HiCache, AKV, sonar #1788, Maya v1.1.21–1.1.26

Data: 2026-10-24. Autor: podagent ResServing (+ podagenci AkvPaper2, MayaSonar2). Tylko CPU, bez GPU, bez pobierania wag. Leady z X (2026-10-21/22).

Przeczytane:
- blogi [vLLM Humming](https://vllm.ai/blog/2026-10-21-humming), [SGLang HiCache](https://sglang.io/blog/hicache) i [LMSYS Unified Radix Cache](https://www.lmsys.org/blog/2026-08-11-unified-radix-cache/);
- PR SGLang [#33639](https://github.com/sgl-project/sglang/pull/33639), [#30393](https://github.com/sgl-project/sglang/pull/30393), [#34798](https://github.com/sgl-project/sglang/pull/34798) i [#21259](https://github.com/sgl-project/sglang/pull/21259);
- artykuł [AKV arXiv 2610.28577](https://arxiv.org/abs/2610.28577) i [stronę projektu](https://fuvty.github.io/thinking_yard_project_page/projects/akv/);
- [sonar PR #1788](https://github.com/dphnAI/sonar/pull/1788) (diff);
- wydania Maya [v1.1.21](https://github.com/mw00/project-maya/releases/tag/v1.1.21) … [v1.1.26](https://github.com/mw00/project-maya/releases/tag/v1.1.26) i PR #344/#369/#370/#382.

Sklonowane (`--filter=blob:none`) do `~/qwen-opt/research/`:
- `humming` (`db930af`, 2026-10-22);
- `AKV` (`c567a42`, 2026-10-21);
- `sonar` (`11c991b7`, 2026-10-18; PR w gałęzi `pull/1788/head`, `f653ba4e`).

Maya: istniejący klon `~/qwen-opt/research-src/project-maya` (tagi v1.1.21 `451f9cb` … v1.1.26 `f26d8ba`).

**Ten raport to delta.** Wcześniej badane były:
- Maya: R21g, R32a, R39a, R57f, nota [[project-maya]];
- idea HiCache dla GDN: R21f, wiersz 11 katalogu A–Z;
- Humming wyłącznie jako baseline w R21g (inferrous) i R57a.

Pierwszy raz badam kod Humming, mechanizm HiCache dla stanu hybrydowego, AKV, sonar #1788 oraz Maya v1.1.21–1.1.26.

Oznaczenia: `[INFERENCE]` = mój szacunek; `[niezweryfikowane]` = nie dało się sprawdzić u źródła.

## TL;DR

1. **Humming nie ma nic dla XTX i nic nowego dla dekodu batch 1.**
   - Tylko CUDA (Turing+ i T-Head Zhenwu): w repo nie ma ani jednej linii HIP/ROCm/gfx. Nie wspiera GGUF.
   - Przy M=1 to kafle MMA z dopełnieniem M do 8/16 plus Stream-K, a nie GEMV. Ich własny pomiar na RTX 4090 (W4A16, 8192², kanałowe skale, zimne L2) daje **610 GB/s = 60% pasma**, tyle co Marlin.
   - Zgłoszenie z zewnątrz ([#111](https://github.com/vllm-project/humming/issues/111)) pokazuje, że przy M≤4 kernel jest ograniczony liczbą instrukcji dequantu, a nie pamięcią. Maintainer odrzucił osobną ścieżkę GEMV.
   - Nasze wielokolumnowe MMVQ na XTX czyta 75.7% pasma ([[podrecznik-gpu]]).
   - Zyski Humming (do 5×, E2E +14–43%) dotyczą MoE i dużych batchy na Hopper/Blackwell, w tym W4A8-MXFP4 na H20.
2. **HiCache daje trzy konkretne, tanie pomysły dla naszego llama-server + omp.**
   - (a) **Przywracanie wpisu `--cache-ram` przez pinned staging.** Dziś 2.3 GB to ~1.1 s, czyli ~2 GB/s.
   - (b) **Lekki wpis „prefiks systemowy”.** To KV pierwszych ~2.5k tokenów plus *jeden* checkpoint GDN na granicy prefiksu, tak jak branch-checkpoint w #33639. Nowa sesja podagenta nie kopiowałaby wtedy całych 2.3 GB.
   - (c) **Eviction według `prompt_cache_key`** (session_id z URC), który omp już wysyła, a serwer ignoruje.
   - Szacunek łączny: start nowej sesji Qwena 1612 → ~400–600 ms `[INFERENCE]`.
   - Poziom L3 (dysk) odpada decyzją użytkownika „KV tylko w RAM” ([[2026-10-19-kv-tylko-w-ram]]).
3. **AKV (Tsinghua) to sterowanie KV przez harness/agenta:**
   - drop wiadomości narzędzi plus repozycjonowanie kluczy RoPE bez re-prefillu;
   - −27.7% to **koszt w centach API** (ceny Groq/MiniMax), a nie FLOPy;
   - przepustowość przy szczycie na 8×A800 jest 1.18–1.53× wyższa.

   **U nas repozycjonowanie jest zablokowane:** Qwen3.8 ma IMROPE, a llama.cpp odmawia `seq_add` (`get_can_shift()==false`). Sam drop działa (`seq_rm`), a GDN i tak trzyma informację o usuniętych tokenach. Wdrożenie jest drogie (cache kluczowany historią operacji, spany wiadomości, KV MTP). Zostaje do obserwacji, z tanim testem sufitu na transkryptach omp.
4. **sonar #1788** (otwarty, AGPL-3.0 repo): all-reduce dla 4 GPU w 1 CTA (butterfly przez P2P + TMA), **tylko sm_120, TP=4, hidden 5120/6144, ≤8 wierszy, wymaga P2P**. Daje +12.7% dekodu na 4× RTX PRO 6000. Dla nas **nie dotyczy**: jedno GPU, 3090 = sm_86, brak ROCm.
5. **Maya v1.1.21–1.1.26 to wyłącznie silnik DeepSeek (maya-ds4).** Dla gfx1100 nic do wzięcia „za darmo”. Warte zapamiętania:
   - WMMA BF16 z rozbiciem hi/lo (sparse attention prefill, 2.4× na Strix Halo);
   - „dekoduj gorących ekspertów do FP16 raz + GEMM biblioteczny” (`DS4_FAT_ROWS`, 1.3–1.56× prefillu na 3× V100);
   - all-reduce przez copy engine i pinned host **bez P2P** (v1.1.22);
   - pomiar na **2× RX 7900 XTX**: batchowanie kwantyzacji q8 w jednym launchu nie dało nic (12.5 vs 13.1 t/s).

## 1. Co to jest

### 1.1 Humming
Biblioteka kerneli GEMM dla skwantowanych wag i aktywacji (WnA16, W8A8, W4A8, W4A4), gęstych i MoE (ścieżki Indexed/Grouped). Kernele są kompilowane JIT (NVRTC/NVCC) z komponentów CUDA według trzech konfiguracji: Layer, Compute i Tuning ([blog](https://vllm.ai/blog/2026-10-21-humming)). Od vLLM 0.29.0 jest zależnością buildów CUDA i jest wybierana przez `--linear-backend humming --moe-backend humming` (tamże).

### 1.2 SGLang HiCache
Hierarchiczny cache prefiksów: L1 = HBM GPU, L2 = DRAM CPU, L3 = zewnętrzny storage (3FS, Mooncake…). Opiera się na drzewie HiRadixTree i od 2026 na **Unified Radix Cache** (URC), czyli jednym drzewie z komponentami FULL / SWA / MAMBA ([blog HiCache](https://sglang.io/blog/hicache), [blog URC](https://www.lmsys.org/blog/2026-08-11-unified-radix-cache/)). Dla modeli hybrydowych zapisuje i przywraca także snapshoty stanu rekurencyjnego i stan draftu MTP/EAGLE.

### 1.3 AKV („Cache Engineering for Agents”)
Agent albo harness edytuje KV w trakcie sesji:
- **append**;
- **drop(P)**: tokeny znikają z atencji, pozycje reszty zostają;
- **repos**: klucze przenumerowane na 0..r−1 przez K ← R(q)R(p)⁻¹K, wartości bez zmian.

Wszystko dzieje się bez re-prefillu i bez edycji tekstu ([arXiv 2610.28577 §3.3, Eq. 5](https://arxiv.org/html/2610.28577)).

### 1.4 sonar PR #1788
„perf(sm120): optimize DeepSeek-V4.1 inference”, PR na 12 550 linii w forku Aphrodite/vLLM. Jego częścią (commit `927f3262f8`) jest all-reduce „paired_single” dla małych komunikatów w TP=4 po PCIe ([PR](https://github.com/dphnAI/sonar/pull/1788)).

### 1.5 Project Maya v1.1.21–1.1.26
Kolejne wydania silnika DeepSeek-V4.1-Flash: Maya-XS (IQ1_S), TP na wielu GPU, szybszy drafting DSpark, prefill na tensor cores dla Volta/Turing/Ampere oraz gfx11/gfx12 ([releases](https://github.com/mw00/project-maya/releases)).

## 2. Kto / skąd

| projekt | autorzy | repo / licencja | daty |
|---|---|---|---|
| Humming | Ant Group (Jinzhen Lin, Zekai Gu, Zhilin Huang) + vLLM (Michael Goin, Roberto L. Castro i in.) | [vllm-project/humming](https://github.com/vllm-project/humming), Apache-2.0, pakiet `humming-kernels` | 1. commit 2026-02-12, 325 commitów, ~260 od Jinzhen Lin (3 aliasy) |
| HiCache | SGLang (tutorial: Yichi Zhang); PR: xiezhq-hermann (#34798), Chen-0210 (#33639), 1e4ves (#30393), huangtingwei9988 (#21259) | [sgl-project/sglang](https://github.com/sgl-project/sglang), Apache-2.0 | CPU 2025-02, L3 2025-07, mamba 2026-04-14, draft 2026-08-06, branch 2026-08-10, buffer-only 2026-08-19 |
| AKV | Tianyu Fu, Ruoxi Wang, Zihan Min (równy wkład) … Yu Wang; Tsinghua NICS-EFC (+ CUHK) | [thu-nics/AKV](https://github.com/thu-nics/AKV), Apache-2.0 | arXiv v1 2026-10-20; 1. commit 2026-10-08 |
| sonar #1788 | AlpinDale (dphnAI) | [dphnAI/sonar](https://github.com/dphnAI/sonar), repo AGPL-3.0 (nowe pliki z nagłówkiem SPDX Apache-2.0) | otwarty 2026-10-21, stan OPEN (sprawdzone 2026-10-24) |
| Maya | mw00 + społeczność (@needmorevram #344, @jinsoojinsoo #369, gfx12 #370, @mrsirg97-rgb #356) | [mw00/project-maya](https://github.com/mw00/project-maya) | v1.1.21 2026-10-21 … v1.1.26 2026-10-23 |

## 3. Jak działa technicznie

### 3.1 Humming: kod (`db930af`)

**Brak AMD.**
- `grep -i 'hip|rocm|amd|gfx|wavefront'` po całym repo trafia tylko w `msvc_arch: amd64` w CI.
- Heurystyki istnieją wyłącznie dla sm75, sm8x, sm90/H20, sm100, sm120, sm121 i T-Head PPU (`humming/tune/*.py`).
- Backendy MMA to `mma.sync`, WGMMA, UMMA/tcgen05 i TMA (`include/humming/mma/`, `utils/ptx/`).
- Port na HIP oznaczałby przepisanie warstwy MMA/kopiowania na WMMA gfx11 i LDS. Dequant w C++ (lop3/prmt) przeniósłby się na `v_bfi_b32`/`v_perm_b32` `[INFERENCE]`.
- Nie ma issue ani PR o ROCm (`gh issue list -S rocm`).

**Formaty** (`humming/dtypes.py:189-223`):
- wagi: uint1–8, int2/3/4/6/8;
- „float bez wykładnika” `float2e0m1` … `float8e0m7`;
- FP: `float4e2m1`, `float6e2m3`, `float6e3m2`, `float8e3m4`, `float8e4m3`, `float8e5m2`, `float8e5m3`;
- skale: `float8e8m0` (MX), FP16/BF16, grupy po K i po N (`weight_scale_group_size[_n]`), zero-pointy całkowite lub FP, skale drugiego poziomu (`schema/humming.py:20-67`).

Importery (`humming/schema/`): AutoRound, AWQ, BitNet, compressed-tensors, FP8, gpt-oss MXFP4, GPTQ, ModelOpt, MXFP4, Quark. **GGUF nie ma** (grep `gguf|ggml` pusty), więc K-quantów z super-blokami i 6-bitowymi podskalami też nie.

**Mały M (dekod)** (`humming/tune/base.py`):
- Próg compute-bound liczony z rooflinu urządzenia (`_estimate_compute_bound_threshold`, l. 14-31).
- Przy `shape_m <= block_m` kafel M = 8 (MMA m8, jeśli dostępne) albo zaokrąglenie do 16 (l. 95-96).
- Poniżej progu połowi się `block_k`, żeby wydłużyć potok (l. 234-239).
- Stream-K jest domyślnie włączony dla K > 1024, chyba że siatka wypełnia falę ≥ 90% (l. 334-376).
- Dla dense A16 przy kaflu 64×64 działa „weight reuse” (64×128×64, 2 CTA/SM, l. 304-332).
- **Dedykowanej ścieżki GEMV nie ma.** W #111 maintainer napisał wprost, że Humming „does not accept implementations that add a separate branch outside the main kernel”.

**Dequant** (`include/humming/datatype/`):
- *int → f16*: magiczna stała `0x6400`/`0x4300` wstawiona przez `lop3`, potem `__hsub2` zero-pointu (`dequant_single.cuh:25-47`). Jak w Marlinie.
- *uint → int8/int4*: jeden `lop3` + odejmowanie + XOR (`:8-22`).
- *Symetryczny int → float e0mX*: blog podaje, że Humming automatycznie konwertuje symetryczne inty do formatu bez wykładnika, bo dequant to wtedy tylko przesunięcie bitów (`fp_to_fp`, `:103-110`).
- *MXFP4 → INT8* (`dequant_fused.cuh:33-54`): 8-wpisowa tablica wartości FP4 ×2 {0,1,2,3,4,6,8,12} przesunięta **o wykładnik skali E8M0** (`0x03020100 << exp_offset`, `0x0C080604 << exp_offset`), indeksowana `prmt`, znak dokładany przez `(val − flag) ^ mask`. Skala potęgi dwójki jest więc wtopiona w wartości int8, a nie mnożona po iloczynie.
- *MXFP4 → FP8 E4M3* (`:15-30`): dodanie przesunięcia wykładnika `prmt`-em do bajtów wykładnika.

**Ich własny benchmark sm86/sm89** (`benchmarks/results/4090/dense_n8192_k8192_g0/*.json`, commit `6174972` 2026-03-30; RTX 4090, 1008 GB/s teoret., kanałowe skale g0, zimne L2):

| kernel | M=1 | M=8 | M=16 | M=64 |
|---|---|---|---|---|
| Humming W4A16 int4 | 55.1 µs, 610 GB/s | 55.5 µs | 55.4 µs | 70.4 µs |
| Marlin W4A16 int4 | 55.0 µs, 611 GB/s | 55.3 µs | 56.4 µs | 66.5 µs |
| Humming W8A16 int8 | 102.5 µs, 656 GB/s | 103.0 µs | 103.2 µs | 106.1 µs |
| Humming W4A8 fp4×fp8 | 54.5 µs, 617 GB/s | 54.5 µs | 54.6 µs | 57.4 µs |

Czas jest płaski do M=16. To cecha kafli MMA: weryfikacja 5 tokenów kosztuje tyle co 1, ale przy 60% pasma.

**Zgłoszenie [#111](https://github.com/vllm-project/humming/issues/111)** (dfmcintosh-hash, 2026-10-04, CMP 170HX sm80 + spot-check RTX 3090):
- MoE W2/W4-A16 przy M=1–4 działało na 2.5–3.5× czasu progu HBM.
- Kernel z tą samą siatką, ale samym XOR zamiast dequantu, strumieniował 1100–1200 GB/s. Wąskim gardłem jest więc potok F16: ~17 instrukcji na słowo wag.
- Ich ścieżka Tritonowa GEMV + split-K + subnormalny trik fp16 (pole bitowe wstawione w mantysę, jedna `fma.f16x2` na 2 wagi, zero-point i skala raz na grupę przez sumy grup x) dała 1.36× (M=1) i 1.51× (M=2) na CMP.
- Na RTX 3090: 2/2 bit 1.65–1.74×, 4/4 bit 1.13–1.17×.
- Issue zamknięte bez scalenia.

### 3.2 HiCache: co jest nowe dla modeli hybrydowych

- **Układ pamięci:** L1 jest „layer-first”, host i L3 są „page-first”. Konwersja odbywa się w transferze. Kernele I/O GPU↔host mają do 3× przepustowości `cudaMemcpyAsync`, a page-first z zero-copy do 2× host↔storage ([blog](https://sglang.io/blog/hicache)).
- **Nakładanie transferu na obliczenia:** warstwa L liczy nowe tokeny, gdy tylko jej KV dojdzie z hosta, a kolejne warstwy wciąż się ładują (tamże).
- **Polityki:**
  - prefetch: best-effort, wait-complete lub timeout;
  - backup: write-through, write-through-selective (licznik trafień) lub write-back przy eviction.
- **Snapshoty stanu rekurencyjnego ([#33639](https://github.com/sgl-project/sglang/pull/33639)):**
  - Gdy na *istniejącym* prefiksie powstaje nowy snapshot (np. na końcu wspólnego dokumentu, a nie na końcu pytania A), dostaje on osobny backup do hosta. Pełne KV nie jest kopiowane drugi raz.
  - Test (6.4K wspólnego + 3.6K nowego): pełne odzyskanie prefiksu 1/10 → 10/10 żądań, trafienie tokenów 15.74% → 64.00%.
  - Uruchamiane z `--mamba-radix-cache-strategy extra_buffer` na Qwen3-Next-80B, TP2.
- **Stan draftu ([#30393](https://github.com/sgl-project/sglang/pull/30393)):**
  - KV/indexer/SWA draftu MTP/EAGLE/DSpark jest przenoszony razem z targetem: jako „packed” (ogon warstw w puli targetu) albo „sidecar”.
  - Bez tego trafienie prefiksu obniża akceptację spekulacji.
- **Buffer-only ([#34798](https://github.com/sgl-project/sglang/pull/34798)):** host służy tylko jako bufor transferu do L3.
- **Sesje w URC** ([blog URC](https://www.lmsys.org/blog/2026-08-11-unified-radix-cache/)): aplikacja dołącza `session_id`. Po zakończonej turze URC rejestruje region wielokrotnego użycia sesji; FULL śledzi ścieżkę, SWA okno, a MAMBA „frontier”. Referencje zmieniają **kolejność eviction**, nie przypinają pamięci.

**Nasz stan dla porównania (llama-server topka):**

| mechanizm | my | SGLang HiCache/URC |
|---|---|---|
| cache prefiksów | `--cache-ram`: wpis = **pełny stan slotu** (KV + GDN + draft) w `std::vector`, wybór przez `f_keep`/`f_sim` (`server-task.cpp:1804-1879`), przywrócenie „na wyłączność” (dane czyszczone po załadowaniu, l. 1850) | drzewo radix, bloki/strony współdzielone przez wiele żądań |
| stan GDN | checkpointy n−4−ub i n−4 promptu, pinned staging `LLAMA_CKPT_VRAM=2` (14.9 ms/ckpt, [[raport-38-ckpt-vram]]) | snapshoty w puli MAMBA, osobny backup snapshotów gałęzi (#33639) |
| współdzielenie między sesjami | `LLAMA_SERVER_CACHE_SHARE_MIN=1024`: **kopia** całego wpisu i powrót do checkpointu na wspólnym prefiksie; Qwen 8019 → 1612 ms, z czego ~1.1 s to kopia 2.3 GB z RAM ([[2026-10-18-cache-promptu-agenta]]) | wspólny węzeł prefiksu; kopiowany jest tylko brakujący komponent |
| draft MTP | `data.drft` zapisywany razem z wpisem (`server-task.cpp:1854-1870`) | packed/sidecar (#30393) |
| L3 / dysk | `--slot-save-path` (53k Qwen: 2.28 GiB, odczyt 2.51 s, [[cache-sesji-na-dysku]]); decyzja: tylko RAM | 3FS/Mooncake/…; buffer-only |
| sesje | `prompt_cache_key` od omp **ignorowany** | `session_id` steruje kolejnością eviction |

### 3.3 AKV: mechanizm (`c567a42`)

- **Silnik:** łatany SGLang (`sglang==0.5.20+akv`, `akv/system/sglang.patch` 6630 linii, upstream `94602c9c`). Dozwolone architektury to Qwen1–3, GptOss i MiniMaxM2 (`akv/system/sglang/srt/context_system/capabilities.py:17-26`).
- **Decyzja o dropie:**
  - W eksperymentach głównych decyduje polityka harnessu „tool-response rolling drop”: zostaje KV 12 ostatnich odpowiedzi narzędzi plus całe rozumowanie (§5.1; `akv/agent/policies/{triggers,selectors,reposition}.py`).
  - Repos uruchamia się po przekroczeniu progu podsumowania: 96K, a dla MiroThinker 192K.
  - Wariant „Cache-As-Tool” daje modelowi narzędzie `drop_context(message_ids, reposition)`. Usuwać można tylko wcześniejsze wyniki narzędzi, a pierwsze 2 wiadomości są chronione (`policies/tools.py:50-109`).
  - Fine-tuning nie jest potrzebny: modele gotowe, sterowane promptem (§6).
- **Protokół:** dodatkowe pola w żądaniu OpenAI, np. `drop_message: {"3":[1,2]}` i `reposition: [3]` (`akv/system/README.md:91-107`).
- **Rotacja:** `kernels/ops/attention/context_reposition.py:28-123` robi w FP32 obrót odwrotny o starą pozycję, potem obrót do nowej. Celowo **nie** obraca o deltę, bo „nawet 1 ULP BF16 się wzmacnia” (l. 93-95). Wartości i nierotowany ogon K są kopiowane bez zmian. Działa copy-on-write do nowych slotów; wymaga `page_size=1` i niekwantyzowanego KV (l. 126-236).
- **Serwer:**
  - drzewo radix rozszerzone o węzły drop/repos (ten sam tekst może dać różne KV zależnie od historii operacji);
  - eviction świadome dropów;
  - „segment-batch attention” odtwarza wyrzucony stan jednym prefillem (§4.2, §A.1.1).
- **Wyłączone w kodzie:** spekulacja, HiCache, kwantyzowane KV, `page_size≠1` (`capabilities.py:44-88`).
- **Modele liniowe/hybrydowe:** tylko jedno zdanie w §6, że to przyszła praca.

### 3.4 sonar #1788: all-reduce „paired_single”

Źródło: `csrc/pcie_pull_all_reduce.cu`, `aphrodite/distributed/device_communicators/pcie_pull_all_reduce.py` w PR.

- **Algorytm:** butterfly w 2 rundach w **jednym CTA (512 wątków)**.
  - Runda 1: pełny wektor BF16 do rank^1.
  - Runda 2: ranki 0/1 wysyłają sumę par w FP32, ranki 2/3 spakowaną parę BF16 do rank^2.
  - Na końcu ustalona kolejność dodawań w FP32 i jedno zaokrąglenie, więc wszystkie ranki dostają identyczny wynik.
- **Transport:** zapis P2P do slabów CUDA-IPC przez TMA (`cp.async.bulk`), tylko `__CUDA_ARCH__==1200`. Flagi epokowe `st.release.sys`/`ld.acquire.sys`, timeout 2 s przez `%globaltimer`. Bez fallbacku w runtime: błąd zatrzymuje silnik.
- **Kwalifikacja (`should_use`):** BF16, 1–8 wierszy × 5120/6144 (≤ 96 KiB).
- **Bramki startowe:** TP=4 na jednym węźle, CC dokładnie 12.0, NVML P2P READ/WRITE OK dla każdej pary, topologia ≤ `NVML_TOPOLOGY_NODE`.

### 3.5 Maya v1.1.21–1.1.26 (tylko maya-ds4, DeepSeek-V4.1-Flash)

| wersja | zmiana | mechanizm (commit / plik @v1.1.26) | przełącznik |
|---|---|---|---|
| 1.1.21 | prefill AMD ~2.4× | `sparse_attn_wmma_kernel` (`ds4_kernels.cu:1612`) na `__builtin_amdgcn_wmma_f32_16x16x16_bf16_w32` z rozbiciem Q i P na BF16 hi+lo; eksperci low-bit na `wmma_f32_16x16x16_f16_w32` (`ds4_gguf.cu:912`); GEMM-y gęste przez hipBLASLt z wyborem kernela per kształt (`ds4_lt.cu`, `lt-picks.txt`); router po 8 tokenów (`3453271`) | `DS4_ATTN_WMMA=0`, `DS4_LT=0`, `MAYA_DS4_NO_TC=1`, `DS4_ROUTER_ROWS=0` |
| 1.1.21 | dekod +9%, gdy eksperci w VRAM | pominięcie mailboxa hosta | `DS4_HOST_FREE` |
| 1.1.22 | TP bez P2P | `allreduce_dma` (`ds4_kernels.cu:3514`): częściowe FP16 D2H przez copy engine do pinned hosta, H2D zero-copy ≤4 GPU; ≥5 GPU `HostReducer` na CPU; bitowo = `ar_rs16_kernel` (PR #344, `68c0f31`) | `DS4_AR_ZC`, `DS4_AR_OVERLAP` |
| 1.1.22 | drafting 1 GPU „~1.85×” | na HIP `hc_mix`/`hc_split` z powrotem na strumieniu warstwy (każde czekanie między strumieniami ~1 ms/warstwę na Windows HIP); rollback jednym launchem (`comp_restore_batch`) (PR #344) | `DS4_HC_STREAM` |
| 1.1.22 | Maya-XS 120.6 GB | eksperci IQ1_S (384/warstwę), gęste Q8_0; GPTQ z error-feedback na superblokach 256 (`tools/maya_quant/gptq.py:1-17`, pipeline GLM); przepis DS „warstwa po warstwie na skwantowanym modelu” `[niezweryfikowane]`: w repo jest tylko opis (`tools/ds4/download_gguf.json:267`) | – |
| 1.1.23 | crash >32 768 tok. na AMD i RTX 20 | bufor top-k z rozmiaru shared memory (64 KB/blok) (`7856997`) | – |
| 1.1.24 | prefill RTX 30+ | `sparse_attn_mma_kernel` (`:1810`) `mma.sync.m16n8k16` BF16 hi/lo (PR #369, `e9b5df4`) | `DS4_ATTN_MMA=0` |
| 1.1.24 | prefill RDNA4 | ten sam kernel na gfx12; PR podaje, że asm gfx1100 jest bajtowo identyczny (PR #370, `f6f2604`) | – |
| 1.1.25 | sesje przeżywają przełączenie i restart | opt-in `MAYA_DS4_SLOT_KEEP=1` (#356); ponowiona tura cofana do checkpointów rozmowy (#394) | `MAYA_DS4_SLOT_KEEP` |
| 1.1.26 | prefill Volta/Turing 2× | `sparse_attn_v7_kernel` (`:3019`): `nvcuda::wmma` FP16, S=QKᵀ do smem, **dokładny softmax FP32 bez online-rescale**, P·V; skalowanie potęgami 2 (K/V ×2⁻⁴, Q do ~2¹², P ×2¹⁴); hi/lo FP16 ~22 bity; ≤640 wierszy (`c8cb6ea`) | `DS4_ATTN_V7=0` |
| 1.1.26 | prefill „każde NVIDIA” | gorący ekspert dekodowany **raz** do FP16 (`f16_rows_kernel`, `gather_f16`, `swiglu_f16`, `ds4_iq.cu:1290-1349`) i mnożony cuBLAS-em zamiast ponownego dekodu co 64 wiersze; slaby atencji do 3% pamięci | `DS4_FAT_ROWS` (64; 0 = wył.) |

Opt-in z PR [#348](https://github.com/mw00/project-maya/pull/348) (`c896e53`): swizzle LDS w kernelu atencji HIP (`DS4_HIP_ATTN_SWIZZLE=1`), bitowo zgodny.

## 4. Liczby (z warunkami pomiaru; żadna nie jest nasza)

| co | liczba | warunki | źródło |
|---|---|---|---|
| Humming W4A16 M=1 | 55.1 µs, 610 GB/s (60%) | RTX 4090, 8192×8192, g0, zimne L2, torch 2.10 cu128 | `benchmarks/results/4090/.../humming_w4a16_int4_float16.json` |
| Humming E2E | +14.1% (C=1) … +43.3% (C=64) przepustowości wyjścia; TTFT −25…−32% | DeepSeek-V4.1-Flash MXFP4, 8× H20, TP8, Marlin W4A16 → Humming W4A8 | [blog](https://vllm.ai/blog/2026-10-21-humming) |
| Humming kompilacja | 1.82 s (NVCC) / 1.88 s (NVRTC) vs CUTLASS 23.35 s | 1 kernel W4A16, H200, CUDA 13.4, bez cache | blog |
| GEMV z #111 vs Humming | 1.36× (M=1), 1.51× (M=2); 3090: 1.65–1.74× (2/2), 1.13–1.17× (4/4) | MoE GLM-5.3, 75 warstw, 6× CMP 170HX, CUDA graphs | [#111](https://github.com/vllm-project/humming/issues/111) |
| HiCache LooGLE | TTFT 8.61 → 4.84 (L2) → 1.83 s (3FS L3) → 1.43 s (L3 wypełnione); 51 168 → 76 322 tok/s | DeepSeek-R1, 8× H20-3e | blog HiCache |
| HiCache multi-turn | 9.4K → 14.3K → 145.5K tok/s efektywnego wejścia (L1/L2/L3), trafienie ~98% | DeepSeek-V4-Flash, TP4, 4× H200, Mooncake 500 GiB | blog HiCache / URC |
| HiCache hybryda | 15.5K → 21.1K → 67.1K tok/s, 96.8% trafień, TTFT 1.23 s | Inkling-Small (FULL+SWA+MAMBA) | tamże |
| branch snapshot | odzyskanie 1/10 → 10/10, trafienie 15.74 → 64.00% | Qwen3-Next-80B, TP2, 6.4K wspólne + 3.6K nowe | [#33639](https://github.com/sgl-project/sglang/pull/33639) |
| AKV koszt | −27.7% vs Standard, −21.9% vs Text Eng. (centy API, średnio 3 modele × 4 benchmarki) | ceny Groq/MiniMax/Qwen; tokeny repozycjonowane liczone jak cache-hit | arXiv §5.1, Tab. 1, 6 |
| AKV jakość (śr.) | MiniMax-M2.7 52.4 → 53.7; GPT-OSS-120B 51.0 → 53.1; MiroThinker 44.1 → 45.8 | BrowseComp-Plus, GAIA-Text, SWE-Verified, xbench-DS | Tab. 1 |
| AKV serwer | latencja śr. 12.39 → 9.09 s; wejście 33 832 → 51 837 tok/s; wyjście 313 → 369 tok/s | GPT-OSS-120B BF16, 8× A800, PD TP4+TP4, top-80 trajektorii SWE, C=12 vs C=14 | Tab. 2 |
| AKV krok dekodu | 26.186 → 21.990 ms (−16%), atencja 7.082 → 2.849 ms | ten sam batch | §A.4.1 / strona |
| sonar #1788 | 290.4 → 327.2 tok/s (+12.7%), akceptacja 59.43 vs 59.05% | 4× RTX PRO 6000 Blackwell, TP4, KV FP8, 1 żądanie, 2674 tok. wejścia, DSpark K7, CUDA graphs, mediana 7 | [PR body](https://github.com/dphnAI/sonar/pull/1788) |
| Maya TP v1.1.22 | prefill 424/435 → 785/818 tok/s; dekod 42.9 → 66.8 tok/s; PPL 3.4114 vs 3.4081 | 9 GPU PCIe 3.0 x8, `--tp 8`, EXL3 3.5 bit | PR #344 |
| Maya drafting | 8.5 → 15.9 tok/s | Maya-S + DSpark, Ryzen AI Max, v1.1.21 vs v1.1.22 | PR #344 (komentarze) |
| Maya RTX 30 MMA | atencja 0.62 → 0.40 ms/tok; prefill 8–9K 478–490 → 575–627, ~30K 957–992 → 1104–1234, ~103K 1292 → 1483 tok/s | RTX 3090, EXL3 3.5 bpw, `--tp 1`, chunk 8192 | PR #369 |
| Maya RDNA4 | prefill 1.16× (2K), 1.40× (8K), 1.33× (32K, 485 → 643), 1.28× (122K) | 2× gfx1201 32 GB, Maya-S | PR #370 |
| Maya AMD v1.1.21 | prefill 2.35–2.53× | Ryzen AI Max, Maya-S, 4K–18K | release v1.1.21 |
| Maya FAT_ROWS | 1.3× (2K), 1.56× (8K), 1.49× (32K); KL 0.285 → 0.276 | 3× V100, Maya-XS | release v1.1.26 |
| **Maya na 2× XTX** | `MAYA_DS4_Q8_BATCH=1`: dekod 12.5 vs 13.1 t/s (bez zysku); gap launchu 3.3 µs, praca ~2 µs | 2× RX 7900 XTX, ROCm 7.2.4 | PR #382 |
| Maya na 2× XTX | dekod 37.1 t/s (42.8 z cache promptu), prefill 155 tok/s przy 130K | 2× XTX TP2 (PCIe 4.0 x4) + 8060S, Maya-S, eksperci z NVMe USB4 | issue #410 / README `8412d5e` |

## 5. Licencja / dostępność

- **Humming:** Apache-2.0, `pip install humming-kernels` (~500 KB, kompilacja JIT); w vLLM ≥ 0.29.0 domyślnie dla CUDA; tylko NVIDIA sm75+ i T-Head.
- **SGLang/HiCache:** Apache-2.0; od podstaw Python + kernele CUDA; dla nas to źródło wzorców, nie kodu.
- **AKV:** Apache-2.0; tylko łatany SGLang, bez spekulacji i bez kwantyzowanego KV.
- **sonar:** repo AGPL-3.0 (nowe pliki z PR mają nagłówek Apache-2.0 SPDX `[niezweryfikowane: która licencja wiąże po scaleniu]`); PR otwarty.
- **Maya:** jak w [[project-maya]] (bez zmian licencji w tych wydaniach).

## 6. Co z tego dla nas

Ranking według szacowanego zysku do wysiłku. Wszystkie zyski `[INFERENCE]`, dopóki nie zmierzymy.

| # | pomysł (źródło) | cel | szac. zysk | wysiłek |
|---|---|---|---|---|
| 1 | **Przywracanie i zapis wpisu `--cache-ram` przez pinned staging + jedna seria async** (HiCache: kernele I/O 3× nad `cudaMemcpyAsync`; u nas wzorzec `LLAMA_CKPT_VRAM=2`) | XTX (też 3090) | kopia 2.3 GB ~1.1 s → ~0.15–0.3 s przy ~8–20 GB/s PCIe 4.0; start nowej sesji Qwena 1612 → ~0.8 s | 1–2 dni; najpierw 1 h pomiaru, czy 1.1 s to pasmo (pageable) czy coś innego |
| 2 | **Lekki wpis „prefiks systemowy”**: KV tokenów [0, P) + jeden checkpoint GDN dokładnie na P (koniec promptu systemowego i narzędzi omp, ~2.5k tok.) zamiast kopii całego wpisu 53k (HiCache #33639: snapshot na końcu wspólnego prefiksu) | XTX, 3090 | wpis ~0.1 GB KV + ~0.15 GB stanu zamiast 2.3 GB, więc nowa sesja podagenta ~1.6 s → ~0.3–0.5 s; łącznie z #1 | 2–3 dni (checkpoint na granicy wiadomości wymaga znajomości spanów z szablonu) |
| 3 | **Eviction i wybór wpisu według `prompt_cache_key`** (URC `session_id`), zamiast samej heurystyki `f_keep ≥ 0.25` | XTX, 3090 | usuwa przypadki 7–8 s re-prefillu przy przeplocie sesji i podagentów; zysk zależy od workloadu | 1 dzień |
| 4 | Stream-K dla MMQ RDNA3 w prefillu (Humming włącza Stream-K domyślnie dla K>1024 i niepełnej fali; u nas `stream_k=false` w `mmq-config-rdna3.cuh`) | XTX | prefill: do −5…−15% czasu przy kształtach z niepełną falą (szacunek z rr-prefill-kv F7) | wysoki (5+ dni); już na liście, Humming tylko to wzmacnia |
| 5 | „Zdekoduj raz do FP16 + GEMM biblioteczny (hipBLASLt)” dla dużych chunków prefillu zamiast MMQ (Maya `DS4_FAT_ROWS`, Strata/R21g #3058) | XTX | niepewny: −10…+15% pp przy ≥ 4k `[INFERENCE]`; nasz prefill to w 72–81% MMQ | niski koszt testu (flaga kompilacji `GGML_CUDA_FORCE_CUBLAS` lub próg), średni koszt wdrożenia |
| 6 | AKV „tylko drop”: usuwanie KV starych wyników narzędzi w warstwach atencji bez re-prefillu (`seq_rm`); repos niemożliwy przy IMROPE | XTX | dekod przy długim kontekście: tylko część atencji (16 z 64 warstw pełnej atencji + MTP); przy 64k na XTX z `kvq` raczej kilka % `[INFERENCE]` | wysoki: cache kluczowany historią operacji, spany wiadomości, KV MTP, unieważnianie checkpointów |
| 7 | Humming jako baseline vLLM na 3090 (W4A16 GPTQ/AWQ Qwen3.8-27B) | 3090 | pomiarowy, nie produktowy; przewidywanie: batch-1 ≈ Marlin, poniżej naszego MMVQ | 1 h wynajmu, ale wymaga pobrania checkpointu na maszynie Vast (poza zakazem lokalnym, decyzja użytkownika) |
| – | Humming MXFP4 → INT8 z wykładnikiem E8M0 wtopionym w LUT (`0x03020100 << e`) | – | **nie dotyczy** (nie używamy MXFP4; dla gpt-oss MoE w ggml mnożenie skali i tak jest raz na blok 32) | – |
| – | subnormalny trik fp16 z #111 | – | **nie dotyczy**: nasze MMVQ to int8 `dot4` z aktywacjami q8_1, a „suma grup x” to dokładnie pole `s` w `block_q8_1`, które Q4_K/Q4_1 już wykorzystują | – |
| – | sonar #1788 all-reduce | – | **nie dotyczy**: jedno GPU; sm_120, P2P, TP=4. Gdyby kiedyś 2× 3090 bez P2P, wzorcem jest `allreduce_dma` z Maya v1.1.22 (copy engine + pinned host) | – |
| – | Maya WMMA BF16 hi/lo dla atencji | – | dotyczy sparse attention DSA (DeepSeek), nie naszego FA dla 16 warstw atencji Qwena; lekcja: hi/lo split daje ~16 bitów mantysy na WMMA BF16, gdyby kiedyś trzeba było precyzji fp32 na WMMA | – |

**Wniosek z Maya PR #382** (2× XTX, ROCm 7.2.4): batchowanie małych kernelików kwantyzacji w jeden launch nic nie dało, bo gap launchu wynosi 3.3 µs przy ~2 µs pracy. To niezależne potwierdzenie, że na gfx1100 zysk z fuzji małych kerneli zależy od przewidywanego gapu, a nie od liczby launchy. Nasza ścieżka PM4 replay tego problemu w ogóle nie ma.

**Qwen3.8-27B:** dotyczą nas #1–#3, czyli całe TTFT sesji agentów. Kernelowo nic nowego.

**LFM2.5:** #1–#3 dotyczą w mniejszym stopniu: wpis 53k to tylko 0.55 GB, a przywracanie zajmuje już ~230 ms.

**Flint:** nie dotyczy (bez zmian w kernelach) `[INFERENCE]`.

## 7. Do przetestowania

| test | jak | oczekiwany zysk | koszt | kill |
|---|---|---|---|---|
| T1: gdzie idzie 1.1 s przywracania `--cache-ram` | `LLAMA_CKPT_TIMING=1` + timery wokół `llama_state_seq_set_data_ext` (`server-task.cpp:1843`) na scenariuszu 16f E4 (sesja 53k → obce zapytanie → nowa sesja); porównać z teoretycznym pasmem pinned (`hipMemcpy` bench) | rozstrzyga #1 | 1 h GPU XTX | jeśli > 70% czasu to nie transfer H2D, odpuścić #1 |
| T2: pinned staging w prompt cache | wpis alokowany w pinned hoście (lub ring pinned) + `tensor_set_async` warstwami, jedna synchronizacja; md5 gate c4708318/6f14e814/894e56e4 | start sesji Qwena 1612 → ~800 ms | 1–2 dni + 1 h GPU | < −200 ms |
| T3: wpis „prefiks systemowy” | checkpoint GDN wymuszony na końcu promptu systemowego przy pierwszej turze sesji + osobny wpis z KV [0, P); replay omp z 3 podagentami | nowa sesja podagenta ~1.6 s → ≤ 0.5 s | 2–3 dni + 2 h GPU | < −500 ms lub zmiana md5 |
| T4: `prompt_cache_key` w eviction | trzymać mapę klucz → wpis; przy wyborze preferować wpis tej samej sesji; replay przeplotu 2 sesji + podagent | eliminacja re-prefillu 7–8 s w przeplocie | 1 dzień + 1 h GPU | brak przypadków z re-prefillem > 2k w replayu |
| T5: sufit AKV na transkryptach (CPU, $0) | z logów omp policzyć udział tokenów starych wyników narzędzi (poza ostatnimi 12) w kontekście tury, przy 32k/64k/100k | rozstrzyga #6: jeśli < 30% kontekstu, porzucić | 2 h CPU | udział < 30% |
| T6: hipBLASLt vs MMQ dla dużego prefillu | build z `GGML_CUDA_FORCE_CUBLAS` (cpuheavy) albo progiem; `llama-bench -p 2048,8192 -ub 2048` Qwen Q4_K_XL | −10…+15% pp (niepewne) | 1 build + 30 min GPU | pp8192 nie lepsze o ≥ 5% |
| T7: Humming baseline na 3090 (opcjonalny) | vLLM ≥ 0.29, `--linear-backend humming`, GPTQ-Int4 27B, batch 1 tg vs nasz cuda-topka | wiedza (nie zysk) | ~1 h Vast; wymaga pobrania wag na Vast (decyzja użytkownika) | – |

## 8. Do bazy wiedzy

- Nowe noty: [[humming]] (repo), [[sglang-hicache]] (repo), [[akv-cache-agentow]] (metoda), [[raport-60d-serving-kernels-cache]] (research).
- Aktualizacja [[project-maya]]: v1.1.21–1.1.26 (WMMA BF16 hi/lo, FAT_ROWS, all-reduce bez P2P, pomiar #382 na 2× XTX).
- sonar #1788 opisany w nocie raportu (bez osobnej noty: nie dotyczy).
- Rejestr [[ZRODLA]]: Humming `db930af`, HiCache (blog 2026-10, PR do #34798), AKV `c567a42`, sonar #1788 `f653ba4e`, Maya v1.1.26 `f26d8ba`.
- CompWatch: dodane `vllm-project/humming` (B), `thu-nics/AKV` (C), `dphnAI/sonar` (C); Maya, vLLM i SGLang już były.

## 9. Źródła

- Humming: https://vllm.ai/blog/2026-10-21-humming ; https://github.com/vllm-project/humming (`db930af`): `humming/dtypes.py:189-223`, `humming/schema/`, `humming/tune/base.py:14-31,95-96,234-239,304-376`, `humming/tune/sm8x.py`, `humming/include/humming/datatype/dequant_single.cuh:8-123`, `dequant_fused.cuh:8-76`, `benchmarks/results/4090/`; https://github.com/vllm-project/humming/issues/111
- HiCache: https://sglang.io/blog/hicache ; https://www.lmsys.org/blog/2026-08-11-unified-radix-cache/ ; https://www.lmsys.org/blog/2025-09-10-sglang-hicache/ ; PR https://github.com/sgl-project/sglang/pull/33639 , /30393 , /34798 , /21259
- AKV: https://arxiv.org/abs/2610.28577 ; https://arxiv.org/html/2610.28577 ; https://fuvty.github.io/thinking_yard_project_page/projects/akv/ ; https://github.com/thu-nics/AKV (`c567a42`): `akv/system/sglang/kernels/ops/attention/context_reposition.py`, `akv/system/sglang/srt/context_system/capabilities.py`, `akv/agent/policies/`, `akv/system/README.md`
- llama.cpp (lokalnie): `~/llama-master/tools/server/server-task.cpp:1722-1879` (`f61994f58`); `~/llama.cpp` (`b356fa262`): `src/llama-kv-cache.cpp:570-618,1193-1195,1914-1964`, `src/llama-memory-recurrent.cpp:188-246,336-345`, `src/llama-memory-hybrid.cpp:143-150`, `src/llama-model.cpp:2958-2962`, `tools/server/server-context.cpp:1185-1191` (IMROPE → brak shift)
- sonar: https://github.com/dphnAI/sonar/pull/1788 (`csrc/pcie_pull_all_reduce.cu`, `aphrodite/distributed/device_communicators/pcie_pull_all_reduce.py`); repo `11c991b7` `LICENSE`, `custom_all_reduce.py:252-264`
- Maya: https://github.com/mw00/project-maya/releases/tag/v1.1.21 … /v1.1.26 ; PR https://github.com/mw00/project-maya/pull/344 , /348 , /369 , /370 , /382 ; issue /410 ; kod @v1.1.26: `src/ds4/ds4_kernels.cu:1612,1810,3019,3246,3514`, `src/ds4/ds4_iq.cu:1290-1349`, `src/ds4/ds4_gguf.cu:912`, `tools/maya_quant/gptq.py`
- Nasze: [[2026-10-18-cache-promptu-agenta]], [[raport-38-ckpt-vram]], [[cache-sesji-na-dysku]], [[2026-10-19-kv-tylko-w-ram]], [[podrecznik-gpu]], [[mmvq-multikolumnowe]], [[wmma-small-n]], `~/KERNEL/qwen-opt/research/v2/rr-prefill-kv.md:224-244`
