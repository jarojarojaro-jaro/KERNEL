# 21j — morluto/flameox: co to jest i co z tego weźmiemy

Data: 2026-10-19. Autor: podagent ResFlameox. Praca tylko na CPU, koszt $0, **zero uruchomień GPU**.

Źródła:
- https://github.com/morluto/flameox, klon w `~/qwen-opt/research-src/flameox`, HEAD `c7ea167` z 2026-10-11, wersja 0.2.9;
- środowisko `uv sync --extra dev --extra inference --extra trace --extra cpu`, `nice -n 19`, pytest `-n 4`;
- dema i skrypty w `~/qwen-opt/research-src/flameox-demo/`: `fx_union.py`, `fx_cov.py`, `fx_list.py`, pliki `*.samples.json`, `kv-*.json`, `exp.json`.

Oznaczenia: `[INFERENCE]` to mój wniosek, `[SZACUNEK]` to wycena, `[NIEZWERYFIKOWANE]` to rzecz, której nie sprawdziłem.
Raport siostrzany o drugim repo tego autora: [21k-smokinggun](21k-smokinggun.md).

---

## 0. Najważniejsze

1. **Flameox nie jest silnikiem, nie ma kerneli i nie rysuje flame graphów.**
   - To serwer MCP i CLI w Pythonie (24 093 linii `src/`), który uruchamia **cudze** profilery i benchmarki albo czyta ich artefakty.
   - Zwraca agentowi ograniczone, typowane „dowody” i opcjonalnie zapisuje je w niezmiennym magazynie adresowanym sha256.
   - Opis z README: „Bounded local runtime evidence for coding agents” (`README.md:11`).
   - „Flame” to tylko marka (maskotka). W kodzie nie ma renderowania SVG ani flame graphów. Czyta Speedscope z py-spy i stosy z `perf script` (`providers/cpu.py`).
2. **Dla AMD jest prawie bezużyteczny.**
   - ROCm obsługuje tylko w jednej postaci: `rocprofv3 --output-format pftrace` (`providers/capture.py:327-355`).
   - Analiza to listing pierwszych ≤ 1000 slice'ów według czasu, **bez agregacji per kernel** (`workers/perfetto.py:24-74,152-157`; limit 1000 wierszy: `docs/runtime-safety.md:110`). W naszym trace `prof/mtp4` jest 289 691 kerneli w stanie ustalonym, więc pierwsza strona pokrywa 0.35% populacji.
   - Brak ATT, PMC i odczytu CSV z rocprofv3.
   - Cała obsługa ROCm ma jeden test, który sprawdza tylko walidację argumentów (`tests/providers/test_rocprof.py:14-38`).
   - Vulkan i HIP nie występują nigdzie poza nazwą tabeli Nsight `VULKAN`.
   - NVIDIA jest obsłużona szerzej (nsys, ncu, compute-sanitizer, Triton), ale tego nie mogłem sprawdzić `[NIEZWERYFIKOWANE]`.
3. **Statystyka eksperymentów jest słabsza niż w naszej fabryce v1.**
   - Metryka to wyłącznie `wall_time_ns` całego procesu, razem ze startem (`runtime_contracts.py:912-915`). Dla llama-server oznacza to ładowanie modelu.
   - Kolejność w blokach jest losowa, a nie ABBA (`runtime.py:1611-1616`).
   - Nie ma ramienia A/A ani MDE.
   - Werdykt opiera się na estymacie punktowej (`runtime.py:3159-3166`). CI to percentile bootstrap z 1999 resamplami (`runtime.py:3225-3246`).
   - Zmierzyłem, że **percentile bootstrap przy małym n jest antykonserwatywny**: przy n = 5 wyklucza 0 w 17.8% przypadków dla średniej i w 7.4% dla mediany, przy nominalnych 5%; Student t daje 5.5% (§4.4).
   - Własne demo A/A flameoxa dało CI [0.58, 29.80] ms, czyli **wykluczające 0 dla identycznych programów**.
4. **Dojrzałość: młody projekt jednej osoby, pisany z agentami, ale z dobrą dyscypliną testów.**
   - 523 commity w 79 dni, od 2026-07-25 do 2026-10-11.
   - 400/400 issues założył sam autor.
   - 9 commitów współtworzył Devin.
   - Na naszym CPU: **649 passed, 11 skipped w 98 s**.
   - Licencja MIT. 210 gwiazdek, 14 forków (`gh api`, 2026-10-19).
