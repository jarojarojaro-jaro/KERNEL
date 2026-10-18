# 16c. E1: port kernela `kvq` na CUDA (Ampere+)

Data: 2026-10-16. Autor: agent CudaKvq. Zlecenie: eksperyment E1 z raportu 15d (`15d-prefill-dlugi-kontekst.md:187-218`).
Kod: worktree `~/wt/kvq-cuda`, gałąź `kvq-cuda` od `cuda-3090-opt` (`3da7a02ec`), commity `f08dc78bb` (kernel), `67445d884` + `678473a27` (wyjątek dla decode 1 tokenu D256 q4_0, §9). Wyłączniki: `GGML_CUDA_KVQ=0` (całość), `GGML_CUDA_KVQ_N1_D256_Q4=1` (włącza kvq także dla decode 1 tokenu D256 q4_0; domyślnie wyłączone).
Surowe wyniki: `~/qwen-opt/cloud/results/kvq-cuda-20261016/` (3090) i `.../kvq-cuda-20261016/5060ti/`. Skrypty: `~/qwen-opt/cloud/runs/kvq-cuda/` (`inst/*.sh`, `perf_table.py`, `bench_table.py`) i `runs/kvq-cuda-5060ti/`.

## TL;DR

1. **E1 przechodzi kryterium kill z dużym zapasem.** Na 3090 tg64 przy 64k rośnie o **+36.8%** dla Qwen3.8-27B (28.61 → 39.14 t/s, KV q4_0) i o **+30.4%** dla LFM2.5-24B (159.65 → 208.12 t/s, KV q8_0). Próg kill to +10%. Szacunek z 15d (~37 i ~200 t/s) potwierdził się, a dla Qwena wynik jest nawet lepszy.
2. **MTP przy 64k (serwer, flagi A3):** 70.33 → **89.75 t/s (+27.6%)**, przy 32k +13.8%, przy 8k +2.4%. Akceptacja draftu bez zmian (366/578 vs 371/556 tokenów). Wbrew szacunkowi 15d baza MTP@64k na 3090 to już 70 t/s, a nie 52–55 t/s.
3. **5060 Ti (sm_120, Blackwell, KV q8_0) też zyskuje:** Qwen UD-Q3_K_XL tg64 @64k **+24.6%** (20.61 → 25.69), LFM Q4_K_M **+30.0%** (119.82 → 155.77). Przy krótkim kontekście różnica mieści się w ±0.1%.
4. **Kernel FA osobno, 64k, układ cache KV, 3090:** Qwen q4_0 przy 1 tokenie 680 → **115 µs** (5.9×, ~656 GB/s), przy 5 tokenach 1054 → 236 µs. LFM q8_0 przy 1 tokenie 301 → 120 µs (2.5×). Na 5060 Ti Qwen q8_0 przy 1 tokenie 895 → 347 µs, czyli ~92% pasma 448 GB/s.
5. **Poprawność:** test-backend-ops `FLASH_ATTN_EXT` daje 4095/4095 z kvq i bez, na sm_86 i sm_120 (w tym 36 nowych przypadków). Greedy md5 na świeżych serwerach jest deterministyczny w obu trybach. Tekst z kvq różni się od bazy (zmiana numeryki, jak dla HIP kvq).
6. **Bramka KLD: 4 z 5 zgodnie z oczekiwaniem, 1 FAIL na granicy.** Kanarek (KV q4_0) poprawnie FAIL przy +22σ. Przeszły: LFM ub1 (kvq **lepszy** od vec o −2.0σ), LFM ub5, Qwen ub5 (kvq lepszy od ścieżki MMA_F16 o −2.0σ). **Qwen ub1 (zwykły decode) FAIL przy +2.53σ:** 0.002899 vs 0.002527. Same top i 99.9% KLD przechodzą. Kontrola szumu (to samo jądro, inny podział KV) jest w §5. Moja interpretacja i decyzja do podjęcia są w §6.
7. **Aktualizacja 2026-10-18 (§9): powtórka bramki dla Qwena na dłuższym tekście (5 × 8192 tok.) daje FAIL** na ogonie 99.9% KLD (×2.04 wobec vec, średnia +1.52σ, same top −1.98σ). Kontrola szumu (sam podział KV) też oblewa ogon (×1.41). Zgodnie z regułą wszedł wąski wyjątek: decode 1 tokenu D256 q4_0 zostaje na vec. **Koszt:** tg64@64k Qwena wraca do 27.40 t/s (kvq dawał 36.99). Weryfikacja MTP (pp5@64k) zachowuje zysk: 141.83 vs 103.18 t/s bez kvq. LFM, q8_0 i ub 2–16 bez zmian.

