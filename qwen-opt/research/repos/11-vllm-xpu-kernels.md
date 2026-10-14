# 11. vllm-project/vllm-xpu-kernels: kernele vLLM na Intel GPU (SYCL)

Klon: `--depth 1`, HEAD `6b30c9b9` (2026-10-14). Ścieżki niżej są względne do korzenia repo. Odwołania do naszego kodu: `~/llama-master/ggml/src/ggml-cuda/...`.

## 1. Co to jest

Biblioteka custom opów PyTorch dla backendu XPU w vLLM: Intel Arc B (Xe2, „BMG”), Data Center Max (PVC) i Xe3. Kod to SYCL/DPC++ plus CUTLASS-SYCL (cute). Gęste GEMM-y (int4/fp8/fp4) idą przez oneDNN (`csrc/xpu/onednn/*`). Repo jest bardzo aktywne: 404 commity, pierwszy 2025-07, ostatni push w dniu analizy, 90 otwartych issues i PR razem (licznik GitHub API), licencja Apache-2.0 (pliki CUTLASS: BSD-3). W repo nie ma żadnych opublikowanych wyników wydajności. Katalog `benchmark/` zawiera tylko skrypty, bez CSV i bez liczb. Z tego powodu każda ocena zysku w tym raporcie jest moja.

Model wykonania Intela jest inny niż nasz. Subgrupy mają SIMD16/32. Instrukcja DPAS ma zmienną liczbę wierszy M od 1 do 8 („repeat count”), N=16 i K=16 (bf16) albo 32 (int8). Są sprzętowe ładowania 2D bloków z prefetchem do cache i tryb „GRF 256” (więcej rejestrów kosztem obłożenia).

## 2. Kluczowe techniki (z dowodami)

### 2a. Decode attention (paged, split-KV)
- **GQA w wymiarze M.** Głowy Q jednej grupy KV są pakowane w wiersze kafla (`qgroup` 8 albo 16), więc K/V są czytane raz na głowę KV. Dowody: `csrc/xpu/attn/xe_2/kernel/paged_decode_kernel.hpp:283-286`, `csrc/xpu/attn/kernel_configs/paged_decode_default.conf:19-23`. Atom MMA ma postać `XE_DPAS_TT<gcd(SGTileQ,8)>` (`csrc/xpu/attn/xe_2/paged_decode.hpp:504-507`): M=8 pasuje do GQA≤8 bez marnowania wierszy.
- **Split-K z osobnym kernelem redukcji** `ReduceSplitK` (`paged_decode_kernel.hpp:547-878`, uruchamiany osobno w `paged_decode.hpp:453-471`). LSE scalane przez SLM i `reduce_over_group` (`:806-858`).
- **„Group split-K”** (`docs/group_split_kv_design.md`). Plan podziału liczy host (Python) z `kv_lens` i wysyła listę zadań `(seq, tile_start, tile_count, split)`. Siatka ma wtedy dokładnie `total_wgs × heads_kv`, bez pustych WG. Heurystyka: `min_wgs = 2·xe_cores/heads_kv`, `target_tiles_per_wg = max(4, total/min_wgs)`, podział bez dzielenia sekwencji krótszych niż 32/128 kafli (§3). Zysk dotyczy batchy o mieszanych długościach.
- **KV fp8 ze skalą per tensor.** Skala K jest wliczona w skalę softmaxu, skala V jest mnożona raz po pętli, a w pętli zostaje tylko konwersja typu. Dowody: `csrc/xpu/attn/xe_2/collective/chunk_prefill_mainloop.hpp:1227-1238`, `:1368-1374`.
- **Prefetch.** Prefetch V przed GEMM2 i prefetch K następnej strony po GEMM2 (`chunk_prefill_mainloop.hpp:1266-1267`, `:1360-1363`).
- **Maska końcówki K bez gałęzi.** Wynik to `fmin(S, NaN lub -inf)` (`:1308-1321`).
- **Xe3 „full fp8”.** P jest przesunięte o +8 w wykładniku (×256), żeby zmieściło się w zakresie fp8 do GEMM P·V. Suma wierszy jest liczona per lane, a redukcja pozioma jest odłożona do epilogu (`csrc/xpu/attn/xe_3/collective/chunk_prefill_mainloop.hpp:857-889`).