5. **Werdykt: nie instalujemy flameoxa ani jako narzędzia, ani jako MCP w omp.** Powody:
   - katalog MCP ma 1.05 MB;
   - narzędzia capture pozwalają agentowi samodzielnie uruchomić GPU, co łamie H0;
   - polityka blokuje `LD_LIBRARY_PATH`, a od niego zależy wybór buildu w A/B;
   - analiza AMD jest płytka.

   **Warto natomiast przenieść 6 konkretnych zasad.** Najtańsze i najcenniejsze trzy:
   - (P1) zakaz percentile bootstrap dla małego n w `factory`;
   - (P2) inwarianty pokrycia w naszych skryptach profilu;
   - (P3) magazyn dowodów adresowany sha256 z kompresją zstd pod ledger i RSI-F.

   Ranking jest w §7.

---

## 1. Czym jest flameox (odpowiedź na pytanie „engine? profiler? kernels? flame graph?”)

| pytanie | odpowiedź | dowód |
|---|---|---|
| silnik inferencji? | nie | brak kodu modelu, `src/` to orkiestracja i parsery |
| profiler? | nie własny; **koordynator** cudzych (py-spy, perf, memray, rocprofv3, nsys, ncu, compute-sanitizer, torch profiler, xctrace, Node) | `docs/adapters.md:57-68`, `providers/capture.py` |
| kernele? | nie; czyta wyniki walidacji kerneli i cache autotune Tritona, „does not generate kernels, wrap compilers” | `docs/investigations.md:44-49` |
| flame graph? | nie renderuje; „does not … launch native viewers” | `docs/runtime-safety.md:143-145` |
| dla inferencji? | tylko offline: czyta eksporty AIPerf, `vllm bench`, `sglang bench_serving` i trace Mooncake, bez promptów | `docs/adapters.md:67,70-72`, `providers/inference_exports.py`, `providers/aiperf.py` |
| dla kogo? | dla agentów kodujących przez MCP (Codex, Claude Code, opencode…) oraz przez CLI | `README.md:25-56` |

**Model pracy** (`docs/investigations.md:8-11`): symptom → artefakt albo capture → ograniczony dowód → hipoteza agenta → eksperyment rozstrzygający.
Flameox odróżnia twierdzenia *observed*, *derived* i *inferred*. Wprost pisze, że profil nie dowodzi przyczyny ani poprawy (`README.md:79-83`).

---

## 2. Język, zależności, backendy

- **Python ≥ 3.12**, `uv`, hatchling. Zależności (`pyproject.toml`):
  - `mcp==2.3.0`, pydantic 2.13, duckdb 1.5 (tylko w pamięci), pyarrow, psutil, pyperf, rfc8785;
  - opcjonalnie: aiperf 0.13, memray, perfetto 0.57, py-spy 0.4, torch.
- **Rozmiar**: `src/` 24 093 linii, `tests/` 14 811 linii, 334 funkcje testowe, 660 przypadków po parametryzacji (`wc -l`, `grep def test_`, wynik pytest).
- **Backendy GPU**:

| dostawca | capture | analiza | uwagi |
|---|---|---|---|
| NVIDIA nsys | `nsys profile`, eksport `parquetdir` | `inspect_gpu_launches`, `summarize_trace_operations/lifecycle` | odrzuca SQLite z nsys z zasady (`docs/adapters.md:209-211`) |
| NVIDIA ncu | `ncu` + `extras/python/ncu_report.py` | `inspect_gpu_kernel_metrics` | wymaga czytnika dostarczanego przez vendora (`providers/nsight_compute.py:27-31`) |
| compute-sanitizer | tak | `inspect_sanitizer_failures` | — |
| Triton | cache autotune | `inspect_triton_autotune` | przebieg z zimnym cache (`docs/adapters.md:109-113`) |
| **AMD rocprofv3** | `--output-format pftrace`, domyślnie `--kernel-trace` | **tylko** `summarize_trace`, czyli surowe slice'y | brak ATT, PMC, CSV i rocpd; brak `inspect_gpu_launches` dla AMD (`runtime_contracts.py:1200-1205`) |
| Vulkan / HIP kod | — | — | brak |

---

