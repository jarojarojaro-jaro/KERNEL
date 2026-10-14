# 07 — flashinfer-ai/flashinfer

Klon: HEAD `2895577` (2026-10-14), wersja 0.7.2. Sparse checkout: `include/flashinfer`, `csrc`, `docs`, wybrane pliki `flashinfer/*.py`. Nic nie budowane ani uruchamiane. Ścieżki `plik:linia` są względem korzenia repo. Liczby z repo to pomiary autorów (H100/B200), nie nasze. Kod forka cytuję jako `fork:` (`~/llama-master/ggml/src/ggml-cuda/...`).

## 1. Co to jest

Biblioteka kerneli do serwowania LLM (vLLM, SGLang, MLC). Zawiera attention (FA2 decode/prefill, warianty Hopper/Blackwell, MLA, XQA z TRT-LLM), cascade/merge stanów attention, sampling, top-k, normy, RoPE, MoE (TRT-LLM, CUTLASS, „monomoe”, MegaMoE), GDN/Mamba, komunikację. Licencja Apache-2.0. Repo jest bardzo aktywne (commit z dnia klonu). Kod jest tylko pod NVIDIA (sm75–sm121), kompilowany JIT. Duża część nowego kodu to wygenerowane `csrc/cake_*` pod sm90/sm100. Nie ma tu nic pod ROCm. Dla nas liczy się „klasyczny” rdzeń: `attention/decode.cuh`, `state.cuh`, `cascade.cuh`, `scheduler.cuh`, `sampling.cuh`, `pos_enc.cuh`, oraz dokument projektowy monomoe i XQA.

## 2. Kluczowe techniki (z dowodami)

### Attention decode
1. **GQA w decode: jeden blok na głowę KV, wszystkie głowy Q grupy w jednym bloku.** Wątki `(bdx = head_dim/vec, bdy = group_size, bdz)`, `qo_head_idx = kv_head_idx*bdy + ty` (`attention/decode.cuh:239,428`). Kafel K/V trafia do shared memory raz (cp.async, `decode.cuh:288-307, 503-527`) i czytają go wszystkie `bdy` głowy. Iloczyn qk to redukcja shfl po `bdx` lanes (`decode.cuh:83-89`).
2. **Maska liczona z indeksu, bez tensora maski**: `s = (iter_base+... < iter_bound && variant.LogitsMask(...)) ? s : -inf` (`decode.cuh:90-99`). W decode przyczynowość wynika z `kv_len`.
3. **Dla 1-bajtowego KV (FP8) mniej wątków**: 256 zamiast 512 przy grupie 8, „not enough registers” (`decode.cuh:635-645`). FP8 jest rozpakowywane po załadowaniu (`vec_dtypes.cuh:210-259`, programowy dequant w stylu Marlina: `__byte_perm` + maski + mnożenie przez bias wykładnika).
4. **Tensor cores dla dużych grup / wielu tokenów**: `use_tensor_cores=True` kieruje decode do kernela prefill z „packed” wierszami `qo_len × group` (`flashinfer/decode.py:1035-1037, 1115-1118`; q_len_per_req>1 wymaga tej ścieżki `decode.py:2148-2153`). Kafel Q dobiera `FA2DetermineCtaTileQ`: packed długość ≤16 → kafel 16, 17–64 → 64, czyli **jeden CTA i jedno przejście po KV** (`utils.cuh:432-440`). Przy D ≥ 512 jest „VO-split”, który połowi rejestry akumulatora O (`utils.cuh:418-424`).
5. **Split-KV + merge stanów (LSE).** `state_t{o,m,d}` i `merge` (`attention/state.cuh:28-84`), kernele merge (`cascade.cuh:220` MergeStates, `:374` PersistentVariableLengthMergeStates). Single decode nie dzieli przy `seq_len ≤ 256`. Dłuższe sekwencje dzieli na `max(ceil(seq/(max_grid/kv_heads)), 256)`, gdzie `max_grid` pochodzi z zapytania o occupancy (`decode.cuh:704-748`).
6. **Przyjazne dla CUDA graph**: rozmiar chunka czytany z pamięci urządzenia `*(params.kv_chunk_size_ptr)` (`decode.cuh:432`). Grid jest wypełniony do `max_grid/gdy` (`scheduler.cuh:444`). Z grafem split jest zawsze włączony (`scheduler.cuh:200-206`). Dzięki temu graf nie zależy od długości KV.
7. **Persistent „holistic” attention**: dwa runnery attention plus redukcja w jednym kernelu kooperacyjnym, z `grid.sync()` między fazami (`attention/persistent_template.cuh:76-91`, launch `persistent.cuh:697-707`). Przydział pracy liczy planner na hoście (`work_indptr`, `persistent.cuh:276`).
8. **XQA (TRT-LLM) multi-block: ostatni CTA scala wyniki w tym samym kernelu.** `atom.acq_rel.gpu.inc.u32` z wartością `nbSubSeq-1`: licznik sam wraca do 0, więc nie trzeba go resetować. Wynik `old == last` wybiera scalającego (`csrc/xqa/mha.cu:2756-2766`). Scalanie idzie w stałej kolejności `n = 0..nbSubSeq` (`mha.cu:2808-2831`), czyli deterministycznie.
9. **Cascade / shared prefix**: attention rozkładana na wspólny prefiks i unikalne sufiksy, potem merge. Autorzy podają „30x” przy dużym batchu i długim wspólnym promptcie (`docs/tutorials/recursive_attention.rst`, blog cascade-inference). To funkcja dla serwowania wielu żądań naraz.

