# 30 — hipfire (Kaden-Schutt/hipfire → warpfront/hipfire)

Źródło: https://github.com/Kaden-Schutt/hipfire (przekierowuje na `warpfront/hipfire`), płytki klon HEAD `1ff5182` z 2026-10-14, wydanie v0.4.2. Ścieżki niżej są względne do korzenia repo. **Wszystkie liczby z repo to pomiary autorów hipfire** (gfx1100 = ich 7900 XTX, maszyny „hipx”/„k9lin”; gfx1201 = R9700; gfx1151 = Strix Halo), chyba że oznaczono inaczej. Nasze liczby pochodzą z `NOTES.md`. Polecił je raport 22-lucebox (`HIP_PERF_PLAN.md:559-591` tam: „132 t/s DFlash na 7900 XTX”).

## 1. Co to jest

Silnik inferencji w Rust + HIP tylko pod AMD (RDNA1–4, CDNA). Ma własne formaty wag: MQ4G256V2 to 4.25 bpw z rotacją FWHT wag i aktywacji. Ma też własną warstwę „Redline”, która odtwarza nagrany token jako zatrzymany bufor PM4 przez kolejkę ROCr, oraz własny toolchain ISA „PeaceMaker”, który emituje i certyfikuje kod maszynowy bez hipcc. Repo jest bardzo aktywne: 667 gwiazdek, push w dniu analizy, CHANGELOG ma 3201 linii, wydanie co tydzień. Licencja Apache-2.0, część plików MIT.

Ten sam model co u nas, Qwen3.8-27B, ale we własnej kwantyzacji: kanoniczny `qwen3.8-27b.mq4-xts` ma 14.99 GB, nasz UD-Q4_K_XL 17.56 GB. Na gfx1100 KV jest domyślnie Q8_0 (`AGENTS.md:931`).

**„132 t/s” z lucebox to stara liczba historyczna.** Obecne liczby na gfx1100:

| Pomiar (gfx1100, 7900 XTX) | hipfire | my (fork amd-opt) |
|---|---|---|
| AR, krótki kontekst | 50.8 t/s, MQ4-XT 15 GB, HIP graph (`CHANGELOG.md:669`); 54.3 t/s z PM4, Qwen3.6-27B „H2” (`CHANGELOG.md:1208`) | ~38.6 t/s, 17.6 GB (stary pomiar z 2026-10-09) |
| AR, 32K | 46.0 t/s (`CHANGELOG.md:1237`) | — |
| MTP | 76.4 t/s, K=3, 1 prompt kodu, graf wyłączony (`docs/perf-checkpoints/2026-08-21-qwen38-mqv2-mtp-prefix-cache.md:39-47`); 61.3 t/s przy 32K (`CHANGELOG.md:1106`) | **104 t/s**, 28.9 ms/krok, mieszanka 6 promptów, T=1; 105 / 100.6 t/s przy 29.5k / 94k (T=0) |
| DFlash, kod | **307.9 t/s** na jednym krótkim prompcie, τ≈13 (`CHANGELOG.md:34`); 290.7 na `humaneval_0` (`:27`) | DFlash2 n=6: 111–116 (kod EN) |
| DFlash, proza i długi kontekst | fikcja 60.8; proza 8K 87.6; kod 21.6K 56.7 (`CHANGELOG.md:27,34`) | MTP (T=0): 118 przy 6.6k, 105 przy 29.5k |
| Prefill | **~3000 t/s pp8192** (W4A4, stratny) (`CHANGELOG.md:1474-1475`) | ~950–1044 t/s pp4096 |

## 2. Kluczowe techniki (z dowodami)

### A. DFlash2 o szerokości 16 na checkpoincie trenowanym na 8
- `DFLASH_BLOCK_UNBATCHED = 16` (`crates/hipfire-runtime/src/dflash.rs:51-60`). Selektor i konwolucje DFlash2 są „length-generic”, więc runtime pracuje na 16, a w serwerze z batchowaniem na 8 (`:166-171`).
- Selektor (`dflash.rs:4568-4660`):
  - per wiersz top-16 z `lm_head`;
  - wynik = unarny + biliniowy `pred_cb[prev]·proj(h)·succ_cb[cand]` (rank 256);
  - łańcuch wybierany na hoście sekwencyjnie.
  - To samo robimy w `common/speculative.cpp:1297-1319` (patrz 22-lucebox).