## 3. Architektura (przeczytana w kodzie)

- **`AnalysisRuntime`** (`runtime.py`, 3344 linie) posiada:
  - rejestr operacji;
  - broker procesów;
  - ograniczony scratch sesji;
  - cache LRU analiz.

  CLI i MCP to cienkie projekcje tego samego rejestru (`docs/architecture.md:37-50,72`).
- **Rejestr**: 26 operacji (`runtime_contracts.py:1085-1270`). MCP wystawia **51 narzędzi**: 26 analiz, 20 `capture_and_*` i 5 do dowodów i setupu (`flameox mcp inspect`).
- **Broker procesów** (`execution.py`, 1653 linie):
  - argv bez shella, `start_new_session`;
  - śledzenie potomków przez psutil także poza grupą procesów (`execution.py:679-762,972-1036`);
  - limity czasu, RSS, wyjścia i przyrostu dysku;
  - blokada zmiennych środowiska `LD_*`, `PYTHONPATH` i nazw z TOKEN/KEY/SECRET (`environment_policy.py:5-33`).
- **Izolowane workery**: parsery ciężkie albo niebezpieczne działają w podprocesie z typowanym protokołem i budżetem (`workers/harness.py`, `workers/protocol.py`).
- **Magazyn dowodów** (`docs/storage-and-evidence.md:44-58,64-90,105-122`):
  - artefakty pod `artifacts/sha256/<prefix>/<digest>/payload`;
  - manifest kanonizowany RFC 8785, a `evidence_id` = sha256 manifestu;
  - publikacja przez staging, `fsync` i atomowy `rename`;
  - bez SQLite, bez mutowalnych indeksów i bez GC;
  - natywne bajty zachowywane nawet przy błędzie dekodera (`docs/adapters.md:192-194`).
- **Eksperymenty** (`runtime_contracts.py:875-945`, `runtime.py:1604-1617,3118-3246`):
  - 2–16 przypadków i 1–100 bloków;
  - kolejność losowana seedem w każdym bloku;
  - paired differences względem pierwszego przypadku;
  - `median_difference` albo `mean_difference`;
  - opcjonalna wyrocznia semantyczna, czyli osobny argv uruchamiany po każdym przebiegu.
- **Zasady dowodu**, najlepsza część projektu (`docs/adapters.md:144-171,178-181`):
  - selekcja semantyczna *przed* obcięciem;
  - `rows_observed`, `complete` i truncation opisują tę samą populację;
  - niedopasowany selektor to „incomplete”, a nie dowód braku;
  - tożsamość serii obejmuje device, dtype, variant, scope i worker;
  - jednostki normalizowane przed agregacją;
  - nierozwiązane referencje to uszkodzony dowód.

---

## 4. Twierdzenia i ich weryfikacja

### 4.1 Tabela twierdzeń

| twierdzenie | źródło | werdykt | jak sprawdziłem |
|---|---|---|---|
| „helps agents … burn down hotspots in … GPU kernels, and inference stacks” | `pyproject.toml:8` | **przesadzone dla AMD**; dla NVIDIA `[NIEZWERYFIKOWANE]` | kod rocprof/perfetto (§0 pkt 2); dla inferencji tylko czytniki offline, bez capture (`docs/adapters.md:67`) |
| zestaw testów działa | `docs/testing.md` | **potwierdzone** | `uv run pytest -q -n 4`: 649 passed, 11 skipped, 98.35 s (memray i Node nie zainstalowane) |
| wyniki wydajności samego flameoxa (usunięty `docs/performance.md`) | `git show f91942c^:docs/performance.md` | **arytmetyka się zgadza**, uczciwie opisane jako obserwacje z macOS arm64 | 159.9 → 17.7 ms = 9.0×; 6.174 → 5.791 s = −6.2% (autor sam pisze „not statistically established”). To jedyne liczby wydajności w historii repo; dotyczą narzędzia, nie inferencji |
| kontrola spójności werdyktów walidacji kerneli | `docs/investigations.md:155-159` | **potwierdzone** | demo `kv-cand.json`: producent `pass`, nmse 9e-7 > próg 5e-7 → `status: inconclusive`, `rule: numeric_comparator` |
| porównanie benchmarków po zgodnej tożsamości | `docs/investigations.md:92-97` | **potwierdzone**, ale tylko jako ratio średnich, **bez CI** | nasze llama-bench z 5060 Ti (§4.2) |
| „within_threshold does not establish equivalence”, interwał „not a calibrated equivalence test” | `docs/investigations.md:57-62` | **prawdziwe zastrzeżenie, a problem większy niż sugeruje** | §4.3–4.4 |
| capture zwraca typowaną remediację przy braku dostawcy | `docs/adapters.md:36-42` | **częściowo** | `perf` przy `perf_event_paranoid=4`: wynik `DECODE_FAILURE` „zero-sized data”, bez wskazania przyczyny (uprawnienia) |

