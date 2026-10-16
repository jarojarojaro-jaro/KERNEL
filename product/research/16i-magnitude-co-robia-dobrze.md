# 16i. Magnitude: co robią dobrze i co z tego możemy przejąć

Data: 2026-10-16. Autor: podagent MagnitudeStudy (z trzema scoutami: MagDraftCtl, MagDflashFam, MagVerifyKern). Tylko CPU: czytanie kodu i gotowych logów, bez GPU i bez chmury.
Skrypt rozkładu i projekcji: [16i-magnitude/decompose.py](16i-magnitude/decompose.py), wynik w [16i-magnitude/results.txt](16i-magnitude/results.txt).

Skróty ścieżek w cytatach:
- `M/` = `~/qwen-opt/magnitude/src/inference/` (z tego katalogu jest zbudowany release `magnitude-engine`, `build/magnitude-sha.txt`; release 0.2.9, `sourceCommit 954d677d`, `~/qwen-opt/magnitude/magnitude-release.json`);
- `D/` = `~/qwen-opt/magnitude/src/design/`;
- `R5/` = `~/qwen-opt/cloud/results/magnitude-vs-5060ti-20261016/`, `R3/` = `~/qwen-opt/cloud/results/magnitude-vs-3090-20261016/`.

## 0. Najważniejsze w 10 punktach

1. **Na Qwen3.8-27B (3090) cała ich wygrana na code-edit to sufit bloku, a nie szybsze kernele.** DFlash2 ma blok 8, czyli 7 propozycji + anchor (`M/engine/families/dflash/tests/interpretation.rs:553-598`). Na 3 z 4 plików robią **7.88 tok/krok** (894 z 897 propozycji przyjęte) przy **50.0 ms/krok**. My mamy 4.92 tok/krok (sufit n_max=4 to 5) przy 46.5 ms. Daje to 157 vs 105 t/s: ×1.60 z tok/krok i ×0.93 z czasu kroku (`R3/x/xbench.jsonl`, tabela §2).
2. **Szerokość draftu dobierają adaptacyjnie per runda i to jest ich najlepszy pomysł do skopiowania.**
   - Kandydaci to drabinka szerokości, przy których propozycje + anchor wypełniają klasę wierszy 2/4/8/16 (`M/engine/executor/src/planning/capabilities.rs:29-42`), plus szerokość 0.
   - Akceptację mierzą osobno dla każdej głębokości. Oceniają **każdą wydraftowaną propozycję, także niezweryfikowaną**, przez porównanie z tokenami zatwierdzonymi później.
   - Koszty launchy mierzą per (wiersze, klasa kontekstu = potęga 2).
   - Wybierają parę (wydraftowane, zweryfikowane) o największej liczbie tokenów na sekundę. Około 1% czasu dekodowania idzie na „looks”, czyli rundy szersze niż optymalna (`M/engine/generation/src/draft_control.rs:1-32,352-506`; kontrakt `D/inference/engine/speculative-generation.md:282-379`).
   - Domyślnie włączone (`M/engine/src/options.rs:280-290`). W naszym sweepie widać to wprost: propozycji na krok jest od 1.81 (pl-proza) do 6.75 (pl-kod) na 3090 i 0.23 (pl-proza, praktycznie bez draftu) na 9B.
3. **Kerneli weryfikacji nie mają lepszych od naszych.**
   - Ich krok 27B na 3090 przy ~3 wierszach wynosi 44.0 ms, tyle co nasz przy 5 wierszach (sweep pl-proza). Przy 8 wierszach mają 48–50 ms.
   - Ich własna tabela kosztów w testach: weryfikacja 8 wierszy +40%, a 16 wierszy +150% względem 1 wiersza przy 4k (`M/engine/generation/src/draft_control/tests.rs:49-63`).
   - U nas na XTX V(16) − V(5) = +7.1 ms, czyli +25% (`~/qwen-opt/k4/vcost_qwen-k4b.csv`).
   - Hasło z ich dokumentacji „verification costs one decode step” (`M/docs/kernels/drafting-and-verification.md:59-83`) jest celem projektowym, nie stanem faktycznym. Na 5060 Ti krok 16 wierszy wynosi 35 ms, a krok niemal plain 18.3 ms.
4. **Długi kontekst to ich słabość.** Krok 8 wierszy przy 64k ma 91 ms, przy 2k 50 ms, czyli +41 ms. Nasz krok 5 wierszy rośnie z 46.5 do 64.8 ms (+18 ms). Dlatego na copy 64k wygrywają tylko 1.15× (80.2 vs 69.7 t/s), mimo ×1.62 tok/krok.
5. **Nie mają żadnego lookupu ani n-gramu.** Kernele `ngram_*` to osadzenia n-gramów modelu Qwen4exp, a nie spekulacja (`M/engine/kernels/kernels/ngram.seismic:1-15`). Kopię „widzi” sam drafter DFlash, który ma własną historię KV cech celu (`M/engine/executor/src/programs/native_draft.rs:742-818`), ograniczoną oknem 2048 w DFlash2. Na `lazy.py` (prompt 3148 tokenów) ich tok/krok spada do 5.63 [INFERENCE: okno].
6. **Sprzężone próbkowanie draftu (coupled sampling) da się przenieść 1:1 i jest bezstratne.**
   - Każda propozycja jest wybierana z tym samym ziarnem i tą samą pozycją co próbka celu (`M/engine/generation/src/lib.rs:745-779`).
   - Sampler to Gumbel-max na Philox, kluczowany pozycją i tokenem (`M/engine/kernels/kernels/readout.seismic:325-329`).
   - Gdy rozkłady draftu i celu są równe, wybory są identyczne także przy T=1.
   - U nas DFlash traci przy T=1 20% (T=0: 90.6, T=1: 71.9 t/s; wiki `eksperymenty/2026-10-10-sweep-mtp-dflash.md`), a MTP 2–6%.
