# 66d — Saber (GGZ14/saber-engine): silnik w Ruście dla Qwen3.8-27B na R9700 (RDNA4), porównanie z topką na gfx1100

Data: 2026-11-07. Praca tylko na CPU: klon kodu, bez GPU, bez pobierania wag. Klon: `~/src/research66/saber-engine` @ `c8a1e84b39e73363495e549d480a6f6c3893800c` (2026-11-06, jeden squashowany commit). Topka do porównania: `~/wt/topka-q63` @ `c0576e3e8` (2026-11-05).

## 1. TL;DR

1. **Saber to przepisanie w Ruście (+HIP) prywatnego stosu vLLM autora na 1–2 karty R9700 (gfx1201).** Wszystkie kernele to HIP C++ z builtinami gfx12: FP8 WMMA, `global_load_tr`, `s_wait_storecnt`. Ręcznie pisanego asm nie ma, są tylko fence'y. Żaden kernel nie uruchomi się na gfx1100. Wagi to MXFP4 W4A8 (aktywacje e4m3), KV fp8, głowica fp8, czyli **cała numeryka jest stratna względem naszej** (§6).
2. **Pętla GEMV nie daje nam nic.** Ich decode GEMM osiąga w łańcuchu 453 GB/s z 635, czyli ~71% (`rules/mxfp4_gfx1201.toml:167-168`). Nasze MMVQ na XTX ma 81–88% na kernel, a cały plain decode 75.7% pasma 960 GB/s. Strumieniowe ładowania (NT), WMMA w decode i buffer-loady topka już ma (`mmvq.cu:180-231,374-383`).
3. **NOWE i przenośne: atencja decode czyta KV raz dla wszystkich wierszy weryfikacji.** Jeden workgroup obsługuje do 4 fal × 16 wierszy Q, a fale dzielą kafel KV (`sattn_decode.h:1-7,155-481`). Topka `kvq` przy MTP-4 (5×6 = 30 kolumn) robi 2 kafle × pełny odczyt KV (`fattn-kvq.cu:661-681`). To konkretny projekt dla planu #8 i daje szansę na wariant **bitowo identyczny**.
4. **NOWE: dwa pomysły po stronie draftu, oba bezstratne.**
   - (a) Głowica draftu int2 + **dokładny rerank top-K** (`dflash_head.hip:1-40,607-610`). U nas IQ4_XS kosztowało −2–3% akceptacji (łatka 0032); rerank na wierszach Q6_K może to odzyskać i jednocześnie zmniejszyć bajty.
   - (b) Weryfikacja drzewa na hybrydzie GDN w formie WY z maską przodków (`sgdn_tree.h:1-10`, `spec_tree.rs`), u nich symulacja +7.8%.
5. **Liczby to deklaracje autora.** 229 tok/s dotyczy TP=2 na dwóch kartach z DFlash2. Na jednej R9700: 67 / 148 / 231 tok/s (proza / kod / liczenie, T=0, 256 tok., 210 W). Pełnego zestawu warunków (prompty, akceptacja) w repo nie ma. Wątek na Reddicie (6 645 pp, 316 decode „peak”) jest nieczytelny (blokada), znamy tylko tytuł.

## 2. Co to jest