### 4.2 Nasze dane przez `compare_benchmarks`

Przekonwertowałem `~/qwen-opt/cloud/results/5060ti-20261016/lb/qwen38-27b-q3.*.jsonl` (`samples_ns`, po 5 próbek, rundy r1–r8) na `flameox.benchmark-samples.v1`. Wynik:

| test | base-default [ms] | fork-safe [ms] | ratio |
|---|---|---|---|
| pp512 | 488.70 | 499.35 | 1.0218 |
| pp4096 | 3924.17 | 4012.70 | 1.0226 |
| tg128 | 4453.87 | 4369.55 | 0.9811 |

- **Kontrola**: 128 / średnia(28.78, 28.70) t/s = 4.453 s oraz 128 / średnia(29.28, 29.31) = 4.369 s. Zgadza się z `avg_ts` w plikach.
- **Czego brakuje**:
  - nie ma CI;
  - nie wie, że rundy tworzą palindrom (r1/r8, r2/r7, r3/r6, r4/r5), więc nie korzysta z parowania przeciw dryfowi;
  - trzeba usunąć `variant_id`, bo należy do tożsamości serii (`benchmark_samples.py:41`), a inaczej serie A i B się nie łączą.

  Fabryka v1 robi to lepiej: ABBA, A/A, MDE, t-CI (`~/qwen-opt/factory/fk/stats.py:1-21,53-61,98-122`).

### 4.3 Demo eksperymentu A/A (CPU, `exp.json`)

- **Ustawienia**: 3 przypadki (`base` = `sum(range(3e6))`, `cand` = 6e6, `aa` = kopia `base`), 5 bloków, seed 42.
- **Ograniczenie**: 7 bloków odrzucił limitem źródeł, 42 > 32 (`LIMIT_EXCEEDED`).
- **Różnice `aa − base` [ms]**: 0.58, 29.80, 1.04, 14.62, 0.95.
- **Wynik flameoxa**: mediana 1.04 ms, CI `bootstrap.percentile.paired.median_difference.v1` = **[0.58, 29.80] ms**, klasyfikacja `within_threshold`.

CI wyklucza 0 dla dwóch identycznych programów. Przy n = 5 wystarczy, że wszystkie różnice mają ten sam znak. Pod H0 zdarza się to z prawdopodobieństwem 2/2⁵ = 6.25%. Klasyfikacja jest poprawna tylko dlatego, że opiera się na estymacie punktowej, a nie na CI.

### 4.4 Pokrycie CI: symulacja (`fx_cov.py`, 1500 prób na n, N(0,1), H0 prawdziwa)

| n | percentile bootstrap, mediana | percentile bootstrap, średnia | Student t |
|---|---|---|---|
| 4 | 12.3% | 19.7% | 5.1% |
| 5 | 7.4% | 17.8% | 5.5% |
| 6 | 6.7% | 14.9% | 5.7% |
| 8 | 7.9% | 11.6% | 4.8% |
| 10 | 6.5% | 10.8% | 4.8% |
| 12 | 5.7% | 7.7% | 4.3% |

Wartości to odsetek prób, w których 95% CI wykluczył 0. Nominalnie powinno to być 5%, a SE symulacji ≈ 0.6 pp.

**Wniosek dla nas:**
- `factory` ma `summarize(method="bootstrap")` z percentile bootstrap (`fk/stats.py:43-50,89-95`). Domyślnie używa `t`, więc dziś jest bezpiecznie.
- Ścieżka bootstrap przy typowym n par z 2–4 rund ABBA da jednak 2–3× więcej fałszywych wykluczeń 0.
- Patrz P1.

### 4.5 Koszt katalogu MCP (`fx_list.py`, prawdziwy klient stdio)