### 2b. Gated DeltaNet (bezpośrednio nasza architektura)
- **Decode i spec-decode, rekurencja na rdzeniach skalarnych.** WG ma 256 wątków. Subgrupa 32 trzyma 4 wiersze V, a każda lana 4 elementy K (128/32). Na każdy token przypadają redukcje `reduce_over_group` dla `kv` i `o` (`csrc/xpu/gdn_attn/gated_delta_rule.hpp:7-15`, `:139-236`). Stan w pamięci może być **fp32, bf16 albo fp16**, a obliczenia idą zawsze w fp32 w rejestrach (`gated_delta_rule.hpp:804-833` `DISPATCH_STATE_DTYPE`, testy `tests/gdn_attn/test_gated_delta_rule.py:334`).
- **Starszy spec kernel zapisuje pełny stan po każdym tokenie draftu** (`gated_delta_rule.hpp:277-291`). To podejście my już porzuciliśmy (S4).
- **RecoverSSM / `--use-replayssm`** (`csrc/xpu/gdn_attn/gated_delta_rule_recoverssm.hpp:10-28`, `:172-283`). Stan jest tylko czytany. Dla każdego tokenu kernel zapisuje rekord fp32 `[corr = (v − Sᵀk)·β (po decay) | k znormalizowane | decay]`. Commit przyjętego prefiksu to wtedy same aktualizacje rangi 1, `S = decay·S + k·corrᵀ`, bez liczenia `Sᵀk`. Commit robi vLLM osobno po próbkowaniu (`gdn_attn_interface.cpp:630-632`).
- **Prefill w chunkach (FLA/WY) na DPAS** (`csrc/xpu/gdn_attn/xe_2/chunk_gated_delta_rule_kernels_xe2.hpp`). Chunk ma 64 tokeny (`gdn_attn_utils.h:8`). Pięć kernerli:
  1. cumsum log-decay;
  2. `A = β·KKᵀ ⊙ maska decay` (MMA 64×64);
  3. odwrotność `(I+A)⁻¹` blokami 16×16: bloki diagonalne przez podstawianie w rejestrach, pozadiagonalne przez łańcuch GEMM 16×16 (`:391-690`);
  4. `W`, `U`;
  5. jeden kernel na (sekwencja, głowa V), który sekwencyjnie po chunkach liczy `U −= W·S`, wyjście `O = (Q·S)⊙e^g + mask(QKᵀ)·U` oraz aktualizację stanu. `W·S` i `Q·S` dzielą jedno ładowanie `S` (`:884-1231`, fuzja `:1108-1126`).

  Kernel działa w trybie `grf_size<256>` (`:1287-1289`). Na PVC autorzy omijają błąd dokładności MMA i liczą odwrotność skalarnie (`:1386-1414`).
- **Conv1d spec.** Okno stanu ma długość `(W−1) + num_spec`, a start wynika z `num_accepted−1` (`csrc/xpu/gdn_attn/causal_conv1d.hpp:477-485`). Ten sam kernel rozdziela q/k/v/z/b/a i przestawia je przez `token_indx`. To jest równoważne naszemu T1 i A5.

### 2c. MoE
- **Potok bez fuzji:** `remap_hidden_states` → grouped GEMM1 → aktywacja → grouped GEMM2 → `moe_gather` (ważenie). Do tego `masked_fill` i alokacje w Pythonie (`vllm_xpu_kernels/fused_moe_interface.py:360-502`).
- **Grouped GEMM z trwałym schedulerem** po kafelkach wszystkich ekspertów. `rows_per_expert` jest czytane na GPU, więc host nie synchronizuje się z urządzeniem (`csrc/xpu/grouped_gemm/collective/gemm/moe_tile_scheduler.hpp`). Kafel M wybiera średnia liczba wierszy na eksperta: ≤4 daje M=8, ≤8 daje M=16, ≤128 daje M=32, więcej daje 256 (`csrc/xpu/grouped_gemm/xe_2/grouped_gemm_xe2_interface.hpp:239`, `:357-368`).
- **int4 u4→s4 przy ładowaniu.** Punkt zerowy jest wpisany w kodowanie, więc kernel nie odejmuje zp (`fused_moe_interface.py:156-184`).