- τ na gfx1100, prompt `merge_sort` (38 tokenów): 157 tokenów w 11 cyklach, **τ=13.18** (`docs/perf-checkpoints/2026-09-09-gfx1100-packed-lds-gate-up.json:78-104`). Na R9700 proza ma τ 1.09, a prompt 21.5K τ 2.07 (`CHANGELOG.md:664-665`).
- Anatomia cyklu na gfx1100 (`2026-09-08-gfx1100-packed-residual-qkvza.json:7949-8124`, eager, bez grafu):
  - 1000 kerneli, 41.67 ms pracy GPU, 49.07 ms cyklu;
  - GEMM-y weryfikacji ~30 ms: residual 12.6, gate_up 12.0, qkvza 4.3;
  - GDN 1.94 ms, draft ~5 ms.
- Adaptacyjna szerokość `clamp(ceil(τ̂)+2, 2, 16)` po 8 cyklach jest opcjonalna i domyślnie wyłączona (`dflash_adaptive_block.rs:1-40`, `CHANGELOG.md:1562`). Nie ma przełączania DFlash→AR (`docs/plans/adaptive-dflash.md` to tylko propozycja).

### B. GEMM-y weryfikacji N≤16 na gfx1100
- `ldsstage` (`kernels/src/gemm_mq4g256v2_residual_wmma_gfx1100_ldsstage.hip:1-36`):
  - 256 wątków kopiuje surowy plaster wag 16 wierszy × 512 K do LDS (4352 B) loadami dwordx4;
  - 8 fal dekwantyzuje po 64 K do fragmentu f16, potem WMMA f16 i redukcja w LDS w stałej kolejności.
- `ksplit_lds` ks2/4/8 (`…_ksplit_lds.hip:1-28`, `crates/rdna-compute/src/gemm.rs:37000-37040`): kilka fal dzieli K dla jednego kafla 16×16, bo „jedna fala na kafel nie wypełnia 96 CU”.
- Zysk: DFlash 290.6→301.2 t/s (+3.6%) (`2026-09-09-gfx1100-packed-lds-residual.json:3-50`). Gate/up przy 16 kolumnach ~162 µs/wywołanie, czyli ~585 GB/s `[WNIOSEK z ich liczb]`.
- Wariant gfx1151 XLDS (aktywacje X w LDS raz, z podwójnym buforem) dał +38% DFlash na Halo (`CHANGELOG.md:47-50`). **Nie przeniesiono go na gfx1100.**
- Mała szerokość to ich słabość. Gate_up WMMA przy N=3 ma 239 µs = 305 GB/s, a trzy warianty nie pomogły (`docs/plans/mtp-gate-up-wmma-ceiling-2026-05-21.md`). Stąd ich wniosek, że weryfikacja „kosztuje tyle samo od M=4 do M=16” (`docs/plans/mtp-goal-a-asymptote-ruling-2026-05-23.md`).

### C. Atencja decode i weryfikacji, KV Q8_0 (gfx1100)
- **Decode** (`kernels/src/attention_flash_q8_0_tile_gqa.gfx1100.hip`):
  - jedna grupa 256 wątków na (głowa KV, 128 kluczy) obsługuje 6 głów Q, więc K/V czytane są raz;
  - wszystkie loady wydane na wejściu (`:153-201`), buffer rsrc + offset 32-bit (`:156-159`);
  - bloki Q8_0 po 34 B czytane jednym niewyrównanym dwordem (`:29-33`);
  - QK jako łańcuchy FMA f32 (bez dot4), redukcja DPP `row_xmask` (`:76-119`).
  - Combine (`attention_flash_q8_0_reduce_gated_mq_rotate_dec.gfx1100.hip`): bramka sigmoid + FWHT-256 przez `ds_swizzle` w epilogu.
  - Na warstwę: 74.0→28.4 µs (ctx 517) i 300→153.5 µs (32K) (`CHANGELOG.md:1238`). E2E +10.6% przy 32K.
- **Weryfikacja** (`attention_verify_gqa.gfx1100.hip:1-52`, `CHANGELOG.md:1102-1106`):
  - jeden skan KV dla 6 głów × do 8 wierszy;
  - dokładna dekwantyzacja int8→f16 w ~2.25 VALU/element: `v_perm` wstawia `byte^0x80` pod wykładnik f16 0x64 (daje 1024+u), potem odejmowanie 1152 (`:77-102`).
  - B=16, 32K: 1.67→1.27 ms/warstwę; DFlash przy 32K 54.9→60.6 t/s.
  - Opcjonalny split-KV FA2 (WMMA) dla B 4..32 przy kontekście >4K (`attention_q8_0_fa2_gqa.gfx11.hip:1556-1621`).
