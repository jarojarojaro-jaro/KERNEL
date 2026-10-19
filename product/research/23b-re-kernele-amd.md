# 23b — RE kerneli AMD (gfx1100) vs nasze MMVQ / weryfikacja / atencja

Autor: ResVendorAmd3 (na danych ResVendorAmd/2) · 2026-10-19 · tylko CPU (`llvm-objdump --mcpu=gfx1100`, odczyt metadanych), zero GPU.
Artefakty (poza repo): `~/qwen-opt/re/amd/` (kody obiektów, dumpy `.s`, profile `*.json`). Narzędzia: `~/KERNEL/tools/re/{kpack_extract,fatbin_split,isa_profile,tensile_lib,aotriton_extract}.py`.
Źródła: rocBLAS + hipBLASLt z `.kpack`/`TensileLibrary_*_gfx1100.co` (2182 rozwiązań, profil 1025 kerneli TN), MIOpen CK WMMA (`libMIOpenCKGroupedConv_gfx1100.so`, 1371 kerneli), CK reduce (`libdevice_reduction_operations.a`), AOTriton `attn_fwd` gfx110x (z torch w `.venv-train`), nasze `libggml-hip.so` z `~/llama-opt` (tu036 MMVQ, tu023 kvq, tu098/106 MMQ). hipBLAS nie ma kodu GPU (`libhipblas.so.3.6` bez `.hip_fatbin`, GEMV = rocBLAS). rocWMMA i CK-tile są tylko nagłówkami.

## Werdykt

**AMD nie ma lepszego kernela GEMV ani skinny-GEMM dla N=1..16 na gfx1100.** Nasze MMVQ wielokolumnowe stosuje już wszystkie ich techniki ładowania: zasób bufora w SGPR + `soffset`, `buffer_load_b128`, `waves_per_eu`, VOPD i DPP. Do przeniesienia zostały tylko trzy rzeczy:
1. Szerokie ładowania bufora w **ścieżce n=1**. Ta ścieżka to nadal upstream: `global_load_b32` i `d16` przy 3.3 B na instrukcję.
2. Szeroki loader dla **Q6_K n=2..6**, który nie ma ani jednego b128.
3. Bariera tylko-LDS. Usuwa `buffer_gl0_inv`, ale liczy się w prefillu, nie w dekodowaniu.

Reszta odpada: bity cache, prefetch PGR2, wave64, split-K i rocBLAS gemv jako wzór. Powody są w tabeli „Odrzucone”.

## Liczby (statycznie, główna pętla)

| kernel | VGPR / occ | ładowania na iterację | B/lane/it. | B/instr. | vmcnt | bariera → gl0_inv | cpol |
|---|---|---|---|---|---|---|---|
| nasz MMVQ Q4_K n=1 (rows 2) | 36 / 16 | 18 global (12 b32 + 6 d16), 5 par adresów VGPR | 60 | **3.3** | 17→0 w każdej it. | – | – |
| nasz Q5_K n=1 / Q6_K n=1 | 43 / 16, 30 / 16 | 22 / 14 global | 76 / 40 | **3.5 / 2.9** | →0 | – | – |
| nasz Q4_K n=2 / n=5 / n=8 | 64/16, 140/10, 190/8 | 12 / 28 / 40 buffer (8 / 18 / 24 b128) | 144 / 328 / 448 | 12.0 / 11.7 / 11.2 | →0 (2×) | – | glc dlc |
| nasz **Q6_K n=2 / n=5** | 84/16, **250/5** | 26 / **60 buffer, 0 b128** | 148 / 336 | **5.7 / 5.6** | →0 | – | glc dlc |
| nasz IQ4_XS n=1 / n=5 | 43/16, 166/9 | 6 (3 b128) / 23 (14 b128) | 57 / 266 | 9.5 / 11.6 | →0 | – | – / glc dlc |
| hipBLASLt `Cijk_Alik_Bljk_HHS_…MT32x16x128` (skinny N≤16, WMMA f16, N dopełniane do 16) | 256 / 5 | 12 `buffer_load_b128`, jeden voffset + `soffset` s66..s75 | 192 | 16 | **kroczące `vmcnt(11)`**, nigdy 0 (pętla @0x271CE0) | 14574 barier / **0 inv** | brak |
| rocBLAS `gemvt_warp_reduce<false,256,int,_Float16,float,float>` (N=1) | 20 / 16 | 6 global d16 | 16 | 2.7 | →0 | tak (`__syncthreads`) | brak |
| nasz kvq D128 (decode FA) | 144 / 10 | 14 global (9 b128 w kernelu) | 88 | – | max 5 | 55/55 inv, **wszystkie poza pętlą KV** | – |
| AOTriton `attn_fwd` D128 M16N16 | 218 / – | 11 global b128 | 176 | 16 | max 1 | 11 w pętli, 0 inv | – |
| nasze MMQ (prefill), np. tu098 | 190 / 8 | 82 global, głównie b32 | 312 | 3.8 | max 38 | **4 bariery + 4 inv na iterację** | – |
| MIOpen CK WMMA (1371 kerneli) | – | 17178 buffer / 1258 global | – | – | – | 6023 / **0 inv**; `s_setprio 1/0` wokół serii WMMA | brak |

