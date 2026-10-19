# 21i — RSI-Inference Bench (Apple ML Research): co naprawdę mierzy, jak solidny jest weryfikator i co z tego bierzemy do RSI-F

Data: 2026-10-19. Praca tylko na CPU, koszt $0. Repozytorium sklonowane do
`~/qwen-opt/research-src/ml-rsi-inference-bench` (commit `a6b10af`, „Initial commit”, 3154 pliki, 425 MB).
Paper ma status „coming soon” (README, badge), więc wszystkie liczby poniżej pochodzą z kodu, z `task.toml` i z danych
leaderboardu osadzonych w `docs/leaderboard.html` (snapshot `2026-10-12T05:39Z`, obiekty `window.RSI_LEADERBOARD` i
`window.OV`). Wyciągnąłem je do `/tmp/rsi_lb.json` i `/tmp/rsi_ov.json`. Ścieżki `tasks/...` są względne wobec klonu.
`[INFERENCE]` oznacza mój wniosek, którego nie potwierdza żadne źródło. `[SZACUNEK]` to moja arytmetyka.

---

## 0. Najważniejsze

1. **26.7% to pass@1 Sonnet-5.5 w torze Day-0 Model Support i nic więcej.** Benchmark ma 10 zadań, a model wykonał
   28 prób (~3 na zadanie). Wynik to 8 pełnych zaliczeń. Liczba jest średnią z `passes/attempts` po zadaniach. Leaderboard sam
   podaje 95% CI **[0.10, 0.467]** (`OV.agents[0].ms_lo/ms_hi`). Mój bootstrap po zadaniach i próbach daje
   [0.067, 0.533]. Przewaga nad Opus-5.5 (0.133) **nie jest istotna**: P(różnica ≤ 0) ≈ 7%. Jedno zadanie (GLM-5.3-Flash,
   3/3) odpowiada za 0.10 z 0.267. W 5 z 10 zadań **żaden** z 12 agentów nie zaliczył ani jednej próby. Drugi tor
   (optymalizacja) to geomean speed-upu 1.677× [1.499, 1.904], liczony z **jednej** próby na zadanie.
2. **Weryfikator jest lepszy od typowych benchmarków kerneli, ale słabszy od naszej fabryki w statystyce.** W 20
   zadaniach throughput kandydat jest mierzony **przed** baseline'em, na zimno. Autorzy sami piszą w kodzie, że to daje
   systematyczny bias, którego trimmed mean nie usuwa (`_paired_helper.py:854-858`). W 10 z 20 zadań workload
   `decode_heavy` ma **1 pomiar na ramię**, a w 8 z nich także `high_load`, czyli 2/3 geomeanu. Nigdzie nie ma CI na
   poziomie zadania. Zadania regresyjne mają 2 rotowane rundy i twardy próg `noise_floor = 1.03`.
3. **Instrukcje obiecują rzeczy, których kod nie egzekwuje.** Wszystkie 20 `instruction.md` optymalizacji mówią
   o „hidden bench workloads” i o tym, że zmiany samych flag i konfiguracji dają 0. Tymczasem `environment/public/workloads.json`
   jest bajt w bajt równe `tests/workloads.json` w 20/20 zadań, a `NARROW_REJECTED_KINDS = set()` w 20/20 verifierach.
   Lekcja dla nas: reguła zapisana tylko w prompcie nie istnieje.
4. **Najcenniejsze do skopiowania** (szczegóły w §4): (a) bramka acceptance length plus *generation judge* dla
   spekulacji: zepsuty drafter może podnieść tok/s; (b) wynik `VOID` („infra, uruchom ponownie”) oddzielony od 0;
   (c) neutralna łatka jako sonda szumu, która przechodzi pełną ścieżkę rebuildu; (d) ciągła nagroda
   `max(0, r−1)`, bramkowana poprawnością, do rankingu ramion RSI-F; (e) workloady-strażnicy (guard shapes);
   (f) pinowanie środowiska: lockfile `===`, asercje przy buildzie, `.git` zredukowany do jednego commitu `inference_base`.
5. **Żadne z 37 zadań nie uruchomi się u nas bez przeróbek.** Wszystkie są na H100/B200, a preflight zna tylko
   `{H100, H200, B200, A100}` (`preflight.py:18`). Pier rezerwuje GPU sterownikiem `nvidia`, obrazy budują
   `TORCH_CUDA_ARCH_LIST=9.0+PTX`, a silniki to vLLM/SGLang, nie llama.cpp. Po przeróbce realne są najwyżej 1–2
   zadania na małych modelach (§6).
6. **Własny benchmark z naszej historii jest wykonalny i tani w formacie „Harbor-lite”.** Jest jednak *testem
   regresji dla RSI-F*, a nie leaderboardem: przy naszym budżecie GPU (≤ 15 h/30 dni, 21h §5.4 H6) da się zrobić
   ~5–12 zadań GPU na przebieg agenta. Projekt i 5 przykładowych zadań z liczbami z ledgera i wiki są w §5.

Trzy najważniejsze ustalenia wysłałem wcześniej do `RsiF` (`agent://RsiF`, 2026-10-19).

---

## 1. Czym jest benchmark

**Teza autorów** (README, `CITATION.cff`): to długohoryzontowy benchmark agentów, które poprawiają stos inferencji.
Agent dostaje vLLM albo SGLang na przypiętym commicie, model i 1–8 GPU. Pracuje offline do ~8.3 h. Osobny verifier
buduje edytowany silnik, serwuje model i mierzy.

**Skład** (`RSI_LEADERBOARD.release`, `tracks`):

| tor | zadania | metryka | silnik | GPU |
|---|---|---|---|---|
| Day-0 Model Support | 10 | pass@1 (binarny) | vLLM 5, SGLang 5 | 2–8 × H100/B200 |
| Inference Optimization (throughput) | 20 | geomean speed-upu | vLLM 11, SGLang 9 | 1–8 |
| Bug Fix (regression) | 7 | geomean speed-upu | vLLM 4, SGLang 3 | 1–8 |
| **razem** | **37** | ranking: ważony Bradley–Terry na skali Elo (wagi 0.25 / 0.5 / 0.25) | 20 / 17 | H100 17, B200 20; 1 GPU: 7 zadań, 2: 6, 4: 14, 8: 10 |

Zadanie `optimize_qwen3_8_27b_1xb200_dflash2_open` dotyczy **naszego modelu** (Qwen3.8-27B) z DFlash2, ale na
1×B200 i w bf16 (`task.toml`, `[metadata.inference_bench.model]`).

### 1.1 Format zadania (Harbor / Pier)

Każde `tasks/<id>/` zawiera:
- `task.toml` (schema 1.2): `[agent] timeout_sec = 30000` (8.33 h), `[verifier] timeout_sec` od 3 600 do 158 330 s,
  `[environment] gpus`, `gpu_types`, `memory_mb` (do 1 TiB), `allow_internet = false`; metadane `score_profile`,
  `scoring`, `correctness`, `oracle`, workloady;
