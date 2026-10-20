# 40. Akceptacja draftu na prozie (E0): gdzie pęka łańcuch MTP, które dźwignie zostały, plan treningu głowicy

Data: 2026-10-20. Autor: podagent ProseAccept. Karta: RX 7900 XTX, produkcyjna `~/llama-topka` (MTP n=4, lookup 3 W16, sprzężone próbkowanie, GPU verify, PM4 WA=2 + GUARD, `HSA_USE_SVM=0`).
GPU tylko przez kolejkę (`p40.jobs`, `p40b.jobs`, `p40c.jobs`, każde zadanie z jawnym env PM4). Łącznie ~19 min GPU: log per krok 7.8 min, `mtp_extract` 1.7 min, ABBA głębokości ~9.5 min. Bez treningu na GPU, bez błędów amdgpu.
Skrypty i wyniki: `40-skrypty/` (kopia z `~/qwen-opt/prose-accept/`), logi `~/qwen-opt/prose-accept/logs/`, `~/qwen-opt/queue/logs/p40-*.log`.
`[INFERENCE]` = wniosek bez pomiaru.

## 0. Werdykt

- **Proza bez myślenia jest dla głowicy MTP trudniejsza niż wszystko, na czym ją dotąd mierzyliśmy.** Warunkowa akceptacja na E0 przy T=1 wynosi 0.655 / 0.503 / 0.407 / 0.382 (pozycje 1–4), po polsku 0.635 / 0.461 / 0.350 / 0.296. Na odpowiedziach po myśleniu (dane z 24s) jest to 0.710 / 0.587 / 0.533 / 0.530. Strata leży głównie na pozycjach 2–4: wyrocznia greedy (draft = argmax celu) trzyma 0.76 na każdej pozycji.
- **T=0 niewiele pomaga:** 2.265 tok/krok wobec 2.175 przy T=1. Problem nie leży w losowaniu, tylko w tym, że głowica nie trafia w argmax celu (zgodność argmax na pozycji 1: PL 0.66, EN 0.71).
- **Lookup na prozie daje dokładnie 0.** Na 13 187 krokach nie było ani jednego ogona ani łańcucha. Całą akceptację daje MTP.
- **Gdzie pęka (PL):** 58% to wybór następnego słowa, 23% inna końcówka tego samego słowa (np. `łem`→`łam`), 14% tokeny spoza słownika 64k, 4% interpunkcja. Tokeny OOV pękają 2.1× częściej niż przeciętny token, rzadkie (ranga 32–64k) 1.4× częściej. Po angielsku 84% to wybór słowa.
- **Jedyna dźwignia z sufitem ≥ +25% to lepsza głowica MTP.** Wszystkie pozostałe dają ≤ +5% każda. Głowica z report 11 (train1, 0.39 M tokenów PL on-policy z myśleniem) daje na E0 w lustrze **PL +2.0%, EN −1.1%, razem +0.4%**. Zysk siedzi na pozycjach 3–4, więc trening rekurencyjny działa, tylko dane były złe (z myśleniem, prawie bez prozy, tylko PL) i za małe.
- **Rekomendacja:** samodestylacja głowicy MTP na 20 M tokenów on-policy, w 70% bez myślenia, ze stratą TV na filtrowanych rozkładach (to, co nagradza sprzężone próbkowanie), łańcuch K=4. Chmura (A100/H100) ~$15–30, ~1 dzień pracy + ~10 h maszyny. Szansa, że sama da +25% na prozie: **~10%**. Szansa na +10%: ~35%. Razem z małymi dźwigniami (§4) oczekuję ~+15–20% (≈ 91–95 t/s), a 100 t/s z prawdopodobieństwem ~25%.
- **Szybka wygrana z pomiaru:** głębokość n=3 na samej prozie (§3.3).

## 1. Metoda

