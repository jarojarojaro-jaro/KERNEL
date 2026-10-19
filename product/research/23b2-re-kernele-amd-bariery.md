# 23b — RE kerneli AMD (gfx1100) vs nasze MMVQ/MMQ/FA + porównanie barier LDS

Autor: ResVendorAmd (kontynuacja ResVendorAmd2) · data: 2026-10-19 · tryb: CPU-only (nice 19, taskset), zero GPU, nic nie mierzone na karcie.
Źródło AMD: lokalny ROCm `/opt/rocm/core-10.0` (wersja 10.0.0, TheRock, kody w `.kpack`) + koło PyTorch ROCm w `~/qwen-opt/.venv-train` (AOTriton).
Źródło „nasze”: `~/llama-opt/lib/libggml-hip.so.0.26.0` (gałąź amd-opt, 15.10), `.hip_fatbin` rozcięty na TU (`~/qwen-opt/re/amd/ours/co/tuNNN.co`).
Artefakty: `~/qwen-opt/re/amd/` (dumpy `.s`, JSON-y profilu). Narzędzia (nowe, wielokrotnego użytku): `~/KERNEL/tools/re/{kpack_extract.py, isa_profile.py, tensile_lib.py, fatbin_split.py, aotriton_extract.py}`.

## TL;DR

1. **AMD nie ma lepszego GEMV niż nasz.** rocBLAS `gemvt_*` dla fp16 to kod HIP z wąskimi `global_load_b32`/u16, bez `b128`, bez buforów (§2.1). hipBLASLt na N≤16 robi zwykły GEMM z kaflem N=16 na `v_wmma_*_16x16x16` (N dopełniane do 16), więc dla N=1 marnuje 15/16 WMMA. To nie jest wzorzec dla dekodu N=1.
2. **Od Tensile (ręczny asm hipBLASLt) warto wziąć dwie rzeczy:** (a) **głęboki potok pamięci**: 12 `buffer_load_b128` w locie, prefetch na 2 iteracje do przodu (PGR2 w 65% rozwiązań), stopniowy `s_waitcnt vmcnt(N)` zamiast `vmcnt(0)` co iterację; (b) **bariery bez `buffer_gl0_inv`**: 14 574 `s_barrier` i 0 `gl0_inv` w 1025 kernelach. Nasze MMVQ co iterację czeka do `vmcnt(0)` i niczego nie ściąga z wyprzedzeniem (§3).
3. **Bariera LDS (pytanie z 21g):** wszystko, co AMD kompiluje z HIP-a przez `__syncthreads()`, płaci `buffer_gl0_inv` tak samo jak my: CK reduce 1584/1584 barier, MIOpen-CK 2136/2152, rocBLAS. Ręczny asm (Tensile, extop) i CK-tile (`block_sync_lds` = `s_waitcnt lgkmcnt` + goły `__builtin_amdgcn_s_barrier`) go nie mają. U nas `gl0_inv` stoi po 93–100% barier, a najdroższe miejsce to **gorąca pętla MMQ: 4 bariery i 4 `gl0_inv` na iterację K**. W pętli `fattn-kvq` barier nie ma wcale (§4).
4. **Cache policy:** AMD **nigdy** nie ustawia bitów nontemporal/glc/slc/dlc na operandach GEMM: 0/2182 rozwiązań hipBLASLt, 0/7461 rocBLAS, 0 w CK. My dajemy `glc dlc` na wagach w MMVQ n≥2. To nie dowód, że robimy źle, ale warto zrobić tani test A/B (§5, poz. 4).
5. **Uwaga, attention:** AMD nie dostarcza skompilowanego decode-attention dla gfx11 (MIOpen bez gfx11, CK-tile FMHA tylko jako nagłówki). Jedyny gotowy kod to AOTriton `attn_fwd`, a ten jest gorszy od naszego `fattn-kvq`: 218 vs 144 VGPR, 11 barier na iterację vs 0, P przez LDS vs `v_permlanex16` (§2.4).

## 1. Co i jak wyciągnięto

