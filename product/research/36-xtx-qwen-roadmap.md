# 36. XTX / Qwen3.8-27B: budżet kroku prozy T=1, dźwignie z sufitami, droga do prozy ≥ 100 t/s

Data: 2026-10-20. Autor: podagent XtxRoadmap. Tylko CPU (analiza śladów i logów + jedna symulacja numpy głowicy LM), **bez zadań GPU**.
Karta: RX 7900 XTX (gfx1100), topka `9056cea22` + host-gap (zainstalowana `~/llama-topka`), UD-Q4_K_XL, MTP n=4 + lookup W16, coupled, GPU verify, KV q4_0.
Skrypty i surowe wyniki: `~/qwen-opt/xtxroadmap/` (`burst_decomp.py/.txt`, `head2stage2.py/.log/.json`, `hg-trace-{A,B}.parse.txt`).
`[INFERENCE]` = wniosek bez pomiaru.

## 0. Werdykt

1. **Krok prozy T=1 = 27.38 ms przy 2.63 tok/krok = 96.1 t/s** (`~/qwen-opt/hostgap/logs-next/SUMMARY-sweep.txt:7`, pl-proza, ramię B).
   - 89.5% to taśma weryfikacji (24.50 ms), z tego **MMVQ n=5: 21.79 ms**.
   - Draft MTP: 2.28 ms. GPU top-k: 0.11 ms. Host między taśmami: 0.49 ms. Bilans zamyka się co do 0.01 ms.
2. **Podłoga fizyczna** (16.83 GB/krok przy 926 GB/s) to 18.17 ms, czyli 144.7 t/s. **Podłoga inżynierska** to ~21.4 ms (~123 t/s). Dziś krok wykorzystuje 66% sufitu pasma.
3. **Do 100 t/s brakuje 1.08 ms/krok (−3.9%) albo +4.1% tok/krok.** Ten sam config daje jednak pl-prozę 96.1–103.6 t/s zależnie od harnessu i seedów (§1.3). Pierwszy krok to więc stała metryka prozy (E0), bo bez niej nie da się stwierdzić „steady ≥ 100”.
4. **Dwustopniowy head (tqLLM) przy naszym samplerze: jako dokładny (z certyfikatem) nie daje zysku.**
   - Certyfikat wymaga przybliżenia klasy Q8_0, a to zajmuje więcej bajtów niż nasz Q6_K. Q5_K certyfikuje się dopiero przy m = 8192, więc netto ≈ 0.
   - Wariant bez certyfikatu (Q4_K/Q3_K + dokładne przeliczenie top-64) miał 0 chybień na 3000 pozycjach. Daje +1.3–2.0%, ale jest **stratny formalnie** i kosztuje +0.55–0.72 GB VRAM (§3).
5. **Wyniki raportu 35:**
   - E1: n=5 wygrywa tylko na T=0 reasoning (+6.8%), a na czacie n=6/7 przegrywa;
   - E2: kopie checkpointów to 12–14% TTFT świeżego 2k i 41–81% tury agenta, więc **wdrażamy** (tylko strona promptu);
   - E3: kary w drafcie się nie opłacają;
   - E4: prefill nie jest bimodalny;
   - E5: w toku, bramka nie przeszła (§2.2).
6. **Top 5 do prozy ≥ 100 (wszystko bezstratne):**
   1. dataflow w weryfikacji, etap 1;
   2. drzewo dynamiczne 5 wierszy;
   3. fuzja norm w prologu MMVQ;
   4. resztka hosta;
   5. bitexact + adaptacyjna głębokość.

   Łącznie **96.1 → ~104.6 t/s (zakres 102–113)**. Próg 100 pada po #1 + #2 albo po #1 + #3 + #4 (§5).

## 1. Budżet kroku prozy T=1 (~2.6 tok/krok)

### 1.1 Tabela

Źródła:
- ślad rocprofv3 `~/qwen-opt/vcost/prof-gv1/off` (MTP n=4, GPU_VERIFY=1, mediana 107 kroków, wall 27.4 ms; `24r-mmvq-pasmo.md:16-18`), rozbity na serie przez `burst_decomp.py` (`~/qwen-opt/xtxroadmap/burst_decomp.txt`, numery linii niżej jako `bd:N`);
- ślad host-gap `hg-trace-B.parse.txt` (`hg:N`; pod śladem wall 34.45 ms, więc z niego biorę tylko czasy GPU taśm i luki między taśmami).

