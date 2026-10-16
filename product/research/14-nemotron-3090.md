# 14 — Nemotron 3.5 Bolt 74B-A9B (IQ2_XXS) na RTX 3090, 2026-10-16

Instancja Vast 56246385 (Polska, rel 0.996, $0.225/h z dyskiem 90 GB, transfer ~$0.13/TB). Działała 12:39–~15:00 UTC i została zniszczona: `show instances` pokazuje 0 instancji.
- Preferowana oferta 47626122 (Ryzen 9 7900) zniknęła między wyszukiwaniem a wynajmem (`no_such_ask`). Wziąłem następną 3090 z nowoczesnym CPU.
- Surowe wyniki: `~/qwen-opt/cloud/results/nemotron-3090-20261016/` (`scorecard.json`, `scorecard.md`, `sweep/`, `probe/`, `lb/`, `greedy/`, `nsys/`, `opt/`, `tbo/`, `hw/`, `logs/`).
- Skrypty: `~/qwen-opt/cloud/runs/nemotron-3090/` (`inst/*.sh` na instancji, `summ.py`, `nsys_tok.py`, `scorecard-n.py`).
- Kod: gałąź `nemotron-3090` w `~/wt/nemotron-opt` (od `cuda-3090-opt` 3da7a02ec).

Kampania została skrócona z powodu limitu zapytań agenta: zamiast planowanych 10 h instancja działała ~2.3 h. Czego nie zrobiłem, opisuję w sekcji 10.

## 1. Sprzęt

| | |
|---|---|
| GPU | RTX 3090 24 GB, VBIOS 94.02.26.80.8C, sm_86, sterownik 580.173.02 |
| PCIe | gen4 x16 (karta), oferta: x8 (12.8 GB/s); tylko ładowanie modelu, offload CPU nie jest potrzebny |
| limit mocy | 350 W (max 385) |
| CPU | AMD Threadripper PRO 5945WX (Zen 3), kontener: kwota CFS 4.6 CPU (cgroup v1 `cpu.cfs_quota_us=460800`), `nproc`=24, więc `-t 4 -tb 4` |
| RAM | limit cgroup 54 GB |
| toolchain | nvcc 12.8.93, gcc 13.3, obraz `nvidia/cuda:12.8.1-devel-ubuntu24.04` |

Build forka na 4.6 CPU szedł ~4 rekordy/min. Zbudowałem go lokalnie (Zen 3 5700X, ten sam nvcc 12.8.93 i gcc 13.3, `-march=native` = znver3, RPATH `$ORIGIN`) i wysłałem binaria; upstream zbudował się na instancji.
- **Lekcja:** sondy pojemności uruchomione w trakcie buildu dały 19 t/s zamiast 87, bo kwota CPU była zajęta przez 24 procesy nvcc. Te liczby odrzuciłem.

## 2. Model i licencja