- `instruction.md`: jedyne, co agent czyta jako zadanie;
- `environment/`: `Dockerfile`, `scripts/` (bench, correctness, timer, healthcheck), `public/workloads.json`;
- `tests/`: ukryty verifier (`test.sh`, `verify_*_real.py`, `_verifier_lib/`);
- `solution/`: wyrocznia (`solve.sh` + łatka). W zadaniach optymalizacji `known_good.patch` to celowo neutralny
  marker, a nie rozwiązanie (§2.1).

Pier (`third_party/pier`) prowadzi trial w kolejności: healthcheck → setup agenta → agent → `pre_artifacts` →
weryfikacja. `tests/` trafia do kontenera dopiero po fazie agenta (`pier/verifier/verifier.py:147-153`).
`allow_internet=false` oznacza `network_mode: none` (`environments/docker/docker.py:~345-370`). Rezerwacja GPU to na
sztywno `"driver": "nvidia"` (`environments/docker/__init__.py:61`).

---

## 2. Weryfikacja i nagrody, co dokładnie robi kod

### 2.1 Optymalizacja throughput (20 zadań)

Przepływ (`tasks/optimize_qwen3_8_27b_1xb200_dflash2_open/tests/verify_throughput_real.py`):
1. Preflight. Infra fault daje VOID z kodem 79, nie 0 (`:1175-1193`).
2. Capture nieśledzonych plików kandydata (`candidate_capture.py`) i klasyfikacja diffu (`category_gate.py`).
3. Correctness: teacher-forced logprobs na 20 promptach × 100 tokenów. Referencję generuje na żywo pristine worktree.
   Pozycja przechodzi, gdy |Δlp| ≤ 0.05 + 0.05·|lp_ref|. Całość przechodzi przy ≥ 95% pozycji
   (`_candidate_runner.py:378-437`). **Do 100 z 2000 pozycji może odbiegać dowolnie.** Instrukcja wprost zachęca do
   kwantyzacji i „compressed KV” (`instruction.md`, „Algorithmic substitution”), więc to bramka *stratna*.
4. Pomiar per workload: najpierw cały blok kandydata, potem pristine z disposable worktree na tagu `inference_base`
   (`:1493-1509`). Przed pomiarem jest prewarm obu ścieżek; stare wpisy `torch.compile` są usuwane (`:1478-1487`).
5. Estymator: `trimmed_mean` (odrzuca min i max; przy n=3 to mediana). Docstring przyznaje: *„the candidate arm runs
   FIRST and COLD, so its bias is systematic rather than random, and trimming does not remove it”*
   (`_paired_helper.py:840-859`).
6. Bramki spekulacji (tylko zadania MTP/DFlash): acceptance length i generation judge (§2.3).
7. Nagroda: `reward = max(0, geomean_w(cand_tps / pris_tps) − 1)`, bez celu, normalizacji i sufitu
   (`_verifier_lib/scoring.py:21-23`). Correctness fail daje 0. Za mało pomiarów (`MIN_VALID_RUNS = min(3, num_runs)`)
   daje `insufficient_data`. Pristine poniżej progu daje VOID (`:1656-1717`).

**Liczba pomiarów** (z `task.toml [verifier.env]` i `tests/workloads.json`, policzone skryptem dla 20 zadań):
- 10/20 zadań ma `decode_heavy = 1` i `prefill_heavy = 5`. `high_load` ma 1 pomiar w 8 z nich, 2 w gpt-oss-120b i 5 w
  kimi-linear. W tych 8 zadaniach dwie trzecie geomeanu to pojedyncze pomiary na ramię;
- zadania MTP mają 3–5 pomiarów, zadania P/D 3.

**Sonda szumu:** `solution/known_good.patch` to dwie linie komentarza w `vllm/__init__.py`. Opis łatki: *„a scored run
of it measures this profile's NOISE FLOOR and nothing else… EXPECT reward ≈ 0”*. Repo nie publikuje jednak wyników
takich przebiegów.

### 2.2 Bug Fix / regression (7 zadań)

Fakty z raportu scouta, sprawdzone wyrywkowo:
- Wspólny profil `regression_recovery_v2` i `noise_floor = 1.03` we wszystkich 7 zadaniach. Wynik poniżej 1.03 to
  `no_speedup`, czyli 0, nawet przy 1.02× (`verify_regression_real.py:58`).
- 2 rundy z rotacją kolejności ramion, [pristine, cand] i potem [cand, pristine] (`_bench_rounds.py:6-27`), plus
  adaptacyjny warm-up. Estymator `paired_ratio_median`, który przy n=2 jest średnią (`regression_scoring.py:61`).
- **Guard shapes**: workloady mierzone, ale nie liczone do wyniku. Jeśli kandydat jest na nich wolniejszy, dostaje 0
  (`instruction.md` regresji multimodalnej). Reguła jest łagodna: wystarczy, że **jedna** runda ma ≥ 0.95
  (`best = max(paired)`, `regression_scoring.py:168`).
- Poprawność: pristine bez spekulacji, kandydat, pristine jeszcze raz; 8 promptów × 128 tokenów przy c=1. Kształty
  scored (c8–c128) nie są sprawdzane na równoważność.
- Anty-oszustwa: digest drzewa pristine, ale tylko `*.py` i symlinki (bez `.cu`/`.so`); `deidentify_engine_version.py`
  usuwa `+g<commit>` z wersji; `.git` zastąpiony jednym commitem `inference_base`; asercje „defekt jest na ścieżce”:
  `assert_defect_path_is_exercised.py` (fp8: ≥ 19 500 rows×heads), `assert_gdn_kernel_recompiles.py` (kandydat
  ≤ 25% rekompilacji bazy), `assert_kernel_pack_is_pinned.py`.
- Wyrocznia jest zmierzona (`oracle_speedup`), ale służy tylko diagnostyce: `recovery = (r−1)/(oracle−1)`
  (`regression_multimodal_prefill_ttft/task.toml:69-85`). **Nagroda nie ma sufitu.**

### 2.3 Spekulacja: dwie bramki, których nam brakuje

Instrukcja zadania DFlash2 opisuje atak wprost. Rejection sampling zachowuje rozkład bez względu na drafter, więc
drafter proponujący śmieci jest tani na krok i może **podnieść** surowe tok/s.

- **Acceptance gate** (`acceptance.py`): parsuje `SpecDecoding metrics` z logów obu serwerów. Kandydat odpada przy
  `AL_cand / AL_pris < 1 − INFB_ACCEPT_RTOL`, gdzie `RTOL = 0.04` (`task.toml [verifier.env]`). Brak draftów po stronie
  pristine daje osobny powód void.