1. **Log per krok na E0** (`p40-e0log`). Produkcyjna topka z `LLAMA_SPEC_LOOKUP_LOG` (istniejący przełącznik: drafty, liczba draftów MTP, rodzaj kroku, liczba przyjętych). Zestaw E0: 8 promptów × seedy 1–8 przy T=1 oraz jedno przejście T=0, 400 tokenów, thinking off (`pa_bench.py`, `pa_arm.sh`). Token, na którym pękł łańcuch, to `id` następnego kroku. Analiza: `pa_analyze.py`.
   - Wynik ramienia: 77.11 t/s, 2.175 tok/krok, 28.20 ms/krok. E0 z raportu 37: 78.93 t/s, 2.158 tok/krok, 27.34 ms/krok. Tok/krok się zgadza. ms/krok jest o +3% wyższe, bo w tym samym czasie na CPU szła moja ekstrakcja w lustrze (4 wątki poza `taskset`). Do wniosków o akceptacji to nie przeszkadza.
2. **Lustro MTP na wyjściach E0** (`p40-extract`). `mtp_extract` przebudowany na nagłówkach i bibliotekach topki (`mtp_extract_topka`). 40 sekwencji (T=1 seedy 1–4 + T=0), 18 392 tokenów. Prompty odtworzone tokenizerem BPE z GGUF (`bpe.py`), długości zgodne 40/40 z logiem serwera. Odpowiedzi to dokładnie tokeny serwera.
   - Łańcuch llama.cpp na tych danych daje T=0 PL 2.132 tok/krok, a serwer 2.133. Lustro PyTorch (`ext_head.py` + `pa_offline.py`, estymatory z 24s) daje T=1 sprzężone 2.244 wobec 2.175 online (+3%, w tym brak rekwantyzacji IQ4_XS). **Protokół offline odtwarza E0**, więc nadaje się na bramkę treningu.
3. **Dane fazy 1** (`ext_p1`, 17.7k startów prozy z myśleniem, 24s) jako porównanie oraz głowica train1 z raportu 11 w obu zestawach.

## 2. Diagnoza

### 2.1 Akceptacja per pozycja (warunkowa: P(przyjęty k | przyjęte 1..k−1))

| zestaw | poz. 1 | poz. 2 | poz. 3 | poz. 4 | S₁..S₄ (bezwarunkowe) | tok/krok |
|---|---|---|---|---|---|---|
| **E0 T=1, online** | **0.655** | **0.503** | **0.407** | **0.382** | 0.655 / 0.328 / 0.133 / 0.051 | **2.175** |
| E0 T=1 PL | 0.635 | 0.461 | 0.350 | 0.296 | 0.635 / 0.292 / 0.102 / 0.030 | 2.066 |
| E0 T=1 EN | 0.677 | 0.546 | 0.457 | 0.440 | 0.677 / 0.369 / 0.168 / 0.074 | 2.296 |
| E0 T=0, online | 0.685 | 0.527 | 0.417 | 0.422 | 0.685 / 0.360 / 0.150 / 0.063 | 2.265 |
| E0 T=0 PL / EN | 0.675 / 0.697 | 0.481 / 0.577 | 0.310 / 0.515 | 0.293 / 0.493 | – | 2.133 / 2.413 |
| E0 T=1, lustro: draft greedy | 0.625 | 0.502 | 0.419 | 0.387 | – | 2.121 |
| E0 T=1, lustro: sprzężony (produkcja) | 0.674 | 0.523 | 0.441 | 0.404 | – | 2.244 |
| E0 T=1, lustro: maksymalne sprzężenie tej głowicy (Σ min(q′, p′)) | 0.694 | 0.540 | 0.463 | 0.429 | – | 2.316 |
| E0 T=1, lustro: wyrocznia greedy (draft = argmax celu) | 0.769 | 0.761 | 0.760 | 0.758 | – | 3.136 |
| proza z myśleniem (24s, odpowiedzi), sprzężony | 0.710 | 0.587 | 0.533 | 0.530 | – | 2.467 |

