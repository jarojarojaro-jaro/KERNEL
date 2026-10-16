# 16h — Fabryka v1: co zbudowano, jak z niej korzystać, ograniczenia

Data: 2026-10-16. Praca wyłącznie na CPU, koszt $0, **ani jednego uruchomienia GPU**. Projekt pochodzi z
[15f §5](15f-agentowa-nauka.md) (role, artefakty, bramki, antyoszustwo), a działanie nr 1 z rankingu
[15-synteza §3](15-synteza.md). Kod leży w `~/qwen-opt/factory/`, instrukcja użytkownika (po polsku) w
`~/qwen-opt/factory/README.md`. Oznaczenia: `[INFERENCE]` to mój wniosek, `[SZACUNEK]` to wycena,
`[NIEZWERYFIKOWANE]` to rzecz niesprawdzona na GPU.

## 1. TL;DR

- **Zbudowany rdzeń fabryki v1:**
  - karta twierdzenia zamrażana przed pomiarem;
  - `ledger.jsonl`, tylko do dopisywania, z łańcuchem sha256 i plikiem `head`;
  - weryfikator z kaskadą G0 → G5 i werdyktem;
  - zapieczętowany zestaw 10 promptów;
  - 36 deterministycznych reguł z fixture'ami z prawdziwych incydentów;
  - komendy `report`, `merge-check`, `harness lock`;
  - tryby `--dry-run` i `--fake`.

  Całość to Python stdlib: 2394 linie w `fk/` + CLI, 1141 w `rules/`, 928 w testach. **57 testów przechodzi w ok. 30 s
  na CPU.**
- **Weryfikator opakowuje istniejące narzędzia, nie zastępuje ich.**
  - Poprawność: `fusion/greedy.sh` (uruchamiany z kopii nazwanej hashem).
  - Opy: `test-backend-ops`.
  - Prefill: `llama-bench`.
  - KLD: `llama-perplexity` + `tools/kld_gate.py`.
  - Dekodowanie mierzy własny sterownik `fk/measure.py` z ciałem żądania takim jak w `spec_sweep.py`. Dokłada to,
    czego spec_sweep nie zapisuje: sha256 tekstu każdego żądania, `build_info` z `/props`, telemetrię (junction, VRAM,
    GTT) i PID procesu.
- **Odmowa pracy jest strukturalna, nie promptowa.** Weryfikator odmawia, gdy:
  - diff implementera dotyka `llama-bench`, `perplexity`, `build-info`, pól czasu serwera albo osłabia testy
    `test-backend-ops`;
  - karta nie jest zarejestrowana albo zmieniła się po rejestracji;
  - harness różni się od ostatniego wiersza `harness-lock`;
  - pieczęć zestawu zapieczętowanego jest naruszona;
  - sha256 binarek albo modelu nie zgadza się z kartą.
- **Backtesty reguł na naszych prawdziwych danych (CPU) dały nowe liczby:**

  | reguła | dane | wynik |
  |---|---|---|
  | R21 anomaly breaker (rodzina modelu z całych słów labela) | `spec_sweep.jsonl` 194 wiersze; kopia `KERNEL` 182 | **1/1 incydent (wiersz 15, 5.6 t/s), 0 fałszywych alarmów** (15f E-D: 5/182 przez podciąg „lfm”) |
  | R23 denylista | 70 łatek `amd-opt` | **0/70** odmów (brak fałszywych odmów) |
  | R29 konstrukcje HIP poza guardem | `amd-opt`, 283 pliki `.cu/.cuh` | 5 trafień, wszystkie w `ggml_cuda_mmq_epi_pin` łatki 0070 (prawdziwy błąd, naprawiony w `57e0bdfe4`) |
  | R29 | `cuda-compat`, 283 pliki | **0** |
  | R28 PDL bez `ggml_cuda_pdl_sync` | `amd-opt` | 3 trafienia: 0053, 0057 (znane) i **nowe: `fattn-kvq.cu` `flash_attn_kvq_combine_fwht` (`3a1279f95`)** |
  | R28 | `cuda-compat` | 1 trafienie (to samo nowe) |
  | R20 label ≠ binarka | `spec_sweep.jsonl` | 7 labeli z rozrzutem ms/krok > 1%, np. `DRAFT_N=4 qwen mtp rocm` 28.94–41.74 |
  | R20 | `fusion/spec_sweep.jsonl` | `r1-base-qwen` 33.15–41.81 |
  | R12 roofline na tekście | `autokernel-amd/reports/15-road-to-65.md` | łapie 1075 GB/s, 1138 GB/s i „112% PEAKU”; nie odpala na „595 GB/s, 62% peaku” z 15f |

  Nowe trafienie R28 jest dziś prawdopodobnie nieosiągalne na CUDA, bo kvq działa tylko na RDNA3_0 `[INFERENCE]`.
  CudaKvq potwierdził, że jego port `kvq-cuda` tego kernela nie używa.
