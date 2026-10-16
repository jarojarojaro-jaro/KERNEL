# Fabryka v1: karta twierdzenia, ledger, weryfikator

Fabryka zamienia pomysł na łatkę w liczbę, której da się zaufać. Numerów do `ledger.jsonl` nie wpisuje ani człowiek,
ani agent, który wymyślił zmianę. Wpisuje je tylko kod weryfikatora (`factory.py verify`), który implementer nie może
zmienić bez śladu. Projekt opisuje raport `KERNEL/product/research/15f-agentowa-nauka.md` §5, a stan wdrożenia raport
`16h-fabryka-v1.md`.

Wymagania: tylko Python 3 stdlib oraz `bash`, `curl` i `jq` (dla `fusion/greedy.sh`). Wszystkie komendy poza
`verify` w trybie rzeczywistym działają na CPU.

## 1. Przepływ w pięciu komendach

```bash
cd ~/qwen-opt/factory
./factory card new 2026-10-17-moj-pomysl --author agent:Impl-17       # szablon claims/<id>.json
#   wypełnij: hypothesis, metric, expected, kill, correctness_class, switch, probe, attacked, ops
./factory card fill claims/2026-10-17-moj-pomysl.json \
    --base-build ~/wt/x/base-inst --cand-build ~/wt/x/inst \
    --repo ~/wt/x --base <sha bazy> --cand <sha kandydata>            # sha256 binarek i modelu, touched_paths z diffa
./factory card check claims/2026-10-17-moj-pomysl.json                # schemat + bramka statyczna, bez GPU
./factory register claims/2026-10-17-moj-pomysl.json                  # zamrożenie karty PRZED pomiarem
./factory verify claims/2026-10-17-moj-pomysl.json --dry-run          # plan bloków GPU, nic nie uruchamia
./factory verify claims/2026-10-17-moj-pomysl.json                    # Planista: pomiar, werdykt do ledgera
./factory report --out /tmp/fabryka.md                                # markdown dla wiki
```

`card fill` liczy sha256 modelu GGUF (17 GB, ok. 20 s za pierwszym razem, potem z `cache/`). Uruchamiaj go jak build:
`flock -s /tmp/quiet.lock nice -n 10 ./factory card fill ...`.

## 2. Kto co robi

| rola | uruchamia | nie robi |
|---|---|---|
| Implementer (podagent na hipotezę) | łatkę z przełącznikiem env, build, `card new/fill/check`, `register` | nie czyta `sealed/prompts.jsonl`; nie uruchamia `verify` bez `--dry-run`; nie edytuje `factory/`, `fusion/greedy.sh`, `spec_sweep*`, `tools/` |
| Planista (agent główny) | `verify`, `harness lock`, `merge-check`, `report` | nie poprawia ręcznie wierszy ledgera |
| Weryfikator (ten kod) | bramki G0–G5, jedyny zapis werdyktów | nie widzi rozumowania implementera, tylko kartę, diff i binarki |
| Człowiek | zgoda na numerykę (KLD, NEAR-TIE), na merge, na zmianę harnessu | — |

Zmiana harnessu, czyli kodu fabryki, reguł, zestawu zapieczętowanego, `fusion/greedy.sh`, `spec_sweep.py` albo
`tools/kld_gate.py`, idzie osobnym commitem. Potem Planista wykonuje
`./factory harness lock --reason "co i kto zatwierdził"`. Bez tego `verify` odmawia pracy.

## 3. Karta twierdzenia (`claims/<id>.json`)

Pełna lista pól jest w docstringu `fk/card.py`. Przykład z prawdziwymi hashami to
`claims/2026-10-17-mmq-epi-0070.json`: łatka 0070, wpisana jako UNMEASURED.

- `hypothesis`: jedno falsyfikowalne zdanie. `mechanism`: dlaczego zmiana ma zadziałać.
- `profile`: `qwen-mtp` | `qwen-plain` | `lfm`. Flagi serwera, prompty, liczba tokenów, seedy i rundy należą do
  harnessu (`fk/profiles.py`), nie do karty.
- `metric`: tylko metryki end-to-end: `ms_step`, `ms_token`, `tok_step`, `tps` (serwer) albo `pp_tps`, `tg_tps`
  (llama-bench). Mikrobenchmark nie daje werdyktu (reguła R07).