| | |
|---|---|
| Repo | [GGZ14/saber-engine](https://github.com/GGZ14/saber-engine), Apache-2.0, utworzone 2026-11-05, 47★, 5 forków (GitHub API 2026-11-07); brak release'ów |
| Sprzęt | 2× Radeon AI PRO R9700 (gfx1201, 32 GB, 640 GB/s nominalnie; zmierzony szczyt DRAM 635 GB/s, `saber-cli/src/draft_step.rs:859-861`), PCIe, limit 210 W/kartę |
| Modele | tylko Qwen3.8-27B (dense, z drafterem DFlash2) i Qwen3.8 Flash-Next (MoE) (README:177-193) |
| Toolchain | ROCm „TheRock” 10.1.0rc3 (64 obiekty) i 7.14.0rc3 (52 obiekty); obraz publiczny ROCm 7.2.4 **nie odtwarza** prebuiltów (README:346-356) |
| Kernele | 141 plików HIP w `crates/saber-kernels/hip`, 116 code objectów `prebuilt/gfx1201/*.hsaco` z manifestem (sha256 źródła, flagi `-O3 -ffp-contract=off`, VGPR/SGPR) |
| Host | Rust: `saber-plan` (plan z reguł TOML), `saber-exec` (capture/replay grafów HIP), `saber-sched` (wsadowanie, szerokość weryfikacji, parkowanie sesji), `saber-hsa` (prototyp FN63: tablica pakietów AQL i jeden doorbell), `saber-serve` (OpenAI API) |
| Pochodzenie | Komentarze stale odwołują się do „prod” / „reference server” (`qwen_prod_nvfp4`, `patch_dynwidth.py`, `qwen3_dflash2.py:181`, `ref/serve-mxfp4.sh`). Saber przenosi ten stos kernel po kernelu z bramką bajtową. `[INFERENCE]` „prod” to fork vLLM tego samego autora ([GGZ14/vllm-mxfp4](https://github.com/GGZ14/vllm-mxfp4), „vLLM-Radiance”) |

### Opublikowane liczby i warunki

| Twierdzenie | Warunki według źródła | Status |
|---|---|---|
| ~229 tok/s single-stream, TTFT ~47 ms, 5 000+ tok/s prefill, ctx 262 144 (README:7-9) | TP=2, 2× R9700, DFlash2, 210 W/kartę; prompt, T i akceptacja **niepodane** | deklaracja autora |
| TP=1: **67 / 148 / 231 tok/s** proza / kod / liczenie (README:142) | 1× R9700, 256 tokenów, T=0, karta 0 @210 W, obraz ROCm 10.1, pula P2P 2 GiB; karta 1 @300 W: 68 / 152 / 237 | deklaracja; autor pisze, że **nie robił** BetterBench, sweepu prefillu ani soaku na TP=1 (README:149-151) |
| TP=1: maks. ctx 65 536 domyślnie, 163 840 bootuje, prompt 145k → prefill ~2 650 tok/s (README:143) | VRAM 29.5 GiB z 32 (README:145) | deklaracja |
| Szerokość weryfikacji według wsadu: static 8 → 158.0 t/s single / 416.2 conc-8; static 5 → 131.7 / 427.7 (`saber-sched/src/width.rs:9-15`) | „paired BetterBench”, main `0b8a39f`, `[INFERENCE]` TP=2 | wewnętrzny ledger (brak `docs/LEDGER.md` w repo) |
| Bez spekulacji (stos prod): 18.7 ms/krok (`saber-cli/src/engine.rs:23-24`) | TP=2, 210 W, SPEC=0 | wewnętrzny ledger |
| Reddit „6 645 tok/s prefill, 316 tok/s decode peak” | — | **nieczytelne** (Reddit blokuje; web_search zwraca tylko tytuł) |

Normalizacja do naszej karty `[INFERENCE]`, tylko orientacyjnie. Wynik TP=1 67 tok/s (proza, T=0) × 960/640 daje ~100 tok/s, wobec naszych 78.93 (proza E0). **To nie jest porównywalne**, z trzech powodów:
- inne prompty i metryka;
- inny drafter (DFlash2, blok 8, + własna pula 6.4 GB) wobec naszego MTP-4;
- ~6% mniej bajtów na krok przy stratnych wagach MXFP4 (15.4 GB wag na token: `saber-exec/src/tune.rs:2154`) wobec naszych 16.48 GB.

Punkt odniesienia z tej samej karty: Lucebox mierzy na R9700 llama.cpp plain 29.7–30.9 tok/s, 13.3 GiB/token, ~71% pasma ([blog Lucebox, 2026-08-21](https://www.lucebox.com/blog/qwen38-r9700)).

## 3. Kernele: jak działają i co ma topka

### 3.1 GEMV/GEMM dla Q4 w dekodzie (`mxfp4_gemm_decode.hip`)

- **Format.** MXFP4 (e2m1 + wykładnik E8M0 na 32) jest przepakowany offline do „packów”: kolejność fragmentów WMMA, transponowane skale, połączone projekcje (README:181-187).
- **Fold.** Wykładnik bloku jest wtopiony w wagę przez LUT `kMag[d]` i `v_perm_b32`. 4-bitowy kod staje się bajtem e4m3 przesuniętym o `d = Wref[n] − Ws[blk][n]` binad, więc skala zostaje jednym czynnikiem na wiersz w epilogu (`mxfp4_common.h:20-54`).
  - Dokładne dla d ≤ 8 dzięki subnormalnym e4m3, które FP8 WMMA na gfx12 honoruje.
  - Dla d ≥ 9 następuje zaokrąglenie: w warstwie 58 zostaje 0.31% błędu normy. **Stratne**.
- **Rdzeń.**
  - Dla M ≤ 64 kafel 16×(8 fal × 16 kolumn), slab K 64/128 bajtów jest stage'owany do LDS, potem `wmma_f32_16x16x16_fp8_fp8` (`:168-186`).
  - Split-K (1/2/4) jest dobierany regułą „najmniejszy podział, który wypełnia maszynę” (`rules/mxfp4_gfx1201.toml:88-98`).
  - **Redukcję robi ostatni przybyły blok** (atomowy licznik, reset przez ostatniego, bez drugiego launcha), według nich −5.5…−29% czasu kernela (`mxfp4_gemm_decode.hip:239-262`).
- **Ładowania.** Wagi czytane `__builtin_nontemporal_load` (`th:TH_LOAD_NT`), skale i partiale normalnie (`:29-39`). Układ WPERM: fala czyta 128 ciągłych bajtów (`:125-167`).
- **Wariant „pf” (opcja, domyślnie wyłączona).** Prefetch do rejestrów następnego slabu przed WMMA bieżącego, z barierami tylko na LDS, bo na gfx12 `__syncthreads()` = `s_wait_loadcnt 0` (`mxfp4_gemm_decode_pf.hip:1-19`).
- **Pomiar.** 453 GB/s w łańcuchu przy b1s5, czyli ~71% z 635 (`rules/mxfp4_gfx1201.toml:167`).

**Topka na gfx1100.** MMVQ ma ścieżkę WMMA dla wielu kolumn (`mmvq.cu:171-178`), buffer resource w SGPR (`:180-231`) i politykę cache GLC|DLC dla wag (`:374-383`, w weryfikacji MTP 22.95 → 22.08 ms). Reguły R=1/2 wierszy na blok dla 1024-wierszowych k/v pochodzą z [raportu 49](49-mmvq-ogon-1024.md). Pasmo: 81–88% na kernel ([wiki sufit-pasma](../../wiki/metody/sufit-pasma-i-mapa-czasu.md):12), plain 75.7% ([wiki qwen3-8-27b](../../wiki/modele/qwen3-8-27b.md):25). **Wniosek: nasza pętla jest lepsza w relacji do szczytu.** Z Sabera warto rozważyć tylko split-K z redukcją ostatniego przybyłego dla małych N (§5, pomysł F).

### 3.2 Atencja decode, split-KV (`sattn_decode.h`, `sattn_prims.h`)

- **Siatka i role fal.** Siatka to (segment KV, głowica KV, sekwencja). Workgroup ma **NW ≤ 4 fale, każda z 16 wierszami Q**, gdzie wiersz r = token r/GQA, głowica r%GQA. GQA 6 i `q_len ≤ 10` dają ≤ 64 wiersze, więc **cała weryfikacja jednej głowicy KV mieści się w jednym workgroupie i każdy bajt KV jest czytany z DRAM raz** (`sattn_decode.h:1-7,203-209`; reguły `decode_max_nw = 4`, `saber_gfx1201.toml:36-39`).
- **K.** Każda fala ładuje K z pamięci globalnej prosto do operandu A WMMA. Dla fp8 dwie grupy są w locie (`:377-421`), a po pierwszej fali K trafia z L2.
- **V.** Transponowane ładowanie `global_load_tr_b128`, **tylko gfx12**, do LDS jeden raz na kafel, wspólne dla fal. Następny kafel V jest prefetchowany (`:257-375`; `sattn_prims.h:174-180`).
- **Softmax.** Online w domenie log2, **leniwe przeskalowanie przy wzroście maksimum > 14** (`:447-460`). P idzie do f16 RTZ i PV przez WMMA f16 (`:462-480`).
- **Partiale.** f16 + (m, l) (`:483-507`). Merge może zrobić **ostatni przybyły segment** (wariant `declc`), ale jest **wyłączony domyślnie** (ws-h38, `saber_gfx1201.toml:428-463`, `saber-exec/src/layer.rs:504-506`); zwykle chodzi osobny kernel combine.
- **Prawo podziału.** fill 192 / (głowice KV × sekwencje), w dół do potęgi 2, zakres 16…128, ≥ 2 kafle na segment. „Argmin 64 przy każdej głębokości” (`saber_gfx1201.toml:47-56`).
- **KV.** fp8 e4m3, czyli 1 B na element (`saber-plan/src/model.rs:697-716`).

**Topka (`kvq`, gfx110x).** Tak samo K jest dekwantowane prosto do fragmentów A WMMA, a V transponowane przez LDS (`fattn-kvq.cu:1-24`). Leniwe przeskalowanie ma próg 8 (`:36-38`). Różnice:
- **Kafel ma 16 kolumn Q (`:30`), a fale w bloku dzielą wiersze KV, nie Q.** Przy weryfikacji MTP-4 jest 5×6 = 30 kolumn, czyli `ntiles_x = 2` bloki, które **każdy czyta cały KV** (`:661-681`).
- Partiale są f32, a combine to osobny launch (`:695-711`).
- Podział: 2 bloki na SM / (ntiles_x × głowice) (`:615-636`).

Plan #8 (63c E7) proponował kafel 32 kolumn. Saber pokazuje drugi, działający w produkcji układ: **fale dzielą wiersze Q, a kafel KV jest wspólny**. Porównanie w §5, pomysł A.

### 3.3 GDN (gated delta net), decode i spekulacja

- **Rekurencja decode.** Dwa wątki na wiersz v stanu [V][K], po 64 elementy k w rejestrach, akumulatory f32 (`sgdn_rec.h:1-10`). Stan f32 jest domyślny, wariant `f16s` jest stratny (`saber_gdn_recurrent_update_f16s.hip`).
- **Fuzja conv + rekurencja z barierą siatki.** Jeden launch przy batch 1 daje **19.34 vs 19.99 µs na węzeł**. Przy batch ≥ 2 fuzja przegrywa, bo sama bariera kosztuje ~0.7 µs (`saber_gfx1201.toml:64-89`).
- **Snapshot stanu na wiersz** do wycofania po akceptacji (`naccept`, `sidx`) (`sgdn_rec.h:110-120`).
- **Weryfikacja drzewa (P27-15, P27-W2).**
  - Forma WY nad zbiorem przodków: z zatwierdzonego stanu liczy się na raz u_r i wyjście każdego węzła drzewa (do 10, a w wariancie 16 do 16 wierszy).
  - Zapisuje się „record” (U, znormalizowane k, P, słowa przodków).
  - Stan dla zaakceptowanej ścieżki aplikuje osobny „advance”, także jeden launch dla wszystkich warstw (`sgdn_tree.h:1-10`, `p27_tree_advl.hip`).
  - Okno conv jest przesuwane na miejsce łańcucha (`p27_tree_flush.hip`).
  - Atencja dostaje maskę przodków (`MaskBy::Ancestor`, `sattn_decode.h:242-245,431-439`).
- **Prefill.** Chunked WY (chunk 64, gram f32 nie trafia do HBM) (`saber-plan/src/model.rs` sekcja P2).

**Topka.**
- GDN z dokładnym lag/replay (`GATED_DELTA_NET_LAG`) i slotami snapshotów (`gated_delta_net.cu:45-52,431`).
- Normalizacja l2 jest w kernelu.
- Conv jest zfuzowany z MMVQ alpha/beta w jednym launchu (`ggml-cuda.cu:4170-4177`).
- **Drzewa nie ma**, weryfikacja to łańcuch.
- Chunked WY w prefillu był już odrzucony na gfx1100 (−39%, Strata #888, wiki `repo/strata.md`).
- Fuzja z barierą siatki daje 0.65 µs na węzeł, około 30 µs na krok, czyli ~0.1%. Nie warto.

### 3.4 Głowica, sampler, drafter

- **Głowica celu.** fp8 + skala per wiersz, kafel 64 wierszy w jednym przejściu (`saber_head_w8_m64.hip:1-17`), **stratna**.
- **Argmax z wartością.** Zwraca też bf16 wygrywającego logitu, żeby host nie robił rozproszonych odczytów; ~3.5 µs na wiersz (`saber_argmax_pv.hip:1-14`). Do tego warianty `device_row_*` samplera (podział wiersza na G workgroupów, ten sam porządek sum).
- **Drafter DFlash2 (z-lab), blok 8, osobny pack 6.4 GB.**
  - Selector to jeden WMMA 16×16 na pozycję (`dflash_selector.hip:1-15`).
  - **Głowica draftu int2:** asymetryczna, grupy po 128, „quarter-split”. Kandydaci to maksima bloków po 64 kolumny (KCAND 8).
  - Potem **dokładny rerank** kandydatów na wierszach e4m3/bf16 głowicy: „kilkaset KB wobec 0.167 GiB grubego przejścia” (`dflash_head.hip:1-40,88-93,607-610`).
  - Według ich censusu głowica draftu to 4.0% kroku (`:6-7`).
- **Prompt-lookup (FN69).** n-gram 3–4 nad promptem i wyjściem. **„Zastąp, gdy pewny”:** dopasowanie ≥ `min_match` (3) i kontynuacja nie krótsza od propozycji draftera zastępuje cały blok draftu (`saber-engine/src/lookup.rs:1-27,50-56`). Domyślnie wyłączone (`flashnext/run.rs:1781`).
- **Szerokość weryfikacji.** Tablica według wsadu (8 przy batch 1–3, 5 od 4). Reguła EMA akceptacji przegrała pomiar (`width.rs:1-30`). Dla nas, przy `-np 1`, bez znaczenia.

**Topka.**
- Głowica Q6_K celu jest w MMVQ.
- MTP ma zredukowany słownik 65 536 i głowicę/blok przekwantyzowane do IQ4_XS (łatka 0032: draft 4.82 → 3.62 ms na krok, **akceptacja −2–3%**, netto +1–3%; wiki `latki/latki-spekulacji.md:15`).
- DFlash2 z selectorem jest w kodzie (`src/models/dflash.cpp:34-35,139-153`), ale **rerankera nie ma**.
- Lookup działa w trybie „ogon”: tokeny lookupu dokleja się tylko wtedy, gdy draft zgadza się z początkiem lookupu, `MMIN` 6 (`common/speculative.cpp:2824-2850`).

### 3.5 Host, launch, pomiar

- **Grafy HIP** przechwycone per kubełek (batch × szerokość). FN63 to prototyp replayu tablicy pakietów AQL z jednym doorbellem i bramką bajtową plus kontrolą negatywną (`saber-cli/src/fn63_hsa.rs:1-21`). Topka ma niżej poziomowy replay PM4 (znane).
- **ws-h28:** **+6.6 ms na krok** przy `--max-ctx 32768` wobec 4096 przy tym samym ciągu dispatchy. Przyczyną było wysyłanie co krok całego bloba indeksów, w tym tablicy RoPE wielkości pojemności. Poprawka: stałe raz, co krok tylko zmieniony zakres (`saber-engine/src/index.rs:345-361,1606-1612`). To ten sam wzorzec, co nasze podejrzenie F5 (maska KQ budowana na CPU w O(n_kv), 63d E7).
- **Strojenie „IC-cold”.**
  - Bufory są rotowane, aż `(kopie − 1) × bajty ≥ 64 MiB` (MALL), plus **zapis 2× MALL między próbkami**.
  - Sama rotacja trzech kopii dawała 925 GB/s = 1.46× szczytu DRAM (`saber-exec/src/tune.rs:2150-2186`).
  - Wycofana reguła BK=64 była +30% „na gorąco” i **−11% na zimno** (`rules/mxfp4_gfx1201.toml:150-171`).
- **Bramki.** Każdy kernel z bramką bajtową ma symbol kontroli negatywnej (np. `*_drop1` gubi ostatni segment merge'a; `saber_gfx1201.toml:435-442`).
  - Lekcja z `saber-exec/src/layer.rs:510-517`: bramka, której wejścia były w części zerami, „przechodziła” z 0 różnic. Po podpięciu prawdziwych wejść różnic było 627 393 bajty.
- **Opcja P2PDMA NVMe → VRAM.** Łatka jądra `amdgpu.p2pmem_mb`, 9.5–10.7 GB/s, tylko ładowanie wag (README:309-325). Dla Enigmy odpada, bo wymaga własnego jądra.

## 4. Macierz przydatności

Legenda: ✅ przenośne, ◐ częściowo, ✗ nie, — nie dotyczy.

| Element Sabera | AMD gfx1100 (topka) | Enigma NVIDIA CUDA | Apple Metal | Intel (SYCL/Vulkan) | Strix Halo gfx1151 |
|---|---|---|---|---|---|
| Kernele hsaco gfx1201 (FP8 WMMA, `global_load_tr`, `s_wait_*`) | ✗ (gfx12-only ISA) | ✗ | ✗ | ✗ | ✗ (RDNA3.5 = WMMA gfx11) |
| MXFP4 W4A8 + fold `kMag` | ✗ stratne | ✗ | ✗ | ✗ | ✗ |
| Atencja: fale dzielą wiersze Q, KV raz na weryfikację | ✅ (kvq, pomysł A) | ◐ upstream FA-MMA już pakuje GQA × tokeny do 64 kolumn `[INFERENCE]`; fork kvq-CUDA tak | ◐ idea dla Metal FA-vec `[INFERENCE]` | ◐ | ✅ (ta sama ścieżka kvq co gfx11) |
| Merge split-KV przez ostatni blok | ✅ | ✅ | ◐ | ◐ | ✅ |
| Split-K + redukcja ostatniego bloku w GEMV dla małych N | ✅ | ✅ | ◐ | ◐ | ✅ |
| Drzewo weryfikacji + GDN w formie WY | ✅ (wspólny kod ggml + kernele) | ✅ | ✅ (CPU/Metal op GDN) | ✅ | ✅ |
| Głowica draftu: grube przejście + dokładny rerank | ✅ (op-y ggml) | ✅ (Enigma używa MTP z upstream) | ✅ | ✅ | ✅ |
| Lookup „zastąp, gdy pewny” | ✅ (host) | ✅ | ✅ | ✅ | ✅ |
| Upload tylko zmienionych bajtów wejść kroku | ✅ (F5) | ✅ | ✅ | ✅ | ✅ |
| IC-cold (rotacja + scrub 2× MALL) | ✅ (MALL 96 MB → scrub 192 MB) | ✅ (L2 4090 72 MB, 3090 6 MB) | ◐ (SLC) | ◐ | ✅ (MALL 32 MB `[INFERENCE]`) |
| R9700 / RX 9070 XT (planowany zakup, wiki `karty/rx-9070-xt.md`) | — | — | — | — | — |

Ostatni wiersz: **Saber jest najlepszym publicznym wzorcem operandów WMMA gfx12** (f16x8 / i32x2 na linię, `sattn_prims.h:136-143`) i pułapek gfx12 (`__syncthreads()` opróżnia prefetch: `mxfp4_gemm_decode_pf.hip:6-8`). Przyda się przy porcie topki na RDNA4.

## 5. Pomysły do przetestowania (tylko bezstratne)

Nasze punkty odniesienia: greedy ~106 t/s, spec_sweep T=1 114.8, proza E0 78.93, `mvs` 433.8, long_ctx 94k 105.6 / 199k 74.5 t/s, plain decode na 75.7% z 960 GB/s. `[SZACUNEK]` = arytmetyka, nie pomiar.

| # | Pomysł | Bezstratny? | Oczekiwany zysk i skąd | Wysiłek | Jak testować u nas | Ryzyko |
|---|---|---|---|---|---|---|
| A | **kvq z grupami wierszy Q** (wzór `sattn_decode.h:155-481`): blok = 2 grupy × `nwarps`; grupa g liczy kolumny 16g…16g+15 tymi samymi warpami KV co dziś; dekwant V raz do LDS, wspólny dla grup; K drugiej grupy z L2. Podział zostaje liczony jak dla `ntiles_x = 2` | **Tak.** Arytmetyka każdej kolumny jak w kvq16, więc bitowo z konstrukcji `[INFERENCE]`; sprawdzić md5. Wariant z nowym podziałem: kolejność sum, bramka KLD | 199k: 74.5 → 77–83 (**+3…11%**); 94k: 105.6 → 107–111 (+1…5%); krótki ctx 0. Skąd: weryfikacja MTP-4 = 30 kolumn = 2 kafle × ~3.7 GB KV na krok przy 199k (63d E7); zysk zależy od tego, ile drugiego odczytu dziś łapie L2 (bloki x=0/1 startują obok siebie `[INFERENCE]`) i ile kosztuje podwójny dekwant | 2–3 d | `test-backend-ops perf -o FLASH_ATTN_EXT` hsk=256, nb=5, kv 94k/199k, KV q4_0; rocprofv3 kroku przy 199k (plan #3); `long_ctx_bench` 94k/199k ABBA; md5 c4708318/6f14e814/894e56e4 | LDS ×2 vs cap 64 KB (plan #5) obniży occupancy; kill: czas FA < −10% w rocprofv3 |
| B | **Głowica draftu MTP: grube przejście + dokładny rerank top-K** (`dflash_head.hip:1-40,607-610`). Ramię B1: IQ4_XS jak dziś + rerank top-8 na wierszach Q6_K `output.weight` (`get_rows` + mul_mat 8 × 5120). Ramię B2: Q2_K na słowniku 65 536 + rerank | **Tak** (zmienia tylko draft) | B1: odzysk −2–3% akceptacji z łatki 0032 przy ~0 bajtów → spec_sweep **+1…3%**. B2: głowica 178 → ~110 MB na przejście draftu × 4 = −0.27 GB na cykl (~0.3 ms z ~31 ms) plus rerank → **+1…4%** `[SZACUNEK]` | 2 d | `spec_sweep` T=1 + proza E0 + `mvs`, ABBA; log akceptacji per pozycja; md5 bez zmian (cel nietknięty) | top-8 grubej głowicy może nie zawierać argmax Q6_K (sprawdzić offline na logitach); +koszt top-k na GPU |
| C | **Drzewo weryfikacji dla MTP z GDN w formie WY** (`sgdn_tree.h`, `spec_tree.rs:490`, maska przodków). Krok 1, CPU: symulacja drzewa best-first (budżet 4–9 węzłów, top-2 MTP na głębokość) na logach draftu, jak ich `tree_sim.py`, potem decyzja | **Tak przy T=0** (twierdzenie w `spec_tree.rs:13-22`); przy T>0 potrzebna wielodraftowa rejekcja (SpecInfer), inaczej rozkład się zmienia | Saber: +7.8% (symulacja P27-10, DFlash2). U nas: kod/T=0 **+3…8%**, czat T=1 0…+4% `[SZACUNEK]`; warunek z 24s: dodatkowy wiersz weryfikacji ≤ 0.57 ms (dziś 0.85) | sym. 1 d; pełne 1–2 tyg. | sym. CPU na `LLAMA_SPEC_*` logach; potem `spec_sweep` T=0/T=1, `mvs`, `long_ctx_bench` (maska przodków w kvq) | kernele GDN tree + KV dla gałęzi + rejekcja T>0; ryzyko regresji czatu |
| D | **Lookup „zastąp, gdy pewny”** (`lookup.rs:23-27`): tryb 4 w `common_spec_lookup_cfg`. Przy dopasowaniu ≥ 3–6 i kontynuacji ≥ draftu lookup zastępuje drafty MTP zamiast wymagać zgodności (dziś tryb 2) | **Tak** | agent/edycje: `mvs` 433.8 → +0…5% `[SZACUNEK]`; czat 0 | 0.5 d CPU (replay `LLAMA_SPEC_LOOKUP_LOG` trybu 1) + 0.5 d kod | najpierw offline: na logach trybu 1 policzyć, ile tokenów zaakceptowałby lookup vs MTP; potem `mvs` + `spec_sweep` | fałszywe dopasowania obniżą akceptację na prozie; kill przy czacie < −1% |
| E | **Merge split-KV w kvq przez ostatni blok** (`sattn_decode.h:509-535`): licznik atomowy na (seq, głowica KV), merge w kolejności `flash_attn_combine_results` | **Tak** (bitowo, jeśli kolejność merge'a = combine; Saber ma symbol kontroli `_drop1`) | −17 launchy na krok (16 FA + MTP) → **+0.2…0.5%** `[SZACUNEK]`; Saber trzyma to wyłączone (brak dowodu zysku) | 1 d | rocprofv3 combine µs przy 94k; `long_ctx_bench` ABBA; md5 | zysk w szumie; pod PM4 replayem przerwy są krótsze |
| F | **Split-K + redukcja ostatniego bloku w MMVQ dla 1024-wierszowych k/v** (`mxfp4_gemm_decode.hip:239-262`) | Tak/kolejność: suma bloków K w innej kolejności, md5 może się zmienić → KLD | pula ≤ 0.2 ms na krok minus zysk R=1 z raportu 49 → **+0.1…0.3%** | 1 d | `klab` mikrobench cold 1024×5120 (Q4_K/Q5_K/Q6_K/Q8_0/IQ4_XS) vs R=1; potem E0 ABBA | marginalne; nowy bufor partiali |
| G | **Wejścia kroku: co krok wysyłać tylko zmienione bajty** (ws-h28 `index.rs:345-361`) → w topce: maska KQ (F5) budowana przyrostowo albo na GPU | **Tak** (bitowo) | 63d F5: 2–6 ms na krok przy 199k → **+5…15% @199k** `[SZACUNEK, warunkowo]`; to już plan #3, Saber dokłada precedens (+6.6 ms na krok z jednego bloba) | po profilu 1–2 d | rocprofv3 + host trace kroku przy 1.7k/94k/199k (plan #3); `long_ctx_bench` | tylko jeśli profil potwierdzi koszt hosta |
| H | **Metodologia:** (1) IC-cold w `klab`/mikrobenchach: rotacja buforów < 96 MB i scrub 192 MB między próbkami; (2) symbol kontroli negatywnej przy każdej bramce bitowej | — (pomiar) | 0% t/s; chroni przed fałszywą wygraną (u nich +30% na gorąco = −11% na zimno) | 0.5 d | sprawdzić, czy `klab`/mmvq-bench pisze ≥ 2× MALL; powtórzyć 1 znany przypadek gorąco i na zimno | — |

Ranking zysk/wysiłek: **A** (po profilu z planu #3, razem z G), **B1** (najtańszy, czysto draftowy), **D** (najpierw offline), potem **C** (symulacja CPU jako bramka), E i F na końcu.

**Już znane, nie powtarzać:** WMMA w GEMV dla wielu kolumn, buffer-loady i GLC|DLC (topka ma), leniwe przeskalowanie (próg 8), K → WMMA A i V przez LDS (kvq), GDN lag/replay i snapshoty (0033–0036), fuzja conv z alpha/beta, grafy i replay kroku (mamy PM4), selector DFlash2 (topka ma), chunked GDN w prefillu (−39% na gfx1100), MTP n per karta (plan #4), szerokość weryfikacji według wsadu (`-np 1`, nie dotyczy).

## 6. Odstawione (stratne): bez rankingu

| Technika Sabera | Dlaczego stratna | Liczby (informacyjnie) |
|---|---|---|
| Wagi MXFP4 przekwantowane z NVFP4/FP8 (README:181-187) | inny kwant wag | pack celu TP=1 18.5 GB; ~15.4 GB wag na token |
| Aktywacje e4m3 (W4A8) w każdym GEMM | kwantyzacja aktywacji | — |
| Fold wykładnika w wagę dla d ≥ 9 | zaokrąglenie; warstwa 58: 0.31% błędu normy | `mxfp4_common.h:26-33` |
| KV fp8 e4m3 | inny KV | 1 B na element vs nasze q4_0 0.5625 B |
| Partiale split-KV w f16; Q bf16 → f16 RTZ | dodatkowe zaokrąglenia, nie tylko kolejność | `saber_gfx1201.toml:40-45` |
| Głowica celu fp8 | inna precyzja głowicy | `saber_head_w8_m64.hip` |
| Stan GDN f16 (`f16s`) | stan o niższej precyzji | wariant opcjonalny |
| All-reduce `wht6` (6 bitów z rotacją) dla wiadomości ≥ 128 KiB | kwantyzowana komunikacja TP | dotyczy TP=2 przy conc-8 (`saber_gfx1201.toml:117-133`) |
| FP8 WMMA w prefillu | inna numeryka (i tylko RDNA4) | 5 000+ tok/s TP=2, 2 650 tok/s TP=1 @145k |

## 7. Źródła

- Repo: [github.com/GGZ14/saber-engine](https://github.com/GGZ14/saber-engine) @ `c8a1e84b39e73363495e549d480a6f6c3893800c` (2026-11-06); klon `~/src/research66/saber-engine`. Metadane z GitHub API (2026-11-07): utworzone 2026-11-05, 47★, 5 forków, Apache-2.0, brak release'ów.
- Wątek: [r/LocalLLaMA „Qwen3.8 27b hitting 6,645 tok/s on prefill and 316 tok/s decode peak on Saber”](https://www.reddit.com/r/LocalLLaMA/comments/1xpicjz/qwen38_27b_hitting_6645_toks_on_prefill_and_316/) (2026-11-07): **treść niedostępna** (blokada Reddita), web_search zwraca tylko tytuł.
- Kontekst R9700: [Lucebox, „Qwen3.8-27B on the AMD R9700: up to 227 tok/s”](https://www.lucebox.com/blog/qwen38-r9700) (2026-08-21): llama.cpp plain 29.7–30.9 tok/s, ~71% pasma; Lucebox DFlash2 blok 16: 208 tok/s HumanEval.
- Stos referencyjny autora `[INFERENCE]`: [GGZ14/vllm-mxfp4](https://github.com/GGZ14/vllm-mxfp4) (nieczytany w głąb).
- Topka: `~/wt/topka-q63` @ `c0576e3e8`; pliki `ggml/src/ggml-cuda/fattn-kvq.cu`, `fattn.cu:635-637`, `mmvq.cu`, `gated_delta_net.cu`, `ggml-cuda.cu:4170-4177`, `common/speculative.cpp:2824-2850`, `src/models/dflash.cpp`.
- Nasze dane: wiki `modele/qwen3-8-27b.md:25`, `metody/sufit-pasma-i-mapa-czasu.md:12`, `kernele/mmvq-multikolumnowe.md:25`, `latki/latki-spekulacji.md:15`, `repo/strata.md:12`; raporty [63-SYNTEZA](63-SYNTEZA.md), [63c](63c-amd-rocm-llamacpp.md) E7, [63d](63d-atencja-spec-kwant.md) E7, [49](49-mmvq-ogon-1024.md); `qwen-opt/run-llm.sh:42-45,96-99`.
