# xtxbench — szybki, bezstratny A/B silnika produkcyjnego RX 7900 XTX

Cel: test wariantu (kernel, binarka, flaga, przełącznik env) w ~10 min GPU zamiast 40–120 min. Metryki główne:
**decode** (1.7k / 94k / 199k kontekstu, T=0, 256 tokenów, md5 tekstu) i **prefill** (4k / 32k).

Produkcja = `~/qwen-opt/run-topka.sh uncensored` (silnik `~/llama-topka`, topka-q63 c0576e3e8; Qwen3.8-27B-Uncensored
Q4_K_M, KV q4_0, MTP n4, ctx 262144, eco 2200). Każdy serwer xtxbench to ten sam launcher z `ROCM_DIR`/env/argumentami
ramienia i `--slot-save-path ~/qwen-opt/xtxbench/slots`, port 18794.

Wyniki walidacji: sekcja [Walidacja](#walidacja-na-gpu). Kopia skryptów: `~/KERNEL/qwen-opt/xtxbench/`, łatka
przełącznika: `~/KERNEL/qwen-opt/patches/xtxbench/`, notatka wiki `metody/xtxbench-szybki-ab`.

## Użycie

Tryby GPU (`t0`, `t1`, `t2`) działają **tylko** w kolejce (`~/qwen-opt/queue/run-jobs.sh`, inaczej odmowa), wymagają eco
2200 (`xtx-eco status`, nigdy nie zmieniane), same zatrzymują :8080 (JEDEN SIGTERM, 60 s, potem SIGKILL) i na końcu
przywracają `run-topka.sh uncensored` (health + n_ctx w logu). **Nic nie kompilują**: brak binarki = odmowa, binarka
starsza niż jej źródła (git worktree nad katalogiem build) = odmowa z ostrzeżeniem (`--allow-stale` mierzy mimo to).

```bash
X=~/qwen-opt/xtxbench/xtxbench.py
$X check --var ~/wt/foo/build-hip            # CPU, przed zgłoszeniem joba: binarki, świeżość, hook, plan, snapshoty
$X prep                                      # CPU: sha modelu i silników do cache (GPU tego nie liczy)
$X status                                    # zestawy snapshotów, cache szumu, wyniki t0
python3 ~/qwen-opt/xtxbench/selftest.py      # CPU self-test (fałszywy serwer): 7 scenariuszy

# job kolejki (linia pliku .jobs):  nazwa|1800|~/qwen-opt/xtxbench|python3 xtxbench.py t1 --label foo --var ~/wt/foo/build-hip
$X t0 --label foo --op FLASH_ATTN_EXT --params 'type_K=q4_0' --perf --var ~/wt/foo/build-hip   # kernel vs CPU (+perf ABBA)
$X t1 --label foo --var ~/wt/foo/build-hip                          # binarka: restart (P, N, ewentualnie P)
$X t1 --label foo --var-env GGML_HIP_FOO=1                          # env czytany przy starcie: restart
$X t1 --label foo --var-args -ub,1024                               # flaga serwera: restart
$X t1 --label foo --base ~/wt/xtxbench/build-hip --snap-compat --var-switch GGML_HIP_MMVQ_PAIR=0   # bez restartu
$X t2 --label foo --var ~/wt/foo/build-hip                          # walidacja przed wdrożeniem
```

Opcje werdyktu: `--target decode|prefill|any` (grupa, która musi zyskać; domyślnie decode), `--pass 1.0` (próg PASS, %),
`--pass-mode max|mean`, `--max-loss 0.5` (tolerowana strata po ABBA, %), `--win-floor 0.5`, `--noise-floor 0.1`,
`--noise-ttl-h 12`, `--renoise`, `--t0 auto|gain|none`, `--own-snap`, `--snap-compat`, `--prove`, `--aa`.

## Poziomy

| tryb | co mierzy | koszt |
|---|---|---|
| `t0` | `test-backend-ops -o OP` obu ramion vs CPU (nowe FAIL = błąd) + z `--perf` A B B A us/run na przypadek; „zysk kernela” = mediana ≥ 1% albo najlepszy przypadek ≥ 2% (zapis `cache/t0-<label>.json`, czyta go reguła KILL w t1) | minuty |
| `t1` | decode z odtworzonego snapshotu 1.7k/94k/199k (T=0, 256 tok., md5), prefill 4k i 32k (czas serwera, `cache_prompt=false`), greedy md5 czatu; reguła adaptacyjna | ~2–5 min/wariant |
| `t2` | t1 + decode T=1 seed 42 ze snapshotów + `spec_sweep.py` T=1 seedy 1,2,3 + prefill 128k + wypełnienie 255k (prefill i decode) | ~15–40 min |

T=1 (`spec_sweep`, seedy 1,2,3) jest tylko w t2: metryką t1 jest deterministyczny decode T=0 z md5.

## Snapshoty kontekstu

- Prompt (jak `kvq-once/lc.py`, korpus `long_ctx_bench.py`, zamrożony w `corpus.txt`, bo jego źródła się zmieniają):
  `pre + doc[:D] + post`, gdzie `pre`/`post` to wyrenderowany `/apply-template` (myślenie wyłączone), a `D` = tokeny
  dokumentu. Snapshot = stan slotu po prefillu `P = pre + doc[:D]` (`/completion`, `n_predict=1`), zapisany
  `POST /slots/0?action=save`. Pomiar: `restore` → `/completion` z `P + post` (`cache_prompt=true`): serwer przetwarza
  tylko pytanie (~40 tokenów; więcej = odmowa, bo stan hybrydowy GDN musiałby się cofać) i dekoduje 256 tokenów.
- Plik slotu topka-q63 niesie KV atencji + stan rekurencyjny GDN, checkpointy kontekstu i stan draftu MTP (KV kontekstu
  MTP + `pending_h`, upstream #30574/#30141).
- Klucz = sha256(model sha + sha binarek silnika (`llama-server` + `lib*.so*` z `/proc/<pid>/exe`) + argv serwera bez
  portu/logu/ścieżki slotów + env `LLAMA_*`/`GGML_*`/`HSA_*`/`HIP_*`/`ROCR_*`/`AMD_*` bez pliku przełączników + sha
  plików z argv (słownik draftu) + sha korpusu + wersja promptu), liczony z żywego procesu. Inny klucz = nowy zestaw
  (`slots/<klucz>.json` + `<klucz>-d<D>.bin`); na dysku zostają 2 najnowsze zestawy (automatyczne unieważnianie).
- Ramię B domyślnie odtwarza zestaw A (ten sam stan startowy; pliku nie da się wczytać przy innym układzie KV — wtedy
  `--own-snap`: B tworzy własny zestaw swoim silnikiem). `--snap-compat`: inny silnik o identycznym modelu/argv/env
  bierze najnowszy zgodny zestaw (np. build z hookiem vs produkcja).
- Przed każdym żądaniem, które nie kontynuuje odtworzonego prefiksu, slot jest kasowany (`erase`): nic nie trafia do
  `--cache-ram` i nic z niego nie wraca.

### Dowód md5 (restore = świeży prefill)

Przy tworzeniu zestawu (albo `--prove`) dla każdej głębokości: (1) świeży prefill `P` + decode `P + post` w pamięci,
(2) restore z pliku + decode (runda A0, ten sam proces), (3) restore w **nowym procesie** (B1 przy `--force-restart`),
(4) jedno zimne żądanie `P + post` jak stara metoda (lc.py). (1) = (2) = (3) dowodzi, że zapis/odczyt stanu (KV + GDN +
MTP) jest bitowo dokładny. (4) może się różnić: zimne żądanie tnie prompt na inne ubatche (serwer łamie batch na
`n − 516` i `n − 4` tokenów przed końcem promptu dla checkpointów), więc to różnica kolejności sum prefillu, nie restore.
Na CPU (LFM2.5-2.6B, hybryda conv, build topka 098ce134d) przy 0.6k (1) ≠ (4), przy 2k (1) = (4) — zgodnie z tym.

## Przełącznik bez restartu (`GGML_HIP_RUNTIME_SWITCH_FILE`)

topka czyta przełączniki kerneli raz (`static const ... = ggml_cuda_env_switch(...)` / `getenv` w lambdzie `static`,
22 miejsca w `ggml-cuda/`), więc zmiana env wymaga restartu. Łatka w `~/wt/xtxbench` (gałąź `xtxbench` z topka-q63,
commit w `git -C ~/wt/xtxbench log -1`; **nie wdrożona** do `~/llama-topka`):

- `GGML_CUDA_RT_SWITCH(NAME, def)` zastępuje te odczyty: bez zmiennej env każde miejsce rozwiązuje się raz ze
  środowiska do tej samej wartości co wcześniej (bezstratnie; jedno porównanie atomowe na wywołanie);
- z `GGML_HIP_RUNTIME_SWITCH_FILE=<plik>` `graph_compute` robi `stat` pliku (najwyżej co 20 ms, przed każdym
  przechwyceniem); zmiana zestawu `NAZWA=WARTOŚĆ` podbija generację, miejsca czytają od nowa (plik > env > domyślna),
  a każdy kontekst robi `cudaDeviceSynchronize` i porzuca przechwycone grafy HIP i taśmy PM4 (ścieżka eksmisji po 10 s
  bezczynności), więc następny graf jest przechwycony z nowymi kernelami; serwer pisze na stderr
  `ggml_cuda_rt_switch: gen N from <plik>: NAZWA=WARTOŚĆ`, a xtxbench po każdym przełączeniu wysyła małe żądanie i
  sprawdza tę linię;
- przełączalne: `ARGMAX_FAST, KVQ_Q8, CONV_MUL, Q8_IDS, MOE_DOWN_REDUCE, NORM_ROUTER, INPROJ_CONV, ATTN_PREP, KVQ_FWHT,
  GATE_UP_Q8, MMVQ_PAIR, NORM_GATE, GDN_CONV_AB, MMQ_EPI, MMVQ_N1_Q8_0, MMVQ_N1_ROWS, MMVQ_Q5K_BIG_ROWS,
  MMVQ_IQ4XS_BIG_ROWS, MMVQ_Q4K_STREAM, CONV_ROWS4, NORM_FAST, GDN_PREFETCH` (prefiks `GGML_HIP_`); `GGML_HIP_PM4` i
  `GGML_HIP_INPUT_BATCH` zostają procesowe. Nowy przełącznik w łatce wariantu: `GGML_CUDA_RT_SWITCH("GGML_HIP_X", 0)`
  zamiast `static const`, wtedy `--var-switch GGML_HIP_X=1` testuje go bez restartu.

## Reguła adaptacyjna (domyślna dla każdego testu)

1. **Szum raz na sesję.** t1 zaczyna od pary bazowej A0, A0' na tym samym snapshocie; szum `n = |A − A'| / A` osobno dla
   każdej głębokości decode i każdego rozmiaru prefillu. Cache `cache/noise-<klucz A>.json` ważny `--noise-ttl-h` (12 h)
   dla tego klucza silnika/konfiguracji; kolejne warianty w sesji mierzą tylko świeże A0.
2. **Wariant zaczyna od jednej pary A → B** (A = pomiar bazowy bezpośrednio przed B), osobno dla grup decode i prefill:
   - `|Δ| ≥ max(5·n, 0.5%)` na **każdej** metryce grupy i jeden znak → od razu **WIN** albo **LOSS**;
   - `|Δ| ≤ max(n, 0.1%)` wszędzie i t0 nie pokazał zysku kernela → od razu **NULL** (KILL);
   - inaczej (niejednoznaczne) → dochodzi B → A (pełne A B B A) i decyzja na średnich: metryka znacząca, gdy
     `Δ̄ > 2·rozrzut` (zysk) albo `Δ̄ < −max(2·rozrzut, 0.5%)` (strata), rozrzut = max(n, |A−A''|/Ā, |B−B'|/B̄, 0.1%);
     zysk bez straty = WIN, strata bez zysku = LOSS, oba = MIXED, nic = NULL.
3. Prefill: jeden pomiar na rozmiar (4k, 32k); powtórka tylko gdy niejednoznaczny według tej samej reguły.
4. **Werdykt PASS** = grupa docelowa WIN z zyskiem ≥ `--pass` (domyślnie +1,0%, najlepsza znacząca metryka), żadna
   grupa LOSS/MIXED, md5 T=0 identyczne we wszystkich rundach i greedy md5 czatu identyczne; inaczej **KILL** z powodem.
5. Raport: tabela `baseline → teraz → %` z szumem i progiem, liczba pomiarów A/B na metrykę, rundy, starty serwera,
   minuty: wariant (A0 + B1 [+ B2 + A2] + restarty), sesja (serwer A, para szumu, :8080), raz na silnik (snapshoty,
   dowód) i szacunek starej metody (4 ramiona × (start + zimne żądanie na głębokość + prefill + md5)).

Grupowanie serwerów: binarka/env/flaga → restart (A na serwerze P, B na N, przy niejednoznaczności B' na N i A'' na
nowym P: każda binarka startuje raz, plus jedna powtórka P); przełącznik runtime → jeden serwer, A B [B A] na żądaniach.

## Pliki

- `xtxbench.py` — narzędzie; `selftest.py` — test CPU; `validate.sh` / `validate.jobs` — job walidacyjny;
- `slots/` — snapshoty i manifesty (z danymi dowodu md5), `cache/` — sha, szum, t0, `corpus.txt` — zamrożony korpus;
- `runs/<MMDD-HHMMSS>-<tryb>-<label>/` — `summary.txt` (tabela), `result.json`, `results.jsonl` (każdy pomiar),
  `timings.jsonl` (każdy etap), `xtxbench.log`, `srv-*.out|log` (logi serwerów).

## Walidacja na GPU

(uzupełniane po jobie `validate.jobs`)