- `tools/list`: 51 narzędzi, **1 047 166 B**, w tym:
  - output schemas: 752 863 B;
  - input schemas: 269 997 B;
  - opisy: 14 112 B.
- Klient, który podaje modelowi opisy i input schemas, wkłada ~284 KB. To około **70 tys. tokenów** przy ~4 B/token `[INFERENCE]`, zanim agent cokolwiek zrobi.
- Autor zgłaszał to jako problem: issue #501 „Reduce MCP catalog size”, zamknięte. Rozmiar dalej jest duży.

---

## 5. Dojrzałość

| cecha | wartość | źródło |
|---|---|---|
| commity | 523 w 79 dni (6.6/dzień), 86 w dniu 2026-10-11 | `git log` |
| autorzy | morluto; 9 commitów `Co-Authored-By: Devin`; 2 zewnętrzne PR (helenanova, mikemikimike), 24 PR bota | `git log --format=%B`, `gh pr list` |
| issues | 400/400 założone przez autora (backlog agenta, nie społeczność) | `gh issue list --state all -L 400` |
| wydania | tag v0.2.9 w repo; GitHub Releases pokazuje „Latest” 0.2.6 z 2026-09-07 (niespójność) | `git tag`, `gh release list` |
| CI | ruff, mypy strict, import-linter (rdzeń nie zależy od transportów), testy deterministyczne i procesowe osobno, cotygodniowy cron | `.github/workflows/ci.yml`, `pyproject.toml` |
| testy | 649/660 OK lokalnie; dostawcy GPU testowani fiksturami, nie sprzętem („A skipped provider test is not provider verification”) | `docs/testing.md:62-74` |
| licencja | MIT | `LICENSE`, `pyproject.toml:10` |
| popularność | 210 gwiazdek, 14 forków, utworzone 2026-07-25 | `gh api repos/morluto/flameox` |
| breaking changes | częste: `refactor(api)!`, `refactor(setup)!` w 0.2.x, format repozytorium dowodów już w wersji 4 | `git log`, `docs/storage-and-evidence.md:180-184` |

---

## 6. Porównanie z naszym forkiem i narzędziami

| obszar | nasze | flameox | kto lepszy dla nas |
|---|---|---|---|
| werdykt A/B | fabryka v1: karta przed pomiarem, ABBA, A/A, MDE, t-CI, 7 werdyktów, ledger z łańcuchem sha256, 36 reguł (`wiki/narzedzia/fabryka-cli.md`) | wall time procesu, losowa kolejność, estymata punktowa, bootstrap | **fabryka** |
| proweniencja | ledger: ścieżka + sha256 plików runu, sha buildów, modelu i harnessu (`fk/verify.py:543-573`) | dowód adresowany treścią, kopia bajtów, manifest RFC 8785, `evidence_id`, atomowa publikacja | **flameox** (my hashujemy, ale nie zachowujemy bajtów) |
| profil GPU AMD | rocprofv3 `--kernel-trace --stats` + `trace_breakdown.py`; ATT na gfx1100 (`att_model.sh`, `attsum.py`); świadomość PM4 (`wiki/rocm/rocprof.md`, `wiki/narzedzia/att-gfx1100.md`) | pftrace → pierwsze ≤ 1000 slice'ów | **nasze** |
| uczciwość podsumowania profilu | `trace_breakdown.py` (41 linii): ucina 30% po czasie, sumuje czasy, kategoria „other”, nie podaje pokrycia | jawne `complete`, `rows_observed`, ograniczenia, zakaz „pusty selektor = brak” | **zasady flameoxa** (P2) |
| walidacja kerneli | `test-backend-ops` w G1; `kt.py fake` z referencją numpy; `llama-bx-diff` (pierwszy rozbieżny węzeł) | schemat `kernel-validation.v2` + kontrola spójności werdyktów | nasze narzędzia; **jego kontrola spójności** do przeniesienia (P4) |
| autotuning | kt harness (Kernel Tuner, `kt.py tune`, tylko gfx1100) | czyta cache Tritona | nasze |
| monitor | REACTOR: sysfs/hwmon, KFD, t/s z logu | brak | nasze |
| sprzątanie procesów | `start_new_session` + `killpg` SIGTERM→SIGKILL po 15 s (`fk/measure.py:73-97`); R08 sprawdza KFD i VRAM przed startem | psutil śledzi też potomków spoza grupy | remis; R08 pokrywa nasz realny przypadek |
| profil hosta CPU | ręcznie (`rr-hip`: ≈ 1.15 ms/krok na uploady) | `perf`, py-spy z rankingiem hotspotów | flameox wygodniejszy, ale `perf_event_paranoid=4` blokuje i tak (§4.1) |
| eksport inferencji bez promptów | brak | AIPerf, vLLM, SGLang, Mooncake + digest tożsamości obciążenia | **flameox** (P6, produkt) |
| analiza trace SQL | Python csv: 2.37 s, 761 MB RSS dla 158 MB CSV | DuckDB/Perfetto | DuckDB 0.48 s, 596 MB, identyczne liczby (§7, P7) |