Per prompt (T=1, online): en-essay 2.37, en-travel 2.30, en-letter 2.28, en-story 2.24, pl-esej 2.19, pl-list 2.09, pl-latarnik 2.00, pl-opis 2.00 tok/krok. Warunkowa akceptacja na pozycji 4 spada w pl-latarnik i pl-list do 0.26.

Wnioski:
- **Na pozycji 1 do wyroczni brakuje ~0.1, na pozycjach 2–4 0.25–0.38.** Cel nie jest bardziej płaski na dalszych pozycjach (wyrocznia jest płaska: 0.77 → 0.76). Głowica traci na rekurencji, czyli na własnym stanie zamiast stanu celu.
- Cel bez myślenia jest nieco bardziej płaski niż po myśleniu: średnie p′max 0.77 vs 0.80–0.82, udział pozycji z p′max < 0.5 20% vs 15%. Tłumaczy to ~6% różnicy tok/krok. Reszta (~8%) to głowica (zgodność argmax na pozycji 1: E0 PL 0.655 vs 0.711 po myśleniu).
- **Sprzężenie jest bliskie maksimum dla tej głowicy:** dokładne rejection sampling na filtrowanym q′ dałoby +3.2% tok/krok (lustro). Reszta zysku wymaga innego q, a nie innego losowania.

### 2.2 Gdzie pęka łańcuch (online, T=1, udział w pęknięciach i w generowanych tokenach)

Klasa = klasa tokenu, który cel wylosował w miejscu pęknięcia (`tokclass.py`). `wstart` = początek słowa (spacja + litery), `cont` = ciąg dalszy słowa bez spacji (końcówki fleksyjne, kawałki słów), `oov` = spoza słownika draftu 64k.

| klasa | PL: pęknięcia | PL: tokeny | PL ×częściej | EN: pęknięcia | EN: tokeny | EN ×częściej |
|---|---|---|---|---|---|---|
| początek słowa (wybór słowa) | **57.6%** | 40.6% | 1.42 | **83.6%** | 76.0% | 1.10 |
| ciąg dalszy słowa / końcówka | **23.7%** | 41.9% | 0.57 | 3.6% | 7.0% | 0.51 |
| poza słownikiem 64k | **14.0%** | 6.7% | **2.09** | 6.3% | 2.7% | **2.38** |
| interpunkcja | 4.4% | 10.1% | 0.44 | 5.5% | 11.9% | 0.46 |
| nowa linia / cyfry / inne | 0.4% | 0.7% | – | 1.0% | 2.3% | – |

- **Polska fleksja:** w 22% polskich pęknięć draft i cel to oba ciągi dalsze tego samego słowa (ten sam rdzeń, inna końcówka: `łem`/`łam`, `ła`/`ł`, `za`/`zał`). Po angielsku takich pęknięć jest 4.5%.
- **Granica słowa i przecinka:** pary „cel słowo, draft przecinek/kropka” i odwrotnie to 12% pęknięć (PL) i 10% (EN). Najczęstsze pojedyncze pary PL to `,`→` w`, `.`→`,`, `,`→`.`, ` w`→` na`.
- **Rzadkie słowa:** tokeny o randze 32–64k pękają 1.4× częściej, OOV 2.1–2.4×. Razem to 21% polskich pęknięć przy 12% tokenów.
- **Pozycja pęknięcia:** 36% na pozycji 1, 34% na 2, 21% na 3, 9% na 4.
- T=0 daje ten sam obraz (PL: słowo 63%, końcówka 17%, OOV 15%).

### 2.3 MTP vs lookup

E0 przy T=1 i T=0: 13 187 kroków, lookup coś zaproponował w 37 z nich, **0 ogonów, 0 łańcuchów, 0 tokenów**. Wszystkie 13 737 + 1 777 przyjętych tokenów pochodzi z MTP. Koszt lookupu na hoście: 39.5 ms na 13 187 kroków, czyli 3 µs/krok. Nie ma czego tu wyłączać ani poprawiać. Lookup zostaje dla kodu i kopii.