| Biblioteka | Format | Wyciągnięte gfx1100 | Narzędzie |
|---|---|---|---|
| rocBLAS (HIP gemv/gemvt) | `.kpack` (zstd, TheRock) | `kpack_blas/…librocblas.so.5.6#NN.gfx1100.co` | `kpack_extract.py` (ctypes na `librocm_kpack`) |
| rocBLAS Tensile | `.dat` msgpack + `.hsaco`/`.co` | 7461 rozwiązań, fallback `MT64x1` | `tensile_lib.py` (własny dekoder msgpack) |
| hipBLASLt | `TensileLibrary_*.dat.zlib` + CCOB `.co` | 2182 rozwiązań, 40 `.elf` (`hipblaslt/`), 1025 kerneli TN profilowanych (`alik_bljk.json`) | `clang-offload-bundler --unbundle` |
| hipBLASLt ext ops | `extop_gfx1100.co`, `Kernels.so-000-gfx1100.hsaco` | LayerNorm/Softmax/AMax (`extop.json`), PostGSU | — |
| CK (instancje) | `libdevice_reduction_operations.a` → `.hip_fatbin` CCOB | 182 kernele reduce (`ck/ck_reduce.json`) | `fatbin_split.py` |
| MIOpen CK grouped conv | `libMIOpenCKGroupedConv_gfx1100.so` | 509 TU (528 MB), próbka co 20. TU = 1371 kerneli (`miopen_ck/sample.json`) | `fatbin_split.py` |
| CK-tile, rocWMMA | tylko nagłówki | lektura źródeł (`/opt/rocm/include/ck_tile`) | — |
| AOTriton (torch) | `aotriton.images/amd-gfx110x/flash/attn_fwd.zip` (AKS2+XZ) | 21 wariantów D128 + 19 D256 dla gfx1100 (`aotriton/fwd`) | `aotriton_extract.py` |
| AITER / Triton-AMD | brak w systemie i w venv | — | — |

Metryki (`isa_profile.py`) pochodzą z metadanych `NT_AMDGPU_METADATA` (VGPR/SGPR/LDS/wave) i z `llvm-objdump --mcpu=gfx1100`. „Pętla” to najgorętszy blok z skokiem wstecz (dla asm Tensile etykiety per kernel). Obsadzenie (`occ`) to fale/SIMD wynikające z VGPR.

## 2. Co robi AMD: kernel po kernelu

### 2.1 rocBLAS gemvt (macierz transponowana = nasz układ wag) — `rocblas_sel.json`, dump `dump_rocblas/`

| Kernel | VGPR | occ | WG | LDS | ładunki w pętli | bajty/lane/iter | `b128` |
|---|---|---|---|---|---|---|---|
| `gemvt_warp_reduce<256, fp16>` | 20 | 16 | 256 | 128 | 6× `global_load` | 16 | 0 |
| `gemvt_sn<256,4, fp16>` (skinny-N, split) | 44 | 16 | 256 | 128 | 13 | 50 | 0 |
| `gemvtsm<256, fp16>` | 22 | 16 | 256 | 256 | 3 | 22 | 1 |
| `gemvt_double_buffered<128,8,8, f32>` | 125 | 10 | 1024 | 32768 | 27× `b32` | 108 | 0 |

Wąskie ładunki (b32/u16), zawsze `global_*` (bez buforów) i `vmcnt(0)` po pojedynczym ładunku: to generyczny kod HIP, nie strojony pod RDNA3. **Nic do przeniesienia.**

### 2.2 hipBLASLt / Tensile (asm) — `hipblaslt/alik_bljk.json`, dump `hipblaslt/dump_mt32x16/0000.s`

- Parametry (2182 rozwiązania gfx1100, w tym 529 „skinny”, czyli min(MT0,MT1)≤16): `nonTemporalA/B/D=0` (100%), `DirectToLds=0`, `streamK=0`, `PrefetchGlobalRead` 2/1/0 = 1418/573/191, `globalSplitU` 1/4/2 = 1992/162/28, `grvwA=8` (ładunki 16 B) w 1759.
- Kafle dla małego N: `MT16x16`, `32x16`, `64x16`, `256x16`, `16x64` z `MI16x16x16` (WMMA), WG 16×2 / 32×2 / 64×2. N=1..16 dopełniane do 16.
- Kernele TN (1025): **100% `buffer_load`** (178 180), 0 `global_load`, 0 glc/slc/dlc, 0 VOPD, 0 DPP, 0 `s_delay_alu`, 784 `s_setprio`, **14 574 `s_barrier` / 0 `buffer_gl0_inv`**.
- Przykład `Cijk_Alik_Bljk_HHS_…_MT32x16x128` (256 VGPR, occ 5, LDS 29 440 B, WG 64). Pętla ma 112 instrukcji, 12 `buffer_load_b128` (8 dla A, 4 dla B) i offsety w SGPR (`s66…s73`, jeden VGPR adresu na operand). Wysyła ładunki iteracji k+2 zaraz po `ds_store_b128` z k+1. `MT256x16x32`: do 63 ładunków w locie (`vmmax 63`).
- MT16x16 ma WG = 32 wątki (1 fala), więc w pętli nie ma ani jednej bariery.
- Split-K (GSU=4) redukowany osobnym, deterministycznym kernelem `Cijk_*_PostGSU{2,4,8,16}` (`Kernels.so-000-gfx1100.hsaco`).