- **Pierwszy prawdziwy przypadek jest gotowy do uruchomienia.**
  - Karta `claims/2026-10-17-mmq-epi-0070.json` opisuje łatkę 0070 `GGML_HIP_MMQ_EPI`, wpisaną jako UNMEASURED.
  - Ma prawdziwe sha256 (`~/llama-opt` @ `f61994f58`, model Qwen) i jest zarejestrowana w ledgerze (seq 1). Harness
    zablokowano w seq 0.
  - `verify --dry-run` planuje 12 bloków GPU (2 × `test-backend-ops`, 2 × greedy, 8 × llama-bench pp4096 w ABBA
    w jednej binarce), każdy ≤ 290 s z pauzami 45 s: **ok. 20 min GPU** `[SZACUNEK]`.
  - Już G0 zgłasza R29 (NEEDS-HUMAN): na `amd-opt` ta łatka nie kompiluje się pod CUDA.

## 2. Co zbudowano

| plik | rola | stan |
|---|---|---|
| `factory` / `factory.py` | CLI: `card new/fill/check`, `register`, `verify [--dry-run/--fake]`, `ledger verify/show`, `report [--drafts]`, `rules list/test/backtest/text`, `sealed check/summary`, `harness status/lock`, `merge-check`, `_block` | działa, testy CLI |
| `fk/card.py` | schemat karty i walidacja (metryka end-to-end, `kill`, klasa, przełącznik, `probe`, `prompt_set` = `sealed-v1+spec6`, `attacked.share_ms` dla metryk ms), `card_sha` | działa |
| `fk/ledger.py` | dopisywanie pod `fcntl.flock`, łańcuch `prev_sha256`/`sha256` (kanoniczny JSON), `ledger.jsonl.head` (wykrywa obcięcie), plik 0444 między zapisami; `verify()` wykrywa edycję, usunięcie, przestawienie i obcięcie | testy |
| `fk/verify.py` | kaskada G0–G5, decyzja, wiersz ledgera (karta, commity, sha256 każdej binarki i `.so`, model, env i argv ramion, protokół, hash harnessu i zestawu, ABBA, wszystkie próbki, A/A, CI, MDE, spec6, `client-ui`, bramki, znaleziska, dowody z sha256) | testy fake + ścieżka rzeczywista na atrapie |
| `fk/stats.py` | harmonogram ABBA/BAAB, pary sąsiednich procesów, A/A i B/B, t Studenta i bootstrap (stały seed), MDE, reguła werdyktu | testy |
| `fk/measure.py`, `fk/block.py`, `fk/gpu.py` | blok GPU: `pgrep` → `flock gpu` → `flock quiet` → `timeout 290` → preflight (reguły) → praca → telemetria → SIGTERM, po 15 s SIGKILL; dry-run drukuje komendę zewnętrzną i wewnętrzną; `FakeGPU` generuje dane syntetyczne | testy, bez GPU |
| `fk/neartie.py` | bramka near-tie (tqLLM): pierwszy rozjazd greedy akceptowany, gdy kandydat wybrał drugi token referencji przy marginesie ≤ 0.1 logprob | testy |
| `fk/preflight.py` | migawka: serwer na 8080, obce `llama-server`, procesy z kontekstem KFD (`/sys/class/kfd/kfd/proc`), VRAM/GTT, `power/control`, junction, moc, loadavg, kwota cgroup, port | test na prawdziwym `/sys` |
| `fk/diffscan.py` | parser diffa, denylista ścieżek i treści, `git show/grep/log` | testy, backtest 70 łatek |
| `fk/sealed.py`, `sealed/prompts.jsonl` | zestaw zapieczętowany (sha256 `1e6c3a4b…` przypięty w kodzie), zestaw publiczny parsowany z `spec_sweep.py` (AST, bez importu), 8-gramy do wykrywania przecieku | testy |
| `fk/profiles.py` | profile `qwen-mtp`, `qwen-plain`, `lfm`; flagi serwera z `run-llm.sh`, greedy z `greedy.sh`, llama-bench z `loo.py`, KLD z `kld_canary.sh`; bajty na przebieg Qwen 16.83 GB i LFM 1.777 GB (15a) | — |
| `fk/report.py` | markdown z ledgera: tabela werdyktów z `ledger:<seq>/<sha8>` przy każdej liczbie, szkice wyników negatywnych, kalibracja przewidywań, szkice notatek wiki w formacie `KONWENCJE.md` | test |
| `rules/r01…r36_*.py` + `rules/fixtures/` | 36 reguł (§3), 53 pliki fixture'ów (328 KB), z czego wiele to kopie prawdziwych artefaktów | `rules test`: 0 rozbieżności |
| `tests/` | 57 testów: piaskownica git + sztuczne buildy, wszystkie werdykty, odmowy, dry-run, CLI, ścieżka rzeczywista z `tests/fake_llama_server.py` (atrapa HTTP, przez którą przechodzi prawdziwy `fusion/greedy.sh`) | OK |
| `claims/2026-10-17-mmq-epi-0070.json` | pierwsza prawdziwa karta (łatka 0070) | zarejestrowana, seq 1 |
| `ledger.jsonl` | seq 0 `harness-lock` (`4163856fa42e`), seq 1 `register` | łańcuch OK |

