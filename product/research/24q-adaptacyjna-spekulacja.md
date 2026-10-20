# 24q. Adaptacyjna spekulacja: bramka ogona lookupu i głębokość MTP z bieżącej akceptacji (Qwen3.8-27B, XTX, topka)

Data: 2026-10-20. Autor: podagent OptAdaptSpec. Sprzęt: RX 7900 XTX (ROCm, PM4 WA=2), build na farmie (rbuild). Koszt: farma buildów ~$0.2.
Kod: `~/wt/adaptspec`, gałąź `adapt-spec` od topki @ `f2217bac7`, commit `a69537d37`. Binarka: `~/llama-adaptspec`.
Skrypty i dane: `~/qwen-opt/adaptspec/` (`oracle.py` + `oracle.txt` to analiza CPU, `as_*.sh`/`as.jobs` to zadania GPU, `as_steps.py` streszcza logi per krok).

## 0. Werdykt

**NEGATYWNY dla topki. Żaden z kontrolerów nie trafia do produkcji.**

1. **Bramka ogona lookupu (`LLAMA_SPEC_TAIL_ADAPT`)** ma sufit ≤ +0.5% nawet jako wyrocznia, na czacie, krótkim dokumencie i edycji kodu. Spadek −9.4% przy 1.7k (fb-lcb17) nie pochodzi od ogona: był tam 1 ogon (0/11 tokenów, ~0.3% czasu), reszta to szum pojedynczego przebiegu (§2).
2. **Głębokość MTP z bieżącej akceptacji (`LLAMA_SPEC_DEPTH_ADAPT`)** ma realny sufit:
   - symulacja kontrolera: czat +2.6…3.1%, krótki dokument +7…8% (model), mvs −0.1%;
   - wyrocznia znająca wynik kroku: +16…20%, ale ona jest nieosiągalna.

   **Na topce nie jest jednak bezstratna w sensie md5.**
   - Bramka GPU: przy wyłączonych przełącznikach plain `c4708318` i MTP `6f14e814` (= topka).
   - Przy włączonych: MTP `d217c1a0` (głębokość + bramka) i `888170e6` (sama głębokość, bez lookupu). Tekst rozchodzi się na znaku 130, na remisie bliskim zera.
   - Przyczyna: numeryka weryfikacji zależy od szerokości batcha. Już plain ≠ MTP n=4 (`c4708318` vs `6f14e814`). Zmienna głębokość = zmienna szerokość weryfikacji (3…7), a więc inny tekst greedy.
   - Rozkład wyjścia się nie zmienia, ale wymóg „md5 identyczne” nie jest spełniony. Pomiar prędkości pominięto (reguła: bramka nie przeszła).
3. **Głębokość adaptacyjna ma sens tylko na weryfikacji niezależnej od szerokości.** Taką daje gałąź `batch-invariant` @ `365af3e5e` (`LLAMA_SPEC_BITEXACT`, raport 12), która sama kosztuje −2.8…−9%. Zysk kontrolera (+2.6…3.1% czat) jest mniejszy niż ten koszt, więc nawet tam łączny wynik byłby ≤ 0 na czacie. Na krótkich dokumentach (+7…8% modelowo) połączenie może dać zysk netto [INFERENCE].

## 1. Co już było (kb search, żeby nie powtarzać)

- **Stała głębokość MTP** (NOTES.md T1, 2026-10-14, spec_sweep T=1): n=4 102.7, n=5 103.0, n=6 103.5 t/s (Qwen). REKORDY: DRAFT_N=6 111.0, z czego pl-kod 124.7.
- **T2 / łatka 0039 `--spec-draft-adaptive`**: koszt wyceniany głębokością, kalibracja pewności głowicy. Wynik 103.6 vs 102.7 t/s (+0.9%): kod/technika lepiej, czat/proza −5 t/s. Testowane tylko na spec_sweep. Kod jest w topce, ale domyślnie wyłączony.
- **TensorFold `11ecb46b`**: adaptacyjna głębokość „landed+1/+2” przegrała 2–4% ze stałą głębokością.
- **16b E-X3 (kontroler szerokości 5/8/16 ogona)** testował coś innego niż tutaj. Wybierał *szerokość* ogona (5/8/16) z szacunku P(głębokość) i kosztu kroku, a nie włączał ani wyłączał ogona per krok.
  - Na kopiach zawsze wybierał 16 (= stałe W16, ±0.2%).
  - Na czacie wybierał 16 dla rzadkich, złych ogonów: 29/162 przyjętych w 13–15 krokach na ~4500.
  - Głębokości MTP nie dotykał.