## 1. Co zbudowałem

Nowy plik `ggml/src/ggml-cuda/fattn-kvq-mma.cu` (+`.cuh`), wybierany w `fattn.cu` jako `BEST_FATTN_KERNEL_KVQ_MMA` przed vec/MMA_F16. Wymagania: NVIDIA cc ≥ 8.0, K/V q4_0/q4_0 albo q8_0/q8_0, D ∈ {64, 128, 256}, Q->ne[1] ≤ 16, KV % 256, maska bez broadcastu po głowach. Bez sinks, ALiBi i softcap.

- **Jedno przejście po KV dla całej grupy GQA:** kolumny Q (tokeny × głowy grupy) idą jako wymiar N mma.sync m16n8k16, w grupach po 8. Blok obsługuje 8·ncg kolumn: ncg ≤ 2 dla D 256 i ≤ 4 dla D ≤ 128 (limit rejestrów akumulatorów; przy D 64 i ncg 8 były spille). Qwen n=1 (6 kolumn) i n ≤ 2 mieści się w jednym kafelku, n=5 w dwóch (drugi czyta KV zwykle z L2).
- **KQᵀ = K·Qᵀ:** K dekwantyzowane z pamięci współdzielonej prosto do fragmentów A (ten sam układ co q4_0/q8_0: wartości 2t, 2t+1, 2t+8, 2t+9 to dwa odczyty u16 na wiersz i blok). Q jest wstępnie przeskalowane (scale·log2e) do f16 we fragmentach B w smem.
- **Softmax online w domenie log2 (f32).** Prawdopodobieństwa zamieniam na fragment B dla Pᵀ przez `movmatrix` (transpozycja 8×8 w rejestrach).
- **VKQᵀ += Vᵀ·Pᵀ:** V dekwantyzowane jak K, transponowane do fragmentów A czterema `movmatrix` na kafel 16×16. Akumulatory f32.
- **Każdy warp ma własny pierścień cp.async** (2–4 etapy, ~9 KiB w locie) i własny zakres 16 wierszy KV. W pętli głównej nie ma synchronizacji całego bloku. Na końcu łączę warpy w smem, a podziały KV łączy `flash_attn_combine_results`. PDL: `pdl_lc`/`pdl_sync` jak w vec.
- Podział KV wynika z occupancy jądra (`cudaOccupancyMaxActiveBlocksPerMultiprocessor` · nsm / bloki). `GGML_CUDA_KVQ_BPSM=n` nadpisuje go do strojenia.
- **Zasoby (ptxas, sm_86):** D256 q4_0 ncg1 to 173 rejestry, 0 spilli, ~41 KB smem, czyli 2 bloki/SM. Bez spilli dla sm_86 i sm_89. Na sm_120 jeden wariant ma spill 36 B: D128 q8_0 ncg4, nieużywany przez nasze modele. HIP (gfx1100) kompiluje plik bez ostrzeżeń (ścieżka wyłączona przez `ampere_mma_available`).
- **SASS/PTX D256 q4_0:** na kafel 16 wierszy przypada 96 `ld.shared.u16` (dekwant), 16 LDS.64 (Q), 32 mma, 66 movmatrix i 18 cp.async.cg (16 B).
- Testy: 36 nowych przypadków poprawności w `test-backend-ops.cpp`: nb 9–16; Qwen/LFM przy kv 65536 i nb 1/5; q8_0 D256. Do tego 45 przypadków perf: Qwen q4_0/q8_0 i LFM q8_0 przy kv 8k/32k/64k, nb 1/2/5/8/16, układ cache KV.

## 2. Środowisko i metoda

| | 3090 | 5060 Ti |
|---|---|---|
| Vast instancja | 56263870 (oferta 56224932), Jordania | 56267012 (oferta 46239656), New Jersey |
| CPU / -t | Ryzen 9 5950X, kwota cgroup 30.72 → `-t 30` | Ryzen 9 5900X, kwota → `-t 11` |
| GPU | RTX 3090 24 GB, sterownik 595.104.02, limit 330 W | RTX 5060 Ti 16 GB, 595.71.05, 180 W |
| binarka | build lokalny nvcc 12.8, sm_86 (drzewo `f08dc78bb`) | build na instancji, sm_120, `GGML_NATIVE=ON` (234 s) |
| $/h | 0.292 | 0.31 |