### 2.1 Bramki

Kaskada idzie od najtańszej bramki. Porażka kończy ścieżkę wierszem `INVALID`.

- **G0** (CPU):
  - schemat karty, rejestracja (sha256 karty = wiersz `register`), łańcuch ledgera, pieczęć zestawu, blokada harnessu;
  - sha256 binarek i modelu vs karta;
  - diff: `touched_paths` musi równać się plikom diffa;
  - przełącznik obecny w diffie albo w drzewie kandydata i w `.so` kandydata; commit kandydata w
    `libllama-common.so` (sprawdzone na `~/llama-opt`: `f61994f58` i `GGML_HIP_MMQ_EPI` są w bibliotekach);
  - reguły statyczne (R02, R05, R06, R07, R10, R19, R23, R26–R29, R32, R34, R36).
- **G1:** `test-backend-ops test -o OP [-p PARAMS]` na kandydacie z przełącznikiem `on`.
- **G2:** `greedy.sh` na świeżych serwerach dla bazy i kandydata, porównanie md5 tryb po trybie.
  - `BIT` i `SAME-TOK` wymagają równości (R01).
  - `NEAR-TIE` przy różnicy uruchamia serwery z flagami `greedy.sh` i `top_logprobs: 2`, potem `neartie.gate`.
  - `KLD` uruchamia `llama-perplexity` według protokołu `kld_canary.sh`, potem `kld_gate.gate` i R25.