### 2d. Normy, RoPE, zapis KV
- **qk-norm + RoPE: jedna subgrupa na (token, głowa).** Partner NeoX jest pobierany przez `permute_group_by_xor` (`csrc/fused_qknorm_rope.cpp:137-144`). Przy ≥20 głowach jedna subgrupa obsługuje 8 głów, przy ≥8 głowach 4 (`:407-417`).
- **Fuzja Q-RMSNorm + RoPE + zapis do KV cache (bf16/fp8)** w jednym kernelu, subgrupa na (token, głowa). Kwantyzacja fp8 ze skalą potęgi 2 liczoną operacjami na bitach (`csrc/xpu/sycl/deepseek_qnorm_rope_kv_insert.cpp:1-50`). Ten wzorzec rozciąga też `fused_kv_compress_norm_rope_insert_sparse_attn.cpp:4-11`: kompresja + norma + RoPE + kwantyzacja + zapis w jednym przejściu.
- **RMSNorm wielowierszowy** przy małym `hidden` (np. normy q/k, head_dim 128). Kilka wierszy trafia do jednej WG, a redukcja idzie przez `shift_group_left` (`csrc/layernorm.cpp:276-391`, `:489-500`).

### 2e. Sampler
Top-k/top-p bez sortowania. Pivot top-k jest szacowany ze średniej i odchylenia logitów (tabela percentyl→σ), potem kernel zbiera tylko elementy odstające. Próg top-p szuka metoda regula falsi w wariancie Illinois (`csrc/xpu/sampler/topk_topp_sampler_kernels.hpp:7-10`, `:445-449`, `:912-980`).

### 2f. GEMV kwantyzowany
Repo **nie ma własnego GEMV/MMVQ**. Liniowe w4a8/w4a16/fp8 idą przez prymitywy oneDNN z cache LRU (`csrc/xpu/onednn/int4_gemm_w4a8.h`, `lru_cache.h`). Nasze główne wąskie gardło (pasmo MMVQ) nie ma tu odpowiednika.

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika Intela | Odpowiednik na gfx1100 | Co się nie przenosi |
|---|---|---|
| DPAS M=1..8 + pakowanie GQA | WMMA 16×16×16 ma stałe M=16. Pakujemy tokeny×głowy do 16 kolumn i robimy to już w `fattn-kvq.cu:5-24`. | Przy GQA 4 i 1 tokenie (LFM) Intel marnuje mniej wierszy niż my. Decode jest jednak ograniczony pamięcią, więc to bez znaczenia. |
| `reduce_over_group` (SIMD32) | DPP `row_shr` / `row_bcast` + `v_permlanex16`. Nasze kernele już tak robią. | — |
| `permute_group_by_xor` (partner RoPE) | `ds_swizzle` / DPP `row_xmask` (gfx10+) | — |
| Ładowania 2D + prefetch do cache | `buffer_load` z deskryptorem w SGPR i wczesne ładowanie następnego kafla do VGPR (`fattn_kvq_load` z `k0_next`) | gfx11 nie ma instrukcji prefetchu do L2 (`s_prefetch_data` jest od gfx12), a sprzętowego bloku 2D nie ma wcale. |
| `grf_size<256>` | Budżet VGPR przez `amdgpu_waves_per_eu` / `__launch_bounds__`. Już stosujemy (K1). | — |
| Wliczenie skali fp8 per tensor w skalę softmaxu | Działa tylko przy skali per tensor albo per token. Nasze q4_0/q8_0 mają skalę na 32 elementy wzdłuż head_dim, więc w pętli trzeba mnożyć per blok. Dziś robimy to jednym `v_pk_fma` na 2 elementy (`fattn-kvq.cu:305-307`), co i tak jest tanie. | Ścieżka fp8 i bias P +8: RDNA3 nie ma fp8. Wariant u8-P × int8-V przez iu8 WMMA nie działa, bo skala V zmienia się wzdłuż wymiaru kontrakcji (pozycje KV). |
| Odroczona suma wierszy softmaxu | Już mamy w `fattn-kvq.cu:434` (`KQ_sum` sumowane przez połówki fali na końcu). | — |
| Plan split-K liczony na hoście | U nas jest jedna sekwencja. Heurystyka „2×CU” jest identyczna (`fattn-kvq.cu:541`). | Cała reszta służy batchom serwerowym. |
| Stan GDN w bf16/fp16 | Ładowanie fp16 → `v_cvt_f32_f16` → rekurencja fp32 → zapis fp16. Koszt VALU pomijalny. | — |
| Rekord replay GDN `(corr, k, decay)` | Ten sam format w naszych wierszach oczekujących (`gated_delta_net.cu:262-281`), replay bez redukcji (`:138-145`). | — |
| Chunked GDN na DPAS | Te same GEMM-y na WMMA f16 z akumulacją f32. Odwrotność bloków 16×16 dokładnie pasuje do WMMA 16×16×16. | Intel ma GRF 256 (64 KB rejestrów na wątek sprzętowy). U nas jest LDS 64 KB/CU i VGPR 1536/SIMD, więc stan S 128×128 trzeba kafelkować w LDS albo, jak u Intela, czytać z globalnej pamięci (L2) przy każdym chunku. |
| Grouped GEMM: kafel według średniego M | Dotyczy MMQ `mul_mat_id` w prefillu LFM. Przy 4096 tokenach ×4/64 wychodzi ok. 256 wierszy na eksperta, czyli duże kafle i tak są właściwe. | — |