- `expected.effect_pct`: przewidywany efekt w %, dodatni = lepiej (niższe ms albo wyższe t/s).
- `kill.effect_pct_below`: próg wpisany przed pomiarem. Jeśli cały 95% CI leży poniżej progu, werdykt to `REFUTED`.
- `correctness_class`: `BIT` (md5 równe), `SAME-TOK` (host/sampler, md5 równe), `NEAR-TIE` (pierwszy rozjazd greedy to
  remis ≤ 0.1 logita), `KLD` (bramka `tools/kld_gate.py`).
- `switch`: każda zmiana siedzi za przełącznikiem env, np. `{"name": "GGML_HIP_X", "on": "1", "off": "0"}`.
- `probe`: jak G3 sprawdza, że zmiana się wykonała:
  - `log`: regex w logu serwera przy `on`, brak przy `off`;
  - `md5`: `off` przywraca md5 bazy (nie dla klasy BIT);
  - `timing`: ramię A to ta sama binarka z `off`.
- `attacked.share_ms`: czas atakowanych kerneli w ms/krok z profilu (pm4trace, `GGML_HIP_PM4_DEBUG=3`). Pole jest
  wymagane dla metryk ms, bo z niego liczy się bramka Amdahla.
- `ops`: opy dla `test-backend-ops -o OP` (G1); `"MUL_MAT|type_a=q4_K"` dodaje filtr `-p type_a=q4_K`, żeby blok
  zmieścił się w 5 minutach.
- `builds`, `model_sha256`, `touched_paths`: wypełnia `card fill`.

`register` zapisuje w ledgerze sha256 karty. Każda późniejsza zmiana karty to nowy sha256, więc `verify` odmówi pracy
do ponownej rejestracji, a stara wersja zostaje w ledgerze.

## 4. Bramki (od najtańszej)

| bramka | co sprawdza | koszt |
|---|---|---|
| G0 statyczna | schemat karty, rejestracja, łańcuch ledgera, pieczęć zestawu, blokada harnessu, sha256 binarek i modelu, denylista diffa (R23), przełącznik w diffie i w `.so` (R34), commit w `libllama-common`, reguły statyczne | CPU, sekundy |
| G1 build/opy | `test-backend-ops test -o OP` na kandydacie | 1 blok na op |
| G2 poprawność | `fusion/greedy.sh` na świeżych serwerach, per tryb (plain, MTP) | 2 bloki |
| | NEAR-TIE: tokeny z `top_logprobs: 2` | +2 bloki na tryb |
| | KLD: `llama-perplexity --kl-divergence` + `kld_gate.py` | +2 bloki |
| G3 czy zmiana działa | `probe` (log: 2 bloki; md5: 1 blok; timing: w ramach G4) | 0–2 bloki |
| G4 ABBA | runda nieparzysta A B B A, parzysta B A A B; każdy przebieg to świeży proces; 10 promptów zapieczętowanych + 6 spec_sweep × 2 seedy × 400 tokenów, T=1; przy zmianach samplera także wariant `client-ui` | 4 bloki na rundę |
| G5 fizyka | roofline na przebieg (R12), Amdahl (R33), anomalia (R21) | CPU |

Statystyka:
- pary to sąsiednie przebiegi (pozycje 0–1 i 2–3 rundy), więc 2 rundy dają 4 pary;
- 95% CI z rozkładu t Studenta (`--ci bootstrap` dla bootstrapu percentylowego);
- A/A to różnica dwóch procesów tej samej binarki w rundzie;
- MDE = max(próg metryki: 0.2% dla ms, 0.3% dla pp/tg, 0.5% dla t/s; 2 × mediana |A/A|; `mde_pct` z karty).

Werdykty, sprawdzane w tej kolejności:

| werdykt | warunek |
|---|---|
| `INVALID` | bramka G0–G3 albo G5 zawiodła, A/A powyżej 0.5% (ms) lub 1% (pozostałe), reguła blokująca |
| `REGRESSION` | cały CI poniżej 0 |
| `REFUTED` | cały CI poniżej progu `kill` |
| `CONFIRMED` | CI powyżej 0 i mediana ≥ MDE |
| `NULL` | pozostałe przypadki (CI zawiera 0 albo efekt jest poniżej MDE) |
| `NEEDS-HUMAN` | zastępuje `CONFIRMED`, gdy klasa to KLD/NEAR-TIE, reguła zgłosiła `NEEDS-HUMAN` (R11, R26, R28, R29) albo zestaw zapieczętowany i spec6 dają przeciwne znaki; pierwotny werdykt zostaje w `stat_verdict` |

## 5. Ledger (`ledger.jsonl`)