- A/B w jednej binarce, przełączane `GGML_CUDA_KVQ=0/1`. Ścieżka `=0` to kod `cuda-3090-opt` bez zmian (tylko dodatkowy warunek w wyborze jądra).
- Kolejność ABBA. Mediany po wszystkich próbkach z rozrzutem min–max.
- llama-bench: `-fa 1 -ngl 99 -d 0,8192,32768,65536 -p 5 -n 64 -r 3`. Krótki kontekst LFM ma powtórzenie z `-r 10`. pp5 to proxy kroku weryfikacji MTP (Q->ne[1] = 5).
- Rozgrzewka/izolacja: polecenia GPU szły po kolei pod `flock /root/gpu.lock`. Wyjątek: jeden przebieg perf (`perf-4-kvq0`) nałożył się na llama-bench i wyłączyłem go z tabel (`perf/excluded/`). Ten llama-bench przerwałem i powtórzyłem od zera.

## 3. Szybkość

### 3.1 Jądro FA osobno (test-backend-ops perf, µs/wywołanie, układ cache KV)

3090, mediana dwóch rund ABBA (kvq0: 3 przebiegi, kvq1: 4). Pełna tabela z rozrzutami (kv 8k/32k/64k, nb 1/2/5/8/16) jest w `perf-table.tsv`.

| kształt (64k) | nb 1 | nb 2 | nb 5 | nb 8 | nb 16 |
|---|---|---|---|---|---|
| Qwen D256 GQA6 q4_0 | 705.0 → **116.5** (6.05×) | 1005.9 → 134.8 (7.46×) | 1053.9 → **231.1** (4.56×) | 1027.7 → 332.7 (3.09×) | 1171.9 → 651.2 (1.80×) |
| Qwen D256 GQA6 q8_0 | 636.8 → 194.9 (3.27×) | 1063.7 → 215.8 (4.93×) | 1031.5 → 383.2 (2.69×) | 1071.2 → 589.1 (1.82×) | 1261.2 → 1157.3 (1.09×) |
| LFM D64 GQA4 q8_0 | 286.0 → **119.4** (2.40×) | 1204.6 → 125.8 (9.57×) | 1178.3 → 173.1 (6.81×) | 1196.9 → 192.7 (6.21×) | 1206.3 → 318.0 (3.79×) |

Przy 8k: Qwen q4_0 nb 1 to 97.3 → 28.3 µs (3.43×), LFM q8_0 nb 1 to 41.4 → 23.1 µs (1.79×). Przy nb ≥ 2 stara ścieżka (MMA_F16 z konwersją do f16) jest 4–10× wolniejsza. Na 16 warstwach Qwena przy 64k i 1 tokenie daje to 11.3 → 1.9 ms na token, co odpowiada zmierzonemu przyrostowi tg (35.0 → 25.5 ms/token).

5060 Ti (sm_120), 64k, ABBA (`5060ti/perf-table.tsv`):

| kształt | nb | kvq0 µs | kvq1 µs | × |
|---|---|---|---|---|
| Qwen D256 q8_0 | 1 | 895.2 | 346.9 | 2.58 |
| Qwen D256 q8_0 | 5 | 2272.7 | 476.2 | 4.77 |
| Qwen D256 q8_0 | 16 | 2300.1 | 1579.1 | 1.46 |
| LFM D64 q8_0 | 1 | 382.9 | 224.7 | 1.70 |
| LFM D64 q8_0 | 5 | 2039.8 | 254.7 | 8.01 |
| Qwen D256 q4_0 | 1 | 3738.9 | 198.3 | 18.9 (vec q4_0 na sm_120 jest wyjątkowo wolny) |

Pasmo przy 64k i 1 tokenie, przy założeniu jednego odczytu KV:

| GPU | kształt | wynik | % szczytu |
|---|---|---|---|
| 3090 | Qwen q4_0 (75.5 MB) | 656 GB/s | 70% z 936 |
| 3090 | Qwen q8_0 | 732 GB/s | 78% |
| 3090 | LFM q8_0 (71.3 MB) | 592 GB/s | 63% |
| 5060 Ti | Qwen q8_0 | 411 GB/s | 92% z 448 |

### 3.2 llama-bench, 3090 (`bench-qwen-table.tsv`, `bench-lfm-table.tsv`)

Qwen3.8-27B UD-Q4_K_XL, KV q4_0, 6 próbek na tryb:

