# 68c — długi kontekst na hybrydzie GDN: bezstratne przyspieszenia decode, prefillu i cache agenta

Data: 2026-11-07. Autor: podagent R68c_LongCtxGdn. Praca tylko na CPU: bez GPU, bez pobierania modeli, bez buildów. Klon kodu: `~/src/research68/llama-cpp-rdna-boosts` (`--depth 1`, HEAD `3cb0e6e`, 2026-11-07, 151 MB). Wiki nieedytowane.

Reguła 2026-11-05: rekomendacje tylko bezstratne (bitowo albo KLD = 0; zmiany samego draftu są dozwolone). Stratne pomysły są wyłącznie w §4.

Oznaczenia: **NOWE** = brak w wiki i raportach 63/66; **znane (X)** = jest w notatce X. `[SZACUNEK]` = arytmetyka z cytowanych pomiarów, `[INFERENCE]` = wniosek niezmierzony. Liczby cudzych autorów są podpisane jako ich liczby, nie nasze pomiary.

## TL;DR

1. **Spadek decode przy długim kontekście to w ~85–90% atencja celu w `kvq`. Klifu przy 128k nie ma.** Nachylenie wynosi ~53–59 µs na 1k tokenów kontekstu na krok (§1.1). Model nachylenia plus niższa akceptacja (0,56 wobec 0,66) odtwarza 95,8 t/s w paśmie 128–160k i 78,7 t/s przy 255k z dokładnością ~2–3%. Weryfikacja W=5 leży na grzbiecie rooflinu (~114 flop/B wobec ~112 flop/B karty przy 2200 MHz). Dlatego ONCE daje tylko −7% (617 → 572 µs na warstwę przy 196k): kernel ogranicza wydawanie WMMA/VALU, nie pasmo.
2. **Prefill przy ≥128k to w 40–55% FA, a nie MMQ.** Przy wypełnianiu 255k FA zajmuje `[SZACUNEK]` ~54% czasu, w turze agenta 4k tokenów przy 103k ~50%. Raport 24v odłożył FA prefillu, bo przy ≤32k miała tylko 2–24% udziału. Przy naszym pain poincie (465 t/s przy 255k) FA to główna dźwignia. Mamy dwie bitowe drogi:
   - przegląd bitowo neutralnych parametrów kernela, które 24v wypisał, ale nie przejrzał;
   - **V (i K) zapisywane od razu w układzie fragmentu WMMA w obowiązkowej konwersji q4_0→f16** (NOWE). Usuwa transpozycję V przez LDS, którą 24v wskazał jako „jedyną większą rezerwę”.
3. **Pochodna maska KQ (llama-cpp-rdna-boosts, blok 05, „V3”)**: widoczność liczona w kernelu z pozycji komórek zamiast maski `n_kv × n_tokens` budowanej na hoście.
   - Przy 255k i ub 512 znika 261 MB zapisu na CPU plus upload na każdy ubatch, a przy 262k −256 MiB VRAM i −256 MiB pinned.
   - U autorów KLD 0.000000, tekst bajt w bajt.
   - Dla decode realizuje znaną poz. 9 z 66 (~0,5 ms na krok przy 199k).
4. **Agent: bufory wpisów `--cache-ram` alokujemy na stronach 4 KiB** (`std::vector::resize`, `server-task.cpp:1778`). Nasz log XTX: 169 ms na 354 MiB plus 530 ms na kopię 1120 MiB checkpointów, czyli ~2,1 GB/s.
   - `MADV_HUGEPAGE` (rdna-boosts r173: 470 → 125 ms na alokację 3,4 GiB) i recykling buforów to zmiana bitowa (tylko alokacja). `[SZACUNEK]` −2…5 s na każde przełączenie wątku przy wpisach 7–14 GB. NOWE.
5. Tania bitowa poprawka prefillu: konwersja q4_0→f16 biegnie z pasmem ~220–390 GB/s (24v). Szybszy kernel K+V w jednym launchu daje ~−2% czasu wypełniania 255k i ~−90 ms na turę przy 255k `[SZACUNEK]`. Najlepiej połączyć to z punktem 2.
6. GDN (chunked prefill, ReplaySSM, SpecLA, DeltaLog) nie ruszy naszych liczb przy długim kontekście. Koszt GDN nie zależy od kontekstu (3–4% prefillu, 24v). Chunked GDN na WMMA nie jest bitowy, a ReplaySSM przy batch 1 jest wolniejszy. Mamy już `rs_lag` (66b).

## 1. Gdzie idzie czas przy długim kontekście (nasze pomiary + arytmetyka)

### 1.1 Decode

- Krótki kontekst: spec_sweep T=1 to 26,9 ms/krok przy 118,3 t/s, czyli ~3,18 tokenu na krok (zadanie).
- 255k: 78,7 t/s ([[2026-11-06-ctx-262k-fit]], `wiki/eksperymenty/2026-11-06-ctx-262k-fit.md`). Przy tej samej liczbie tokenów na krok daje to ~40,4 ms/krok, czyli **+13,5 ms na 255k ≈ 53 µs/1k** `[SZACUNEK]`.
- Składniki z mikrobenchmarków `kvq` (`~/qwen-opt/kvq-once/run-1107-2315/kperf.txt:5-8`; d98304 / d196608, µs na warstwę):