### 2.3 Int8: v_dot4 vs WMMA iu8

- hipBLASLt I8: tylko `v_wmma_i32_16x16x16_iu8` (14 kerneli skinny).
- rocBLAS fallback `4xi8I_HPA`: 2320× `v_dot4_i32_i8`, kafle 16×64/64×16 bez WMMA.
- Nasze `mul_mat_vec_q_wmma<…,8>` (7 typów) używają tego samego `v_wmma_i32_16x16x16_iu8` (112 wystąpień). Pętla: 17–32 `buffer_load`, 0 barier, 157–175 VGPR (occ 8–9). To parytet z AMD.

### 2.4 Attention (decode)

| | AOTriton `attn_fwd` D128 M16 N16 (`aotriton/a.json`) | nasz `flash_attn_ext_kvq` (`ours/kvq.json`, tu023) |
|---|---|---|
| VGPR / occ | 218 / 6 | 143–144 / 10 (najmniejsze warianty); 255/5 największy |
| ładunki w pętli | 11× `global_load_b128`, 176 B | 12–18 `global_load`, 52–152 B |
| bariery w pętli | **11**, bez `gl0_inv` | **0** (11 barier poza pętlą, każda z `gl0_inv`) |
| P (C→A WMMA) | przez LDS (48 `ds_load_b128` + 64 `ds_load_u16`) | `v_permlanex16` w rejestrach (22–70 permlane) |
| WMMA | 20 | 8–32 |

CK-tile `block_fmha_fwd_splitkv_pipeline_qr_ks_vs.hpp` ma ścieżkę `__gfx11__` (`warp_wmma_gemm_gfx11_utils.hpp`) z tym samym trikiem permlane i z tym samym `CK_TILE_BUFFER_RESOURCE_3RD_DWORD 0x31004000` co my (`core/config.hpp`), ale żadna instancja nie jest skompilowana w ROCm. **Wniosek: w attention nie mamy czego kopiować.**

### 2.5 Redukcje (softmax/norm/amax)

- hipBLASLt extop (`extop.json`): LayerNorm 4× `buffer_load_b128` na wątek + 3× `ds_bpermute` + 5 barier; Softmax_DT_S_MT_1_256 to drzewo przez LDS z **18 barierami**, 2 DPP; AMax 4× b128 + `ds_bpermute`. Brak `gl0_inv` (asm).
- CK reduce blockwise/threadwise (182 kernele): drzewo w LDS z barierą na każdy poziom, 1584 barier i 1584 `gl0_inv`, `buffer_load_u16/b32`, 0 DPP.
- Nasze MMVQ (tu036, 798 kerneli): 6332 DPP + 19 529 `ds_swizzle/bpermute`, prawie bez barier (346). **Lepiej niż AMD.** Ich ścieżka z barierami przegrywa z naszymi redukcjami w obrębie fali.

### 2.6 MIOpen CK WMMA (grouped conv, próbka 1371 kerneli)

`buffer_load` 17 178 vs `global_load` 1258; `b128` dominuje. 11 204 WMMA, 7893 VOPD. **0 bitów cache.** 246 `s_setprio` (CK `xdl_cshuffle_v3`): `s_setprio 1` na czas serii WMMA i `s_setprio 0` przed obsługą ładunków (`miopen_ck/co/tu080.co`, dump w §4.2). Bariery: 2136 z 2152 z `gl0_inv` (HIP `__syncthreads`).

## 3. Nasze kernele vs AMD: MMVQ (dekod N=1, weryfikacja MTP N=2..8)

Q4_K (`ggml_type 12`), tu036, `ours/ours_mmvq.json`, dumpy `ours/dump_mmvq/{0000,0001}.s`:

| ncols | VGPR | occ | ładunki w pętli | typ | B/lane/iter | `vmcnt(0)`/iter | glc dlc |
|---|---|---|---|---|---|---|---|
| 1 (nwarps…, wariant `…,2>`) | 36 | 16 | 18 = 12× `global_load_b32` + 6× `d16` | global, para VGPR adresu | 60 | 1 | nie |
| 1 (`…,0>`) | 26 | 16 | 12 global | global | 42 | 1 | nie |
| 2 | 64 | 16 | 12 buf (8× b128) | buffer | 144 | 2 | tak (4) |
| 4 | 88 | 16 | 20 buf (12× b128) | buffer | 224 | 2 | tak |
| 5 | 140 | 10 | 28 buf (18× b128) | buffer | 328 | 2 | tak (8) |
| 8 | 190 | 8 | 40 buf (24× b128) | buffer | 448 | 2 | tak |

Różnice względem Tensile:
1. **N=1 nie używa `b128` ani buforów.** Ładunki są 4 B na lane (Q4_K `vdr`), adres to 64-bitowa para VGPR na każdy strumień. Tensile: 16 B na lane, offsety w SGPR, jeden VGPR adresu.
2. **Brak prefetchu między iteracjami.** Pętla n=5: ładunki na górze, potem `vmcnt(3)→(2)→(1)→(0)` w tej samej iteracji, a następna iteracja startuje z pustym potokiem. Tensile trzyma ≥1 iterację w locie (PGR2: dwie).
3. **Bity cache:** my `glc dlc` na wagach (n≥2), AMD nigdy.
4. Rzeczy, w których mamy przewagę albo parytet: wave32, WG 32, occ 16 przy n≤4, redukcja DPP/swizzle zamiast LDS, WMMA iu8 dla n=8.

MMQ (prefill / szeroka weryfikacja), tu098/tu106, `ours/mmq_tu*.json`: gorące warianty mają 190–209 VGPR (occ 7–8). Pętla K ma 74–82 `global_load` (284–312 B/lane), **w większości `b32`, 0 buforów**, 24 WMMA, **4 `s_barrier` + 4 `buffer_gl0_inv`**, `vmcnt` aż do 38–46 w locie. Odpowiednik Tensile: `b128`-buffer, 0 `gl0_inv`, 1–2 bariery na iterację.

## 4. Porównanie barier LDS (zlecenie Main z raportu 21g)

### 4.1 Liczby (analizator kontekstu `s_barrier`: `vmcnt(0)` w 3 instrukcjach przed, `buffer_gl0_inv` tuż po)

| Kod | kernele | `s_barrier` | z `gl0_inv` po | `vmcnt(0)` przed | źródło |
|---|---|---|---|---|---|
| nasz `fattn-kvq` (tu023) | 5 | 55 | 55 (100%) | 5 | barrier_ctx |
| nasz `fattn-vec` (tu139) | 12 | 40 | 39 | 5 | 〃 |
| nasz `fattn-tile` (tu070) | 42 | 129 | 115 (89%) | 6 | 〃 |
| nasz `fattn-tile` (tu065) | 95 | 259 | 251 | 12 | 〃 |
| nasz `mmq` (tu106) | 128 | 196 | 122 | 20 | 〃 |
| nasz `gated_delta_net` (tu027) | 44 | 0 | — | — | 〃 |
| hipBLASLt HH TN (asm) | 238 | 3404 | **0** | 251 | 〃 |
| hipBLASLt extop (asm) | 11 | dziesiątki (Softmax 18) | **0** | — | `dump_extop/` |
| CK reduce (HIP) | 161 | 1584 | 1584 | 0 | 〃 |
| MIOpen CK WMMA conv (HIP, próbka) | 728 | 2152 | 2136 | 142 | 〃 |
| AOTriton attn_fwd (LLVM-Triton) | 1 | 11 | 0 | — | `aotriton/a.json` (`cache_inv` brak) |

### 4.2 Jak AMD to robi

- **Tensile/extop (asm):** goły `s_waitcnt lgkmcnt(0)` + `s_barrier`, a `vmcnt` liczony ręcznie (rolling). Z `gl0_inv` nie ma nic wspólnego, bo nie przechodzi przez model pamięci LLVM.
- **CK-tile:** `block_sync_lds()` → `s_waitcnt_barrier<kMaxVmCnt, kMaxExpCnt, lgkmcnt>()` → `s_waitcnt lgkmcnt(N)` + `__builtin_amdgcn_s_barrier()` **bez płotów** (`ck_tile/core/arch/arch.hpp:1362-1391`). Flaga `CK_TILE_EXPERIMENTAL_BLOCK_SYNC_LDS_WITHOUT_SYNC_VMEM=1` (`core/config.hpp`) celowo nie czeka na VMEM. Na gfx12 piszą wprost, że `__builtin_amdgcn_s_barrier` wstawia zbędny `s_wait_loadcnt_dscnt 0`, i rozbijają ją na `s_barrier_signal/wait`.
- **Stary CK i MIOpen-CK (`__syncthreads`):** `s_waitcnt lgkmcnt(0); s_barrier; buffer_gl0_inv`, czyli identycznie jak my (`ck/dump/0003.s:142-176`). CK v3 dodatkowo `s_setprio 1/0` wokół WMMA.
- AOTriton (Triton → LLVM z workgroup-scoped fence dla LDS) też nie emituje `gl0_inv`.