Cache-policy u AMD: nonTemporalA/B/D = 0 we wszystkich 2182 rozwiązaniach hipBLASLt; glc, slc i dlc = 0 w 1025 profilowanych kernelach i w CK. DirectToLds = 0, PGR2 w 382 z 529 kafelków skinny. Wszystkie kernele AMD na gfx1100 są wave32.

Bariera: CK-tile `block_sync_lds()` to `s_waitcnt lgkmcnt(0)` + `__builtin_amdgcn_s_barrier()`, bez fence (`/opt/rocm/include/ck_tile/core/arch/arch.hpp:1365-1392`), więc nie emituje `buffer_gl0_inv`. Stare CK reduce na HIP `__syncthreads` ma 1584/1584 barier z `gl0_inv` (to samo, co znalazł raport 21g).

Little's law, czyli dlaczego prefetch nie pomoże: przy 0.9 TB/s i założonej latencji ~1 µs `[INFERENCE]` w locie musi być ~0.9 MB, czyli ~4.7 KB na SIMD (192 SIMD). Mamy 1.9 KB na falę × 16 fal = 31 KB (n=1) oraz 10.5 KB × 10 = 105 KB (Q4_K n=5). Brak równoległości pamięci nie jest więc wąskim gardłem. Zostaje koszt wydawania małych ładowań: ATT z 16g pokazał „zator wydawania małych ładowań” w down, a 85% czasu fali w `vmcnt`.

## Kandydaci (ranking)

| # | zmiana | szacowany zysk (arytmetyka) | wysiłek / ryzyko | eksperyment GPU i kryterium kill |
|---|---|---|---|---|
| 1 | **n=1 przez loader `mmvq_ld` (buffer b128 + `waves_per_eu`)** dla Q4_K/Q5_K/Q6_K oraz MoE n=1. Układ z multi-col jest bitowo zgodny (12-bit-exact). Liczba ładowań na iterację spada z 18 do ~6, pięć par adresów VGPR zastępuje jeden voffset. | Narzut ponad strumień: draft MTP 1.3 ms/krok, plain 4.45 ms/krok, LFM 718 µs/token (23f §3.2–3.3). Odzysk 10–25% tych pul `[SZACUNEK]`: MTP +0.5–1.2%, plain +2–5%, LFM +2–5%. | średni (n=1 vec_dot musi przejąć mapowanie lane → 16 B ciągłych) / niskie (bitowo). Lekcja K1: bez `waves_per_eu` było −5…−40%. | rocprofv3 w modelu: Q4_K n=1 `ffn_up` 5120×17408 oraz LFM gate+up. **Kill:** kernel szybszy o < 3% albo `llama-bench tg128` plain < +0.7%. |
| 2 | **Q6_K n=2..6 z b128** (ql/qh jak Q4_K). Dziś Q6_K n=5 ma 60 ładowań na iterację, 0 b128, 250 VGPR i occ 5. | Głowica Q6_K to 1.043 GB/krok w weryfikacji n=5. Przejście z 700 do 850 GB/s daje 1.49 → 1.23 ms, czyli −0.26 ms/krok (+0.9% MTP) `[SZACUNEK]`; więcej, jeśli w UD-Q4_K_XL są inne tensory Q6_K. | średni / niskie (bitowo) | Najpierw zmierzyć GB/s głowicy n=5 w modelu. **Kill:** już ≥ 820 GB/s albo po zmianie < +0.5% spec_sweep. |
| 3 | **Bariera tylko-LDS** (`s_waitcnt lgkmcnt(0)` + `s_barrier`, jak CK-tile) w MMQ i fattn-tile. Właściciel: OptLdsBarrier. | Decode: kvq ma 55 barier, wszystkie poza pętlą KV, więc ~0%. Prefill: MMQ ma 4 `gl0_inv` na iterację, szacunek 0–2% pp `[SZACUNEK]`. | niski / niskie (bitowo, 21g) | pp4096 ABBA. **Kill:** < +0.5%. |