- **TideLM `spec_depth.py`** (raport 28): wybór 3/5 co 60 tokenów. U nich kod +21%, proza −10% przy głębokości 5.
- **rdna-boosts „adaptive MTP”** (ZRODLA.md wiersz 57): to tylko pomysł, kodu nie ma.

## 2. Analiza CPU (krok 1): sufity

Dane per krok z 16b (`~/qwen-opt/lookup/logs/*.lk.jsonl`):
- czat: `e1-sweep`, 2230 kroków, T=1;
- code-edit: `e4-mvs-W5`, 845 kroków, topka W16;
- kopie: `e4-copy-W5` (W16) i `e1-copy` (sam MTP).

Dla krótkiego dokumentu (fb-lcb17, 1.7k) logu per krok nie ma. Zastępuje go model: kształt akceptacji per głębokość z en-tech (`mtp-train/RESULTS.md`), przeskalowany do zmierzonych 190 przyjętych / 66 kroków, plus 1 ogon 0/11 na 69 kroków (jak w `fb-lcb17-W16.log`).

Koszt kroku przy 2k: V(w) z `lookup/e2/e2_table.txt`, do tego 0.65–0.9 ms na poziom draftu i 0.21–0.26 ms na każdy przyjęty token ponad 4 (catch-up MTP, dopasowane do zmierzonych 35.6 ms/krok na mvs W16). Krok przy głębokości 4 = 28.7 ms. Dwa modele kosztu: A (e2 + 0.9 ms/poziom) i B (płaskie 1.6 ms/poziom); w tabeli zakres A–B.

Drafty 5 i 6 przyjmowane z q = P(draft 4 | draft 3) danego zestawu. Ta warunkowa akceptacja jest płaska po głębokości we wszystkich logach: czat 0.779/0.749/0.724/0.734.

| zestaw | bramka ogona, wyrocznia | głębokość 2..6, wyrocznia (zna wynik kroku) | głębokość z historii (1–2 kroki, dobrana in-sample) | najlepsza stała głębokość | symulacja zaimplementowanego kontrolera |
|---|---|---|---|---|---|
| czat (spec_sweep T=1) | +0.0% | +15.9…18.1% | +2.3…3.4% | +1.3…1.7% (d=5) | +2.6…3.1% |
| krótki dokument 1.7k (model) | +0.3% | +18.5…20.0% | +8.1…8.9% | +8.1…8.9% (d=6) | +7.2…7.9% |
| code-edit mvs W16 | +0.4…0.5% | +0.2% | +0.0…0.1% | +0.0% | −0.1% |
| kopie W16 | +0.5% | +1.7…1.9% | +0.5…0.8% | +0.2…0.3% | +0.5…0.7% |

Czat per prompt (kontroler, model A): pl-proza +0.1%, en-chat −0.8%, en-code +1.2%, pl-tech +2.6%, en-tech +3.7%, pl-kod +4.4% (`oracle.txt:13-18`).

Wnioski z kroku 1:
- **Bramka ogona ma sufit < 1% wszędzie**, nawet jako wyrocznia, więc według progu 3% wynik jest negatywny.
  - Na czacie ogon prawie się nie włącza.
  - Na mvs/kopii ogony są w 92–95% w pełni przyjęte.
  - **Spadek −9.4% przy 1.7k nie pochodzi od ogona.** W `fb-lcb17-W16.log` jest 1 ogon (0/11 tokenów), czyli ~6.4 ms z 2061 ms (0.3%). Resztę składają dwie rzeczy:
    - +4 kroki (70 vs 66; przyjętych 186 vs 190 przy T=0, ten sam tekst);
    - +4% ms/krok (29.45 vs 28.30 ms).
  - Prefill tego ramienia był też wolniejszy o 3.6% (753 vs 781 t/s), a prefill w ogóle nie dotyka lookupu.
  - Przy 29.5k ramię W16 nie miało żadnego ogona, a przyjętych było 177 vs 174, tym razem na korzyść W16.
  - Wniosek: pojedynczy przebieg 256 tokenów ma szum ±3–6% i różnica nie jest efektem ogona.