### 2.4 T=1 vs T=0 i temperatura

- T=0 vs T=1 online: +4.1% tok/krok (2.265 vs 2.175); ms/krok −1.3%.
- T=0.7 / 0.8 zamiast 1.0 (lustro na prozie 24s, sprzężony łańcuch-4): +1.0% / +0.7% tok/krok. Sampler GGUF (top-k 20, top-p 0.95, min-p 0.05) i tak już mocno tnie ogon, więc temperatura użytkownika prawie nie wpływa na akceptację. To zresztą nie jest dźwignia bezstratna, bo zmienia rozkład wyjścia.
- Temperatura draftu (24s): DT=1 optymalne. Sprzężenie vs greedy: +3.7% (24p, już w produkcji).

## 3. Dźwignie

Model kosztu: krok n=4 = 27.34 ms (E0). Dodatkowy wiersz weryfikacji kosztuje 0.85 ms, a poziom draftu razem z przebiegiem MTP 1.45–1.6 ms (35 E1). Do 100 t/s potrzeba **2.734 tok/krok (+26.7%)** przy tym samym koszcie kroku.

| # | dźwignia | sufit tok/krok | Δ ms | sufit t/s | realnie | praca | status |
|---|---|---|---|---|---|---|---|
| 1 | **Douczenie głowicy MTP na prozie bez myślenia** (TV, łańcuch K=4, on-policy) | wyrocznia greedy: 3.14 (+44%); „pozycje 2–4 jak pozycja 1”: 2.55 (+18%); 0.70 na każdej pozycji: 2.77 (+28%) | 0 | 101–114 | **+5…12%** `[INFERENCE]` (train1: +0.4%, PL +2.0%) | 1 dzień + ~10 h maszyny, $15–30 | **rekomendowane (§5)** |
| 2 | Słownik draftu: ogon OOV | OOV: PL 6.7% tokenów / 14% pęknięć, EN 2.7% / 6.3%; sufit 24b przeskalowany na E0 ≈ +4.5% (PL +6.8%) | +0.07 (klastry, 21o) lub +1.5 (pełna głowica, 24b) | – | klastrowy ogon: **+1…2%** (PL), pełna głowica < 0 | 2–3 dni (`mul_mat_id` z klastrami) | kandydat 21o, po #1 |
| 3 | Głębokość draftu | n=3: −2.3% tok; n=5: +0.9% tok | n=3 −1.5; n=5 +1.5 | n=3 +3.3% (model) | ABBA: n=3 +4.3% (82.4 vs 79.0 t/s) | 0 kodu (`DRAFT_N=3` per klasa) | §3.3 |
| 4 | Temperatura / top-k a sprzężenie | sprzężenie maksymalne (klasyczne rejection na filtrowanym q′): +3.2%; T 0.7: +1% (niebezstratne) | ~0 | +3% | +2…3% `[INFERENCE]` | 2–3 dni (q′ z łańcucha, próbka z reszty max(p′−q′,0) w GPU verify) | po #1 (lepsza głowica zmienia q′) |
| 5 | Lookup na prozie | 0 tokenów na 13 187 kroków | 3 µs | 0 | 0 | – | **bez sensu na prozie**, zostaje dla kodu |
| 6 | Drzewo / drugi kandydat na pozycji 1 | 24s: statyczne +4.3% tok, dynamiczne 5 wierszy +3.9%, 6 wierszy +7.9% tok | +0 / +0.85 | +3.9…4.7% | +3…4% (więcej przy lepszej głowicy) | dni (GDN per gałąź, maska przodków) | po #1; 36% pęknięć jest na pozycji 1 |
| 7 | Drugi etap draftu tylko na pozycji 1 (osobny, mocniejszy przewidywacz) | do wyroczni na poz. 1: +0.11 S₁ → +7% tok, jeśli łańcuch dalej jak dziś | koszt przewidywacza | – | < #6 `[INFERENCE]` | nowy model | nie: pozycja 1 to najmniejsza luka (0.10 vs 0.25–0.38) |
| – | odniesienie: dataflow w weryfikacji (37) | – | −0.5 | +2% | +2% | dni, ryzyko zawieszeń | 37 |