| test | d0 | 8k | 32k | 64k |
|---|---|---|---|---|
| tg64 kvq0 → kvq1 (t/s) | 41.63 → 41.89 (+0.6%) | 39.53 → 41.23 (+4.3%) | 34.16 → 39.97 (+17.0%) | **28.61 → 39.14 (+36.8%)** |
| pp5 kvq0 → kvq1 (t/s) | 166.1 → 172.2 (+3.7%) | 164.5 → 177.7 (+8.1%) | 144.1 → 172.5 (+19.7%) | 122.9 → 163.2 (+32.8%) |

Rozrzut tg64 przy 64k: kvq0 28.40–28.97, kvq1 38.30–39.22.

LFM2.5-24B-A2B Q5_K_M, KV q8_0:

| test | d0 | 8k | 32k | 64k |
|---|---|---|---|---|
| tg64 kvq0 → kvq1 (t/s) | 296.6 → 263.0 (szum, patrz niżej) | 276.8 → 256.6 (szum) | 210.2 → 232.2 (+10.5%) | **159.65 → 208.12 (+30.4%)** |

Krótki kontekst LFM powtórzyłem z `-r 10` w ABBA (20 próbek na tryb, `bench-lfm-short-table.tsv`): tg64 d0 279.72 → 286.00 (+2.2%), 8k 248.38 → 275.56 (+10.9%). Rozrzut w obu trybach to 259–303 t/s, więc ten host daje ±8% szumu przy ~3.5 ms/token. W pierwszym pomiarze d0/8k (−11%/−7%) bazowe przebiegi 1 i 4 dały 301/302/302 vs 292/266/260 t/s, czyli był to szum, nie jądro. Potwierdza to 5060 Ti (§3.3) z rozrzutem < 1%.

### 3.3 llama-bench, 5060 Ti (sm_120)

Qwen3.8-27B UD-Q3_K_XL i LFM2.5 Q4_K_M, oba z KV q8_0 (`5060ti/bench-*-table.tsv`, 6 i 10 próbek):

| model, test | d0 | 8k | 32k | 64k |
|---|---|---|---|---|
| Qwen tg64 | 29.76 → 29.79 (+0.1%) | 28.09 → 29.04 (+3.4%) | 24.39 → 27.57 (+13.0%) | **20.61 → 25.69 (+24.6%)** |
| Qwen pp5 | 119.1 → 119.2 | 108.8 → 112.7 | 87.6 → 105.1 (+20.1%) | 70.3 → 96.7 (+37.5%) |
| LFM tg64 | 215.31 → 215.48 (+0.1%) | 191.84 → 202.51 (+5.6%) | 154.39 → 180.88 (+17.2%) | **119.82 → 155.77 (+30.0%)** |
| LFM pp5 | 447.6 → 446.1 | 414.4 → 428.6 | 330.0 → 403.3 (+22.2%) | 254.8 → 373.6 (+46.7%) |

Rozrzuty są tu wąskie (np. LFM tg64 d0: 213.8–215.9 vs 214.8–215.9), więc „spadek” LFM d0 na 3090 to szum hosta, a nie jądro.

### 3.4 Serwer z MTP przy długim kontekście (3090, `mtp/mtp.jsonl`)

Flagi: Qwen3.8-27B UD-Q4_K_XL, A3 (`--spec-type draft-mtp --spec-draft-n-max 4`, wokab draftu 64k, głowica iq4_xs), KV q4_0, `-c 70000`. Prompt to prawdziwy tekst (dokumentacja llama.cpp, md z KERNEL, stdlib Pythona), 512 tokenów odpowiedzi, T=0, ABBA (2 przebiegi na tryb, świeże serwery).

| prompt (tok.) | kvq0 decode t/s | kvq1 decode t/s | zysk | akceptacja kvq0 / kvq1 |
|---|---|---|---|---|
| 6 593 | 99.02 (99.78, 98.26) | 101.36 (101.18, 101.53) | +2.4% | 375/540, 374/544 / 370/561 ×2 |
| 29 538 | 80.77 (80.77, 80.76) | 91.93 (92.37, 91.49) | **+13.8%** | 366/580 / 362/596 |
| 59 383 | 70.33 (70.03, 70.62) | 89.75 (90.18, 89.33) | **+27.6%** | 371/556 / 366/578 |

Prefill bez zmian: 998 t/s przy 59k w obu trybach.

## 4. Poprawność