## Odrzucone (z dowodem)

| pomysł | dlaczego nie |
|---|---|
| bity cache (slc/nt) | AMD nie używa ich nigdzie. U nas GLC\|DLC multi-col dało zmierzony zysk (K1), a slc\|dlc w n=1 Q5_K pogorszyło (12.90 → 14.42 µs). |
| prefetch PGR2 / kroczące vmcnt | Kroczące vmcnt w hipBLASLt wymaga etapu w LDS, 256 VGPR i occ 5. Nasz pipelining Q4_K/Q5_K/IQ4_XS dał wynik ujemny (K1), prefetch w GU_BLOCK tylko +0.33% (16g), a z prawa Little'a wynika, że w locie jest dość danych. |
| split-K (rocBLAS MT64x1 GSU 3..60, hipBLASLt GSU 4) | Zmienia kolejność sum, co łamie bitowość spekulacji. Siatki dużych macierzy nie są niedopełnione. |
| WMMA dla n ≤ 8 | hipBLASLt dopełnia N do 16, więc przy n=5 marnuje 69% WMMA. Nasze WMMA iu8 działa od 9 kolumn (Q6_K od 7) i jest strojone. |
| wave64, VOPD, DPP | AMD na gfx1100 ma 100% wave32. VOPD = 0 w hipBLASLt, my już mamy VOPD i DPP. |
| rocBLAS gemv jako wzór | Ładowania b16, `vmcnt(0)` w każdej iteracji, `gl0_inv` — gorszy od naszego n=1. |
| `s_setprio` wokół WMMA (CK) | Dotyczy prefillu i kvq, spodziewany zysk ≤ 1% bez dowodu. Wraca do kolejki dopiero, jeśli pkt 3 coś da. |

## Do bazy wiedzy

- Vendorowe kernele AMD dla gfx1100 (hipBLASLt, rocBLAS, MIOpen CK, AOTriton) nie mają lepszego GEMV ani skinny-GEMM. Nasze MMVQ wielokolumnowe stosuje już ich techniki ładowania: rsrc + soffset, b128, `waves_per_eu`. Źródło: 23b.
- Nasza ścieżka **MMVQ n=1 to wciąż upstream**: `global_load_b32` i `d16`, 2.9–3.5 B na instrukcję VMEM (Q4_K/Q5_K/Q6_K). Multi-col ma 11–12 B na instrukcję. To kandydat nr 1 dla draftu MTP, plain i LFM MoE n=1.
- **Q6_K n=2..6 nie ma żadnego b128**: n=5 to 60 ładowań na iterację, 250 VGPR, occ 5.
- AMD nie używa bitów cache (nonTemporal = 0 w 2182 rozwiązaniach hipBLASLt; glc/slc/dlc = 0 w kodzie).
- `block_sync_lds` z CK-tile = `lgkmcnt(0)` + `s_barrier` bez fence, więc bez `buffer_gl0_inv` (`ck_tile/core/arch/arch.hpp:1389`). W kvq wszystkie 55 barier są poza pętlą KV, więc w dekodowaniu ta zmiana nic nie daje. W MMQ są 4 bariery z `gl0_inv` na iterację.
- Narzędzia RE AMD: `~/KERNEL/tools/re/` (kpack, fatbin, profil ISA, msgpack Tensile, AOTriton).