7. **Polski: ich drafter jest trenowany prawie bez polskiego.** DFlash trenowano na ~800K próbkach z Nemotron Post-Training v2 i CodeAlpaca, z odpowiedziami regenerowanymi przez cel, przy maksymalnej długości 3072 (arXiv 2602.06036, §5 „Datasets”, A.1). Karta Nemotron v2 wymienia angielski, niemiecki, włoski i 3 inne języki; polskiego nie ma (https://huggingface.co/datasets/nvidia/Nemotron-Post-Training-Dataset-v2). Wynik: 9B pl-proza 1.00 tok/krok, a kontroler schodzi do plain (55.0 vs nasze 86.7 t/s).
8. **Na 27B DFlash2 wygrywa z naszym MTP na generowaniu kodu przy T=1:** pl-kod 109.2 vs 79.3 t/s (5.29 vs 3.52 tok/krok), en-code 86.5 vs 71.2. Na pl-proza przegrywa: 30.1 vs 44.9. Mediana sweepu wychodzi równo: 65.7 vs 66.4 (`R3/x/xbench.jsonl`).
9. **Autotune w release nic nie zmienił.** Wszystkie 67 jednostek dostały domyślne konfiguracje (`"canonical_fallbacks":67`, `R3/logs/qwen.mag.first.tuning.jsonl`, event `concluded`). Ich wydajność to domyślne kernele plus drafter plus kontroler.
10. **Najtańsza droga do ich wyniku:**
    - ogon z lookupu doklejany do MTP4 do 8 wierszy łącznie (agent XtxLookupTail), sterowany kontrolerem w stylu Magnitude. Projekcja na XTX dla code-edit: **×1.4** przy 8 wierszach i ×1.8–2.1 przy 16 wierszach na krótkim kontekście (§3);
    - bez ruszania pisania po polsku, bo kontroler ma szerokość 0 ogona;
    - drugi krok: sprzężone próbkowanie;
    - trzeci krok, opcjonalny: DFlash2 jako drugi drafter do kodu/EN.

## 1. Mechanizm (z kodu)

### 1.1 Drafter: DFlash / DFlash2 / DSpark
- **Wspólna rodzina.** GGUF arch `dflash`; DSpark rozpoznaje po `markov_w1`, DFlash2 po `selector_*` (`M/engine/families/dflash/src/lib.rs:483-541`).
- **Kondycjonowanie.** Tapy na resztach wchodzących do bloków celu (`TapPoint::Sublayer{block, sublayer:0}`, `M/engine/families/contracts/src/family.rs:61-82`). Fuzja `fc` `[hidden, taps·hidden]` jedzie w grafie readoutu celu podczas weryfikacji, bez osobnego launchu (`M/engine/executor/src/programs/graph/readout.rs:961-1000`).

| drafter | tapy celu | warstwy | blok / max propozycji | okno / atencja | źródło |
|---|---|---|---|---|---|
| Qwen3.8-27B DFlash2 | 6, 20, 34, 48, 62 | 5 | 8 / 7 | 2048 na wszystkich, dwukierunkowa | `interpretation.rs:553-598` |
| Qwen3.8-27B DSpark | 5, 17, 29, 41, 53 | – | 7 / 7 (AnchorFirst) | YaRN | `interpretation.rs:529-550` |
| Qwen3.6-35B DFlash | 2, 7, 12, 17, 23, 28, 33, 38 | 6 | 16 / 15 | 5× okno 4096 + 1 pełna | `interpretation.rs:163-209` |
| Qwen3.5-9B DFlash | brak fixtury | 6 (5 block-causal + 1 dwukierunkowa) | 16 / 15 [INFERENCE: 14.3 propozycji/krok w xbench] | – | `interpretation.rs:733,770-781` |

- **Historia draftera.** Każdy zatwierdzony token wstrzykuje swoją cechę jako K/V w każdej warstwie draftera (`native_draft.rs:742-818`). Wiersze bloku nie są dopisywane (`native_draft.rs:1335-1338`). Długość historii ogranicza okno lub `context_length` (`lib.rs:358-360,664-674`).
- **Readout.** Pełny słownik celu: lm_head i embedding celu. Zredukowany słownik `d2t` jest odrzucany (`lib.rs:88,426-435`).
- **DFlash2 vs DFlash:**
  - dynamiczna konwolucja grupowa K=2 wokół atencji i FFN (`M/engine/families/contracts/src/draft.rs:84-107`);
  - ścieżka kandydatów: top-16 na wiersz, po czym sekwencyjny `draft_path_step` z biliniowym członem rangi 256 (poprzednik → następnik) zamiast niezależnego argmax (`draft.rs:109-124`; `M/engine/kernels/kernels/cuda/draft_path_step.cu:1-38`).
- **DSpark.** Ma głowę Markowa i głowę pewności, która może przycinać sufiks (`draft_confidence.cu:26-28`), ale w serwowaniu próg jest 0, więc ta głowa jest wyłączona (`native_draft.rs:16-19`). Długość wyznacza tylko kontroler.
- **Koszt draftu.**
  - Jeden zamknięty graf natywny na transakcję (wstrzyknięcie + przejście bloku) (`native_draft.rs:1-21`), plus 7 drobnych launchy `draft_path_step` w DFlash2 (`native_draft.rs:1781-1808`).
  - Drafter 27B w Q8_0 to 2.06 GB (`R3/build/downloads.tsv`), czyli ~2.2 ms czytania na 3090 [INFERENCE: 936 GB/s].
- **MTP u nich.** `MAX_DRAFT_PROPOSALS = 8`, drabinka {1,3,7,8} (`capabilities.rs:9`, `options.rs:519-524`). W katalogu Qwen3.8-27B używa DFlash2, nie MTP (`D/models/speculative-methods.md:18`).

### 1.2 Kontroler szerokości (adaptive draft budget)
Domyślny, gdy nie podano `--mtp-proposals` ani `--draft-budget` (`M/engine/src/options.rs:280-290`). Szczegóły w `M/engine/generation/src/draft_control.rs`:
- **Drabinka szerokości.** `draft_ladder(w)` zostawia szerokości k, dla których k+1 jest potęgą dwójki, plus w: 15 → {1,3,7,15}, 7 → {1,3,7}. Do tego zawsze 0 (`capabilities.rs:29-42`, `draft_control.rs:336-343`). Uzasadnienie: weryfikacja, która nie wypełnia klasy wierszy, płaci za niewykorzystane wiersze (`D/inference/engine/speculative-generation.md:305-312`).
- **Akceptacja per głębokość.** `right[k]` to P(blok poprawny do głębokości k). Start 1.0, więc pierwsza runda jest najszersza. Aktualizacja: średnia, potem EMA z `MEMORY = 0.25` (`:28,509-517`). Wartości są monotonicznie przycinane do minimum płytszych głębokości (`:303-312`).
  - **Ocenia się każdą wydraftowaną propozycję, także niezweryfikowaną**, porównaniem z tokenami zatwierdzonymi w kolejnych rundach (`:8-14,520-551`).
  - Stan jest wspólny dla requestów jednego loadu (`:262-275`).
- **Koszty.**
  - EMA `COST_MEMORY = 0.25` czasu urządzenia każdego launchu, osobno dla draftu (wg liczby wygenerowanych) i weryfikacji (wg wierszy), per (klasa kontekstu = `next_power_of_two(pozycja)`, liczba sekwencji) (`:29-58,372`).
  - Niezmierzony launch kosztuje co najmniej tyle, ile zmierzony mniejszy, także przy krótszym kontekście; większy launch nic nie mówi o mniejszym (`:60-69,86-120`).
- **Wybór.**
  - Maksimum `(1 + Σ right[..v]) / (draft(g) + verify(v+1))` po parach g ≥ v; przy remisie wygrywa węższa (`:352-366`).
  - Szerokość, która przestała być najszybsza, jest jeszcze przez jakiś czas generowana („kept rounds”, do 100).
  - „Looks”: `LOOK_SHARE = 0.01` czasu dekodowania na rundy szersze. Look odpala też po serii pełnych akceptacji; próg serii jest połowiony po trafieniu i podwajany po chybieniu, przenoszony między requestami (`:31-32,413-457,535-543`).
  - Po drafcie `verify()` wybiera ponownie v ≤ g, więc mogą wydraftować 15 i zweryfikować 7 (`:496-506`).
- **Dowód działania** (sweep T=1, `R5/` i `R3/` xbench, kolumna „propozycje/krok” w §2.3): 3090 pl-proza 1.81 → pl-kod 6.75; 9B pl-proza 0.23 (19 ms/krok, prawie plain).

### 1.3 Akceptacja, próbkowanie, rollback
- **Akceptacja.** Dokładne dopasowanie prefiksu do tokenów próbkowanych przez cel, bez rejection sampling z resztą rozkładu (`M/engine/generation/src/acceptance.rs:7-20`, `round.rs:276-289`; kontrakt `D/inference/engine/speculative-generation.md:202-208`).
- **Sprzężone próbkowanie.**
  - `proposal_selects` daje każdej propozycji ten sam `seed` i `position`, co próbka celu dla tej pozycji. Komentarz w kodzie: „identical draft and target distributions select identical tokens” (`M/engine/generation/src/lib.rs:745-779`).
  - Sampler celu to Gumbel-max z szumem Philox4x32-10 na liczniku (token, pozycja…) (`readout.seismic:325-329`).
- **KV.** Wiersze poza przyjętym prefiksem po prostu nie są publikowane; nie ma kopiowania (`M/engine/executor/src/domain/reconcile.rs:81-117`).
- **Gated DeltaNet.** „Taśma” (u = innowacja, k, decay) per wiersz spekulacji. Następny krok najpierw aplikuje rank-1 `S ← dS + ukᵀ` dla przyjętych wierszy, bez drugiego przejścia (`M/engine/kernels/kernels/recurrent.seismic:9-29,318-330`). To ta sama idea co nasz S4 GDN-lag replay (wiki `kernele/gdn-replay.md`), więc nie ma tu nic nowego do przejęcia.

### 1.4 Kernele weryfikacji
- **Projekcje.**
  - Swap-AB GEMV na `mma.sync.m16n8k16`: 16 wierszy wag to operand A, wiersze aktywacji to kolumny N=8 (NB=1 dla M ≤ 8, NB=2 dla M ≤ 16).
  - Wagi czytane raz, kody wchodzą do MMA jako dokładne liczby całkowite.
  - **Wynik wiersza nie zależy od M, więc M = 1..16 są bitowo identyczne z M = 1** (`M/engine/kernels/kernels/cuda/lib/projection/projection.cuh:1-35`).
  - Klasy wierszy: 1, 2, 4, 8, 16, 32, potem wielokrotności 64 (`M/engine/batching/src/classes.rs:8-24`).
  - Wagi są przepakowane przy ładowaniu do układu `mma16`, co widać w logu: `q4k@mma16`, `iq4g32@mma16`, `q8g32s@mma16` (`R3/logs/qwen.mag.6.log`).
- **Atencja.**
  - Do 8 wierszy używają entry dekodowania; powyżej 8 entry prefill flash (`M/engine/executor/src/operators/attention/graph.rs:287-293`).
  - Entry prefill czyta historię raz na kafel wierszy (token × głowa).
  - W entry dekodowania forma wektorowa ma siatkę (KV, PARTS, M), więc każdy wiersz czyta K/V osobno. Forma MATRIX=1 współdzieli kafle, a tuner ustawia ją jako punkt startowy dla wierszy weryfikacji na CUDA (`M/engine/executor/src/native/tuning/attention.rs:84-114`, wg MagVerifyKern).
  - KV domyślnie `AffineK8V4` (`M/engine/src/options.rs:121`), ~1.75 B/element [INFERENCE] wobec 0.5625 B naszego q4_0.
- **Readout.**
  - 16 wierszy przez `readout_head_rows_gemv16`, głowa czytana raz.
  - Do 4 wierszy na CUDA działa „certyfikowany progresywny readout”: najpierw 4-bitowy widok bitplanów Q8_0, potem doprecyzowanie ocalałych; dokładny także przy próbkowaniu, bo zna szum Gumbela (`readout.seismic:300-323`; `M/engine/executor/src/programs/graph/readout.rs:103-113`).
- **Launch.**
  - Jawne grafy CUDA z krawędziami PDL; kernel ładuje pierwsze wagi przed `griddepcontrol.wait` (`M/seismic/runtime/src/native/cuda_prelude.cuh:143-173`, wg MagVerifyKern).
  - W logu startu jest 91 702 zapieczętowanych grafów w 2461 klasach (`R3/logs/qwen.mag.6.log`).
  - Brak persistent megakernela.
- **`--lookahead`.** Kolejkuje następny krok plain decode przed odczytem hosta i działa tylko dla jednowierszowego plain decode, nie dla weryfikacji (`M/engine/executor/src/domain/lookahead.rs:1-78`).
- **Nakładanie draftu następnej rundy na weryfikację nie jest zaimplementowane;** istnieje tylko jako cel w dokumentacji (`M/docs/kernels/drafting-and-verification.md:100-102`). Runda to około 2 submisje i 2 synchronizacje hosta (`M/engine/generation/src/mtp.rs:517-575,642`).

### 1.5 Autotune, prefill, cache
- **Autotune.**
  - Budżet 60 s; przestrzeń: KSPLIT, ROTATE, INT8, a dla atencji PARTS/WARPS/MATRIX/… Punkty pomiarowe: wiersze 1–512 × kontekst 0–64k (`M/engine/executor/src/native/tuning/mod.rs:204-211,329-331`).
  - W release: `"searched":67,"stored":0,"canonical_fallbacks":67`; „refused … reason: seconds” (`R3/logs/qwen.mag.first.tuning.jsonl`, eventy `budget`/`concluded`). Każdy `searched …` w logu kończy się „serving 1.000 of the defaults” (`R3/logs/qwen.mag.first.log`).
  - Pierwsze ładowanie 27B trwa 51.5 s, kolejne 9–10 s (`R3/servers.jsonl`).
- **Prefill.**
  - Granty po 512 tokenów, `decode_tokens = 32` (`M/engine/src/options.rs:25-31`).
  - Drafter w prefillu zapisuje tylko swój stan (`M/docs/kernels/drafting-and-verification.md:26-57`). U nas to samo robi T3 (0041, „warstwa MTP liczy tylko K/V dla wierszy promptu”, wiki `latki/latki-spekulacji.md`).
  - **Prefill mamy szybszy:**
    - 3090 27B: 2k 915 vs ~1080 t/s, 14k 907 vs 1131 t/s, 64k 86.4 vs 72.4 s;
    - 5060 Ti 9B: 64k 31.1 vs 27.3 s, 14k 5.47 vs 4.91 s (`R3/x`, `R5/x` wiersze `ttft` i `copy`).
- **Prefix cache.** Wznowienie od najgłębszego dokładnego punktu, z historią draftera w prefiksie (`D/inference/engine/prefix-cache.md`, `speculative-generation.md:148-155`). U nas jest odpowiednik (cache promptu + GDN replay), więc tu nie ma przewagi.

## 2. Rozkład zmierzonej wygranej

Definicje (sprawdzone na obu silnikach): kroki = n − accepted, tok/krok = n / kroki, ms/krok = ms / kroki, propozycje/krok = draft / kroki. Dla pad.cu u Magnitude 1024 / (1024 − 952) = 14.22, zgodnie z `tok_step` w pliku. Jedna runda na silnik.

### 2.1 Zbiorczo (suma żądań)

| GPU | model | workload | silnik | tok/krok | ms/krok | propozycje/krok | akcept. propozycji | t/s |
|---|---|---|---|---|---|---|---|---|
| 3090 | Qwen3.8-27B Q4_K_XL | code-edit (4 pliki) | fork MTP4 | 4.91 | 46.6 | 3.97 | 0.984 | 105.3 |
| 3090 | 〃 | 〃 | Magnitude DFlash2 | 7.14 | 50.3 | 6.89 | 0.891 | 141.9 |
| 3090 | 〃 | copy 64k | fork | 4.51 | 64.7 | 3.89 | 0.904 | 69.7 |
| 3090 | 〃 | 〃 | Magnitude | 7.31 | 91.2 | 6.44 | 0.980 | 80.2 |
| 5060 Ti | Qwen3.5-9B Q4_K_XL | code-edit | fork | 4.81 | 20.1 | 3.97 | 0.959 | 239.3 |
| 5060 Ti | 〃 | 〃 | Magnitude DFlash | 13.17 | 35.3 | 14.29 | 0.852 | 372.9 |
| 5060 Ti | 〃 | copy 64k | fork | 4.53 | 35.2 | 3.88 | 0.909 | 128.6 |
| 5060 Ti | 〃 | 〃 | Magnitude | 8.26 | 47.2 | 9.95 | 0.729 | 174.8 |

| GPU | workload | speedup Mag/fork | czynnik tok/krok | czynnik ms/krok | t/s Magnitude przy naszym ms/krok |
|---|---|---|---|---|---|
| 3090 27B | code-edit | 1.35× (bez lazy.py: 1.49×) | 1.45× (bez lazy.py: 1.60×) | 0.93× | 153 |
| 3090 27B | copy 64k | 1.15× | 1.62× | **0.71×** | 113 |
| 5060 Ti 9B | code-edit | 1.56× | 2.74× | **0.57×** | 656 |
| 5060 Ti 9B | copy 64k | 1.36× | 1.82× | 0.75× | 234 |

Wniosek: **we wszystkich czterech przypadkach całą przewagę daje tok/krok, a czas kroku działa na ich niekorzyść** (×0.57…×0.93). Gdybyśmy mieli ich tok/krok przy naszym czasie kroku, wygrywalibyśmy wszędzie.

### 2.2 Per żądanie, Qwen3.8-27B na 3090 (`R3/x/xbench.jsonl`)

| silnik | element | prompt tok | propozycje | przyjęte | kroki | propozycje/krok | tok/krok | ms/krok | t/s | prefill s |
|---|---|---|---|---|---|---|---|---|---|---|
| fork | moby-dick/0 @64k | 64145 | 212 | 201 | 55 | 3.85 | 4.65 | 64.9 | 71.5 | 72.1 |
| fork | moby-dick/1 @64k | 64407 | 227 | 198 | 58 | 3.91 | 4.41 | 64.8 | 67.9 | 72.5 |
| fork | pad.cu | 1792 | 828 | 816 | 208 | 3.98 | 4.92 | 46.5 | 105.7 | 1.7 |
| fork | ngram-cache.h | 1187 | 828 | 815 | 209 | 3.96 | 4.90 | 46.3 | 105.8 | 1.1 |
| fork | sampling.h | 1527 | 833 | 814 | 210 | 3.97 | 4.88 | 46.4 | 104.9 | 1.4 |
| fork | lazy.py | 3148 | 824 | 816 | 208 | 3.96 | 4.92 | 47.0 | 104.7 | 2.7 |
| Mag | moby-dick/0 @64k | 64145 | 223 | 221 | 35 | 6.37 | 7.31 | 90.9 | 80.4 | 86.5 |
| Mag | moby-dick/1 @64k | 64407 | 228 | 221 | 35 | 6.51 | 7.31 | 91.5 | 79.9 | 86.4 |
| Mag | pad.cu | 1792 | 897 | 894 | 130 | 6.90 | 7.88 | 50.2 | 157.0 | 1.9 |
| Mag | ngram-cache.h | 1187 | 897 | 894 | 130 | 6.90 | 7.88 | 49.6 | 158.9 | 1.3 |
| Mag | sampling.h | 1527 | 911 | 892 | 132 | 6.90 | 7.76 | 50.0 | 155.3 | 1.6 |
| Mag | lazy.py | 3148 | 1250 | 842 | 182 | 6.87 | 5.63 | 51.2 | 109.9 | 3.3 |

Arytmetyka:
- **pad.cu: 7.88 / 4.92 = ×1.60 tok/krok i 46.5 / 50.2 = ×0.93 krok, razem ×1.49** (157.0 / 105.7).
  - Magnitude weryfikuje 6.90 propozycji na krok, czyli praktycznie cały blok 7 przy 8 wierszach. Przyjmuje 99.7% (894/897), więc **siedzi na swoim suficie, tak jak my na naszym** (816/828 = 98.6%, sufit 5).
  - Różnica między nami to po prostu 8 vs 5 tokenów z jednego przejścia wag. Kosztuje ich +3.7 ms (+8%) na kroku, łącznie z draftem.
- **lazy.py:** akceptacja spada do 0.67 (842/1250), tok/krok do 5.63, wynik 1.05× nad nami.
  - Prompt (3148 tokenów) jest dłuższy niż okno DFlash2 2048, a odpowiedź to kopia pliku (prefix_frac 1.0) [INFERENCE: przyczyną jest okno, `interpretation.rs:553-598`].
  - Nasz MTP ma pełną atencję i trzyma 4.92.
- **copy 64k:** ×1.62 tok/krok, ale krok 91 vs 65 ms (×0.71), razem 1.15×.
  - Ich krok rośnie od 2k do 64k o +41 ms, nasz o +18 ms.
  - Gdyby mieli nasz czas kroku, robiliby 113 t/s. Gdybyśmy my mieli ich tok/krok przy naszym kroku 5-wierszowym, robilibyśmy 113 t/s, ale szerszy krok u nas też podrożeje (§3.2).

### 2.3 Sweep T=1 (nowe pisanie), per prompt

| GPU/model | prompt | Mag t/s | fork t/s | Mag tok/krok | fork tok/krok | Mag ms/krok | fork ms/krok | Mag propozycje/krok |
|---|---|---|---|---|---|---|---|---|
| 3090 27B | pl-proza | 30.1 | **44.9** | 1.32 | 1.97 | 44.0 | 44.0 | 1.81 |
| 3090 27B | pl-tech | 52.9 | **67.4** | 2.48 | 2.99 | 46.9 | 44.4 | 4.57 |
| 3090 27B | pl-kod | **109.2** | 79.3 | 5.29 | 3.52 | 48.4 | 44.4 | 6.75 |
| 3090 27B | en-chat | **60.6** | 58.2 | 2.87 | 2.61 | 47.3 | 44.9 | 5.47 |
| 3090 27B | en-tech | **70.7** | 65.4 | 3.39 | 2.97 | 47.9 | 45.4 | 5.86 |
| 3090 27B | en-code | **86.5** | 71.2 | 4.18 | 3.24 | 48.3 | 45.6 | 6.36 |
| 3090 27B | mediana | 65.7 | 66.4 | | | 47.6 | 44.6 | |
| 5060 Ti 9B | pl-proza | 55.0 | **86.7** | 1.00 | 1.71 | 18.3 | 19.8 | 0.23 |
| 5060 Ti 9B | pl-kod | 56.5 | **119.9** | 1.25 | 2.56 | 22.1 | 21.3 | 1.55 |
| 5060 Ti 9B | en-code | 105.2 | **148.5** | 3.06 | 2.91 | 29.1 | 19.6 | 5.79 |
| 5060 Ti 9B | mediana | 68.2 | 121.0 | | | 24.9 | 20.5 | |

Wnioski:
- Na 27B DFlash2 z kontrolerem bije nasze MTP4 na kodzie (+38% pl-kod, +21% en-code) i lekko na EN (+4…+8%). Przegrywa na polskiej prozie i tech (−22…−33%). Krok jest u nich tylko o 0–4 ms dłuższy przy ~1.5–1.7× więcej propozycji.
- Na 9B (DFlash v1, blok 16) przegrywają wszędzie poza en-tech/en-code, gdzie wychodzi remis w tok/krok. Ich krok 25–29 ms przy 4–6 propozycjach wobec naszych 20 ms, więc krótkie bloki są u nich drogie.

## 3. Co dałby nasz silnik przy bloku 8 / 12 / 16 (XTX, Qwen3.8-27B)

### 3.1 Krótki kontekst (d=2048)
Założenia:
- krok MTP4 = 27.74 ms = weryfikacja W5 ≈ 24.1 ms + łańcuch MTP 3.62 ms (`15b-spekulacja-frontier.md:255`);
- ΔV(w) z `~/qwen-opt/k4/vcost_qwen-k4b.csv` (llama-bench, w wierszy): V5 27.85, V8 30.33, V12 33.05, V16 34.97 ms;
- łańcuch MTP kosztuje +0.65 ms na poziom ponad 4 (T1, wiki `eksperymenty/2026-10-14-t1-t2-draft.md`);
- ogon z lookupu kosztuje 0 ms GPU [INFERENCE: hash na CPU];
- akceptacja geometryczna z p warunkowym na pozycję. Nasze code-edit 3.92 przyjętych na 4 propozycje daje p ≈ 0.99.

| wariant | propozycje | wiersze | krok ms | tok/krok (p MTP 0.99 / ogon 0.99) | t/s | vs dziś | tok/krok (ogon 0.95) | t/s | vs dziś |
|---|---|---|---|---|---|---|---|---|---|
| MTP4 (dziś) | 4 | 5 | 27.74 | 4.90 | 177 | 1.00× | 4.90 | 177 | 1.00× |
| MTP4 + ogon | 7 | 8 | 30.22 | 7.73 | 256 | **1.45×** | 7.50 | 248 | **1.41×** |
| MTP4 + ogon | 11 | 12 | 32.94 | 11.36 | 345 | 1.95× | 10.41 | 316 | 1.79× |
| MTP4 + ogon | 15 | 16 | 34.87 | 14.85 | 426 | 2.41× | 12.77 | 366 | 2.07× |
| łańcuch MTP | 7 | 8 | 32.17 | 7.73 | 240 | 1.36× | – | – | – |
| łańcuch MTP | 15 | 16 | 42.02 | 14.85 | 354 | 2.00× | – | – | – |

- Przy p MTP 0.95 i ogonie 0.85 (słabsza kopia): 8 wierszy daje 1.28×, 16 wierszy 1.47× (`16i-magnitude/results.txt`).
- Kontrola z pomiaru serwera po T1: łańcuch 8 dawał 37.2 ms, a n=4 29.36 ms (+1.6 ms/poziom). To drożej niż model 0.65 + ΔV (~0.6/wiersz), bo pomiar był przed PM4 i liczy pełny koszt kolumny w serwerze ~1 ms. Wiersze ogona kosztują wtedy ~1 ms, a nie 0.6, i 16 wierszy kosztowałoby ~+11 ms zamiast +7.1. Przy p = 0.99 nadal daje to ~1.9× [INFERENCE].
- **Ten sam sufit 8 wierszy, który Magnitude ma na 27B, daje nam z ogona ~1.4×,** czyli ich +49% na code-edit 3090. Do tego nasz krok jest szybszy.
- Łańcuch MTP do 8 jest gorszy od ogona (1.36× vs 1.45×), ale nie wymaga kopiowalnego kontekstu. Na kodzie bez kopii (en-code) jego akceptacja głębokich pozycji jest jednak niska (T1: n=8 przegrywa na spec_sweep, 96.7 vs 102.7).

### 3.2 Długi kontekst (64k), model kafli FA [INFERENCE]
- Nasz kvq czyta KV raz na kafel 16 wierszy (token × głowa GQA), czyli `ceil(6·w/16)` kafli (`15b-spekulacja-frontier.md:20`).
- Kalibracja na 3090: +18.3 ms przy 2 kaflach (W5, 46.5 → 64.8 ms).

| wiersze | kafle | krok ms (est.) | tok/krok @0.99 | t/s |
|---|---|---|---|---|
| 5 | 2 | 64.8 | 4.90 | 76 |
| 8 | 3 | 78.1 | 7.73 | 99 |
| 12 | 5 | 100.9 | 11.36 | 113 |
| 16 | 6 | 113.3 | 14.85 | 131 |

- Na kopii 64k szerszy blok nadal się opłaca, ale już tylko ~1.3× przy 8 wierszach.
- Na CUDA ten model może nie obowiązywać: upstream FA dla KV q4_0 przy n ≥ 2 na Ampere konwertuje K/V do f16 (wiki `kernele/fattn-kvq.md`, „Luka na CUDA”). Koszt na 3090 jest do zmierzenia (E-C1).
- **Kontroler musi mieć koszt per klasa kontekstu, tak jak Magnitude.**

## 4. Techniki do przejęcia: ranking

Kolumny zysku: (a) code-edit/copy, (b) normalne pisanie (spec_sweep PL/EN T=1).

| # | technika (źródło u nich) | (a) zysk | (b) zysk | koszt (osobodni) | ryzyko | bezstratność / bit-exact | minimalny eksperyment (XTX, Qwen3.8-27B) | kill |
|---|---|---|---|---|---|---|---|---|
| 1 | **Szerszy blok z darmowych draftów: MTP4 + ogon lookup do 8 wierszy** (u nich to samo daje blok DFlash2 8; u nas drafter to lookup) | **+35…45%** (§3.1); kopia 64k ~+30% | 0 (ogon się nie włącza) | w toku (XtxLookupTail), ~2 | niskie | drafty, weryfikacja bez zmian, więc bezstratne; W ≤ 8 mieści się w BITEXACT (n_max ≤ 7, `15b:265`) | `arm.sh` z `LLAMA_SPEC_LOOKUP=2 LLAMA_SPEC_LOOKUP_W=8`, zestaw `mvs` z `~/qwen-opt/lookup/copy_prompts.json` + spec_sweep 6×3 T=1 | code-edit < +20% t/s albo spec_sweep < −0.5% |
| 2 | **Kontroler szerokości w stylu Magnitude** (`draft_control.rs`): drabinka wierszy {5, 8, 16} (MTP4 + ogon 0/3/11), akceptacja per głębokość z oceną niezweryfikowanych pozycji ogona, koszt per (wiersze, klasa kontekstu 2^k), looks 1% | umożliwia 16 wierszy tam, gdzie się opłaca: +15…+45% ponad #1 na krótkim kontekście; chroni długi kontekst | 0 (ogon 0) | 3–4 (część infrastruktury jest w T2: `common/speculative.cpp:1392-1594`, czas per szerokość, graf per szerokość) | średnie: przełączanie szerokości kosztuje ~1.6 ms bez cache grafu (T2) | bezstratne; poza BITEXACT tekst greedy zależy od szerokości (wsadowa niezmienniczość); w BITEXACT wymaga bit-exact wszystkich szerokości z drabinki (#5) | sekwencja mvs → pl-proza → copy 32k w jednej sesji; kontroler vs stałe W8 i W16 | gorzej niż najlepsza stała szerokość per segment o > 3% albo regres spec_sweep > 0.5% |
| 3 | **Sprzężone próbkowanie draftu** (`generation/src/lib.rs:745-779`, Gumbel-Philox `readout.seismic:325-329`): draft wybiera token z szumem celu dla tej samej pozycji | ≈0 (T=0 i kopia) | MTP: ≤ +2…6% (luka T0 vs T1: 86.3 vs 81.1); DFlash: do +26% (71.9 → 90.6) | 2–3: sampler celu musi stać się Gumbel-max kluczowany (seed, pozycja, token), a głowa MTP musi stosować ten sam łańcuch (temp/top-k/top-p/min-p) | średnie: trzeba zmienić sampler (inny strumień RNG niż dziś, więc inne teksty przy tym samym seedzie) | bezstratne (próbka celu nie zależy od draftów); w BITEXACT T>0 daje nawet wynik identyczny ze spekulacją i bez, o ile logity są bitowe | spec_sweep T=1 6×3, przeplatane A/B; dodatkowo zestaw odłożony (wiki `metody/zestaw-odlozony.md`) | < +2% t/s na spec_sweep T=1 i < +10% dla DFlash2 |
| 4 | **DFlash2 jako drugi drafter do kodu/EN, wybierany przez kontroler #2** (z #3) | +0…10% ponad #1 (kopię łapie już ogon) | kod +20…38% (3090: pl-kod 109 vs 79, en-code 86.5 vs 71.2); PL proza: 0 przy dobrym kontrolerze, inaczej −33% | 5–8 (dwa drafty w jednym slocie, VRAM +1.1 GB Q4_K_M, krok +5 ms wg naszych pomiarów, `drafter-dflash.md`) | wysokie | bezstratne; okno 2048 psuje kopię długich plików (`lazy.py`) | najpierw sam DFlash2 z #3 i ladder {0,3,7} na spec_sweep; dopiero potem hybryda | DFlash2 + #3 < MTP4 na en-code/pl-kod T=1 → zamknąć |
| 5 | **Weryfikacja 1..16 kolumn bitowo niezależna od M** (`projection.cuh:16-18`, swap-AB MMA) | warunek W=16 w BITEXACT | – | HIP: 3–5 (K4 WMMA 9–16 + MMVQ 2–8 muszą mieć tę samą kolejność redukcji co N=1); CUDA: port gemv16 dla 3090/5060 Ti, 5–8 | średnie | definiuje bit-exact | test kolumnowy jak tqLLM `quant.cu:1392` (15b:133-135) dla 1..16 kolumn | brak bitowej równości po 3 dniach → W16 tylko poza BITEXACT |
| 6 | **Atencja weryfikacji: jedno czytanie KV dla ≤ 16 wierszy** (u nich prefill-flash dla > 8 wierszy, `attention/graph.rs:287-293`; nasz plan #4 w 15b:267) | długi kontekst: W16 @64k z 113 do ~80 ms [INFERENCE], kopia 64k +40% | +1…3% przy długim kontekście (W5: 2 → 1 kafel) | 2–3 (HIP kvq) | niskie–średnie | kolejność sumowania per kafel bez zmian, więc bitowe [INFERENCE] | llama-bench `-p 5,8,12,16 -d 2048,32768,65536` przed i po | V16 − V5 @32k > 12 ms po zmianie |
| 7 | **PDL w grafach** (`cuda_prelude.cuh:143-173`): prefetch wag przed `griddepcontrol.wait` | +2…5% wszędzie [INFERENCE] | +2…5% | HIP: PM4-PDL (raport 15a); CUDA: atrybut PDL w ggml-cuda | średnie (zakleszczenia) | bitowe | mikrobench X1 z 15a | brak zysku ≥ 1% na LFM tg128 |
| 8 | Certyfikowany progresywny readout lm_head (`readout.seismic:300-323`) | ~1–2% | ~1–2% (lm_head Q6_K ≈ 1.04 GB z 17.5 GB [INFERENCE]) | 4–6, wymaga Gumbel-max z #3 | średnie | dokładne z konstrukcji | – | robić dopiero po #3 |
| ✗ | ich autotune | 0 | 0 | – | – | – | release: 67/67 domyślnych | – |
| ✗ | KV `AffineK8V4` | – | jakość lepsza od q4_0 [INFERENCE] | – | – | – | 3× więcej bajtów niż q4_0, a u nich to powoduje OOM 64k na 16 GB | – |
| ✗ | taśma GDN | 0 | 0 | – | – | mamy S4 (`gdn-replay.md`) | – | – |
| ✗ | DSpark z przycinaniem pewnością | – | – | – | – | – | u nich wyłączone (`native_draft.rs:16-19`); nasz `p_min` / `p_cum` też nic nie dał | – |

## 5. Ocena szczegółowa

### 5.1 Adaptacyjna długość (krótko na prozie, długo na kopii)
- **Dlaczego u nich działa, a nasza T2 nie dała nic:**
  - T2 (0039) była testowana tylko na spec_sweep (czat/proza) i tylko z łańcuchem MTP, którego głębsze poziomy kosztują ~1.6 ms każdy i rzadko trafiają. Wynik 103.6 vs 102.7 t/s (`eksperymenty/2026-10-14-t1-t2-draft.md`).
  - Nie było w niej taniego długiego draftera ani workloadu kopii.
  - U Magnitude szerszy blok kosztuje tylko wiersze weryfikacji, bo DFlash jest jednym przejściem. U nas taki koszt ma tylko ogon z lookupu.
- **Różnice w samym kontrolerze, które trzeba skopiować do T2:**
  1. Akceptacja per głębokość z oceną **niezweryfikowanych** propozycji przez porównanie z późniejszymi zatwierdzonymi tokenami.
     - Dla ogona lookupu ocena jest darmowa: ogon można zawsze wyliczyć na CPU i porównać z tokenami, które potem padną. Głębokości 8–16 są więc obserwowane bez kosztu GPU, czego nie ma przy MTP.
     - Shadow-log XtxLookupTail (`LLAMA_SPEC_LOOKUP=1`) już to liczy.
  2. Szerokości tylko z drabinki wypełniającej klasy wierszy: 5 (dziś), 8, 16. Nie 6, 7, 9 itd., bo każdy graf szerokości jest osobny (PM4/T2) i przełączenie kosztuje.
  3. Koszt per (wiersze, klasa kontekstu 2^k), monotoniczny i bez prognozy. Bez tego W16 przy 64k zabije kopię (§3.2).
  4. Looks: 1% czasu oraz seria pełnych akceptacji z progiem /2 po trafieniu i ×2 po chybieniu, przenoszonym między requestami.
  5. Brak kalibracji pewnością głowicy. W T2 kalibracja per bin pewności dała 87 t/s, czyli wypadła negatywnie.
- **Ryzyko.** Kontroler współdzieli stan między requestami jednego loadu (`draft_control.rs:262-275`), więc po przełączeniu rodzaju ruchu potrzeba kilku rund adaptacji. To koszt rzędu 1 rundy na szerokość na klasę kontekstu (`speculative-generation.md:376`).

### 5.2 DFlash (blok równoległy) vs nasz MTP + ogon lookup

| cecha | DFlash2 (Magnitude) | MTP4 + ogon (my) |
|---|---|---|
| sufit tok/krok | 8 (27B), 16 (9B) | 5 + ogon do 16 |
| koszt draftu | 1 przejście 2 GB Q8_0 + 7 path-stepów; u nas DFlash2 kosztował ~+5 ms kroku | MTP 3.62 ms (IQ4_XS), ogon 0 ms |
| kopia z kontekstu | tylko w oknie 2048 (lazy.py 5.63 tok/krok) | pełna atencja MTP (P(MTP d1 \| lookup) = 0.968, `15b:11`) + dokładny lookup sufiksu |
| nowy kod bez kopii | **lepszy** (3090 pl-kod 5.29 vs 3.52 tok/krok) | ogon nie pomaga |
| polski | trening bez PL (§5.4), pl-proza 1.00–1.32 tok/krok | MTP Qwena + nasz słownik 64k: 1.71–1.97 |
| T=1 | sprzężone próbkowanie | dziś greedy draft (luka 2–6%) |
| bit-exact | – | W ≤ 8 już mieści się w BITEXACT |

Wniosek: dla rynku PL i code-edit/agentów **MTP4 + ogon + kontroler** to lepszy pierwszy krok. Pokrywa kopię, czyli tam, gdzie przegrywamy 1.4–1.7×, i nie rusza polskiego. DFlash2 to osobny projekt pod EN/kod (+20…38% na 3090 przy T=1) i ma sens dopiero ze sprzężonym próbkowaniem (#3) i kontrolerem wybierającym drafter.

### 5.3 Sztuczki weryfikacji
- **Nie wyjaśniają ich przewagi.** Ich 8 wierszy na 3090 kosztuje 48–50 ms wobec naszych 44.4–46.5 ms przy 5 wierszach (§2). Ich własna tabela testowa daje V16 = 2.5× V1 przy 4k (`draft_control/tests.rs:49-63`), a nasza krzywa V16/V1 = 1.27 (`vcost_qwen-k4b.csv`).
- **Warte przejęcia są trzy rzeczy:**
  - bitowa niezależność GEMV od liczby wierszy, z konstrukcji (#5);
  - jedno czytanie KV przez kafle token × głowa dla > 8 wierszy (#6);
  - PDL (#7).
- **Gdzie u nas jest dziura: CUDA na 3090/5060 Ti.** Weryfikacja powyżej 8 kolumn przechodzi tam na MMQ (`15b:266`), a FA z KV q4_0 konwertuje K/V (`kernele/fattn-kvq.md`). Przed obietnicą W16 na NVIDIA trzeba to zmierzyć (E-C1).

### 5.4 Polski: dlaczego ich drafter zawodzi
- **Dane treningowe.** DFlash: ~800K próbek z Nemotron Post-Training v2 + CodeAlpaca, odpowiedzi regenerowane przez cel, sekwencje ≤ 3072 tokenów (arXiv 2602.06036, §5 „Datasets”, A.1). Nemotron v2: „English, German, Italian + 3” (karta HF), bez polskiego.
  - Drafter 27B w GGUF ma `general.organization = z-lab`, `source.url = huggingface.co/z-lab/Qwen3.8-27B-DFlash2` (nagłówek `~/models/draft/Qwen3.8-27B-DFlash2-Q4_K_M.gguf`, odczyt MagDflashFam).
- **Architektura** [INFERENCE]: blok dwukierunkowy przewiduje pozycje łącznie, bez widzenia poprzednich propozycji. To działa na przewidywalnym EN/kodzie, a na fleksyjnym polskim mnoży błędy. DFlash2 łagodzi to selektorem rangi 256 tylko w obrębie top-16.
- **Skutek z kontrolerem:** 9B pl-proza 0.23 propozycji/krok, 1.00 tok/krok, czyli efektywnie plain 55.0 t/s (krok 18.3 ms). Bez kontrolera byłoby gorzej niż plain.
- **Nasza przewaga.** Głowica MTP Qwena trenowana na rozkładzie pretrainingu plus pilot MTP-PL (raport 11) dają pl-proza 1.71–1.97 tok/krok przy T=1. Ta przewaga zniknie, jeśli ktoś wytrenuje DFlash z polskimi danymi; Magnitude tego nie robi, bo ich drafterów dostarcza z-lab.

## 6. Interakcje z bit-exact (`LLAMA_SPEC_BITEXACT`)
- **Ogon lookupu (#1)** zmienia tylko drafty, więc wynik jest bezstratny. W BITEXACT tekst jest identyczny, o ile szerokość weryfikacji należy do zbioru bitowo niezależnego. Dziś to n_max ≤ 7, czyli 8 wierszy (`15b:265`). **W8 działa od ręki, W16 wymaga #5.**
- **Kontroler (#2)** zmienia szerokość per krok. Poza BITEXACT greedy może się różnić przy remisach (wiki `lekcje/determinizm-fma.md`: „weryfikacja batcha liczy inaczej niż N=1”). W BITEXACT drabinka musi być ograniczona do szerokości bitowych.
- **Sprzężone próbkowanie (#3)** wymaga RNG kluczowanego pozycją. W BITEXACT przy T>0 daje silniejszą gwarancję niż dziś: tekst ze spekulacją równy tekstowi bez niej przy każdej temperaturze, jeśli logity są bitowe. Magnitude ma tę samą gwarancję w kontrakcie: „Position-addressed RNG prevents batch membership or rejected work from changing a seeded request's random draws” (`speculative-generation.md:205-208`). Zmiana samplera zmienia jednak teksty względem obecnych md5 testów.
- **Magnitude samo nie jest bit-exact między szerokościami.** GEMV tak (`projection.cuh:16-18`), ale atencja przechodzi z entry dekodowania na entry prefill powyżej 8 wierszy (`attention/graph.rs:287-293`), a bramka tuningu to α = 8, nie bity (wiki `repo/magnitude.md`). To argument produktowy dla nas.

## 7. Co robią źle (pozycjonowanie)
- **Kwantyzacje.**
  - Brak IQ2_S, IQ2_XXS, Q2_K, Q4_1, IQ1_* (`M/engine/executor/src/planning/weights.rs:2086-2147`).
  - Qwen3.8-27B UD-Q3_K_XL, czyli jedyny 27B mieszczący się z 64k na 16 GB, w ogóle się u nich nie ładuje: „unsupported source encoding Iq2S” (`R5/logs/qwen.mag.1.log`).
  - Q3_K i IQ3_S rozszerzają do q6k (`weights.rs:2132`), co daje ~1.9× bajtów na tych tensorach.
- **Pamięć.** LFM2.5-24B przy 64k na 16 GB: OOM, „allocation requires 165675008 bytes; 89577882 bytes available” (`R5/logs/fail64k/lfm.mag.1.log`). Musieli zejść do 32k. KV K8V4 to ~3× nasze q4_0 [INFERENCE].
- **Brak HIP/ROCm.** AMD tylko przez Vulkan: „RDNA1 and newer run natively 32-wide” (`M/docs/compatibility.md:150`); ścieżki GCN niekwalifikowane (`:187-189`). **Uwaga: na XTX mogą działać przez Vulkan,** a my tego nie zmierzyliśmy (E-X5).
- **Polski i nowe pisanie.**
  - 9B: mediana sweepu 68.2 vs 121.0 t/s (−44%), pl-proza 1.00 tok/krok.
  - 27B: pl-proza 30.1 vs 44.9, pl-tech 52.9 vs 67.4.
- **Długi kontekst.** Krok +41 ms przy 64k (27B, 8 wierszy) vs nasze +18 ms. Prefill 64k: 86.4 vs 72.4 s (3090), 31.1 vs 27.3 s (5060 Ti).
- **Brak drafterów dla LFM 24B** („DSpark announced, unreleased”, `D/models/speculative-methods.md:26`). Plain 158 vs nasze 207 t/s na 5060 Ti (`R5/x`, sweep `lfm32k|mag` vs `lfm|fork`).
- **Pierwsze ładowanie** z 60 s tuningu, które w praktyce nic nie stroi (51.5 s vs 9–10 s kolejne).
- **Mocne strony, które trzeba nazwać uczciwie:** code-edit 1.35–1.56×, kod przy T=1 na 27B (+21…+38%), adaptacja bez strojenia przez użytkownika, Mac/Metal i Vulkan, desktop i integracje (wiki `repo/magnitude.md`).

## 8. Plan eksperymentów GPU (po zgodzie na GPU)

Kolejność: XTX (lokalnie), potem 3090 w chmurze, dopiero gdy jest kandydat. Każdy krok A/B jest przeplatany: restart serwera na ramię, `arm.sh`, 3 seedy. Zestawy: `mvs` (code-edit MagnitudeVs, `~/qwen-opt/lookup/copy_prompts.json` z `make_prompts.py:69-71`), copy (`prose-repeat`, `~/qwen-opt/magnitude/fixtures/prose-repeat.jsonl`) przy 8k/32k/64k, spec_sweep 6×3 T=1 oraz zestaw odłożony.

| id | cel | komenda / flagi | metryki | hipoteza | kill |
|---|---|---|---|---|---|
| E-X0 | krzywa kosztu szerokości przy kontekście (XTX) | `vcost.sh` z `-d 2048,32768,65536`, `-p 1..16`, `-ctk q4_0 -ctv q4_0` (rozszerzenie `~/qwen-opt/k4/vcost.sh`); powtórzyć z `LLAMA_SPEC_BITEXACT=1` | V(w, d) | V16 − V5 ≤ 12 ms przy 32k (`15b:290`) | > 12 ms → W16 tylko < 8k kontekstu; priorytet dla #6 |
| E-X1 | baseline akceptacji per głębokość na mvs | `arm.sh base 1 copy` z `LLAMA_SPEC_LOOKUP=1 LLAMA_SPEC_LOOKUP_LOG=…` (shadow) | trafienia ogona na głębokościach 5–16, tok/krok MTP4 | ogon ≥ 0.95 na głębokościach 5–8 dla mvs | < 0.8 → problem w regule `MMIN` |
| E-X2 | ogon W8 i W16 | `LLAMA_SPEC_LOOKUP=2 LLAMA_SPEC_LOOKUP_W=8` oraz `=16`, mvs + copy 8k/32k + spec_sweep | t/s, tok/krok, ms/krok | W8: mvs ≥ +35% (projekcja +41–45%), spec_sweep ±0.5% | W8 < +20% na mvs albo spec_sweep < −0.5% |
| E-X3 | kontroler w stylu Magnitude (#2) | nowy tryb `LLAMA_SPEC_LOOKUP=3` (drabinka 5/8/16, koszt per klasa kontekstu) | t/s w sesji mieszanej mvs → pl-proza → copy 32k → en-code | w 3% od najlepszej stałej szerokości per segment | > 3% gorzej niż najlepsza stała albo spec_sweep < −0.5% |
| E-X4 | sprzężone próbkowanie (#3), najpierw MTP | sampler Gumbel-max (seed, pozycja, token) + ten sam łańcuch w drafcie, spec_sweep T=1 i zestaw odłożony | akceptacja i t/s przy T=1 | +2…6% (domknięcie luki T0/T1) | < +2% → zostawić tylko dla DFlash2 |
| E-X5 | **Magnitude Vulkan na XTX** (pozycjonowanie) | `magnitude-engine --device vulkan --method dflash2 …` z `R3/servers.jsonl`, ten sam xbench | t/s mvs, copy, sweep | przegrywają z naszym HIP | jeśli wygrywają mvs > 1.2× nad E-X2/E-X3 → priorytet #5/#6 |
| E-C1 | 3090: krzywa szerokości CUDA | jak E-X0 na buildzie `cuda-compat` (`~/wt/cuda-compat`) | V(w, d) | V8 − V5 ≤ 4 ms przy 2k | V16 − V5 > 15 ms przy 2k → na CUDA tylko W8 |
| E-C2 | 3090 head-to-head z Magnitude 0.2.9 | kandydat E-X2/E-X3 + flagi z `R3/servers.jsonl` (fork) vs `magnitude-engine --method dflash2` (bez zmian), ten sam xbench; 2 rundy na silnik | t/s code-edit, copy 64k, sweep | code-edit ≥ 150 t/s (Mag 141.9 średnio, 157 bez lazy.py); copy 64k ≥ 80 t/s; sweep mediana ≥ 66 | code-edit < 1.3× naszego dzisiejszego 105 t/s (< 137) → nie włączać domyślnie; sweep < 65 → regres |

## 9. Do bazy wiedzy

| folder | tytuł | treść (liczby ze źródłami) |
|---|---|---|
| `repo/` | aktualizacja `magnitude.md` | Release 0.2.9 (`954d677d`): adaptacyjna szerokość draftu domyślnie (`options.rs:280-290`), drabinka wierszy 2/4/8/16 (`capabilities.rs:29-42`), ocena niezweryfikowanych propozycji, koszt per klasa kontekstu, looks 1% (`draft_control.rs:28-32`). Sprzężone próbkowanie (`generation/src/lib.rs:745-779`). Autotune w release: 67/67 domyślnych (`qwen.mag.first.tuning.jsonl`). Kwantyzacje: brak IQ2_S/Q2_K/Q4_1, Q3_K → q6k (`weights.rs:2086-2147`). AMD przez Vulkan (`docs/compatibility.md:150`). Status z „do-sprawdzenia” na „aktualne”. |
| `eksperymenty/` | `2026-10-16-magnitude-rozklad-wygranej.md` | 3090 27B code-edit: 7.88 vs 4.92 tok/krok, 50.2 vs 46.5 ms, 157 vs 105.7 t/s (×1.60 tok/krok, ×0.93 krok); copy 64k: 7.31 vs 4.51 tok/krok, 91.2 vs 64.7 ms, 80.2 vs 69.7 t/s; 5060 Ti 9B code-edit 13.17 vs 4.81 tok/krok, 35.3 vs 20.1 ms, 373 vs 239 t/s; lazy.py 5.63 (okno 2048) (`R3/x`, `R5/x`, `16i-magnitude/results.txt`). |
| `lekcje/` | `lekcja-sufit-bloku.md` „Na kopii wygrywa sufit bloku, nie kernel” | Obie strony siedzą na swoich sufitach (Mag 894/897, my 816/828); różnica 8 vs 5 tokenów z jednego przejścia wag; ich krok jest wolniejszy we wszystkich 4 przypadkach (×0.57…×0.93). |
| `modele/` | aktualizacja `drafter-dflash.md` | Trening DFlash: ~800K próbek Nemotron v2 + CodeAlpaca, seq ≤ 3072 (arXiv 2602.06036 §5); Nemotron v2 bez PL; u Magnitude 27B T=1: pl-kod 109.2 vs MTP 79.3, pl-proza 30.1 vs 44.9 t/s (`R3/x`); okno DFlash2 2048 (`interpretation.rs:553-598`). |
| `metody/` | `kontroler-szerokosci-draftu.md` | Algorytm Magnitude (§1.2) + różnice wobec T2 (§5.1); propozycje/krok 0.23–6.75 w zależności od tekstu (`R3/x`, `R5/x`). |
| `kernele/` | aktualizacja `mmvq-multikolumnowe.md` / `wmma-small-n.md` | Wzorzec: swap-AB `mma.m16n8k16`, wiersze 1..16 bitowo jak M=1 (`projection.cuh:1-35`); warunek W16 w BITEXACT. |
| `produkt/` | aktualizacja `produkt-ryzyka.md` | Magnitude na XTX przez Vulkan: niezmierzone (E-X5); nasze przewagi: PL (sweep 9B 121 vs 68 t/s), Q3_K_XL 27B na 16 GB (u nich nie ładuje się), 64k na 16 GB (LFM OOM u nich), prefill 27B na 3090 +18–25% (2k 1080 vs 915 t/s, 14k 1131 vs 907 t/s, 64k 72.4 vs 86.4 s; `R3/x` wiersze `ttft`/`copy`). |
| `research/` | `raport-16i-magnitude.md` (strona hub) | Link do tego raportu; ranking §4; plan §8. |
