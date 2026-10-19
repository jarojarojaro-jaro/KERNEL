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
| `VOID` | odmowa sprzętowa lub infrastrukturalna (bramki H0–H11, preflight R08/R09/R14/R15, serwer na :8080), padnięte ramię A albo A/A powyżej 0.5% (ms) lub 1% (pozostałe): powtórzyć, nigdy nie liczyć jako porażki (21i A3) |
| `INVALID` | wina kandydata: bramka G0–G3 albo G5 zawiodła, reguła blokująca (m.in. R37); **page fault / reset GPU = `INVALID` + kwarantanna builda (H3), nigdy `VOID`** |
| `REGRESSION` | cały CI poniżej 0 |
| `REFUTED` | cały CI poniżej progu `kill` |
| `CONFIRMED` | CI powyżej 0 i mediana ≥ MDE; strażnicy (`guards`, 1 runda ABBA llama-bench na profil) bez całego CI < −MDE, inaczej `REGRESSION` |
| `NULL` | pozostałe przypadki (CI zawiera 0 albo efekt jest poniżej MDE) |
| `NEEDS-HUMAN` | zastępuje `CONFIRMED`, gdy klasa to KLD/NEAR-TIE, reguła zgłosiła `NEEDS-HUMAN` (R11, R26, R28, R29), zestaw zapieczętowany i spec6 dają przeciwne znaki albo karta `null_rebuild` dała `CONFIRMED`/`REGRESSION`; pierwotny werdykt zostaje w `stat_verdict` |

Wiersz `verdict` ma też `reward` (= mediana/100 tylko przy `CONFIRMED`, inaczej 0), `recovery` (gdy karta ma
`task_ref.oracle_effect_pct`), `void_reason`, `sealed_draw` (seed i 10 wylosowanych id), `ci_note` i `evidence_id`.
Bootstrap CI tylko przy n ≥ 12 par; poniżej weryfikator wymusza Student t (21j §4.4: przy n = 5 bootstrap średniej
fałszywie wyklucza 0 w 17.8% przypadków).

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

Aktywny zestaw wskazuje `sealed/registry.json` (id, plik, sha256 każdego zestawu kiedykolwiek użytego); `sealed-v1` ma
10 promptów, kolejne zestawy w `sealed/pool.jsonl` po 40 (`sealed-v2`). Każdy cykl RSI-F aktywuje następny zestaw
(`factory rsi cycle PLAN --go --open` albo `factory rsi sealed rotate`), zużyty zestaw nie wraca. Każdy `verify`
losuje 10 promptów aktywnego zestawu warstwowo (5 „new-writing”/5 „copy-edit”, 4 PL/6 EN), seed trafia do ledgera
(21i A12). Zestawy są rozłączne ze spec_sweep, `greedy.sh` i `build_draft_vocab.py`; sealed-v1:
- czat wieloturowy PL i EN;
- kod PL (Go) i EN (TypeScript);
- ekstrakcja do JSON;
- zadanie matematyczne PL;
- 4 edycje kodu w stylu agenta (`old_string`/`new_string` albo unified diff; Python, TypeScript, C, polecenie PL).