Stos realistyczny: #1 (+8%) × #3 (+3%) × #6 (+4%) × #4 (+2%) × #2 (+1%) × dataflow (+2%) ≈ **+21%**, czyli ~95 t/s `[INFERENCE]`. Same małe dźwignie bez #1 dają ~+12%. **Bez lepszej głowicy 100 t/s na prozie jest nieosiągalne.**

### 3.1 Głowica MTP: co zmierzył raport 11 i co widać teraz

- Raport 11: 1.7 M tokenów (0.39 M on-policy PL, z myśleniem), FastMTP K=5, 0.9 TV + 0.1 CE. Offline +0.2%, online n=4 pl-proza +2.3%, reszta 0…−1.7%. Metryka offline była greedy (sprzężenia jeszcze nie było).
- **Teraz w metryce sprzężonej (lustro, ta sama głowica train1):**
  - proza z myśleniem (24s): razem +0.8%, PL +2.3%, EN −1.0%;
  - **E0 bez myślenia: razem +0.4%, PL +2.0% (2.101 → 2.143), EN −1.1%** (2.388 → 2.362);
  - zysk PL leży na pozycjach 3–4: warunkowa 0.375 → 0.410 i 0.331 → 0.367.
- Sprzężenie nie ukrywało więc zysku (ten sam obraz co w metryce greedy). Trening rekurencyjny przesuwa jednak dalsze pozycje, i to przy 0.39 M tokenów, 220 krokach i danych tylko PL. EN spada, bo w danych nie było EN.
- **Luka do wyroczni jest na E0 większa niż na danych z raportu 11** (+40% vs +27%). Proza bez myślenia to klasa, na której głowica Qwena jest najsłabsza, i dokładnie tej klasy nie było w danych treningowych.

### 3.2 Słownik 64k

- E0 PL: 6.7% wygenerowanych tokenów jest spoza 64k, a 24b mierzył 5.0% na prozie z myśleniem. EN: 2.7%.
- Pęknięcia na OOV to 14% (PL) i 6.3% (EN). Część z nich i tak by pękła: OOV to najczęściej rzadkie słowa, a w paśmie 32–64k pękanie jest 1.4×.
- Sufit pełnej głowicy (każdy OOV trafiony jak przeciętny token) ≈ +4.5% tok/krok na E0. Koszt pełnej głowicy +5.6% kroku przy stałym użyciu (24b), więc netto ujemne.
- Klastrowy ogon (21o, +0.25% kroku, odzysk 35–55% luki) daje ≈ +1…2% na PL, ~+1% średnio `[INFERENCE]`. Po douczeniu głowicy udział OOV w pęknięciach wzrośnie, bo reszta pęknięć się zmniejszy. Zrobić po #1.

### 3.3 Głębokość na samej prozie

Model (S₄ = 0.051, krok −1.5 ms na poziom): n=3 +3.3% (PL +4.3%, EN +2.4%), n=2 +2.8%, n=5 −4.4%. E1 z raportu 35 (n=4 najlepsze na czacie) liczono na spec_sweep z myśleniem, gdzie S₄ jest 2–3× większe.

Pomiar ABBA (`p40c.jobs`, E0 seedy 1,2, n=4 | n=3 | n=3 | n=4, świeży serwer na ramię, `prose_sum.py`, 16 komórek na ramię, 12 800 tok): **n=3 82.4 t/s [79.6, 85.4] vs n=4 79.0 t/s [76.2, 81.7] → +4.3%** (tok/krok 2.147 vs 2.162, ms/krok 26.05 vs 27.37). n=3 wygrywa na wszystkich 8 promptach (PL +1.8…+6.7%). Zgadza się z modelem (+3.3%). Głębokość nie zmienia wyjścia zachłannego, więc bramka md5 nie zależy od n. Na czacie z myśleniem i na kodzie n=4 nadal jest lepsze (raport 35), dlatego wdrażać tylko per klasa (proza → `DRAFT_N=3`). Kandydat przekazany do IntegTopka.