- Plik: `NVIDIA-Nemotron-3.5-Bolt-74B-A9B-IQ2_XXS.gguf`, 22 018 326 528 B, sha256 `91d63363…99af75`, zgodny.
- Drafter: `dflash-…-NVFP4.gguf`, 998 242 560 B, sha256 `080e1ea4…010194`, zgodny.
- Rewizja HF: `f56d370e`.
- Licencja: **OpenMDW-1.1** (`license: other`, https://openmdw.ai/license/1-1/). Karta modelu: „ready for commercial or non-commercial use”.
- Arch `nemotron_h_moe`, 88 warstw:
  - **40 warstw Mamba-2**: d_inner 8192, state 128, 8 grup, 128 głów; `ssm_in`/`ssm_out` w **NVFP4** ze skalą per tensor;
  - **40 warstw LatentMoE**: latent 1024, top-9, liczba ekspertów **różna w warstwach: 240/304/368/432/496**, aktywacja relu², sigmoid + bias + norm + skala 5.0, shared expert 5376; eksperci w IQ2_XXS;
  - **8 warstw attention**: GQA 32/2, head 128, Q8_0;
  - słownik 131072; głowa wyjściowa i embedding w Q8_0;
  - brak głowicy MTP.
- Bajty na token przy decode (szacunek z nagłówka): ~4.8 GB wag + ~0.34 GB stanu SSM (odczyt i zapis), w tym NVFP4 2.47 GB. Przy zmierzonych 805 GB/s daje to sufit ~150 t/s.
- llama.cpp v0.7.0 obsługuje i model, i DFlash/LiLiCorr (`draft-dflash`, block 8, 5 warstw SWA 1024). NVFP4 na Ampere działa przez dp4a z tablicą; nie ma tu natywnego FP4.

## 3. Co mieści się w 24 GB (pełny offload, `-fit off -ngl 999`, `probe/gen.jsonl`)

| konfiguracja | max ctx który ruszył | VRAM |
|---|---|---|
| bez draftera, KV f16 | **262144** (pełne 256K) | 23.4 GB |
| bez draftera, KV q8_0 / q4_0 | 262144 | 22.6 / 22.1 GB |
| + DFlash, KV q4_0 | 131072 (262144 OOM) | 24.0 GB |
| + DFlash, KV q8_0 | 98304 (131072 OOM) | 24.1 GB |
| + DFlash, KV f16 | < 65536 (65536 OOM w trakcie pracy) | — |

Wniosek: model z drafterem mieści się w 24 GB. Pełne 256K kontekstu jest dostępne tylko bez draftera.

**Pułapka upstream `-fit on` z DFlash:** fit nie umie zmierzyć draftera („failed to measure the memory of the extra model, fitting without it”).
- Wynik: 67 t/s przy `-c 65536` i niższym VRAM, wobec 95 t/s przy pełnym offloadzie.
- Dlatego A1 używa `-fit off -ngl 999`. To ta sama klasa błędu co lekcja `lekcja-fit-mtp-16gb`.
- A0 (`-m` bez flag): fit wybiera 4 sloty × 104704 ctx, KV f16, bez spekulacji, 22.0 GB.

## 4. Spekulacja (sonda, 1 seed, upstream / fork)

| typ | t/s | ms/krok | tok/krok |
|---|---|---|---|
| bez | 87.1 / 90.6 | 11.5 / 11.0 | 1.00 |
| ngram-mod | 86.4 / 90.3 | — | 1.00 (brak trafień) |
| DFlash n_max 3 | 132.6 / 135.5 | 23.0 / 22.1 | 3.07 / 3.01 |
| **DFlash n_max 5** | **137.6** / 135.3 | 27.9 / 27.1 | 3.85 / 3.67 |
| DFlash n_max 7 (przepis vLLM) | 125.2 / 122.9 | 33.3 / 32.2 | 4.19 / 3.96 |

- DFlash z drafterem NVFP4 działa na Ampere i daje ~1.5× decode.
- Koszt weryfikacji rośnie ~2.5 ms na każdy dodatkowy token draftu. Przyczyny: dodatkowe experty MoE (każdy token czyta 9 innych) i snapshoty stanu Mamby (`ssm_scan` przy weryfikacji trwa 36 µs wobec 9 µs przy jednym tokenie).
- Optimum wychodzi przy n_max 5, a nie 7 jak w przepisie vLLM.

## 5. Tabele A0 / A1 / A2 / tuned

Metoda: spec_sweep, 6 promptów × 3 seedy, T=1, 400 tokenów, kolejność ABBA (A0 A1n A1 A2n A2 A2s, potem odwrotnie), świeży serwer na rundę. Wspólne flagi: `-c 65536`, KV q8_0, `-t 4`, DFlash n_max 5. Wariant „tuned” to osobne ABBA A2/T, w którym A2 dało 129.9.

| tryb | decode t/s (zakres) | ms/krok | tok/krok | TTFT 2k | pp512 / pp4096 | tg128 | VRAM |
|---|---|---|---|---|---|---|---|
| A0 (upstream, `-m`) | 87.2 (87–88) | 11.5 | 1.00 | 1865 ms | 1602 / 1566 | 87.3 | 22.0 GB |
| A1n (upstream, bez draftera) | 86.8 (86–88) | 11.5 | 1.00 | 1849 ms | 1605 / 1562 | 86.8 | 21.0 GB |
| **A1** (upstream + DFlash) | **131.4** (107–141) | 28.6 | 3.76 | 2332 ms | j.w. | — | 23.1 GB |
| A2n (fork, bez draftera) | 90.6 (90–91) | 11.0 | 1.00 | 1832 ms | 1605 / 1563 | 90.6 | 21.0 GB |
| A2 (fork + DFlash) | 129.0 (114–150) | 27.1 | 3.51 | 2318 ms | j.w. | — | 23.1 GB |
| A2-safe | 127.3 (113–147) | 27.5 | 3.51 | 2325 ms | 1606 / 1563 | 89.2 | 23.1 GB |
| **tuned** (fork + nowe łatki) | **141.1** (112–155) | 27.1 | 3.82 | 2332 ms | = A2 | 96.7* | 23.1 GB |

\* tg128 z osobnego ABBA llama-bench (fork 91.1 → 96.7).

- **Fork bez draftera:** +4.4% (86.8 → 90.6), ms/token 11.5 → 11.0.
- **Fork z DFlash:** krok jest krótszy (28.6 → 27.1 ms), ale akceptacja spada (tok/krok 3.76 → 3.51), więc wynik to 131.4 → 129.0 (−1.8%).
- **Tuned:** ten sam ms/krok co A2, ale tok/krok 3.82, czyli akceptacja wróciła do poziomu upstream. To skutek zmiany numeryki w topk-moe (sekcja 8). Mechanizmu nie wyjaśniłem `[INFERENCE]`: niezmierzone, potrzebne więcej seedów i KLD.

## 6. Długi kontekst (llama-bench tg32 na głębokości, 1 runda, `opt/longctx/`)

| | d0 | 32k | 64k |
|---|---|---|---|
| upstream KV q8_0 | 84.6 | 74.6 | 65.8 (−22%) |
| tuned KV q8_0 | 91.4 | 79.9 | 69.4 (−24%) |
| upstream KV **f16** | 85.2 | 84.5 | **82.5 (−3%)** |

Uwagi:
- Tylko 8 warstw ma KV, więc spadek z kontekstem jest mały, ale **wyłącznie przy KV f16**.
- Ścieżka FA vec z KV q8_0 na CUDA kosztuje ~0.2 ms na warstwę przy 32k. To ~10× gorsza przepustowość na bajt niż f16, prawdopodobnie przez GQA 16:1 bez współdzielenia K/V `[INFERENCE]`.
- 128k: niezmierzone (etap przerwany).

## 7. Profil nsys (llama-bench tg64, `--cuda-graph-trace=node`, `nsys/`, `nsys_tok.py`)

| | kernele/token | GPU busy | rozpiętość | przerwy |
|---|---|---|---|---|
| upstream | 1822 | 11.12 ms | 12.93 ms | 1.81 ms |
| fork | 1559 | 10.77 ms | 12.47 ms | 1.70 ms |
| opt1 (fork + TOPK_MOE_NP2) | **1279** | 10.13 ms | 11.48 ms | 1.35 ms |

MMVQ to 70–74% czasu GPU. Przepustowość per kernel (fork):
- NVFP4 `ssm_in` (42.8 MB): 51 µs, **833 GB/s**.
- NVFP4 `ssm_out`: 663 GB/s.
- Głowa Q8_0 (570 MB): 644 µs, 885 GB/s.
- **IQ2_XXS** (shared + routed experts): **320–400 GB/s**, razem 2.68 ms/token. To największy rezerwuar.
- Q8_0 `latent_up` (K=1024): 474 GB/s.

Pozostałe kernele:
- Upstream argsort i łańcuch bramki MoE: 0.95 ms/token, bo upstreamowa fuzja topk-moe nie obsługuje tych liczb ekspertów.
- `ssm_scan`: 9 µs/warstwę, czyli ~890 GB/s.

W trybie DFlash (server):
- `mul_mat_vec_q_moe` (IQ2 eksperci, 6 kolumn) to 20% GPU;
- `ssm_scan` to 5.6%;
- drafter (BF16 GEMM, cutlass) ~5%.

## 8. Przełączniki i nowe łatki (commit na `nemotron-3090`)

1. **`GGML_CUDA_TOPK_MOE_NP2`** (domyślnie on). Fuzja topk-moe dla 240/304/368/432/496 ekspertów: ceil(n/32) slotów na lane, ogon maskowany do −INF. Testy test-backend-ops dodane.
   - Zastępuje 9 kerneli na warstwę MoE: sigmoid, add, argsort, get_rows, sum, clamp, div, scale.
   - Efekt: −280 kerneli/token, rozpiętość −0.99 ms/token.
   - **Zmienia bity:** `=0` przywraca md5 forka.
2. **`GGML_CUDA_MMVQ_N1_IQ2`** (domyślnie on). IQ2_XXS dołącza do 2 wierszy na blok na sm_80–87. Bitowo neutralne (md5 identyczne z `=0`).
3. **`GGML_CUDA_IQ2_LUT`** (opt-in). Kopia `iq2xxs_grid` w pamięci współdzielonej. Bitowo neutralne, ale **wolniejsze**: tg128 96.7 → 94.4 (−2.4%). **Wynik negatywny**; gather z L1 nie był wąskim gardłem w tej formie.

Pomiar łączny (llama-bench ABBA ×2, `opt/lb/`):

| | fork | + NP2 + N1_IQ2 + LUT | + NP2 + N1_IQ2 (domyślne) |
|---|---|---|---|
| tg128 | 91.1 | 94.4 | **96.7 (+6.1%)** |
| pp6 | 263 | 266 | 269 |

Server ABBA z DFlash: A2 129.9 → tuned 141.1. Zysk pochodzi z tok/krok, ms/krok się nie zmienił.

**Przełączniki forka:** pełne A/B per przełącznik nie zostało wykonane (etap `switch` przerwany). A2 vs A2-safe:
- DFlash: 129.0 vs 127.3 (+1.3%);
- tg128: 90.6 vs 89.2.

Większość fuzji forka (GDN, shortconv, gate+up) nie dotyczy tej architektury.

## 9. Poprawność

- test-backend-ops (fork): **19573/19573 OK**.
- Testy opt2 (MUL_MAT / MUL_MAT_ID / TOPK_MOE): niewykonane, etap przerwany. Nowe testy TOPK_MOE są w commicie.
- Greedy md5 (świeże serwery, 2 prompty × 400 tok, thinking off). Wszystkie wyniki deterministyczne (×2):

| tryb | upstream | fork | fork-safe | opt2 | opt2 bez TOPK | werdykt |
|---|---|---|---|---|---|---|
| plain | 94b0e175 | 8610e165 | 8610e165 | d3905509 | 8610e165 | fork: DIFF-BUILD; opt2: tylko przez TOPK_MOE_NP2 |
| DFlash | c9fe478d | 93e4dfe0 | 93e4dfe0 | e7d2197f | — | j.w. |

- KLD: **niezmierzone** (etap przerwany przez limit). Skrypt `inst/kld.sh` jest gotowy: wikitext-2, ctx 512, 24 chunki.

## 10. Czego nie zrobiłem (limit zapytań agenta)

- KLD fork/opt2 względem upstreamu.
- A/B per przełącznik forka.
- Długi kontekst 128k i ABBA forka.
- test-backend-ops opt2.
- Ollama.
- Sweep n_max na zoptymalizowanym buildzie.
- Kandydaci na kernel, niezaimplementowani:
  - IQ2_XXS MMVQ (wciąż 320–400 GB/s);
  - FA vec dla KV q8_0 przy GQA 16:1;
  - replay zamiast snapshotów stanu Mamby przy weryfikacji (jak `LLAMA_GDN_REPLAY` dla GDN);
  - szybszy `topk_moe_cuda` (8.4 µs/wywołanie, 1 warp).

## 11. Koszt

| pozycja | koszt |
|---|---|
| instancja ~2.3 h × $0.225 | ≈ $0.52 |
| transfer (~24 GB w dół, ~0.2 GB w górę) | < $0.01 |
| **razem** | **≈ $0.52** (limit $3.50) |

Kredyt spadł o $0.39 do momentu zniszczenia; reszta to rozliczenie z opóźnieniem.

## 12. Rekomendacje

- Domyślnie dla 3090:

  ```
  -fit off -ngl 999 -fa on -c 65536 -ctk q8_0 -ctv q8_0 -np 1 -t <kwota CPU>
  --spec-type draft-dflash -md dflash-…-NVFP4.gguf --spec-draft-n-max 5
  ```

  - **Nigdy `-fit on` z DFlash.**
  - Dla długich rozmów bez draftera: KV f16 i ctx do 256K; przy 64k f16 zachowuje 97% prędkości, q8_0 tylko 78%.
  - Z drafterem i ctx ≤ 48K warto spróbować f16 (niezmierzone).
- Łatki: `TOPK_MOE_NP2` i `N1_IQ2` do manifestu z predykatem „nemotron_h_moe / IQ2_XXS”. `IQ2_LUT` zostaje opt-in. Przed produktem trzeba zmierzyć KLD dla `TOPK_MOE_NP2`.
- Hasło na landing (RTX 3090, ta sama waga GGUF):
  - **87 → 141 t/s (×1.62)** względem domyślnego llama.cpp (`-m`);
  - **131 → 141 (×1.07)** względem najlepszych flag upstream.
  - Zastrzeżenie: zysk tuned vs A2 pochodzi z akceptacji draftu po zmianie numeryki topk-moe (2 rundy ABBA, 3 seedy). Twardy zysk kodu bez draftera to +6–11% (A1n 86.8 → tg128 opt 96.7).

## Karta wyniku dla aplikacji

Definicje:
- **decode**: mediana 2 rund ABBA × 18 żądań; w nawiasie zakres per prompt.
- **500 słów**: EN 1.17 tok/słowo, PL 2.69 tok/słowo (współczynnik tokenizera Qwena, dla tego modelu niezmierzony).
- **TTFT**: prompt ~2.1k tokenów.

### Nemotron 3.5 Bolt 74B-A9B IQ2_XXS (RTX 3090)

| | Typowa aplikacja (A0) | Najlepsze flagi (A1, DFlash n5) | Nasz silnik (tuned) |
|---|---|---|---|
| decode t/s | **87.2** (87–88) | **131.4** (107–141) | **141.1** (112–155) |
| prefill pp512 / pp4096 | 1602 / 1566 | 1605 / 1562 | 1605 / 1563 |
| TTFT ~2k tok | 1.87 s | 2.33 s | 2.33 s |
| 500 słów EN | 6.7 s | 4.5 s | 4.1 s |
| 500 słów PL | 15.4 s | 10.2 s | 9.5 s |
| słowa/s EN / PL | 74.5 / 32.4 | 112.3 / 48.8 | 120.6 / 52.5 |
| VRAM | 22.0 GB (ctx 4×104k, f16) | 23.1 GB (ctx 64k q8_0 + drafter) | 23.1 GB |
| md5 | ref. (inne flagi) | referencja | różni się od A1 (łatki build-only forka + TOPK_MOE_NP2); deterministyczny; KLD niezmierzone |

Speedupy:
- A0 → nasz: **×1.62**.
- A1 → nasz: **×1.07**.
- Rozkład A0 → nasz: flagi (DFlash) ×1.51, łatki ×1.07.
- Bez draftera: A1n 86.8 → A2n 90.6 (×1.04) w serwerze; tg128 87 → 96.7 (×1.11) w llama-bench.

## 13. KLD: `TOPK_MOE_NP2` vs upstream (uzupełnienie, 2026-10-16, raport 16d)

Pomiar domyka lukę z §9 i §12 („przed produktem trzeba zmierzyć KLD dla `TOPK_MOE_NP2`”). Metoda jak w raporcie 09 (3060).

- **Sprzęt:** inna instancja RTX 3090 (Vast 56264196: i5-14400, kwota cgroup 15.36 CPU, sterownik 595.84, limit mocy 280 W, PCIe gen1 x16 w spoczynku).
- **Plik:** ten sam `NVIDIA-Nemotron-3.5-Bolt-74B-A9B-IQ2_XXS.gguf`, sha256 `91d63363…99af75`.
- **Buildy:** upstream v0.7.0 (`620d222`) oraz `nemotron-3090` @ `e46d34e0e`, CUDA 12.8, sm_86.
- **Wywołanie:** `llama-perplexity -f wikitext-2-raw/wiki.test.raw -c 512 --chunks 24 -fit off -ngl 999 -fa on -t 15 -b 512`.
- **Baza:** logity upstreamu przy `-ub 512`.
- **Szum:** ten sam upstream przy `-ub 256` względem tej bazy.

| przebieg | Mean KLD | 99.9% KLD | Max KLD | Same top p | PPL(Q) |
|---|---|---|---|---|---|
| upstream ub 512, powtórka (determinizm) | 0.000000 | 0.000050 | 0.000053 | 100.000% | 5.9218 |
| **upstream ub 256 (szum batcha)** | **0.002254 ± 0.000069** | 0.0552 | 0.171 | 98.088 ± 0.175% | 5.9249 |
| **fork `nemotron-3090` (domyślnie NP2=1, N1_IQ2=1)** | **0.002135 ± 0.000066** | 0.0589 | 0.159 | 98.105 ± 0.174% | 5.9248 |
| fork z `GGML_CUDA_TOPK_MOE_NP2=0` | 0.000000 | 0.000050 | 0.000053 | 100.000% | 5.9218 |
| fork, ub 256 | 0.002266 ± 0.000082 | 0.0550 | 0.335 | 98.056 ± 0.177% | 5.9242 |

Wnioski:
- **Bramka KLD: PASS.** Fuzja `TOPK_MOE_NP2` daje KLD 0.00214 wobec upstreamu, czyli poziom jego własnego szumu przy zmianie ubatch (0.00225). Top-1 zgadza się w 98.1% przypadków, tak samo jak przy szumie batcha (98.09%). PPL 5.9248 vs 5.9218 (różnica 0.05%, w granicach ±0.19).
- **Jedynym źródłem różnicy numerycznej forka w ścieżce prefill jest `TOPK_MOE_NP2`.** Z `NP2=0` logity forka są bit w bit równe upstreamowi: KLD 0, 100% top p, identyczne PPL 5.921825.
  - Max KLD 5.3e-5 w powtórce samego upstreamu pochodzi z zapisu logitów bazy, nie z niedeterminizmu.
  - Tłumaczy to też §9: md5 „opt2 bez TOPK” = md5 forka.
- **Zastrzeżenie:** `llama-perplexity` liczy batch 512, więc nie pokrywa ścieżki dekodu n=1 (`MMVQ_N1_IQ2`). Ta ścieżka jest bitowo neutralna według greedy md5 z §8.
- Wcześniejsza hipoteza z §5 (`[INFERENCE]`: akceptacja draftu wraca przez zmianę numeryki topk) jest zgodna z tym wynikiem. Fuzja przesuwa wybór ekspertów przy prawie remisach (max KLD 0.16 przy medianie 0.00067), ale średnio nie pogarsza modelu.
- Rekomendacja §12 zmienia się następująco: `TOPK_MOE_NP2` może wejść do manifestu z predykatem „nemotron_h_moe / IQ2_XXS” jako **łatka niebitowa z KLD na poziomie szumu**. Bez obietnicy „bit w bit jak upstream”.

Surowe dane: `~/qwen-opt/cloud/results/magnitude-vs-3090-20261016/kld/` (`summary.txt`, pełne logi per przebieg). Skrypt: `~/qwen-opt/cloud/runs/magnitude-3090/inst/kld-nemotron.sh`. Koszt: ok. 2 min GPU w ramach instancji raportu 16d.
