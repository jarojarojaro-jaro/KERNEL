# 63d. Rzadka atencja (LSA, Strata KVA), głębokość MTP, Soft-MTP, vLLM 0.33 (FLy, XPress, DSpark), Flash-Next NVFP4, LLM Compressor 0.15

Data: 2026-11-05. Autor: podagent R63dAttention. Pracowałem tylko na CPU: bez GPU, bez serwera na :8080 i bez pobierania wag.
- Jedyny ruch sieciowy dotyczący wag to metadane mapy D-LSA: katalog ZIP (40 KB z końca pliku) i nagłówek `data.pkl` (3 KB z początku), pobrane przez HTTP Range. Samego pliku 6.3 MB nie pobierałem.
- Kod sklonowany do `~/src/research63/`: `latent-sparse-attention`, `Soft-MTP`, `Rapid-MLX`, `Strata`.

Sekcje C (atencja) i D (spekulacja i kwantyzacja) z `research-input-63.md`. Sprawdziłem rejestr źródeł: LSA, rapidmlx, KVA, Soft-MTP, closedcircuit, FLy i XPress nie były wcześniej badane. DSpark, Flash-Next i HIGGS były badane, więc przy nich podaję tylko **deltę** (sekcje 6.3, 7 i 8).

## TL;DR