## 4. Dlaczego nie inne drogi do +25%

- Drzewa, sprzężenie maksymalne, OOV i głębokość mają sufity +3–5% każda (§3), bo działają na tej samej głowicy. Na prozie 44–49% pierwszych odrzuceń leży poza top-6 MTP (24s).
- DFlash2 / EAGLE-3: na polskiej prozie ×0.67 tok/krok (32f, 16d), publiczny EAGLE-3 dla tej rodziny τ 2.2–2.4 vs MTP 3.74 (raport 10). Trening od zera kosztuje dziesiątki do setek GPU-h, a TensorFold dostał 3.8–5.1% akceptacji pierwszego tokenu.
- Głowica dwuwarstwowa: dodatkowe ~0.65 ms na każdy przebieg × 4 = +2.6 ms/krok (+9.5%). Musiałaby dać > +10% tok/krok, zanim w ogóle wyjdzie na zero `[INFERENCE]`.

## 5. Rekomendacja i plan

### 5.1 Jedna droga: samodestylacja głowicy MTP na prozie bez myślenia

**Co:** ta sama architektura, ten sam GGUF i te same typy kwantów (Q6_K/Q8_0 w pliku, IQ4_XS przy ładowaniu), podmienione tylko `blk.64.*` (pień nietknięty: md5 plain bez zmian, raport 11 §5). Bezstratne z definicji, bo zmienia się tylko draft.

**Szansa:** +25% na prozie z samej głowicy ~10%; ≥ +10% ~35%; ≥ +5% ~60%; brak zysku ~25%.
- Za: luka do wyroczni +40%; train1 przesunął PL o +2% na 0.39 M tokenach niewłaściwej klasy, i to tam, gdzie luka jest największa (pozycje 3–4); Red Hat: +6.8% τ na natywnym MTP.
- Przeciw: raport 11 pokazał, że głowica Qwena jest blisko swojego optimum na danych z myśleniem; jedna warstwa ma ograniczoną pojemność; do +25% potrzeba warunkowej ~0.70 na każdej pozycji (dziś 0.655/0.50/0.41/0.38).

### 5.2 Dane (licencje)

| źródło | licencja | użycie |
|---|---|---|
| WildChat-1M (allenai @7d6490e4) | ODC-BY-1.0 | prompty PL/EN z intencją pisania (filtr: napisz/opisz/opowiadanie/list/esej/felieton, write a story/essay/letter…), toxic=False, redacted=False |
| oasst2 (OpenAssistant @179dd21f) | Apache-2.0 | prompty PL/EN |
| aya_dataset (CohereLabs @f9ea0458) | Apache-2.0 | prompty PL |
| PLLuMIC (pelcra) | CC-BY-SA-4.0, gated | prompty PL (wniosek o dostęp na HF; w 11 nieużyte) |
| Wikipedia PL (tytuły haseł jako tematy) | CC BY-SA 4.0 | nasiona tematów do szablonów „gatunek × temat × forma × długość” |
| Wolne Lektury (utwory w domenie publicznej) | domena publiczna (opracowania CC BY-SA 3.0) | prompty „scena / list / opis w stylu…” i krótkie fragmenty do kontynuacji (tylko jako prompt) |
| FineWeb-2 `pol_Latn` | ODC-By-1.0 | krótkie fragmenty jako prompty „rozwiń / przepisz” |
| **odpowiedzi** | Qwen3.8-27B: Apache-2.0 | generuje nasz model; datasetów nie publikujemy, tylko głowicę |