- **G3** sprawdza, czy zmiana się wykonała:
  - `probe log`: regex w logu serwera musi być przy `on` i nie może go być przy `off`;
  - `probe md5`: `off` przywraca md5 bazy, a `on` coś zmienia;
  - `probe timing`: ramię A to ta sama binarka z `off`, więc zmierzony efekt jest efektem przełącznika.

  Zawsze obowiązuje do tego R34 (przełącznik skompilowany w bibliotece).
- **G4:**
  - rundy A B B A / B A A B, każdy przebieg to świeży proces serwera (albo llama-bench);
  - prompty: 10 zapieczętowanych + 6 spec_sweep, 2 seedy, 400 tokenów, T=1, `cache_prompt: false`;
  - przy zmianach samplera (R05) dodatkowo wariant `client-ui`: `reasoning_control`, `logit_bias`, `n_probs`,
    permisywna gramatyka, na promptach zapieczętowanych z jednym seedem;
  - pary to sąsiednie procesy; A/A i B/B to drugi proces vs pierwszy w rundzie;
  - werdykt liczony jest na zestawie zapieczętowanym, spec6 jest raportowany obok.
- **G5:** roofline na przebieg (R12), Amdahl `saving_ms ≤ 1.1 × share_ms + 0.02` (R33), anomalia (R21) i bimodalność
  (R11, w G4).

### 2.2 Reguła werdyktu

MDE = max(próg metryki, 2 × mediana |A/A|, `mde_pct` z karty). Progi metryk: 0.2% dla ms, 0.3% dla pp/tg, 0.5% dla t/s
i tok/krok. Wynikają z A/A 15f E-B: 0.09% ms/krok, 0.16% t/s.

| werdykt | warunek |
|---|---|
| `INVALID` | bramka G0–G3/G5 albo reguła blokująca, albo \|A/A\| > 0.5% (ms) lub 1% (pozostałe) |
| `REGRESSION` | cały CI < 0 |
| `REFUTED` | cały CI poniżej progu `kill` z karty (twierdzenie obalone, nawet przy małym realnym efekcie) |
| `CONFIRMED` | CI > 0 i mediana ≥ MDE |
| `NULL` | pozostałe przypadki |
| `NEEDS-HUMAN` | zastępuje `CONFIRMED` przy klasie KLD/NEAR-TIE (G7), przy regule NEEDS-HUMAN (R11, R26, R28, R29) albo przy przeciwnych znakach zestawu zapieczętowanego i spec6 |

## 3. Reguły i ich incydenty

Każda reguła ma co najmniej jeden fixture „fire” i jeden „clean”. „real” oznacza kopię istniejącego artefaktu,
„reconstructed” oznacza dane odtworzone z liczb w notatce (źródło podane w fixture).