### Fuzje wokół attention
10. **RoPE + kwantyzacja + zapis K/V do cache w jednym kernelu**, `blockIdx.y` dzieli pracę na Q-rope / K-rope / K-nope / V (`pos_enc.cuh:801-990`, `RopeQuantizeAppendPagedKVCache` `:1133`). Wariant z normą: operator `fused_qk_rmsnorm_rope_append_paged_kv_cache_bf16` (`csrc/cake_fused_qk_rope_append/*manifest.json`). Siatka Q/K/V jako typy bloków jest też w `norm/fused_qk_rmsnorm_rope.cuh:306-322`.
11. `QKRMSNormKernel`: norma per-head q i k jednym launchem (`norm.cuh:291`). `FusedAddRMSNorm` (`norm.cuh:414`).

### MoE
12. **Monomoe: cała warstwa MoE (routing → up+SiLU+requant → down → combine) w jednym trwałym kernelu** dla BS ≤ 8 (`docs/design_docs/monomoe_kernel.md:3-6`). Szczegóły:
    - `GRID_SIZE ≤ liczba SM`, jeden blok na SM, `__launch_bounds__(...,1)`. Gwarantuje to, że spinujący konsument nie czeka na nieuruchomiony blok (`:24-28, 448-454`).
    - **Routing replikowany w każdym bloku**, bez komunikacji między blokami (`:99-104`).
    - **Brak barier gridu**. Handoff up→down to „sentinel w danych”: komórka skali aktywacji służy jako flaga gotowości dla swojego segmentu (`:81-83, 185-195, 457-466`). Down→zapis używa liczników przybycia per pas kolumn (`:468-473`).
    - **Reset flag przez parytet launchu**: każdy blok inkrementuje własny licznik, zużywa stan bieżącego parytetu i zeruje stan drugiego w prologu. Działa przy replayu grafu bez resetu z hosta (`:475-483`, kod `csrc/fused_moe/monomoe/src/moe.cuh:75-109`).
    - Repo nie podaje liczb (jest tylko skrypt `benchmarks/bench_monomoe.py`). Implementacja wymaga sm90a (WGMMA/TMA).
13. „Distribution-aware MoE”: węzły warunkowe SWITCH w grafie CUDA wybierają ciało kernela według histogramu routingu (`fused_moe/da_moe.cuh:37-87, 654-700`).