### 4.3 Co z tego dla nas

- Wariant „fence local + `s_barrier`” z 21g (wiki `kernele/bariera-lds-rdna3.md`) odpowiada praktyce CK-tile, ale jest **bezpieczniejszy**: płot workgroup/local zabrania kompilatorowi przenoszenia dostępów LDS przez barierę, a goły builtin CK-tile tego nie gwarantuje.
- **Priorytet według miejsca w pętli, nie według liczby barier:**
  1. `mmq.cuh`: 4 bariery i 4 `gl0_inv` w **każdej iteracji K** (dump `ours/dump_mmq/0000.s`, MXFP4 128: 6 barier, 6 `gl0_inv`, linie 67/691/906/988). To największy realny zysk dla prefillu i dla weryfikacji przy N>8.
  2. `fattn-tile`: 115–251 `gl0_inv`, część w pętli KV (do sprawdzenia per bariera).
  3. `fattn-vec`: 39.
  4. `fattn-kvq`: pętla KV **nie ma barier**, a 11 `gl0_inv` siedzi w epilogu (kombinacja wyników), więc zysk będzie znikomy `[INFERENCE]`.
- Warunek poprawności bez zmian: między barierami nie może być komunikacji przez pamięć globalną. Każdą barierę trzeba przejrzeć osobno, test-backend-ops + md5.

## 5. Kandydaci dla MMVQ/weryfikacji na XTX (ranking)

Kolejność: oczekiwany zysk × pewność / koszt. Nic nie było mierzone; wszystkie oczekiwania to `[INFERENCE]`.

| # | Zmiana | Gdzie | Dowód „AMD tak robi” | Koszt | Uwagi / ryzyko |
|---|---|---|---|---|---|
| 1 | **Bariera tylko-LDS (`GGML_LDS_BARRIER()`, fence local)** zamiast `__syncthreads` | `mmq.cuh` (pętla K), `fattn-tile`, `fattn-vec` | Tensile 0/14 574 `gl0_inv`; CK-tile `block_sync_lds` | S | bitowo identyczne; Strata #3064: −1.3…−5% czasu kerneli (21g) |
| 2 | **Prefetch między iteracjami (software pipelining, „PGR1/2”)** w pętli MMVQ: ładunki bloku k+1 przed liczeniem k, `vmcnt(N)` zamiast `vmcnt(0)` | `mmvq.cu`, n=1..8 | Tensile PGR2 w 65% rozwiązań, 12–63 ładunków w locie | M | +VGPR: przy n=1 zapas duży (26–36 VGPR, occ 16), przy n≥5 spadnie occ (140→?) |
| 3 | **N=1: ładunki 16 B na lane przez `buffer_load_b128`** (jak nasza ścieżka n≥2) albo przynajmniej `b64`, z offsetem w SGPR | `mmvq.cu` `vec_dot_*` dla ncols=1 (Q4_K/Q5_K/Q6_K/IQ4_XS) | hipBLASLt `grvwA=8` w 1759/2182; 0 `global_load` w Tensile | M–L | zmienia mapowanie lane→blok (VDR) i kolejność sumy; trzeba sprawdzić bitowość z verify |
| 4 | **A/B: zdjąć `glc dlc` z wag** w n≥2 | `mmvq.cu` (ścieżka buffer) | AMD 0 bitów NT w 2182 + 7461 + CK | XS | wcześniejsze pomiary u nas mogły uzasadniać glc/dlc (rr-hip) – sprawdzić przed zmianą |
| 5 | `s_setprio 1` na serię WMMA, `0` przy ładunkach | `mul_mat_vec_q_wmma`, MMQ, kvq | CK v3 (246 wystąpień) | S | korzyść tylko przy wielu falach na SIMD |
| 6 | Split-K (GSU 2–4) z deterministycznym drugim kernelem dla małej liczby wierszy | MMVQ przy małym M (np. lm_head z wąskim N?) | hipBLASLt GSU=4 w 162 rozw. + `PostGSU*` | M | zmienia kolejność sumowania (bitowość vs nie-split); dodatkowy launch |
| — | Nie przenosić: rocBLAS gemvt, redukcje przez LDS (CK/extop), AOTriton FA, brak VOPD/`s_delay_alu` w Tensile (to cecha asm, nie lekcja) | | | | |

