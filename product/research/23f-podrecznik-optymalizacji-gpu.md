# 23f — Podręcznik optymalizacji GPU A–Z (lokalna inferencja LLM: RX 7900 XTX + konsumenckie NVIDIA)

2026-10-19 · ResGpuHandbook · tylko CPU (raporty, wiki, kod, statyczne ISA), zero GPU.
Dla kogo: świeży agent RSI-F/fabryki, który ma projektować, recenzować albo mierzyć kernele forka (`amd-opt`; źródła `~/llama-master` = produkcja `f61994f58`).
Część I (werdykt, ranking, liczby) to wersja „na 2 strony”; część II to ściąga referencyjna; część III to checklista.
Oznaczenia: `[ISA]` statyczny odczyt kodu, `[SZACUNEK]` rachunek, `[INFERENCE]` wniosek bez pomiaru, `[ZEWN]` dokumentacja producenta. Źródła RE: 21l (narzędzia, zasoby 7832 kerneli), 23b/23b2 (kernele AMD), 23c (kernele NVIDIA), 23d (runtime/firmware AMD), 23e (silniki konkurencji).

---

# Część I — werdykt, ranking, liczby

## 1. Werdykt

1. **Decode batch 1 to strumień bajtów.** Qwen3.8-27B plain: 16.82 GB/krok, 75.7% pasma XTX (23.15 ms vs 17.5 ms podłogi); LFM2.5-24B-A2B: 1.777 GB/token, 54% (3.40 ms vs 1.85 ms) (`18:116`, `15a:13-14`). Reszta to pula „DRAM bezczynny”: rampy/ogony kerneli, małe kernele, granice, host.
2. **Vendorzy i konkurenci nie mają lepszej pętli GEMV niż nasza wielokolumnowa** (hipBLASLt, rocBLAS, CK, AOTriton — 23b; cuBLASLt, exllamav3, FlashInfer, Marlin — 23c; hipfire, tqLLM, Magnitude — 23e). Przewaga hipfire (54.3 vs 43.2 t/s plain) to ~2.7 ms mniej bajtów (4.25 bpw) + ~0.8 ms fuzji, nie ISA (23e).
3. **Nasza najsłabsza gorąca ścieżka to MMVQ n=1** (plain, draft MTP, cały LFM): wciąż upstreamowa — `global_load_b32/d16` przy **3.3 B na instrukcję VMEM**, pełny drenaż `vmcnt(0)` w każdej iteracji, redukcja przez 5× `ds_bpermute` + `lgkmcnt(0)`; ścieżka 5-kolumnowa ma `buffer_load_b128` (11.7 B/instr.) i DPP (`[ISA]` §II.4; 23b; `mmvq.cu:180-187` „for the multi path”).
4. **Największa pojedyncza dźwignia na XTX to bezpieczne PM4** (+13% LFM, +5% Qwen MTP względem PM4-off): firmware MEC potwierdza, że PRIV dla fal taśmy ustawiamy tylko my (`GGML_HIP_PM4_WA=2`, 23d). Bez PM4 podłoga to 2.08 µs na pakiet AQL — praca firmware, nie do obejścia flagami HIP (23d §2).
5. **Na NVIDIA tanie i bitowe:** trigger PDL w gęstym MMVQ (SASS: `ACQBULK` bez `PREEXIT`, 23c), prefetch/`evict_first` na strumieniu wag.
6. **Nie robić** (zmierzone/wykazane negatywnie): PM4-PDL i flagi/tickety między kernelami na RDNA3, prefetch do L2/MALL osobnym dispatchem, nontemporal, wave64/VOPD w decode, split-K w MMVQ, WMMA dla n ≤ 8, TMA/FP8/FP4 w decode, pełny megakernel warstwy (§II.10, `wiki/metody/wyniki-negatywne.md`).

## 2. Co jeszcze możemy poprawić — ranking