- **Generation judge** (`generation_judge.py`): **niespekulacyjny** serwer pristine robi teacher-forcing tego, co
  *wyemitował* serwer kandydata (32 prompty × 256 tokenów, greedy i T=1).
  - J1 liczy tokeny greedy o więcej niż ε = 0.5 nata poniżej top-1 pristine. Odrzuca, gdy nadwyżka kandydata nad
    pristine przekracza `max(0.005·n, 4·√(c+p+1))` (`:343-385`).
  - J2 to dwupróbkowy test kalibracji top-1 w zbiorze T=1, odrzucenie przy |z| > 5 (`:262-296`, `:386-394`).
  - Jest też sanity: jeśli sędzia nie zgadza się z greedy samego pristine, wynik to „unavailable”, a nie fałszywy
    werdykt.

### 2.4 Day-0 Model Support (10 zadań)

Z raportu scouta `ResRsiBench.ScoutSupport`:
- Referencyjna implementacja modelu jest wycięta z silnika. Robią to `no_reference_impl.py`, `scrub_reference_impl.py`,
  `no_withheld_code.py` i `no_answer_address.py`, uruchamiane w `Dockerfile`.
- Testy są przywracane z obrazu verifiera, nie z drzewa agenta (`test.sh:37-45`). Sieć odcina `unshare -r -n`, a gdy
  się nie da, przebieg jest VOID (`test.sh:70-86`).
- Nagroda binarna: 1 tylko wtedy, gdy przechodzą wszystkie f2p (fail-to-pass) i żaden p2p nie pada (`grader.py`).
  Częściowy wynik `f2p` jest raportowany i służy jako tie-break.
- Rozmiary wyroczni od 4 345 do 80 524 linii diffu (`wc -l solution/*.patch`). `[INFERENCE]` To zadania na dni pracy
  człowieka.

---

## 3. Pytanie 1: co znaczy 26.7% i jak solidna jest weryfikacja

### 3.1 Arytmetyka 26.7%

Sonnet-5.5 w Model Support, per zadanie (passes/attempts): DSV4-Flash 1/3, GLM-5.3-Flash 3/3, GPT-OSS 0/3,
Qwen3.8-Flash-Next 0/3, DSV4.1-Flash 1/3, DiffusionGemma 0/3, Inkling 2/3, Kimi-Linear 1/3, MiniMax-M3 0/3, SD3 0/1.
Średnia z ułamków: 2.667/10 = **0.2667**. Zgadza się z `pass_at_1` w `RSI_LEADERBOARD.model_support`.

