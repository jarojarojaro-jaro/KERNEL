# 16k. Sprzężone próbkowanie draftu (E-X4) na XTX

Data: 2026-10-18. Autor: podagent CoupledSampling. Eksperyment E-X4 z raportu [16i](16i-magnitude-co-robia-dobrze.md) §4 #3 i §8.
Kod: `~/wt/coupled`, gałąź `opt-coupled` (z `amd-opt` @ `f61994f58`), commit `760ee6990` + commit z wynikiem (§6). Skrypty i surowe wyniki: `~/qwen-opt/coupled/`.

## 0. Najważniejsze

- **Mechanizm przeniesiony 1:1 i jest bezstratny.** Cel losuje Gumbel-max z szumem Philox kluczowanym (seed, pozycja, token), jak Magnitude. Draft MTP wybiera tym samym szumem przez nowy op `GGML_OP_GUMBEL_MAX` (CPU + HIP) w grafie łańcucha MTP. Wszystko za `LLAMA_SPEC_COUPLED` (domyślnie wyłączone).
- **Dowód (§2):** próbka celu zależy tylko od prefiksu i szumu pozycji. Wyjście spekulacji jest więc token w token równe wyjściu bez spekulacji, dla każdego draftera i każdej temperatury draftu. Zastrzeżenie: logity celu muszą być bitowe; w trybie `LLAMA_SPEC_BITEXACT` daje to gwarancję „spec == plain przy każdym T”.
- **Poprawność potwierdzona:**
  - CPU, 200k losowań: wszystkie testy chi² p > 1e-4; spekulacja == plain dla każdego seeda, **0/20 000** różnic;
  - op GPU == CPU == łańcuch samplera: `test-backend-ops` **152/152**, 0/2000 różnic;
  - greedy md5 bez zmian przy wyłączniku off i on: plain `c4708318`, MTP `6f14e814`.
- **Zysk na XTX jest mały i niepewny; pomiar A/B jest NIEPEŁNY.**
  - Ważne 12 bloków ABBA (3 seedy) przy T=1: tok/krok 3.00 (off) → 3.16 (sprzężone), t/s 107.7 → 114.2 (+6.0%).
  - Ale **kontrola** (sprzężony cel + draft greedy, czyli bez sprzężenia draftu) daje +7.8% t/s i +3.6% tok/krok. Ta różnica to tylko szum tekstu: inny strumień RNG daje inne 18 tekstów.
  - Czysty efekt sprzężenia draftu (tryb 1 vs 2, te same teksty z dokładnością do numeryki):
    - tok/krok +1.6% (T=1) i +2.6% (T=0.7);
    - koszt kroku +1.5% (pierwsza wersja kernela), czyli netto ≈ 0;
    - test identyczności (160 tekstów): akceptacja 0.377 → 0.404, tok/krok +4.0% (T=1).
  - Po przyspieszeniu kernela (`3f25fc204`) koszt spadł do +0.4% ms/krok. Na 20 seedach zdążył się wykonać tylko jeden blok na tryb: T=1 tok/krok +3.8%, t/s +4.4% (bez bloku kontrolnego).
  - **Szacunek: +0…+3.6% t/s przy T=1.** Próg kill (+2%) nierozstrzygnięty.