- Ich decode przy 32K czyta K+V z prędkością ~465 GB/s `[WNIOSEK]`, czyli też daleko od pasma.

### D. Redline: zatrzymany PM4 zamiast HIP graph (najważniejsze dla LFM)
- Mechanizm:
  - nagranie realnych uruchomień tokenu (obiekt kernela, bajty kernarg, siatka, alokacje R/W);
  - zamiana na jeden bufor PM4 `INDIRECT_BUFFER`, wysyłany **jednym pakietem AQL typu vendor** przez publiczną kolejkę ROCr (`crates/redline-rocr/src/packet.rs:415-462`).
- Koder PM4 gfx10/11 (`crates/redline-rocr/src/pm4_gfx10.rs`):
  - `dispatch_image` (`:539-611`): SET_SH_REG COMPUTE_PGM_LO/HI, RSRC1-3, NUM_THREAD, RESOURCE_LIMITS, USER_DATA_0..15, potem `DISPATCH_DIRECT`;
  - zależność: `EVENT_WRITE CS_PARTIAL_FLUSH` (`:614-618`) + `ACQUIRE_MEM` GCR 0x380, inwalidacja L0/K$ bez L2 (`:298-341`);
  - czekanie tylko przy konflikcie R/W na poziomie alokacji (`crates/rdna-compute/src/replay.rs:6787-6830`).
- Liczby z gfx1100:

  | Model | HIP graph | PM4 | Uwagi |
  |---|---|---|---|
  | Qwen3.6-35B-A3B MQ4R, 603 dispatchy | 219.6 t/s | **251.8 t/s** (×1.146) | `registry/redline-golden-v1.json:33-74` |
  | 27B „H2” | 51.1 t/s | **54.3 t/s** (+6.3%) | mediana kroku 21.25→19.67 ms (`CHANGELOG.md:1203-1208`) |

  - `[WNIOSEK]` A3B: ~1 µs mniej na dispatch; H2: ~1.8–2.4 µs.
- **Warunek: kernargi w VRAM.** Z kernargami w pamięci hosta PM4 było *wolniejsze* od grafu (50.7 vs 51.1). Prologi z zależnymi `s_load` kernargów płaciły latencję hosta (`CHANGELOG.md:1203`).
- Wyniki negatywne:
  - surowe AQL per dispatch było wolniejsze od HIP: 3.97 vs 3.22 µs w burście na XTX (`crates/redline/PHASE2_RESULT.md:15-36`);
  - PM4 bezpośrednio do sterownika na XTX timeoutował (`crates/redline/PHASE1_STATUS.md:43`);
  - „dirty-gating” rejestrów dało ±0.5%, więc parsowanie przez CP nie jest wąskim gardłem;
  - dwie kolejki z barierami przegrywały (`2026-08-05-mq2r-a3b-lowbit-campaign.md`).
- Floor z zewnętrznego dokumentu (`crates/hipfire-runtime/examples/dispatch_floor_probe.rs:9-13`, GPU nieokreślone): hipGraphLaunch ~2.13 µs/dispatch, PM4 IB 0.12–0.21 µs.