| składnik | nachylenie | na krok przy 255k |
|---|---|---|
| FA celu, nb5 (2 kafle): 318,8 → 616,9 µs | 3,03 µs/1k × 16 warstw = **48,5 µs/1k** | ~12,4 ms |
| FA draftu, nb1: 171,6 → 326,7 µs | 1,58 µs/1k × ~5 wywołań = ~7,9 µs/1k | ~2,0 ms |
| maska KQ na hoście (66e §3.3: 0,25 ms/graf przy 199k) | ~2,5 µs/1k | ~0,6 ms |
| **suma** | **~59 µs/1k** | **~15 ms** |

- Pasmo 128–160k w prawdziwej sesji: 95,8 t/s przy akceptacji 0,56, wobec 123,1 t/s przy 0,66 w paśmie 96–128k (`wiki/eksperymenty/2026-11-06-sesja-uzytkownika-final-mode.md`). Model: krok(144k) ≈ 25 + 144 × 0,0566 ≈ 33,2 ms; tokeny/krok ≈ 1 + 4 × 0,56 = 3,24, więc ~97,6 t/s (zmierzone 95,8). Dla 112k: 31,3 ms i 3,64 tokenu, czyli ~116 t/s (zmierzone 123,1). **Wniosek `[INFERENCE]`:** „klif” to akceptacja plus liniowe nachylenie FA. W `kperf` FA skaluje się liniowo (1,5–2,1 µs/1k na kafel przy 32k–196k), bez progu MALL ani podziałów.
- **Weryfikacja na grzbiecie rooflinu.**
  - nb5 to 30 wierszy Q dopełnionych do 32. Na każdy bajt KV q4_0 (0,5625 B/element) przypada 32 × 2 flop na K i tyle samo na V, czyli ~114 flop/B.
  - XTX przy 2200 MHz: 96 CU × 512 flop/takt × 2,2 GHz ≈ 108 TFLOPS f16 WMMA na 960 GB/s, czyli ~112 flop/B.
  - Podłogi przy 196k: WMMA 2,58e10 flop / 108 TFLOPS ≈ 239 µs, pasmo 226 MB / 960 GB/s ≈ 236 µs. Zmierzone: 617 µs (ONCE 572, `kperf.txt:8,16`), czyli ~45 TFLOPS i ~400 GB/s naraz.
  - Wspólny odczyt K (ONCE) usunął tylko 45 µs, więc drugi kafel kosztuje głównie wydawanie WMMA/VALU (dequant K w obu grupach, perm, softmax), a nie pasmo.
  - Sufit idealnego kernela ~300 µs/warstwę, czyli −4,3 ms/krok przy 196k i ~−5,6 ms przy 255k (≈ +12…16% decode) `[SZACUNEK]`. To obszar XtxKvOnce/R68a (§3, poz. 8).
- Szerokość weryfikacji przy długim kontekście: koszt rośnie z liczbą kafli `ceil(6·W/16)` (24h:13).
  - W=1–2: 1 kafel, W=3–5: 2 kafle, W=6–8: 3 kafle, W=11–16: 5–6 kafli.
  - Krok z ogonem lookup W16 przy 255k to `[SZACUNEK]` ~+20–25 ms wobec MTP4 (4 dodatkowe kafle × 16 warstw × ~0,35–0,4 ms). Przy długim kontekście n=4 (W=5) jest więc naturalnym optimum, a DRAFT_N=5 (W=6, 3 kafle) kosztuje +~5 ms na krok.

### 1.2 Prefill

- Profil 24v (`24v-prefill-fa.md:19`): pp512@d32768, ostatni ubatch = 547 ms, z czego FA `<256,256,32,2>` 131 ms (8,2 ms/warstwę), konwersja KV→f16 1,3%, GDN 3,0%, MMQ 63%.
- Model na ubatch 512 przy głębokości d: ~416 ms (część stała) + 131 ms × d/32k (FA) + ~7 ms × d/32k (konwersja) `[SZACUNEK]`.

| przypadek | FA | konwersja | reszta | udział FA |
|---|---|---|---|---|
| wypełnienie 255k (498 ubatchy, średnio d ≈ 127k) | ~254 s | ~14 s | ~207 s | **~54%** |
| wypełnienie 128k (250 ubatchy) | ~64 s | ~3,5 s | ~104 s | ~38% |
| tura agenta 4,2k tokenów przy 103k | ~0,42 s/ubatch | ~22 ms | ~0,42 s | ~50% |

- Kontrola modelu:
  - przewiduje ~471 s na 255k przy zegarach z 24v (sprzed eco), a zmierzone jest 548 s przy eco 2200 (×1,16);
  - tura 4242 tokenów przy 103k: model 0,84 s/ubatch × 1,16 ≈ 0,97 s, zmierzone ~1,02 s (498,6 t/s, `2026-11-06-sesja-uzytkownika-final-mode.md`).
- **Konwersja q4_0→f16 (staging) jest wolna.**
  - Przy 32k: 0,4 s na ~88 GB ruchu (16 warstw × K+V × d × 1024 × (0,5625 odczyt + 2 zapis)), czyli **~220 GB/s**. Ostatni ubatch: ~390 GB/s.
  - Kod: `fattn-common.cuh:1089-1143` (osobne `to_fp16` dla K i V), wybór MMA dla prefillu: `fattn.cu:701-705`.
  - Bufor f16 to `ggml_nelements(K)·2 B` (`fattn-common.cuh:68-80`), czyli ~1 GiB przy 262k.