Rejestr i pula leżą w `sealed/`, więc rotacja jest zmianą harnessu i wymaga `harness lock` (robi to `--open`).
`./factory sealed summary` pokazuje tylko liczności. Implementerzy nie czytają `sealed/`, a reguła R36 sprawdza, czy
w diffie nie ma 8-gramów z któregokolwiek zestawu (użytego, aktywnego, w puli).

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
  - przed każdym blokiem kod sprawdza bramki sprzętowe H0–H11 (§12; m.in. `ss -ltn 'sport = :8080'`, gpu-guard,
    hotspot < 70 °C i VRAM < 75 °C, journal wszystkich bootów, budżet GPU), po każdym bloku skanuje journal pod kątem
    page fault / ring timeout / reset; każdy blok dostaje `GGML_HIP_PM4=0` (H2);
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
cd ~/qwen-opt/factory && cpuheavy python3 -m unittest discover -s tests
```

- Testy budują piaskownicę: repo git z bazą i kandydatem, dwie sztuczne instalacje, model, ledger.
- Testy przechodzą przez wszystkie werdykty, odmowy (denylista, brak rejestracji, zmiana karty, zmiana harnessu,
  sha256), dry-run i CLI.
- Ścieżkę rzeczywistą `_block` → `measure.serve_run` → `fusion/greedy.sh` testują na serwerze-atrapie
  (`tests/fake_llama_server.py`), bez GPU i bez locków.
- `test_hwgates.py`: każda bramka H0–H11 ma przypadki „odpala” i „czysto”, plus kwarantanna, ack, budżet i odmowy
  w `Runner`/G0; `test_rsi.py`: playbooki, recenzja bez diffu, briefy, scoring k1–k3, kalibracja, cykl, snapshot.

## 11. Ograniczenia

Pełna lista jest w raporcie 16h §5. Najważniejsze:
- pierwszy przebieg na GPU: P0 (raport 22, wiersz ledgera z werdyktem 0070);
- izolacja przed implementerem jest konwencją plus hashe, a nie piaskownicą systemową;
- bramka near-tie działa na `top_logprobs` serwera, nie na logitach FP32 referencji;
- G2 md5 na krótkich promptach `greedy.sh` nie testuje ścieżek prefillu (np. MMQ J ≥ 48).
- implementer RSI-F nie ma odciętej sieci (21i A10): to konwencja w briefie, nie `unshare -n`;
- bramka „generation judge” dla klas NEAR-TIE/KLD (21i A2) nie jest jeszcze zbudowana: te klasy i tak kończą się
  `NEEDS-HUMAN`.

## 12. RSI-F: pętla samodoskonalenia bez trenowania wag (raport 21h §5, raport 22)

```bash
./factory rsi gates [--card CARD]                  # H0–H11 na żywo, nic nie uruchamia
./factory rsi hw status | ack --reason "..."       # watermark faultów, halt, kwarantanna (ack = człowiek przeczytał)
./factory rsi playbook new|check|review|accept|list|show ...
./factory rsi transfer brief|effort|score ...      # brief świeżego agenta z samego playbooka, ramiona A/B, k1–k3
./factory rsi calib [--write]                      # przewidziane vs zmierzone, |błąd|, Brier, prior P(CONFIRMED)
./factory rsi workspace --repo R --commit C --dest D   # snapshot jednego commita bez historii (21i A9)
./factory rsi aob list|validate|plan               # AMD-Opt Bench aob-v1 (aob/tasks, 21i §5)
./factory rsi cycle PLAN --dry-run | --go --open | --go [--stop-topka]
./factory preserve RUNDIR | check ID | restore ID DEST   # magazyn dowodów sha256 + zstd (21j P3)
```

- **Jedyny sygnał sukcesu:** wiersz `verdict` w trybie real z `CONFIRMED` (albo `NEEDS-HUMAN` ze `stat_verdict`
  `CONFIRMED` i notą `human-approval`). G0–G3 + `NULL` daje w rankingu SPR 0.25, nigdy 1.
- **Playbook** (`playbooks/<id>.json`, schemat w `fk/playbook.py`): `draft` tylko ze źródła będącego sukcesem;
  `candidate` po automatycznej recenzji bez diffu (0 8-gramów diffu, 0 długich linii, 0 nowych identyfikatorów,
  hashy commitów i nazwy przełącznika źródła, 0 tekstu sealed, 0 zmierzonych liczb źródła) i podpisie recenzenta
  innego niż autor; `accepted` dopiero po `CONFIRMED` świeżego agenta (inny autor) w ramieniu A na innym celu, z
  briefem, którego sha256 jest w ledgerze. Każde przejście to wiersz `note` w ledgerze; zmiana treści cofa status.
- **Transfer:** `rsi/targets/<id>.json`; brief jest generowany z celu (+ playbook w ramieniu A) i przechodzi tę samą
  recenzję; budowanie przez `rsi/build-slot.sh` (jedno drzewo buildu, CPU: `cpuheavy --quiet`, `-j2`). Kill: k1 recenzja nie przepuszcza, k2 ramię A bez G3 albo z wysiłkiem ≥ B, k3 fault.
- **Krytyk:** kalibracja z ledgera (`rsi/calibration.jsonl`, nigdy nie resetowana) daje prior do rankingu kolejki.
- **Cykl:** `--open` rotuje zestaw zapieczętowany i blokuje harness; `--go` wymaga karty `null_rebuild` (sonda szumu,
  oczekiwany `NULL`), weryfikuje karty w kolejności rankingu, staje przy pierwszym faultcie (H3) albo budżecie (H6),
  `--stop-topka`: każdy blok GPU zatrzymuje serwer na :8080 dopiero WEWNĄTRZ swojego hold (pod lockami); fabryka go
  nie wznawia — robi to `tools/topka-keeper.sh`, gdy lock GPU jest wolny. Procesy bloków (llama-server/bench/
  perplexity/test-backend-ops) startują pod `taskset -c 2-5` (`paths.HOST_PIN`).
- **Bramki sprzętowe** (`fk/hwgates.py`, odmowa w kodzie): H0 locki GPU, H1 gpu-guard + start przy hotspot < 70 °C
  i VRAM < 75 °C, H2 PM4=0, H3 kwarantanna + halt, H4 journal wszystkich bootów od watermarku, H5 kernel ⇒ `ops`,
  H6 ≤ 60 min GPU/24 h i ≤ 15 h/30 dni, H7 zakaz zegarów/napięć/limitów mocy (diff, argv, env, baseline sysfs: power1_cap,
  perf level, sha tylko sekcji OD_SCLK/OD_MCLK/OD_VDDGFX_OFFSET — krzywa wentylatora `gpu_od/fan_ctrl` wyłączona),
  H8 `ss -ltn 'sport = :8080'`, H9 SSD ≤ 2 GiB stanu i ≤ 512 MiB/24 h, H10 chmura z watchdogiem, H11 CPU.