- Ledger jest tylko do dopisywania. Każdy wiersz ma `seq`, `prev_sha256` (sha256 poprzedniego wiersza) i `sha256`
  (sha256 kanonicznego JSON-a wiersza bez tego pola).
- `ledger.jsonl.head` trzyma sha256 ostatniego wiersza, więc wykryte zostanie także obcięcie ogona.
- Między zapisami plik ma tryb 0444.
- `./factory ledger verify` sprawdza łańcuch. Przy zerwanym łańcuchu `verify` niczego nie dopisze.

Rodzaje wierszy: `register`, `harness-lock`, `verdict`. Wiersz `verdict` zawiera:
- tożsamość: commit bazy i kandydata, sha256 każdej binarki i `.so`, sha256 modelu, `build_info` z `/props`;
- środowisko i flagi: env i argv obu ramion;
- protokół, harness i zestaw: protokół, hash harnessu, hash zestawu zapieczętowanego, kartę w całości;
- przebieg: kolejność ABBA i wszystkie próbki (żaden przebieg nie znika);
- statystykę: medianę, CI, A/A, MDE, wynik spec6 i `client-ui`;
- rozstrzygnięcie: bramki, znaleziska reguł, werdykt z powodami;
- dowody: ścieżki logów (`runs/<verify_id>/`) z sha256 każdego pliku.

`--fake` pisze do `ledger.fake.jsonl`, nigdy do produkcyjnego ledgera.

## 6. Zestaw zapieczętowany (`sealed/prompts.jsonl`)

Zestaw liczy 10 promptów, rozłącznych ze spec_sweep, `greedy.sh` i `build_draft_vocab.py`:
- czat wieloturowy PL i EN;
- kod PL (Go) i EN (TypeScript);
- ekstrakcja do JSON;
- zadanie matematyczne PL;
- 4 edycje kodu w stylu agenta (`old_string`/`new_string` albo unified diff; Python, TypeScript, C, polecenie PL).

Podział:
- klasy: 5 „new-writing” i 5 „copy-edit”;
- języki: 4 PL i 6 EN.

Sha256 zestawu jest przypięty w `fk/sealed.py` (`SEALED_SHA256`) i trafia do każdego wiersza ledgera. Zmiana zestawu jest
zmianą harnessu. `./factory sealed summary` pokazuje tylko liczności. Implementerzy nie czytają pliku, a reguła R36
sprawdza, czy w diffie nie ma 8-gramów z tego zestawu.

Werdykt liczy się na zestawie zapieczętowanym. Spec6 jest raportowany obok, a przeciwne znaki obu zestawów dają
`NEEDS-HUMAN` (klątwa zwycięzcy, 15f E-C).

## 7. Reguły (`rules/`)

Każda reguła to mały moduł `rNN_*.py` z `POLICY` (stage, severity, verdict, źródło incydentu, lekcja) i funkcją
`check(ctx)`. Ma też fixture `rules/fixtures/rnn.json` z co najmniej jednym przypadkiem „fire” i jednym „clean”,
w miarę możliwości z prawdziwego artefaktu (`kind: real`).

| # | reguła | incydent |
|---|---|---|
| R01–R17 | 17 trybów awarii z raportu 07 §2.2.4 (FMA, kolejność FA, świeży serwer, tryb md5, sampler klienta, PM4 w rocprof, mikrobench, zombie, BACO, T=1, siatka = fala, roofline, jeden prompt, OOM/termika, CPU, UNMEASURED, losowe spowolnienia) | `07#1`–`07#17` |
| R18 | harness zmieniony w trakcie (nadpisany `plan.sh`) | lekcja |
| R19 | „BIT” względem upstreamu | lekcja |
| R20 | label to nie binarka (`r1-base-qwen` 41.70 vs 33.15 ms/krok) | lekcja |
| R21 | anomaly breaker (5.6 t/s, `spec_sweep.jsonl` wiersz 15) | E-D |
| R22 | protokół (tokeny, seedy, T, cache) stały | Sakana §6.3 |
| R23 | denylista diffa | T1 |
| R24 | klasy i języki w zestawie | benchmark-kopia |
| R25 | protokół KLD | 15e |
| R26 | wątki vs kwota cgroup | chmura |
| R27 | `-fit on` ze spekulacją | 5060 Ti |
| R28 | PDL bez `ggml_cuda_pdl_sync` | 0053/0057 |
| R29 | konstrukcje HIP poza guardem | 0070 |
| R30 | assert / crash serwera | embd_state |
| R31 | baza z tej samej sesji | Lucebox |
| R32 | identyczne flagi ramion | MTP Q6_K vs IQ4_XS |
| R33 | Amdahl | 15f T8 |
| R34 | tożsamość binarki | T5 |
| R35 | teksty z mierzonych przebiegów równe | T7 |
| R36 | przeciek zestawu zapieczętowanego | E-E |