| pytanie | odpowiedź | źródło |
|---|---|---|
| co to jest | średnia po 10 zadaniach z `passes/attempts`; zaliczenie częściowe = porażka | README (grafika tracks), arytmetyka wyżej |
| moc statystyczna | 28 prób, per zadanie ułamki z {0, 1/3, 2/3, 1}; CI leaderboardu [0.10, 0.467], mój bootstrap [0.067, 0.533] | `OV.agents[].ms_lo/hi`; własny bootstrap 20 000× |
| czy #1 jest lepszy od #2 | P(Sonnet − Opus-5.5 ≤ 0) ≈ 0.07 (paired bootstrap) | własne |
| koncentracja | bez GLM-5.3-Flash: 1.667/9 = 0.185; 5/10 zadań ma 0 zaliczeń u wszystkich 12 agentów (SD3, GPT-OSS, Qwen3.8-Flash-Next, MiniMax-M3, DiffusionGemma) | `RSI_LEADERBOARD.tasks[]` |
| „prawie” | f2p Sonnet = 0.90, tzn. średnio 90% ukrytych testów przechodzi, a binarna nagroda i tak wynosi 0 | `model_support[].f2p` |
| optymalizacja | 1 próba na (agent, zadanie): 27 × 12 = 324 wyniki; geomean 1.677× [1.499, 1.904] dla Sonnet, 1.484× [1.348, 1.659] dla Opus-5.5; CI się nakładają | `OV.agents[].opt_lo/hi` |
| odporność rankingu opt | leave-one-task-out: Sonnet 1.595–1.705, Opus-5.5 1.419–1.502; kolejność 1–2 stabilna | własne, z `tasks[].results` |
| koszt | 658 prób; API ≈ **$44.5 K** wyceniony w snapshocie; 3 110 h ścienne agentów; mediana na próbę opt: Sonnet $39 / 7.1 h, Opus-5.5 $56 / 5.9 h | suma `OV.agents[].runs.all.cost.all`, `.hours` |
| „$100K / 50K GPU h” | tylko w tweecie zapowiedzi ([x.com/onloglogn/status/2111170954944823685](https://x.com/onloglogn/status/2111170954944823685), wg snippetu wyszukiwarki, X blokuje odczyt). Górna granica z timeoutów: faza agenta ≤ 22 950 GPU·h, verifier ≤ 40 909 GPU·h, razem rząd 50 K. Snapshot wycenia $44.5 K, reszta to zapewne prace rozwojowe `[INFERENCE]` | `task.toml` × liczba prób, własne |

### 3.2 Jak solidna jest weryfikacja

**Mocne strony** (warte skopiowania):
- pristine mierzony w tej samej sesji, z disposable worktree (`verify_throughput_real.py:1442`);
- infra fault to VOID, nie 0; sygnatury deterministyczne blokują bezsensowne powtórki
  (`deterministic_failures.py`, `:1689-1717`);
- testy ukryte do fazy weryfikacji; obraz z lockfile `===` i asercjami przy buildzie (scout Pier: `Dockerfile`
  ~450–560);
- bramki spekulacji (§2.3), asercje „defekt na ścieżce” w regresjach, deidentyfikacja wersji, `.git` z jednym commitem.

**Słabości** (z kodu, z liczbami):
1. **Bias kolejności** w 20 zadaniach throughput: kandydat zawsze pierwszy i zimny, bez naprzemienności (przyznane
   w `_paired_helper.py:854-858`).
2. **n = 1 na ramię** dla `decode_heavy` w 10/20 zadaniach i dla `high_load` w 8/20; floor ważnych pomiarów =
   `min(3, n)` = 1.
3. **Brak CI na poziomie zadania.** W regresjach twardy klif przy 1.03. W throughput brak progu szumu: wynik 1.01×
   daje nagrodę 0.01.
4. **Bramki throughput nie zadziałały ani razu.** W 240 wynikach toru throughput `gate` jest zawsze `null`. W 84
   wynikach regresji zadziałało 12: `correctness_failed` 4, `guard_regressed` 3, `no_speedup` 4, `candidate_failed` 1.
   14/240 wyników throughput jest < 1.0 (minimum 0.804) i wchodzi do geomeanu bez korekty. Albo agenci nigdy nie
   psują poprawności w throughput, albo bramka stratna 95% jest za luźna `[INFERENCE]`.
5. **Brak sufitu i ślepa wyrocznia.** W regresjach agent przebija wyrocznię maintainera w **63 z 84** wyników. W
   `regression_multimodal_prefill_ttft` mediana 12 agentów to 3.17× przy wyroczni 1.62×, a Sonnet-5.5 ma 6.17×.
   Repo tego nie wyjaśnia. Hipotezy `[INFERENCE]`: agenci usuwają więcej niż jeden defekt rekompilacji Triton (zadanie
   to zachęca, „no particular fix”); ewentualnie efekt cache'u na dysku i warm-upu. Tak czy inaczej „Bug Fix” mierzy
   ogólne przyspieszenie, nie „znalezienie błędu”.
6. **Reguły tylko w prompcie**: „hidden workloads” i „config = 0” (§0 pkt 3).
7. **Wycieki poza kontener.** Snapshot kosztów notuje `server_web_search_requests: {"DeepSeek-V4.1-Flash": 2}`
   (`OV.cost_summary`). Narzędzia po stronie serwera API omijają `network_mode: none`. Do tego 9 prób, w których jeden
   „agent” używał kilku modeli (np. Fable 5.1 + Opus 5.5), co psuje atrybucję wyniku.
8. **Model Support:** capture tylko commitów (`pre_artifacts.sh:13`), więc niezacommitowana praca przepada; pass@k z
   Piera liczy infra error jako porażkę (`pier/utils/pass_at_k.py:48-49`).
9. **Digest pristine w regresjach** obejmuje tylko `*.py`.

**Przypadki reward hackingu:** repo nie publikuje żadnego przypadku przypisanego do konkretnego agenta. Verifiery
kodują jednak zagrożenia, które autorzy przewidzieli albo widzieli:
- zły drafter (bramka acceptance);
- flip konfiguracji (`category_gate`, dziś wyłączony);
- nieaktualne wpisy cache'u `torch.compile` po rebuildzie `.so`;
- ShareGPT po cichu odrzucający prompty > 1024 tokenów (komentarz w `workloads.json`);
- „naprawa” innego defektu niż ten z zadania (`assert_gdn_kernel_recompiles.py`, próg 0.25).

Wynik 6.17× pozostaje anomalią bez wyjaśnienia.

**Werdykt:** weryfikacja jest wystarczająco dobra do rankingu rzędu 1.0 vs 1.5×. **Nie wystarcza** do różnic poniżej
~5% na zadanie ani do pass@1 z dokładnością lepszą niż ±0.2.

---

## 4. Pytanie 2: co bierzemy do RSI-F i fabryki v1 (konkretne zmiany)

Punkt odniesienia: fabryka v1 (README fabryki, wiersze 71–99) już ma rzeczy, których brakuje Apple'owi:
- G4 ABBA na świeżych procesach, A/A, MDE i 95% CI (Student t lub bootstrap);
- klasy poprawności BIT/SAME-TOK/NEAR-TIE/KLD;
- zapieczętowany zestaw, który jest naprawdę ukryty (R36);
- ledger z łańcuchem sha256.

**Tego nie cofamy.** Ich 95%-stratna bramka correctness i brak naprzemienności są gorsze od naszych.

| # | mechanizm Apple | u nas dziś | zmiana (karta / bramka) | priorytet |
|---|---|---|---|---|
| A1 | acceptance gate (`AL_c/AL_p ≥ 0.96`) | R10 każe raportować `tok_step` przy profilu spec, ale nie bramkuje | **R37 `acceptance-floor`**: dla profilu `qwen-mtp`/DFlash/lookup werdykt `CONFIRMED` wymaga, żeby CI `tok_step` kandydata nie leżał w całości poniżej `−max(MDE_tok_step, 1%)`. W przeciwnym razie `INVALID`, gdy karta deklaruje metrykę `ms_step`, albo `REGRESSION`, gdy `tok_step`. Fixture z prawdziwego artefaktu: „drafter tańszy, gorszy” | wysoki: dziś G2 greedy md5 nie widzi degradacji draftera, bo przy greedy weryfikacji tekst jest ten sam |
| A2 | generation judge J1/J2 (teacher-forcing emisji kandydata przez serwer niespekulacyjny) | KLD (`llama-perplexity --kl-divergence`) na ścieżce nieserwerowej | **G2c dla klas NEAR-TIE/KLD**: `llama-server` bazy bez spec robi teacher-forcing tokenów z G4 kandydata (`n_probs`, `/completion` z `prompt` = prompt + emisja). J1: ε = 0.5 nata, bar `max(0.005·n, 4·√(c+p+1))`. Sanity: baza vs baza | średni |
| A3 | VOID ≠ 0 + sygnatury deterministyczne | `INVALID` łączy winę harnessu i agenta | nowy werdykt **`VOID`**: preflight R08/R09/R14/R15, crash ramienia A, A/A ponad próg. `INVALID` zostaje dla winy kandydata. Meta-metryka 21h §5.3 „odsetek INVALID z winy agenta” wymaga tego rozdziału. **Wyjątek H3:** page fault, timeout ringu albo reset GPU to nigdy VOID/retry, tylko kwarantanna | wysoki, tani (CPU) |
| A4 | neutralna łatka jako sonda szumu | A/A = ta sama binarka, dwa procesy | **karta `null-rebuild` raz na cykl RSI-F**: komentarz w pliku, który kompiluje się do `libggml-hip`, pełny `card fill` → `verify`. Oczekiwany werdykt `NULL`. Mierzy szum *rebuildu* (układ kodu, alignment), którego A/A nie widzi. Jeśli `CONFIRMED` albo `REGRESSION`, cykl stoi `[INFERENCE: na HIP alignment kodu może dawać ±0.x%]` | średni |
| A5 | ciągła nagroda `max(0, r−1)` bramkowana poprawnością | werdykt kategoryczny | **pole `reward` w wierszu `verdict`**: `median_effect` (w krotności) − 1, gdy `CONFIRMED`, w pozostałych przypadkach 0. Ramiona RSI-F (z i bez `skills/`) porównujemy geomeanem `1 + reward`. Werdykt zostaje źródłem prawdy, nagroda tylko agreguje | średni |
| A6 | guard shapes: wolniej na strażniku = 0 | R24 klasy workloadów + spec6 vs sealed (NEEDS-HUMAN przy przeciwnych znakach) | **pole karty `guards: [profile…]`** (np. `qwen-plain` tg, pp4096, `lfm`): 1 runda ABBA na strażnika; `CONFIRMED` wymaga, żeby żaden strażnik nie miał całego CI < −MDE. Reguła z CI, nie „best-of-rounds ≥ 0.95”. Przypadek z historii: 0070 J=16 tracił (wiki `kernele/mmq-epilog.md`) | średni |
| A7 | rekompilacja i defekt na ścieżce (`assert_*`) | R34 przełącznik w `.so`, `probe` (log/md5/timing) | bez zmian w strukturze. Dopisać do `probe.kind=log` wymóg, że regex trafia **w ramieniu B każdego przebiegu G4**, nie tylko w G3 | niski |
| A8 | reguły egzekwowane kodem, nie promptem | R23, R32, R36 w kodzie | **audyt promptów Implementera RSI-F**: każde zdanie „nie wolno X” ma regułę z fixture'em albo znika z promptu (lekcja z §3.2 pkt 6) | wysoki, CPU |
| A9 | `.git` = jeden commit `inference_base`; deidentyfikacja | worktree na pełnej historii `amd-opt` | **worktree Implementera bez historii** (squash do `base`), bez dostępu do `~/KERNEL/qwen-opt/patches`, wiki i `research/`. Inaczej `git log`/`grep` zdradza przyszłe łątki 00xx (kontaminacja benchmarku z §5) | wysoki przed P2 |
| A10 | sieć: `unshare -n`, VOID gdy się nie da | konwencja | Implementer w `bwrap --unshare-net` albo osobnym użytkowniku; **wyłączone narzędzia serwerowe API** (web search) w konfiguracji omp dla przebiegów benchmarku; log modelu per request (atrybucja) | średni |
| A11 | timer w pliku (`/app/.timer/remaining_secs`, alert 5 min) | budżet tokenów i czasu w prompcie | Implementer dostaje plik z pozostałym czasem i obowiązek „land early”: karta `register` z commitem najpóźniej w połowie budżetu, potem iteracje. Powód: agenci zużywają 34–86% budżetu (§7) | niski |
| A12 | eval-time seed losujący prompty ze znanego rozkładu | stałe 10 promptów sealed | **pula sealed 40 promptów, 10 losowanych per `verify`** z seedem zapisanym w ledgerze; obie strony ABBA dostają te same. Mniej overfittingu do 10 promptów (winner's curse 13–20 pkt przy 16 elementach, R36 source). Koszt: większa wariancja między weryfikacjami; per-verify bez zmian | niski (zmiana harnessu, `harness lock`) |

**Czego nie bierzemy:**
- 95%-stratnej bramki logprob (u nas bezstratność, 21h §5.6);
- kandydata mierzonego pierwszego i na zimno;
- n = 1;
- klifu 1.03 bez CI;
- nagrody bez sufitu bez przeglądu. Dla benchmarku z §5: `recovery > 2` daje `NEEDS-HUMAN`, analogicznie do R21.

**Zmiany w karcie twierdzenia** (`fk/card.py`), minimalny diff schematu:
```json
{
  "guards": ["qwen-plain", "lfm"],
  "spec": {"acceptance_floor_pct": 1.0},
  "task_ref": {"bench": "aob-v1", "task": "opt_mmq_epilogue", "oracle_effect_pct": 2.2},
  "seed": "<losowany przy verify, wpisywany przez weryfikator, nie przez autora>"
}
```
Wiersz `verdict` dostaje `reward`, `recovery` (gdy jest `task_ref`) i `void_reason` (gdy `VOID`).

---

## 5. Pytanie 3: własny benchmark z naszej historii („AMD-Opt Bench”, `aob-v1`)

### 5.1 Czy się da

Tak, materiał istnieje:
- 70 łatek `amd-opt` z bazą i commitem (`patch-manifest.json`, `latki/seria-amd-opt.md`);
- liczby „przed → po” w wiki (np. `kernele/mmq-epilog.md`, `kernele/sampler-fast-path.md`);
- wyniki negatywne z liczbami (`metody/wyniki-negatywne.md`, 16a);
- poprawki poprawności z testami (0023, rebase v0.7.0);
- fabryka jako gotowy verifier.

Ograniczenia:
- **Budżet GPU** ≤ 60 min/dobę i ≤ 15 h/30 dni (21h §5.4 H6). Jeden `verify`: Qwen MTP ~45 min, LFM ~20 min,
  llama-bench ~15 min (21h §5.5). Jeden przebieg agenta na 12 zadaniach GPU to ~4–6 h `[SZACUNEK]`, czyli 30–40%
  miesięcznego budżetu. Apple ma ≤ 1 292 GPU·h na przebieg agenta w samej fazie agenta, ~100× więcej.
- **Moc statystyczna**: przy 10 zadaniach binarnych i p ≈ 0.3 SE = √(0.21/10) = 0.145. SE 0.05 wymaga ~84 prób na
  agenta. Wniosek: `aob-v1` to **test regresji i postępu RSI-F** (czy pętla coś zepsuła, czy `recovery` rośnie),
  nie leaderboard modeli.
- **Kontaminacja**: łatki leżą w `~/KERNEL/qwen-opt/patches`, a 0018 jest w upstreamie (`1bb2b9fcb`). Potrzebne A9/A10
  oraz baza przed upstreamowym merge'em.
- **Bezpieczeństwo sprzętu**: żadne zadanie nie może włączać PM4 (17, H2/H3). Zadania o PM4 są wyłącznie CPU.

### 5.2 Format (Harbor-lite, zgodny z ich układem katalogów)

```
aob/tasks/<id>/
  task.toml        # kind=opt|fix|neg|port, profile=qwen-mtp|qwen-plain|lfm|bench, base_commit, gpu_minutes,
                   # correctness_class, oracle_effect_pct, noise_floor=MDE z fabryki, split=dev|test, guards
  instruction.md   # objaw albo cel, bez nazwy łątki; pliki do edycji; jak mierzyć lokalnie (tylko --dry-run)
  environment/     # build.sh (hipcc, -j6, nice), model sha256, base worktree bez historii, rocm_version pin
  tests/           # ukryte: generator karty (hypothesis/metric/switch z zadania), f2p/p2p (test-backend-ops -o,
                   # greedy md5, samp_ab), skrypt CPU-tier; uruchamiane przez Planistę po fazie agenta
  solution/        # oracle.patch = nasza prawdziwa łatka; null.patch = sonda szumu (A4)
```

Ocena każdego zadania (jedna funkcja, w stylu `compute_reward`):
1. **CPU tier** (zawsze, $0): build HIP i CUDA (R29), reguły statyczne, testy hosta (np. `samp_ab` CPU), ISA offline
   (liczba VALU/VGPR przez `--save-temps`). Wynik: `cpu_pass` ∈ {0, 1} i `f2p_cpu` ∈ [0, 1].
2. **GPU tier** (tylko gdy CPU tier przeszedł): `factory verify` z kartą wygenerowaną przez `tests/`. Implementer jej nie
   pisze, więc nie może zmienić protokołu (R22).
3. Nagroda:
   - `opt`/`port`: `reward = max(0, r − 1)`, gdy werdykt `CONFIRMED`, w pozostałych przypadkach 0. Do tego
     `recovery = (r−1)/(oracle−1)`; `recovery > 2` daje `NEEDS-HUMAN`;
   - `fix`: binarna (wszystkie f2p i żaden p2p nie pada) oraz `f2p` jako tie-break;
   - `neg`: binarna za trafną decyzję go/kill oraz ciągła `1 − min(1, |log(pred/meas)|)` za oszacowanie.
4. Split: zadania z łatek 0001–0047 (Qwen, 9–14.10) to **dev**, które RSI-F może widzieć w `skills/`; 0048–0070 i
   negatywy z 16a/16g to **test**, nigdy nie trafiają do `skills/`. Recenzent przecieku 21h §5.3 dostaje do 8-gramów
   także `oracle.patch` zadań test (próg 0, jak R36).

### 5.3 Pięć przykładowych zadań

| id | rodzaj | baza → wyrocznia | cel / objaw w `instruction.md` | weryfikacja (ukryta) | nagroda | liczby wyroczni | GPU |
|---|---|---|---|---|---|---|---|
| **T1 `opt_mmq_epilogue`** | opt, test | `f4f0deae5` → `f61994f58` (0070; karta `claims/2026-10-17-mmq-epi-0070.json`) | „Prefill Q4_K/Q5_K Qwen3.8-27B na gfx1100: przyspiesz `pp4096`, bitowo identycznie” | G0, G1 `MUL_MAT\|type_a=q[45]_K`, `MUL_MAT_ID`, logity prefillu bit w bit, G4 llama-bench `pp_tps`; strażnicy: pp512, LFM pp4096, J=16 | ciągła + `recovery` | 1099.5 → 1123.2 t/s (+2.2%, każda z 3 rund), pp512 +1.9%, LFM +0.3%; MUL_MAT 2486/2486, MUL_MAT_ID 933/933 (wiki `kernele/mmq-epilog.md`) | ~15 min |
| **T2 `fix_q8_1_overflow`** | fix, dev | rodzic `ba90baf3a` → 0023 | „Na niektórych długich promptach Qwen generuje NaN / śmieci po dużej aktywacji” | f2p: przypadek `test-backend-ops` z blokiem aktywacji, którego suma przekracza ±65504 (**do zbudowania** z opisu upstream ggml-org/llama.cpp#23606); p2p: MUL_MAT 2444/2444, FLASH_ATTN_EXT 4017/4017, RMS_NORM 53/53, greedy md5 plain i MTP = `9f83f1f81` | binarna + f2p | wiki `kernele/clamp-q8-1.md` | ~10 min (CPU tier: build) |
| **T3 `opt_sampler_slow_path`** | opt (host), test | baza przed 0048, 0065–0069 (przy 0031 już wgranej) | „Przez web UI i narzędzia omp LFM ma ~254 t/s, a llama-bench sugeruje więcej” | CPU tier: harness 312k wektorów fast vs slow, 0 różnic; `samp_ab.py` md5 tekstu i tool calls w 5 przypadkach (SAME-TOK); GPU: serwer LFM z profilem `client-ui` (R05) | ciągła; `recovery` | narzędzia omp LFM 254.2 → 294.3 t/s, Qwen MTP 104.8 → 113.2; budżet myślenia LFM 256.9 → 292.9 (wiki `kernele/sampler-fast-path.md`) | ~20 min |
| **T4 `neg_pm4_pdl_ceiling`** | neg, test, **tylko CPU** | brak łatki; dane: 15a hipoteza, pm4trace LFM, X1 microbench jako tekst | „Oszacuj zysk PM4-PDL z bezpieczną synchronizacją na taśmie LFM; decyzja go/kill przy progu +3%” | porównanie z pomiarami 16a; agent **nie** dostaje GPU (H2/H3) | binarna (kill = trafnie) + ciągła za oszacowanie | X1: 4.775 → 4.669 µs/kernel (0.11 µs przy progu 0.5); X2: górna granica +12.0%, realnie ≈ +2.9% → KILL (16a TL;DR) | 0 |
| **T5 `fix_mtp_embd_state_rebase`** | fix, test | `amd-opt-v070` @ rodzic `8c942e5a9` → `8c942e5a9` | „Po rebase na v0.7.0 serwer Qwen MTP ze słownikiem draftu pada przy pierwszym żądaniu” | f2p: 16 żądań MTP + draft vocab bez `GGML_ASSERT` (R30), greedy md5 MTP = md5 MTP przed rebase'em **w tym samym trybie** (R04); p2p: plain md5, `test-backend-ops` dotkniętych opów; continuous guard: `ms_step` w MDE | binarna + f2p | objaw `GGML_ASSERT(ubatch->embd_state …)`; przyczyna upstream `781dbc5ac` (#30257); nasze miejsca `draft_greedy_chain`, `draft_chain_segment` (wiki `lekcje/lekcja-mtp-embd-state.md`) | ~45 min |

Kandydaci na dalsze zadania:
- **trap/negatyw GPU**: „fuzja gate+up+SwiGLU w MMVQ 2–8 kolumn”. Historia: DFlash 111 → 96, MTP 82 → 76 t/s
  (`metody/wyniki-negatywne.md`). Nagradza agenta, który *nie* wysyła regresji;
- **NVIDIA consumer**: brak `ggml_cuda_pdl_sync` w 0053/0057 (stale reads na sm_120, R28, poprawka `14506801c`).
  Jedyne zadanie fix na RTX 5060 Ti;
- **port** (RSI-F R2): epilog 0070 → Q6_K/Q8_0 (21h §5.7 T1), wyrocznia jeszcze nie istnieje, więc to zadanie typu
  „open”.

**Koszt pełnego przebiegu 5 zadań:** ~90 min GPU na agenta i próbę `[SZACUNEK: 15+10+20+0+45]`. Plus sonda `null.patch`
raz na przebieg (~15 min, llama-bench). Przy 1 próbie na zadanie mieści się w 1.5 dnia budżetu.

**Pierwszy krok, tylko CPU:** zbudować T4 i część CPU T2/T3. Uruchomić na nich Implementera RSI-F z `skills/` i bez,
zanim wydamy minutę GPU.

---

## 6. Pytanie 4: czy ich zadania ruszą na naszym sprzęcie

Nasze karty: RX 7900 XTX 24 GB (gfx1100), pomocniczo RTX 5060 Ti 16 GB (sm_120), chmurowe 3060/3090/5060 Ti (raporty
09; `KERNEL/hardware/rx-7900-xtx.md`).

**Blokery dla wszystkich 37 zadań:**
1. Preflight voiduje nieznane GPU (`_verifier_lib/preflight.py:18`). Istnieje obejście
   `INFB_PREFLIGHT_ALLOW_GPU_MISMATCH` (`:20`).
2. Pier: `"driver": "nvidia"`, brak `/dev/kfd` i ścieżki ROCm (scout Pier; `docker/__init__.py:61`).
3. Obrazy: `FROM nvidia/cuda:12.8.1-devel`, `TORCH_CUDA_ARCH_LIST=9.0+PTX` (np.
   `regression_multimodal_prefill_ttft/environment/Dockerfile:7,326`); kod sprzątający GPU woła `nvidia-smi`.
4. Pamięć: 30/37 zadań wymaga ≥ 2 GPU klasy 80–192 GB.
5. Silniki vLLM/SGLang. vLLM oficjalnie wspiera RX 7900 (gfx1100) na ROCm
   ([docs vLLM v0.6.6](https://docs.vllm.ai/en/v0.6.6.post1/_sources/getting_started/amd-installation.md),
   [ROCm docs](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/inference/vllm.html)), ale to nie jest nasz
   stos. Przypięte wersje są budowane pod CUDA.

**Zadania jednokartowe z małym modelem, czyli jedyni kandydaci:**

| zadanie | model | pamięć wag `[SZACUNEK]` | XTX 24 GB | 5060 Ti 16 GB | problem |
|---|---|---|---|---|---|
| `regression_multimodal_prefill_ttft` | Qwen3.5-4B, SGLang | ~9 GB bf16 | mieści się | mieści się | defekt (rekompilacja Triton przy `T: tl.constexpr`) jest sprzętowo neutralny; SGLang na ROCm gfx1100 niepewny `[INFERENCE]`; wyrocznię 1.62× i floor 1.03 trzeba zmierzyć od nowa |
| `regression_spec_decode_acceptance_drop` | Llama-3.1-8B + EAGLE3, vLLM | 16.1 GB bf16 + drafter + KV | ciasno | nie | wymaga fp8 KV: RDNA3 nie ma FP8 (`hardware/rx-7900-xtx.md`, tabela); defekt w Pythonie (padded draft seq lens) jest przenośny |
| `regression_mxfp4_moe_decode_throughput` | gpt-oss-20b MXFP4, SGLang | ~13 GB `[INFERENCE]` | mieści się | mieści się | defekt to konfiguracja Triton MoE „na Hopperze”; `triton_kernels` na gfx1100 raczej nie `[INFERENCE]` |
| `optimize_llada2_mini_1xh100_sglang_open` | LLaDA2.0-mini (16B MoE `[INFERENCE]`) | ~32 GB bf16 | nie | nie | — |
| `optimize_qwen3_6_27b_1xh100`, `optimize_qwen3_8_27b_1xb200_dflash2` | 27B bf16 | ~54 GB | nie | nie | — |

**Wniosek:** bez przeróbek nie rusza nic, ich zadania są *datacenter-only*. Po przeróbce (własny obraz ROCm lub CUDA
sm_120, nowa wyrocznia i noise floor, obejście preflightu) sens ma tylko regresja multimodalna na 5060 Ti. Mierzyłaby
jednak agenta w vLLM/SGLang, nie w llama.cpp/HIP. Ich wartość dla nas to **projekt verifiera, nie zadania**.

---

## 7. Pytanie 5: lekcje o trybach porażek agentów w inference engineering

Paper z analizą jeszcze nie wyszedł. Poniższe wynika z danych leaderboardu i z obron wpisanych w verifiery.

| tryb porażki | dowód | co z tym robimy |
|---|---|---|
| **„prawie gotowe”** w dużych zadaniach | f2p 0.84–0.90 u top-5 przy pass@1 0.10–0.27; 5/10 zadań 0 zaliczeń u wszystkich | w `aob` zadania `fix` mają f2p jako tie-break; w RSI-F karty dzielone na mniejsze kroki (jedna hipoteza = jedna karta, już tak jest) |
| **przedwczesne zatrzymanie** | mediana wykorzystania 8.3 h w opt: Gemini-3.7-Flash 2.8 h, GPT-6-Astra 3.5 h, Sonnet-5.5 7.1 h. Spearman(godziny, wynik opt) = 0.51 przy n = 12, więc słaby dowód. Instrukcja regresji wprost: *„stop when you cannot find more, not when it looks fixed”* | A11 (timer i „land early”); Proponent RSI-F dostaje informację, ile budżetu zostało niewykorzystane |
| **koszt ≠ jakość** | Spearman(mediana $ na próbę, wynik opt) = 0.22; Opus-4.8 $99/próbę i 1.139×, GPT-6.1-Sol $11.7 i 1.374× | meta-metryka RSI-F „CONFIRMED na $” obok „na h GPU” |
| **regresje sprzedane jako optymalizacja** | 14/240 wyników throughput < 1.0 (minimum 0.804); w regresjach 3× `guard_regressed` | nasze `REGRESSION` i strażnicy A6 |
| **psucie poprawności** | 4× `correctness_failed`, wszystkie w regresjach, 3 z 4 u Gemini Flash | klasy BIT/SAME-TOK; nie luzować |
| **hakowanie metryki spekulacji** | dedykowane bramki AL i J1/J2 (§2.3) | A1, A2 |
| **przeoptymalizowanie pod jawny workload** | workloady jawne 1:1, a agent ma ten sam `_paired_helper.py` co verifier | nasz sealed i A12 |
| **wyjście poza piaskownicę przez API** | 2 server-side web search mimo `network_mode: none`; 9 prób z kilkoma modelami | A10 |
| **„naprawa” obok defektu** | `assert_gdn_kernel_recompiles.py`, próg 0.25, dobrany ręcznie; `recovery` do 3.8× wyroczni | `probe` w każdym przebiegu B (A7); `recovery > 2` → NEEDS-HUMAN |
| **artefakty środowiska** | prewarm dropuje nieaktualne wpisy `torch.compile`; niezacommitowana praca przepada w Support | R20/R34 (binarka ≠ etykieta) już są; `card fill` z commitu |

Nasze własne obserwacje (reguły R01–R36 to katalog incydentów) pokrywają się z ich obronami:
- R22 (agent zmienia protokół) = ich `category_gate` i flagi narzucane przez verifier;
- R13 (jeden prompt) = ich „n=2c”, żeby każdy punkt robił tyle samo kroków;
- R31 (baseline w tej samej sesji) = ich pristine worktree.

Nie mają odpowiednika naszych R08/R09/R14 (zombie VRAM, BACO, temperatura). Na datacenter ma to mniejsze znaczenie, u
nas jest krytyczne.

---

## 8. Ryzyka i otwarte pytania

- Paper może opisać przypadki hackingu i rozkład szumu sondy `known_good`. Wtedy uzupełnić §3.2. Do sprawdzenia po
  publikacji.
- Anomalia 6.17× (regresja multimodalna) bez wyjaśnienia. Jeśli to artefakt pomiaru, to cały tor regresji ma problem
  z walidacją.
- `aob-v1` T2 wymaga zbudowania nowego przypadku f2p; dziś mamy tylko p2p z commitu 0023.
- Kontaminacja `aob`: Implementery RSI-F mają dziś dostęp do `~/KERNEL` (21h §6 „izolacja to konwencja”). Bez A9/A10
  wyniki na `test` są bez znaczenia.
- Wycena „$100K / 50K GPU h” pochodzi z tweeta, nie z repo. Snapshot pokazuje $44.5 K.

---

## 9. Źródła

Zewnętrzne (sprawdzone 2026-10-19):
- Repozytorium: [github.com/apple-aiml-research/ml-rsi-inference-bench](https://github.com/apple-aiml-research/ml-rsi-inference-bench),
  commit `a6b10af`. Strona [rsi-inference.com](http://rsi-inference.com) przekierowuje na podgląd
  `docs/leaderboard.html`.
- Zapowiedź: [x.com/onloglogn/status/2111170954944823685](https://x.com/onloglogn/status/2111170954944823685) (Ruixiang
  Zhang, „$100K API tokens, 50K GPU hours”). Treść tylko ze snippetu wyszukiwarki, X blokuje odczyt.
- vLLM ROCm gfx1100: [docs.vllm.ai v0.6.6](https://docs.vllm.ai/en/v0.6.6.post1/_sources/getting_started/amd-installation.md);
  [rocm.docs.amd.com vLLM](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/inference/vllm.html).

Z klonu (`~/qwen-opt/research-src/ml-rsi-inference-bench`):
- `README.md`, `CITATION.cff`, `docs/leaderboard.html` (`RSI_LEADERBOARD`, `OV`, `STEPS`; snapshot 2026-10-12T05:39Z);
- `tasks/optimize_qwen3_8_27b_1xb200_dflash2_open/`:
  - `task.toml`, `instruction.md`;
  - `tests/verify_throughput_real.py:1-200,856-960,1158-1800`;
  - `tests/_verifier_lib/{scoring.py:21-23, acceptance.py, generation_judge.py:128-400, category_gate.py, preflight.py:18-20, _paired_helper.py:840-859}`;
  - `tests/_candidate_runner.py:378-437`;
  - `solution/known_good.patch`;
- `tasks/optimize_qwen3_6_27b_1xh100_open/task.toml:64-65,114-128` i `tests/workloads.json` (n=1);
- `tasks/regression_multimodal_prefill_ttft/{task.toml:65-100, instruction.md, environment/Dockerfile:7,326}`;
- `tasks/regression_spec_decode_acceptance_drop/tests/{verify_regression_real.py:58, _verifier_lib/regression_scoring.py:15,61,168, _bench_rounds.py:6-29}`;
- `third_party/pier/src/pier/{verifier/verifier.py:147-153, environments/docker/__init__.py:61, environments/docker/docker.py:~345, utils/pass_at_k.py}`;
- raporty podagentów: `agent://ResRsiBench.ScoutRegression`, `agent://ResRsiBench.ScoutSupport`,
  `agent://ResRsiBench.ScoutPier`. Ich numery linii oznaczone `~` są przybliżone.

Wewnętrzne:
- `~/qwen-opt/factory/README.md:71-99` (bramki, werdykty), `factory/rules/r01…r36` (`POLICY.source`),
  `factory/claims/2026-10-17-mmq-epi-0070.json`;
- `KERNEL/product/research/21h-rsi.md` §5.3–5.7, `16a-pm4-pdl.md` (TL;DR), `patch-manifest.json`;
- wiki: `latki/seria-amd-opt.md`, `kernele/mmq-epilog.md`, `kernele/clamp-q8-1.md`, `kernele/sampler-fast-path.md`,
  `metody/wyniki-negatywne.md`, `eksperymenty/2026-10-16-rebase-v070.md`, `lekcje/lekcja-mtp-embd-state.md`;
- `KERNEL/hardware/rx-7900-xtx.md`.

Obliczenia własne (bootstrap pass@1, LOO geomean, korelacje, sumy kosztów, liczba pomiarów per workload): eval
sesji ResRsiBench na `/tmp/rsi_lb.json`, `/tmp/rsi_ov.json` oraz plikach `task.toml`.

---

## Do bazy wiedzy

- **RSI-Inference Bench (Apple, 2026-10):**
  - 37 zadań vLLM/SGLang na H100/B200: 10 Day-0 Support (binarne), 20 optymalizacji i 7 regresji (geomean speed-upu);
  - 8.3 h na próbę, offline;
  - snapshot 2026-10-12: 12 agentów, 658 prób, ~$44.5 K API.
- **„26.7%”** to pass@1 Sonnet-5.5 w Support: 8/28 prób, CI [0.10, 0.47], różnica do #2 nieistotna (P ≈ 0.07). 5/10
  zadań bez żadnego zaliczenia. Optymalizacja: 1.677× [1.50, 1.90] z 1 próby na zadanie.
- **Nagroda:** `max(0, geomean(cand/pristine) − 1)`; correctness fail = 0; infra = VOID (rerun), nie 0. Pristine
  mierzony w tej samej sesji z disposable worktree.
- **Słabości weryfikatora:**
  - kandydat mierzony pierwszy i na zimno (przyznane w kodzie);
  - n = 1 na ramię dla 2/3 workloadów w 8/20 zadań (`decode_heavy` i `high_load`);
  - brak CI per zadanie, klif 1.03 w regresjach;
  - bramka correctness stratna (95% pozycji w ±0.05 nata);
  - agenci przebijają wyrocznię regresji w 63/84 wyników (max 6.17× vs 1.62×).
- **Reguły tylko w prompcie nie działają:** „hidden workloads” i „config = 0” nieegzekwowane w 20/20 zadań.
  Server-side web search API omija `network_mode: none`.
- **Do RSI-F:**
  - bramka acceptance length (R37) i generation judge dla spekulacji;
  - werdykt `VOID` oddzielony od `INVALID`;
  - sonda `null-rebuild` raz na cykl;
  - pole `reward` w ledgerze;
  - `guards` w karcie (CI, nie best-of);
  - worktree bez historii i sieci;
  - pula sealed z losowaniem per verify.
- **Nie bierzemy** ich stratnej poprawności ani pomiaru bez naprzemienności; nasza fabryka (ABBA, A/A, MDE, CI) jest
  w statystyce mocniejsza.
- **Na naszym sprzęcie** żadne zadanie nie rusza bez przeróbek (preflight H100/H200/B200/A100, Pier `driver: nvidia`,
  sm_90). Jedyny sensowny port: regresja multimodalna Qwen3.5-4B na RTX 5060 Ti.
- **Własny benchmark `aob-v1`** w formacie `task.toml`/`instruction.md`/`environment`/`tests`/`solution`, z fabryką
  jako verifierem i podziałem dev (0001–0047) / test (0048–0070 + negatywy):
  - 5 przykładów: 0070 epilog MMQ (+2.2%), 0023 clamp q8_1 (fix), sampler fast path (254 → 294 t/s), PM4-PDL
    (neg, tylko CPU, KILL), crash `embd_state` po rebase (fix);
  - ~90 min GPU na przebieg. To test regresji RSI-F, nie leaderboard: SE ≈ 0.15 przy 10 zadaniach.