- Skład: 70% bez myślenia, 30% z myśleniem (effort low), żeby nie stracić czatu. Języki: PL 55%, EN 35%, kod/technika 10% jako zabezpieczenie przed regresją.
- Długość: do 1024 tokenów. Sampler produkcyjny: T=1, top-k 20, top-p 0.95, min-p 0.05.
- Wolumen: pilot 5 M tokenów odpowiedzi, pełny przebieg 20 M.
- Tylko on-policy: odpowiedzi z datasetów (off-policy) szkodziły w raporcie 11.
- Held-out: 8 promptów E0 (nigdy w treningu) i 100 nowych promptów prozy PL/EN.

### 5.3 Pipeline i hiperparametry

1. **Generacja:** vLLM bf16 na H100/A100 80 GB. Tekst bf16 jest prawie on-policy dla Q4 (KLD UD-Q4_K_XL 0.012). Zapasowo llama.cpp CUDA Q4 z `-np 64 -t 6 -tb 6` (lekcja z 11: domyślne wątki w kontenerze).
2. **Teacher i stany:** `mtp_extract` na naszym Q4 (CUDA, KV q4_0, draft KV q4_0), tylko teacher forcing (h_nextn fp16 + top-32 celu). Paczki po 1 M tokenów (10 GB h), po treningu kasowane.
3. **Trening** (`mtp-train/train.py`, zmiany):
   - trenowalne `blk.64.*` (~0.42 B), zamrożone embeddingi i 64k wierszy głowicy draftu;
   - łańcuch rekurencyjny K=4 (= produkcyjne n), wagi głębokości β^(k−1) z β = 0.8 (pozycje 2–4 to tu główna luka, w 11 β = 0.65);
   - strata: 0.9·TV(q′_k, p′_k) + 0.1·CE, gdzie p′ to rozkład celu po filtrach samplera, a q′ to rozkład draftu po tych samych filtrach co op `GUMBEL_MAX` (maska filtra stała, softmax różniczkowalny). TV to dokładnie wielkość, którą nagradza sprzężenie i rejection;
   - AdamW lr 2e-5, cosine, 3% warmup, betas (0.9, 0.95), wd 0, clip 1.0, partia 32k tokenów, 2 epoki po 20 M (~1 250 kroków), bf16 autocast z wagami master fp32;
   - ewaluacja co 100 kroków na held-out (lustro, metryka sprzężona n=4), early stop.
4. **Zapis:** `writeback.py` (Q6_K/Q8_0/F32 jak w pliku, weryfikacja bajtów poza `blk.64`).

### 5.4 Protokół ewaluacji

1. **Offline (CPU, ~15 min na głowicę):** `pa_offline.py` na `e0x` (wyjścia E0, ten raport) i na held-out, metryka sprzężona i T=0, per pozycja, per klasa, n=3/4/5.
   - Bramka do GPU: E0 PL **i** EN ≥ +5% tok/krok, czat (`ext_p1` chat) ≥ −0.5%.
2. **Online XTX (kolejka, ≤10 min na ramię):**
   - md5: plain `c4708318` bez zmian (pień); MTP T=0 zapisać jako nową referencję;
   - E0 ABBA seedy 1–8 (`p100_arm.sh` + `prose_sum.py`: t/s, tok/krok, sparowany bootstrap po promptach);
   - spec_sweep T=1 seedy 1–8 i `mvs` T=0.
   - Kryterium wdrożenia: E0 t/s ≥ +5% z CI nad 0, żadna klasa spec_sweep poniżej −1%.

### 5.5 Budżet

| etap | czas | A100 80 GB ($0.73–0.80/h) | H100 ($2.2–3.1/h) |
|---|---|---|---|
| pilot 5 M (generacja + ekstrakcja + trening + offline) | ~4 h A100 / ~2 h H100 | ~$3–4 | ~$5–7 |
| pełny 20 M | generacja 2–4 h, ekstrakcja 2–4 h, trening 2–3 h (2 epoki; train1 szedł 2 980 tok/s na A40) | ~12–16 h → **$10–13** | ~6–8 h → **$15–25** |
| ewaluacja online | XTX, 3 × ≤10 min | $0 | $0 |
| praca | ~1 dzień (pipeline z 11 istnieje: ekstraktor, lustro, trener, zapis) | | |