| # | tryb awarii / lekcja | fixture „fire” (rodzaj) |
|---|---|---|
| R01 | 07#1 kontrakcja FMA | md5 `fusion/greedy/k2a.plain.txt` 32b54d31 vs `k2base` c4708318 (real) |
| R02 | 07#2 kolejność akumulacji FA | diff 0043 (`fattn-mma-f16.cuh`) pod kartą SAME-TOK (real) |
| R03 | 07#3 świeży serwer | det_probe: ten sam prompt 2× w jednym PID (reconstructed, NOTES:377) |
| R04 | 07#4 md5 tylko w tym samym trybie | plain c4708318 vs MTP 6f14e814 (real) |
| R05 | 07#5 wolna ścieżka samplera | diff 0066 bez wariantu `client-ui` (real) |
| R06 | 07#6 rocprof nie widzi PM4 | `share_ms` z rocprofv3 przy PM4 on (reconstructed) |
| R07 | 07#7 mikrobench | metryka `kernel_us` (reconstructed, NOTES:247) |
| R08 | 07#8 zombie / VRAM | serwer agenta K4 na 8097 (reconstructed, NOTES:300); „clean” to prawdziwa migawka tej maszyny |
| R09 | 07#9 BACO | vram 35 MB, gtt 23.8 GB (real liczby, NOTES:122-126) |
| R10 | 07#10 szum T=1 | wiersze `spec_sweep.jsonl` 2026-10-10 bez ms/krok (real) |
| R11 | 07#11 siatka = fala | 13.6 / 14.6 µs per proces (reconstructed, NOTES:378) |
| R12 | 07#12 roofline | `15-road-to-65.md:54-69` (real) |
| R13 | 07#13 jeden prompt | „DFlash 120 t/s” (reconstructed, NOTES:158) |
| R14 | 07#14 OOM / termika | junction 106°C (real liczba, NOTES:118); OOM `-ub 2048` (reconstructed) |
| R15 | 07#15 obciążenie CPU | loadavg 34.2 na 16 CPU (real: zmierzone na tej maszynie 2026-10-16 w trakcie buildów innych agentów) |
| R16 | 07#16 UNMEASURED | nagłówek łatki 0066 (real) |
| R17 | 07#17 losowe spowolnienia per proces | 1 proces na ramię (reconstructed, NOTES:359) |
| R18 | nadpisany działający skrypt | hash harnessu przed ≠ po (reconstructed) |
| R19 | md5 fork ≠ upstream | BIT względem upstreamu (LFM 894e56e4 vs 949a753b) |
| R20 | label ≠ binarka | `fusion/spec_sweep.jsonl` `r1-base-qwen` 41.70 vs 33.15 (real) |
| R21 | anomaly breaker | `spec_sweep.jsonl` wiersze 0–20 z 5.6 t/s (real); „clean” to label `r3final_lfm3_inst_r1 qwen mtp` |
| R22 | agent zmienia protokół | `max_tokens` 256, `cache_prompt`, `n_votes` (reconstructed, Sakana §6.3) |
| R23 | denylista (T1) | diff `spec_sweep.py` + `predicted_per_second`; „clean” to hunk testów 0053 (real) |
| R24 | benchmark na kopiowaniu | zestaw tylko „copy” (HyperQwen 381 vs 133) |
| R25 | protokoły KLD | ISTA ctx 512 vs 2048 |
| R26 | kwota cgroup | RunPod A40: nproc 96, kwota 7.65 |
| R27 | `-fit on` ze spekulacją | 5060 Ti 7.7 vs 31.8 t/s |
| R28 | PDL na sm_120 | `topk-moe.cu` @ `c15c84e83` vs `14506801c` (real) |
| R29 | build CUDA 0070 | `mmq-vec-dot.cuh` @ `f61994f58` vs `57e0bdfe4` (real) |
| R30 | crash `embd_state` | GGML_ASSERT w logu |
| R31 | baza z tej samej sesji | `r1-base-qwen` z dwóch sesji (real) |
| R32 | identyczne flagi ramion | `--spec-mtp-type iq4_xs` vs `q6_k` (11-mtp-pl-pilot +0.45% tok/krok) |
| R33 | Amdahl | 0.9 ms oszczędności z kerneli wartych 0.61 ms |
| R34 | tożsamość binarki (T5) | przełącznika brak w `.so`; „clean” to prawdziwe `~/llama-opt` |
| R35 | md5 z mierzonych przebiegów (T7) | różne teksty ramion przy identycznym A/A |
| R36 | przeciek zestawu zapieczętowanego (E-E) | diff z promptem zestawu; „clean” to prawdziwa lista promptów `build_draft_vocab.py` |

Lekcje bez reguły, bo dotyczą operacji chmurowych albo szacowania, a nie weryfikatora: `lekcja-5060ti-bezczynna`,
`lekcja-vast-cli-klucz`, `lekcja-brak-column-w-obrazie`, `lekcja-slaby-cpu-3090`, `lekcja-mtp-juz-kopiuje`,
`lekcja-bit-exact-attention`, `lekcja-sondy-en-na-polskim`. Ostatnia częściowo wchodzi w R24 (PL i EN w zestawie).