Komendy:

```bash
./factory rules list                     # tabela reguł
./factory rules test                     # fixture'y (0 mismatches)
./factory rules backtest ~/qwen-opt/spec_sweep.jsonl   # R21/R20 na historii
./factory rules text raport.md           # R12 na tekście (GB/s powyżej peaku, >100% peaku)
```

Nowa reguła powstaje z nowego incydentu: najpierw fixture z artefaktu, potem `check`, potem `harness lock`.

## 8. GPU: zasady i tryby

- `--dry-run` drukuje każdy blok GPU dokładnie tak, jak by go uruchomił (`pgrep`, `flock`, `timeout`, komenda w
  środku, pauzy). Nic nie uruchamia, nic nie zapisuje.
- `--fake` przechodzi przez cały pipeline z syntetycznymi danymi (`--fake-effect`, `--fake-md5-diff`) i zapisuje do
  `ledger.fake.jsonl`. Służy do testów i do nauki.
- Tryb rzeczywisty:
  - każdy blok to `flock /tmp/gpu.lock flock /tmp/quiet.lock timeout 290 python3 factory.py _block SPEC`;
  - przed każdym blokiem sprawdza `pgrep -f "llama-server.*--port 8080"` (odmowa, gdy działa serwer produkcyjny);
  - między blokami pauza 45 s (`--pause`), port 18471 (dozwolone 18434–18499);
  - w bloku preflight (R08 obce serwery, procesy KFD i zajęty VRAM; R09 BACO; R14 junction ≥ 90°C; R15 loadavg) i
    czyste środowisko: zmienne `GGML_*`, `LLAMA_*`, `HIP_*` wołającego są usuwane, a ustawiane są tylko te z karty i
    profilu;
  - serwer kończony jest SIGTERM, a po 15 s SIGKILL.
- `greedy.sh` uruchamia się z kopii nazwanej hashem (`runs/<id>/harness/greedy.<sha12>.sh`), nigdy z żywego pliku.

Koszt jednego twierdzenia `[SZACUNEK]`:
- Qwen MTP, 2 rundy: 8 przebiegów × ok. 3 min + 2 × greedy ok. 2.5 min + probe 2 × 1.5 min + pauzy 45 s, razem
  **ok. 45 min GPU**;
- LFM: ok. 20 min;
- metryka `pp_tps`/`tg_tps` (llama-bench, bez promptów): ok. 15 min.

## 9. Raport i merge

- `./factory report --out plik.md` renderuje tabelę werdyktów z `ledger:<seq>/<sha8>` przy każdej liczbie. Zawiera
  sekcję wyników negatywnych (szkice) i kalibrację przewidywań (zmierzone / przewidziane).
- `--drafts` zapisuje szkice notatek wiki dla wierszy z trybu rzeczywistego do `wiki-drafts/`. Do wiki wnosi je agent
  główny według `wiki/KONWENCJE.md`.
- `./factory merge-check <sha> --repo ~/llama-master` kończy się kodem 0 tylko przy werdykcie `CONFIRMED` dla tego
  commita i braku „UNMEASURED” w treści (R16).

## 10. Testy

```bash
cd ~/qwen-opt/factory && python3 -m unittest discover -s tests     # 57 testów, ok. 30 s, tylko CPU
```

- Testy budują piaskownicę: repo git z bazą i kandydatem, dwie sztuczne instalacje, model, ledger.
- Testy przechodzą przez wszystkie werdykty, odmowy (denylista, brak rejestracji, zmiana karty, zmiana harnessu,
  sha256), dry-run i CLI.
- Ścieżkę rzeczywistą `_block` → `measure.serve_run` → `fusion/greedy.sh` testują na serwerze-atrapie
  (`tests/fake_llama_server.py`), bez GPU i bez locków.

## 11. Ograniczenia

Pełna lista jest w raporcie 16h §5. Najważniejsze:
- weryfikator nie był jeszcze uruchomiony na GPU;
- izolacja przed implementerem jest konwencją plus hashe, a nie piaskownicą systemową;
- bramka near-tie działa na `top_logprobs` serwera, nie na logitach FP32 referencji;
- G2 md5 na krótkich promptach `greedy.sh` nie testuje ścieżek prefillu (np. MMQ J ≥ 48).