---

## 7. Pomysły do adopcji: ranking wartość / koszt

| # | pomysł | dla | wartość | koszt | minimalny eksperyment | kill |
|---|---|---|---|---|---|---|
| **P1** | `stats.summarize`: percentile bootstrap tylko przy n ≥ 12, poniżej wymuszony `t` z notatką w ledgerze | fabryka, RSI-F | wysoka (trafność werdyktu) | 15 min | gotowy: `fx_cov.py` (§4.4) + test jednostkowy w `factory/tests` | brak; to strażnik |
| **P2** | inwarianty pokrycia w `trace_breakdown.py` i `attsum.py`: (a) liczba wierszy razem, zachowanych i wyciętych z oknem w ns; (b) liczba kolejek i strumieni; (c) union-busy vs sum-busy, przy różnicy > 0.1% ostrzeżenie; (d) pusty `--kernel-include-regex` albo 0 dopasowań → exit ≠ 0 „INCOMPLETE”; (e) odczyt `GGML_HIP_PM4` z metadanych runu, przy PM4 ≠ 0 odmowa | profil → Proponent (Amdahl `attacked.share_ms`) | wysoka (zły udział = zła kolejka hipotez) | 1 h | uruchomić v2 na 20 istniejących `run_kernel_trace.csv` (CPU) i policzyć anomalie. Już sprawdzone na 5 trace'ach: overlap 0.00–0.01 ms, 2–3 kolejki, idle 10.2–30.6% bez zmian | jeśli 0 anomalii w 20 trace'ach i nie planujemy wielu strumieni, zostawić tylko (d) i (e) |
| **P3** | `factory preserve`: pliki runu → `factory/evidence/sha256/<aa>/<sha>/payload.zst` + `manifest.json` kanonizowany, `evidence_id` = sha256 manifestu; wiersz ledgera wskazuje `evidence_id` zamiast ścieżek; atomowy rename; bez GC | fabryka, Replayer i Rewriter RSI-F, AUDYT | średnio-wysoka | 0.5–1 dnia | backfill `~/qwen-opt/prof` (617 MB): zmierzyć bajty po zstd i deduplikacji. Jeden trace: 158.2 MB → 8.56 MB przy `zstd -3`, czyli 18.5× | jeśli backfill > 60 MB (kompresja < 10×), trzymać tylko podsumowania + sha |
| **P4** | kontrola spójności werdyktów producenta w G1 i kt: parsować liczby z `test-backend-ops` (NMSE vs próg) i `kt.py`; werdykt przeliczany z liczb; sprzeczność → `INVALID`; schemat jak `kernel-validation.v2` (case/output/metric/comparator/threshold/status + do 32 „failure witnesses”) | fabryka G1, kt harness | średnia | 2–3 h | przepuścić archiwalne logi `ops-*.log` i wyniki `kt.py` przez parser; liczba sprzeczności | 0 sprzeczności i `test-backend-ops` jest jedynym źródłem → wdrożyć tylko dla kt |
| **P5** | metadane pomiaru czasu w kt i konwersji llama-bench: `measurement_clock` (`hip_event`/`host_monotonic`), `synchronization`, osobne `warmups`, oś tożsamości (device, dtype, shape, variant); zakaz mieszania zegarów pod jedną nazwą metryki (`benchmark_samples.py:52-123`, `workers/benchmark_samples.py:97-103`) | kt harness, chmura | średnia | 1–2 h | konwerter llama-bench → samples już zrobiony dla 4 plików 5060 Ti (§4.2); dodać do `kt.py tune` | jeśli `kt.py` już zapisuje zegar i synchronizację, tylko dopisać pola |
| **P6** | digest obciążenia bez promptów dla telemetrii i porównań „Podkręt”: sha256 z listy (ISL, OSL, offset) + sha buildu + sha modelu + klasa sprzętu; porównania tylko przy równych digestach; projekcja przez allowlistę pól, nie przez regex (`providers/aiperf.py:59-108`, `inference_exports.py:573-659`) | produkt (`PLAN.md:324`: telemetria domyślnie wyłączona, podgląd JSON) | średnia | 0.5 dnia projektu | policzyć digest dla jednego runu `sealed-v1` i sprawdzić, że dwa runy tej samej karty dają ten sam digest | jeśli produkt nie planuje dzielenia wyników benchmarków |
| **P7** | DuckDB do analiz trace (okna per krok, histogram przerw) | profilowanie | niska | 1 h | gotowe: `fx_union.py`, 0.48 s vs 2.37 s, identyczne wall 5885.3 ms i busy 4085.7 ms | jeśli nie potrzebujemy zapytań okienkowych |
| **P8** | offline'owa analiza nsys/ncu z chmury NVIDIA przez flameox (tylko analiza, na CPU lokalnie) | chmura NVIDIA | niska | 0.5 h na run | przy najbliższej sesji 5060 Ti: `nsys profile` → `flameox analyze inspect_gpu_launches` | jeśli nic ponad `nsys stats` |