## 4. Jak inni agenci mają korzystać z fabryki od teraz

1. **Implementer** (podagent na hipotezę):
   - robi łatkę za przełącznikiem w swoim worktree i build w osobnym `inst/`;
   - potem `card new` → wypełnienie pól → `card fill` (pod `flock -s /tmp/quiet.lock nice -n 10`) → `card check` →
     `register`;
   - może wykonać `verify --dry-run`, żeby zobaczyć plan i znaleziska G0;
   - **nie uruchamia `verify` w trybie rzeczywistym**, nie czyta `sealed/prompts.jsonl`, nie edytuje `factory/`,
     `fusion/greedy.sh`, `spec_sweep*` ani `tools/`.

   W raporcie podaje ścieżkę karty i jej sha256, a nie liczby z własnych pomiarów jako wynik.
2. **Planista** (agent główny):
   - uruchamia `./factory verify <karta>` w oknie GPU. Weryfikator sam bierze locki, robi pauzy i sprawdza
     `pgrep 8080`;
   - do commita wpisuje werdykt z ledgera: `ledger:<seq>/<sha8>`, mediana i CI;
   - przed scaleniem do `amd-opt` wykonuje `./factory merge-check <sha> --repo <repo>`;
   - wyniki do wiki generuje przez `./factory report --drafts`.
3. **Zmiana harnessu** (kod fabryki, reguły, zestaw, `greedy.sh`, `spec_sweep.py`, `kld_gate.py`) idzie osobnym
   commitem i kończy się komendą `./factory harness lock --reason ...`. Wiersz blokady trafia do ledgera.
4. **Nowy incydent** oznacza najpierw fixture z artefaktu, potem regułę `rNN_*.py`, potem `rules test` i
   `harness lock`. To wzorzec KernelGuard: tanie reguły zawsze włączone, a znaleziska drogiego audytu destylowane
   do reguł.
5. **Pierwsze uruchomienie GPU** (proponowane, ok. 20 min, na decyzję Planisty):

   ```bash
   cd ~/qwen-opt/factory && ./factory verify claims/2026-10-17-mmq-epi-0070.json
   ```

   Spodziewany werdykt to `NEEDS-HUMAN` (R29: CUDA build na `amd-opt`) albo `INVALID`/`NULL`, zależnie od pomiaru.
   Ten przebieg jednocześnie waliduje fabrykę na GPU. Potem warto zrobić X2 z 15f §7 na 0055, 0060 i 0066–0069.

## 5. Ograniczenia (uczciwie)

- **Brak walidacji na GPU.**
  - Ścieżka rzeczywista (`_block` → `measure.serve_run` → HTTP → `greedy.sh`) jest przetestowana na atrapie serwera.
    Prawdziwy `llama-server` może odpowiadać inaczej w szczegółach `[NIEZWERYFIKOWANE]`: na przykład czy permisywna
    gramatyka `root ::= [^\x00]*` przejdzie parser GBNF i czy `top_logprobs` działają w trybie MTP.
  - Czasy bloków (Qwen: przebieg serwera ok. 3 min, `test-backend-ops -o MUL_MAT` z filtrem) to szacunki
    `[SZACUNEK]`. Blok przekraczający 290 s kończy się `INVALID` z jawnym powodem, a nie cichym obcięciem.
- **Izolacja to konwencja i hashe, nie piaskownica.**
  - Każdy agent z powłoką może przeczytać zestaw zapieczętowany. R36 wykrywa tylko dosłowne 8-gramy w diffie, nie
    przeciek „tematyczny” (E-E).
  - Ledger chroni przed przypadkową edycją i przed edycją bez przeliczenia łańcucha. Ktoś, kto przepisze cały łańcuch
    i `head`, nie zostanie wykryty bez zewnętrznej kotwicy `[INFERENCE]`. Propozycja: kopiować sha256 `ledger.head`
    do `wiki/log.md` przy każdym wpisie.