## 4. Pomysły dla nas

Liczby ms/krok to `[SZACUNEK]`, chyba że zaznaczono inaczej. Bazy: Qwen 28.9 ms/krok, LFM 4.10 ms/token, granica kernela w grafie HIP 2.53 µs (pomiar z `lfm-decode-round2.md` §1).

**P1. Stan GDN w fp16 (opcja `LLAMA_GDN_STATE_F16`), obliczenia dalej w fp32.**
- Co: `gated_delta_net.cu` czyta i zapisuje `s_shard` jako `half`. Do tego bufor stanu w `llama-memory-recurrent` jako F16 i op CPU dla testów. Wiersze oczekujące S4 zostają w fp32.
- Uzasadnienie: stan Qwena to 48 głów V × 128 × 128 × 4 B = 3 MiB na warstwę. W lag/replay czytamy i zapisujemy go raz na weryfikację: 48 × 6 MiB ≈ 302 MB/krok. GDN kosztuje 638 µs/weryfikację (pomiar S4), czyli ok. 470 GB/s, więc kernel jest w dużej mierze związany z ruchem stanu. Połowa bajtów daje **−0.15…−0.3 ms/krok (+0.5–1%)** dla Qwena, z MTP i bez. VRAM −72 MiB. Mniejszy jest też zapis stanu przy cache promptu.
- vLLM-xpu traktuje bf16/fp16 jako pełnoprawne typy stanu (`gated_delta_rule.hpp:804-833`). `[WNIOSEK]`: w vLLM `mamba_ssm_cache_dtype=auto` oznacza typ modelu, więc stan 16-bitowy jest w produkcji normalny. Wybrałbym fp16 zamiast bf16 (10 bitów mantysy, a k jest znormalizowane). Zakres trzeba sprawdzić.
- Koszt: 1–2 dni. Ryzyko: wynik nie jest bitowo identyczny, a błąd zaokrąglenia może dryfować przez 100k+ tokenów.
- Pomiar: KLD/PPL na krótkim i długim tekście (≥64k, `llama-perplexity` z `--ctx` długim), greedy na 94k, rocprofv3 dla czasu GDN na weryfikację i spec_sweep ms/krok.