| pozycja | ms/krok | % kroku | podłoga (ms) | strata vs podłoga | źródło |
|---|---:|---:|---:|---:|---|
| **taśma weryfikacji (GPU)** | **24.50** | 89.5 | 17.44 | 7.06 | `hg:49` (tape.l.gpu); busy 24.47 `bd:12` |
| ├ MMVQ n=5 (wagi, 340 uruch.) | 21.79 | 79.6 | 17.44 | 4.35 | `bd:13`; 16.15 GB/krok `24r:8` |
| │ ├ w tym głowica LM Q6_K 1043 MB | 1.23 | 4.5 | 1.13 | 0.10 | `24r:27`, `lekcja-lm-head-bottleneck.md:12` |
| │ ├ w tym koszt stały uruchomienia (~7–9 µs × 340) | ~2.4 | 8.8 | 0 | 2.4 | `24r:9` |
| │ └ w tym pasmo poniżej sufitu 926 GB/s (małe kształty: k,v 40%, 5120×6144 70%) | ~1.95 | 7.1 | 0 | 1.95 | reszta; `24r:24-30` |
| ├ rms_norm (209 uruch.) | 0.79 | 2.9 | ~0 | 0.79 | `bd:14` |
| ├ GDN (48) + ssm_conv (48) | 0.98 | 3.6 | ~0.16 (stan 151 MB) | 0.82 | `bd:15,17`; stan: `lekcja-prefetch-mall-xtx.md` |
| ├ flash-attn (32) | 0.50 | 1.8 | ~0.05 (KV q4_0) | 0.45 | `bd:16` |
| └ gated/quantize/fwht (145) | 0.40 | 1.5 | 0 | 0.40 | `bd:18-20` |
| **taśma draftu MTP (catch-up + łańcuch)** | **2.28** | 8.3 | 0.73 | 1.55 | `hg:54`; busy 2.02 (+ rzadkie serie b2/b3) `bd:4-11,21-32` |
| └ MMVQ n=1 (warstwa MTP + głowica 64k, 178 MB/przebieg) | 1.66 | 6.1 | | | `bd:5`; `lekcja-lm-head-bottleneck.md:12` |
| **GPU top-k (top-128 dla samplera)** | **0.11** | 0.4 | ~0.02 | 0.09 | `bd:1-3` |
| **host: luka przed taśmą weryfikacji** (sampler CPU, akceptacja, budowa wejść) | **0.49** | 1.8 | ~0.1 | 0.39 | `hg:51` (tape.l.idle_before) |
| reszta (27.38 − suma) | 0.00 | 0 | | | |
| **krok** | **27.38** | 100 | **18.17** | **9.21** | `SUMMARY-sweep.txt:7` |

Uwagi:
- **Granice kerneli w taśmie PM4** to 929 kerneli × 0.46–0.86 µs ≈ 0.43–0.80 ms. Są wliczone w czasy GPU taśm (`lekcja-megakernel-prefetch-nie-granica.md`). Graf HIP kosztowałby kilka razy więcej, ale go nie używamy.
- **Wiersze weryfikacji:** każdy dodatkowy wiersz to +0.85 ms (`24s-proza-drzewa.md:10`). Każdy dodatkowy poziom draftu (wiersz + przebieg MTP) to +1.40 ms (n4 → n5: 27.38 → 28.78 ms, `queue/logs/e1ab-n4a.log:2`, `e1ab-n5a.log:4`).
- **Sampling:** sampler sprzężony (Gumbel) kosztuje +0.66% ms/krok ≈ 0.18 ms (`24p-sprzezone-t1.md:9`) i siedzi w taśmach. Sampler CPU działa na 128 kandydatach, mieści się w 0.49 ms hosta.

### 1.2 Podłogi

- **Fizyczna:** 16.83 GB/krok (`lekcja-lm-head-bottleneck.md:12`) ÷ 926 GB/s (`24r:7`) = **18.17 ms → 144.7 t/s** przy 2.63 tok/krok. Dla kodu (`mvs`, 14.0–14.4 tok/krok) to ~780 t/s.
- **Inżynierska** `[INFERENCE]`:
  - wagi przy 90% sufitu (asymptota MMVQ to 837–873 GB/s, `24r:9`): 20.2 ms;
  - małe operacje po fuzjach: ~1.0 ms;
  - host: ~0.2 ms;
  - razem **~21.4 ms → ~123 t/s**.