- **Głębokość:** sufit wyroczni jest duży (+16–20%), ale osiągalny z historii jest mały:
  - czat: +2–3% (tyle samo co T2), z czego połowę daje sama stała głębokość 5;
  - krótki dokument: modelowo +7–9%, prawie w całości ze stałej głębokości 6 (bez logu per krok to [INFERENCE]);
  - mvs/kopie: ~0, bo krok i tak niesie ogon/łańcuch.

  Próg 3% przekracza czat (na granicy) i krótki dokument, więc zgodnie z zadaniem oba kontrolery zostały zaimplementowane i zmierzone.

## 3. Implementacja (gałąź `adapt-spec`, domyślnie wyłączone)

Pliki: `common/speculative.cpp`, `common/common.h`, `src/llama-context.{h,cpp}`, `src/llama-ext.h`. Przy wyłączonych przełącznikach ścieżka jest niezmieniona (md5 = topka, §4).

- **`LLAMA_SPEC_DEPTH_ADAPT=1`** (`LLAMA_SPEC_DEPTH_MIN`/`_MAX`, domyślnie 2..6): `common_spec_depth_ctl` w drafterze MTP (łańcuch greedy, jedna sekwencja, nie razem z `--spec-draft-adaptive`).
  - Głębokość wybiera argmax po d z E[tok | d] / t(d):
    - E[tok | d] = 1 + q1·(1 + q + … + q^(d−1));
    - q1 i q to zanikające (0.9 na krok) liczniki akceptacji bieżącego zapytania;
    - t(d) = t4 (EMA czasu kroku przeliczona na d = 4) + dt(d), gdzie dt = 0.65 ms/poziom plus kolumny V(w) z 16b E2.
  - `common_spec_depth_n_max()` podnosi rozmiary batcha i stanów rekurencyjnych (`need_n_rs_seq`, `common_speculative_n_max`), tak jak lookup.
  - Graf łańcucha MTP jest trzymany osobno dla każdej głębokości: `llama_set_verify_graph_cache` na kontekście draftu → `chain_scheds` w `llama_context::decode`. Grafy weryfikacji są trzymane per szerokość.
  - Statystyki: linia `draft depth from acceptance` w `print_stats`.
- **`LLAMA_SPEC_TAIL_ADAPT=1`** (tryb lookupu ≥ 2): ogon jest wysyłany tylko wtedy, gdy ostatnie ogony zapytania dają średnio ≥ 1 przyjęty token. Sumy zanikają o 0.8 na ogon, prior to 1 ogon z 4 przyjętymi tokenami.
  - Wstrzymany ogon jest oceniany za darmo, po wygenerowaniu tokenów na jego pozycjach. Dzięki temu bramka może się ponownie otworzyć bez kosztu weryfikacji.
  - Log per krok dostaje pole `"tg":1`. Statystyki: `tail gate withheld …`.

## 4. Pomiary GPU

Kolejka: `~/qwen-opt/adaptspec/as.jobs`; po regule użytkownika „≤ 10 min na pomysł” zestaw skrócono do 4 zadań.

| zadanie | wynik | źródło |
|---|---|---|
| `as-gate` (greedy.sh, 2 prompty × 400 tokenów, T=0, env topki) | A plain `c4708318` ✓, A MTP `6f14e814` ✓; **B (głębokość + bramka) `d217c1a0` ✗**, **B0 (sama głębokość, LOOKUP=0) `888170e6` ✗**; rozjazd na znaku 130 | `~/qwen-opt/queue/logs/as-gate.log`, `/tmp/adaptspec/md5-*.txt` |
| kontroler działał | B: 120 kroków na pierwszym prompcie, głębokości 4:48 5:32 6:40, q1 0.871 q 0.809; łącznie 301 kroków, 2:20 3:87 4:121 5:33 6:40; krok 28.77 ms przy d=4; bramka ogona nic nie wstrzymała (1 ogon, 0/5) | `as-gate.log` (linie `print_stats`) |
| `as-lcb17`, `as-mvs`, `as-sweep` | pominięte (brak znacznika PASS), rc=1 po 0 s | `~/qwen-opt/queue/logs/queue.log` 01:25:39–01:25:42 |