**P2. Fuzja prologu atencji: norma q/k + RoPE (+FWHT) + `set_rows` K i V (kwantyzacja q4_0/q8_0) w jednym kernelu.**
- Wzorzec: `deepseek_qnorm_rope_kv_insert.cpp`, jedna subgrupa/fala na (token, głowa). Głowy Q i K zostają w istniejącej fuzji `rms_norm_mul_rope`. Bloki obsługujące K piszą też q4_0/q8_0 do cache, a blok V (z wyjścia v-proj) kwantyzuje i zapisuje V. Znika `set_rows` K i V, czyli 2 uruchomienia na warstwę attn. Jest to już na naszej liście (K2 „Zostało”, `lfm-decode-round2.md` §5); vLLM daje gotowy układ.
- Zysk: LFM 10 warstw × 2 × (2.5 µs granicy + ok. 0.3 µs) ≈ **−0.05…−0.07 ms/token (+1.2–1.7%)**, bo `set_rows` q8_0 to 54 µs/token (pomiar round2 §2). Qwen 16 warstw × 2 × ok. 4–7 µs ≈ **−0.13…−0.2 ms/krok (+0.5–0.7%)**.
- Koszt: 1–2 dni. Ryzyko: niskie, wynik bitowy (te same funkcje kwantyzacji). Indeksy slotów KV przychodzą jako wejście grafu, tak jak dla `set_rows`.
- Pomiar: liczba kerneli na token, logit-hash (`lh.sh`), llama-bench tg128 A/B.

**P3. Combine split-KV jako „ostatni blok” (ticket) w `fattn-kvq` i w `flash_attn_ext_vec` (LFM, q8_0).**
- vLLM-xpu robi to osobnym kernelem (`paged_decode.hpp:453-471`), tak jak dziś my. Nasz pomiar mówi jednak, że ogon ticketu kosztuje ok. 1 µs, a granica plus kernel combine ok. 2.5 + 1.9 µs.
- Zysk: LFM 10 wywołań na token ≈ **−0.03…−0.035 ms (+0.8%)**, Qwen 16 na weryfikację ≈ −0.05 ms.
- Ryzyko: wynik pozostaje bitowy, jeśli kolejność sumowania po splitach jest identyczna (ostatni blok czyta wszystkie partiale w porządku `blockIdx.y`). Koszt: 1 dzień.

**P4. Replay GDN bez redukcji: w wierszu oczekującym zapisywać `delta_col` zamiast `v` i `beta` (format RecoverSSM).**
- W `gated_delta_net.cu:213` `delta_col` jest już policzone tym samym wyrażeniem, którego używa replay (`:145`). Zapis jest więc bitowo identyczny, a replay robi tylko `s = g·s + k·delta` (`:138-143` znika). Wiersz kurczy się z `H·(2S+2)` do `H·(2S+1)` floatów.
- Zysk: ok. 3 wiersze × 48 warstw × (16 zależnych FMA + 3 kroki DPP) ≈ **0.01–0.03 ms/krok**, czyli marginalnie. Warto zrobić tylko przy okazji P1 albo T8 z TensorFolda, bo to jedna linijka w zapisie i usunięcie pętli.
- Uwaga: nasz commit w następnej weryfikacji jest lepszy niż osobny commit vLLM (o jedno uruchomienie na warstwę mniej).

**P5. Chunked GDN dla prefillu (WMMA), po pomiarze.**
- Upstream ma `//TODO: Add chunked kernel` (`gated_delta_net.cu:377`). Prefill HIP idzie przez fused kernel rekurencyjny po tokenach (`llama-context.cpp:238` `fused_gdn_ch = true`).
- Najpierw: rocprofv3 dla pp512 i pp4096 i udział `gated_delta_net` w czasie. Mój szacunek to ok. 1–3% prefillu: 512 kroków × ok. 0.3–0.6 µs × 48 warstw ≈ 7–15 ms na ubatch 539 ms. Jeśli pomiar pokaże ≥5%, przenieść 5-kernelowy potok vLLM (§2b). Odwrotność 16×16 na WMMA, `W·S` i `Q·S` ze wspólnym ładowaniem S, stan w L2/global między chunkami, jeden blok na (seq, głowa V) dla kroku wyjściowego (48 bloków na 96 CU, więc warto podzielić V na 2–4 kafle).
- Zysk: do +2–5% prefillu `[SZACUNEK]` przy krótkich promptach. Przy długich dominuje FA, więc zysk znika.
- Koszt: 4–6 dni. Ryzyko: wynik nie jest bitowy (bf16/f16 GEMM zamiast rekurencji fp32), potrzebny KLD.