- **test-backend-ops `-o FLASH_ATTN_EXT`:** 4095/4095 przy `GGML_CUDA_KVQ=1` i `=0` na 3090 (sm_86) i na 5060 Ti (sm_120 z PDL). Logi: `tbo/eval-kvq{0,1}.log`, `5060ti/tbo/`.
- **Greedy md5, świeże serwery, 2 prompty × 400 tok., ctx 8192, ABBA (`greedy/md5.txt`):**
  - kvq0: plain `4589b2ea…` w obu przebiegach, MTP `35ea686c…` w obu;
  - kvq1: plain `88802ce4…` w obu, MTP `d6a1f596…` w obu.
  - Oba tryby są deterministyczne. kvq zmienia tekst od 68. znaku (`A hash map is…` vs `A **hash map** (or hash table) is…`). To oczekiwane przy zmianie numeryki: f16 Q + mma zamiast q8_1 Q + dp4a, f16 P i V zamiast f32. Oba teksty są poprawne.
- **KLD** (`kld/`, `bramka-kld-kanarki`): wikitext-2, referencja f16 KV na tej samej karcie. Qwen: `-c 8192 --chunks 2` (8192 ocenianych tokenów). LFM: `-c 16384 --chunks 3` (24 576 tokenów). `kld_gate.py`, k=2:

| para (baza → kandydat) | mean KLD baza | mean KLD kvq | ΔKLD/σ | same top Δ | 99.9% KLD | werdykt |
|---|---|---|---|---|---|---|
| Qwen q4_0, ub 1: vec → kvq | 0.002527 ± 0.000081 | 0.002899 ± 0.000123 | **+2.53** | −0.68σ | ×1.005 | **FAIL** (tylko średnia) |
| Qwen q4_0, ub 5: MMA_F16 → kvq | 0.004005 ± 0.000183 | 0.003549 ± 0.000145 | −1.95 | −0.21σ | ×0.773 | PASS |
| LFM q8_0, ub 1: vec → kvq | 0.045909 ± 0.002158 | 0.040339 ± 0.001761 | −2.00 | +0.66σ | ×0.667 | PASS |
| LFM q8_0, ub 5: MMA_F16 → kvq | 0.061220 ± 0.002061 | 0.059626 ± 0.001953 | −0.56 | −0.83σ | ×0.845 | PASS |
| kanarek: LFM q8_0 vec → KV q4_0 (kvq) | 0.045909 | 0.124364 ± 0.002808 | +22.2 | −24.6σ | ×1.301 | FAIL (oczekiwany) |

Tabela bramki: `kld/gate-table.txt`, „4 OK, 1 UNEXPECTED”.

**Kontrola szumu numerycznego (§5):** to samo jądro kvq z innym podziałem KV (`GGML_CUDA_KVQ_BPSM=1`) zmienia tylko kolejność sumowania.
- Qwen ub1: 0.002755 ± 0.000088. Względem vec daje to +1.91σ, czyli **PASS**. Względem domyślnego kvq: −0.95σ.
- LFM ub1: 0.044189 ± 0.001930. Względem domyślnego kvq: ΔKLD +1.47σ, same top −1.88σ, 99.9% ×1.278, czyli **FAIL** bramki, choć arytmetyka jest identyczna.
- Wniosek: progi bramki (2σ, ×1.25) leżą na poziomie szumu samej kolejności sumowania na tych hybrydach (por. [[lekcja-kolejnosc-akumulacji-fa]]). FAIL Qwen ub1 (+2.53σ) mieści się w tym szumie.

## 5. Kontrola szumu KLD i strojenie podziału KV

**Podział KV (`GGML_CUDA_KVQ_BPSM`, 3090, µs, `bpsm/`).** Domyślnie podział wynika z occupancy jądra: 2 bloki/SM dla q4_0 D256 i q8_0 D64, 1 blok/SM dla q8_0 D256 (70 KB smem).

| kształt | 1 | 2 | 3 | 4 | 6 |
|---|---|---|---|---|---|
| Qwen q4_0 64k nb1 | 122.0 | **119.4** | 141.1 | 140.9 | 141.1 |
| Qwen q4_0 64k nb5 | 298.2 | **224.5** | 306.8 | 245.0 | 289.8 |
| Qwen q8_0 64k nb1 | 202.5 | **197.4** | 214.9 | 229.8 | 243.4 |
| Qwen q8_0 8k nb5 | **62.1** | 83.5 | 93.0 | 118.1 | 127.2 |
| LFM q8_0 64k nb1 | 127.0 | **118.7** | 145.2 | 147.5 | 171.6 |
| LFM q8_0 64k nb5 | 243.8 | **172.6** | 220.5 | 199.6 | 207.8 |