### E. Prefill: od ~990 do ~3000 t/s na XTX (Qwen3.8-27B XT)
Kolejne kroki według CHANGELOG:
- MMQ int8 z aktywacjami per-32: pp512 **990** (≈ nasz poziom).
- **X128** (`:1624`, +15%, KLD WT2 +0.0002): skala aktywacji co 128 K, akumulacja i32 przez cały blok 128 i jedna korekta float. Pp512 990→1141.
- **W4A4 iu4 WMMA** (`:1619`, +32%): pp512 1204→1589, pp8192 1094→1405. Wagi nibble idą wprost do `wmma_i32_16x16x16_iu4`, aktywacje kwantyzowane do int4 per 128. Na RDNA3 iu4 = 1024 op/clk/CU, czyli **2× iu8** (GPUOpen, https://gpuopen.com/learn/wmma_on_rdna3/).
- „C baseline” (`:1605`): pp8192 2071.
- GDN chunk scan WMMA (`:1613`, GPU niepodane): pp8192 2433→2710.
- Kernele z PeaceMaker i FA2 (`:1474-1489`, `:1592`, `:1600`): **~3000 pp8192**.

Kernel V2C (`kernels/src/gemm_mq4g256v2_residual_iu4_v2c.gfx11.hip:1-60`):
- kafel 128×128, 8 fal, 2×16 KB LDS z podwójnym buforem, czyli **2 CTA na WGP**;
- **permutacja fragment-major przy zapisie do LDS**: każdy operand WMMA to jeden ciągły 128-bajtowy przebieg, a zapisy b64 są bez konfliktów banków;
- rebias wag przez XOR 0x88888888;
- **skale wag z pominięciem LDS**: lane ładuje skalę jednego wiersza, a pozostałe zbiera DPP `row_share`;
- **liczba magiczna**: akumulator i32 startuje od 0x4B400000 (1.5·2²³), więc float(C) to jedno `v_sub`;
- `ADD_TOUCH`: residual dociągany kilka epok K przed epilogiem.

Koszt jakości A4 (`AGENTS.md`, tabela pinów KLD): na gfx1201 WT2 **0.0696 (A4) vs 0.0419 (natywne fp8)**, code24 0.052 vs 0.030. Na gfx1100 A4 daje 0.0693. Wagi są obracane FWHT, bez tego A4 nie działa.

### F. GDN
- **Stan rekurencji Q8** z per-wierszową skalą + opcjonalny residual f16 („error feedback”) albo stochastyczne zaokrąglanie (`kernels/src/gated_delta_net_q8.hip:26-43,119-176`):
  - w obrębie jednego wywołania stan siedzi w LDS jako f32, rekwantyzacja tylko na końcu;
  - stan jest **stratny**: ~3 B/element z EF, 1 B bez EF.
- Rollback:
  - snapshot + taśma pre-conv qkv i α/β; przy częściowej akceptacji replay conv+norm+GDN (`crates/hipfire-arch-qwen35/src/speculative.rs:2025-2041`);
  - na gfx1100 2 uruchomienia na warstwę i dwie kopie bulk po ~0.5 ms;
  - na gfx1201 replay wszystkich 48 warstw w 2 uruchomieniach: 1.96→1.05 ms (`CHANGELOG.md:1218-1222`).
- **Chunk scan prefillu na WMMA** (`kernels/src/gdn_chunk_scan.gfx1201.hip`, kompilowany też dla gfx1100):
  - C=64, stan jako akumulatory WMMA f32, kopia f16 w LDS;
  - KKT solve osobno: na XTX 48.5→31.2 ms przy pp8192 (`CHANGELOG.md:1598`);
  - bariera z `s_waitcnt 0xFC07`, żeby nie czekać na globalne prefetche (`:118-128`).
  - To dodatni wynik na gfx1100, w przeciwieństwie do Straty (−39%). U nich GEMM-y są jednak 3× szybsze, więc udział GDN w czasie jest większy.

### G. FA2 prefill (gfx1100)
- Specjalizacja fal (`attention_q8_0_fa2_gqa.gfx11.hip:147-184`): 6 fal liczy WMMA, 2 fale „pomocnicze” dekwantyzują Q8 K/V do LDS f16 w tle.
  - Czas FA przy pp8192 347→269 ms (−22.6%) (`CHANGELOG.md:1600`).
- Poprawka konfliktów banków w zapisach pomocników (V 8-way, K 4-way), `-mcumode`, najcięższe kafle najpierw: kernel −24.7% (`CHANGELOG.md:1475`).
- ~49–60 TFLOPS `[WNIOSEK]`, podobnie jak u nas (49–52).

### H. Decode GEMV (1 kolumna)
- Zwykłe FMA f32, jedna fala na wiersz, aktywacje f32 z globala, bez dp4a i bez LDS (`kernels/src/gemv_hfq4g256.gfx1100.hip:15-131`).
- Nagłówki grup MQ4V2 są pod adresami niezależnymi od lane, więc idą jako loady skalarne (`docs/quant-formats/mq4-v2.md:190-196`).
- Wynik: ~650–690 GB/s, czyli **tyle co nasze MMVQ, nie więcej**.
- Specjalizacja na kształt: K=5120 wpisane na stałe przez podmianę tekstu przy JIT (`crates/rdna-compute/src/kernels.rs:7315-7325`) daje +1.0% AR, bitowo identycznie (`CHANGELOG.md:668-670`).
- Długa lista wyników negatywnych (`kernels.rs:7203-7310`): R2–R8 wierszy na falę, LUT nibbli, `s_setprio`, prefetch.
- SLC jest domyślne tylko dla strumienia wag ekspertów MoE gate/up (`gemv.rs:14470-14475`). Dla macierzy gęstych dało wynik płaski.

### I. MoE decode
- Wierna fuzja router+softmax+top-k: +0.07%, neutralnie.
- Router w wave64 z 64-bitowym kluczem: +0.9–1.3% na gfx1201.
- Warianty down+combine:
  - w jednej fali: znak efektu zależny od kolejności przebiegów;
  - kooperacyjny: −2.8…−4.9%.
- Na gfx1100 wydany down → combine+residual+RMSNorm następnej warstwy+FWHT (`moe_down_combine_rmsnorm_mq_rotate_vecsum.gfx1100.hip`).
- „Mniej uruchomień ≠ szybciej” pod PM4: −231 dispatchy dało +0.04% (`2026-07-27-ds4-gfx1151-ar-roofline-amendment-1.md`).

### J. Proces
- Każda zmiana ma przełącznik `HIPFIRE_*=0`.
- Bitowe piny `.kldseq` per arch.
- Pomiary ABBA na świeżych procesach.
- Ostrzeżenia:
  - synchronizacja hosta kosztuje ~22 µs na pomiar;
  - mikrobenchmarki zawyża MALL (`mq4-v2.md:356-372`).
- To samo stosujemy już u nas (hash logitów, `mmvq-bench` na zimno).

## 3. Przeniesienie na AMD/HIP/RDNA3 (nasz fork)

| Technika | Przenośna? | Jak / dlaczego nie |
|---|---|---|
| Zatrzymany PM4 (Redline) | **Tak, ten sam GPU**, ale duży koszt | Zamiast `hipGraphLaunch` własna kolejka ROCr (`hsa_queue_create`) i pakiet vendor z IB. Kernargi w puli VRAM dostępnej z hosta. Między zależnymi kernelami CS_PARTIAL_FLUSH + ACQUIRE_MEM 0x380. Trzeba odczytać deskryptory kerneli ggml i ich kernargi z węzłów grafu HIP (`hipGraphKernelNodeGetParams`) `[WNIOSEK: uzyskanie adresu deskryptora kernela z runtime HIP wymaga obejścia, np. załadowania tego samego code object przez HSA]`. |
| DFlash2 B=16 | Tak (logika hosta) | To samo co pomysł 1 z 22-lucebox. hipfire dokłada niezależne potwierdzenie na gfx1100. Nasz `fattn-kvq` przyjmuje już do 16 tokenów (`fattn-kvq.cu:605-607`), a K4 WMMA obsługuje 9–16 kolumn. |
| Liczba magiczna 1.5·2²³ zamiast `v_cvt_f32_i32` | Tak, bitowo | W epilogu MMQ (`mmq-vec-dot.cuh:357-361`, `dmA.x*dsB.x*C.x[l]`) i w K4. Przy |C| ≤ 32·127·128 < 2²² konwersja jest dokładna. `v_sub_f32` wchodzi w VOPD (dual issue), `v_cvt` nie `[WNIOSEK]`. |
| Skale przez DPP `row_share`, LDS fragment-major | Tak | Mniej LDS (`x_dm` w tile MMQ), czyli więcej CTA/WGP i mniej `ds_load` w pętli. |
| X128: akumulacja i32 przez 128 K | Częściowo, nie bitowo | Q4_K/Q5_K mają całkowite 6-bitowe skale per 32, więc Σ sc_j·C_j da się sumować w i32 (`v_mad_i32_i24`). Wymaga jednak aktywacji ze skalą per 128 (nowy blok q8 „128”) i członu min z całkowitych sum aktywacji. Przepełnienia nie ma: Q5_K 32·31·127·63·4 ≈ 3.2e7 < 2³¹. |
| W4A4 iu4 | **Nie** dla GGUF | iu4 wymaga 4-bitowych *aktywacji*, a bez obrotu FWHT wag (re-kwantyzacja GGUF) jakość leci. U nich A4 kosztuje +0.027 KLD WT2 przy wagach 4-bit, czyli tyle co połowa całej kwantyzacji. |
| Decode Q8_0 GQA-shared | Tak | Dokładnie „instancja q8_0 w kvq” z `lfm-decode-round2.md` §4 (LFM: D=64, GQA 4). Dekwantyzacja `v_perm`/0x6400/−1152 daje f16 do WMMA tanio. |
| Warp-specialized FA2 prefill | Mało warte | U nas prefill przy KV q4_0 robi `to_fp16` całego KV raz na ubatch (`fattn-common.cuh:1035-1085`). Zysk z dekwantyzacji w kernelu to tylko brak tej konwersji, ok. 1% przy 94k `[WNIOSEK]`. Nasze FA ma już ~50 TFLOPS, jak ich. |
| GDN chunk scan WMMA | Tak, ale mało warte | U nas GDN to ~15 ms z ~554 ms ubatcha (2.7%, `research/v2/roadmap.md:25`). U nich zysk jest widoczny dopiero po 3× szybszych GEMM-ach. |
| Stan GDN Q8+EF | Nie | Stratny. Przy EF oszczędza ~25% bajtów stanu, czyli ~0.08 ms/krok `[SZACUNEK]`. |
| ldsstage / ksplit dla N≤16 | Do sprawdzenia | Nasz K4 to ~0.43 ms/kolumnę. Trzeba sprawdzić w rocprofv3, czy K4 przy 9–16 kolumnach wypełnia 96 CU, bo dla K=5120 bloków jest mało. |
| Specjalizacja K na stałe | Tak, bitowo | Szablon MMVQ z `ncols_x` jako constexpr dla gorących kształtów: 5120, 17408, 6144 (Qwen) i 2048 (LFM). |
| SLC dla wag ekspertów | Tak | Bit SLC w buffer load MMVQ-ids. Dla gęstych macierzy już nie działało (NOTES K1). Eksperci LFM to inny wzorzec (strumień raz na token). |

## 4. Pomysły dla nas

1. **LFM2.5 (też Qwen): zatrzymany PM4 dla grafu decode, po etapie pomiarowym.**
   - **Etap 0** (1–2 dni):
     - rozszerzyć `~/wt/lfm2-prof/launch_cost.hip` o kolejkę ROCr i jeden pakiet vendor z IB zawierającym 500 `DISPATCH_DIRECT` pustego kernela;
     - wzorować się na `pm4_gfx10.rs:539-618` i `packet.rs:415-462`;
     - trzy warianty granicy: (a) tylko CS_PARTIAL_FLUSH, (b) + ACQUIRE_MEM 0x380, (c) + 0xc380 (L2);
     - kernargi w VRAM.
     - Porównać z naszymi 2.53 µs/granicę. Jeśli (b) wyjdzie ≤1 µs, iść dalej.
   - **Etap 1** (2–4 tygodnie):
     - w `ggml-cuda.cu` alternatywa dla `hipGraphLaunch` dla ustabilizowanego grafu decode;
     - po instancjacji przejść po węzłach grafu i zbudować IB;
     - przy aktualizacji grafu (zmiana kernargów) przebudować IB albo łatać kernargi w puli VRAM, jak hipfire łata pozycje.
   - Zysk `[SZACUNEK]`, przy 1–2.4 µs/dispatch zmierzonych przez hipfire na gfx1100:
     - LFM 416 granic → −0.4…−1.0 ms z 4.1 ms (**+10…+30% t/s**). Benchmark: ich A3B na XTX w PM4 robi 603 dispatchy w 3.97 ms/token.
     - Qwen ~930 kerneli/krok (weryfikacja + draft) → −0.9…−2.2 ms z 28.9 (+3…+8%).
   - Ryzyko:
     - zawieszenia GPU (u nich surowy PM4 do sterownika timeoutował na XTX, a jeden błąd VMM zrzucił kartę z PCIe, `CHANGELOG.md` v0.4.2 „Lloyd2/Lloyd4”);
     - synchronizacja z wejściami grafu wysyłanymi `hipMemcpyAsync`;
     - utrzymanie przy rebase'ach upstreamu.
   - Pomiar: llama-bench tg128 przeplatane A/B, hash logitów 64 kroków (te same kernele, więc wynik musi być bitowy), liczba granic z rocprofv3.

2. **Qwen prefill: tanie, bitowe triki z V2C w MMQ (RDNA3).**
   - Co zmienić w `mmq-vec-dot.cuh` i `mmq.cuh`:
     - (a) akumulator WMMA i32 inicjowany 0x4B400000 i `v_sub_f32` zamiast konwersji w epilogu `dmA.x*dsB.x*C.x[l]` (`mmq-vec-dot.cuh:357-361`);
     - (b) skale `x_dm` per wiersz w VGPR i DPP `row_share` zamiast odczytu z LDS dla każdego `l`;
     - (c) układ LDS „fragment-major” dla `load_ldmatrix` (ciągłe 128 B na fragment, zapisy b64 bez konfliktów).
   - Najpierw audyt ISA pętli (`--save-temps`): ile VALU przypada na epilog między WMMA. Dziś na każde 32 K przypada ~8× (`cvt` + 2 mnożenia/FMA + `ds_load` skali) na dwie WMMA iu8.
   - Zysk `[SZACUNEK]`: 5–15% czasu MMQ, czyli +4–10% pp. U hipfire sam epilog per-128 dał +15%.
   - Koszt: 3–5 dni. Ryzyko niskie, wynik bitowy.
   - Pomiar: rocprofv3 MMQ przy pp4096, hash logitów.

3. **Qwen prefill: X128 dla K-quantów (nie bitowe, za bramką KLD).**
   - Co zmienić:
     - nowy blok aktywacji q8 ze skalą per 128 i całkowitymi sumami per 32 (dla członu min);
     - w `vec_dot` Q4_K/Q5_K/Q6_K akumulacja Σ sc_j·C_j w i32 (skale 6-bit z `load_tiles` zostają całkowite) i jedna FMA float na 128.
   - Zysk `[SZACUNEK]`: +8–15% pp. hipfire: +15% przy pp512 na XTX, KLD +0.0002.
   - Koszt: 1–2 tygodnie (`load_tiles` + kwantyzacja aktywacji + epilog).
   - Ryzyko:
     - jakość, bo skala co 128 to grubsza kwantyzacja aktywacji;
     - wymaga `llama-perplexity --kl-divergence` vs baza na 24 chunkach, jak u nich.
   - Pomiar: pp512/pp4096/pp32k + KLD.

4. **Qwen: DFlash2 B=16. Potwierdzenie pomysłu 1 z 22-lucebox, z danymi z gfx1100.**
   - Nowe względem 22-lucebox:
     - (a) τ≈13 na krótkim kodzie i ~2 na 21K na tym samym drafterze;
     - (b) nasz `fattn-kvq` i K4 już przyjmują 16 tokenów, więc nie potrzeba nowego kernela atencji;
     - (c) ich cykl to ~49 ms przy 15 GB; u nas weryfikacja 16 = 35.0 ms + draft ~5 ms ≈ 41 ms `[SZACUNEK]`.
   - Zysk `[SZACUNEK]`:
     - kod przy τ 6–13: 150–320 t/s;
     - proza przy τ 1.1–1.7 przegrywa z naszym MTP (ich fikcja 60.8 t/s);
     - konieczny wybór MTP/DFlash per żądanie (pomysł 3 z 22-lucebox).
   - Koszt: 0.5–1 dnia na `common/speculative.cpp:1074-1081`. Pomiar: `spec_sweep`.

5. **LFM2.5: decode atencji q8_0 z GQA-shared** (instancja q8_0 w kvq albo bitowy wariant vec, `lfm-decode-round2.md` §4).
   - hipfire dostarcza twarde dane z XTX: współdzielenie K/V między głowami Q dało 300→153.5 µs/warstwę przy 32K (+10.6% e2e).
   - Przepis na tanią dekwantyzację q8_0→f16: `v_perm` + 0x6400 + odejmowanie 1152 = 2.25 VALU/element.
   - Zysk: ten sam co w `round2` (98k: −1.1 ms, +19%).
   - Koszt: 3–5 dni. Ryzyko: wariant WMMA nie jest bitowy.

6. **Specjalizacja MMVQ na kształt (bitowa, tania).**
   - `ncols_x`/K jako stała szablonu dla 5120/17408/6144 (Qwen) i 2048/1536 (LFM) w ścieżkach n=1 i 2–8 kolumn.
   - Zysk `[SZACUNEK]`: ~0.5–1%. U hipfire +1.0% AR przy 50 t/s.
   - Koszt: 1 dzień. Uwaga na rozrost binarki (typy × n × kształty).
   - Pomiar: rocprofv3 MMVQ + hash logitów.

7. **LFM2.5: bit SLC dla wag ekspertów w MMVQ-ids** (gate+up, down). Do zbadania też w związku z losowym „slow mode” gate+up (`round2` 3b).
   - Zysk `[SZACUNEK]`: 0–2%. Koszt: godziny.
   - Pomiar: 8 profili na wariant, bo „slow mode” jest losowy.

8. **Outside the box: bramka jakości jak u hipfire.**
   - Stały KLD na 24 chunkach + `.kldseq` (hash sekwencji KLD) jako pin per arch. Każda niebitowa zmiana (pomysły 3, 5) musi go reprodukować albo jawnie przepiąć.
   - Koszt: dzień. Zysk: szybsze, bezpieczniejsze decyzje o zmianach niebitowych.

## 5. Krytyka

- **„307.9 t/s” i „132 t/s” to jeden krótki prompt kodu przy greedy.**
  - 38 tokenów promptu, 157 wygenerowanych, τ 13.
  - Na prozie mają 60.8 t/s.
  - W samplowanych sesjach z thinking DFlash spada do 15.5–17.7 t/s, poniżej AR 39.75 (`2026-08-21-qwen38-mqv2-mtp-prefix-cache.md:85-99`).
  - Sami oznaczają tabele jako „historical” (`docs/BENCHMARKS.md:1-60`). Uczciwie, ale nagłówek README wprowadza w błąd.
- **Porównanie z nami nie jest 1:1.**
  - Ich 27B ma 15 GB (MQ4, 4.25 bpw) wobec naszych 17.6 GB.
  - Ich KV Q8_0 jest 2× większe niż nasze q4_0.
  - Teacher-KLD MQ4-XT to 0.048 WT2. Naszego KLD vs BF16 nie znam, więc nie da się stwierdzić, kto ma lepszą jakość na bajt.
  - Na bajt ich AR (~690 GB/s `[WNIOSEK]`) jest na poziomie naszego MMVQ.
- **W czym jesteśmy lepsi:**
  - MTP: 104 vs ~76 t/s. Ich własny wniosek był, że MTP na XTX nie dobije do 100 (`docs/plans/mtp-goal-a-asymptote-ruling-2026-05-23.md`). Nam się udało dzięki weryfikacji 5 kolumn przy ~700 GB/s (u nich N=3 = 305 GB/s), stanowi GDN/conv z opóźnieniem bez snapshotów i draftowi MTP jednym grafem.
  - Długi kontekst: 100.6 t/s przy 94k vs ich 61 przy 32K. Pomaga `fattn-kvq` q4_0 dla wszystkich głów i tokenów.
  - Bitowo dokładny stan GDN f32 (ich Q8+EF jest stratny).
- **Prefill 3× to w większości wybór stratny (A4).** Do tego własny format z FWHT. Bez re-kwantyzacji modelu nie do wzięcia.
- **Dużo inżynierii nie dotyczy gfx1100:** NPU XDNA2, gfx1201 FP8, EP2, PeaceMaker. Kilka dźwigni gfx1201 (replay GDN w 2 uruchomieniach, akceptacja samplowana na urządzeniu) nie ma wersji na gfx1100.
- **Ich LFM to 8B-A1B na gfx1201** (241 t/s), z ekspertami MQ4 i KLD vs bf16 **0.424** (`crates/hipfire-arch-lfm2moe/NEXT-STEPS.md`). Jakościowo nieporównywalne z naszym Q5_K_M.
- **Wyniki negatywne zgodne z naszymi:**
  - drzewo DDTree na gfx1100 przegrywa z łańcuchem (`AGENTS.md:514-535`);
  - MTP+DFlash razem: 140–148 vs 219.6 t/s;
  - wiele wierszy na falę w GEMV nie działa;
  - fuzje MoE down+combine dają szum.

## 6. Werdykt

**Średnia–wysoka (dla LFM: wysoka).** Kernelowo w decode nie są przed nami: GEMV jest na tym samym poziomie pasma, a MTP i długi kontekst mamy wyraźnie lepsze. Repo daje jednak jedyny zmierzony na naszym GPU sposób na koszt granicy kernela, czyli zatrzymany PM4 z kernargami w VRAM (A3B ×1.146, 27B +6.3% na XTX). To jest wprost nasze wąskie gardło w LFM. Do tego konkretny przepis na tańszy epilog MMQ w prefillu i niezależne potwierdzenie DFlash2 B=16 na gfx1100.