- **XTX lokalnie:** trening się mieści (głowica + Adam ~10–12 GB). Generacja 20 M tokenów przy ~80–100 t/s to jednak ~60 h zajętej produkcji. Nadaje się tylko do ewaluacji.
- **TPU/TRC (39e):** pasuje wyłącznie do części treningowej (2–3 h). Ekstrakcja teachera na Q4 to llama.cpp, którego na TPU nie ma, a port trenera kosztuje więcej niż 3 h A100. **Nie warto.**
- Limity bezpieczeństwa jak w 11: watchdog kosztu i deadline, samozniszczenie poda.

### 5.6 Pierwszy eksperyment (≤10 min GPU, przed jakimkolwiek wydatkiem)

**train1 online na E0 vs baza: czy lustro przewiduje online deltę na tej klasie?**
- `writeback.py apply` na kopii modelu (CPU, 17 GB dysku; jest 196 GB wolnego), potem ABBA z seedami 1,2 przez `p100_arm.sh` z `MODEL=` kopii (4 ramiona po ~2.3 min).
- Lustro przewiduje PL +2.0%, EN −1.1% tok/krok.
- Jeśli online da ten sam znak i rząd wielkości, offline staje się wiarygodną bramką i iteracje treningu idą bez GPU (CPU 15 min na głowicę). Jeśli nie, przed wydaniem pieniędzy trzeba naprawić zgodność lustra (IQ4_XS, KV draftu).
- Następny krok: pilot 5 M w chmurze ($3–7), z bramką offline z §5.4.

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| eksperymenty | 2026-10-20 akceptacja MTP na prozie E0 per pozycja | Online (log `LLAMA_SPEC_LOOKUP_LOG`, 64 + 8 żądań): T=1 warunkowa 0.655/0.503/0.407/0.382 (PL 0.635/0.461/0.350/0.296), 2.175 tok/krok; T=0 2.265. Wyrocznia greedy 0.77 na każdej pozycji (lustro). Pęknięcia PL: słowo 58%, końcówka 23%, OOV 14%, interpunkcja 4%; OOV 2.1× częściej. Lookup 0/13 187 kroków (raport 40 §2) |
| lekcje | Proza bez myślenia to najsłabsza klasa głowicy MTP | Na odpowiedziach po myśleniu warunkowa 0.71/0.59/0.53/0.53, bez myślenia 0.67/0.52/0.44/0.40 (lustro). Cel jest płaski tylko trochę bardziej (p′max 0.77 vs 0.81). Liczby z danych „reasoning low” (raport 11, 24s) zawyżają prozę czatu o ~10% (raport 40 §2.1) |
| eksperymenty | Głowica train1 (raport 11) w metryce sprzężonej | E0 bez myślenia: +0.4% (PL +2.0%, EN −1.1%), zysk na pozycjach 3–4; proza z myśleniem +0.8%. Sprzężenie nie ukrywało zysku (raport 40 §3.1) |
| metody | Lustro MTP na wyjściach serwera (protokół ewaluacji głowicy) | `pa_extract_prep.py` (prompty przez BPE z GGUF, odpowiedzi z logu per krok) → `mtp_extract_topka` (1.7 min GPU na 18k tokenów) → `ext_head.py --head` → `pa_offline.py`; T=0 PL 2.132 vs serwer 2.133 (raport 40 §1) |
| wyniki-negatywne | Lookup i temperatura jako dźwignie prozy | Lookup: 0 tokenów na prozie. T 0.7 vs 1.0: +1% tok/krok (sampler top-k 20/top-p 0.95/min-p 0.05 już tnie). Sprzężenie Gumbel jest 3% od maksymalnego sprzężenia tej głowicy (raport 40 §2.3–2.4) |