Domyślne wartości trafiają w optimum albo są w granicach 3% od niego, więc niczego nie zmieniałem.

**Qwen przy krótkim kontekście,** `-r 5` ABBA (10 próbek, `bench-qwen-short-table.tsv`): tg64 d0 41.67 → 41.78 (+0.3%), 8k 39.59 → 41.29 (+4.3%). Regresji nie ma.

## 6. Ocena i decyzja

- **Kill (zysk przy 64k < +10%) nie zachodzi:** +36.8% (Qwen) i +30.4% (LFM) na 3090, +24.6% i +30.0% na 5060 Ti, MTP@64k +27.6%. Hipotezy 15d: H1 potwierdzona (przyrost czasu tokenu przy 64k spada z +11.4 ms do ~1.7 ms dla Qwena). H3 potwierdzona dla Qwena (≤ 2.5 ms). H2 nieistotna, bo MTP@64k już ma 70 t/s.
- **Bramka KLD:** ścieżki weryfikacji (ub 5) i LFM przechodzą z wynikiem lepszym od upstreamu. Jedyny FAIL to Qwen ub 1 przy +2.53σ, z zachowanymi top-p i ogonem 99.9%. W tej samej serii dwie inne pary wyszły o −2.0σ na korzyść kvq, więc moim zdaniem ±2σ to rozrzut między dwiema różnymi, równie dokładnymi numerykami na hybrydzie. Kontrola szumu (§4/§5) to potwierdza: zmiana samej kolejności sumowania daje ±1–1.9σ i potrafi oblać bramkę. Z teorii f16 Q (2⁻¹² względnie) jest dokładniejsze od q8_1 Q w vec (~2⁻⁸) `[INFERENCE]`.
- **Rekomendacja (pierwotna, 2026-10-16):** domyślnie włączone dla ub 2–16 (weryfikacja MTP) i dla LFM; dla Qwen ub 1 powtórzyć KLD na dłuższym tekście. **Rozstrzygnięcie w §9: FAIL → wyjątek dla decode 1 tokenu D256 q4_0 jest domyślny.**

## 7. Koszt

| pozycja | czas | koszt |
|---|---|---|
| 3090 56263545 (zła konfiguracja SSH hosta, zniszczona po ~4 min) | ~0.07 h | ~$0.02 |
| 3090 56263870 | 1.834 h × $0.292 | $0.54 |
| 5060 Ti 56267012 | 0.590 h × $0.31 | $0.18 |
| transfer (~75 GB × $0.0026) | | ~$0.20 |
| **razem** | | **~$0.94** (limit $1.80) |

Wszystkie trzy instancje są zniszczone (`vastai show instances`: brak etykiet `kvqcuda-*`), lokalne watchdogi zabite. RunPod nieużywany.

## 8. Ograniczenia i dalsze kroki

- Brak sinks/ALiBi/softcap i maski z broadcastem po głowach. Tam dalej działa stara ścieżka.
- Dla D 256 i n ≥ 6 (≥ 36 kolumn) jest kilka kafelków x, które czytają KV ponownie, zwykle z L2. nb 16: 1.74× zamiast ~6×. Kandydat: rozdzielić D między warpy, żeby zmieścić 32+ kolumn.
- LFM na 3090 osiąga tylko 63% pasma przy D 64. Kandydat: 8 warpów albo większe kafle (więcej bajtów w locie na blok).
- Nie mierzyłem `spec_sweep` z krótkim kontekstem (regresji przy d0 nie ma: tg64 +0.6% i +0.1%, MTP 8k +2.4%) ani VRAM. kvq nie alokuje bufora f16 K/V, więc dla n ≥ 2 VRAM powinien spaść `[INFERENCE]`.
- Turing (sm_75) nie jest obsłużony (cp.async). Ścieżka HIP RDNA3 (`fattn-kvq.cu`) jest nietknięta.

## 9. Powtórka bramki KLD dla Qwena (2026-10-18)

Zlecenie rodzica: powtórzyć bramkę Qwena na dłuższym tekście z kontrolą szumu. PASS → kvq zostaje dla decode 1 tokenu. FAIL → wąski wyjątek za przełącznikiem i pomiar.