**P6 (outside the box). Wiele głów na falę w małych kernelach per głowa** (`fused_qknorm_rope.cpp:407-417`: 4–8 głów na subgrupę).
- Gdzie: `rms_norm_mul_rope` (4.4/7.0 µs, NOTES K2) i bramkowana norma GDN. Mniej fal, więcej ładowań w locie na falę. To ma sens tylko wtedy, gdy profil pokazuje, że kernel jest ograniczony opóźnieniem, a nie granicą.
- Zysk ≤0.5 µs na wywołanie, czyli **≤0.03 ms/krok**. Niski priorytet.

**Nie polecam:** potoku MoE z vLLM (5 uruchomień plus glue w Pythonie, gorzej niż nasze 8 uruchomień na całą warstwę LFM), grouped GEMM (u nas jedna sekwencja), samplera z pivotem gaussowskim (host to dziś ok. 140 µs, a `--backend-sampling` nie dał zysku i nie jest bitowy), ścieżek fp8/MXFP4/MLA/sparse-attn.

## 5. Krytyka

- **Brak liczb.** Benchmarki są, wyników nie ma. Projekt group split-K obiecuje zyski „na skośnych batchach” bez danych (`docs/group_split_kv_design.md` §8). Nie da się ocenić jakości kerneli względem pasma.
- **Repo jest dla serwera batchowego**, nie dla jednego strumienia. Paged KV, mieszane długości, prefill i decode w jednym batchu, EP/TP. Dla nas większość logiki (work-list, `is_prefill`, `token_indx`) jest bez znaczenia.
- **Decode attention to standardowy FA2 split-K z CUTLASS** i osobnym reduce. Każda kombinacja (qgroup, head, page, causal, local, sink) to osobny kernel z pliku konfiguracyjnego (384 w trybie „full”). Brak nieoczywistych pomysłów, a nasz `fattn-kvq` (KV q4_0 czytane wprost, `v_permlanex16`, leniwy rescale) jest dalej.
- **MoE nie jest sfuzjowane** i ma glue w Pythonie (`masked_fill` na każdym wywołaniu, `torch.empty`). Pod launch-bound decode (nasz LFM) to antywzorzec.
- **Rekurencja GDN dla decode jest prosta:** skalarne FMA, 2 pełne redukcje 32-lane na wiersz V i token. Nasz układ (8 lane na kolumnę, 3 kroki DPP) jest co najmniej równie dobry `[WNIOSEK]`.
- **Nieaktualne względem nas:** spec kernel GDN zapisuje stan po każdym tokenie (`gated_delta_rule.hpp:277-291`), a commit RecoverSSM jest osobnym krokiem.
- **Uczciwie:** ścieżka chunked GDN jest dopracowana (WY, blokowa odwrotność na MMA, fuzja `W·S`/`Q·S`) i przyznaje się do problemu dokładności MMA na PVC (`chunk_gated_delta_rule_kernels_xe2.hpp:1386-1388`). Dla nas to jedyny duży, gotowy wzorzec do przeniesienia, ale dotyczy prefillu, który u nas ograniczają GEMM-y i FA, nie GDN.
- **Nasze wąskie gardło (pasmo MMVQ 1 i 5 kolumn) nie jest tu w ogóle ruszane.** GEMV idzie przez oneDNN.

## 6. Werdykt

**Niska.** Repo nie dotyka naszego głównego problemu (pasmo MMVQ, koszt uruchomień w MoE). Dla Qwena z GDN daje trzy przenośne pomysły (stan fp16 ok. +0.5–1%, prolog atencji z zapisem KV, chunked GDN w prefillu do zmierzenia), a reszta to fp8 i logika batchowa specyficzne dla Intela.