- **Maska KQ w prefillu.** Szybka ścieżka kopiuje wiersz bazowy `n_kv` do każdego z 512 wierszy (`llama-kv-cache.cpp:1861-1866`). Przy 255k to 261 MB zapisu na CPU i tyle samo H2D na ubatch, a potem odczyt przez FA każdej z 16 warstw.

### 1.3 Cache agenta (nasz log)

- Sesja użytkownika 06.11 (`~/qwen-opt/logs/server-2026-11-06_175345.log`, mój parser `/tmp/gaps68.py`):
  - 145 tur, prompt eval łącznie 177,5 s;
  - 133 tury < 2000 tokenów zajęły 98 s (mediana 196 tokenów);
  - przerwa między końcem generacji a następnym żądaniem: p10 53 ms, **p50 158 ms**, p90 2,07 s (22 > 1 s).
- Każda tura zaczyna się od `f_keep` ≈ 0,52–0,66 (np. `n_tokens = 5968` → `f_keep = 0.524`). Wygenerowana odpowiedź (z myśleniem) nie trafia więc do następnego promptu, a widoczna część odpowiedzi jest prefillowana od nowa w kolejnej turze.
- Zapis wpisu cache na XTX (`~/qwen-opt/latency/logs/l45-budget.server.log:166,193`):
  - `alloc 698.5 ms (buf 168.9, ckpt copy 529.6)` dla 345,8 MiB stanu i 1120 MiB checkpointów;
  - `buf 122.9, ckpt copy 208.3` dla 252 + 436 MiB;
  - czyli **~2,1 GB/s, limit stron 4 KiB**.

## 2. Ustalenia per źródło

### 2.1 stew675/llama-cpp-rdna-boosts (r234, `3cb0e6e`, 2026-11-07)

W ZRODLA ostatnio sprawdzane w Q:v2 (10-12) jako „adaptacyjne MTP — pomysł”. Od tego czasu repo urosło do 16 bloków dla RDNA3/4. Liczby poniżej są liczbami autorów, w większości na gfx1201 (R9700).

- **Pochodna maska KQ (blok 05, V3)**: „per-token bounds + one per-cell position replace the packed mask; the FA kernel computes visibility on the fly” (`patches/README.md:455-462`), w MMA i tile, tylko dla `n_tokens > 8`.
  - Rezerwa przy ctx 204800 i ub 2048: −799 MiB GPU i −799 MiB host. Przy ub 512: −199 MiB i −199 MiB, czyli dokładnie `n_kv × n_tps × 2 B` (`archive/work/arch-independent-memory/V3-DERIVED-KQ-MASK-PLAN.md:337-358`).
  - Tekst bajt w bajt, `gate-prefill-logits` KLD **0.000000** (`benchmarks/2026-10-29-derived-kq-multiseq.md`, §4).
  - Prędkość: 4B pp20480 −1,1%. 27B na 3 GPU w bramce MTP: prompt 1123,6 → 1229,2 t/s (+9,4%), „because the host fill disappeared”. MoE z `-ncmoe`: 27–31 s → 9,7–10,1 s.