Sprawdzenie, że to nie błąd kodu: zmienia się tylko długość draftu. Tekst greedy to argmax logitów celu, który zależy jedynie od numeryki weryfikacji o danej szerokości. Zależność od szerokości na topce jest znana: plain ≠ MTP n=4, a tylko `batch-invariant` daje plain == MTP (raport 12).

## 5. Działania

1. **Nie włączać** `LLAMA_SPEC_DEPTH_ADAPT` ani `LLAMA_SPEC_TAIL_ADAPT` w topce/produkcji. Gałąź `adapt-spec` zostaje jako zapis (domyślnie wyłączone, md5 przy wyłączonych = topka). Bez kroków instalacji.
2. Bramkę ogona zamknąć na stałe. Sufit wyroczni ≤ 0.5% (`oracle.txt`), a w 16b ogony są w 92–95% w pełni przyjęte.
3. Głębokość adaptacyjną odłożyć do czasu, aż weryfikacja będzie niezależna od szerokości przy koszcie < 2%. Wtedy przenieść `common_spec_depth_ctl` + `chain_scheds` (commit `a69537d37`) na `batch-invariant` i zmierzyć krótki dokument (fb-lcb17) oraz spec_sweep.
4. Pomiar fb-lcb17 (1 przebieg, 256 tokenów) ma szum ±3–6%. Porównania ogona i MTP na nim opierać na ms/krok i liczbie kroków z logu per krok (`as_steps.py`), nie na samym t/s.
5. Zostaje do sprawdzenia [INFERENCE]: stała głębokość 6 na długich podsumowaniach dokumentów. Model daje +8%, ale to zmiana konfiguracji, a nie adaptacja, i też zmienia tekst greedy (inna szerokość).

## Do bazy wiedzy

| folder | tytuł | treść | liczby (źródło) |
|---|---|---|---|
| `eksperymenty/` | 2026-10-20 adaptacyjna spekulacja: bramka ogona i głębokość MTP (`2026-10-20-adaptacyjna-spekulacja.md`) | Kontrolery za `LLAMA_SPEC_TAIL_ADAPT` / `LLAMA_SPEC_DEPTH_ADAPT` (gałąź `adapt-spec` @ `a69537d37`); bramka md5 nie przeszła, więc wynik negatywny dla topki | md5 włączone `d217c1a0` / `888170e6` vs `6f14e814` (`~/qwen-opt/queue/logs/as-gate.log`); głębokości 2:20 3:87 4:121 5:33 6:40 |
| `lekcje/` | nowa: „Zmienna głębokość draftu = inny tekst greedy, dopóki weryfikacja zależy od szerokości” (`lekcja-glebokosc-zmienia-tekst.md`) | Każda polityka zmieniająca szerokość weryfikacji (głębokość, ogon) jest bezstratna tylko rozkładowo; md5 wymaga `batch-invariant` (raport 12, −2.8…−9%) | rozjazd na znaku 130 promptu hash-map (`/tmp/adaptspec/md5-A.mtp.txt` vs `md5-B.mtp.txt`) |
| `metody/` | aktualizacja `kontroler-szerokosci-draftu.md` | Sufity z logów per krok: bramka ogona ≤ 0.5% (wyrocznia); głębokość: wyrocznia +16–20%, z historii czat +2.3–3.4%, krótki dokument ≈ stała d=6 (+8–9%, model), mvs ~0 | `~/qwen-opt/adaptspec/oracle.txt:2-18`, skrypt `oracle.py` |
| `eksperymenty/` | aktualizacja wpisu fb-lcb17 (1.7k −9.4%) | Spadek nie pochodzi od ogona: 1 ogon 0/11 (0.3% czasu); +4 kroki (70 vs 66) i +4% ms/krok przy prefillu też −3.6%; przy 29.5k bez żadnego ogona akceptacja różni się o 3 tokeny | `~/qwen-opt/logs/fb-lcb17-*.log`, `fb-lcb-*.log` (print_timing, print_stats) |
| `research/` | hub raportu 24q (`raport-24q-adaptacyjna-spekulacja.md`) | Link do raportu; status: odłożone do weryfikacji niezależnej od szerokości | §0, §5 tego raportu |