**Oczekiwany zysk, arytmetyka** (tylko trafność, nie t/s):
- **P1.** Przy 30 werdyktach/miesiąc (21h §5.5) i ~70% hipotez zerowych `[SZACUNEK]` jest 21 przypadków z prawdziwą H0. Przy n = 5 bootstrap średniej daje 21 × 17.8% ≈ 3.7 fałszywych wykluczeń 0 na miesiąc, a t daje 21 × 5.5% ≈ 1.2. To górna granica, bo `CONFIRMED` wymaga jeszcze mediany ≥ MDE. Dziś domyślnie jest `t`, więc P1 chroni przed regresją, a nie naprawia błędu.
- **P3.** `~/qwen-opt/prof`, `s2/prof` i `t2/prof` to razem 1.18 GB. Przy 18.5× daje to ~64 MB `[INFERENCE: zakładam podobny współczynnik dla innych trace'ów]`. To mieści się w H9 (SSD).
- **P2.** Zysku nie da się dziś policzyć. Zapobiega klasie błędu „profil z PM4 = 1 albo pusty regex wygląda jak prawdziwy” (`wiki/rocm/rocprof.md:17`).

**Czego nie adoptujemy:**
- **flameox jako MCP w omp.** Katalog ~284 KB widoczny dla modelu (§4.5). 20 narzędzi capture omija H0. Nie znalazłem przełącznika „tylko analiza”: `grep` po `mcp/server.py` i `cli.py` nie znalazł flag typu read-only. `LD_LIBRARY_PATH` jest zablokowany (`environment_policy.py:12`), a nasze A/B buildów od niego zależy (`fk/measure.py:106-111`).
- **Silnik eksperymentów flameoxa.** Wall time z ładowaniem modelu, brak ABBA, A/A i MDE (§4.3–4.4).
- **`compare_benchmarks` i `compare_inference`.** Ratio średnich bez CI (`providers/benchmark_comparison.py:12-60`, `inference_exports.py:600-623`).
- **Losowa kolejność w blokach zamiast ABBA.** ABBA jest odporna na liniowy dryf termiki, a to nasz główny wróg (R09/R14).

---

## 8. Bezpieczeństwo sprzętu

- **Analiza** (`flameox analyze`) to czyste CPU: parsery w podprocesach z limitem RSS. Bezpieczna. Wszystko w tym raporcie poza testami flameoxa było tylko analizą.
- **Capture** uruchamia dowolny argv. Nie ma `flock /tmp/gpu.lock`, `gpu-guard`, `GGML_HIP_PM4=0`, sprawdzenia :8080 ani limitu temperatury.
  - Agent z MCP flameoxa mógłby odpalić `rocprofv3 -- llama-server` poza fabryką. To łamie H0, H1, H2 i H8 z 21h §5.4.
  - Jeśli kiedyś go użyjemy, to wyłącznie przez CLI `analyze`, nigdy jako MCP z capture.