- **Dziś:** 16.83 GB / 27.38 ms = 615 GB/s, czyli **66% sufitu**. Sama weryfikacja: 16.15 GB / 24.50 ms = 659 GB/s (71%).
- **Kubełki straty (9.21 ms):**

  | kubełek | ms | dźwignia |
  |---|---:|---|
  | małe operacje w weryfikacji | 2.67 | L7, L12 |
  | koszt stały uruchomień MMVQ | 2.4 | L7 |
  | pasmo małych kształtów MMVQ | 1.95 | L7 |
  | draft powyżej podłogi | 1.55 | L7, L6c |
  | host + top-k | 0.58 | L11 |

### 1.3 Ile brakuje do 100 t/s i dlaczego metryka jest problemem

Przy 2.63 tok/krok trzeba **≤ 26.30 ms/krok (−1.08 ms)**. Przy 27.38 ms trzeba **≥ 2.738 tok/krok (+4.1%)**.

Ta sama konfiguracja n=4 daje jednak różne wyniki na pl-prozie:

| harness | pl-proza t/s | tok/krok | źródło |
|---|---:|---:|---|
| `hg_ab`, seedy 1–3 | 96.1 | 2.63 | `SUMMARY-sweep.txt:7` |
| `x_arm`, seedy 1,2 | 99.1 | 2.71 | `e1ab-n4a.log:2` |
| `x_arm`, seedy 1,2 | 103.6 | 2.83 | `e1-n4a.log` |
| `x_arm`, P0 | 99.1 / 100.8 | | `e3-pen.log:2,7` |

ms/krok jest stabilne (27.3–27.8), a różnica siedzi w tok/krok jednego promptu. **„Steady ≥ 100” trzeba więc zdefiniować na stałym zestawie (E0):**
- ≥ 6 promptów prozy PL/EN × 8 seedów, 400 tok.;
- t/s jako suma tokenów / suma czasu;
- CI 95% bootstrap po promptach, cel ±1.5%.

## 2. Wyniki raportu 35 wpięte w plan

### 2.1 E1–E4

| # | wynik (`35-xtx-eksperymenty-z-researchu.md`) | co to zmienia w planie |
|---|---|---|
| E1 | n=5: T=0 reasoning **+6.8%** (deterministyczne), code-v1 +2.6%, czat T=1 +1.4% [−2.4, +5.4], `mvs` −2.1%; n=6/7 na czacie −2.7% / −7.2% (`35:16,53-56`) | Głębokość nie jest dźwignią prozy w agregacie. Profil `DRAFT_N=5` opt-in dla T=0 reasoning już jest. **Ciekawostka:** pl-proza n=5 = 104.4 w obu połówkach ABBA vs 99.1 przy n=4 (+5.3%, tok/krok 2.71 → 3.01; `e1ab-n5a.log:4`, `e1ab-n5b.log`). To jeden prompt przy seedach 1,2, więc trzeba to sprawdzić na zestawie E0, zanim cokolwiek się z tym zrobi |
| E2 | kopie checkpointów: 12–14% TTFT świeżego 2k; **41–81% prompt_ms tury agenta**; bez checkpointów TTFT 2k −22% (`35:17,82,93-95`) | **Wdrożyć** w trzech krokach (`35:102-104`): (1) bez duplikatu po restore: −150 ms/turę; (2) `std::move` w `prompt_save`: −215 ms; (3) kopia D2D + D2H w tle: −290…−450 ms/turę, +224–450 MiB VRAM. Bezstratne (kopie bajtów). Dekodu nie zmienia |
| E3 | presence 1.5: akceptacja −1.8 pp, t/s −3.1%; repeat 1.05: −1.4 pp (`35:18,119-121`) | Kar po stronie draftu nie robimy. Uwaga dla klientów: presence 1.5 kosztuje ~3% t/s |
| E4 | 10 świeżych startów pp512: rozrzut 0.22% (`35:19`) | Brak problemu MES, nic do zrobienia |

### 2.2 E5 (bitexact + adaptacyjna głębokość): w toku

Bramka `queue/logs/e5-gate.log` pokazuje dla bitexact plain md5 `d41d8cd9`, czyli md5 pustego wyjścia. Wariant `bx.mtp` się różni. Zadania A/B zostały pominięte („E5 gate not passed”, `e5-{Aa,Ab,Ba,Bb}.log`).

Wynik jest więc nieznany. Do planu wchodzi z liczbami z symulacji (`32b:30`, `24q:12-13,55`):
- czat +2.0…2.5% netto (po −0.6% kosztu bitexact);
- pl-proza ≈ +0.1%;
- krótkie dokumenty +6.6…7.3%;
- `mvs` ≈ 0.