- **A/B przerwane z powodu sprzętu.** W 4 blokach (także w trybie 0, wyłącznik off) serwer z mojego buildu dostał page fault GPU pod adresem 0 (klient SQC), a po nim reset GPU. Zgodnie z regułą użytkownika build jest wstrzymany na GPU do czasu analizy (agent Pm4FaultAnalysis, §5.3).
- **Wniosek wstępny:** dla MTP sprzężenie odzyskuje najwyżej kilka procent, bo luka T=0/T=1 jest mała (16i: 2–6%), a filtry top-k 20 / top-p 0.95 / min-p 0.05 zostawiają większość pozycji prawie deterministyczną. Mechanizm i test są gotowe dla DFlash2, gdzie luka wynosi 20% (16i #3, #4).

## 1. Co robi Magnitude (źródło)

- **Cel próbkuje Gumbel-max.** Wynik wiersza to `logit / temperature + noise` (`M/engine/kernels/kernels/readout.seismic:315-317`). Szum to Philox4x32-10 na liczniku (token, pozycja…) z kluczem = seed, `u = ((x >> 9) + 0.5)·2⁻²³`, `g = −log(−log u)` (`readout.seismic:325-329`). Filtry top-k/top-p/min-p działają przed losowaniem (`sampling.seismic:1-5`).
- **Każda propozycja draftu ma ten sam `seed` i `position` co próbka celu dla tej pozycji** (`M/engine/generation/src/lib.rs:747-779`). Cel liczy próbki z tym samym kluczem (`generation/src/shaping.rs:26-56`, `position: generated_position + row`).
- **Akceptacja to zwykłe dopasowanie prefiksu** do tokenów spróbkowanych przez cel (`generation/src/acceptance.rs:7-20`). Nie ma rejection samplingu ani rozkładu draftu `q`.
- **Kontrakt:** „Position-addressed RNG prevents batch membership or rejected work from changing a seeded request's random draws” (`D/inference/engine/speculative-generation.md:202-208`).
- **To znany schemat z literatury:** „drafter-invariant speculative decoding” przez komunikacyjnie wolne sprzężenie Gumbela (Daliri, Musco, Suresh, arXiv 2408.07978). Gwarancja: P(a = b) ≥ (1 − TV)/(1 + TV), a Gumbel jest Pareto-lepszy od Weighted MinHash.
- **DFlash bez sprzężenia traci przy T=1** (arXiv 2602.06036, tab. 1): Qwen3-8B, średnie τ spada z 6.49 (T=0) do 5.48 (T=1), czyli −16%. U nas DFlash traci −20% t/s (wiki `eksperymenty/2026-10-10-sweep-mtp-dflash.md`).

## 2. Dlaczego to jest bezstratne (szkic dowodu)

Oznaczenia: `z(x_<k)` to logity celu po łańcuchu filtrów (top-k → top-p → min-p, potem dzielenie przez T). Zbiór `S` to tokeny, które filtry zostawiają. `g_k(t) = G(seed, k, t)` to szum Gumbela dla pozycji k i tokenu t.

1. **Gumbel-max.** Jeśli `g(t)` są niezależne o rozkładzie Gumbel(0,1), to `argmax_{t∈S} (z_t + g(t))` ma rozkład softmax(z) na S. To ten sam rozkład, z którego losuje `dist` w llama.cpp.
2. **Sampler celu jest deterministyczną funkcją** prefiksu i szumu pozycji k: `X_k = F(x_<k, g_k)`. Szum zależy tylko od (seed, k, token). Nie zależy od draftu, odrzuceń ani szerokości batcha.
3. **Tokeny emitowane przy spekulacji z dopasowaniem prefiksu** to zawsze próbki celu `F(x_<k, g_k)`. Przyjęty token draftu jest równy próbce celu z definicji akceptacji, a token „bonusowy” to próbka celu. Indukcją po k: wyjście spekulacji = wyjście zwykłego dekodowania z tym samym szumem, **token w token, dla każdego seeda i każdego draftera**. Zakładamy przy tym, że logity celu są bitowo takie same.
4. **Szum na różnych kluczach jest niezależny** (Philox jako funkcja pseudolosowa licznika). Zwykłe dekodowanie z kluczowanym szumem jest więc dokładnym próbkowaniem łańcuchowym z rozkładu celu. Ze sprzężonym draftem jest tak samo, na mocy pkt 3.
5. **Zysk.** Draft wybiera `argmax_{t∈S'} (z'_t + g_k(t))` z tym samym `g_k`. Jeśli q = p, to wybór jest identyczny z celem (akceptacja 1 przy dowolnym T). Ogólnie P(trafienie) ≥ (1 − TV(p,q))/(1 + TV(p,q)) (2408.07978). Draft greedy trafia tylko z prawdopodobieństwem p(argmax q), np. ≤ 0.6 przy p_max = 0.6, nawet gdy q = p.

**Zastrzeżenia (warunki dowodu):**
- Pkt 3 wymaga, by logity celu nie zależały od draftu. U nas weryfikacja batcha 5 wierszy liczy numerycznie inaczej niż N=1 (lekcja `lekcja-spekulacja-zmienia-numeryke.md`). Tekst może się więc różnić od plain po pierwszym remisie numerycznym, dokładnie tak jak dziś przy T=0. Rozkład wyjścia pozostaje rozkładem celu, z dokładnością do tej samej numeryki co dziś.
- **W trybie `LLAMA_SPEC_BITEXACT`** (gałąź `batch-invariant`: plain == MTP bitowo) pkt 3 daje twardą gwarancję: tekst ze spekulacją = tekst bez niej przy każdej temperaturze i każdym seedzie. Tego nie testowałem w tym zadaniu (inna gałąź) [INFERENCE z pkt 3 i z md5 `74952fd5` plain == MTP w bit-exact].
- Temperatura i filtry draftu wpływają tylko na zysk, nie na poprawność (pkt 3). Dlatego w kodzie jest `LLAMA_SPEC_COUPLED_DT`.

## 3. Implementacja (fork, wszystko za `LLAMA_SPEC_COUPLED`, domyślnie wyłączone)

| element | plik | opis |
|---|---|---|
| szum | `common/gumbel.h` | Philox4x32-10 na (token, klucz, domena, 0) z kluczem (seed, 0); `u = ((x>>9)+0.5)·2⁻²³`; jak w Magnitude |
| sampler celu | `common/sampling.cpp` (`common_sampler_coupled_*`) | zastępuje `dist` na końcu łańcucha, gdy `LLAMA_SPEC_COUPLED > 0` i T > 0 (greedy przy T=0 bez zmian). Klucz = liczba tokenów przyjętych przez sampler (prompt + wygenerowane), czyli indeks tokenu w sekwencji. Remisy idą do mniejszego id tokenu, więc wynik nie zależy od kolejności kandydatów. Pomija szum kandydatów, które nie mogą wygrać (logit + 16.64 < najlepszy wynik), bo przy pełnym słowniku 248k Philox na każdy token kosztuje |
| resample gramatyki | `common_sampler_sample` | drugie przejście (po odrzuceniu tokenu przez gramatykę) używa domeny 1, czyli niezależnego szumu, tak jak `dist` losuje wtedy drugą liczbę |
| draft MTP | `src/models/qwen35.cpp`, nowy op `GGML_OP_GUMBEL_MAX` (CPU `ggml-cpu/ops.cpp`, HIP/CUDA `ggml-cuda/gumbel-max.cu`) | w grafie łańcucha MTP (`LLAMA_MTP_DRAFT_CHAIN`) `ggml_argmax` zastępuje Gumbel-max po logitach głowy 64k: top-k → top-p → min-p → /T + szum klucza `key + j` dla przejścia j. Parametry (seed, klucz, T, k, p, min_p) są wejściem grafu, więc graf i nagranie PM4 są reużywane |
| sterowanie | `tools/server/server-context.cpp`, `common/speculative.{h,cpp}` | serwer przekazuje do `draft_params` seed i klucz celu oraz jego filtry. Ścieżka bez łańcucha (pętla per poziom) używa sprzężonego `common_sampler`. Weryfikacja zostaje dopasowaniem prefiksu (`result_q = nullptr`, bez rejection) |
| tryby | `LLAMA_SPEC_COUPLED` | 0 wył. (produkcja); 1 cel sprzężony + draft sprzężony; 2 cel sprzężony + draft greedy (izoluje wpływ sprzężenia draftu); `LLAMA_SPEC_COUPLED_DT` mnożnik temperatury draftu (domyślnie 1) |

**Interakcje:**
- **Łańcuch samplera** (domyślny serwera: penalties → dry → top_n_sigma → top_k → typical → top_p → min_p → xtc → temperature; z GGUF Qwen3.8 top_k=20, top_p=0.95, min_p=0.05 domyślne).
  - Sprzężenie zmienia tylko ostatni sampler.
  - Kary (penalties) działają na celu, draft ich nie stosuje. To kosztuje tylko akceptację, nie poprawność.
  - Słownik draftu 64k: token spoza niego nie może zostać wydraftowany.
- **Szybkie ścieżki samplera 0031/0048/0066–0069** (`LLAMA_SAMPLER_FAST_*`):
  - dają tych samych kandydatów co pełna tablica (SAME-TOK), a sampler sprzężony nie zależy od kolejności kandydatów, więc zostają dokładne;
  - kandydaci z pominiętym szumem nie mogą wygrać (pkt 2.1).
- **Budżet myślenia (FORCING):** zostaje jeden token, sampler go wybiera.
- **`n_probs`:** prawdopodobieństwa liczone jak w `dist`.
- **Backend sampling:** sprzężenie wyłączone (zostaje `dist`).
- **Mirostat / adaptive-p:** bez zmian (`dist` nie jest używany).
- **Seed:** inny strumień losowy niż `dist`, więc przy tym samym seedzie powstają inne teksty niż dziś (rozkład ten sam). Przy T=0 nic się nie zmienia.
- **`LLAMA_SPEC_BITEXACT`:** patrz §2. Sprzężenie jest jedynym sposobem, by spekulacja przy T>0 dawała ten sam tekst co plain.

## 4. Poprawność

**CPU, test statystyczny** (`tests/test-coupled-sampling.cpp`, `build-cpu/bin/test-coupled-sampling 200000`; wyniki w `~/qwen-opt/coupled/test-coupled-sampling-200k{,-v2}.txt`, 13.5 s). Próg: p > 1e-4. Wszystkie testy przechodzą:

| test | wynik |
|---|---|
| rozkład brzegowy, 200k losowań, 64 tokeny, 5 konfiguracji (T 0.3–1.5, z filtrami top_k 20/40, top_p 0.9/0.95, min_p 0.05 i bez) | chi² `coupled` p = 0.94 / 0.54 / 0.21 / 0.58 / 0.85; dla porównania `dist` p = 0.32 / 0.11 / 0.14 / 0.27 / 0.92 |
| niezależność: kolejne klucze, 100k par (6×6 komórek) | p = 0.20 |
| niezależność: sąsiednie seedy, ten sam klucz | p = 0.87 |
| spekulacja na zabawkowym modelu Markowa (V=8, cel p, draft q = p + szum σ 0.6), rozkład łączny 3 tokenów (512 komórek), 200k sekwencji, T=1 bez filtrów / T=1 z filtrami / T=0.7 z filtrami | wszystkie 7 wariantów (plain dist, plain sprzężony, draft greedy × 2 samplery, draft sprzężony przy DT 1.0/0.7/1.5) p > 0.09 |
| **bezstratność token w token:** wyjście spekulacji == wyjście plain dla tego samego seeda | **0 / 20 000 różnic** w każdej z 15 par (draft greedy i sprzężony, DT 0.7/1.0/1.5) |
| tok/krok w zabawce (n_max=4, T=1 bez filtrów) | draft greedy 1.60 → sprzężony 3.02 (DT=1); z filtrami 1.68 → 2.43; T=0.7 z filtrami 1.64 → 2.10 |
| `GGML_OP_GUMBEL_MAX` (CPU) vs łańcuch samplera (ten sam seed/klucz, id tokenów 4096 z 248k) | 0 / 2000 różnych wyborów w 5 konfiguracjach |

**GPU:**
- `test-backend-ops -o GUMBEL_MAX -b ROCm0`: **152/152** (wiersz 65536 = słownik draftu, filtry serwera, 64 seedy przy T 1.0 i 0.7, plus bez filtrów, bez `ids`, T=0). Op na HIP wybiera bitowo to samo co CPU, a CPU to samo co łańcuch samplera, więc draft na GPU losuje dokładnie tym samym szumem co cel. Sprawdzone dla obu wersji kernela (`760ee6990` i `3f25fc204`).
- **Greedy md5 (T=0) na świeżym serwerze** (`~/qwen-opt/fusion/greedy.sh`, `~/qwen-opt/coupled/greedy/`): wyłącznik off i `=1` dają plain `c4708318…`, MTP `6f14e814…`, czyli tyle co baza produkcji (wiki `zgodnosc-bitowa-md5.md`). Przy T=0 sprzężenie się nie włącza (sampler greedy).
- **Identyczność na GPU** (`logs/ident.jsonl`: 2 prompty × 40 seedów × T 1.0/0.7, 96 tokenów, `ident.py`). Tryb 1 (draft sprzężony) vs tryb 2 (draft greedy), ten sam sprzężony cel:
  - identyczne teksty: 30/80 (T=1) i 38/80 (T=0.7); średni wspólny prefiks 67% / 71%;
  - rozjazdy są tylko numeryczne, bo różny draft daje inne pozycje w batchu weryfikacji (jak przy T=0, wiki `lekcja-spekulacja-zmienia-numeryke.md`).
  - Gdyby draft „wybierał” tekst, identycznych tekstów praktycznie by nie było.


## 5. Pomiar na XTX (Qwen3.8-27B UD-Q4_K_XL, MTP n=4, flagi produkcyjne `run-llm.sh qwen mtp rocm`)

Narzędzia: `~/qwen-opt/coupled/arm.sh` (świeży serwer `run-llm.sh qwen mtp rocm` z `ROCM_DIR=~/qwen-opt/coupled/inst`, port 18493, oba locki; spec_sweep 6 promptów × seedy × T 1.0 i 0.7, 400 tokenów), `driver.sh` (przeplot, odrzucanie nieudanych prób), `analyze.py`.
- Tryby: **0** = off (produkcyjny `dist`); **1** = sprzężony cel + sprzężony draft; **2** = sprzężony cel + draft greedy. Tryb 2 to kontrola: ten sam rozkład tekstów co tryb 1 i ten sam drafter co tryb 0.

### 5.1 Run 3: 12 bloków ABBA (kolejność 0 1 2 2 1 0 1 0 2 2 0 1), seedy 1–3, kernel `760ee6990` (ważny, `logs/`)

| T | tryb | t/s (mediana 6 promptów, średnia 4 bloków) | tok/krok (średnia promptów) | ms/krok |
|---|---|---|---|---|
| 1.0 | 0 off | 107.7 ± 0.1 | 3.00 | 28.12 |
| 1.0 | 1 sprzężone | 114.2 ± 0.1 | 3.16 | 28.57 |
| 1.0 | 2 kontrola | 116.1 ± 0.3 | 3.11 | 28.16 |
| 0.7 | 0 off | 112.7 ± 0.2 | 3.11 | 28.18 |
| 0.7 | 1 sprzężone | 118.3 ± 0.2 | 3.19 | 28.61 |
| 0.7 | 2 kontrola | 117.8 ± 0.5 | 3.11 | 28.15 |

- Per prompt przy T=1 (t/s/tok-krok), tryb 0 → 1 → 2:
  - pl-proza 98.4/2.76 → 92.2/2.63 → 97.0/2.73;
  - pl-kod 123.5/3.48 → 133.8/3.83 → 127.9/3.60;
  - en-code 108.6/3.05 → 112.4/3.21 → 119.0/3.35.
- **Lekcja metodyczna.** Przy ustalonym seedzie tekst jest deterministyczny, więc powtórzenie bloku nie zmniejsza szumu tekstu (blok do bloku ±0.1–0.5 t/s). Różnica 0 vs 2 (+7.8% t/s przy tym samym drafcie) pokazuje, że 18 tekstów to za mało, by zmierzyć efekt rzędu 2%. Potrzeba wielu seedów, a nie powtórzeń bloku. Kontrola tryb 2 jest konieczna: off vs on miesza zmianę strumienia RNG ze zmianą draftu. Wiki: [[lekcja-szum-t-s-przy-t1]].
- **Efekt czysto sprzężenia (1 vs 2):** tok/krok +1.6% (T=1), +2.6% (T=0.7); ms/krok +1.5% (koszt opu Gumbel w 4 przejściach łańcucha MTP). Netto przy T=1: 1.016 × 28.16/28.57 = **+0.2%**.

### 5.2 Identyczność i akceptacja na tych samych tekstach (`logs/ident.jsonl`, 2 prompty × 40 seedów, 96 tokenów, bez myślenia)

| T | tryb 1: akceptacja / tok/krok | tryb 2: akceptacja / tok/krok | identyczne teksty |
|---|---|---|---|
| 1.0 | 0.404 / 2.54 | 0.377 / 2.44 (+4.0% dla 1) | 30/80 |
| 0.7 | 0.413 / 2.57 | 0.396 / 2.51 (+2.4%) | 38/80 |

### 5.3 Run 5: 20 seedów (4–23), szybszy kernel `3f25fc204` (przerwany)

- Kernel zmieniony tak:
  - kandydaci z najciaśniejszego progu, który mieści top_k (dokładnie jak łańcuch);
  - klucze sortowania w LDS;
  - jedno przejście zliczanie+zbieranie;
  - 1024 wątki.
- GPU: `test-backend-ops` 152/152 (`~/qwen-opt/coupled/test-backend-ops-gumbel-3f25fc204.txt`).
- Ważne bloki (`logs5/`):
  - tryb 0 (`c1-m0-a2`): T=1 114.1 t/s, 3.01 tok/krok, 27.74 ms/krok; T=0.7 118.6 / 3.09 / 27.77;
  - tryb 1 (`c2-m1-a1`, tylko T=1): 119.1 t/s, 3.12 tok/krok, 27.85 ms/krok → **+4.4% t/s, +3.8% tok/krok, +0.4% ms/krok** wobec trybu 0.
- Bloków kontrolnych (tryb 2), `LLAMA_SPEC_COUPLED_DT=1.3` i drugiej połowy ABBA nie wykonano.

**Awarie:**
- Bloki `b1-m0-a1` 22:42, `b1-m0-a2` 22:57, `b2-m1-a1` 23:25 i `c1-m0-a1` 00:16 (UTC, 18–19.10) oraz 3 wcześniej (run 1–2, 19:47, 19:56, 20:14) skończyły się `hip-pm4.cu:664 tape of 823 dispatches did not complete within 10 s`.
- W `journalctl -k` przy każdej: `[gfxhub] page fault … address 0x0 … client SQC (data)`, potem „MES might be in unrecoverable state”, potem reset GPU.
- Dotyczy to także trybu 0, w którym żaden nowy kod nie działa. Kernel jest ten sam (`f61994f58`), flagi CMake są identyczne z produkcją, nowe wejście grafu i op nie powstają.
- Taśma 823 dispatchy to graf celu, którego zmiana nie dotyka.
- Ten sam podpis (SQC, adres 0) miał 16.10 15:35 inny `llama-server` (pid 338733) przed powstaniem tego kodu.
- Występuje tylko w długich seriach (≥ ~50 kolejnych requestów z flagami produkcyjnymi, eksmisja cache promptu w każdym requeście). Bloki po 36 requestów (run 3) przeszły 12 razy bez awarii.
- **Przyczyna nieustalona** [INFERENCE: błąd ścieżki PM4/graf, nie kod sprzężenia]. Analizuje ją agent Pm4FaultAnalysis.
- Wg reguły użytkownika (pierwsze wystąpienie = stop buildu na GPU) dalsze A/B wstrzymane. Przed wprowadzeniem tej reguły (po 7 awariach) stosowałem odrzucanie i powtarzanie bloków; te bloki nie weszły do wyników.

## 6. Decyzja

- **Kill-test (< +2% t/s przy T=1) nierozstrzygnięty.**
  - Najlepszy ważny pomiar sparowany (1 vs 2, run 3) daje netto **+0.2%** (stary kernel).
  - Po przyspieszeniu kernela spodziewane netto to **+1…+3.6%** [INFERENCE: tok/krok +1.6…+4.0% z §5.1–5.2 minus koszt +0.4% z §5.3].
  - Jedyny blok z 20 seedami: +4.4% wobec off, ale bez kontroli.
  - **Nie włączać domyślnie.** Kod zostaje w gałęzi `opt-coupled` za wyłącznikiem.
- **Dokończenie, po zwolnieniu GPU i wyjaśnieniu awarii PM4:**
  1. 20–40 seedów, bloki 0/1/2 (+ `LLAMA_SPEC_COUPLED_DT` 1.3, bo głowica MTP jest „za pewna siebie”, wiki `modele/glowica-mtp.md`);
  2. metryka: tok/krok i ms/krok 1 vs 2;
  3. komenda wznowienia w `~/KERNEL/STAN-PRAC.md` (sekcja CoupledSampling).
- **Wartość niezależna od zysku MTP:**
  - (a) spec == plain przy T>0 w trybie BITEXACT, co jest argumentem produktowym (deterministyczne seedy z MTP);
  - (b) gotowy fundament dla DFlash2 przy T=1 (luka 20%, 16i #3/#4);
  - (c) op `GGML_OP_GUMBEL_MAX` jest warunkiem certyfikowanego progresywnego readoutu (16i #8).
- **Commity:**
  - `760ee6990`: mechanizm, test CPU, md5;
  - `3f25fc204`: szybszy kernel, ms/krok +1.5% → +0.4%.

## 7. Do bazy wiedzy

| folder | tytuł | treść (liczby ze źródłami) |
|---|---|---|
| `eksperymenty/` | `2026-10-18-sprzezone-probkowanie-mtp.md` | E-X4. Mechanizm Magnitude (`lib.rs:747-779`, `readout.seismic:325-329`) w forku za `LLAMA_SPEC_COUPLED`: test CPU 200k (chi² p > 1e-4, spec == plain 0/20000), `test-backend-ops GUMBEL_MAX` 152/152, md5 `c4708318`/`6f14e814` bez zmian. XTX run 3 (12 bloków ABBA, 3 seedy): T=1 tok/krok 3.00 off / 3.16 sprzężone / 3.11 kontrola, ms/krok 28.12/28.57/28.16; czysty efekt +1.6% tok/krok, netto +0.2%; identyczność: akceptacja 0.377 → 0.404. Run 5 (20 seedów, szybszy kernel): +4.4% t/s, +0.4% ms/krok, bez kontroli. Status: niedokończone, wstrzymane przez awarię PM4 (`~/qwen-opt/coupled/`, raport 16k). |
| `metody/` | `sprzezone-probkowanie.md` | Gumbel-max z szumem kluczowanym (seed, pozycja, token): bezstratne dla każdego draftera (szkic §2), P(trafienie) ≥ (1−TV)/(1+TV) (arXiv 2408.07978); weryfikacja zostaje dopasowaniem prefiksu, bez `q`; przy BITEXACT spec == plain przy każdym T. Interakcje: filtry celu w drafcie, szybkie ścieżki samplera dokładne, resample gramatyki w osobnej domenie szumu. |
| `lekcje/` | `lekcja-ustalony-seed-to-nie-powtorzenie.md` | Przy ustalonym seedzie powtórzenie bloku daje ten sam tekst (rozrzut bloków ±0.1–0.5 t/s), więc ABBA nie redukuje szumu tekstu. Zmiana strumienia RNG sama dała +7.8% t/s / +3.6% tok/krok na 18 tekstach (run 3, tryb 2 vs 0). Efekt rzędu 2% wymaga ≥ 20 seedów i ramienia kontrolnego z tym samym rozkładem tekstów. |
| `kernele/` | `gumbel-max.md` | Op `GGML_OP_GUMBEL_MAX` (CPU + HIP): top-k/top-p/min-p + Gumbel na wierszu 65536 tokenów; 1. wersja +0.41 ms/krok (28.16 → 28.57, tryb 2 vs 1) w łańcuchu MTP (4 przejścia), 2. wersja (próg mieszczący top_k, LDS, 1 przejście, 1024 wątki) +0.11 ms (27.74 → 27.85). |
| `rocm/` | aktualizacja `pm4-replay.md` | 4 resety GPU 18–19.10 (22:42, 22:57, 23:25, 00:16) + 3 wcześniej: `tape of 823 dispatches did not complete within 10 s` po page faulcie SQC pod adresem 0, także w trybie bez nowego kodu, tylko w seriach ≥ ~50 requestów z eksmisją cache promptu; ten sam podpis 16.10 15:35 (pid 338733). Przyczyna w analizie (Pm4FaultAnalysis). |
| `research/` | `raport-16k-sprzezone-probkowanie.md` (hub) | Link do raportu; status E-X4 w planie 16i §8: kod gotowy, zysk MTP +0…3.6% (nierozstrzygnięty), fundament dla DFlash2. |