- **Bramka near-tie** liczy margines z `logprob` serwera, a nie z logitów FP32 referencji jak tqLLM. Referencją jest
  nasz kwantyzowany przebieg bazy. Założenie „różnica logprob = różnica logitów” wymaga, żeby llama-server liczył
  `top_logprobs` z pełnego softmaxu bez samplera; z kodu (`server-task.cpp:264-307`) wynika to tylko pośrednio
  `[NIEZWERYFIKOWANE]`. Kill z 15f X4 (margines > 0.5) dalej czeka na GPU.
- **Zakres G2:** prompty `greedy.sh` są krótkie, więc md5 nie pokrywa ścieżek prefillu (np. MMQ J ≥ 48 w 0070).
  Dla takich zmian G1 (`test-backend-ops`) i klasa KLD są ważniejsze od md5.
- **Probe `timing` dla klasy BIT:** `NULL` nie odróżnia „zmiana się nie wykonała” od „brak zysku”. Lepszy jest
  `probe log` (np. `GGML_HIP_PM4_DEBUG=3` + nazwa kernela), gdy łatka daje sygnał w logu.
- **Koszt:** Qwen MTP to ok. 45 min GPU na twierdzenie przy 2 rundach `[SZACUNEK]`, więcej niż ~27 min z 15f. Każdy
  przebieg zawiera oba zestawy i każde ramię ma 2 procesy na rundę. Wspólna baza w stylu `loo.py` (k przełączników
  w jednej sesji) **nie jest zaimplementowana**.
- **Czego z 15f §5.5 nie zbudowano:**
  - `claimcheck` (jest tylko R12 na tekście);
  - `plot.py`, `queue.py` z kalibracją (kalibracja jest tylko w raporcie);
  - backfill 70 łatek jako `UNVERIFIED-HISTORICAL`;
  - integracja z `cloud/bench.sh` (CUDA);
  - `spec_sweep.py --prompt-set` (zamiast tego własny sterownik z identycznym ciałem żądania);
  - G6 (platforma) i formalny przepływ G7 (jest tylko werdykt `NEEDS-HUMAN`);
  - LLM do projektu ablacji.
- **Heurystyki reguł statycznych:**
  - R28 i R29 parsują preprocesor bez rozwijania makr. Makra pochodne HIP z innych plików znają tylko z
    `common.cuh`, który weryfikator podaje z drzewa kandydata.
  - R03 i R04 są w weryfikatorze spełnione z konstrukcji (`greedy.sh` uruchamia świeży serwer na tryb). Chronią
    raczej dowody zbierane ręcznie.
- **Preflight bywa ostrożny:**
  - R08 odmawia, gdy działa jakikolwiek `llama-server` albo proces z kontekstem KFD (poza keepawake).
  - R14 odmawia startu przy junction ≥ 90°C. W czasie testów sysfs pokazał 94°C, gdy GPU pracowało dla innego
    agenta. Pauza 45 s powinna wystarczyć do ostygnięcia `[INFERENCE]`, ale próg może wymagać strojenia po
    pierwszych przebiegach.
- **Karta pinuje `~/llama-opt`** (nadpisywany katalog). Po reinstalacji produkcji karta 0070 przestanie przechodzić
  G0 i trzeba ją ponownie wypełnić i zarejestrować. To zamierzone (lekcja „label ≠ binarka”).

## 6. Dowody wykonanych sprawdzeń

- `python3 -m unittest discover -s tests`: **57 testów OK, 29.5 s** (2026-10-16), tylko CPU.
- `./factory rules test`: 0 rozbieżności na 36 regułach i ich fixture'ach.
- `./factory rules backtest` na `~/qwen-opt/spec_sweep.jsonl` (194 wiersze), `~/KERNEL/qwen-opt/spec_sweep.jsonl` (182)
  i `fusion/spec_sweep.jsonl` (63): liczby w §1.