Wartość ≈ zysk × p / dni. Baza: Qwen MTP 27.74 ms/krok (109 t/s), Qwen plain 23.15 ms, LFM 3.40 ms/token z PM4 (3.86 bez). Eksperymenty uruchamia później fabryka/RSI-F (`GGML_HIP_PM4=0` dla wszystkiego poza #1).

| # | zmiana | platforma | zysk (arytmetyka) | p | dni | bitowe | minimalny eksperyment → kill | źródło |
|---|---|---|---|---|---|---|---|---|
| 1 | **PM4 z `WA=2`** (PRIV=1, RESTART=0, inicjator bez ORDERED_APPEND); `WA=3` (+ORDER_MODE, `PGM_HI|=0x100`) tylko po faultcie | XTX | odzysk PM4: LFM 3.86 → 3.40 ms (**+13.5%**), Qwen MTP 103.7 → 108.8 t/s (**+4.9%**) | 0.6 | (Pm4Fix) | tak | S4: ≥ 1000 wstrzykniętych ewikcji w taśmie → **pierwszy fault = PM4 zostaje off** | 23d #1–2; 17 |
| 2 | **MMVQ n=1 przez loader `mmvq_ld`**: buffer b128 + SGPR offset, `waves_per_eu`, bez `vmcnt(0)` na końcu pętli, redukcja DPP | XTX (potem NVIDIA) | odzysk 10–25% puli n=1: plain 4.45 ms → **+2–5%**; draft MTP ~1.3 ms → **+0.5–1.4%**; LFM gęste n=1 ~342 µs (in_proj+conv 145, out_proj 92, q/k/v 83, FFN 22) → **+2–4%** | 0.35 | 3 | tak (ta sama kolejność sum per lane i to samo drzewo redukcji) | mikrobench in_proj+conv 6144×2048 Q5_K + `ffn_up` 5120×17408 Q4_K w 3 procesach, potem rocprofv3 w modelu → **kill: kernel < −3% albo tg128 plain/LFM < +0.7%**, md5 ≠ baza | §II.4; 23b #1 |
| 3 | **Jedno przejście po KV dla wszystkich kafli N×G** w weryfikacji (dziś `ceil(6·5/16)` = 2 przejścia) | XTX | −2.08 GB/krok @113k → MTP @94–113k **+8%** | 0.5 | 5 | tak | spec_sweep @94k ABBA → kill < +3% | 18 #5 |
| 4 | **Fuzje poza GEMV wg listy hipfire** (rmsnorm+rotate w prologu, qkvza jednym GEMV, moe_down+combine+rmsnorm, conv1d+silu+qknorm) | XTX | górna granica ~0.8 ms → Qwen plain **≤ +3.5%**; każdy usunięty kernel −2.1…−3.3 µs (AQL) / −0.5…−0.9 µs (PM4) | 0.4 | 2–5 | zwykle | najpierw diff listy kerneli/token vs hipfire (CPU) → kill: < 0.3 ms w małych kernelach (rocprof) | 23e #3; 23d #4 |
| 5 | **PDL: `pdl_lc` na starcie gęstego MMVQ + prefetch/ładowanie wag przed `pdl_sync`** | 5060 Ti, 5090 | LFM +1.1–4.6% / +2.5–11%; Qwen +0.7–2.6% / +1.6–7% | 0.35 | 1.5 | tak | krok 0: `GGML_CUDA_PDL=0/1` ABBA; potem zmiana → kill < +1.5% LFM tg128 (5060 Ti) | 21b E1; 23c #1 |
| 6 | **Q6_K n=2..6 z ładowaniami b128** (dziś n=5: 60 ładowań/it., 0 b128, 250 VGPR, 5 fal) | XTX | głowa 1.043 GB/weryfikację: 700 → 850 GB/s = −0.26 ms/krok → **+0.9% MTP** | 0.4 | 2 | tak | najpierw GB/s głowy n=5 w modelu → kill: już ≥ 820 GB/s albo < +0.5% spec_sweep | 23b #2 |
| 7 | **MMVQ ncols=5 ≤ 120 VGPR** (10 → 12 fal) albo weryfikacja jako 4+1 (ncols=4: 89 VGPR, 16 fal) | XTX | klif VGPR 89 → 140 przy 4 → 5 kolumnach; zysk `[INFERENCE]` 0–3% czasu MMVQ weryfikacji | 0.3 | 0.5 | tak | `amdgpu_waves_per_eu(12)`, `co_stats.py` spill = 0 → ABBA krok weryfikacji → kill: spill > 0 albo < +1% | 21l A1 |
| 8 | Lookup dla LFM (code-edit) / ogon W16 na CUDA | XTX / NVIDIA | ×2.3–2.8 code-edit LFM; 3090 code-edit 105 → ~200 t/s | 0.5–0.6 | 1–2 | n/d | copy_bench `mvs` → kill < +30% | 18 #1–2 |
| 9 | Serwer wielostrumieniowy z batched MTP | XTX | ×1.6–1.8 wall-clock roju agentów (37% czasu ≥ 2 żądania) | 0.5 | 5+ | n/d | replay sesji omp → kill < ×1.2 | 18 #4 |
| 10 | Hinty strumienia na NVIDIA: prefetch L2 w pętli MMVQ dla 2–8 kolumn; `ld.global.L1::evict_first` na wagach, `evict_last` na q8_1; L2 persisting window (głowa LFM 215 MB) | NVIDIA | 0…+3% weryfikacji; 0–2%; LFM +1–2% (4090/5090) | 0.3–0.4 | 0.5–1 każde | tak | test-backend-ops perf ne11 = 1..8, potem ABBA → kill < +1% / < +0.5% | 21b E3–E4; 23c #2–3 |
| 11 | Bariera tylko-LDS (`lgkmcnt(0)` + `s_barrier`, jak CK-tile) w MMQ i fattn-tile | XTX | prefill: MMQ ma 4 `gl0_inv` na iterację K → 0–2% pp | 0.4 | 1 | tak | pp4096 ABBA → kill < +0.5% (właściciel: OptLdsBarrier/ResEnginesNew) | 23b #3; 23b2 §4 |
| 12 | Trwały blok MoE (dataflow, tagged pairs, bounded spin) — **tylko jeśli #1 padnie** | XTX | LFM +8–10% względem PM4-off | 0.3 | 10–12 | tak | mikrobench trwałej siatki → kill: < 1.5 µs oszczędności/granicę albo wygaśnięcie spinu w 10⁵ replayów | 21b #6 |
| 13 | Mniej bajtów, stratnie: 4.25 bpw (IQ4_KS) dla Qwena; stan GDN w Q8 | XTX | +14–17% (MTP/plain); stan GDN ~−0.24 ms → +1% | 0.4 / 0.3 | 2 / 2 | **nie** (KLD) | bramka KLD z kanarkami → kill: ΔKLD > 2σ / > 0.005 | 18 #9; 23e #2, #5 |
| 14 | Narzędzia-bramki: physics-floor check w weryfikatorze; `co_stats.py`/`isa_kstat.py` diff per łatka; offline audyt taśmy PM4 (`umr`) | wszystkie | wiarygodność, mniej regresji typu „hak spilluje” | 0.9 | 0.5 każde | n/d | — | 21b #8; 21l A2–A3 |

Już mamy (nie proponować): rollback GDN przez przeliczenie zamiast snapshotów (23e #1 = nasze S4/`GATED_DELTA_NET_LAG`, 0033–0036, `LLAMA_GDN_REPLAY`), kernargi PM4 w VRAM, `GLC|DLC` na wagach weryfikacji, `waves_per_eu`, DPP/VOPD w multi-col i MMQ, `kvq` (GQA jednym przejściem, P przez `v_permlanex16` jak AOTriton).

## 3. Liczby, które trzeba znać

| wielkość | wartość | źródło |
|---|---|---|
| pasmo XTX / realny strumień | 960 / ~900 GB/s (789–925) | `15a:121` |
| granica kernela: graf HIP / podłoga AQL / taśma PM4 / bariera trwałej siatki | 2.75 / 2.08 / 0.46–0.86 / 0.48–0.77 µs | `wiki/metody/mikrobench-granicy-kernela.md`; 23d |
| kernargi w pamięci hosta | +1 µs/dispatch | `wiki/rocm/pm4.md` |
| hand-off flagą/ticketem zamiast granicy (1024 bloki) | −0.11 µs (94% zysku zjada synchronizacja) | 16a X1 |
| Qwen: wagi plain / głowa Q6_K / blok MTP / stan GDN / KV q4_0 | 16.48 GB / 1.043 GB / 0.351 GB / 151 MB f32 (R+W) / 18 432 B/token | `18:103-112` |
| Qwen: dispatche na krok / kernele weryfikacji | 807–919 / ~830 (z 2156) | `15a:155`; `hip-graph-narzut.md` |
| LFM: aktywne bajty / dispatche / narzut matvec | 1.777 GB / 304 / 718 µs (gate+up 247, in_proj+conv 145, down 129, out_proj 92) | `15a:121`; `16g:§1` |
| LFM KV q8_0 / głowa | 10 880 B/token / 215 MB (12.1%) | `18:597` |
| Little's law (600 ns) | ~6 KB w locie/CU XTX; 6.8 KB/SM 3090; 7.5 KB/SM 5060 Ti | `21b:82` |
| ATT: % czasu fali w `s_waitcnt vmcnt` | gate+up 85%, in_proj+conv 75–83%, down 37–45% (+33–43% wydawanie VMEM) | `16g:§1` |
| koszt 1 ms/krok | ≈ +3.6% t/s Qwen MTP; ≈ +4.3% Qwen plain | rachunek |
| szum A/A (ten sam label, ta sama sesja) | 0.09% ms/krok (mediana); MDE ~0.2–0.3% | `wiki/metody/pomiar-abba.md` |

---

# Część II — ściąga referencyjna

## II.1 RX 7900 XTX (gfx1100)

| element | wartość | konsekwencja |
|---|---|---|
| CU / WGP / SIMD | 96 CU = 48 WGP; CU = 2× SIMD32 | ≥ 96·k bloków; **nie** dokładnie 3072 (pełna pojemność → bimodalne czasy, 0062) |
| fala | wave32 (wszystkie kernele AMD na gfx1100 są wave32, 23b) | wave64 tylko dla kodu VALU-bound |
| VGPR | 1536/lane/SIMD, ≤ 256/fala; **fale/SIMD = min(16, ⌊1536 / roundup(VGPR, 24)⌋)** (zweryfikowane z `; Occupancy`, 21l) | progi: ≤ 96 → 16, ≤ 120 → 12, ≤ 144 → 10, ≤ 168 → 9, ≤ 192 → 8, ≤ 216 → 7, ≤ 240 → 6, 241–256 → 5 |
| LDS | 128 KiB/WGP, ≤ 64 KiB/WG, granulat 512 B | firmware odrzuca > 64 KiB (23d) |
| cache | L0 per CU (linia 128 B), GL1 per shader array, L2 6 MiB, MALL 96 MiB (niesterowalny z HIP) | MALL nie pomaga decode (odległość reużycia 16.8 GB / 1.8 GB ≫ 96 MB) |
| obliczenia | FP32 61 TFLOPS dual-issue; WMMA FP16/BF16/IU8 ≈ 123 T, IU4 ≈ 246 T (na ALU SIMD, A/B zduplikowane) | WMMA = przepustowość VALU dual-issue |
| brak | FP8/FP4, PDL (tylko enum), TMA/async copy, DynDataPrefetch (0 regionów < gfx12.5) | |
| instrukcje | `v_dot4_i32_iu8`, `v_wmma_*_16x16x16`, DPP/`permlanex16`, VOPD (`v_fma_mix`/`v_cvt` nie w parze), `buffer_load_b128` + SGPR rsrc/soffset, bity `GLC/DLC` | |
| bariera | HIP `__syncthreads()` = `s_barrier` + `buffer_gl0_inv` (u nas po 93–100% barier); CK-tile `block_sync_lds` = `lgkmcnt(0)` + `s_barrier` bez inwalidacji | §I.2 #11 |
| dispatch | MEC czyta KD (4 odczyty), sanityzuje RSRC1 (`& 0xe4aff3ff`, PRIV z flagi kolejki), składa user SGPR, inicjator `0x1065|W32<<15`; `DISPATCH_DIRECT` w IB bierze RSRC1 jak jest | własny PM4 musi ustawić PRIV=1 (23d) |

## II.2 Konsumenckie NVIDIA

| karta | arch | SM | GB/s | L2 | warpy/SM; smem/SM; /blok | PDL | TMA | FP8 / FP4 |
|---|---|---|---|---|---|---|---|---|
| RTX 3060 | sm_86 | 28 `[ZEWN]` | 360 `[ZEWN]` | 3 MB `[ZEWN]` | 48; 100 KB; 99 KB | — | — | — |
| RTX 3090 | sm_86 | 82 | 936 | 6 MB | 48; 100 KB; 99 KB | — | — | — |
| RTX 4090 | sm_89 | 128 | 1008 | 72 MB | 48; 100 KB; 99 KB | — (cc < 9.0) | — | tak / — |
| RTX 5060 Ti | sm_120 | 36 | 448 | 32 MB | 48; 128 KB; 99 KB | tak | tak, bez multicast | tak / tak (`sm_120a`) |
| RTX 5090 | sm_120 | 170 | 1792 | 96 MB (persist ≤ 60) | 48; 128 KB; 99 KB | tak | j.w. | tak / tak |

Źródła: `21b:59-60,72-80`; sm_120 nie ma tcgen05/TMEM, wgmma, 2-CTA, multicast (FA3/FA4/DeepGEMM się nie przenoszą). Occupancy: warpy/SM = min(48, ⌊65536 / roundup(rej. × 32, 256)⌋, limit bloków/smem).
Mapowanie PTX → SASS (23c, kalibracja): `L1::evict_first` → `LDG.E.EF`, `evict_last` → `.EL`, `L1::no_allocate` → `.NA`, `.nc` → `.CONSTANT`, `prefetch.global.L2` → `CCTL.E.PF2`, `griddepcontrol.launch_dependents` → `PREEXIT`, `griddepcontrol.wait` → `ACQBULK`, `cp.async.bulk.prefetch.L2` → `UBLKPF.L2` (sm_120a).

| pojęcie | RDNA3/HIP | NVIDIA/CUDA |
|---|---|---|
| wymiana w fali | DPP, `permlanex16` (bez LDS); `ds_bpermute`/`ds_swizzle` (przez LDS) | `__shfl_*_sync`, `redux.sync` |
| macierze | WMMA 16×16×16 na SIMD | `mma.sync` m16n8kX, `ldmatrix`, `movmatrix` |
| strumień poza cache | `GLC|DLC` | `evict_first`, `no_allocate` |
| async copy | brak (gfx1250+) | `cp.async` (sm_80+), TMA (sm_90+) |
| tani launch | taśma PM4, trwała siatka | graf CUDA, PDL (sm_90+) |
| LLC | MALL (niesterowalny) | L2 persisting window |
| zasoby kernela | `.amdhsa_next_free_vgpr`, `; Occupancy`, `llvm-readelf --notes` | `ptxas -v`, `cuobjdump -res-usage` |

## II.3 Roofline i bajty

- Podłoga kroku = bajty przebiegu / BW; przy spekulacji bajty liczymy **na przebieg wag**, t/s = tok/krok ÷ ms/krok (błąd „112% peaku”).
- Rozkład najpierw na tok/krok × ms/krok (Magnitude wygrywa code-edit 7.88 vs 4.92 tok/krok przy wolniejszym kroku 50.0 vs 46.5 ms, `16i:§0.1`).
- Zysk kernela ≤ jego udział w puli; Qwen plain 76% → pełny megakernel najwyżej +3–6%.
- Projekcja karty: narzut stały nie skaluje się z pasmem (5090 LFM 435–571 t/s = 37–48% pasma, `21b:§3.1`) → techniki przeciw bańkom są tam warte ~2×.
- Physics-floor: czas kernela < bajty/BW = błąd pomiaru.

## II.4 Occupancy, ładowania, latencja — nasze kernele `[ISA]`

Źródło: `~/opt/isa101/v100/*.s` (produkcja `f61994f58`, ROCm 10.0) przez `~/KERNEL/tools/re/isa_kstat.py`; pętle i B/instr. z 23b (niezależnie na `libggml-hip.so` z `~/llama-opt`).

| kernel | VGPR / fale | ładowania VMEM na iterację | B/instr. | czekanie | redukcja |
|---|---|---|---|---|---|
| MMVQ Q4_K n=1 rows2 (produkcja n=1) | 36 / 16 | 18 global (12 b32 + 6 d16), 5 par adresów 64-bit w VGPR | 3.3 | `vmcnt(17)…(0)` w każdej iteracji | 5× `ds_bpermute` + `lgkmcnt(0)` |
| MMVQ Q5_K n=1 rows2 (`.LBB271_9`) | 43 / 16 | 22 (b32 + d16) | 3.5 | `vmcnt(20)…(0)` | j.w. |
| MMVQ Q6_K n=1 rows2 | 30 / 16 | 14 | 2.9 | → 0 | j.w. |
| MMVQ Q4_K n=2 / 5 / 8 | 64/16, 140/10, 190/8 | 12 / 28 / 40 buffer (8 / 18 / 24 b128) | 12.0 / 11.7 / 11.2 | → 0 (2×), `glc dlc` | DPP (21 instr.) |
| MMVQ **Q6_K n=5** | **250 / 5** | 60 buffer, **0 b128** | 5.6 | → 0 | DPP |
| MMVQ IQ4_XS n=1 / n=5 | 43/16, 166/9 | 6 (3 b128) / 23 (14 b128) | 9.5 / 11.6 | → 0 | — |
| `kvq<256,8,Q4_0>` (Qwen FA decode) | 255 / 5 | b128 + d16; 32 WMMA, 90 DPP | — | max `vmcnt(5)` | 55 barier, wszystkie poza pętlą KV |
| `kvq<64,8,Q8_0>` (LFM) | 144 / 10 | — | — | — | — |
| `gated_delta_net_cuda<128,…,lag>` | 84 / 16 | 87× b32 (stan f32) | 4 | — | 0 DPP |
| MMQ Q4_K (prefill), np. tu098 | 190 / 8 | 82 global, głównie b32 | 3.8 | max 38 | **4 bariery + 4 `gl0_inv` na iterację K** |
| hipBLASLt skinny `MT32x16x128` (porównanie) | 256 / 5 | 12 `buffer_load_b128` | 16 | **kroczące `vmcnt(11)`, nigdy 0** | 0 `gl0_inv` |
| hipfire GEMV MQ4G256 (porównanie) | 76 / 16 | 8 b128 (x w fp32) + 4 b32 | — | — | 4× `ds_bpermute` + swizzle |

Reguły:
- Little's law na papierze jest spełnione przy pełnym occupancy (n=1: ~1.9 KB/falę × 16 fal ≈ 31 KB/SIMD wobec ~5 KB potrzebnych, 23b) — **wąskim gardłem jest koszt wydawania wielu małych ładowań, drenaż `vmcnt(0)` co iterację i małe siatki** (out_proj LFM 2048 wierszy przy 2 wierszach/blok ≈ 1024 fal ≈ 5 fal/SIMD `[SZACUNEK]`), co pokazuje ATT (zator wydawania VMEM w down, 85% `vmcnt` w gate+up).
- Najpierw **sufit wzorca** (ten sam wzorzec i siatka, czysty odczyt): gate+up 2 wiersze/falę = 22.4–24.4 µs nawet bez arytmetyki, 4 wiersze/blok 19.68 µs (879 GB/s) (`16g:§2`). Jeśli kernel jest blisko sufitu wzorca — zmieniaj wzorzec, nie arytmetykę.
- Kernel na limicie VGPR (kvq 255) jest kruchy: hak w szablonie dał 14 spillowanych VGPR i −6% tg128 → dodatki jako osobna instancja szablonu; per łatka diff `co_stats.py`/`isa_kstat.py` (spill, fale).
- `amdgpu_waves_per_eu` per (typ, kolumny) jest obowiązkowe przy zmianie loadera (bez niego K1 miał −5…−40%, 23b).
- Prefetch: do VGPR wewnątrz konsumenta tak (GU_BLOCK −1 µs/24 µs); do L2/MALL osobnym dispatchem nie (16a X3); kroczące `vmcnt` à la Tensile wymaga etapu w LDS i 256 VGPR — dla GEMV nie przenosić 1:1 (pipelining Q4_K/Q5_K w K1 wyszedł ujemnie, 23b „Odrzucone”).
- Cache policy: AMD nie ustawia bitów nigdzie (0/2182 hipBLASLt, 0/7461 rocBLAS); u nas `GLC|DLC` w multi-col dało −0.87 ms, ale `slc|dlc` w n=1 Q5_K pogorszyło (12.90 → 14.42 µs) i głowa Q6_K traci ~0.14 ms → **decyzja per typ i kształt z profilu w modelu**, nigdy z mikrobencha.

## II.5 Skwantyzowany iloczyn

| typ | wag/blok | B/blok | bpw |
|---|---|---|---|
| Q4_0 / Q8_0 / q8_1 (aktywacje) | 32 | 18 / 34 / 36 | 4.5 / 8.5 / 9 |
| Q4_K / Q5_K / Q6_K / IQ4_XS | 256 | 144 / 176 / 210 / 136 | 4.5 / 5.5 / 6.56 / 4.25 |

- Decode: aktywacja → q8_1 raz (cache 0003, producenci w epilogu 0015/0049/0056) → `v_dot4_i32_iu8`/`dp4a` (NVIDIA: `IDP.4A`); człon min K-quantów z sumy bloku q8_1 (`v_dot4 … 0x01010101`); clamp d/sum do ±65504 (0023).
- Weryfikacja: multi-col 2–8 kolumn (wagi rozpakowane raz; Q5_K 8 kol. 296 → 621 GB/s), WMMA iu8 dla 9–16 (0037). Klif VGPR 4 → 5 kolumn (89 → 140, 16 → 10 fal, 21l).
- Prefill: ~66% czasu MMQ to `vec_dot` (WMMA + epilog skal), ładowania 11%, bariery 7% (ablacja); epilog w parach VOPD +2.2% pp4096 (0070).
- Fuzja producent → q8_1 to decyzja per platforma: na NVIDIA ticket + bariera droższe niż osobny `quantize_q8_1` (`GATE_UP_Q8` off: +6.5% LFM na 3090).
- FP4/FP8 nie przyspieszają decode (te same bajty); NVFP4 W4A4 tylko prefill sm_120a (+65–81%, jakość plików słaba).

## II.6 Atencja decode

- Flash-decoding: split KV + online softmax (log2) + combine; **cała grupa GQA jednym przejściem** (`kvq`: Qwen 6 głów/KV; 94k 43.0 → 70.9 t/s; 3090 kernel 680 → 115 µs, ~656 GB/s; 5060 Ti ~92% pasma na `cp.async`).
- KV q4_0/q8_0 dekwantyzowany w rejestrach, bez konwersji do F16.
- Numeryka: podział KV zależny od N/n_kv i zamaskowane wiersze w WMMA zmieniają bity; sam inny podział KV przesuwa KLD o ±1–1.9σ (ogon 99.9% ×0.69–×1.41) → przy bramce kontrola „to samo jądro, inny podział”.

## II.7 Stan rekurencyjny i MoE

- GDN Qwena: stan 151 MB f32 (R+W 0.30 GB/krok); cofanie przez przeliczenie (S4) zamiast snapshotów: −720 MiB zapisów, 793 → 638 µs/weryfikację; `gdn-fast` (DPP + b128 przez LDS): prompt −14%, decode w szumie.
- MoE LFM: unia ekspertów przy weryfikacji u(N) = 64(1 − (60/64)^N); fuzje 0049/0051/0053/0056 −0.565 ms/token; GU_BLOCK (16 fal = 1 grupa q8_1, ogon przez LDS zamiast fence + ticketu: ATT 1.7k + 2.6k cykli/falę) +0.33% LFM / +1.39% Uncensored; bąbel router → ekspert ~0.2–0.25 ms/token nieusuwalny bez shared expert.

## II.8 Launch: grafy, PM4, PDL, trwałe kernele

- Najpierw mniej kerneli (fuzje), potem tańszy launch. Każdy kernel mniej: −2.1…−3.3 µs (AQL) / −0.5…−0.9 µs (PM4).
- Na Linuksie CLR dzwoni doorbellem przy każdym pakiecie (`rocvirtual.cpp:1610`); graf kopiuje pakiety hurtem; flagi `DEBUG_HIP_GRAPH_*` dają szum — podłogę 2.08 µs wyznacza firmware (23d).
- Zysk megakerneli to prefetch wag ponad granicą operacji, nie sama granica; wygrywa tylko dataflow (wagi przed czekaniem, tagged pairs = wartość + epoka jednym store'em, `pre_poll`, bounded spin + słowo błędu) (`15a:§2`).
- Hand-off przez pamięć na RDNA3 ≈ koszt granicy; flaga pollowana przez cały grid jest wolniejsza od granicy (≥ 16 kopii po 128 B albo relay).
- PM4 zamienia fault kernela w reset GPU (9/10); fault w AQL zabija tylko proces → eksperymenty zawsze `GGML_HIP_PM4=0`.
- CUDA PDL: każdy kernel przez `ggml_cuda_kernel_launch` woła `pdl_sync` przed pierwszym zależnym odczytem (3 wyścigi na sm_120).

## II.9 Numeryka i bit-exactness

| źródło rozbieżności | reguła |
|---|---|
| kontrakcja FMA (0025: 1 ulp w ~4% wierszy; GDN fast 94 vs 83 FMA) | jawne `fmaf`, `ggml_cuda_no_contract`; porównać mieszankę f32 fma/mul/add w ISA |
| kolejność akumulacji (kafle, split-K, chunki; FA KLD 0.0135 → 0 po 0043) | każda zmiana podziału pracy → KLD albo bitowość; split-K w MMVQ łamie bitowość spekulacji |
| batch ≠ N=1, splity zależne od N | MTP porównujemy z bazą MTP; `LLAMA_SPEC_BITEXACT` |
| zamaskowane wiersze w WMMA | zerować wiersze za pozycją |
| niedeterminizm serwera (rozjazd po ~270 znakach) | greedy md5 zawsze na świeżym serwerze |
| fork ≠ upstream (0001/0002, 0013) | „identyczne z poprzednim buildem w tym samym trybie” + KLD vs upstream |

Bramki: `test-backend-ops` (+ nowy przypadek dla każdej fuzji), greedy md5 + hash FNV logitów 64 kroków (d0, d3000), logity prefillu 2048 tok., `llama-bx-diff`, `isadiff.py`, emulator ISA (`gdnemu.py`/`mmvqemu.py`), KLD z kanarkami (PASS: ΔKLD ≤ 2σ, Δsame-top ≥ −2σ, KLD99.9 ≤ 1.25×), KLD tylko w tym samym protokole.

## II.10 Profilowanie

| cel | AMD | NVIDIA |
|---|---|---|
| mapa czasu w modelu | `rocprofv3 --kernel-trace --stats` z `GGML_HIP_PM4=0`; taśma: `GGML_HIP_PM4_DEBUG=3` | `nsys` bez `--cuda-graph-trace=node` |
| per instrukcja | ATT: `rocprofv3 --att --att-target-cu 1 --att-simd-select 0 …` + `attsum.py` | `ncu` (tylko kierunek), NVBit (własne binarki) |
| statyka | `isa2.sh`, `isa_kstat.py`, `co_stats.py`, `isa_profile.py`, `llvm-objdump --mcpu=gfx1100`, `llvm-readelf --notes`, `clang-offload-bundler`, RGA `--livereg --cfg`, `umr` offline (PM4) | `ptxas -v`, `cuobjdump -res-usage`, `nvdisasm -cfg` (triton/bin, CUDA 13.1; `~/opt/cuda-12.8`), `sass_mix.py` |
| nie działa | PMC bez `STABLE_STD` (root), PC sampling/rocprof-compute (tylko Instinct/APU), rocprof nie widzi PM4 | radare2 „sass” dekoduje sm_86 błędnie |

Kolejność: sufit → mapa czasu w modelu → kubełki strat → sufit wzorca → ATT najgorszego kernela → ablacja → hipoteza z budżetem µs.
Legalność (21l §4): własne binarki i otwarte biblioteki AMD (MIT) — tak; cuBLAS tylko metadane + black-box (EULA §1.2); firmware AMD — licencja linux-firmware zabrania RE. 23d deasemblował MEC wyłącznie dla interoperacyjności własnej ścieżki dispatchu (art. 6 dyr. 2009/24/WE; art. 75 ust. 2 pkt 2–3 i art. 76 uPrAut wg 21l) — dumpów nie publikować ani nie redystrybuować; ocena prawna należy do użytkownika.

## II.11 Dyscyplina pomiaru

1. Metryka: ms/krok (kernel), tok/krok (akceptacja), t/s (użytkownik) — zawsze wszystkie trzy.
2. ABBA w jednej binarce (wyłącznik env), ≥ 3 rundy `-r 5`, wiele procesów (rozrzut per proces 24.3 vs 27.2 µs), A/A dla progu; sha256 `libggml-*.so` + `build_info` w każdym wierszu.
3. Treść: 6 promptów PL/EN × ≥ 3 seedy (≥ 5 dla typów kwantów, ≥ 20 dla ~2% przy T>0); T=0 i T=1 osobno; nowe pisanie i kopiowanie osobno.
4. Zysk kernela ≠ zysk tokena (limit 285 W przesuwa zegar sąsiadów) — decyzja tylko e2e.
5. Kill criterion zapisany przed pomiarem; wynik negatywny też do NOTES; commity bez pomiaru = UNMEASURED.
6. Bezpieczeństwo: `flock /tmp/gpu.lock` + `/tmp/quiet.lock`, porty 18433–18499, nie dotykać :8080, `gpu-guard.sh`, `GGML_HIP_PM4=0` dla eksperymentów, zero zmian zegarów/napięć/limitów mocy; CPU-heavy: `flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-1`, buildy `-j2`.

---

# Część III — checklista projektu i recenzji kernela

**A. Przed kodem**
- [ ] Bajty na wywołanie i na krok, podłoga (bajty/900 GB/s), udział w kroku → górna granica zysku w ms/krok i t/s.
- [ ] Sufit wzorca zmierzony; ATT/ablacja mówi, co ogranicza (VMEM issue / `vmcnt` / VALU / bariery).
- [ ] Kill criterion i klasa poprawności (bitowa vs KLD) zapisane.

**B. Projekt**
- [ ] Siatka ≥ 96·k bloków, nie dokładnie 3072; przy małych macierzach policz fale/SIMD z siatki, nie z VGPR.
- [ ] Ładowania 16 B (buffer + SGPR offset na RDNA3), mało instrukcji VMEM na bajt, brak `vmcnt(0)` w środku pętli, prefetch do VGPR, jeśli VGPR pozwala.
- [ ] VGPR poniżej progu (§II.1), 0 spilli, `waves_per_eu` ustawione.
- [ ] Redukcje DPP / `__shfl_xor_sync`, nie LDS + bariera; bariery LDS bez `gl0_inv`, gdzie nie ma zależności przez L0.
- [ ] Brak atomików na blok w gorącej ścieżce; hand-off tylko przez fuzję albo tagged pair z bounded spin.
- [ ] Cache policy per typ z profilu; kernargi w VRAM; `pdl_sync` (CUDA); PRIV=1 (własny PM4).
- [ ] Wyłącznik env (`GGML_HIP_*` / `GGML_CUDA_*`), predykat per arch; dodatki przy limicie VGPR jako osobna instancja szablonu.

**C. Recenzja ISA (bez GPU)**
- [ ] `isa_kstat.py` / `co_stats.py` przed/po: VGPR, fale, scratch = 0, b128 vs b32, B/instr., DPP vs `ds_bpermute`, `s_waitcnt` w pętli, `gl0_inv` po barierach.
- [ ] `isadiff.py`: kernele bazowe bajtowo identyczne przy wyłączniku = 0; mieszanka f32 fma/mul/add bez zmian (zmiany „bitowe”); emulator ISA dla przepisań arytmetyki.
- [ ] NVIDIA: `ptxas -v` dla sm_86/89/120a; `sass_mix.py`: `PREEXIT`/`ACQBULK`, `LDG.E.EF`, LDL = 0.

**D. Poprawność i pomiar**
- [ ] `test-backend-ops` (+ nowy przypadek), greedy md5 plain + MTP na świeżym serwerze, hash logitów d0/d3000, logity prefillu jeśli dotyczy.
- [ ] KLD z kanarkiem i kontrolą „inny podział”, jeśli niebitowe.
- [ ] ABBA e2e (≥ 3 rundy, wiele procesów, ms/krok + tok/krok), physics-floor, sha256 binarki; `PM4=0` najpierw, PM4 i soak dopiero po przejściu.
- [ ] NOTES/ledger (także negatywne), REKORDY przy rekordzie.

---

## Do bazy wiedzy

| folder | plik | treść | źródło |
|---|---|---|---|
| `metody/` | `podrecznik-gpu.md` (nowa) | wejście dla świeżego agenta: werdykt §I.1, ranking §I.2, liczby §I.3, checklista cz. III | 23f |
| `rocm/` | `rdna3-gfx1100.md` (poprawka) | fale/SIMD = min(16, ⌊1536/roundup(VGPR, 24)⌋); 255 VGPR → 5 fal (nie 6); `__syncthreads` = `s_barrier` + `buffer_gl0_inv` | 21l; 23b2 |
| `lekcje/` | `lekcja-mmvq-n1-upstream.md` (nowa) | produkcyjne MMVQ n=1: b32/d16 (3.3 B/instr.), `vmcnt(0)` co iterację, 5× `ds_bpermute`; multi-col: b128 (11.7 B/instr.) + DPP; kandydat #2 | `~/opt/isa101/v100/mmvq.s` `.LBB271_9`; `mmvq.cu:180-187`; 23b |
| `kernele/` | `mmvq-multikolumnowe.md` (uzupełnienie) | Q6_K n=5: 60 ładowań/it., 0 b128, 250 VGPR, 5 fal; klif VGPR 4 → 5 kolumn (89 → 140) | 23b; 21l |
| `narzedzia/` | `isa-kstat.md` (nowa) | `~/KERNEL/tools/re/isa_kstat.py FILE.s [REGEX]`: VGPR, fale (granulat 24), LDS, scratch, ładowania wg szerokości, DPP/VOPD/WMMA/dot, `s_waitcnt`, bariery, atomiki | 23f |
| `research/` | `raport-23f.md` (nowa) | ranking 14 pozycji ze wszystkich raportów RE; „już mamy” (GDN replay = S4, nie Strata-nowość) | 23f §I.2 |