Kontrole po wdrożeniu (dla Main): `test-backend-ops -o MUL_MAT`/`FLASH_ATTN_EXT`, md5 wyjść verify (bitowość), rocprof per kernel przed/po, ISA: `isa_profile.py --kernel mul_mat_vec_q …` (oczekiwane `vmcnt` ≠ 0 na końcu pętli dla #2, 0 `gl0_inv` w pętli MMQ dla #1).

## 6. Ograniczenia

- Profil statyczny ISA, bez pomiarów czasu. Liczby „w pętli” dotyczą jednego (najgorętszego) bloku z skokiem wstecz.
- MIOpen-CK: próbka co 20. TU. Z hipBLASLt profilowane tylko TN (`Alik_Bljk`), czyli nasz układ.
- rocBLAS `MT64x1` (Tensile GEMV, GSU do 60) istnieje tylko w fallbackach NN/`Ailk_Bjlk` (symbole w `.hsaco`); profil `rocblas_mt64x1.json` pusty, bo w układzie TN tego kafla nie ma.
- rocWMMA i CK-tile nie skompilowane: ograniczenie CPU/temperatury, źródła wystarczyły.

## Do bazy wiedzy

- hipBLASLt gfx1100 (ROCm 10.0, 2182 rozwiązań): nonTemporalA/B/D=0 w 100%, DirectToLds=0, streamK=0, PGR2 w 1418, GSU=4 w 162; kernele TN: 100% `buffer_load`, 0 glc/slc/dlc, 0 VOPD, 14 574 `s_barrier` i 0 `buffer_gl0_inv` (`~/qwen-opt/re/amd/hipblaslt/alik_bljk.json`).
- Skinny-N w hipBLASLt = kafle MT×16 na `v_wmma_*_16x16x16` (N dopełniane do 16); MT32x16x128: 256 VGPR, occ 5, 12 `buffer_load_b128`/iter, offsety w SGPR, prefetch 2 iteracje (`hipblaslt/dump_mt32x16/0000.s:1104-1217`).
- rocBLAS `gemvt_*` fp16 na gfx1100: wąskie `global_load_b32`/u16, 0 `b128`, nie jest wzorcem dla GEMV (`~/qwen-opt/re/amd/rocblas_sel.json`).
- CK-tile `block_sync_lds` = `s_waitcnt lgkmcnt` + `__builtin_amdgcn_s_barrier` bez płotów (`/opt/rocm/include/ck_tile/core/arch/arch.hpp:1362-1391`); stary CK/MIOpen-CK przez `__syncthreads` emituje `gl0_inv` po 1584/1584 i 2136/2152 barierach.
- Nasze: `gl0_inv` po 55/55 barierach `fattn-kvq` (wszystkie poza pętlą KV), 39/40 `fattn-vec`, 115/129 `fattn-tile` tu070, 122/196 `mmq` tu106; pętla K MMQ ma 4 bariery + 4 `gl0_inv` (`~/qwen-opt/re/amd/ours/mmq_tu106.json`).
- Nasze MMVQ Q4_K n=1: 18 `global_load` (12× b32 + 6× d16), 60 B/lane/iter, 0 `b128`, `vmcnt(0)` co iterację; n≥2: `buffer_load_b128 glc dlc`, bez prefetchu między iteracjami (`~/qwen-opt/re/amd/ours/ours_mmvq.json`).
- AOTriton attn_fwd gfx1100 D128 M16N16: 218 VGPR, occ 6, 11 `global_load_b128` + 11 barier na iterację, P przez LDS; nasz `fattn-kvq` 144 VGPR, occ 10, 0 barier w pętli, P przez `v_permlanex16` (`aotriton/a.json`, `ours/kvq.json`).
- Narzędzia RE AMD: `~/KERNEL/tools/re/kpack_extract.py` (TheRock .kpack), `tensile_lib.py` (msgpack .dat/.zlib bez zależności), `fatbin_split.py` (CCOB + bundle v2), `aotriton_extract.py` (AKS2/XZ), `isa_profile.py` (metadane + mix + pętla, obsługa asm Tensile).