- Backtest R28/R29 na `git ls-tree` gałęzi `amd-opt` i `cuda-compat` w `~/llama-master` (tylko odczyt): liczby w §1.
- Denylista na 70 plikach `KERNEL/qwen-opt/patches/llama.cpp-amd-opt/*.patch`: 0 trafień.
- `./factory verify claims/2026-10-17-mmq-epi-0070.json --dry-run`: 12 bloków, G0 bez odmów (po `harness lock` i
  `register`), 5 znalezisk R29.
- `./factory ledger verify`: łańcuch OK, 2 wiersze.

## 7. Do bazy wiedzy

| folder | tytuł (plik) | co wpisać | liczby i źródło |
|---|---|---|---|
| `narzedzia/` | Fabryka v1: `factory` CLI (`fabryka-cli.md`), nowa | Komendy, role, tryby dry-run/fake, zasady GPU, gdzie leżą karta, ledger i runy | 57 testów OK w 29.5 s; 36 reguł; zestaw 10 promptów `1e6c3a4b…`; harness `4163856fa42e` (`qwen-opt/factory/ledger.jsonl` seq 0); ten raport §2, §4 |
| `metody/` | aktualizacja [[fabryka-v1]] | `status: aktualne` dla części zbudowanej; link do narzędzia; lista niezbudowanych elementów (§5); reguła werdyktu z REFUTED przez `kill` | 16h §2.2, §5 |
| `metody/` | aktualizacja [[zestaw-odlozony]] | Zestaw `sealed-v1` istnieje: 10 promptów (5 new-writing / 5 copy-edit, 4 PL / 6 EN, 4 edycje agentowe), hash przypięty w kodzie, werdykt na nim, spec6 obok | `factory/sealed/prompts.jsonl`, `fk/sealed.py` |
| `metody/` | aktualizacja [[pomiar-abba]] | ABBA/BAAB z parami sąsiednich procesów, A/A z dwóch procesów tej samej binarki w rundzie, MDE = max(próg, 2×\|A/A\|) | `fk/stats.py`; progi 0.2/0.3/0.5% z 15f E-B |
| `eksperymenty/` | Backtest reguł fabryki na historii (`2026-10-16-backtest-regul-fabryki.md`), nowa | X1 z 15f §7 przechodzi: R21 1/1 incydent, 0 FP na 194 i 182 wierszach (wcześniej 5/182); R23 0/70 łatek; R29 0 FP na `cuda-compat`; R20 7 labeli z dryfem | 16h §1, §6 |
| `lekcje/` | aktualizacja [[lekcja-pdl-sm120]] | Reguła R28 znalazła trzeci przypadek: `fattn-kvq.cu` `flash_attn_kvq_combine_fwht` (`3a1279f95`) bez `ggml_cuda_pdl_sync`, poza `FATTN_KVQ_AVAILABLE`; dziś prawdopodobnie nieosiągalny na CUDA `[INFERENCE]` | `git show cuda-compat:ggml/src/ggml-cuda/fattn-kvq.cu` (~l. 590, launch ~701) |
| `lekcje/` | aktualizacja [[lekcja-label-to-nie-binarka]] | R20 na historii: `DRAFT_N=4 qwen mtp rocm` 28.94–41.74 ms/krok, `r1-base-qwen` 33.15–41.81 (fusion) | `rules backtest` na `spec_sweep.jsonl` i `fusion/spec_sweep.jsonl` |
| `latki/` | aktualizacja notatki łatki 0070 (jeśli istnieje) | Karta `2026-10-17-mmq-epi-0070` zarejestrowana (ledger seq 1), czeka na ~20 min GPU; R29 = CUDA build na `amd-opt` (naprawione w `cuda-compat` `57e0bdfe4`) | `factory/claims/2026-10-17-mmq-epi-0070.json` |
| `AUDYT.md` | wiersze dla liczb powyżej | — | źródła jak wyżej |