- **rocprofv3 przez flameox** nie wie o PM4. Przy `GGML_HIP_PM4=1` trace pokazałby tylko część dispatchy, a flameox nie oznaczyłby tego jako niepełne.
- **Broker flameoxa dobrze sprząta potomków.** U nas ten sam realny przypadek, czyli zombie serwer trzymający VRAM, łapie R08 przed startem bloku (`rules/r08_zombie.py:1-30`). Nie ma czego dokładać.

---

## 9. Odpowiedzi wprost

- **Silnik?** Nie. **Profiler?** Nie własny, tylko orkiestrator. **Kernele?** Nie. **Flame graph dla inferencji?** Nie, mimo nazwy.
- **Backendy:** Python; NVIDIA (nsys, ncu, sanitizer, Triton) szeroko, ale niesprawdzone przeze mnie; AMD tylko pftrace bez agregacji; Vulkan brak.
- **Benchmarki:** jedyne liczby wydajności dotyczą samego flameoxa na macOS, arytmetyka OK. Statystyka eksperymentów słabsza niż nasza, co zmierzyłem.
- **Dla nas:** wziąć zasady (P1–P6), nie narzędzie.

---

## Do bazy wiedzy

| folder | tytuł (plik) | co wpisać | liczby i źródło |
|---|---|---|---|
| `research/` | Raport 21j: flameox (`raport-21j-flameox.md`), nowa | Orkiestrator profilerów i magazyn dowodów dla agentów (MCP, Python), nie silnik i nie flame graph; AMD tylko pftrace bez agregacji; nie instalujemy, adoptujemy zasady P1–P6 | 649/660 testów OK w 98 s; katalog MCP 1 047 166 B; 0.35% pokrycia pierwszej strony na `prof/mtp4` (§0, §4) |
| `repo/` | morluto/flameox (`flameox.md`), nowa | MIT, 0.2.9, HEAD `c7ea167`, 523 commity / 79 dni, 400/400 issues od autora, Devin współautorem 9 commitów; 26 operacji / 51 narzędzi; rocprofv3 1 test | §5; `gh api` 2026-10-19 (210★, 14 forków) |
| `lekcje/` | Percentile bootstrap przy małym n kłamie (`lekcja-bootstrap-male-n.md`), nowa | Przy n ≤ 10 par percentile bootstrap wyklucza 0 za często; dla średniej 2–4× za często; używać Student t; A/A flameoxa z CI [0.58, 29.80] ms dla identycznych programów | n = 5: 17.8% (średnia), 7.4% (mediana), 5.5% (t); `flameox-demo/fx_cov.py`, `exp.json` |
| `metody/` | Zasady uczciwego dowodu z profilu (aktualizacja [[fabryka-v1]] albo nowa `dowod-z-profilu.md`) | `complete`/`rows_observed`/ograniczenia przy każdym podsumowaniu; pusty selektor = INCOMPLETE; selekcja przed obcięciem; tożsamość serii z device/dtype/variant; nie mieszać zegarów | `flameox docs/adapters.md:144-181`; P2, P5 |
| `narzedzia/` | aktualizacja [[fabryka-cli]] | propozycje P1 (strażnik bootstrapu), P3 (`factory preserve`, evidence store zstd), P4 (spójność werdyktów G1) | 158.2 → 8.56 MB `zstd -3` (18.5×); `fk/stats.py:43-50,89-95` |
| `rocm/` | aktualizacja [[rocprof]] | `trace_breakdown.py`: sum-busy = union-busy na 5 trace'ach (overlap ≤ 0.01 ms); DuckDB 0.48 s vs Python 2.37 s na 158 MB CSV przy identycznych liczbach | `flameox-demo/fx_union.py` |
| `produkt/` | aktualizacja telemetrii (przy `PLAN.md:324`) | digest obciążenia bez promptów (ISL, OSL, offset) + sha buildu i modelu; porównania tylko przy równych digestach; projekcja przez allowlistę | `flameox providers/aiperf.py:59-108` (P6) |
| `metody/` | aktualizacja [[petla-rsi-f]] | MCP flameoxa łamie H0 (20 narzędzi capture, brak trybu tylko-analiza); dowody dla Replayera przez `evidence_id` (P3) | §7, §8 |