## 3. Dwustopniowy head weryfikacji (tqLLM, 32f): czy jest bezstratny przy naszym samplerze

**Sampler produkcyjny:** top-k 20 → top-p → min-p → T=1 → Gumbel (sprzężony). Szybka ścieżka GPU top-k bierze kandydatów top-m z pełnego wiersza i robi test rozłączności z 24m (`24p:11`).

Wynik samplera zależy tylko od zbioru S = top-20 dokładnych logitów i ich wartości. Test 24m potrzebuje jeszcze z(21), żeby wykryć remis na granicy.

**Warunek dokładności.** Niech:
- ẑ = logity przybliżonej głowicy;
- C = top-m według ẑ, przeliczone dokładnie;
- x̃ = q8_1(h), czyli to, co widzi MMVQ;
- eⱼ = wⱼ − ŵⱼ (błąd wiersza).

Wynik jest bitowo identyczny z pełnym wierszem, gdy spełnione są oba warunki:
1. przeliczenie wiersza j ∈ C daje bitowo ten sam float co MMVQ n=5 Q6_K (ten sam x̃, ta sama kolejność redukcji w wierszu; RPB pokazał, że kolejność nie zależy od liczby wierszy na blok, `24r:11`);
2. top-21 ⊆ C.

Warunek 2 da się sprawdzić w czasie działania przez Cauchy'ego–Schwarza, |ẑⱼ − zⱼ| ≤ ‖eⱼ‖₂·‖x̃‖₂:

  **max_{j∉C} ( ẑⱼ + ‖eⱼ‖₂·‖x̃‖₂ ) < z₍₂₁₎(C)**   (ostro; przy niespełnieniu liczymy pełny wiersz).

Dla greedy (T=0) wystarczy: max_{j∉C}(ẑⱼ + ‖eⱼ‖‖x̃‖) < z₍₁₎(C) oraz z₍₁₎ > z₍₂₎.

Koszt oczekiwany = przybliżony przebieg + gather/przeliczenie m wierszy × 5 kolumn + P(fallback) × pełna głowica.

**Pomiar (CPU)** — `head2stage2.py 3000 500`, numery linii = `head2stage2.log:N`:
- 3000 pozycji z `mtp-train/data/ext_p1`, 8 klas PL/EN;
- h = stan po output-norm (odtwarza zapisane log-proby: top-1 0.969);
- przybliżenie = ten sam Q6_K przekwantowany do tańszego typu, więc ocena jest raczej pesymistyczna.

| przybliżenie | MB (vs Q6_K 1043) | med. max\|błąd logitu\| | med. obwiednia CS | certyf. top-21, m=64 / 1024 / 8192 | certyf. greedy, m=128 | empirycznie top-21 ⊆ C, m=64 | linia |
|---|---:|---:|---:|---|---:|---|---|
| Q8_0 | 1351 (+30%) | 0.053 | 0.73 | 100% / 100% / 100% | 100% | 3000/3000 | 3,5-7 |
| Q5_K | 874 (−16%) | 0.36 | 4.94 | 0.4% / 82.7% / 99.0% | 99.87% | 3000/3000 | 9-13 |
| Q4_K | 715 (−31%) | 0.71 | 9.75 | 0% / 0.3% / 5.7% | 86.8% | 3000/3000 | 15-19 |
| Q3_K | 546 (−48%) | 1.50 | 20.7 | 0% | 11.3% | 3000/3000 (m=32: 37 chybień) | 20-25 |
| Q2_K | 417 (−60%) | 2.94 | 40.4 | 0% | 0% | 2990/3000 | 26-31 |

Odstępy dokładnych logitów (mediana / p1): z(21) − z(129) = 3.85 / 2.22; z(21) − z(1025) = 7.46 / 4.53; z(1) − z(1025) = 21.8 / 10.7 (`:32-36`). Obwiednia CS jest ~14× luźniejsza niż prawdziwy błąd.