**Środowisko:** Vast 56603163 (oferta 56200479, Utah), RTX 3090, sterownik 595.71.05, limit 300 W, EPYC 7402 (kwota → `-t 15`). Build na instancji z bundla (`67445d884`, sm_86, 221 s). Protokół jak w 16c: wikitext-2, `-c 8192 -b 8192 -ub 1`, referencja f16 KV na tej samej karcie, ale **`--chunks 5`** (40 960 tokenów zamiast 8 192). Wyniki: `~/qwen-opt/cloud/results/kvq-cuda-20261016/kld-c5/`.

| para (baza → kandydat) | mean KLD baza | mean KLD kand. | ΔKLD/σ | same top Δ | 99.9% KLD | werdykt |
|---|---|---|---|---|---|---|
| vec → kvq | 0.011093 ± 0.001968 | 0.016625 ± 0.003057 | +1.52 | −1.98σ | 1.106 → 2.256 (×2.04) | **FAIL** (ogon) |
| vec → kvq z innym podziałem KV (`GGML_CUDA_KVQ_BPSM=1`) | 0.011093 | 0.012422 ± 0.002256 | +0.44 | −1.21σ | ×1.41 | FAIL (ogon) |
| kvq → kvq z innym podziałem KV | 0.016625 | 0.012422 | −1.11 | +0.77σ | ×0.69 | PASS |

- Chunki 1–2 to ten sam tekst co w 16c (te same liczby: kvq 0.00290 vs vec 0.00253 po 2 chunkach).
- Cały ogon pochodzi z chunku 3 (średnia vec skacze 0.0025 → 0.0166). Pojedyncze tokeny mają tam KLD ~20 we wszystkich trzech wariantach (max: vec 20.56, kvq 23.93, kvq-bpsm1 19.50), czyli to miejsca, gdzie KV q4_0 samo psuje rozkład. 99.9% z 40 960 tokenów to ~41 tokenów i ta statystyka jest niestabilna. Sama zmiana kolejności sumowania w tym samym jądrze przesuwa ją o ×0.69/×1.41.
- Interpretacja: średnia i top-p przechodzą. Ogon jest gorszy, ale w zasięgu szumu kolejności sumowania, więc różnicy jakości nie da się tu wykazać ani wykluczyć. Reguła bramki mówi FAIL, więc wszedł wąski wyjątek.

**Wyjątek** (`678473a27`, `fattn-kvq-mma.cu`, `ggml_cuda_flash_attn_ext_kvq_mma_supported`): przy `Q->ne[1] == 1`, D 256 i K q4_0 kvq nie jest wybierany i wybór wraca do vec. `GGML_CUDA_KVQ_N1_D256_Q4=1` włącza kvq z powrotem. Pomiar na tej samej instancji (llama-bench, KV q4_0, `-d 0,65536 -p 5 -n 64 -r 3`, kolejność off/on/wyj./wyj./on/off, `kld-c5/bench/`; ostatni przebieg „off” przerwano przy 64k, więc off@64k ma 3 próbki):

| test | kvq off | kvq on | wyjątek |
|---|---|---|---|
| tg64 d0 | 40.41 (39.47–41.19) | 40.91 (40.28–41.33) | 40.93 (40.47–41.48) |
| tg64 d65536 | 27.29 (27.26–27.33) | 36.99 (36.89–37.01) | **27.40** (27.34–27.44) |
| pp5 d0 | 140.70 | 138.65 | 142.29 |
| pp5 d65536 | 103.18 (102.44–113.62) | 139.27 (130.46–165.49) | **141.83** (131.94–165.85) |

- Wyjątek odbiera zysk zwykłego decode Qwena (tg@64k +35.5% → +0.4%). Zachowuje go dla weryfikacji MTP (pp5@64k +37.5%) i dla wszystkich ścieżek q8_0/LFM. MTP@64k (§3.4, +27.6%) korzystał głównie z weryfikacji, ale serwer MTP robi też decode 1 tokenu (prompt/draft), więc część zysku może zniknąć `[INFERENCE]`, nie zmierzone.
- KLD wariantu z wyjątkiem nie zdążyło się skończyć (instancja zniszczona na polecenie użytkownika przed restartem serwera). Przy `-ub 1` wszystkie wywołania FA mają 1 token, więc z wyjątkiem idą ścieżką vec i log powinien być IDENTICAL z `qwen-q4-vec.log` `[INFERENCE]`, niezmierzone.
- Na tej instancji zysk on/off przy 64k jest mniejszy niż w 16c (+35.5% vs +36.8%; inny host: EPYC 7402, 300 W).
- Możliwe dalsze kroki (bez zlecenia): (a) bramka na innym korpusie albo z większą liczbą chunków, żeby ustabilizować 99.9%; (b) dokładniejszy wariant n=1, np. akumulacja P·V w f32 zamiast f16 P.

