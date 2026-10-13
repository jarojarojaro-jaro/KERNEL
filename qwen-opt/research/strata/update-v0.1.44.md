# Strata: aktualizacja badania (a0116b27 / v0.1.43.1 → ed4773eb / v0.1.44)

Klon `~/research/Strata`, `git fetch` z 2026-10-13. `origin/HEAD` = `ed4773eb` = tag `v0.1.44` (wydany 2026-10-13 19:26 UTC). Po tagu nie ma żadnych commitów. Delta liczy 271 commitów (241 bez merge'y, 355 plików, +46.5k/−1.2k linii). Autorzy: Niko1221 237, reszta to wkład społeczności (sergiywith NVFP4 6, Andy Slater SYCL 4, Techannel P40 4, Shawn Jackson geometria GGUF 4 i inni). Większość linii to nowe platformy: Metal/Mac (~75 commitów `metal:`), NVFP4, obrazy, Unsloth, Qwen3.6. Dla nas liczą się trzy wątki:

1. gałąź **f-latency**, czyli opóźnienia silnika (merge `0b8d3101`);
2. **ścieżka Qwen3.6-35B-A3B** (`src/qwen35/q36_engine.cu`, 2513 linii): ta sama rodzina GDN+GQA z blokiem MTP co nasz model, napisana od zera;
3. kilka issue/PR z ROCm o tym, jak strumienie trafiają na kolejki sprzętowe.

Nic nie było budowane ani uruchamiane. `#N` = https://github.com/Niko1221/Strata/issues/N lub /pull/N. Oszacowania oznaczam [INFERENCE].

Nasza arytmetyka (stan obecny): krok ≈ 29.4 ms przy ≈ 102 t/s, czyli ≈ 3.0 tok/krok, więc **1 ms/krok ≈ +3.5% t/s**.

---

## 1. Oś czasu delty

| Kiedy (2026-10) | Commity | Co |
|---|---|---|
| 10-11 (gałęzie sprzed taga) | `0a379a1f`, `b60aab1b`, `446bec51`, `2d47caa4`, `b59e69c7` | `STRATA_HC_Q8`: projekcje hyper-connection czytane jako Q8_0 zamiast kopii BF16 (gfx12 domyślnie: R9700 +2.5–4%, KL 0.0003–0.0010) |
| 10-11 | `24d972e5` | Multi-GPU: warstwa draftu na **pierwszej** karcie w pipeline (+19–22% kod na 2–4× R9700) |
| 10-11 00:16 | `009dc6c1` | `STRATA_DRAFT_TIMING=1`: pary cudaEvent wokół grafu rundy draftu i każdego kroku oraz czas hosta |
| 10-12 10:42–23:19 | `ad9eb890`…`513fc615` | Port Metal (M4/M5). Negatywne próby: persistent kernel z barierą (`4e5ea96d`), GEMV na simdgroup-matrix (`79b98c82`), chunked WY GDN (`272bbbbd`), `qsa_flash`. Fold commitu GDN na początku następnego okna (`1f4b6b36`, ten sam pomysł co nasz S4). Draft MTP BF16→Q8_0 (`8bf827b9`) |
| 10-12 20:19–21:13 | `e51b4379`…, `546d7675`, `6e6d4faf` | NVFP4 (sergiywith); eksperci NVFP4 w decode bitowo identyczni, 1.14–2.5× |
| 10-12 20:41–23:30 | `3a020d58`, `de81ac91`, `1176eb3c`, `b5568470`, `38436f2a` | **Qwen3.6 T1**: implementacja referencyjna, parity z llama.cpp, osobny silnik, **spekulacja MTP z bloku nextn GGUF**, decode zawsze na kernelach GDN per token |
| 10-12 20:48–23:08 | `0d3553fc`, `5ef9f4c8`, `945fee23`, `465cd61d` | Miarka jakości `tools/quant_quality.py`; bench GEMV Q8_0; Q8_0 GEMV „1 wiersz/blok” tam, gdzie zmierzono zysk; kernele MMQ dla K-quantów jako osobna biblioteka |
| 10-13 00:30–02:48 | `f29e74c7`, `27f2d167`, `54eb42a3`, `b23869bf` | q36: atencja promptu FP16, kernel GDN chunk z podziałem na kolumny, split-K SGEMM dla małych projekcji F32, tryb hybrydowy, rozgrzewka przy ładowaniu |
| 10-13 01:24–04:49 | `65514542`, **`6f3e3810`**, **`1d21b9cd`**, `728097fb`, `3d5819df` | **f-latency**: graf commitu jednym launchem na rodzaj warstwy, profil etapów MTP, **priorytet strumienia draftu na HIP**, priorytet strumienia kopii, ponowny start po `hsa_exception` |
| 10-13 nocą | PR-y społeczności: `ac21812c` (#2170), `d8a49433` (#2175), `640ac438` (#2191), `9c5bbc36`/`22161613`/`40ba0cf9` (#2178, P40), SYCL `65cf5435`/`d4b48b33`/`e682bded` | Prompt ustępuje krótkiemu żądaniu; `env_to_user`; `--prefill-head-alias`; P40; Arc |
| 10-13 09:17–09:34 | merge'e do `f-144-rel`, `289f8f03` | wersja 0.1.44 |
| 10-13 10:00–21:23 | Mac, `f087f780`/`ab6bce05` (pin by need), `1aa0abf6` (adapt-async w arenie), README | Tag `v0.1.44` = `ed4773eb` |
| Po tagu | #2322/#2323/#2324 | Zapowiedziane 0.1.44.1 (CUDA 12.1, Metal M2, Pascal bez AVX2) |

**Status PR-ów z poprzedniego badania:**
- **#2231** (bitowo identyczne +11.7% na 7900 XTX) został **zamknięty bez merge'a** przez autora PR-a 2026-10-13 11:30, bez komentarza. W delcie nie ma ani jednego commitu, który by go przenosił. Nasze K2 zrobiło swoje odpowiedniki niezależnie, więc nic się dla nas nie zmienia. Upstream po prostu nie zwalidował tych zmian.
- **#2226** (persistent kernel z barierą, gfx1030) jest nadal otwarty. Nowe liczby: **−6.6% (4K) / −4.4% (32K) ms/okno, 10/10 par** (wcześniej −2.8…−4.2%). Doszły testy parity i `hc_persist_default_off`.
- **#2020** (F16 WMMA dla K-quantów w prefill, gfx11) jest otwarty, bez ruchu.

---

## 2. Co nowego i jak działa

### 2.1 f-latency: opóźnienie jednego okna (merge `0b8d3101`)

**(a) Graf commitu jednym launchem na rodzaj warstwy** (`6f3e3810`, `STRATA_COMMIT_BATCH`, domyślnie włączony):
- Commit po oknie verify miał ok. 98 węzłów grafu, bo na każdą warstwę GDN szedł osobny launch dla historii conv i osobny dla stanu.
- Teraz są dwa kernele z wymiarem siatki „warstwa”:
  - `gdn_conv_commit_layers_kernel`, `blockIdx.y` = warstwa (`src/kernels/cuda/verify_kernels.cu`, w diffie `+188…+226`);
  - `gdn_step_commit_layers_kernel`, `blockIdx.z` = warstwa.
- **Historia conv jest po prostu gatherem.** Nowa historia to ostatnie 3 wiersze sklejenia `[hist(3) | x_0..x_{n_keep-1}]`:
  `src = n + j; seq[j] = src < 3 ? hist[c*3+src] : qkv[(src-3)*C + c]`.
- `n_keep` jest czytane z pamięci urządzenia, więc graf jest stały dla każdego T.
- Bitowość pokazują `gdn_parity` (n_keep 1–8) i `qsa_parity`.
- Efekt: R9700 UD-Q4_K_XL **2.35 → 0.65 ms GPU na commit**. Na HIP runda draftu czekała na commit.

**(b) Strumień draftu z wysokim priorytetem na HIP** (`65514542` opt-in, `1d21b9cd` domyślnie na gfx1200/1201):
- Komentarz w `src/core/mtp.cpp:445-449`: „ROCm hands out hardware queues per priority (GPU_MAX_HW_QUEUES per level)”.
- Strumień draftu dzielił kolejkę sprzętową z verifierem, więc runda draftu stała w FIFO za grafem commitu, którego draft wcale nie potrzebuje.
- Strumień z wyższym priorytetem dostaje własną kolejkę i commit liczy się równolegle z draftem.
- Efekt: R9700 **draft wall 5.8 → 3.5 ms/okno**.
- Na gfx1100 przełącznik jest opt-in (`STRATA_MTP_HIP_PRIO=1`), bo autor nie ma tej karty i trzyma się zasady „default tylko po pomiarze na danej karcie”.

**(c) Strumień kopii z wysokim priorytetem** (`728097fb`, opt-in): w trybie `--pcie-mode dma` kopie i host function podnosząca flagę stały w tej samej kolejce **za grafem okna, który na tę flagę czekał w spinie**. Na R9700 każde żądanie kończyło się timeoutem na warstwie 1. To jest zakleszczenie, które wynika wprost z mapowania strumieni na kolejki.

**(d) Narzędzia:**
- `STRATA_DRAFT_TIMING` (`009dc6c1`): rozbicie rundy draftu na pre/launch/PLE/wait0/waitj (host) i czasy GPU każdego kroku.
- `STRATA_MTP_PROFILE` (`65514542`): znaczniki GPU między etapami warstwy draftu wewnątrz przechwyconego grafu. Każdy znacznik to dodatkowy węzeł, a autor zaznacza, że sumy wychodzą przez to trochę zawyżone.
- `STRATA_VERIFY_NODES` dla grafów draftu.
- `STRATA_COMMIT_TIMING`.

**(e) Issue #2305, raport społeczności z R9700 (gfx1201):**
- Czas draftu jest **bimodalny i zależy od startu silnika**: 2.3–2.9 vs 3.8–4.4 ms/okno na PCIe x16, 2.9–5.1 vs 8–13 ms na x4 chipsetowym.
- Tryb jest ustalony na cały czas życia procesu. Verify się nie zmienia.
- `GPU_MAX_HW_QUEUES=2` daje szybki tryb w 6/6 startów. 1 jest wolne na x4, 16 wolne zawsze, 4 (domyślne) bimodalne.
- Hipoteza reportera: HIP rozdziela strumienie procesu round-robin po kolejności tworzenia, a przekazanie pracy między kolejkami kosztuje.
- To samo zjawisko opisuje `docs/MULTI_GPU.md` (0.1.44): okno ostatniego etapu trwało 27 zamiast 13 ms, kiedy obok szedł łańcuch draftu, „in most engine starts and for the whole life of that engine”. Stąd przeniesienie draftu na pierwszą kartę (`24d972e5`).

### 2.2 Ścieżka Qwen3.6-35B-A3B: „ta sama rodzina co nasz model, od zera”

`src/qwen35/q36_engine.cu`. Plik `include/strata/core/family_layout.hpp` czyta geometrię z GGUF (`qwen35moe`). Model to GDN + bramkowana atencja GQA (16 Q / 2 KV × 256, NEOX RoPE na 64 wymiarach), blok MTP `blk.<n_layers>` (`nextn.enorm/hnorm/shared_head_norm`, `eh_proj`) oraz MoE 256/top-8.

Autor napisał to jako **osobny driver obok Flash-Next**, „so the Flash-Next identity gate cannot move” (nagłówek pliku, linie 1-3). Przygotowanie (`3a020d58`): wolna referencja `q36ref` z parity per warstwa względem llama.cpp i teacher-forced KL (`tools/qwen35/kl.py`, podłoga = backend CPU llama.cpp).

**Mechanizmy:**
- **Verify bez zapisu stanu, commit przez replay.** `layer(..., verify)`:
  - okno verify czyta stan GDN i historię conv, ale ich nie zapisuje (`q36_engine.cu:592,653`), a wejścia każdego wiersza trafiają do `v_qkv/v_alpha/v_beta[li]`;
  - `commit(n_keep)` (`:1524-1536`) przelicza `k_conv_seq` i rekurencję dla zaakceptowanych wierszy tym samym kernelem.
  - **Nie ma żadnych snapshotów conv ani stanu, a T jest dowolne** (`--mtp 0..7`).
- **Tekst MTP = tekst zwykłego greedy.** Okna verify i zwykły decode używają tych samych kerneli GDN per token (`b5568470`: 10/10 promptów identycznych).
  - `38436f2a`: złączony kernel conv dla jednego tokenu różnił się o 1 ulp od sekwencyjnego (FMA contraction w 4-tapowej sumie). Q8_1 zamieniło to w odwrócony near-tie, więc autor usunął przełącznik, żeby verify i decode zawsze liczyły tymi samymi kernelami.
- **Krok spekulacyjny** (`spec_step`, `:1798-1856`):
  - pierwsze wywołanie MTP liczy razem catch-up wierszy zaakceptowanych w poprzednim oknie i pierwszy draft (`forward_mtp(T0 = fix.size()+1)`);
  - kolejne drafty idą łańcuchem przez graf `gm1`, a potem jest jedno okno verify i `commit(a+1)`;
  - setup ustawia dla tej rodziny `--mtp 2`, a Metal `--spec 2` (`4eca56f4`), podczas gdy Flash-Next ma 3–4. Brak uzasadnienia w kodzie. [INFERENCE: przy MoE każdy dodatkowy wiersz okna dotyka nowych ekspertów, więc szerokość jest droga.]
- **Prefill:**
  - `f29e74c7`: scores i P·V atencji jako strided-batched GEMM FP16 (akumulacja FP32, softmax pisze prawdopodobieństwa FP16), bez FA, plus delta rule z podziałem głowy V na 4 grupy kolumn (16 grup po 8 wierszy). pp4096 na gfx1201: **2557 → 3290 tok/s**.
  - `27f2d167`: małe projekcje F32 (router, GDN alpha/beta, gate shared experta; n_out 1–256, K 2048) szły przez hipBLAS z kafelkami 8×8 i 16×16, co zajmowało ~10% promptu. Własny `k_sgemm_nt` (kafel 16·TM×64, split-K z deterministyczną sumą) daje **3290 → 3455**.
- **Rozgrzewka przy ładowaniu** (`b23869bf`): prompt chunk, krok decode i krok spekulacyjny tworzą code objects, kernele BLAS i grafy. Pierwszy pp4096 rośnie 1770 → 3273 tok/s, a pierwszy prompt 34-tokenowy spada **1032 → 48 ms**.
- **Wynik (R9700, UD-Q4_K_XL, release notes):** 4K prompt 3466 tok/s vs llama.cpp 3054; decode 83 vs 82; **z `--mtp 2` ok. 161 tok/s**.
  - Na zwykłym decode autor jest więc na poziomie llama.cpp, a cały zysk daje MTP.

### 2.3 Unsloth, K-quanty, miarka jakości

- **`tools/quant_quality.py`** (`0d3553fc`):
  - stały zestaw 5×1000 tokenów (`data/quant_quality/v1`);
  - tekst czytany teacher-forced **przez okna decode**, log-prob i top-64 na każdej pozycji;
  - metryki: top-1 zgodność i KL(Q8_0‖quant) na top-64; Q8_0 vs Q8_0 bajtowo identyczne;
  - ścieżka promptu osobno (`prompt`/`pcompare`, pełny KL słownika na 20 promptach).
  - Ten sam plik na innym backendzie (A4000 vs R9700) daje 94.5% top-1 / KL 0.038, czyli to jest podłoga międzybackendowa (`docs/QUANTS.md`).
- **MMQ vs ścieżka FP16 dla K-quantów w prompcie** (`docs/QUANTS.md`):
  - na AMD x1.3–1.7 (eksperci MoE, ścieżka FP16 dekwantyzuje ok. 10 MB na eksperta);
  - KL vs Q8_0: MMQ ma lepszą medianę wszędzie i gorszą średnią na Q4/Q5;
  - Q6_K: MMQ 0.028 vs FP16 0.029, więc domyślne tylko dla UD-Q5/Q6.
- **Dense Q8_0 GEMV, 1 wiersz na blok** (`945fee23`):
  - gfx1201: przy n_in ≤ 4096 i n_out ≥ 4096 wykorzystanie rośnie z 51–80% do 76–86% z 644 GB/s, a 6144→2560 spada (79% → 55–59%), więc tam zostają 2 wiersze;
  - sm_86: n_out ≥ 2048;
  - inne karty bez zmian, „until measured”. UD-Q4 decode +1.0–2.7%.
- **Diagnoza autora dla MoE** (`docs/QUANTS.md`, „Where a decode window goes”): decode na R9700 idzie z prędkością 35–40% granicy przepustowości. Kernele formatów są blisko pasma, a resztę zjadają „the per-window latency of the small kernels and the draft” (draft 5.8 ms z 34.3 ms okna przed `1d21b9cd`).

### 2.4 Reszta (dla nas tylko kontekst)

- **Mac/Metal:** silnik na M4/M5, decode 1.6–1.9× llama.cpp Metal. Negatywy: persistent kernel z barierą (poprawny tylko z fence'ami device-scope, niewiele szybszy), GEMV na matrix units, chunked WY GDN w skalarnym FP32.
- **NVFP4, obrazy (Qwen-Image), P40, Arc:**
  - SYCL: rekurencja GDN promptu z jedną barierą na token zamiast pięciu, kernel 2× szybszy (`65cf5435`);
  - `2a0d2f55`: wariant GEMV 2× szybszy w mikrobenchu, w silniku ±0.5%, więc zostaje opt-in.
- **Arena/RAM:** pin by need, adapt-async (#1904/#1905), `STRATA_PROMPT_DIRECT`.
- **Multi-GPU:** pipeline od 2 etapów, chunk 8192.
- **Serwer:**
  - `env_to_user` (#2175) przenosi blok `<env>` opencode z system promptu do pierwszej wiadomości użytkownika, więc prefix cache trafia także w nowym folderze czy nowym dniu: **11.9 → 1.1 s**;
  - prompt ustępuje krótkiemu żądaniu (#2170);
  - `--prefill-head-alias` (#2191): VRAM głowicy wyjściowej trzyma bufory promptu na 8 GB, chunk 512 → 2048 i prefill 292 → 667 tok/s.
- **Nowe PR-y/issue warte odnotowania:**
  - **#2299**: `STRATA_GDN_CHUNKED` (WY w chunkach po 16 na WMMA) na gfx11. Na gfx1151 rekurencja jest 1.44–1.6× szybsza, a **cały prompt tylko +1.4–2.1%**; KL 0.004–0.007, opt-in.
  - **#2318**: KV `q2k` (K 2-bit per kanał + V 4-bit), −22% bajtów vs q4_0, KL 2.5–5× większy. Obserwacja: przy równych bajtach bity powinny iść na V.
  - **#2227**: pełna głowica draftu daje akceptację +4 pp i prędkość −2.1%; top-2 był celem 0/14 razy (to już znaliśmy).

---

## 3. Rozumowanie autora: co nowego w metodzie

1. **„Opóźnienie okna” jako osobna kampania.** Gałąź `f-latency` (komentarze `engine-latency`, 10 miejsc w `src`) liczy węzły grafu i czas między grafami, a nie przepustowość kerneli. Najpierw powstały narzędzia (DRAFT_TIMING, MTP_PROFILE, COMMIT_TIMING), dopiero potem zmiany. Każdy commit podaje zmierzony µs.
2. **Kolejki sprzętowe ROCm traktuje jak zasób.** Priorytet służy jako sposób na wymuszenie osobnej kolejki. Gdzie praca jest niezależna (commit vs draft), dostaje osobną kolejkę. Gdzie jedna strona czeka w spinie na drugą (flaga vs kopia), osobna kolejka jest warunkiem poprawności.
3. **Default tylko tam, gdzie zmierzono.** HIP_PRIO jest domyślne na gfx12 i opt-in gdzie indziej, Q8_0 rows1 tylko na gfx1201 i sm_86, HC_Q8 tylko na gfx12 i dla UD na NVIDIA. „Other cards keep two rows until measured” (`945fee23`).
4. **Izolacja nowego kodu od bramki tożsamości.** Qwen3.6 dostał osobny driver i bibliotekę, release był zbudowany z kodem Mac i bez niego, a obiekty silnika są bajtowo identyczne. Formaty kosztują coś tylko wtedy, gdy są używane: K-quant MMQ to osobna biblioteka, bo code objects zjadały sloty ekspertów (`465cd61d`).
5. **Tekst MTP = tekst greedy jako bramka poprawności** (q36). Lepiej zrezygnować z szybszego złączonego kernela niż dopuścić 1 ulp różnicy między verify a decode (`38436f2a`).
6. **Replay zamiast snapshotów to dla autora stały wzorzec.** CUDA (`352cad8f`, wcześniej), Metal (`1f4b6b36`, fold na początku następnego okna) i q36 (`commit()`) robią to samo. Wszędzie T jest dowolne i nie ma limitu slotów.
7. **Mikrobench nadal nie decyduje.** SYCL `2a0d2f55`: 2× w mikrobenchu i ±0.5% w silniku, więc opt-in. Q8_0 rows1 wybrano z `q8_gemv_bench` na kształtach silnika i potwierdzono 5/5 parami w silniku.
8. **Głębokość draftu dobiera do kosztu szerokości.** Dla MoE Qwen3.6 i dla Maca domyślnie są 2 drafty, dla Flash-Next 3–4 z DraftPolicy. [INFERENCE]

---

## 4. Ranking transferu na nasz setup

| # | Pomysł (źródło) | Jak u nas | Oczekiwany zysk (nasze liczby) | Wysiłek | Ryzyko | Który nasz punkt zmienia |
|---|---|---|---|---|---|---|
| **1** | **Historia conv bez snapshotów: gather ostatnich `d_conv−1` wierszy z `[hist \| x_0..x_{n_keep−1}]`, `n_keep` z pamięci urządzenia** (`6f3e3810` `gdn_conv_commit_layers_kernel`; q36 `commit()`; Metal `1f4b6b36`) | U nas klif ma konkretną przyczynę w kodzie: `SSM_CONV_FUSED_MAX_SNAPSHOTS 8` (`~/wt/k4/ggml/src/ggml-cuda/ssm-conv.cuh:6`); fuzja A5 zapisuje snapshot conv na każdy możliwy `n_keep`, a powyżej 8 graf wraca do concat + K węzłów cpy. Wariant pasujący do S4: trzymać wiersze x (przed conv) okna w buforze oczekujących i w następnym verify złożyć historię w fuzji SSM_CONV z `n_keep` z lag info (`53be90b39` już ma `[n_seqs,4]`). Wariant prostszy: jeden kernel gather po accept dla wszystkich 48 warstw (`blockIdx.y` = warstwa) | T ≤ 8: ≈0…0.1 ms (snapshoty conv to 4% bajtów, `NOTES` S4). **T 9–16: znika klif**, czyli serwer może używać K4 (9 kol. 32.1 ms, 16 kol. 35.0 ms w llama-bench) i T2. Bufor x: 48 × 16 × 10240 × 4 B ≈ 31 MB. Nie ma już slotów `n_rs_seq` dla conv ani hostowego checkpointu ≈151 MB przy dłuższych draftach (roadmap) | średni (ta sama hydraulika co S4) | niski: gather jest bitowo dokładny | **8-token cliff** wprost; warunek dla **T2** i pełnego użycia **K4** |
| **2** | **Kolejki sprzętowe ROCm: `GPU_MAX_HW_QUEUES` i priorytet strumienia** (#2305, `1d21b9cd`, `728097fb`, `docs/MULTI_GPU.md` 0.1.44) | Mamy co najmniej 2 strumienie: kontekst celu i kontekst MTP, każdy z własnym strumieniem backendu [INFERENCE ze struktury ggml-cuda]. Test bez kodu: `GPU_MAX_HW_QUEUES` = 1/2/4 × ≥3 restarty serwera na ramię, porównać `draft ms` i ms/krok. Jeśli rozkład jest bimodalny, ustawić env w `run-llm.sh`, ewentualnie `hipStreamCreateWithPriority` dla strumienia MTP | 0…1 ms/krok (0…3.5%) [INFERENCE: u nas nie ma grafu commitu, na który draft by czekał, bo S4 przeniosło replay do verify, więc efekt (b) z §2.1 raczej odpada; zostaje koszt przekazania między kolejkami] | bardzo niski | brak | Wpływa też na **metodę A/B**: jeśli tryb jest ustalony na życie procesu, porównanie z jednego restartu na ramię może wylosować tryb. Ważne dla **T1** (GPU-side accept): spin na flagę z innego strumienia może się zakleszczyć, jeśli oba strumienie trafią do jednej kolejki (`728097fb`) |
| **3** | **Profil etapów draftu wewnątrz grafu i rozbicie host/GPU** (`009dc6c1`, `65514542`) | Znaczniki GPU między etapami grafu MTP (embd+norm, eh_proj, atencja, FFN, głowica 64k, argmax) dla kroków 1..n; osobno host: staging, launch, wait | 0 bezpośrednio; daje koszt draftu jako funkcję głębokości, czyli brakujący składnik dla T2 | niski | brak | **T2**: koszt(T) = verify(T) z tabeli K4 + Σ draft(k) z profilu |
| **4** | **Catch-up i pierwszy draft w jednym wywołaniu MTP** (q36 `spec_step`, `forward_mtp(T0 = fix+1)`) | `NOTES`: catch-up nie złączony, bo „chowa się za próbkowaniem CPU, 0.2 ms”. Po K3 sample+accept spadło z 645 do 140 µs, więc catch-up [INFERENCE] może już się nie chować. Najpierw zmierzyć narzędziem z pkt 3 | 0.2–0.3 ms → +0.7–1% | niski–średni | drafty się zmieniają, verify zostaje bezstratne | **T2/S3** (mniej przebiegów MTP na krok) |
| **5** | **Q8_0 GEMV: wiersze na blok mierzone na kształcie** (`945fee23`, `5ef9f4c8`) | W UD-Q4_K_XL `ssm_out` jest **Q8_0 6144→5120** w 48 warstwach, ok. 1.6 GB/krok (odczyt z gguf-py). U Straty 6144→2560 jest szybsze z 2 wierszami, a n_in ≤ 4096 z 1 wierszem (gfx1201). Sprawdzić w tabeli rocprof K1 % pasma dla `ssm_out` przy 5 kolumnach; jeśli < 80%, dodać wariant rows-per-block do przeszukiwania K1 | jeśli 70 → 80% pasma: ≈ −0.3 ms → +1% [INFERENCE] | niski (już mamy uprząż K1) | brak, bitowo | **K1** (dopięcie) |
| **6** | **Rozgrzewka wszystkich grafów przy starcie** (`b23869bf`: pierwszy krótki prompt 1032 → 48 ms) | llama-server robi warmup jednego forwardu; grafy HIP dla verify T = 2..16, łańcucha MTP i chunków prefill powstają przy pierwszym użyciu [INFERENCE, nie mierzyliśmy] | tylko pierwsze żądanie po starcie: TTFT o ~0.1–1 s [INFERENCE] | niski | brak | UX, `run-llm.sh` |
| **7** | **K5: dane z q36 i #2299** | (a) Skinny GEMM w prefill: nasze `ssm_alpha/beta` to Q8_0 48×5120, więc idą przez MMQ, nie SGEMM [INFERENCE], i `k_sgemm_nt` nie przenosi się 1:1. Zostaje kontrola w rocprof, czy macierze o 48 wierszach (×96 wywołań na chunk) nie zajmują nieproporcjonalnie dużo. (b) Atencja promptu: q36 robi GEMM FP16 z materializowanymi scores, bo kontekst jest krótki; dla naszych 94k plan WMMA FA (K5) zostaje lepszy [INFERENCE]. (c) #2299: chunked GDN na WMMA gfx11 daje tylko +1.4–2.1% promptu, co potwierdza nasze „sufit ≈ 2%”. (d) MMQ Q6_K: KL MMQ ≈ FP16 (0.028 vs 0.029) jest argumentem za int8 MMQ Q6_K zamiast F16 WMMA, bo #2020 stoi | (a) 0…3% pp [INFERENCE]; (b–d) zmieniają priorytety, nie liczby | (a) niski diagnostycznie | — | **K5**: GDN chunked zostaje nisko; Q6_K przez MMQ (iu8) przed F16 |
| **8** | **Miarka jakości jako narzędzie** (`tools/quant_quality.py`) | Stały zestaw ok. 5k tokenów, teacher-forced **przez ścieżkę verify z MTP**, top-1 i KL vs referencja (Q8_0 naszego 27B albo BF16), plus podłoga A/A i międzybackendowa | 0 t/s; umożliwia decyzje dla S2 (typ draftu), self-distillation i ewentualnych zmian bitów | niski–średni | — | **MTP self-distillation**, S2, każda zmiana niebitowa |
| 9 | **Persistent kernel z barierą** (#2226: teraz −6.6% / −4.4% ms/okno, 10/10 par, gfx1030) | Krótkie łańcuchy (norma → kwantyzacja → mały GEMV); Metal: niewiele szybszy (`4e5ea96d`) | [INFERENCE] 0–2%, po K2 mniej łańcuchów | wysoki | zakleszczenie przy złym occupancy | K2 (później), bez zmian w kolejności |
| 10 | **`env_to_user`** (#2175) | Tylko jeśli używamy opencode lub innego klienta z blokiem `<env>` w system prompt: przenieść go do pierwszej wiadomości użytkownika (proxy/szablon) | TTFT nowej sesji 11.9 → 1.1 s (u nich); t/s bez zmian | niski | — | cache promptu |
| 11 | **Tekst MTP = tekst greedy jako bramka** (`38436f2a`, `b5568470`) | U nas tekst MTP różni się od zwykłego greedy już na bazie (`fusion/greedy/base.mtp.txt` vs `base.plain.txt`), bo verify T=5 liczy innymi kernelami niż T=1. To nie jest regresja, tylko inny standard | 0 t/s; determinizm | wysoki (kernele T=1 i T>1 bitowo równe) | — | nie planować; zanotować w metodzie |

**Łączny potencjał [INFERENCE, bez nakładania się]:**
- Pozycje 2+4+5 dają ≈ 0.5–1.6 ms/krok, czyli +2–5% na krótkim kontekście (102 → ok. 104–107 t/s).
- Pozycja 1 nie przyspiesza czatu przy n=4. Odblokowuje T2 i szerokie okna (K4) na kodzie i przy odtwarzaniu treści (roadmap A9: +10–40% dla kodu/agentów), co jest największą dźwignią z tej delty.

---

## 5. Wpływ na nasz plan

- **8-token cliff:**
  - Strata potwierdza kierunek: zamiast snapshotów conv, gather lub replay z `n_keep` z urządzenia, jednym launchem na wszystkie warstwy.
  - Mamy już lag info i bufor oczekujących z S4, więc najtańsza droga to rozszerzyć lag na historię conv: złożyć `[hist | wiersze oczekujące[0..n_keep)]` w fuzji SSM_CONV następnego verify.
  - Limit `SSM_CONV_FUSED_MAX_SNAPSHOTS` wtedy znika. Zostaje `SSM_CONV_FUSED_MAX_TOKENS 16`.
- **T2 (głębokość wyceniana kosztem):**
  - Delta nie przynosi nowej polityki. Daje natomiast potrzebne narzędzie (profil etapów draftu, pkt 3) i obserwację, że autor dla MoE wybiera 2 drafty.
  - U nas dodatkowe kolumny są tanie (dense; K4), więc oczekiwana głębokość jest większa.
  - Fakty z #2227 nadal obowiązują: drzewa bez sensu (top-2 0/14), pełna głowica −2.1%.
  - Kolejność: pkt 1 → pkt 3 → tabela koszt(T) → T2.
- **K5 prefill:**
  - GDN chunked zostaje nisko (#2299: +1.4–2.1%).
  - Q6_K przez MMQ iu8 jest uzasadniony jakościowo (KL MMQ ≈ FP16). #2020 (F16 w LDS) nadal nie jest w upstream.
  - Dochodzi szybka diagnostyka macierzy o 48 wierszach w prefill (pkt 7a).
  - Plan GQA FA na WMMA bez zmian.
- **T1 (accept po stronie GPU):** projektować w obrębie jednego strumienia albo z wymuszoną osobną kolejką (priorytet). Spin GPU na flagę ustawianą z innego strumienia w tej samej kolejce sprzętowej to zakleszczenie (`728097fb`).
- **S3 (okno atencji MTP), T3 (MTP prompt jako K/V only), self-distillation:** brak nowych danych. q36 przepuszcza prompt przez pełny blok MTP (`q36_engine.cu:1778-1785`), więc Strata T3 nie robi. Dla self-distillation przyda się miarka z pkt 8.
- **Metoda A/B:** przy każdym A/B na ROCm robić ≥2–3 restarty serwera na ramię (#2305, `docs/MULTI_GPU.md`: tryb ustalony na życie procesu). Dotyczy to szczególnie wyników „szum” z przeszłości (env HIP, `DEBUG_HIP_GRAPH_BATCH_SIZE`).

## 6. Nie przenosić (z delty)

- **HC_Q8, route tail skip, NVFP4, arena/pin by need/adapt-async, multi-GPU, Metal, SYCL, P40, obrazy:** nie mamy hyper-connections, MoE, offloadu ani tego sprzętu.
- **Commit batch (`6f3e3810`) jako taki:** u nas commit stanu GDN siedzi już w następnym verify (S4). Przenosi się tylko część conv (pkt 1).
- **Atencja promptu przez GEMM z materializowanymi scores (q36):** przy 94k gorsza od FA [INFERENCE].
- **KV `q2k` (#2318):** −22% bajtów KV przy KL 2.5–5× q4_0. Pamięć nas nie ogranicza, a jakość tak.
- **Q8_0 rows1 jako default:** reguła jest per arch (gfx1201/sm_86); na gfx1100 tylko jako wariant do przeszukania w K1 (pkt 5).
- **Fuzje z #2231:** PR zamknięty, nic nowego. Nasze K2 już to pokrywa.

## 7. Kolejność (najtańsze dowody najpierw)

1. Pkt 2: A/B `GPU_MAX_HW_QUEUES` 1/2/4 × 3 restarty, bez kodu.
2. Pkt 3 i pkt 5 jako pomiary: profil etapów draftu i catch-upu po K3 (decyduje o pkt 4) oraz % pasma `ssm_out` Q8_0 w rocprof.
3. Pkt 1: lag historii conv, potem tabela koszt(T) i T2.
4. Pkt 4 i 6, potem K5 z korektami z pkt 7, a pkt 8 przed self-distillation.