**Wnioski:**
- **Dokładnie, T=1:** certyfikat wymaga Q8_0, a ten jest większy od Q6_K. Q5_K przy m = 8192 to gather ~34 MB + top-8192 po 248k × 5 kolumn + 1% fallbacku wobec oszczędności 169 MB, czyli netto ≈ 0…+0.4%. **Kill.**
- **Dokładnie, T=0** (Q5_K, m=128, 99.87%): ~−0.15 ms ≈ +0.5% na kodzie T=0 `[INFERENCE]`, 1–2 dni pracy. **Poniżej progu.**
- **Stratnie (bez certyfikatu):**
  - Q4_K + top-64: −328 MB → −0.35 ms → **+1.3%** (proza i kod);
  - Q3_K + top-64: −497 MB → −0.54 ms → **+2.0%**;
  - górna granica chybień ~0.1% pozycji (95%, 0/3000);
  - VRAM +0.55–0.72 GB, bo obie głowice zostają.

  tqLLM jest stratny podwójnie: int8 zamiast oryginału i brak certyfikatu. Jego „lossless” to nie nasza definicja (md5).
- Źródło metody certyfikatu: [verified-progress PR #45](https://github.com/SamMausberg/verified-progress/pull/45) (int8 head z obwiednią i fallbackiem, tylko argmax/temperatura). U nich działa, bo bazą jest BF16, a int8 zajmuje połowę jego bajtów. U nas bazą jest Q6_K.

## 4. Dźwignie

Kolumny:
- „Sufit” = górna granica t/s. Proza liczona od 27.38 ms / 2.63 tok, kod (`mvs`) od ~32.9 ms / 14.2 tok.
- „Bezstr.”: **md5** = tekst identyczny z dzisiejszym; **rozkład** = ten sam rozkład próbkowania, inny tekst przy tym samym seedzie albo nowa referencja md5 greedy; **stratna** = zmienia model albo logity.

| # | dźwignia | sufit proza | sufit kod | bezstr. | koszt | ryzyko | pierwszy eksperyment (≤ 10 min GPU, chyba że napisano CPU) | status |
|---|---|---|---|---|---|---|---|---|
| L1 | **Drzewo dynamiczne MTP** (kształt z pewności MTP, te same 5 wierszy; 6 wierszy) | **+3.9%** / +4.7% offline (`24s:11-12`), realnie +2.5…3.9% po narzucie | ~0 (łańcuchy, lookup) `[INFERENCE]` | rozkład | 10+ dni (maska przodków, stan GDN wg rodzica; TreeWY może skrócić) | wysokie: narzut niezmodelowany | CPU: przeliczyć `tree_dynamic` 24s na danych sprzężonych (24p), bo sufit liczono bez sprzężenia, a sprzężenie + drzewo sumują się słabo (`24s:21`) | otwarte |
| L2 | **Bitexact + adaptacyjna głębokość** (E5) | ≈ 0 (pl-proza +0.1%) | ≈ 0 (`mvs` −0.1%) | md5 = plain bitexact | 0.5–1 dnia | średnie (bramka E5 nie przeszła) | naprawić puste wyjście bitexact (`e5-gate.log`), potem ABBA `x_arm e5` | w toku (XtxLab) |
| L3 | **Profil głębokości per klasa** (E1) | 0 w agregacie; pl-proza +5.3% na 1 prompcie (niepotwierdzone) | reasoning T=0 **+6.8%**, code-v1 +2.6%, `mvs` −2.1% | rozkład (nowa referencja md5 `d71a2c04`) | gotowe (opt-in) + router klas 1–2 dni | niskie | w ramach E0: zestaw prozy n=4 vs n=5 ABBA | n=5 opt-in wdrożone |
| L4 | **Dwustopniowy head** | dokładny: ≈ 0; stratny: +1.3…2.0% | dokładny T=0: +0.5%; stratny: +1.1…1.6% | dokładny / stratny | 1–2 dni | VRAM +0.55–0.72 GB przy ctx 204800 | CPU zrobione (§3). Dalej tylko za zgodą na stratność | dokładny: kill |
| L5 | **DFlash2 na GPU jako tryb klasy** | 0 (PL proza ×0.67 tok/krok, T=1 −6…−10%; `32f:27,115`) | T=0 EN kod/reasoning **+26…32%** (`32f:25`) | rozkład (q-ratio / Gumbel) | 3–5 dni + router; VRAM +0.8–1.1 GB | wysokie (cechy przez hosta → dziś ~+2%) | 32f E2: reasoning-v1 T=0, 3 nonce, drafter Q4_K_M, odczyt tok/krok i ms/krok | otwarte, poza prozą |
| L6a | Fine-tune głowicy MTP na prozie PL | ±2% (`11-mtp-pl-pilot.md:5`) | 0…−3% | rozkład | dni (pod) | — | — | **kill** |
| L6b | Słownik draftu (pełny 248k przy OOV) | −0.51% (`24b:10`) | — | rozkład | — | — | — | **kill** |
| L6c | Tańsza głowica draftu 64k (np. IQ3, 48k) | ≤ +1% `[INFERENCE: 178 MB × przebiegi ≈ 0.6–0.9 ms taśmy draftu]` | ≤ +0.5% | rozkład (tylko draft) | 1 dzień | akceptacja może spaść więcej niż oszczędność | CPU: OOV i akceptacja top-1 MTP na `ext_p1` przy 48k/32k i IQ3 vs IQ4_XS | otwarte, niski priorytet |
| L6d | Korpusy lookupu dla prozy | ≤ +0.5% (wyrocznia ogona `24q:11`) | — | md5 | — | — | — | **kill** |
| L7 | **Dataflow w weryfikacji i drafcie** (wagi następnego MMVQ do VGPR w ogonie małych operacji, małe operacje na wolnych CU) | teoretycznie +32% (pula 6.6 ms: 2.67 + 2.4 + 1.55); **etap 1 realnie 0.7–1.1 ms → +2.6…4.2%** | +2.1…3.5% | md5 (ta sama arytmetyka) | etap 1: 1–2 tyg.; pełny megakernel: miesiące | wysokie (zawieszenia taśmy PM4, `16a:89`) | port `GGML_HIP_PM4_UB` (`16a:70`) do topki z klasą `mmvq5`; górna granica UB po jednej klasie naraz (złe wyniki, tylko czas) | otwarte, **#1** |
| L7' | Trwały kernel z barierami / replay grafu HIP (ROCm 10) | ~0: bariera 0.48–0.77 µs ≈ granica PM4 (`lekcja-megakernel-prefetch-nie-granica.md`); zmiany grafów w ROCm 10.0 nie dotyczą taśm PM4 | ~0 | — | — | — | — | **kill** |
| L8 | Rezydencja w Infinity Cache (96 MB) | < 1%: odległość ponownego użycia 16.8 GB ≫ 96 MB; touch +0.2…0.6% = szum (`lekcja-prefetch-mall-xtx.md`) | < 1% | md5 | — | — | — | **kill** |
| L9 | Precyzja stanu GDN / KV | int8 GDN: KLD 0.0234 (`24g:43`); bf16 stanu ≈ −0.15 ms (+0.5%) `[INFERENCE]`; KV już q4_0 | +0.4% | stratna | 2–3 dni | KLD | — | **kill** (int8), bf16 poniżej progu |
| L10a | Mieszanka typów tensorów GGUF przy równym KLD | **+4…6.6%** (−5…8% bajtów weryfikacji przy 762 GB/s) `[INFERENCE]` | j.w. | stratna (inny model, nowe md5) | 2–4 dni (KLD per tensor na CPU + kwantyzacja) | decyzja użytkownika „nie zmieniamy kwantów” (`24g:11`) | CPU: wrażliwość KLD per tensor na wiki/plprose (bez pobierania BF16 nie da się; łącze `35:21-22`) | zablokowane decyzją |
| L10b | EXL3-SC 4.0 (−24% bajtów przy KLD 0.0062 vs 0.0051; `32c:40,61`) | +15…23% przy tej samej sprawności kernela; GEMV kraty na gfx1100 niezmierzone | j.w. | stratna | tygodnie (nowy format i kernel) | wysokie | E6 z 35 (zablokowane łączem) | zablokowane |
| L11 | **Resztka hosta** (0.49 ms luki przed weryfikacją) | **+0.7…1.8%** | +0.6…1.5% | md5 | 1–3 dni (ZOS-lite: wejścia następnego kroku w trakcie taśmy) | średnie | A/B `GPU_FORCE_BLIT_COPY_SIZE=1024` (~−60 µs `[INFERENCE]`) + nowy ślad host-gap z medianą per para | otwarte, **#4** |
| L12 | **Fuzja norm w prologu MMVQ** (rms_norm 0.79 + gated 0.21 + quantize 0.15 + fwht 0.04 ms w weryfikacji) | górna granica ~0.9 ms (`24g:37`), realnie 0.3–0.5 ms → **+1.1…1.9%** | +0.9…1.5% | md5 (ta sama kolejność sum, q8_1 w LDS) | 3–5 dni | średnie | `~/qwen-opt/hipfire/ub.sh` z `GGML_HIP_UB_SKIP_NORM=1` (build w `~/wt/hipfire` istnieje, `24g:47`): < 0.3 ms → kill | otwarte, **#3** |
| L13 | Koszt stały MMVQ (RPB, PAIR2, k/v w jednym uruchomieniu) | RPB −3% (`24r:10-12`), PAIR2 +0.4% (`24w:5`); k+v razem ~0.1 ms | — | md5 | — | — | — | kill / wchłonięte przez L7 |
| L14 | Strona promptu: checkpointy (E2), natywny renderer ChatML (32b) | dekod 0; **TTFT 2k −12…22%, tura agenta −290…−450 ms**; renderer 63 → ~1–2 ms przy 91k (`32b:83`) + ochrona przed wstrzyknięciem | 0 | md5 | 1–2 dni + 2–3 dni | niskie | E2 zrobione; dalej md5 greedy + restore == żywy serwer | **do wdrożenia** |
| L15 | Kary w drafcie (E3) | ≤ 3% i tylko przy karach | — | — | — | — | — | **kill** |

## 5. Droga do prozy ≥ 100 t/s steady (i dalej)

**Krok 0: E0, metryka prozy** (10 min GPU). Zestaw z §1.3, n=4 vs n=5 w ABBA. Daje bazę z CI i rozstrzyga sygnał pl-prozy z E1. Bez tego żadnej wygranej poniżej ~3% nie da się odróżnić od szumu.

| # | dźwignia | oczekiwany zysk prozy (środek) | zakres | skumulowane (od 96.1) | kod `mvs` | pierwszy eksperyment |
|---|---|---:|---|---:|---|---|
| 1 | L7 dataflow, etap 1 (weryfikacja + draft) | +3.0% | +2.0…4.2% | **99.0** | +2.5% | UB `mmvq5` w topce (port + 10 min) |
| 2 | L1 drzewo dynamiczne 5 wierszy (TreeWY dla GDN) | +3.0% | +2.5…3.9% | **102.0** | 0 | CPU: `tree_dynamic` na danych sprzężonych |
| 3 | L12 norm w prologu MMVQ | +1.3% | +1.0…1.9% | **103.3** | +1.2% | `ub.sh` SKIP_NORM (10 min) |
| 4 | L11 resztka hosta | +1.0% | +0.5…1.8% | **104.3** | +1.0% | A/B blit env + ślad (10 min) |
| 5 | L2 bitexact + adaptacja (E5) | +0.3% | 0…+5% (jeśli E0 potwierdzi głębokość 5 na prozie, kontroler to złapie) | **~104.6** | 0 | naprawa bramki E5, ABBA |

- **Zakres skumulowany: 102–113 t/s**, środek ~104.6.
- **Kiedy pada próg 100:** po #1 + #2 (środek 102.0) albo po #1 + #3 + #4 bez drzewa (środek ~101.3, mniejsze ryzyko). Drzewo jest drogie (10+ dni), więc kolejność wykonania to: #3 i #4 (tanie, testy po 10 min), potem #1, potem #2.
- **Kolejność eksperymentów GPU** (wszystkie ≤ 10 min, jawny env PM4 w zadaniu):
  1. E0;
  2. `ub.sh` SKIP_NORM;
  3. A/B `GPU_FORCE_BLIT_COPY_SIZE`;
  4. UB `mmvq5` po porcie (najpierw osobno `norm`, potem `mmvq5`, nigdy wszystkie klasy naraz);
  5. E5 po naprawie bramki.
- **Dalej (poza prozą albo wymaga decyzji użytkownika):**
  - L5 DFlash2 jako tryb T=0 EN kod/reasoning: +26…32%;
  - L3 profil n=5 reasoning: +6.8%, zrobione;
  - L10a mieszanka GGUF przy równym KLD: +4…6.6% na wszystkim, **stratna, decyzja użytkownika**;
  - L10b EXL3-SC: +15…23%, zablokowane łączem i kernelem;
  - L4 stratny head: +1.3…2.0%.
- Z L7 (etap 1 i 2), L12, L11 i L1 razem proza dochodzi do ~110–115 t/s `[INFERENCE]`. To ~90% podłogi inżynierskiej (123 t/s). Dalej tylko bajty (L10) albo więcej tok/krok (lepszy drafter).

## 6. Nowe źródła (2026-10-20)

| źródło | co | dla nas |
|---|---|---|
| [verified-progress PR #45](https://github.com/SamMausberg/verified-progress/pull/45) | certyfikowany int8 head (obwiednia + przeliczenie kandydatów + fallback), Qwen3.5-4B BF16 | metoda certyfikatu z §3; zysk tylko wobec bazy BF16 |
| [TreeWY, arXiv 2608.20961](https://arxiv.org/abs/2608.20961) | weryfikacja drzewa dla hybryd GDN: odtwarza tylko stan przyjętej ścieżki | może skrócić L1 (stan GDN wg rodzica) |
| [DominoTree, arXiv 2607.08642](https://arxiv.org/abs/2607.08642), [DARTree, arXiv 2608.13524](https://arxiv.org/abs/2608.13524) | drzewa dla drafterów blokowych (DFlash) | tylko EN i T=0; dotyczy L5, nie prozy |
| [hipfire PR #894](https://github.com/warpfront/hipfire/pull/894), [v0.4.2](https://github.com/warpfront/hipfire/releases/tag/v0.4.2) | domyślny split-KV weryfikatora FA2 na gfx1100 przy długim kontekście (+13.6% DFlash) | tylko długi kontekst; proza przy krótkim nie zyskuje |
| [ROCm 10.0 release notes](https://rocm.docs.amd.com/en/docs-10.0.0/about/release-notes.html) | grafy HIP: koalescencja zdarzeń, atrybucja per węzeł w ROCprofiler-SDK | nie dotyczy taśm PM4; atrybucja może pomóc w diagnostyce |
| [AMD-Ecosystem llama.cpp gfx11-rocm-100-20261015](https://github.com/AMD-Ecosystem/llama.cpp/releases/tag/gfx11-rocm-100-20261015) | prebuilt gfx11 | nic nowego dla nas |

## 7. Pliki

- `~/qwen-opt/xtxroadmap/burst_decomp.py` (+ `.txt`): rozbicie kroku na serie i klasy kerneli ze śladu rocprofv3 (`vc_trace.kclass`).
- `~/qwen-opt/xtxroadmap/head2stage2.py` (+ `.log`, `.json`): certyfikat i empiria dwustopniowego heada; `head2stage.py/.log`: v1 (ustalenie, że `h.f16` to stan po normie).
- `~/qwen-opt/xtxroadmap/hg-trace-{A,B}.parse.txt`: parsowanie śladów host-gap (`hg_parse.py`).

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| metody | Budżet kroku prozy T=1 (XTX, Qwen 27B, topka) | 27.38 ms = weryfikacja 24.50 (MMVQ n=5 21.79, w tym head 1.23, koszt stały ~2.4) + draft 2.28 + top-k 0.11 + host 0.49. Podłoga fizyczna 18.17 ms (144.7 t/s), inżynierska ~21.4 ms (~123 t/s); dziś 66% sufitu 926 GB/s (raport 36 §1) |
| lekcje | Dwustopniowy head jest dokładny tylko przy przybliżeniu klasy int8 | Przy top-k 20 certyfikat CS (max_{j∉C}(ẑⱼ+‖eⱼ‖‖x̃‖) < z₍₂₁₎) przechodzi dla Q8_0 (100% przy m=64), dla Q5_K dopiero przy m=8192 (99%), dla Q4_K nigdy. Obwiednia CS ~14× luźniejsza niż prawdziwy błąd. Przy bazie Q6_K dokładny wariant nie oszczędza bajtów; stratny Q4_K/Q3_K + top-64 to +1.3–2.0% (raport 36 §3) |
| lekcje | Metryka pl-prozy na jednym prompcie nie wystarcza | Ten sam config n=4: 96.1 (hg_ab, seedy 1–3) vs 99.1–103.6 (x_arm, seedy 1,2) przy stałym ms/krok; różnica w tok/krok. „Steady ≥ 100” mierzyć na ≥ 6 promptach × 8 seedów, suma tokenów / suma czasu, CI po promptach |
| wyniki-negatywne | Infinity Cache, trwały kernel z barierami, kary w drafcie, fine-tune MTP na PL, korpusy lookupu dla prozy | sufity < 1% albo ujemne; powody i źródła w raporcie 36 §4 (L6, L7', L8, L15) |
| eksperymenty | E5 bitexact + adaptacja: bramka 2026-10-20 | bitexact plain dał md5 `d41d8cd9` (puste wyjście), A/B pominięte; wynik nieznany (raport 36 §2.2) |
| metody | Pula „DRAM bezczynny” w kroku Qwena | małe operacje 2.67 + koszt stały MMVQ 2.4 + pasmo małych kształtów 1.95 + draft 1.55 + host 0.58 = 9.2 ms; tylko dataflow (prefetch do VGPR, małe operacje na wolnych CU) celuje w więcej niż granice PM4 |