- **Natywne czytanie KV q4_0/q8_0 w FA (V4/V5)**: zysk tylko w decode (u nas już jest `kvq`). Dla prefillu autorzy zostawili staging: „reading the quantized cache once per *output* tile is slower (worth +1.5 / +2.7 / +5.1 % pp at 8k/16k/32k on gfx1201)” (`patches/README.md:1991-1993`). Wniosek dla nas: nie wycinać konwersji, tylko ją przyspieszyć i przerobić (§3 poz. 2–3).
- **Staging FA dzielony na kawałki KV** (`GGML_CUDA_FA_STAGE_CHUNK`): arena 64 MiB zamiast 1 GiB przy 262144, ale KLD 0,001 przy 2 kawałkach, czyli stratne (§4).
- **q8_0 fetch-ahead (r98)**: surowe bajty następnej partii K/V pobierane do rejestrów, konwersja do LDS dopiero w chwili użycia. Bariery porządkują tylko LDS, bo `__syncthreads()` czeka też na globalne odczyty i opróżniłoby prefetch (`patches/README.md:524-530`). Wzorzec dla pogłębienia prefetchu w `kvq`: dziś `kvq` pobiera tylko jedną partię naprzód (`fattn-kvq.cu:388,433,492`).
- **Huge pages dla wpisów cache promptu (r173, PR #248 commit 2)**: `reserve + madvise(MADV_HUGEPAGE) + resize`, alokacja z zerowaniem 3,4 GiB 470 → 125 ms. Zapis nowego wpisu 100k: 828 → 497 ms. Bufor z recyklingu: bez zmian (292 ms), bo „spares keep their pages”. Zmiana tylko alokacji, więc logity bez zmian (`benchmarks/2026-10-29-prompt-cache-hugepage.md`).
- **Checkpoint spekulacji celu w VRAM (r184, PR #254)**: +1,6…4,3% tylko przy częstych checkpointach (n-gram, edycje). U nas GDN replay (S4) nie robi checkpointu na krok, więc to nie dotyczy [INFERENCE].
- **Chunked GDN bf16/WMMA dla gfx11 (blok 03)**: numeryka bf16, czyli stratne (§4).
- **Okno KV draftu MTP domyślnie włączone (blok 15, auto ≥ 32768)**: tekst celu nienaruszony, tylko akceptacja (`benchmarks/2026-11-01-spec-draft-window-264.md`). U nas to S3, wynik negatywny (`qwen-opt/NOTES.md:327`).
- **Adaptacyjna głębokość MTP (blok 02)**: znane (T2, kontroler szerokości).

### 2.2 llama.cpp upstream

- **#24561 „chunked MFMA prefill kernel for GATED_DELTA_NET (CDNA)”** (06-13 → zamknięty 07-10). Kernel izolowany na MI250X 1,56–2,44×, e2e Qwen3.6-27B przy ub 512 +2…6%. Różnica do kernela per-token ~1,2e-4. Dla MTP (`keep_rs`) kernel był omijany (komentarz am17an). Zamknięty z braku opiekuna. Dla nas: stratne, bo GEMM f16; GDN to 3–4% prefillu.
- **#29846 „fuse KV cache dequantization into fattn-mma-f16”** (2026-10-02, CUDA): qwen35 27B q4_0 przy ub 512 pp1024@d32768 ×1,02 (3090). Zysk jest tylko przy małym ub; przy ub 512 staging nie jest wąskim gardłem. Zgodne z rdna-boosts.
- **#22880 „HIP: RDNA3 mma FA, faster AMD transpose”** (scalony 2026-05-14): jest w topce (`3e037f313`). „For RDNA3/4 I was not able to get better performance than the tile kernel for head sizes > 128”, więc D=256 zostało słabo dostrojone u źródła.
- **#29918 `--cache-reuse-hybrid`** (draft, 2026-10-03): przesuwanie KV i rozwidlanie stanu GDN po edycji w środku promptu. KL od 0,008 do 0,819 zależnie od poziomu, czyli stratne (§4).

### 2.3 vLLM / SGLang / AMD

- **vLLM #52585 (2026-08-17) + PR #52684**: na 7900 XTX Triton `unified_attention` z BLOCK_M=64 zamiast 16 daje wall 1,11–1,46× przy prefillu 8k, a atencja Qwen2.5-7B (D=128) idzie z 43 do **93 TFLOPS**. GEMM fp16 rocBLAS na tej karcie to ~107 TFLOPS. Liczby autora przy zegarach stock. Dowód, że FA prefillu na gfx1100 może przekroczyć nasze ~50 TFLOPS (24v), choć dla D=128.
- **chelokot/flash-attention-rdna3** (Triton, gfx1100): forward 33–42 TFLOPS (D=128), autor szacuje sufit czystego GEMM WMMA na ~70 TFLOPS. To przeczy rocBLAS ~107 z #52585 [INFERENCE: ich GEMM referencyjny jest słabszy]. Split-K decode osiąga do 865 GB/s (~90% pasma).
- **vLLM RFC #61761 (DFlash2 na MI355X, 10-15 → 11-03)**: odroczony stan GDN w weryfikacji (#61434/#64325, „write one full state plus the raw per-token inputs, and replay”) +5,6…10,6% przy c=16/64. U nas to GDN replay S4 (znane, `wiki/kernele/gdn-replay.md`). Split-K atencji przy B=1 i długim kontekście (#61760, pkt 3 planu) mamy w `kvq`.
- **SGLang RFC #28511 (ReplaySSM, 06-17)**: „slightly slower at batch 1”, a rekonstrukcja na rdzeniach tensorowych nie jest bitowa („bit-exactness and the speedup are mutually exclusive by construction”). Część spec decode (#27658: kompaktowe `(k, Δv, decay)`, replay w fp32) = nasz `rs_lag` (66b §3.8).
- **FlashQLA (QwenLM, v0.1.3, 2026-09)**: TileLang, ścieżki SM90/SM100/SM120, bez AMD.

### 2.4 Prace (arXiv / ACL)

- **ReplaySSM** (arXiv 2610.13778, 2026-10-09; blog Dao AI Lab 06-15): zysk w przepustowości przy dużym batchu. Przy batch 1 nic nie daje (wyżej).
- **SuffixReplay** (arXiv 2609.33477, 2026-09-27): przybliża stan GDN przez replay sufiksu, 91,4–100% jakości. Stratne (§4).
- **MASW „Strong Drafts Need Compact Memories”** (EMNLP Findings 2026, s. 6481–6494): draft z ujściami + oknem 128 + wyuczonymi slotami pamięci. Cel ma pełne KV, więc metoda jest bezstratna dla wyjścia.
  - Przy 32k Llama 70B: opóźnienie draftu 41 → 14 ms, tokeny na iterację 4,05 → 3,65.
  - Samo okno (SWA) w ich tabeli ciągnie akceptację w dół (0,37–0,63×), zgodnie z naszym S3.
  - U nas draft FA przy 255k to ~2 ms/krok (~5%), więc sufit ~+5%, a wymaga treningu adaptera głowicy MTP. Niski priorytet.
- **SpecLA** (arXiv 2607.16673), **KVBuffer** (arXiv 2605.19049), **DeltaLog** (2026-08): odroczona materializacja stanu i weryfikacja drzew dla modeli liniowych. To ten sam wzorzec co S4/`rs_lag`, drzewa są w 66 poz. 14. Nic nowego dla batch 1.

### 2.5 Społeczność

- **vahpetr, fork s1 (llama.cpp Discussion #30282, 10-10/16/21, Vulkan Strix Halo)**: „a KQ mask built from cell metadata instead of a context x batch plane” (ten sam pomysł co V3). v64: zmiana układu LDS kernela FA prefillu (31 → 21 KiB na WG, 4 → 6 WG na WGP), FA **−16,5%**, prefill 32k +7,2%, 72k +8,2%, „shader math unchanged”, 32 tokeny greedy + top-8 logprobów identyczne. To dowód, że bitowo neutralne strojenie zajętości/LDS FA prefillu na RDNA3.5 daje dwucyfrowy zysk kernela (liczby autora, Vulkan, nie HIP).
- Reddit/llamaperf (XTX, Qwen3.8-27B): brak publicznych liczb ≥128k lepszych od naszych 78,7 t/s / 465 t/s. Wątek r/LocalLLM „106.9 tok/s code / 120.7 tok/s agentic” na XTX (Windows) jest bez długiego kontekstu.

## 3. Testowalne pomysły bezstratne

| # | pomysł | NOWE / znane | oczekiwany zysk u nas + dlaczego | wysiłek | dokładny test na naszym boxie | kill | ryzyko |
|---|---|---|---|---|---|---|---|
| 1 | **Przegląd bitowo neutralnych parametrów FA prefillu D=256 przy dużej głębokości**: `nbatch_K2`, `nbatch_V2`, `nbatch_combine`, `Q_in_reg`, `nstages`, occupancy, układ LDS (24v:64 wypisuje je jako neutralne bitowo) | NOWE jako cel (24v wypisał parametry przy ≤32k, ale ich nie przejrzał); wzorzec: vahpetr v64 FA −16,5% | FA to ~54% wypełnienia 255k i ~50% tury przy 103k (§1.2). FA −10…20% daje wypełnienie 255k **+5…11%** (465 → 490–515 t/s), turę przy 103k +5…10% `[SZACUNEK]` | 1 d | `test-backend-ops perf -o FLASH_ATTN_EXT` hs 256, nb 512, KV q4_0, kv 131072/262144 dla każdej konfiguracji (wzór `prefillfa-tools/pfa_gate.sh`); zwycięzca → `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -ub 512 -p 512 -d 131072,250000 -r 3` ABBA (PM4 off); bitowość: md5 `/completion` z `n_probs` przy prompcie ≥ kilka ubatchy (metoda 24v) + `greedy.sh` c4708318/6f14e814 | kernel FA < −5% przy d=131k albo jakakolwiek różnica md5 | konfiguracja musi zostać neutralna bitowo; occupancy zmieniająca `max_blocks_per_sm` zmienia podział stream-K (24v:64), takie warianty odpadają |
| 2 | **V (i K) od razu w układzie fragmentu WMMA, zapisywane przez konwersję q4_0→f16** (staging i tak powstaje co ubatch); kernel MMA czyta V bez transpozycji `ds_read_b32` + perm | NOWE (24v:55 nazywa „przepisanie ładowania V, 2192 operacji LDS na iterację” jedyną większą rezerwą) | FA −15…30% `[SZACUNEK]`, czyli wypełnienie 255k **+8…16%**, tura przy 103k +7…14%. Kolejność działań arytmetycznych bez zmian, więc bitowe z konstrukcji | 3–4 d | jak poz. 1 + `fa_hash` (wzór `~/qwen-opt/kvq-once/fa_hash.cpp`) stary vs nowy dla nb 512, kv 4k/98k/196k, potem `long_ctx_bench` wypełnienie 128k i 255k ABBA | FA < −8% przy d=131k albo jakikolwiek hash ≠ | sprzężenie układu z podziałem stream-K i fixupem; kernel musi czytać K/V z bufora staging także dla `kvq`=off |
| 3 | **Szybsza konwersja staging q4_0→f16**: K i V w jednym launchu, zapisy 16 B, cel ~800 GB/s (dziś ~220–390 GB/s, §1.2) | NOWE | konwersja to ~3% wypełnienia 255k. Zysk: **−2% czasu wypełniania 255k** (~11 s), **~−90 ms na turę przy 255k** (2 ubatche na turę z podziałem n−4−ub/n−4). Te same wartości f16, więc bitowe | 0,5 d | `rocprofv3 --kernel-trace` kerneli `to_fp16`/`dequantize_block` przy pp512@d196608: µs i GB/s przed i po; `llama-bench -p 512 -d 196608` ABBA; md5 jak poz. 1 | < +1% pp512@d196608 | znikome; połączyć z poz. 2 (ten sam kernel) |
| 4 | **Pochodna maska KQ** (rdna-boosts V3): pozycje komórek + przedział `[lo, hi]` tokenu, widoczność w kernelu MMA (prefill) i w `kvq` (decode), bez maski `n_kv × n_tokens` z hosta | częściowo znane (66 poz. 9: „maska poza ścieżką krytyczną” dla decode); NOWE: gotowa implementacja RDNA z bramką KLD 0, strona prefillu i VRAM | decode przy 199–255k **+0,5…1,5%** (66e: ~0,5 ms/krok), wypełnienie 255k **+0…3%** (261 MB zapisu CPU + H2D na ubatch na końcu wypełnienia), **−256 MiB VRAM i −256 MiB pinned** przy 262k/ub 512 `[SZACUNEK]`. U autorów 27B: prompt +9,4% (3 GPU), 4B −1,1% | 2–3 d (port `load_mask` w MMA + porównanie pozycji w `kvq` + flaga w grafie) | `LLAMA_HOSTGAP_TRACE=1` przy 199k (czas `graph→inputs`) + `long_ctx_bench` 199k/255k ABBA; md5 `greedy.sh` + md5 długiego promptu z `n_probs`; wyrocznia jak `LLAMA_KQ_MASK_DERIVED_VERIFY` (host porównuje maskę spakowaną z pochodną komórka po komórce) | decode < +0,5% przy 199k i wypełnienie < +1% przy 255k → zostaje tylko jako zysk VRAM | multi-seq/M-RoPE (obraz) muszą wrócić do maski spakowanej; PM4 replay musi przechwytywać nowe wejście |
| 5 | **`MADV_HUGEPAGE` + recykling buforów wpisów `--cache-ram`** (alokacja bez zerowania 4 KiB; pula zwolnionych buforów do limitu) | NOWE (brak w wiki; wzorzec rdna-boosts r173) | zapis nowego wpisu ~2,1 GB/s → ~6–8 GB/s (u autorów alokacja 3,4 GiB 470 → 125 ms); przy przełączeniu wątku 75–120k (wpisy 7–14 GB wg 63b) **−2…5 s na przełączenie** `[SZACUNEK]`. Bitowe: zmienia się tylko alokacja | 0,5 d | `LLAMA_SERVER_AP_TIMING=1`, replay 2 przeplatanych wątków 75–120k (uprząż planu #6): `ap save alloc`/`ckpt copy` przed i po; `grep AnonHugePages /proc/<pid>/smaps_rollup`; `dmesg` i liczniki ewikcji KFD (THP + SVM: `wiki/rocm/hip-kopie-stronicowane-zostawiaja-svm.md`, mamy `HSA_USE_SVM=0`) | alokacja < −30% albo jakikolwiek błąd PM4/KFD | kompakcja THP (`defrag=madvise`) zabiera CPU; fragmentacja przy 40 GB `--cache-ram` |
| 6 | **Spekulatywny prefill następnej tury w przerwie**: po końcu generacji serwer renderuje swoją odpowiedź tak, jak wróci od klienta (natywny ChatML, bez reasoning, `<|im_end|>`) i prefilluje ją w tle, z przerwaniem na granicy ubatcha, gdy przyjdzie żądanie | NOWE | log 06.11: `f_keep` 0,52–0,66 na turę, czyli widoczna odpowiedź jest zawsze prefillowana od nowa. 133 małe tury = 98 s, mediana przerwy 158 ms (p90 2,07 s). Ukryje `[SZACUNEK]` ~10–25% czasu małych tur (~10–25 s/h); więcej przy ≥128k, gdzie re-prefill jest 2× droższy | 2–3 d (serwer) | replay sesji (`agent_bench`) z TTFT na turę; trafienie przewidzianego prefiksu (LCP) w %; md5 „trafienie vs zimny start” (bramka planu #6) | trafienie prefiksu < 50% albo TTFT < −5% | renderowanie klienta (omp) może różnić się bajtowo (strata tylko pracy GPU); granice ubatchy zmieniają kolejność sum w FA, więc bramka md5 jak dla checkpointów |
| 7 | **Szerokość lookup zależna od kontekstu**: W16 → W8/W5 przy ≥128k, gdy akceptacja ogona jest niska | znane (`wiki/metody/kontroler-szerokosci-draftu.md`, `LLAMA_SPEC_LOOKUP_ADAPT=1`, „naprawiać przy kopii ≥ 64k”) | krok W16 przy 255k to ~+20–25 ms (6 kafli zamiast 2, §1.1). Na czacie ogon akceptowany w 18% (29/162) to strata przy długim kontekście; zysk zależy od udziału ogonów ≥128k (do zmierzenia) | 0,5 d (konfiguracja + pomiar) | `LLAMA_SPEC_LOOKUP_LOG` z prawdziwej sesji: udział kroków `tail` przy n_past ≥ 128k; potem `ADAPT=1` vs stałe W16 na replayu agenta 128–200k, ABBA | ogony < 2% kroków przy ≥128k | znane ograniczenie: ocena warunkowa za optymistyczna (notatka kontrolera) |
| 8 | **`kvq` W=5 na grzbiecie rooflinu**: K dekwantowane raz na parę (dziś w ONCE obie grupy), głębszy prefetch K/V do rejestrów z barierami tylko na LDS (wzorzec rdna-boosts fetch-ahead) | znane jako obszar (XtxKvOnce, R68a); NOWE: rachunek pokazujący, że nb5 jest ograniczone wydawaniem WMMA/VALU (45 TFLOPS + 400 GB/s naraz; ONCE tylko −7%) | sufit ~300 µs/warstwę przy 196k (dziś 572), czyli **+12…16% decode przy 196–255k** `[SZACUNEK]` | 3–5 d | `kperf` jak `kvq-once/job.sh` (d98k/196k, nb1/nb5) + `fa_hash` + `long_ctx_bench` 199k | nb5@196k < −10% wobec ONCE | rejestry/occupancy (2 bloki na CU); przekazać XtxKvOnce, nie dublować |
| 9 | **Polityka wyrzucania `--cache-ram` ważona kosztem przeliczenia** (Marconi: koszt aN + bN² na bajt; dziś LRU `pop_front`, `server-task.cpp:1763-1768`) | NOWE | przy 2+ długich wątkach chroni wpisy ≥100k (przeliczenie 100–550 s) przed krótkimi; zysk tylko przy presji pamięci (40 GB) `[INFERENCE]` | 0,5–1 d | replay 3 wątków (2 długie + krótkie zapytania) z `LLAMA_SERVER_PREFIX_LOG`, liczba pełnych prefilli ≥20k | 0 uniknięte pełne prefille w replayu | interakcja z „wspólnym początkiem” (plan #7) |
| 10 | **Skompresowana pamięć draftu (MASW)**: głowica MTP czyta ujścia + okno + wyuczone sloty zamiast pełnego KV draftu | NOWE (bezstratne dla wyjścia) | draft FA przy 255k ~2 ms/krok (~5%), więc sufit **+3…5% przy 255k**, minus spadek akceptacji (u nich 4,05 → 3,65 tok/iter) | wysoki (trening adaptera) | najpierw symulacja offline: akceptacja MTP z oknem 128 + sloty na logach; potem spec_sweep + `long_ctx_bench` 199k/255k | akceptacja −5% przy 128k | S3 (samo okno) już negatywne |

**Kolejność:**
- Poz. 3 i 5 to po 0,5 d, obie bitowe.
- Poz. 1: 1 d, jedna sesja GPU i rozstrzyga o 2.
- Poz. 2 robić według wyniku 1.
- Poz. 4 można prowadzić równolegle (kod CPU + krótki test).
- Poz. 6–7 wymagają danych z sesji.
- Poz. 8 przekazać XtxKvOnce po werdykcie ONCE.

## 4. Zaparkowane (stratne, bez rankingu)

| pomysł | źródło | dlaczego odpada | liczby (informacyjnie) |
|---|---|---|---|
| Chunked GDN prefill na WMMA/MFMA (bf16/f16) | rdna-boosts blok 03; llama.cpp #24561 | GEMM w bf16/f16, różnica ~1,2e-4 wobec per-token | MI250X e2e +2…6% przy ub 512; u nas GDN 3–4% prefillu |
| Staging FA dzielony na kawałki KV | rdna-boosts r159 (`GGML_CUDA_FA_STAGE_CHUNK`) | scalanie online-softmax: KLD 0,001 (2 kawałki) / 0,0053 (4) | arena 1 GiB → 64 MiB przy 262144; −4,1% przy 64k |
| ReplaySSM z rekonstrukcją na rdzeniach tensorowych | SGLang #28511, arXiv 2610.13778 | nie bitowe (TF32/bf16); przy batch 1 wolniejsze | +2,3% TPOT tylko przy 128 równoległych |
| SuffixReplay (przybliżony stan GDN z sufiksu) | arXiv 2609.33477 | przybliża stan liniowy | 91,4–100% jakości, TTFT −15…70% |
| `--cache-reuse-hybrid` (przesuwanie KV po edycji w środku) | llama.cpp #29918 | KL 0,008 (poziom 1) … 0,819 (poziom 4) | przeliczane 55% → 0–34% promptu |
| QSA / rzadka atencja, KV 3-bit, FLy, KVA, REAP, zmiana kwantu | 63/66 | decyzja 2026-11-05 | — |

## 5. Źródła (z datami)

Zewnętrzne:
- stew675/llama-cpp-rdna-boosts, HEAD `3cb0e6e` (2026-11-07, release r234): `patches/README.md:388-650` (blok 05), `:1890-2028` (async input, staging arena); `GREEDY-PURITY.md:588-600` (§34); `benchmarks/2026-10-29-derived-kq-multiseq.md`; `benchmarks/2026-10-29-prompt-cache-hugepage.md`; `benchmarks/2026-11-01-spec-draft-window-264.md`; `archive/work/arch-independent-memory/V3-DERIVED-KQ-MASK-PLAN.md:337-375`. https://github.com/stew675/llama-cpp-rdna-boosts
- llama.cpp PR #24561 (2026-06-13 → 07-10): https://github.com/ggml-org/llama.cpp/pull/24561
- llama.cpp PR #29846 (2026-10-02): https://github.com/ggml-org/llama.cpp/pull/29846
- llama.cpp PR #22880 (scalony 2026-05-14): https://github.com/ggml-org/llama.cpp/pull/22880
- llama.cpp PR #29918 (draft, 2026-10-03): https://github.com/ggml-org/llama.cpp/pull/29918
- llama.cpp Discussion #30282 (vahpetr, 2026-10-10/16/21): https://github.com/ggml-org/llama.cpp/discussions/30282
- vLLM issue #52585 (2026-08-17) i PR #52684: https://github.com/vllm-project/vllm/issues/52585
- vLLM RFC #61761 (2026-10-15 → 11-03): https://github.com/vllm-project/vllm/issues/61761
- SGLang RFC #28511 (2026-06-17 → 07-21): https://github.com/sgl-project/sglang/issues/28511
- ReplaySSM, arXiv 2610.13778 (2026-10-09): https://arxiv.org/abs/2610.13778; blog: https://dao-lab.ai/blog/2026/replayssm/
- SuffixReplay, arXiv 2609.33477 (2026-09-27): https://arxiv.org/abs/2609.33477
- MASW, EMNLP Findings 2026 (24–29.10.2026): https://aclanthology.org/2026.findings-emnlp.306.pdf
- SpecLA, arXiv 2607.16673 (2026-07-18): https://arxiv.org/abs/2607.16673
- KVBuffer, arXiv 2605.19049 (2026-05-18): https://arxiv.org/abs/2605.19049
- chelokot/flash-attention-rdna3 (README odczytany 2026-11-07): https://github.com/chelokot/flash-attention-rdna3
- QwenLM/FlashQLA v0.1.3 (2026-09): https://github.com/QwenLM/FlashQLA

Nasze:
- `~/qwen-opt/kvq-once/run-1107-2315/kperf.txt:5-24`, `summary.txt:1-40` (ONCE, podziały);
- `24v-prefill-fa.md:19,55,60,64`, `24h-kv-jeden-przebieg.md:13,22,28`, `66e-anatomia-serwowania-tqllm.md:9,114`;
- `~/qwen-opt/logs/server-2026-11-06_175345.log` (przerwy, `f_keep`), `~/qwen-opt/latency/logs/l45-budget.server.log:166,193` (zapis wpisu);
- topka-q63 `c0576e3e8`: `ggml/src/ggml-cuda/fattn.cu:636-638,701-705`, `fattn-common.cuh:68-80,1089-1143`, `fattn-kvq.cu:388,433,492,617-635`, `src/llama-kv-cache.cpp:1549-1562,1843-1866,1954-1962`, `tools/server/server-task.cpp:1763-1793`, `common/speculative.cpp:2843`;
- wiki: `eksperymenty/2026-11-06-sesja-uzytkownika-final-mode.md`, `eksperymenty/2026-11-06-ctx-262k-fit.md`, `metody/koszt-szerokosci-weryfikacji.md`, `metody/kontroler-szerokosci-draftu.md`, `kernele/gdn-replay.md`, `rocm/hip-kopie-stronicowane-zostawiaja-svm.md`.

### Wiersze do ZRODLA (propozycja, wiki nieedytowane)

| źródło | wersja / data | raport, notatka | werdykt (≤12 słów) | kluczowe liczby | następnym razem sprawdź |
|---|---|---|---|---|---|
| stew675/llama-cpp-rdna-boosts | r234 `3cb0e6e`, 2026-11-07 | R68c §2.1 | Pochodna maska KQ i huge pages cache: bitowe, do portu. | maska −199 MiB/ub512; alokacja 3,4 GiB 470 → 125 ms | blok 05 FA prefill gfx1100 |
| llama.cpp PR #24561 (chunked GDN MFMA) | 2026-06-13 → 07-10, zamknięty | R68c §2.2 | GDN chunked f16: stratne, mały udział u nas. | e2e +2…6% przy ub 512 | port `mma.cuh` z MTP |
| llama.cpp PR #29846 (dekwant KV w FA MMA) | 2026-10-02 | R68c §2.2 | Przy ub 512 staging nie jest wąskim gardłem. | qwen35 27B ub512 ×1,02 | – |
| llama.cpp PR #29918 (`--cache-reuse-hybrid`) | draft 2026-10-03 | R68c §4 | Reużycie po edycji w środku: stratne. | KL 0,008–0,819 | – |
| llama.cpp Discussion #30282 (vahpetr s1) | 2026-10-10…10-21 | R68c §2.5 | LDS/occupancy FA prefillu bitowo: −16,5% kernela. | prefill 72k +8,2% (Vulkan) | port HIP układu LDS |
| vLLM #52585 / PR #52684 | 2026-08-17/18 | R68c §2.3 | gfx1100 FA prefill sięga 93 TFLOPS (D=128). | wall ×1,11–1,46 przy 8k | wersja D=256 |
| vLLM RFC #61761 (DFlash2 ROCm) | 2026-10-15 → 11-03 | R68c §2.3 | Odroczony stan GDN = nasze S4. | +5,6…10,6% przy c≥16 | – |
| SGLang RFC #28511 / ReplaySSM arXiv 2610.13778 | 2026-06-17 / 2026-10-09 | R68c §2.3–2.4 | Przy batch 1 bez zysku, nie bitowe. | +2,3% TPOT przy 128 równoległych | – |
| SuffixReplay arXiv 2609.33477 | 2026-09-27 | R68c §4 | Przybliżony stan GDN: stratne. | 91,4–100% jakości | – |
| MASW (EMNLP Findings 2026.306) | 2026-10 | R68c §2.4 | Bezstratny skompresowany draft, wymaga treningu. | draft 41 → 14 ms przy 32k | adapter dla MTP |
| SpecLA 2607.16673, KVBuffer 2605.19049 | 2026-07-18, 2026-05-18 | R68c §2.4 | Odroczony stan liniowy: mamy (`rs_lag`). | SpecLA 1,70× na H100 | – |
| chelokot/flash-attention-rdna3 | README 2026-11-07 | R68c §2.3 | Triton FA2 RDNA3; split-K 865 GB/s. | fwd 33–42 TFLOPS D=128 | – |
| QwenLM/FlashQLA | v0.1.3, 2026-09 | R68c §2.3 | Tylko NVIDIA (TileLang). | – | port AMD |