1. **LSA nie jest przełomem dla naszego zakresu kontekstu (≤ 262k).**
   - Liczby z nagłówka (72.4× na warstwę, TTFT ~1/9) dotyczą **10M tokenów na 8×H200**.
   - W tej samej tabeli autorów przy 512k na H200 D-LSA daje TTFT **1.03×**, a na B300 **0.68× (wolniej)**. TPOT przy 512k wynosi **0.87× (wolniej)**.
   - Baseline „block sparse flat” (styl QSA) jest w tym zakresie lepszy: 1.61× przy 512k ([arXiv 2610.42147, Tab. 3](https://arxiv.org/html/2610.42147)).
   - Mapa D-LSA dla Qwen3.8-27B była destylowana i oceniana **ze statycznym YaRN ×40 na każdej długości**, także na krótkich promptach ([`_base.yaml`](https://github.com/Prefrontal-AI/latent-sparse-attention/blob/5ebea73/configs/evaluation/accuracy/qwen38_27b/_base.yaml)). Nasz serwer działa na natywnym RoPE, więc dopasowanie mapy jest niesprawdzone.
2. **Udział atencji u nas** (model czasu TTFT z naszych pomiarów, sekcja 0):
   - prefill: 11.5% przy 32k, 34% przy 128k, 44% przy 199k, 51% przy 262k;
   - decode: ~4.5% kroku przy 29.5k, ~14% przy 94k, ~19% przy 128k i ~39% przy 262k (dwie ostatnie wartości to ekstrapolacja `[SZACUNEK]`).
   - Realny zysk TTFT z LSA tylko w prefillu: **−22…−29% przy 128k, −42…−47% przy 262k, ~0–3% przy 32k** `[SZACUNEK]`.
   - Koszt: port 4–7 tygodni (5 nowych kerneli HIP, stan kubełków w checkpointach i slotach, zmiana jakości).
3. **Strata KVA to w praktyce SwiftKV bez destylacji.**
   - Na ostatnich warstwach prompt liczy tylko stan (K/V, rekurencja GDN), a wejściem jest residual z warstwy granicznej.
   - U nas (podział na warstwie 48 z 64) to **−19…−22% TTFT na każdej długości ≥ 8k** `[SZACUNEK]`, przy małym koszcie (3–6 dni).
   - Jest stratne. U Straty spadła akceptacja draftu po długim prompcie: R9700 −11% decode. Testy „needle” nie wykrywają szkód; wykrywają je dopiero zadania ekstrakcji i agentowe.
4. **Głębokość MTP zależy od karty** ([closedcircuit](https://closedcircuitconsultants.com/blog/mtp-speculative-decoding-local-qwen)): najlepsze n to 3 na 5090, 2 na 5080 i 1 na 4060; na 4060 n=3 daje 32 t/s wobec 46 przy n=1.
   - **Luka w aplikacji Enigma:** optymalizator kandydatów dla silnika upstream ma stałe `--spec-draft-n-max 4` ([`optimize.ts:104`](../../app/engine/src/server/optimize.ts)).
   - Najtańszy zysk w tym raporcie: przegląd n=1…4 w istniejącej pętli benchmarku.
5. **Soft-MTP: dla nas nic.** Przy zamrożonym pniu sprowadza się do samodestylacji KL głowicy, którą już zrobiliśmy, z wynikiem ±0.2–2% ([raport 11](11-mtp-pl-pilot.md), [lekcja](../../wiki/lekcje/lekcja-mtp-glowica-optimum.md)).
6. **vLLM 0.33:**
   - **FLy** (stratna weryfikacja) daje na Qwen3.8-27B MTP K=3 przy bs=1 **+8.2% (MI355X) i +5.3% (B300)**, akceptacja +6…+9 pp ([PR #53987](https://github.com/vllm-project/vllm/pull/53987)). Kandydat na opt-in „tryb szybki”.
   - XPress nie ma checkpointu dla 27B. Poprawka DSpark dotyczy tylko batcha. Kwantowaną głowicę draftu już mamy.
7. **Delta, której nie było na liście, a jest najważniejsza dla LFM:** Liquid wydał **LFM2.5-24B-A2B-DSpark** (GGUF F16, 664 MB, 2026-10-21; 5.16 tok/krok przy T=0 na B300).
   - Nasz `topka` ma już `--spec-type draft-dspark` (upstream [#27383](https://github.com/ggml-org/llama.cpp/pull/27383)).
   - Na MoE weryfikacja K tokenów czyta sumę ekspertów, więc na XTX wynik może być od ~0 do +30% `[SZACUNEK]`. Do zmierzenia w pół dnia (wymaga pobrania 664 MB, decyzja użytkownika).
8. **Flash-Next NVFP4 (NVIDIA)** to checkpoint ModelOpt W4A4 tylko dla B200/B300 (vLLM). Na 24 GB z offloadem potrzeba ≥ 128 GB RAM (eksperci ~68 GB plus PLE 51 GB FP8); szacunek ~30–50 t/s bez MTP, czyli gorzej niż IQ3_S. **Nie dla nas.**
9. **LLM Compressor 0.15:** HIGGS i QAD to zmiana kwantów (reguła „nie zmieniamy kwantów” obowiązuje). **REAP** ma sens tylko dla klas 12–16 GB w aplikacji Enigma (LFM i Qwen3.6-35B-A3B w całości w VRAM). Dla XTX nic.

---

## 0. Stan wyjściowy: ile u nas kosztuje atencja (XTX, Qwen3.8-27B UD-Q4_K_XL, KV q4_0)

| wielkość | wartość | źródło |
|---|---|---|
| Model czasu prefillu | T(N) = a·N + b·N², a = 0.953 ms/tok, b = 3.795 ns/tok² (dopasowanie do `long_ctx.jsonl`) | [21f-inferencex.md:122](21f-inferencex.md), [21f-agentx-stats-out.txt:21](21f-agentx-stats-out.txt) |
| Weryfikacja modelu przy 199k | zmierzone: prefill 339 s (587 t/s); model: 340 s | [WYNIKI-XTX-2026-10-19.md:86](../WYNIKI-XTX-2026-10-19.md) |
| FLOP-y atencji | 393 216 · n_kv na token (4·24·256·16); matmul 48.6 GFLOP/token; FA ~47 TFLOPS, 26% czasu przy 94k | [rr-prefill-kv.md:199-203](../../qwen-opt/research/v2/rr-prefill-kv.md) |
| Udział FA w kernelach | pp4096 2.2%, wypełnienie 32k 13%, pp512@d32k 24%; kernel ~50 TFLOPS (40% szczytu WMMA) | [24v-prefill-fa.md:9,11,60](24v-prefill-fa.md) |
| Decode: część zależna od kontekstu | ~4.5% kroku przy 29.5k, ~14% przy 94k (MTP n=4) | [21m-declarative-attention.md:3,34](21m-declarative-attention.md) |
| Rekordy długiego kontekstu | TTFT 94k 123 s; decode MTP przy 94k / 199k: 105.6 / 74.5 t/s | [REKORDY.md:39,108](../../wiki/REKORDY.md) |
| 262k na 24 GB | mieści się tylko z ub 512 (prefill 903 t/s vs 1256 przy ub 1024), zapas VRAM minimalny | [59-flint.md:53](59-flint.md) |
| Ważenie dla agenta | Qwen, cram 128k: prefill 58% zegara, decode 32%; ×2 prefill → −29.7% zegara | [21f-agentx-stats-out.txt:29](21f-agentx-stats-out.txt) |

Udział składnika kwadratowego (to w praktyce FA: 16 warstw × 4·24·256 FLOP na parę) w TTFT, liczony z modelu:

| N | TTFT (model) | udział b·N² |
|---|---|---|
| 32 768 | 35.3 s | 11.5% |
| 65 536 | 78.8 s | 20.7% |
| 131 072 | 190.1 s | 34.3% |
| 199 122 | 340.2 s | 44.2% |
| 262 144 | 510.6 s | 51.1% |

Wniosek: przy ≤ 64k atencja to mniej niż 21% prefillu, więc każda metoda rzadkiej atencji może dać tam najwyżej kilka procent. Dopiero przy 128–262k sufit (34–51%) robi się poważny.

---

## 1. Latent Sparse Attention (LSA), Prefrontal AI + ETH

Źródła:
- praca [arXiv 2610.42147 v2](https://arxiv.org/abs/2610.42147) (2026-11-03), czytana w całości w [HTML](https://arxiv.org/html/2610.42147);
- kod [Prefrontal-AI/latent-sparse-attention @ `5ebea73`](https://github.com/Prefrontal-AI/latent-sparse-attention) (2026-11-04);
- [blog](https://prefrontal.ai/news/lsa).

### 1.1 Mechanizm (z kodu i pracy)

1. **Klucze indeksu.** Dla każdej z 16 warstw pełnej atencji brane są tylko wymiary bez RoPE: 192 z 256 na głowicę KV, z 4 głowic KV sklejone do 768. Rzutuje je macierz `W_K_idx` 768×64, a wynik jest normalizowany L2. Zapytanie indeksu to suma 6 zapytań każdej grupy GQA (też bez RoPE), sklejona do 768, rzutowana przez `W_Q_idx` i normalizowana L2. Jedna lista kluczy obsługuje wszystkie 24 głowice ([`qwen38_27b.yaml`](https://github.com/Prefrontal-AI/latent-sparse-attention/blob/5ebea73/src/lsa/assets/models/qwen38_27b.yaml), [`lsa_flat_tp1.yaml`](https://github.com/Prefrontal-AI/latent-sparse-attention/blob/5ebea73/configs/evaluation/accuracy/qwen38_27b/lsa_flat_tp1.yaml), §3.3 pracy).
2. **Pooling i klastrowanie.** Co 4 kolejne klucze są sumowane w „pool key”. Gdy blok 512 tokenów jest pełny, jego 128 pool keys łączy się metodą Warda w rundach równoległych (wzajemnie najtańsze pary) do ~64 kubełków: średnio 8 kluczy, maksymalnie 16. Centroid kubełka to znormalizowana suma. Raz zbudowany kubełek nigdy się nie zmienia (§3.1, Alg. 1).
3. **Wyszukiwanie (flat).** Zapytanie liczy iloczyn skalarny z centroidami wszystkich skończonych bloków i bierze top-p = 1024 kubełków. Rozwija je w kolejności od najlepszego do k = 4096 kluczy dalekiego zasięgu, a do tego dochodzi 4 klucze sink i okno 512.
   - Przy ≤ 256k (< 32 768 kubełków) autorzy po prostu zapisują macierz wyników GEMM-em PyTorcha i biorą `topk` (App. F.1).
   - Dopiero powyżej tego progu używają kernela „threshold select”: próbka co 24. kubełka, próg, kompaktowanie w epilogu GEMM.
4. **Atencja.** FlashAttention-3 z `page_size=1`: lista indeksów działa jako tablica stron (README: `--attention-backend fa3 --page-size 1`). Wybór kluczy w prefillu robi host, dlatego `--disable-prefill-cuda-graph` jest wymagany ([README:110-121](https://github.com/Prefrontal-AI/latent-sparse-attention/blob/5ebea73/README.md)).
5. **Destylacja D-LSA.** Trenowane są tylko `W_Q_idx`, `W_K_idx` i temperatura τ (τ tylko w stracie), przy zamrożonym modelu.
   - Strata: KL(A‖Â), gdzie A to uśredniona po głowicach atencja nauczyciela przycięta do top-2048 kluczy.
   - Dane: 352M tokenów dokumentów 16k–1M, 48k kroków.
   - Wariant „Training-Free”: 64 główne kierunki PCA kluczy.
6. **Kernele.** CuTe DSL dla H200/B300 plus Triton jako wersja przenośna (`src/lsa/core/kernels/{cutedsl,triton}`; łącznie ~11k linii w `core` i `sglang`).

### 1.2 Wagi indeksera dla Qwen3.8-27B (tylko metadane)

Release [`d-lsa-weights-v1`](https://github.com/Prefrontal-AI/latent-sparse-attention/releases/tag/d-lsa-weights-v1) (2026-11-02) zawiera plik `qwen38_27b__long-16k-1M-heavy-key-and-query-d2048.pt`:
- **6 302 911 B**, sha256 `24cee934…bb9b`;
- archiwum ZIP z PyTorcha: 32 tensory po 196 608 B, czyli **768×64 fp32**, klucze `3.W_Q_idx`, `3.W_K_idx`, …, `63.W_K_idx`. To warstwy 3, 7, …, 63, czyli dokładnie 16 warstw pełnej atencji. Odczytane z centralnego katalogu ZIP i `data.pkl`.
- **Nie ma mapy dla warstwy MTP** (`blk.64`), więc atencja draftu MTP zostaje gęsta.
- Wariant PCA (`…pca-step0.pt`) ma 6 303 063 B.

Konwersja do GGUF jest trywialna: 32 tensory f32 albo f16, łącznie ~6 MB.

### 1.3 Twierdzenia i ich warunki

| twierdzenie | warunki | co mówi tabela / kod |
|---|---|---|
| warstwa atencji: prefill 72.4×, decode 42.5× (Qwen3.8-27B) | **10M tokenów**, jedna warstwa, ostatni chunk 32k, H200 bf16; baseline FA3 | przy 1M: prefill 8.2×, decode 5.2× ([blog](https://prefrontal.ai/news/lsa)); przy 128k/256k wartości są tylko na wykresie (Fig. 6) |
| TTFT ~1/9 (9.2×) | **10M, 8×H200, TP8+DCP8** | **512k: 1.03×** (H200), **0.68×** (B300 TP8); **1M: 1.51× / 0.96×**; TPOT przy 512k **0.87×** (Tab. 3) |
| „RULER nawet lepiej” | tylko **przy 10M** (63.9 vs 59.9) | ≤ 1M: „w granicach 5 pkt” od gęstej; MultiKey-2/3 i CWE spadają u wszystkich |
| wiedza i rozumowanie bez zmian | MMLU-Pro (2000), GPQA-D, AIME25 ×4, MATH500 (100) | wszystko w 95% CI; **LongBench v2 −5.0** (CI ±11.6, n=60) (Tab. 7) |
| N-LSA = jakość pełnej atencji | model ~0.5B, 24 warstwy (co 4. atencja + GDN), 128k | RULER@128k 32.2 vs 34.7; trening 1.24× szybciej |

**Wiarygodność i pułapki:**
- **Statyczny YaRN ×40 na każdej długości.** Baseline „Full Attention” to Qwen ze stałym YaRN factor 40, także przy 4k: „a short prompt is read under the same rotation and attention temperature as a 10M one” ([`_base.yaml`](https://github.com/Prefrontal-AI/latent-sparse-attention/blob/5ebea73/configs/evaluation/accuracy/qwen38_27b/_base.yaml)). Pod tym samym YaRN destylowano mapę.
  - Przewaga przy 10M jest więc w dużej mierze przewagą nad *zdegradowaną* ekstrapolacją. Rzadka atencja filtruje szum dalekich kluczy.
  - Przy natywnym RoPE do 262k (nasz przypadek) jakości mapy nikt nie mierzył. Projekcje czytają tylko wymiary bez RoPE, ale cel destylacji (rozkład atencji) zależał od rotacji i od temperatury YaRN.
- **Przy ≤ 512k LSA nie wygrywa e2e** (Tab. 3): przegrywa z własnym baseline'em block-sparse flat (styl QSA, 1.61× przy 512k). Sami autorzy piszą, że indeksowanie jest wąskim gardłem dopiero przy ultradługim kontekście (Fig. 2: 98% czasu przy 10M). LSA rozwiązuje problem, którego my przy 262k nie mamy.
- **Pomiary kerneli bez weryfikacji wyboru.** Harness mierzy LSA w trybie `--time-only`, bez sprawdzenia, czy wybór kluczy jest poprawny ([`kernels/qwen38_27b/_base.yaml`](https://github.com/Prefrontal-AI/latent-sparse-attention/blob/5ebea73/configs/evaluation/kernels/qwen38_27b/_base.yaml)). To uczciwie opisane i nie jest „reward hackiem”, ale liczby czasu nie gwarantują jakości.
- **Plus:** pełne konfiguracje, deterministyczne odtworzenie RULER z sumami kontrolnymi (README: 0.974/0.968 wobec 0.975/0.966 w pracy), osobny wariant PCA jako kontrola, przedziały ufności przy każdym benchmarku.

**Tok myślenia autorów (z pracy):**
1. Najpierw zmierzyli, gdzie idzie czas klasycznej rzadkiej atencji przy 10M: 98% to indekser, a „darmowy indekser” dałby 58× (Fig. 2).
2. Wyrocznią top-k sprawdzili, czy rzadka atencja w ogóle wystarczy: przy 128k k=512 trzyma 98% RULER (App. A).
3. Wybrali klastry semantyczne zamiast bloków, bo duże bloki „chowają” pojedynczy ważny klucz (App. E.6: im większy blok, tym wcześniejszy spadek).
4. Drzewo straciło dokładność powyżej 1M na GLM, więc domyślnie wysłali wersję flat.
5. Centroidy w fp8 wybierały 6× więcej kluczy inaczej niż fp32, więc zostały w bf16.
6. Top-k per span w stylu FAISS przegrał z progiem z próbki (1 536 vs 327 680 kandydatów).
7. Poniżej 256k zostawili zwykły GEMM + `topk`, bo specjalny kernel się nie opłaca.

To wzorcowa metodyka: najpierw sufit, potem wyrocznia, a dopiero na końcu kernel.

### 1.4 Co by to dało u nas (XTX, Qwen3.8-27B)

**Prefill (wariant hybrydowy: LSA tylko w prefillu).** W modelu T(N) zastępuję gęste pary (q,k) powyżej 4612 kluczy na zapytanie rzadkimi, z kosztem pary ×2…×5 względem gęstej FA.
- Powód tej kary: zbieranie po liście kluczy, tylko 6 wierszy Q na głowicę KV w kafelku WMMA 16-wierszowym i brak wspólnego kafla K/V dla sąsiednich zapytań.
- Dodaję indekser (scoring 128·N² FLOP przy ~20 TFLOPS, Ward ~2 ms na ubatch) i ruch list kubełków.

| N | TTFT dziś (model) | LSA, kara ×2 | ×3 | ×5 |
|---|---|---|---|---|
| 64k | 79 s | 67 s (−15%) | 69 s (−12%) | 73 s (−7%) |
| 128k | 190 s | 134 s (−29%) | 139 s (−27%) | 148 s (−22%) |
| 256k | 511 s | 269 s (−47%) | 278 s (−45%) | 296 s (−42%) |

`[SZACUNEK]`, obliczenie w sesji: model z §0 i liczba kluczy z Tab. 2 pracy. Przy 32k zysk wynosi ~2–3%, czyli praktycznie zero.

**Decode.** Część zależna od kontekstu to ~19% kroku przy 128k i ~39% przy 262k (ekstrapolacja liniowa z [21m](21m-declarative-attention.md)). Rzadki odczyt KV w weryfikacji (5 wierszy × 4612 kluczy zamiast całego KV) mógłby dać **+15…+17% t/s przy 128k i +30…+47% przy 262k** `[SZACUNEK]`, ale:
- część tego kosztu to atencja **warstwy MTP**, dla której mapy nie ma;
- każdy token odpowiedzi czytałby kontekst w przybliżeniu, więc wpływ na jakość jest większy niż w hybrydzie;
- autorzy mierzą TPOT przy 512k jako 0.87×, czyli wolniej, choć w innym reżimie (TP8 z DCP8, KV na 8 kart).

**Pamięć przy 262k:** centroidy (T/8 × 64 × 2 B) i tablica indeksów (T × 4 B) to ~5 MB na warstwę, czyli ~80–100 MB dla 16 warstw plus bufor wyników przy ub 512 (512 × 32 768 × 4 B = 64 MB). Przy naszym zapasie na 262k ([59-flint.md:53](59-flint.md)) to realne ryzyko utraty okna 262k.

**Koszt portu do llama.cpp/HIP `[SZACUNEK]`:**

| element | praca |
|---|---|
| tensory mapy w GGUF (32×768×64), projekcja i normalizacja L2 kluczy oraz zapytań indeksu w grafie `qwen35` (z K przed kwantyzacją q4_0) | 1–2 d |
| kernel Warda dla bloku 512 kluczy (rundy sekwencyjne, jeden blok na warstwę na ubatch, więc mało równoległości) | 2–4 d |
| stan kubełków: tylko z **zatwierdzonych** tokenów (rollback spekulacji), zapis w checkpointach VRAM, slot save/restore, `CACHE_SHARE_MIN` | 3–5 d |
| scoring GEMM, top-p = 1024 z ≤ 32k kubełków (`GGML_OP_TOP_K`), rozwinięcie do listy | 2–4 d |
| **kernel FA prefillu po listach per zapytanie na KV q4_0 (D=256, GQA 6)**: tu jest prawdziwe ryzyko wydajności | 5–10 d |
| opcjonalnie decode (`fattn-kvq` z listą) | 3–5 d |
| bramki jakości (KLD długi prompt, ekstrakcja PL/EN, agent replay) i ewentualna redestylacja mapy pod natywny RoPE (~50–100 H100-h `[SZACUNEK]`) | 1–2 tyg. + $150–300 |

Razem 4–7 tygodni, ryzyko wysokie.

**Porównanie z alternatywami (ten sam cel: TTFT przy 128–262k):**
- **Bezstratny szybszy kernel FA prefillu.** Dziś ~50 TFLOPS, czyli 40% szczytu WMMA ([24v](24v-prefill-fa.md)). Dojście do 80 TFLOPS daje −13% TTFT przy 128k i −19% przy 262k, bez zmiany tekstu. Strata pokazała na gfx1100 kernel WMMA 4.05× i e2e +22.8% przy 128K, choć z gorszego punktu startu ([notatki Straty, prefill.md:228](../../qwen-opt/research/strata/prefill.md)). To pozycja L7 w [15d](15d-prefill-dlugi-kontekst.md).
- **QSA (Qwen Sparse Attention) w forku llama.cpp** (pentaCoxian): na 4090 przy 255K prefill 2375 vs 1345 t/s, decode 114.7 vs 40.6. Opisuje to **raport 63c (R63cAMD)**, nie dubluję. W pracy LSA właśnie block-sparse flat (styl QSA) wygrywa przy ≤ 512k, więc jeśli robić rzadki prefill, to tą drogą.

### 1.5 Werdykt LSA
Na dziś **nie portować**. Najpierw tani test offline (E4 w §9), który sprawdzi, czy mapa w ogóle pasuje do natywnego RoPE i naszego Q4. Rzadki prefill robić drogą QSA (63c), a bezstratnie przyspieszać FA.

---

## 2. rapidmlx: hybryda „LSA w prefillu, gęsta atencja + MTP w decode”

- **Źródło:** tweet [x.com/rapidmlx/status/2118074173323141191](https://x.com/rapidmlx/status/2118074173323141191). Nie da się go przeczytać (X blokuje automatyczny dostęp), więc twierdzenia biorę z wejścia:
  - M3 Ultra, Qwen3.8-27B przy 128k: TTFT 640 → 440 s (−31%), pamięć 40.7 → 28.8 GB;
  - zysk 1.16× przy 64k i 1.41× przy 128k;
  - czysta LSA spowalnia decode przez routing per token.
- **Weryfikacja:**
  - W repo [raullenchai/Rapid-MLX @ `e2114cf`](https://github.com/raullenchai/Rapid-MLX) (2026-11-04) nie ma kodu LSA: grep po `latent`, `prefrontal` i `lsa` daje zero trafień, nie ma też gałęzi ani PR.
  - Jest za to opt-in **block-sparse prefill QSA** dla Flash-Next ([PR #3055](https://github.com/raullenchai/Rapid-MLX/pull/3055)): TTFT przy 64K −31.1% (116.0 → 80.0 s), przy 16K −1%.
  - Status: **niezweryfikowane**, wiarygodne co do rzędu wielkości.
- **Dlaczego na Macu zysk jest większy niż wyszedłby u nas:** ich prefill 128k trwa 640 s (~205 t/s), a nasz ~190 s.
  - Atencja SDPA w MLX przy 128k jest relatywnie droższa, a dzisiejsza pamięć wynika z materializacji, co sugeruje spadek o 12 GB.
  - Ich 1.16× przy 64k i 1.41× przy 128k pasuje do udziału atencji ~15–20% i ~30–35% prawie całkowicie usuniętego. U nas przy 64k realnie −7…−15% (§1.4).
- **Lekcja dla nas:** decyzja „prefill rzadki, decode gęsty” jest słuszna dla batch 1 z MTP.
  - Weryfikacja MTP liczy 5 wierszy, a każdy potrzebowałby własnej listy kluczy.
  - Narzut routingu per krok (3 kernele × 16 warstw) przy kroku ~28 ms zjada zysk, dopóki kontekst ma < ~100k.
  - Przy 200k+ to się odwraca (§1.4, decode).

---

## 3. Strata KVA (`STRATA_KVA=1`, v0.2.7) w tej samej ramie

Źródła:
- [release v0.2.7](https://github.com/Niko1221/Strata/releases/tag/v0.2.7) (2026-10-27);
- kod [Niko1221/Strata @ `9f7d977`](https://github.com/Niko1221/Strata) (2026-11-05): [`docs/KVA.md`](https://github.com/Niko1221/Strata/blob/9f7d977/docs/KVA.md), [`include/strata/prefill/kva.hpp`](https://github.com/Niko1221/Strata/blob/9f7d977/include/strata/prefill/kva.hpp), `src/prefill/prefill.cpp:3201-3373, 3930-3939, 4116-4122`.

### 3.1 Mechanizm
- **Nazwa „approximate attention on the last 12 layers” myli.** To nie jest przybliżona atencja, tylko **pominięcie ostatnich warstw dla pozycji promptu**.
- Dla pozycji [0, n − 2048) warstwy ≥ `split` (36 z 48 we Flash-Next) liczą **tylko stan**: K/V QSA i klucze indeksera, rekurencję GDN i historię konwolucji. Pomijają wyjście atencji, projekcję wyjściową, całą połowę MoE i transfery ekspertów.
- Wejściem każdej późnej warstwy jest residual **wchodzący do warstwy `split`** (tryb `identity`, zero dodatkowych wag). Ostatnie 2048 pozycji i cały decode liczą się dokładnie.
- Działa tylko przy zimnym odczycie od pozycji 0, przy promptach ≥ 4096 tokenów, na jednej karcie.
- Prior art: **SwiftKV** (Snowflake, [arXiv 2410.03960](https://arxiv.org/abs/2410.03960)), „SingleInputKV” plus destylacja, −25…−50% FLOP-ów prefillu. Strata robi to bez destylacji.

### 3.2 Pomiary i jakość ([`docs/KVA.md`](https://github.com/Niko1221/Strata/blob/9f7d977/docs/KVA.md))
- **Split 36 (domyślny po włączeniu):**
  - RTX 5070: +11% przy 14K, +18% przy 30K;
  - P100: +12% / +20%;
  - R9700: prompt 2411 → 3086 t/s (+28%), ale **decode 94.7 → 84.3 (−11%)**, bo akceptacja draftu spadła z 4.08 do 3.33 tok/rundę: komórki MTP są budowane z przybliżonych wierszy.
- **Jakość:**
  - ekstrakcja 585/606 faktów, tyle samo co dokładnie;
  - agent 6/10 wobec 4 i 7/10 w dwóch dokładnych przebiegach;
  - KL pierwszego tokenu przy split 24: 0.018–0.020 nats wobec podłogi szumu 0.0013–0.0032.
- **Split 24 (pierwsza wersja):** 1.3–1.5× szybciej, ale **0/10 zadań agentowych**, zgubione rekordy i wymyślony wiersz przy 30K, mimo że needle przechodził w każdym wariancie.
- Liczby z wejścia (RTX 2000 Ada, 30K: 913 → 1077, +14.2%; dokument 19.8K 21.4 → 18.4 s) są spójne z dokumentacją.

**Tok myślenia autora:**
1. Najpierw tryby `capture` i `oracle`: oracle odtwarzający prawdziwe wejścia daje identyczną odpowiedź, więc „hydraulika” jest poprawna.
2. Potem tryb `identity`.
3. Projektor liniowy rangi 256 okazał się **gorszy** od identity: błąd względny nigdy < 0.80, bo residual przesuwają decyzje routingu i atencji.
4. Pomiar wrażliwości per typ warstwy: błąd wejścia GDN kumuluje się w rekurencji (0.339 przy 18 warstwach GDN) bardziej niż błąd K/V QSA (0.153 przy 6 warstwach QSA).
5. Na końcu przesunięcie podziału na 36 i domyślnie **off** z decyzji właściciela. Każdy odrzucony odczyt jest logowany z powodem.

**Najcenniejsza lekcja dla naszych bramek:** testy needle i „streść dokument” **nie wykrywają** szkód stratnego prefillu. Wykrywają je ekstrakcja list rekordów i pętle agentowe.

### 3.3 Co to daje u nas (Qwen3.8-27B: 64 warstwy, FFN gęste)
Liczyłem FLOP-y z konfiguracji ([config.json](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/config.json): hidden 5120, FFN 17 408, 24/4 głowic × 256, GDN 16k/48v × 128).
- Warstwa: FFN 267M parametrów, atencja 105M, GDN 116M; pień ~24.35B.
- KVA z podziałem na **warstwie 48**: ostatnie 16 warstw, czyli 4 atencje i 12 GDN.
  - Wersja „state-only” zostawia tylko K/V atencji i wejście GDN (qkv, b, a) plus rekurencję.
  - Oszczędza **22.2% FLOP-ów matmul** i ~25% FA dla przybliżonych pozycji.

| N | TTFT (model) | KVA split 48, sufiks 2048 |
|---|---|---|
| 32k | 35.3 s | 28.5 s (−19%) |
| 64k | 78.8 s | 62.7 s (−20%) |
| 128k | 190.1 s | 149.5 s (−21%) |
| 199k | 340.2 s | 265.4 s (−22%) |
| 262k | 510.6 s | 396.4 s (−22%) |

`[SZACUNEK]`: matmul to ~90% liniowej części prefillu ([rr-prefill-kv roadmap](../../qwen-opt/research/v2/roadmap.md)).

Zestawienie z LSA: KVA daje stałe ~−20% **od 8k w górę** (tam, gdzie żyje agent), LSA daje dużo tylko przy ≥ 128k. Warianty da się złożyć.

**Ryzyka specyficzne dla nas:**
- **MTP.** Hak MTP w prefillu bierze końcowe stany wierszy promptu, a przy KVA ich nie ma. Opcje:
  - (a) komórki MTP z residualu warstwy 48, jak u Straty, co grozi spadkiem akceptacji o −11%;
  - (b) okno MTP tylko nad dokładnym sufiksem. To łączy się z naszym pomysłem okna atencji MTP ([strata/README #6](../../qwen-opt/research/strata/README.md)), który przy 94k i tak miał dać +5–10%.
- **Prefix cache i checkpointy.** Przybliżony stan trafia do cache i jest używany w kolejnych turach (u Straty tak samo, „nothing is approximated twice”). Tekst greedy przestaje być bitowy, więc bramka md5 ma sens tylko przy wyłączonym przełączniku.
- **GDN.** 12 z 16 przybliżanych warstw to GDN, a autor Straty pokazał, że GDN jest wrażliwszy. Warto mieć wariant `ONLY=attn` (u Straty `STRATA_KVA_ONLY=qsa`: tylko 1.08×, ale błąd 0.153).

**Koszt:** 3–6 dni.
- flaga w grafie `qwen35` per ubatch;
- logika „zimny odczyt ≥ 4096, sufiks 2048” w serwerze;
- wariant okna MTP;
- bramki jakości (§9 E3).

---

## 4. Głębokość MTP zależy od karty (closedcircuit, 2026-10-28)

Źródło: [closedcircuitconsultants.com/blog/mtp-speculative-decoding-local-qwen](https://closedcircuitconsultants.com/blog/mtp-speculative-decoding-local-qwen) (2026-10-28). Pomiar: 3 prompty, 1500 tokenów, T=1, po 3 przebiegi.

| karta / model / silnik | off | najlepsze n | wynik |
|---|---|---|---|
| 5090, 27B AWQ, vLLM | 59 | n=3 | 100 |
| 5090, 27B IQ4_XS, llama.cpp (build 11804) | 76 | n=3 | 108 (DFlash2 n=7: 89) |
| 5080, 35B-A3B Q4_K_M (część ekspertów na CPU) | 51 | n=2 | 68 (n=3: 66) |
| 4060, 9B Q4_K_M (distill) | 44 | n=1 | 46 (**n=3: 32**) |

**Krytyka.**
- Autor zgaduje, że 4060 „kończy się compute”. Nie podał akceptacji dla llama.cpp, a 9B to `empero-ai/Qwen3.8-9B-Distill`, czyli fine-tune z oryginalną głowicą MTP. To ten sam wzorzec co niedouczona głowica Swift ([ZRODLA](../../wiki/ZRODLA.md)), więc równie dobrze winna może być niska akceptacja.
- Rozrzut przebiegów jest duży: 88.5–120 t/s w jednym ramieniu.
- Kierunek zgadza się z naszymi danymi z chmury: najlepsze n 2 na 3080 i 3 na 3060 ([REKORDY.md:132-133](../../wiki/REKORDY.md)).

**Dla nas:**
- W aplikacji optymalizator kandydatów dla silnika upstream wymusza **n=4** (`specArgs`, [optimize.ts:104](../../app/engine/src/server/optimize.ts)).
- Profile `enigma` mają n z kampanii (`[INFERENCE]`, nie sprawdzałem manifestów), ale dla kart spoza kampanii i modeli spoza katalogu działa stałe 4.
- Pętla benchmarku kandydatów już istnieje, więc dodanie n ∈ {1, 2, 3, 4} jako osobnych kandydatów to ~pół dnia.

---

## 5. Soft-MTP („Multi-Token Prediction Done Right”, J. Teoh, MIT)

Źródła: [arXiv 2610.38331 v1](https://arxiv.org/abs/2610.38331) (2026-10-28, czytane w [HTML](https://arxiv.org/html/2610.38331)); kod [JaydenTeoh/Soft-MTP @ `4e1cf66`](https://github.com/JaydenTeoh/Soft-MTP) (2026-10-30).

- **Mechanizm.**
  - Gradient CE głowicy MTP rozkłada się dokładnie na dwie części: g_KL, czyli samodestylację do rozkładu NTP tego samego modelu z przesunięciem o k, oraz residuum g_res, czyli gradient CE NTP względem danych.
  - Residuum niesie ~80% gradientu MTP w pniu i ma ~4× niższe SNR (4.1× przy 167M, 4.6× przy 1.2B).
  - Jedna linia `h0[:, k:] += hk.detach() - hk` wstrzykuje −g_res, więc pień i głowica dostają tylko g_KL. Głowica wyjściowa nadal uczy się z CE.
- **Wyniki:** modele 167M–1.2B od zera, FineWeb-Edu 31.5B tokenów. Długość akceptacji **+1.8…+2.2%**, przyspieszenie **+1.4…+1.5%**, niższa perpleksja NTP.
- **Tok myślenia autora:** próbował zamortyzować koszt KL w NextLat, zauważył, że CE MTP już zawiera gradient KL, i dowiódł równości w float64 (test w repo).
- **Dla nas: NIE.**
  - Przy zamrożonym pniu i zamrożonej głowicy wyjściowej (nasz scenariusz douczania `blk.64`) Soft-MTP sprowadza się dokładnie do samodestylacji KL. Tę już zrobiliśmy (strata 0.9·TV + 0.1·CE) z wynikiem ±0.2% offline i ±2% online ([raport 11](11-mtp-pl-pilot.md), [lekcja-mtp-glowica-optimum](../../wiki/lekcje/lekcja-mtp-glowica-optimum.md)).
  - Koszt powtórki: przejście pnia 27B po ~100M tokenów to ~5.4e18 FLOP, czyli ~4 h na H100, ~$12 plus trening głowicy. Spodziewany zysk ≈ 0.
  - Dla LFM (bez MTP) bezcelowe, bo Liquid wydał już drafter DSpark (§6.3).

---

## 6. vLLM v0.33.0: FLy, XPress, DSpark

Tag [v0.33.0 `4ba787e`](https://github.com/vllm-project/vllm/releases/tag/v0.33.0) (2026-11-01). Release finalny nie ma treści, więc opis biorę z [v0.33.0rc3](https://github.com/vllm-project/vllm/releases) (2026-11-02).

### 6.1 FLy: stratna weryfikacja z bramką entropii ([PR #53987](https://github.com/vllm-project/vllm/pull/53987), scalony 2026-10-19; praca [arXiv 2511.22972](https://arxiv.org/abs/2511.22972))
- **Mechanizm.** Odrzucony token draftu zostaje przyjęty, jeśli spełnia trzy warunki:
  1. nie jest zamaskowany ograniczeniami;
  2. entropia top-3 celu jest ≥ 0.3;
  3. następne W tokenów draftu przechodzi **natywną** weryfikację.
  Drugie odrzucenie w oknie cofa wyjątek. Nie ma dodatkowego przejścia celu. Rozkład celu **nie** jest zachowany.
- **Qwen3.8-27B, MTP K=3, W=2, bs=1:** MI355X 220.8 → 238.9 t/s (**+8.2%**), B300 199.0 → 209.6 (**+5.3%**). Akceptacja 61.9 → 71.4% (MI355X) i 57.2 → 63.4% (B300).
- **Jakość:** GSM8K/MATH-500 po 100 pytań, AIME25 i GPQA-D, **jeden przebieg pass@1**. Retencja 98.9–103%; autorzy piszą wprost „not a quality guarantee”. Brak języków innych niż angielski.
- **Dla nas.** Przy T=1 i n=4 na prozie PL (E0: 2.158 tok/krok, [REKORDY.md:126](../../wiki/REKORDY.md)) +6…+9 pp akceptacji to szacunkowo **+5…+8% t/s** `[SZACUNEK]`, przy niezmienionym ms/krok.
  - Implementacja jest tania: decyzja w naszej ścieżce weryfikacji na GPU (`LLAMA_GPU_VERIFY=1`) potrzebuje entropii top-3 z logitów, które i tak liczymy.
  - Stratne, więc tylko opt-in. KLD jako bramka nie pasuje (zmienia się sekwencja), potrzebne są zadania.

### 6.2 XPress ([PR #54448](https://github.com/vllm-project/vllm/pull/54448), scalony 2026-10-22; [arXiv 2608.02438](https://arxiv.org/abs/2608.02438))
- **Mechanizm.** Przyczynowy „refiner” dla drafterów blokowych (DFlash, DSpark): ~80M parametrów, wąskie gardło rangi 256, mikser dolnotrójkątny i iteracja Jacobiego K przebiegów.
- Qwen3-8B na GSM8K: AL 5.65 wobec DFlash 3.5 i DSpark ~4.0.
- **Checkpointy są tylko dla Qwen3-4B/8B i Gemma 4 26B** ([UIUC-SSAIL na HF](https://huggingface.co/UIUC-SSAIL)). Dla Qwen3.8-27B nie ma żadnego, a my używamy MTP, nie drafterów blokowych.
- Werdykt: **nie dotyczy**. Do obserwowania, jeśli pojawi się XPress dla 27B lub dla LFM DSpark.

### 6.3 DSpark: poprawka harmonogramu i delta drafterów
- **Poprawka harmonogramu.** [PR #59468](https://github.com/vllm-project/vllm/pull/59468) (1373 → 3390 tok/s na GB300) przestaje rezerwować sloty draftu w budżecie tokenów, ale tylko przy batchu (64 vs 52 równoległych żądań). Przy batch 1 nic nie zmienia, więc **nie dotyczy**.
- **Kwantowana głowica draftu.** [PR #59973](https://github.com/vllm-project/vllm/pull/59973) (+18% przy c=1 dla Flash-Next na GB10) to ten sam pomysł, który już mamy: blok MTP w IQ4_XS i słownik draftu 64k ([REKORDY.md:18](../../wiki/REKORDY.md)).
- **Delta 1: DSpark v2 dla Qwen3.8-27B** (RadixArk, karta [Anbeeld GGUF @ `77843de`](https://huggingface.co/Anbeeld/Qwen3.8-27B-DSpark-GGUF)).
  - 1.86B parametrów, 5 warstw, blok 7.
  - Przy T=1 na czacie AL 3.23–3.29 (z tokenem bonusowym); v1 miało 2.57–2.61.
  - Nasz MTP4 na czacie daje ~3.1 tok/krok (spec_sweep), a na prozie PL drafter blokowy wypada słabo ([lekcja-drafter-gleboki-vs-mtp](../../wiki/lekcje/_hub.md)).
  - Rejestr mówi „na czacie nie lepsze niż MTP” ([ZRODLA:146](../../wiki/ZRODLA.md)). v2 może to zmienić tylko na EN i kodzie, więc niski priorytet.
- **Delta 2, ważna: drafter DSpark dla LFM2.5-24B-A2B.**
  - [LiquidAI/LFM2.5-24B-A2B-DSpark-GGUF @ `9222226`](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-DSpark-GGUF) (2026-10-21): F16, 664 MB, 5 warstw atencji, blok 9, embedding i lm_head współdzielone z celem.
  - Uruchomienie: `--spec-type draft-dspark --spec-draft-n-max 9`.
  - Karta wersji bf16 ([@ `e052e5b`](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-DSpark)): **5.16 tok/krok** (T=0, z bonusem), 2.38× przy c=1 na B300 FP8.
  - U nas w R33 i R16i drafter LFM 24B był jeszcze „coming soon” ([33-modele-na-karty.md:311](33-modele-na-karty.md), [16i:319](16i-magnitude-co-robia-dobrze.md)). Nasz `topka` ma już obsługę (`common/arg.cpp:393-414`).
  - **Pułapka MoE:** weryfikacja K tokenów czyta sumę ekspertów. Liquid sam pokazuje 8B-A1B na M4 Max: tylko 1.18×, choć akceptacja 6.95 z 10 ([blog](https://www.liquid.ai/blog/lfm2.5-dspark)).
  - Model dla XTX ([config](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B/blob/main/config.json): 64 ekspertów, top-4, 40 warstw), przy niezależnym routingu:
    - eksperci przy K=10 to 64·(1 − (60/64)^10) ≈ 30.5, czyli 7.6× bajtów ekspertów: ~8.2 GB na krok weryfikacji wobec ~1.7 GB plain ([NOTES.md:338](../../qwen-opt/NOTES.md));
    - przy 5.16 tok/krok wychodzi **≈ break-even**;
    - przy K=4–5 i AL ~3.3 wychodzi ~0…+15%.
    - Routing kolejnych tokenów jest skorelowany, więc realna suma jest mniejsza; górny pułap **+30%** `[SZACUNEK]`.
  - To trzeba zmierzyć, nie liczyć (§9 E2).

Poza listą: w tych samych notatkach jest **`ROCM_OCTAVE` KV 3–4 bit („4.6× tokenów KV fp16 na RX 7900 XTX”, #59774)**. Sprawa AMD, więc przekazuję do 63c.

---

## 7. NVIDIA Qwen3.8-Flash-Next-NVFP4

Źródło: [nvidia/Qwen3.8-Flash-Next-NVFP4 @ `fc694b54`](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4) (2026-09-05), metadane i README.

- **Format.** ModelOpt 0.46, mieszana precyzja:
  - routowani eksperci w **W4A4 NVFP4** (skale kalibrowane MSE);
  - atencja, shared expert i reszta pnia w **BF16**;
  - eksperci MTP w FP8 z blokami 128×128;
  - PLE (osadzenia n-gramów, 51B) w FP8 per tensor.
  - Repo ma razem **132.7 GB**, w tym jeden plik `model-fp8-mtp-ple.safetensors` 53.7 GB. Liczba „−63%” to „~2.7× mniej niż BF16”.
- **Środowisko:** vLLM na B200/B300 (Blackwell, natywne FP4). Jakość wobec FP8: GPQA-D 91.5 vs 92.0, Terminal-Bench 82.9 vs 83.3. Licencja NVIDIA Open Model plus Qwen Community (ograniczenia „AI Work Assistant”, [ZRODLA](../../wiki/ZRODLA.md)).
- **Czy da się to uruchomić na 24 GB z offloadem ekspertów?** Rachunek z [config.json](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4/blob/main/config.json) (hidden 2560, 512 ekspertów × 640, top-10, 48 warstw):
  - eksperci ~121B × 0.5625 B ≈ **68 GB**;
  - gęsta reszta BF16 ~3.5–4.2B parametrów ≈ **7–8.4 GB**;
  - PLE **51 GB**.
  - Potrzeba ≥ 128 GB RAM albo PLE z NVMe, jak w Gyro.
- **Prędkość na XTX lub 3090/4090.** Gęsta reszta BF16 to ~7 GB na token z VRAM, czyli ~7.3 ms. Aktywni eksperci to ~1.33 GB na token NVFP4; w VRAM mieści się ~20% ekspertów, więc trafienia wynoszą ~40–60%. Reszta to 0.5–0.8 GB z RAM: przez PCIe ~20–30 ms albo na CPU z DDR5 ~10–15 ms. Wynik: **~30–50 t/s bez MTP** `[SZACUNEK]`.
- **Porównanie z GGUF:** Strata na XTX z IQ3_S ma 62.3 t/s ze spekulacją MTP 3 ([57b:201](57b-strata-qwen38-flash.md)), tqLLM na 3090 77 t/s przy 128K ([60c:55](60c-quant-and-3090-engines.md)). NVFP4 ma 1.3× więcej bajtów ekspertów niż IQ3_S, a na RDNA3 nie ma natywnego FP4.
  - Repack do GGUF NVFP4 jest możliwy, bo mamy NVFP4 `MUL_MAT_ID` na HIP i skale per ekspert jako `ggml_mul` ([59-flint.md:96](59-flint.md)). To jednak wciąż dekwantyzacja bez zysku.
- **Werdykt: nie dla nas.** Na 5090 (32 GB, FP4) też nie mieści się bez offloadu, a vLLM nie ma dobrego offloadu ekspertów.

---

## 8. LLM Compressor v0.15.0 (2026-10-29)

Źródło: [release 0.15.0](https://github.com/vllm-project/llm-compressor/releases/tag/0.15.0).

| funkcja | co robi | dla nas |
|---|---|---|
| **HIGGS autoquant** (#3028, [arXiv 2411.17525](https://arxiv.org/abs/2411.17525)) | MSE per warstwa, potem ILP pod docelowe bpw, zbieranie < 10 s | ten sam pomysł co nasza alokacja per tensor ([57g](57g-quantalloc-ear.md)); wyjście w compressed-tensors, nie GGUF; reguła „nie zmieniamy kwantów” → **nie** |
| **Blokowe QAD bez nauczyciela** (#3029) | destylacja bloków do zbuforowanych wyjść niekwantyzowanych, po GPTQ/AWQ | wyjście W4A16 g32 symetryczne da się bezstratnie przepakować do **Q4_0** (ten sam kod); tak powstał LFM QAD-Q4_0 ([REKORDY.md:88](../../wiki/REKORDY.md)). Dla XTX bez zmiany decyzji |
| **REAP / MoNe** (#3281, #3343; [REAP arXiv 2510.13999](https://arxiv.org/abs/2510.13999)) | przycinanie ekspertów po istotności (wagi routera × norma aktywacji), raport JSON, przycinanie wprost z safetensors; MoNe zwija słabe eksperty do wektorów „novice” | **tylko klasy 12–16 GB w aplikacji:** LFM Q4_K_M 14.5 GB → ~11 GB przy 25% (bez `--n-cpu-moe` na 3060 i 4070 Ti); Qwen3.6-35B-A3B przy 50% w całości w 12 GB. Ryzyko: kalibracja po angielsku i kodzie; REAP sam deklaruje „near-lossless” dla **kodu** przy 50%. Gotowe pliki już są na HF: `anik-jha/Qwen3.6-35B-A3B-coding-reap50-GGUF`, `crucible-labs/Qwen3.6-35B-A3B-REAP-48-v2-GGUF`, `mradermacher/LFM2-24B-A2B-REAP-i1-GGUF` (LFM2, nie 2.5) |
| MXFP6, SpinQuant R1/R2 bez modelu, szybsze obserwatory | — | nie dotyczy (brak FP6 i FP4 na RDNA3) |

Na XTX REAP **nie przyspiesza** decode, bo czyta się tylu samych aktywnych ekspertów. LFM i tak mieści 131k przy KV q8_0.

---

## 9. Co z tego dla nas (ranking: spodziewany zysk / wysiłek)

| # | pomysł | zysk | wysiłek | ryzyko | stratne? |
|---|---|---|---|---|---|
| 1 | **E1: przegląd n MTP per karta w optymalizatorze aplikacji** | słabe karty do +10…+40% (closedcircuit 4060: 32 → 46 t/s); XTX 0 | 0.5 d | niskie | nie |
| 2 | **E2: LFM2.5-24B-A2B + DSpark na XTX** (obsługa już w `topka`) | od −5 do +30% decode LFM `[SZACUNEK]` | 0.5 d pomiaru (+ pobranie 664 MB, zgoda) | niskie | nie (różnice float) |
| 3 | **E3: KVA dla Qwena (podział 48, sufiks 2048, okno MTP), opt-in** | −19…−22% TTFT zimnego promptu ≥ 8k | 3–6 d + bramki | średnie (jakość, MTP) | tak |
| 4 | Bezstratny kernel FA prefillu (L7 z 15d), punkt odniesienia dla LSA | −13% TTFT @128k, −19% @262k | 5–10 d | średnie | nie |
| 5 | **E5: FLy jako opt-in „tryb szybki”** | +5…+8% t/s czatu przy T=1 | 2–3 d | średnie (jakość PL) | tak |
| 6 | Rzadki prefill drogą QSA (patrz **63c**) zamiast LSA | ~−44% TTFT @255k (pomiar 4090 w 63c) | 63c | 63c | tak |
| 7 | **E4: test wykonalności mapy LSA offline** (bramka przed jakimkolwiek portem) | rozstrzyga −27% @128k / −45% @262k | 1 d (10 min GPU + CPU) | niskie | — |
| 8 | Port LSA (prefill, potem decode) | −22…−29% TTFT @128k, −42…−47% @262k; decode +15…+47% @128–262k | 4–7 tyg. | wysokie | tak |
| 9 | **E6: REAP dla klasy 12 GB (LFM, Qwen3.6)** | 12 GB: bez offloadu ekspertów, wielokrotny decode `[SZACUNEK]` | 1–2 d + chmura ~$5–20 | wysokie (jakość PL) | tak (inny model) |
| — | Soft-MTP, XPress, harmonogram DSpark, Flash-Next NVFP4, HIGGS, QAD | ~0 dla nas | — | — | — |

### E1. n MTP per karta (aplikacja Enigma)
- **Dziś:** `specArgs('mtp')` daje zawsze `--spec-draft-n-max 4` ([optimize.ts:104](../../app/engine/src/server/optimize.ts)).
- **Zmiana:** kandydaci `mtp-n1`…`mtp-n4` w `planCandidates`; ta sama pętla `bench.ts` mierzy już t/s i akceptację (`draft_n_accepted`). Wygrywa najlepszy t/s.
- **Pomiar:** spec_sweep T=1 (6 promptów × 3 seedy) na 3060 12 GB, 4060 Ti 16 GB i XTX.
- **Oczekiwany wynik:** baseline n=4 (np. 3060 Qwen Q2_K_XL ~38.6 t/s, kampania z n=3, [REKORDY.md:133](../../wiki/REKORDY.md)) → po przeglądzie najlepsze n → **+0…+15% na kartach 8–12 GB** `[SZACUNEK]`, XTX bez zmian.
- **Kill:** < +3% na wszystkich trzech kartach. Wtedy zostaje n=4, a przegląd tylko w trybie „pełny”.

### E2. LFM + DSpark na XTX
1. **Krzywa kosztu weryfikacji, bez draftera:** `llama-bench -m LFM2.5-24B-A2B-Q5_K_M.gguf -fa 1 -ctk q8_0 -ctv q8_0 -p 1,2,3,4,5,6,8,10 -n 0 -r 5`. Daje t(K) z prawdziwą korelacją routingu i próg AL = t(K)/t(1) na każde K.
2. Jeśli t(5)/t(1) < ~2.5: `llama-server` z `-md LFM2.5-24B-A2B-DSpark-F16.gguf --spec-type draft-dspark --spec-draft-n-max {3,5,9}` (wymaga zgody na 664 MB przez SIM), `spec_sweep lfm` przy T=1 i T=0, plus E0 po polsku.

- **Oczekiwany wynik:** baseline 293.8 t/s (spec_sweep `lfm none`, [REKORDY.md:58](../../wiki/REKORDY.md)) → DSpark z najlepszym n → przyrost **od −5 do +30%** `[SZACUNEK]`.
- **Kill:** krok 1 pokazuje t(5)/t(1) > 3, albo w kroku 2 wynik < +5%.

### E3. KVA dla Qwen3.8-27B (opt-in `LLAMA_KVA_SPLIT=48`, `LLAMA_KVA_SUFFIX=2048`)
1. **Wykonalność (GPU ~10 min):** dump residualu wchodzącego do warstw 48…63 dla promptu 8k i 30k (PL i EN). Na CPU: błąd względny identity vs prawdziwe wejście per warstwa, osobno dla GDN i atencji, jak w `STRATA_KVA_CAPTURE`.
2. **Implementacja:** w grafie `qwen35` dla ubatchy całkowicie poniżej sufiksu warstwy ≥ 48 liczą tylko `attn_k`/`attn_v` z zapisem KV oraz `ssm_in` (qkv, b, a) z konwolucją i rekurencją. Bez `ssm_out`, bramki z, FFN i wyjścia atencji. Hak MTP dostaje okno tylko nad dokładnym sufiksem.
3. **Pomiar:** `long_ctx_bench` (prompty 6.6k, 29.5k i 94k): TTFT, a po nim decode i tok/krok MTP.

- **Bramki jakości** (lekcja Straty: needle nie wystarczy):
  - ekstrakcja list rekordów 14–30k (PL i EN, liczba faktów);
  - replay agenta z `bodies_huge.jsonl`;
  - KL pierwszego tokenu z przebiegiem off-vs-off jako podłogą szumu.
- **Oczekiwany wynik:** TTFT 94k 123 s ([REKORDY.md:39](../../wiki/REKORDY.md)) → ~98 s, czyli **−20%** `[SZACUNEK]`.
- **Kill:** fakty < dokładne −1%, albo decode po długim prompcie gorszy o > 5%, albo zysk TTFT < 12%.

### E4. Wykonalność mapy LSA offline (bramka przed portem)
1. **GPU ~10 min:** dump wymiarów q i k bez RoPE (192 na głowicę) z 16 warstw atencji naszego Q4 dla 3 dokumentów 32k i 128k (PL i EN) oraz dokładnych mas atencji top-k (eval-callback).
2. **CPU:** Ward na blokach 512, projekcja mapą `d2048` i mapą PCA (pobranie 2×6.3 MB, zgoda), wybór top-1024 kubełków. Metryka: pokrycie masy atencji nauczyciela, analogicznie do ich 0.30 przy 1M.

- **Oczekiwany wynik:** brak baseline'u dla naszego modelu; cel ≥ 0.8 masy przy 128k, natywny RoPE.
- **Kill:** < 0.6. Wtedy port LSA odpada albo wymaga redestylacji (~$150–300).

### E5. FLy (opt-in)
- **Zmiana:** w ścieżce weryfikacji na GPU przyjmować pojedyncze odrzucenie, gdy entropia top-3 celu ≥ 0.3 i W=2 kolejne drafty przechodzą.
- **Pomiar:** E0 (8 promptów PL × 8 seedów) i spec_sweep T=1.
- **Oczekiwany wynik:** E0 78.93 t/s, 2.158 tok/krok ([REKORDY.md:126](../../wiki/REKORDY.md)) → **+5…+8%** `[SZACUNEK]`.
- **Bramka jakości:** zestaw zadań PL z 16e plus GSM8K, 3 seedy na ramię.
- **Kill:** < +3% t/s, albo spadek zadań poza szumem off-vs-off.

### E6. REAP dla klasy 12 GB (aplikacja)
- **Zmiana:** raport istotności `llm-compressor` (REAP, `sparsity=0.0`) na kalibracji PL + kod + wywołania narzędzi. Potem przycięcie 25% dla LFM i 25–50% dla Qwen3.6, GGUF Q4_K_M i 3060 12 GB bez `--n-cpu-moe`.
- **Oczekiwany wynik:** baseline z [33-modele-na-karty.md](33-modele-na-karty.md) (3060 z Qwen3.6 i offloadem: 52/40/32 t/s przy 0/64k/131k, `[SZACUNEK]` w R33) → w całości w VRAM: wielokrotność `[SZACUNEK]`.
- **Bramka:** KLD vs pełny model, PL 16e, BFCL.
- **Kill:** KLD > 2× wobec Q4 pełnego albo PL < −2 pkt.
- Wymaga BF16 w chmurze, czyli zgody na wydatek.

### Lekcje do bazy wiedzy
1. **„N× na warstwę przy 10M” nie przenosi się na ≤ 262k.** Najpierw liczyć udział atencji z własnego modelu T(N) = aN + bN²: u nas b·N² to 11% przy 32k i 51% przy 262k.
2. **Stratny prefill sprawdzać ekstrakcją i agentem, nie needle.** Strata: split 24 przechodził needle w każdym wariancie, a dawał 0/10 agentów.
3. **Baseline z YaRN ×40 przy krótkich promptach to inny model** niż nasz serwer na natywnym RoPE.
4. **Spekulacja na MoE: AL nie wystarcza.** Trzeba znać krzywą t(K), bo suma ekspertów rośnie z K (Liquid 8B-A1B: AL 6.95 z 10 daje tylko 1.18× na M4 Max).

---

## Źródła (do ZRODLA)

| źródło | wersja / data | rola |
|---|---|---|
| LSA, [arXiv 2610.42147](https://arxiv.org/abs/2610.42147) | v2, 2026-11-03 (v1 2026-10-30) | §1 |
| [Prefrontal-AI/latent-sparse-attention](https://github.com/Prefrontal-AI/latent-sparse-attention) | `5ebea73` (2026-11-04); 405★ | §1 |
| release `d-lsa-weights-v1` | 2026-11-02; mapa Qwen 6 302 911 B, sha256 `24cee934…` | §1.2 |
| SGLang fork `Prefrontal-AI/sglang` tag `lsa-v0.1.0` | `042d955ba3` (z README, niesklonowany) | §1.1 |
| [prefrontal.ai/news/lsa](https://prefrontal.ai/news/lsa) | 10.2026 | §1.3 |
| rapidmlx, X 2118074173323141191 | nieczytelny | §2 |
| [Rapid-MLX](https://github.com/raullenchai/Rapid-MLX) | `e2114cf` (2026-11-04), PR #3055 | §2 |
| [Strata](https://github.com/Niko1221/Strata) `docs/KVA.md`, `kva.hpp` | `9f7d977` (2026-11-05); v0.2.7 (2026-10-27), v0.2.10 (2026-11-02) | §3 |
| SwiftKV, [arXiv 2410.03960](https://arxiv.org/abs/2410.03960) | v3 | §3.1 |
| [closedcircuit, MTP](https://closedcircuitconsultants.com/blog/mtp-speculative-decoding-local-qwen) | 2026-10-28 | §4 |
| Soft-MTP, [arXiv 2610.38331](https://arxiv.org/abs/2610.38331); [JaydenTeoh/Soft-MTP](https://github.com/JaydenTeoh/Soft-MTP) | v1 2026-10-28; `4e1cf66` (2026-10-30) | §5 |
| vLLM [v0.33.0](https://github.com/vllm-project/vllm/releases/tag/v0.33.0) | tag `4ba787e` (2026-11-01), notatki z rc3 (2026-11-02) | §6 |
| vLLM PR [#53987 FLy](https://github.com/vllm-project/vllm/pull/53987), [#54448 XPress](https://github.com/vllm-project/vllm/pull/54448), [#59468](https://github.com/vllm-project/vllm/pull/59468), [#59973](https://github.com/vllm-project/vllm/pull/59973) | scalone 10-19 / 10-22 / 10-15 / 10-15 | §6 |
| [LiquidAI/LFM2.5-24B-A2B-DSpark-GGUF](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-DSpark-GGUF), [bf16](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B-DSpark) | `9222226` (2026-10-21), `e052e5b` | §6.3 |
| [Liquid blog LFM2.5-DSpark](https://www.liquid.ai/blog/lfm2.5-dspark) | 2026-08-20, zm. 2026-10-27 | §6.3 |
| [Anbeeld/Qwen3.8-27B-DSpark-GGUF](https://huggingface.co/Anbeeld/Qwen3.8-27B-DSpark-GGUF) (karta RadixArk v2) | `77843de` (2026-09-06) | §6.3 |
| [nvidia/Qwen3.8-Flash-Next-NVFP4](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4) | `fc694b54` (2026-09-05) | §7 |
| [llm-compressor 0.15.0](https://github.com/vllm-project/llm-compressor/releases/tag/0.15.0) | 2026-10-29 | §8 |
| REAP, [arXiv 2510.13999](https://arxiv.org/abs/2510.13999) | 2025-10-15 | §8 |