**Koszt §9:** 56603163 przez ~1.42 h × $0.291 ≈ $0.41, transfer ~17.5 GB ≈ $0.05, **razem ~$0.46** (limit $0.80). Instancja zniszczona, watchdog zabity, `vastai show instances`: 0 naszych. Łączny koszt E1: ~$1.40.

## Do bazy wiedzy

1. **kernele/fattn-kvq.md** (aktualizacja, sekcja „Luka na CUDA” → „Port CUDA 16c”):
   - kvq-mma na Ampere+ (commit `f08dc78bb`, gałąź `kvq-cuda`, `GGML_CUDA_KVQ=0`);
   - 3090 tg64@64k: Qwen 28.61 → 39.14 (+36.8%), LFM 159.65 → 208.12 (+30.4%); MTP@59k: 70.33 → 89.75 t/s (+27.6%);
   - FA op 64k: Qwen q4_0 705 → 116.5 µs, LFM q8_0 286 → 119.4 µs;
   - źródło: `16c-kvq-cuda.md` §3, `results/kvq-cuda-20261016/{bench-*-table.tsv,perf-table.tsv,mtp/mtp.jsonl}`.
2. **nvidia/fa-kv-kwantyzowane-cuda.md** (aktualizacja):
   - luka zamknięta w forku;
   - 5060 Ti sm_120: Qwen q8_0 tg@64k +24.6%, LFM +30.0%; jądro osiąga 92% pasma (`5060ti/bench-*-table.tsv`).
3. **eksperymenty/2026-10-16-kvq-cuda.md** (nowa): przebieg E1, ABBA, kill niespełniony, koszt ~$0.94 (`16c §7`).
4. **lekcje/lekcja-kld-szum-kolejnosci.md** (nowa):
   - zmiana samej kolejności sumowania (split-K) w tym samym jądrze daje ±1–1.9σ i dla LFM oblewa bramkę (99.9% ×1.278);
   - bramka 2σ wymaga kontroli „to samo jądro, inny podział” (`results/kvq-cuda-20261016/kld/`, `16c §4`).
5. **lekcje/lekcja-vast-authorized-keys.md** (nowa):
   - host 213.186.183.140 (Jordania): sshd odrzuca klucz („bad ownership or modes for /root/.ssh/authorized_keys”);
   - naprawa: pętla chown/chmod w onstart (`runs/kvq-cuda/up.sh:56-59`).
6. **lekcje/** (dopisać do istniejącej o nakładaniu/pkill albo nowa):
   - `pkill -f "bench.sh"` przez ssh zabił własną powłokę;
   - kolejne zadania GPU na instancji uruchamiać pod `flock /root/gpu.lock`, bo jeden przebieg perf nałożył się na llama-bench i trzeba go było wyrzucić.
7. **chmura**: upload z domu ~155 KB/s (53 MB binarek w 5:42 min). Dla iteracji lepszy bundle (355 KB) + build na instancji (sm_120: 234 s przy 11 wątkach).
8. **research/raport-15d** (korekta): MTP@64k na 3090 to już 70.3 t/s bez kvq, a nie 52–55 t/s `[INFERENCE]` (`mtp/mtp.jsonl`).
9. **kernele/fattn-kvq.md** (dopisać do pkt 1):
   - decode 1 tokenu D256 q4_0 (Qwen bez MTP) domyślnie na vec (`678473a27`, `GGML_CUDA_KVQ_N1_D256_Q4=1` włącza kvq);
   - powód: bramka KLD na 5 × 8192 tok. FAIL na ogonie (×2.04), z kontrolą szumu ×1.41;
   - tg@64k Qwena: off 27.29 / kvq 36.99 / wyjątek 27.40 t/s; pp5@64k 103.18 / 139.27 / 141.83 t/s (`16c §9`, `kld-c5/`).
10. **metody/bramka-kld-kanarki.md** (aktualizacja):
   - 99.9% KLD na 40 960 tokenach to ~41 tokenów; na Qwenie z KV q4_0 jeden fragment tekstu (chunk 3 wikitext, KLD tokenu ~20) decyduje o werdykcie;
   - sama zmiana kolejności sumowania przesuwa 99.9% o ×0.69–×1.41;
   - przy kandydatach blisko progu zawsze dołożyć kontrolę „to samo jądro, inny podział” (`16c §9`).