### Sampling / top-k
14. **Sampling bez sortowania**: rejection sampling z pivotem, wersja „dual pivot”, w każdej rundzie zakres maleje ≥2x (`sampling.cuh:859-981` top-k, `:992-1110` top-p). Blog z dowodem poprawności rozkładu: https://flashinfer.ai/2025/03/10/sampling.html.
15. **Gumbel-max z logitów w jednym przejściu** (argmax(logit + Gumbel), bez softmaxu) (`sampling.cuh:744-789`).
16. **Chain speculative sampling na GPU** (akceptacja u·p<q plus próbkowanie z relu(q−p)) (`sampling.cuh:1888-2005`).
17. Radix top-k na wielu CTA z programową barierą. Lekcja z `topk.cuh:196-204` (issue #3610): stan bariery może zerować tylko **ostatni CTA, który wychodzi**. Zerowanie przez „lidera” zawieszało strumień.

### GDN (Qwen3.8 ma 48 warstw GDN)
18. **ReplaySSM**: weryfikacja nie zmienia checkpointu, a po akceptacji jeden launch `replayssm_commit` dla wszystkich warstw przelicza tylko przyjęty prefiks (`docs/api/gdn_decode.rst:20-33`, `flashinfer/gdn_decode.py:1205-1223`). Jest też „BF16 fast path” stanu dla K=V=128 (`gdn_decode.py:536-563`).
19. Fused GDN decode (sm120): b/a GEMV + conv + GDN w jednym trwałym kernelu. Bariera z licznikiem generacji, która sama się resetuje (`flashinfer/gdn_kernels/experimental/kernel/gdn_fused_decode_sm120.cu:116-133`). Wiersze stanu fp32 są prefetchowane **przed** barierą, żeby latencja nakładała się na fazę gemv/conv (`:135-140`).
20. PDL (programmatic dependent launch) jest wszędzie (`decode.cuh:791-803`).

## 3. Przeniesienie na AMD/HIP/RDNA3

| # | Technika | Na gfx1100 | Co się nie przeniesie |
|---|---|---|---|
| 1 | Kafel K/V współdzielony przez głowy grupy GQA | Tak, wprost. LDS zamiast smem, `ds_swizzle`/DPP zamiast `shfl_xor`, zwykłe (buffer) loady do rejestrów albo LDS zamiast cp.async. Fork już to ma dla q4_0 w `fattn-kvq` (WMMA, tokeny×głowy spakowane w 16 kolumn, `fork: fattn-kvq.cu:5-24`). **Brakuje dla q8_0** (LFM) i dla generycznego `flash_attn_ext_vec`. | cp.async/multistage: na RDNA3 nie ma kopii asynchronicznej, pipelining robi się rejestrami (ładowanie kafla i+1 przed liczeniem i). |
| 2 | Maska z indeksu | Tak: kernel zna `kv_len` i pozycje tokenów Q, maska przyczynowa to porównanie. | llama.cpp zakłada tensor maski (wiele sekwencji, SWA, dziury w komórkach), więc potrzebna jest flaga i ścieżka awaryjna. |
| 3 | Mniej wątków dla 1-bajtowego KV | Na RDNA3 przekłada się na dobór `waves_per_eu`/`launch_bounds` w wariancie q8_0 (VGPR). | — |
| 3' | Dequant 8-bit → f16 bitowo | q8_0 (int8 + skala): trik „magic number” `(x ^ 0x80) | 0x6400` jako f16 minus 1152, przez `v_perm_b32` (`__builtin_amdgcn_perm`) i `v_pk_add_f16`/`v_pk_fma_f16`. Alternatywa bez dequantu: **WMMA iu8** dla KQ (patrz P1b). | FP8 e4m3: na gfx1100 brak FP8, nieistotne. |
| 4 | Jedno przejście po KV dla packed ≤64 wierszy | Tak, ale przy D=256 akumulator VKQ fp32 to 128 VGPR na wave na 16 kolumn (`fork: fattn-kvq.cu:267`). 32 kolumny wymagają VO-split między dwa wave'y (jak `utils.cuh:418-424`). | — |
| 5 | Merge stanów LSE | Fork ma to (`flash_attn_combine_results`, osobny launch, `fork: fattn-kvq.cu:569-577`). | — |
| 6 | Chunk z pamięci urządzenia, grid stały | Tak, ale u nas zysk mały: graf llama.cpp i tak przebudowuje się co 256 tokenów KV. | — |
| 7 | Kooperacyjny kernel attention+reduce | `hipLaunchCooperativeKernel` jest. U nas tańszy jest ticket „ostatni blok” (zmierzone ~1 µs ogona, `lfm-decode-round2.md:36-37`). | Przy batchu 1 nie ma czego balansować. |
| 8 | Ostatni CTA scala, licznik z zawijaniem | Tak: HIP `atomicInc(addr, n-1)` → `global_atomic_inc`, które zawija do 0 (ta sama semantyka co `atom.inc` w PTX). Acquire/release: `__hip_atomic_fetch_add(..., __ATOMIC_ACQ_REL, __HIP_MEMORY_SCOPE_AGENT)`. | — |
| 9 | Cascade | Brak zastosowania przy jednym użytkowniku. Weryfikacja MTP (5 tokenów) to już jeden kafel w kvq. | Cały sens to batch wielu żądań ze wspólnym prefiksem. |
| 10 | Norma + RoPE + kwant + zapis KV jednym launchem | Tak, 1:1. Siatka z `blockIdx.y` = {Q, K, V}, w K dochodzi kwantyzacja do q4_0/q8_0 (+FWHT u nas). Wyniki per element mogą zostać bitowo te same. | FP8 → u nas q4_0/q8_0, bloki 32 = jedna fala (redukcja max |x| po 32 lanes przez DPP). |
| 12 | Monokernel MoE: trwały grid, handoffy przez dane, reset przez parytet | Tak, logika synchronizacji jest przenośna: atomiki z scope agent, `s_sleep` w spinie, grid ≤ rezydentne bloki. **Skala bloku q8_1 (`d`) może pełnić rolę sentinela** dokładnie jak „act_scale” w monomoe. Zmierzone u nas: bariera w małym trwałym gridzie 0.5–0.8 µs, granica kernela 2.53 µs (`lfm-decode-round2.md:27-31`). | WGMMA/TMA/mbarrier: zamiast nich nasze MMVQ (dp4a/buffer loads) w pętli grid-stride. Ryzyko: występujący u nas „spinujący czekający głodzą producentów” przy dużych fazach (`lfm-decode-round2.md:33-36`). Monomoe omija to przez 1 blok/SM i brak dużej liczby czekających. |
| 13 | Warunkowe węzły grafu | W ROCm 10.0 brak conditional nodes w `hip_runtime_api.h` (grep: brak). | Nie przenosi się. |
| 14-16 | Sampling bez sortowania, Gumbel, chain spec. sampling | Tak (wave32 scan/reduce przez DPP). | Wynik jest dokładny co do rozkładu, ale **nie bitowo** zgodny z samplerem CPU llama.cpp (inne zużycie RNG). Fork trzyma się bitowej zgodności, a `-bs` nic nie dało (NOTES:216). |
| 17 | Reset bariery tylko przez ostatni wychodzący CTA | Tak. Dotyczy naszych ticketów (NORM_ROUTER, INPROJ_CONV, MOE_DOWN_REDUCE). | — |
| 18 | ReplaySSM | To nasz S4 (GATED_DELTA_NET_LAG). Nasz wariant jest lepiej zintegrowany: replay wchodzi do następnej weryfikacji, nie ma osobnego launchu commit. | — |
| 18' | Stan GDN w BF16 | Technicznie trywialne (`v_cvt` / pk bf16 na gfx11). | Zmienia numerykę rekurencji, wymaga KLD. |
| 19 | Prefetch stanu przed barierą | Tylko w kernelu trwałym. U nas „prefetch w GDN/FA” już nie zadziałał (NOTES:324). | — |
| 20 | PDL | **Nie ma**: w ROCm 10.0 jest tylko enum `hipGraphDependencyTypeProgrammatic` (`hip_runtime_api.h:2109-2116`), bez atrybutu launchu i bez symbolu w `libamdhip64.so` (strings: brak `Trigger...`). Na RDNA3 odpowiednikiem pozostają fuzje i kernele trwałe. | — |

## 4. Pomysły dla nas

Kolejność według wartość/koszt. Zyski to `[SZACUNEK]` z naszych zmierzonych kosztów (2.53 µs/granicę, profile rocprofv3 z `lfm-decode*.md`).

### P1. LFM: decode attention dla KV q8_0 z kaflem K/V współdzielonym przez 4 głowy Q (wzorzec `decode.cuh`)
Problem jest zmierzony: q8_0 idzie przez `flash_attn_ext_vec`, który czyta K/V raz na każdą z 4 głów Q. Przy 98k to +2.38 ms/token wobec +0.89 ms dla q4_0 kvq, ~450 GB/s (`lfm-decode-round2.md:87-91`, NOTES:354).
- **P1a (bitowy).** Przebudować `fattn-vec.cuh` na układ FlashInfer: blok = głowa KV, `bdy` = 4 głowy Q. Kafel K/V (q8_0) idzie do LDS/rejestrów raz, każda głowa liczy dokładnie tak jak dziś: ten sam mapping wątków per głowa, ten sam podział `parallel_blocks`, Q w q8_1, dp4a. Dowód wykonalności układu: `decode.cuh:239, 288-307, 62-118`.
- **P1b (szybszy, zmienia numerykę).** Instancja q8_0 w `fattn-kvq.cu` z **WMMA iu8 dla KQ**: K zostaje int8 bez dequantu, Q kwantowane do int8 per 32 (jak q8_1 w vec), `v_wmma_i32_16x16x16_iu8` ×2 na blok 32, potem `acc_f32 += float(i32) * d_k[wiersz] * d_q[kolumna]`. Część całkowita iloczynu jest identyczna z dp4a w vec, różni się tylko kolejność sum float. PV w f16: V dequantowane trikiem magic-number (tabela, wiersz 3'). `[WNIOSEK]`: to nie jest technika FlashInfer, wynika z ich podziału „dequant w rejestrach, tensor cores dla dużej grupy”.
- Zysk: 98k −0.85…−1.1 ms/token (+12…+19% t/s przy tej głębokości), 32k ~−0.3 ms, 0–8k ≤0.07 ms. Oszacowanie z przepustowości kvq q4_0 ~640 GB/s na 1070 MB, zgodne z `lfm-decode-round2.md:95-101`.
- Koszt: P1a 2–3 dni, P1b 3–5 dni (szkielet kvq istnieje). Ryzyko: P1a niskie (bitowo), P1b decyzja użytkownika co do KLD.
- Pomiar: `llama-bench -fa 1 -ctk q8_0 -ctv q8_0 tg128 -d 0,8192,32768,98304`, rocprofv3 `flash_attn_*` µs/call, hash logitów (`lh.sh`) dla P1a.

### P2. LFM: warstwa MoE w jednym trwałym launchu (wzorzec monomoe)
Dziś warstwa MoE to 4 launche: `norm_router_topk` → gate+up(SwiGLU) → `quantize_q8_1` → down+reduce+res (`lfm-decode-round2.md:64-65`), czyli 38 warstw × 3 granice. Projekt:
- Grid 96–192 bloków (1–2/CU), `__launch_bounds__` + sprawdzenie rezydencji.
- Faza A: norma (bloki liczą skalę jak dziś) + 64 wiersze routera rozdzielone na bloki. Każdy logit publikowany z flagą.
- **Każdy blok sam liczy top-4 z 64 logitów** (replikacja jak w monomoe Phase 1, `monomoe_kernel.md:99-104`). Znika bariera i ticket.
- Faza B: gate+up+SwiGLU w pętli grid-stride po (ekspert, wiersze), zapis od razu w q8_1. **Skala `d` bloku q8_1 jako sentinel gotowości** (monomoe site #2).
- Faza C: down + ważenie + residual per wiersz wyjścia (obecny MOE_DOWN_REDUCE, deterministyczny, bez atomików). Spin na `d` 48 bloków swojego eksperta.
- Flagi double-buffer przez parytet launchu (`moe.cuh:75-109`), więc bez resetów.
- Zysk: −114 granic −38 launchy quantize ≈ 0.25–0.4 ms/token (6–10%), jeśli MMVQ w trybie grid-stride utrzyma ~700 GB/s. Bitowo możliwe, bo każda suma wiersza zostaje w tej samej kolejności.
- Koszt 1–2 tyg., ryzyko wysokie: bajty w locie na wave przy mniejszej liczbie bloków, głodzenie przez spin. Zmierzone u nas: 1024 bloki zawodzą, 96–192 kosztuje 0.5–0.8 µs/fazę.
- Etap 0 (2–3 dni): tylko B→C (gate+up z q8_1 + down+reduce w jednym launchu z sentinelami). Usuwa 76 launchy/token i weryfikuje model kosztu, zanim ruszy się routing.
- Pomiar: rocprofv3 `tok.py` (kernele/token, µs/token), `ab.sh` tg128, hash logitów.

### P3. Prolog attention jednym launchem (wzorzec `RopeQuantizeAppendPagedKVCache` / `fused_qk_rmsnorm_rope_append`)
LFM na warstwę attention: `rms_norm_mul_rope`(q), `rms_norm_mul_rope`(k), `fwht`(v), `set_rows` K, `set_rows` V, czyli 5 launchy (`lfm-decode.md:66-68`, czasy w `lfm-decode-round2.md:58-61`). Wersja zfuzowana: jeden grid, `blockIdx.y ∈ {Q-głowy, K-głowy, V-głowy}`, w K/V kwantyzacja q8_0/q4_0 i zapis pod `kv_idx` (+FWHT w tym samym kernelu, już robione w fuzji Qwena).
- Zysk: LFM −40 launchy/token. Model 2.5 µs/granicę daje ~0.1–0.15 ms, ale uwaga: usunięcie 10 quantize przy FWHT dało szum (`lfm-decode.md:169-170`), więc realnie 0.03–0.15 ms (1–3%). Qwen −64 launchy/weryfikację (16 warstw), ~0.1–0.2 ms/krok.
- Koszt 2–3 dni, bitowo. Pomiar jak P2. Najpierw połowa tańsza: K-rope+set_rows K i V-fwht+set_rows V.

### P4. Combine split-KV w kernelu FA (wzorzec XQA multi-block)
`flash_attn_combine_results` to osobny launch na warstwę (`fork: fattn-kvq.cu:569-577`, 1.86 µs/call, `lfm-decode-round2.md:61`). Ostatni blok danej (głowy, tokenu) wybrany przez `atomicInc(sem, nsplit-1)` (zawija do 0, bez resetu, `mha.cu:2756-2766`) scala partiale w kolejności splitów 0..n-1, tą samą arytmetyką co dzisiejszy combine, więc bitowo.
- Zysk: LFM −10 launchy ≈ 30–40 µs/token (~1%). Qwen −16/weryfikację ≈ 50 µs (~0.2%).
- Koszt ~1 dzień. Robić razem z P1 (ten sam plik).

### P5. Maska przyczynowa liczona w kernelu FA dla jednej sekwencji (wzorzec `decode.cuh:90-99`)
NOTES:281 szacuje przyrostową maskę KQ na ~0.65 ms/krok przy 94k i jej nie zrobiono. Lepiej nie budować maski wcale: gdy komórki KV jednej sekwencji są ciągłe i `pos == idx` (T1 już wykrywa przypadek jednej sekwencji, NOTES:328), host ustawia flagę. Wtedy kvq/vec liczy `kv_idx ≤ pos_q[j]` i nie czyta maski. Ścieżka awaryjna to zwykła maska.
- Zysk: Qwen przy 94k do ~0.6–0.7 ms/krok (~2%): budowa na CPU + H2D ~1.5 MB + odczyty maski w 16 warstwach. LFM przy 98k ~0.05–0.1 ms/token.
- Koszt 2–3 dni (wejście grafu w llama.cpp + FA). Ryzyko: poprawność przy nieciągłych komórkach (seq_rm/rollback). Pokryć testem `greedy_check.sh` z cofaniem draftów i cache promptu.
- Pomiar: `long_ctx_bench` 29.5k/94k ms/krok, perf CPU `set_input`.

### P6. kvq: jedno przejście po KV dla 17–32+ kolumn (Qwen: 5 tokenów × GQA 6 = 30 kolumn = 2 kafle)
Dziś `ntiles_x = ceil(30/16) = 2` osobne bloki czytają i dequantują ten sam KV (`fork: fattn-kvq.cu:531-555`). FlashInfer wybiera wtedy kafel 64, czyli jedno przejście (`utils.cuh:432-440`). Przy D=256 trzeba VO-split, bo 2×128 VGPR akumulatora się nie mieści: dwa wave'y dzielą D, P idzie przez LDS.
- **Najpierw pomiar zerowym kodem**: rocprofv3 `flash_attn_ext_kvq` µs/call przy 94k dla n=1 (1 kafel) vs n=5 (2 kafle). Jeśli n=5 ≈ 2× n=1, kernel jest ograniczony L2/VALU i warto. Jeśli ≈1×, drugi kafel trafia w L2 i nie ma czego brać.
- Zysk 0–0.9 ms/krok przy 94k `[SZACUNEK]`. Koszt 3–5 dni. Ryzyko średnie (rejestry, bitowa zgodność z obecnym kvq raczej stracona).

### P7. Higiena ticketów/barier (tanie, poprawność)
- Liczniki przez `atomicInc` z zawijaniem (XQA) albo parytet launchu (monomoe) zamiast zapisu zerującego.
- Reset tylko przez ostatni wychodzący blok (`topk.cuh:196-204`, issue #3610).
- Sprawdzić NORM_ROUTER / INPROJ_CONV / MOE_DOWN_REDUCE pod kątem tej klasy wyścigu: zawieszenie strumienia przy replayu grafu.

### P8. Niski priorytet / tylko jeśli profil wskaże
- **Sampling na GPU** (dual pivot, Gumbel-max, chain spec. sampling): dla nas brak zysku. Host sample+accept to już 140 µs (NOTES:278), `-bs` bez efektu, a wynik nie jest bitowy z CPU. Wartość tylko jako warunek wstępny do pętli „token nie wraca na host” (lily, raport 05). Wtedy `ChainSpeculativeSampling` (`sampling.cuh:1888-2005`) jest gotowym wzorem akceptacji na GPU.
- **Prefiltr top-k na GPU dla wierszy weryfikacji**, żeby łańcuch CPU pozostał bitowy (top-k pierwszy w łańcuchu). Oszczędza D2H 5×248k float (~5 MB) na krok, ale tylko jeśli ten transfer jest na ścieżce krytycznej. Najpierw rocprof/strace.
- **Stan GDN w BF16** (`gdn_decode.py:536-563`): ~150 MB mniej ruchu na weryfikację, ≈0.15–0.2 ms/krok. Zmienia numerykę rekurencji (KLD, długie konteksty). Raczej nie.

### Outside the box
- **Sentinel w skali q8_1 jako uniwersalny handoff**. Każdy producent, który już pisze q8_1 (A6, Q8_IDS, CONV_MUL), może publikować „gotowe” przez `d ≠ sentinel`. Konsument w tym samym launchu spina tylko na blokach, których potrzebuje. To zamienia „ostatni blok + ticket” na drobnoziarnisty przepływ danych w kernelach z P2/P3.
- **Merge LSE jako narzędzie fuzji**: K/V bieżących tokenów (jeszcze w f16 z projekcji) mogą wejść do attention z rejestrów, a stary KV z cache. Wtedy `set_rows` nie blokuje FA i może być ogonem kernela. Zmienia numerykę (bieżące tokeny niekwantowane), więc tylko jako opcja.

## 5. Krytyka

- Rdzeń decode FlashInfer (FA2, CUDA cores dla grupy ≤8) jest **prostszy niż nasz `fattn-kvq`**. Fork już ma WMMA, KV q4_0 czytany wprost i pakowanie tokeny×głowy. Wartość dla nas leży w konkretnych wzorcach (GQA-shared tile dla q8_0, maska z indeksu, scalanie przez ostatni CTA, monokernel MoE), nie w wydajności kerneli.
- Większość nowego kodu (TMA, tcgen05, WGMMA, clusters, PDL, FP4/FP8, wygenerowane `cake_*`, MegaMoE, komunikacja) jest specyficzna dla sm90/sm100. Na RDNA3 przenosi się co najwyżej idea.
- Cascade „30x” i „sampling −50% czasu” to liczby dla batch-serving na H100 (vLLM). Przy jednym użytkowniku nieistotne.
- Monomoe: brak opublikowanych liczb w repo, stały kształt (E=256, N=512, K=2048, FP8 block). Projekt synchronizacji jest dobrze opisany, ale wydajność niepotwierdzona.
- Holistic persistent attention balansuje batch o zmiennych długościach. Przy batchu 1 nic nie daje.
- ReplaySSM to to samo co nasz S4. Ich osobny launch commit jest gorszy od naszego replayu wewnątrz następnej weryfikacji.
- Sampling rejection jest dokładny co do rozkładu, ale nie bitowy. Ta ścieżka już raz nie dała zysku (`-bs`).

## 6. Werdykt

**Średnia.** Brak gotowych kerneli pod RDNA3, a nasz kvq jest już dalej niż decode FlashInfer. Repo daje jednak sprawdzone wzorce na trzy otwarte problemy: q8_0 FA dla LFM (P1, do +19% przy 98k), redukcję launchy MoE przez monokernel z sentinelami (P2) oraz tanie fuzje prologu attention, combine i maski (P3–P5).
