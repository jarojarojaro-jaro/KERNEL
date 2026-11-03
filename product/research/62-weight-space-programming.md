# 62 — Weight-Space Programming i Neuron Tuning: czy da się „naprawić” nasze modele edycją kilku wag

Data: 2026-11-03. Research tylko na CPU, GPU nietknięte. Przeczytane źródła: blog MIT
([Takehi i in., 2026-11-02](https://rikiyat.github.io/blog/weight-space-programming/)), pełne logi eksperymentu 8
([RikiyaT/lm_understand-logs](https://github.com/RikiyaT/lm_understand-logs), `exp8_math/`: README, `final_answer.md`,
`work_notes/notes.md`, `edit/manifest.json`, `eval/*/merged.json`, `eval/RESULTS_excerpt.md`), niezależna replikacja
z kontrolami ([openwsp/openwsp](https://github.com/openwsp/openwsp)), audyt logów
([Honesty.Tools](https://www.honesty.tools/blog/weight-edits-and-the-evidence-for-understanding/)), wątek
[HN 50341174](https://news.ycombinator.com/item?id=50341174), Neuron Tuning (kod
[changjonathanc/neuron-tuning](https://github.com/changjonathanc/neuron-tuning) `make_edit.py` i
[wpis](https://jonathanc.net/blog/neuron-tuning)), karta [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/README.md)
oraz nasze źródła llama.cpp (`~/llama.cpp`, b356fa262) i wcześniejsze raporty. Nie pobierałem wag ani zbiorów danych.
Eksperymentów CPU nie robiłem: 27B na 4 wątkach nie wygeneruje sensownej liczby śladów myślenia, a strukturę edycji
(rank-1) widać wprost ze wzoru w logach.

## Werdykt

- **To nie jest przełom w optymalizacji modeli, tylko dobrze udokumentowana abliteracja / steering, którą tym razem
  znalazł agent.** Edycja Qwen3.5-0.8B to wpisany w wagi kierunek „pętli”, policzony z różnicy aktywacji między
  pętlą a produktywnym myśleniem: rank-1, 2 macierze `down_proj`, 64 kolumny w każdej
  ([notes.md:6-8](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/work_notes/notes.md)).
  To ta sama rodzina co [Arditi i in. 2024](https://arxiv.org/abs/2406.11717), czyli dokładnie to, czym są nasze modele
  Uncensored ([wiki](../../wiki/modele/uncensored-ablacja-kierunku.md)).
- **Wynik 7.9% → 48.1% jest prawdziwy, ale baseline jest zepsuty i większość zysku daje zwykła zmiana ustawień.**
  W tym samym pipeline'ie bazowy model **z wyłączonym myśleniem** robi **46.8%** MATH-500, edytowany 50.6%, a
  mechaniczny kierunek „średnia(pętla) − średnia(koniec)” bez żadnego LLM-a 46.0%
  ([OpenWSP, tabela kontroli](https://github.com/openwsp/openwsp#results)). Na modelu, który się nie zapętla
  (Gemma 3 270M), Astra nie poprawiła nic (6.8 → 7.0–7.7%)
  ([RESULTS_excerpt.md:56-66](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/eval/RESULTS_excerpt.md)).
- **Nowe naprawdę jest jedno: ogólny LLM bez specjalnego harnessu sam dochodzi do tego przepisu.** Robi to jednak
  niestabilnie (trzy przebiegi dały 12.3 / 14.1 / 48.1%) i drogo (20.3 h, 158 tur, 50 przebiegów po ≤512 generacji
  po 32k tokenów) ([README:50-55](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/README.md)).
- **Neuron Tuning to nie „bez gradientów”.** To fine-tuning Adamem kilku kolumn `down_proj` (8 neuronów ≈ 12k liczb)
  wybranych tak, żeby odpalały tylko w docelowym kontekście (`make_edit.py:37-44, 501-533`). Daje 3–19× mniejszy wpływ
  na niezwiązany tekst niż LoRA tej samej siły. To dobre narzędzie do **wąskich zmian polityki i stylu**, a nie do
  zdolności. Cel treningu to model z promptem systemowym, więc sufitem jest to, co już daje prompt.
- **Dla nas:** obie techniki przenoszą się na GGUF **bez BF16 i bez re-kwantyzacji**, bo każda z tych edycji to
  dokładnie adapter LoRA (rank-1 albo rank-K, §4.1), a llama.cpp ładuje LoRA w runtime (`--lora`, skala per żądanie
  w serwerze). Realne cele: pętle i przeciągnięte myślenie na Qwen3.8 (o ile zostaną po poprawieniu samplera),
  „pokrętło odmowy” zamiast osobnych plików Uncensored i wąskie nadmierne odmowy. Odpadają: wiedza, rozumowanie,
  jakość polszczyzny ponad poziom promptu.
- **Kolejność:** (1) pomiar pętli z rekomendowanym samplerem, ~$0–5; (2) pokrętło odmowy jako LoRA z kierunków, które
  już mamy, ~$0–5; (3) mechaniczny kierunek pętli jako LoRA rank-1 na GGUF, ~$5–15, tylko jeśli (1) zostawi ≥ 5%
  zapętleń. Agentowe WSP z frontier modelem: nie, setki dolarów i niepowtarzalność.

## 1. Co dokładnie zrobiono z Qwen3.5-0.8B

### 1.1 Edycja

| przebieg | budżet | co zmienione | operacja | MATH-500 | ucięte przy 32k |
|---|---|---|---|---|---|
| bazowy | — | — | — | 7.9 | 93.0% |
| p10c | 10 przebiegów | 30 macierzy wyjściowych (atencja i MLP) w warstwach 8–22 | `W' = W − 1.5·u(uᵀW)`, rzut kierunku „powtarzania” | 12.3 | 87.2% |
| p25c | 25 | głowa atencji 7 w warstwie 15 | wyzerowanie jej 256 kolumn wyjściowych | 14.1 | 86.4% |
| **p50c** | 50 | `layers.15.mlp.down_proj`, `layers.19.mlp.down_proj` [1024×3584], po 64 kolumny | `W = W0 − 6·outer(u, mask64·(uᵀW0))` | **48.1** | 33.1% |

Źródła: [README:50-55,66-72](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/README.md),
[notes.md:1-24](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/work_notes/notes.md),
[manifest.json](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/edit/manifest.json).

- **Typ operacji.** Delta p50c to iloczyn zewnętrzny `u·(mask⊙uᵀW0)`, czyli **macierz rank-1 na warstwę**. Nie jest
  to skalowanie, zerowanie ani bias. Przy α = 6 składowa wzdłuż `u` w 64 kolumnach nie znika, tylko zmienia znak i
  rośnie 5× (1 − 6 = −5). To więc **odwrócony steering**, a nie czysta ablacja. Względna zmiana macierzy wynosi
  10.6% i 8.1% ([manifest](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/edit/manifest.json)).
  Dla porównania nasza abliteracja Qwena zmienia writery o 1.3–1.6% normy ([wiki](../../wiki/modele/uncensored-ablacja-kierunku.md)).
- **Skąd `u`.** Z czterech dopasowanych par kontekstów „produktywny vs powtarzający się”, na wyjściach rezydualnych
  warstw 16/20. Kolumny to 64 neurony MLP, które najmocniej piszą wzdłuż `u`
  ([notes.md:7-8](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/work_notes/notes.md)).
  To różnica średnich z CAA/abliteracji, policzona na parach kontekstów.
- **Jak użyto 50 przebiegów** ([explanations.md](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/explanations.md),
  [README:23-26](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/README.md)). Przebieg to albo
  generacja do 512 zadań (z trybem sparowanym oryginał/edycja po 256), albo teacher-forced odczyt do 1024 tekstów:
  logproby, stany ukryte, aktywacje MLP, atencja.
  1. Diagnoza: 85/96 odpowiedzi doszło do limitu, a ~95% ogonów to zduplikowane frazy.
  2. Ablacja pojedynczego neuronu 19:11: +6.25 pp ± 4.35, niekonkluzywne.
  3. Rzut kierunku z MLP warstwy 19.
  4. Testy dawki α = 1/2/3/4 na logprobach par: repetytywne −0.024/−0.049/−0.104 nat/tok, produktywne prawie bez zmian.
  5. Izolacja warstw 15 i 19, odrzucenie wariantów z głowami atencji.
  6. Kontrola losowym kierunkiem o tej samej normie: +1.56 pp ± 3.52.
  7. Zawężenie do top-64 kolumn i potwierdzenie na 1152 odłożonych zadaniach treningowych: 10.6% → 60.4%,
     579 uratowanych, 5 regresji ([notes.md:15-58](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/work_notes/notes.md)).
  Metodologicznie to porządna robota interpretacyjna (dawka, kontrola losowa, held-out), tylko nie nowa.
- **Zaplecze:** 20.3 h, 158 tur, 80 uruchomień Pythona, 4 restarty konwersacji, `gpt-6-astra` z reasoning `max`
  ([README:50-59](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/README.md)). Pełny przebieg
  generacji trwał do ~30 min.

### 1.2 Mechanizm rozumowania czy zachowanie pętli/EOS?

Raczej to drugie. Edycja tłumi tryb degeneracji, nie uczy matematyki:

- 576 z 579 „uratowanych” zadań było wcześniej uciętych na limicie, a trafność na zadaniach, które oryginał
  kończył, się nie zmieniła ([final_answer.md:17](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/final_answer.md)).
  Mediana długości poprawnych odpowiedzi **wzrosła** z 5 311 do 9 172 tokenów, więc nie jest to „wcześniejszy EOS”
  ([notes.md:88,102](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/runs/p50c/work_notes/notes.md)).
- Sami autorzy: „Fixing loops… is not the same as making a model better at math”. Na niezapętlającej się Gemmie 3 270M
  Astra nie znalazła nic ([blog, Additional experiment](https://rikiyat.github.io/blog/weight-space-programming/)).
- Pętle nie zniknęły. Po edycji 33% odpowiedzi MATH-500 nadal dochodzi do limitu, a 20 z 400 sprawdzonych odpowiedzi
  kończy się ponad 100k znaków białych znaków, wszystkie błędne
  ([Honesty.Tools, Finding 3](https://www.honesty.tools/blog/weight-edits-and-the-evidence-for-understanding/)).

### 1.3 Baseline 7.9%: ustawienia i uczciwe porównanie

- **Ustawienia autorów:** myślenie włączone, T 0.6, top-p 0.95, top-k 20, presence 1.5, 32 768 tokenów
  ([README:38-46](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/README.md)). Karta Qwena zaleca dla
  **myślenia w zadaniach tekstowych T = 1.0** (presence 1.5). T 0.6 jest zalecane dla VL i precyzyjnego kodu, ale
  wtedy z presence 0.0 ([karta, l. 709-712](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/README.md)). Tabela
  benchmarków językowych Qwena była liczona przy T = 1.0 (ta sama karta, przypis pod tabelą „Language”). Ustawienia
  autorów to więc hybryda (T z VL, presence z tekstu), a nie „rekomendowane”. Karta ostrzega też, że 0.8B pętli się
  **nawet przy rekomendowanych** ustawieniach ([l. 860](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/README.md#L856)).
- **Skala zepsucia baseline:** 93% uciętych na MATH-500, 87% na GSM8K, 75% na IFEval
  ([eval/unedited/merged.json](https://github.com/RikiyaT/lm_understand-logs/blob/main/exp8_math/eval/unedited/merged.json)).
  Qwen podaje dla 0.8B IFEval 44.0 (myślenie) i 52.1 (bez myślenia), a autorzy zmierzyli 21.0. MMLU-Pro, gdzie pętli
  jest mniej (29% uciętych), wyszło 40.3 wobec 42.3 u Qwena ([karta](https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/README.md)).
- **Kontrole OpenWSP** (ten sam pipeline vLLM, MATH-500, 1 próbka na zadanie, H100) ([tabela](https://github.com/openwsp/openwsp#results),
  [protokół](https://github.com/openwsp/openwsp/blob/main/docs/TASK.md)):

| ramię (MATH-500) | baseline | teraz | przyrost | ucięte | śr. tokeny |
|---|---|---|---|---|---|
| bazowy, myślenie, ustawienia autorów | — | 7.2% | — | 93.2% | 30 959 |
| bazowy, **bez myślenia**, sampler z karty | 7.2% | **46.8%** | **+550%** | 0.6% | 9 218 |
| bazowy + `repetition_penalty` 1.1 | 7.2% | 23.8% | +231% | 75.6% | 27 114 |
| kierunek mechaniczny (różnica średnich pętla/koniec, kolumny p50c, α 6) | 7.2% | **46.0%** | +539% | 45.2% | 23 050 |
| **edycja Astry p50c** | 7.2% | **50.6%** | +603% | 31.0% | 21 326 |

- **Odczyt:**
  1. Najtańsza poprawka („wyłącz myślenie”) daje 92% wyniku edycji przy 43% tokenów. Ten sam wynik (46%) podał
     komentator na HN ([erratum_hunter](https://news.ycombinator.com/item?id=50341174)).
  2. Agent dokłada ponad przepis Arditiego **+4.6 pp** (SE niesparowane ≈ 3.2 pp, czyli w granicy szumu).
  3. Kontrola mechaniczna pożycza od Astry kolumny i α i liczy kierunek na odpowiedziach z benchmarku. To górna
     granica przepisu bez agenta, nie próba odłożona ([method.json](https://github.com/openwsp/openwsp/blob/main/replications/exp8/results/control2_mechanical/method.json)).
  4. Uczciwe porównanie powinno zawierać ramię „bazowy + najlepszy sampler / tryb”. Autorzy go nie mają.
- **Replikacje:** wynik edycji się odtwarza: 51.0% w re-runie HF na H200
  ([karta modelu](https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming)) i 50.6% w OpenWSP. Wszystkie
  64 222 etykiety i hashe tensorów zgadzają się z publikacją ([Honesty.Tools](https://www.honesty.tools/blog/weight-edits-and-the-evidence-for-understanding/)).
  Pełnej replikacji **procesu** (agent od zera) jeszcze nie ma: próba API OpenWSP stanęła na 4/50 przebiegów po $78
  za edytora ([OpenWSP, Cost](https://github.com/openwsp/openwsp#cost-and-time)).
- **Krytyka:**
  - „basically a steering vector, a very established technique” oraz porównanie z ROME
    ([HN, yurimo](https://news.ycombinator.com/item?id=50341174));
  - test „która gra” to w praktyce wielokrotny wybór z podanymi etykietami kanałów
    ([Wegner na X](https://x.com/GOFIntelligence/status/2117396678919569490));
  - niezależna próba: Claude dobrze **czyta** sieci 10k wag, ale jego edycje **pogarszały** klasyfikator
    ([HN, fancyfredbot](https://news.ycombinator.com/item?id=50341174)).
- **Pozostałe eksperymenty bloga** (Breakout od zera, auto PPO, Go) dotyczą sieci 17k–1.5M wag z czytelną strukturą
  wejścia. Dla naszych modeli nie mają przełożenia.

## 2. Neuron Tuning: jak działa (z kodu)

`make_edit.py` w repo [changjonathanc/neuron-tuning](https://github.com/changjonathanc/neuron-tuning):

1. **Cel (`teacher_items`, l. 133-146):** zachłanne odpowiedzi modelu **z** promptem systemowym („mów potocznie”),
   do 256 tokenów (`--max-new-tokens`, l. 821). Strata to KL(teacher ‖ model bez promptu) na tokenach odpowiedzi
   (`item_loss`, l. 151-182). To destylacja kontekstu. Są też tryby `--append` (dopisek do odpowiedzi) i `--pairs`
   (jawne pary, cross-entropy).
2. **Selekcja (`select_neurons`, l. 307-339 i docstring l. 37-44):**
   - c = średnie |aktywacji| wejścia `down_proj` na celu, g = to samo na tle (7 domen);
   - kwalifikuje się neuron z c w top 10% swojej warstwy i g/c ≤ 0.2;
   - ranking według ‖∂L/∂W_j‖ / g_j, gradient liczony przez adapter z gradient checkpointingiem;
   - zostaje top-K (domyślnie 8).
3. **Edycja:** trenowane są tylko kolumny `down_proj` tych K neuronów, Adamem: 400 kroków, batch 8, lr 3e-2
   (l. 501-533, 807-820). Patch to `{warstwa: (neurony, delta)}` w `.safetensors` (~52 KB). Można go zapiec w wagach
   (`bake`, l. 392-397) albo podpiąć jako hook `out + x[neurony] @ Dᵀ` (l. 372-388).
4. **Ewaluacja:** siła edycji to strata na odłożonych pozycjach. „F” to KL(oryginał ‖ edycja) na 256 stałych tekstach
   z 7 domen (`unrelated_change`, l. 403-424), z opcją fp32. Do tego karty neuronów i porównanie z LoRA rank-1 i rank-8.
5. **Koszt:** „about 10 minutes per learning rate” na RTX 3090 dla Gemma-4-E2B ([README](https://github.com/changjonathanc/neuron-tuning#quick-start)).
   Model ładowany w całości w bf16 na GPU, `attn_implementation="eager"`, myślenie wyłączone w szablonie (l. 89-107).

**Wyniki i granice** ([wpis](https://jonathanc.net/blog/neuron-tuning)):

- przy tej samej sile 3–19× mniejsze F niż LoRA; nadmierna odmowa (wartości laboratoryjne) 230–270× mniejsze F, ale
  liczby dawek pojawiają się w większej liczbie odmów (26 vs 9 na 144);
- sąsiednie tematy przeciekają tak samo jak przy LoRA (keigo → chiński/koreański, nowy fakt → inne twierdzenia), chyba
  że neurony wybiera się na starcie odpowiedzi albo dokłada zbiór preservation;
- przetestowane prawie tylko na Gemma-4-E2B; Qwen3.5-4B tylko na jednej edycji i jednym seedzie.

**Skalowanie na 27B (`[INFERENCE]`):**

- Selekcja i trening wymagają backwardu przez cały model, więc potrzebne są wagi HF, nie GGUF. Qwen3.8-27B w BF16 to
  54.66 GB ([16e](16e-kwanty-kld.md#11-referencja-kld-prawdziwe-bf16-nie-q8_0)), a kod robi `model.to("cuda")`
  (l. 101). Potrzeba więc **A100/H100 80 GB**.
- Wariant z bazą 4-bit (bnb) zmieściłby się w 48 GB, ale repo go nie ma. To byłaby nasza zmiana.
- Warstwy GDN w transformers bez kerneli `fla` liczą się wolną ścieżką torch.
- MoE: kod wymaga `mlp.down_proj` w każdej warstwie dekodera (komentarz l. 72-73), więc warstwy eksperckie LFM2.5 i
  Qwen3.6-A3B nie są obsługiwane bez zmian w kodzie.
- Teacher z limitem 256 tokenów nie nadaje się do korekt w śladach myślenia długich na 8–32k tokenów.

## 3. Na tle wcześniejszych prac: co nowe, a co rebrand

| technika | co edytuje | jak znajduje kierunek/miejsce | relacja do WSP / Neuron Tuning |
|---|---|---|---|
| ROME / MEMIT ([2202.05262](https://arxiv.org/abs/2202.05262), [2210.07229](https://arxiv.org/abs/2210.07229)) | rank-1 (MEMIT: rank-k) update MLP `W_out` | causal tracing + rozwiązanie najmniejszych kwadratów | ta sama algebra (rank-1 na `down_proj`); cel to fakty, nie zachowanie |
| ActAdd / CAA / RepE ([2308.10248](https://arxiv.org/abs/2308.10248), [2312.06681](https://arxiv.org/abs/2312.06681), [2310.01405](https://arxiv.org/abs/2310.01405)) | dodanie wektora do strumienia rezydualnego w runtime | różnica średnich aktywacji par kontrastowych | kierunek `u` w p50c liczy się tak samo; WSP wpisuje go w wagi zamiast dodawać |
| Abliteracja ([Arditi 2406.11717](https://arxiv.org/abs/2406.11717), [mlabonne](https://huggingface.co/blog/mlabonne/abliteration)) | `W' = (I − r rᵀ)W` na writerach strumienia | różnica średnich harmful/harmless | **p10c to dokładnie to**; p50c to ten sam wzór na 64 kolumnach z α = 6. Nasze Uncensored to s ≈ 1 (Qwen) i s = 1.75 (LFM) ([wiki](../../wiki/modele/uncensored-ablacja-kierunku.md)) |
| ITI ([2306.03341](https://arxiv.org/abs/2306.03341)) | przesunięcie wyjść wybranych głów atencji | sondy liniowe per głowa | p25c (zerowanie głowy 15.7) to prostszy wariant interwencji na poziomie głowy |
| Repetition neurons ([Hiraoka i Inui, 2410.13497](https://arxiv.org/abs/2410.13497)); [Mahaut i Franzon 2025](https://www.scholar-inbox.com/paper/Mahaut2025ARXIV_Repetitions_are_not_all) | wyłączanie/wzmacnianie neuronów powtarzania | aktywacje na powtarzającym się tekście | „pętla siedzi w kilku neuronach MLP środkowych warstw” było znane; WSP to potwierdza na modelu myślącym |
| ThinkEdit ([2503.22048](https://arxiv.org/abs/2503.22048)), SEAL ([2504.07986](https://arxiv.org/abs/2504.07986)) | ThinkEdit: edycja wag głów atencji, rzut kierunku długości myślenia; SEAL: wektor sterujący w runtime | różnica aktywacji krótkie/długie albo refleksyjne/wykonawcze myśli | **najbliższy precedens dla pętli/myślenia**: steruje długością rozumowania edycją wag albo wektorem, bez treningu |
| Neuron-level FT ([NeFT 2403.11621](https://arxiv.org/abs/2403.11621)), sparse FT ([Ansell 2110.07560](https://arxiv.org/abs/2110.07560)), Transformer-Patcher ([2301.09785](https://arxiv.org/abs/2301.09785)), [„A Few Bad Neurons” 2601.18939](https://arxiv.org/html/2601.18939) | gradientowy trening wybranych neuronów/parametrów | gradienty, atrybucja | Neuron Tuning należy tutaj. Nowość to reguła selekcji (selektywność g/c) i pomiar lokalności F |
| Task arithmetic / model diff ([Ilharco 2212.04089](https://arxiv.org/abs/2212.04089)) | dodawanie różnic wag modeli | odejmowanie checkpointów | dla nas: Swift − Qwen to gotowa różnica „mniej przeciągniętego myślenia” (§4.3) |

**Ocena nowości:**

- WSP: algebra edycji i sposób znajdowania kierunku są znane. Nowe są trzy rzeczy: (a) ogólny frontier LLM sam
  prowadzi cały proces interpretacji i edycji pod budżet przebiegów; (b) czytanie małych sieci z surowych wag; (c)
  pełne logi z diffem bit-po-bicie.
- Neuron Tuning: inkrementalny i dobrze zmierzony. Najcenniejszy wynik to ρ = 0.90 między „off-target write” a
  zmianą na niezwiązanym tekście, który daje praktyczny filtr przed treningiem.

## 4. Czy to przenosi się na nasze modele

### 4.1 Kluczowy fakt techniczny: każda z tych edycji to LoRA, więc GGUF wystarczy

- **p50c / abliteracja:** `ΔW = −α·u·(m⊙uᵀW0)` jest rank-1, więc LoRA ma `B = −α·u` (n_embd×1) i `A = m⊙uᵀW0` (1×n_ff).
- **Neuron Tuning:** `ΔW = D·S`, gdzie S (K×n_ff) to one-hot wybranych neuronów, więc to LoRA rank-K z `A = S`, `B = D`.
- **llama.cpp:**
  - LoRA działa na każdym matmulu przez `build_lora_mm`, także na `ffn_down` (`~/llama.cpp/src/llama-graph.cpp:1871`)
    i na ekspertach MoE (`build_lora_mm_id`, l. 2249);
  - serwer ma `--lora`, `--lora-init-without-apply` i pole `lora: [{id, scale}]` **per żądanie**. Żądania z różnymi
    LoRA nie są batchowane razem ([README serwera, l. 605](https://github.com/ggml-org/llama.cpp/tree/master/tools/server));
  - `build_cvec` (control vector) jest w `qwen35.cpp`, `qwen35moe.cpp`, `gemma4.cpp` i `lfm2.cpp:279`.
- **Wniosek:** dla edycji typu „kierunek” wystarczą zdekwantyzowane tensory z GGUF, które i tak serwujemy. Pełne BF16
  (54.66 GB) nie jest potrzebne. Gradienty (Neuron Tuning) potrzebują już modelu HF.
- **`llama-export-lora` nie nadaje się do wypiekania w kwant:** wynik zawsze jest F16
  (`~/llama.cpp/tools/export-lora/export-lora.cpp:179-191`), więc dla 27B trzeba by zrobić ~54 GB F16 i
  re-kwantyzować drugi raz.
- **Lepsza droga przy edycji 2–8 tensorów: „splice”.** Zdekwantyzować tylko edytowane `ffn_down`, dodać deltę,
  skwantyzować z powrotem do tego samego typu i podmienić w pliku (gguf-py). Reszta pliku zostaje bit w bit, kernele
  te same, zero kosztu runtime `[INFERENCE]`.
- **Control vector** (`--control-vector`, generator `llama-cvector-generator` liczy mean/PCA wprost na GGUF) jest
  tylko addytywny i bezwarunkowy. Działa na każdym tokenie, więc jest mniej lokalny niż edycja kolumn
  ([README cvector](https://github.com/ggml-org/llama.cpp/tree/master/tools/cvector-generator)). Nadaje się na
  szybki test kierunku, nie do produktu.

### 4.2 Tabela wykonalności

Legenda: ✅ realne, ⚠️ możliwe z zastrzeżeniami, ❌ nie tą drogą.

| cel | Qwen3.8-27B (Main) | Qwen3.8-27B Uncensored | LFM2.5-24B-A2B (+Unc) | Qwen3.6-35B-A3B | Gemma 4 (26B-A4B / 31B / 12B) |
|---|---|---|---|---|---|
| pętle i przeciągnięte myślenie | ⚠️ realne technicznie (kierunek → LoRA rank-1 na `ffn_down`), ale nasz poziom zapętleń jest niski: 3–5/40 ucięć przy 8192 w zadaniach ([16e §1.5](16e-kwanty-kld.md)). Najpierw sampler | ⚠️ jak Main; uwaga: abliteracja „lekko pogarsza stabilność” ([źródło](../../sources/qwen3.8-27b.md)) | ❌/⚠️ LFM nie ma trybów effort ani długiego myślenia; pętle w odpowiedzi łatwiej leczyć samplerem (`repeat_penalty` 1.05 z karty) | ⚠️ jak Qwen; kierunek przez writery (`ffn_down_exps` przez `lora_mm_id`, `ffn_down_shexp`) | ⚠️ możliwe; najpierw zmierzyć, czy w ogóle się pętli |
| resztki nadmiernej odmowy | ✅ wąsko (Neuron Tuning) albo **częściowa skala kierunku r** (już policzony: `21e-skrypty/r_qwen.npy`) | ✅ odwrotnie: „pokrętło” s∈[0,1] między Main a Unc | ✅ `r_lfm.npy` per warstwa 14–39, s = 1.75 | ⚠️ trzeba policzyć kierunek (Arditi: jeden przebieg + prompty) | ✅ Neuron Tuning jest natywnie pod Gemmę 4 (Gemma-4-E2B w repo) |
| polszczyzna (jakość) | ❌ jako zdolność: edycja nie doda wiedzy językowej. ⚠️ jako styl/rejestr: Neuron Tuning z promptem PL jako teacherem, sufit = prompt | jak Main | ❌ tak samo | ❌ tak samo | ⚠️ tak samo |
| format tool-call | ❌ lepiej gramatyka GBNF / JSON schema w llama.cpp (deterministycznie); edycja tylko gdy błąd jest „nawykiem” poza gramatyką | jak Main | jak Main | jak Main | jak Main |
| rozwlekłość | ⚠️ najpierw `--reasoning-effort low/medium` (mamy w `run-llm.sh:42-45`) i prompt; edycja tylko gdy prompt nie działa | jak Main | ⚠️ prompt | ⚠️ | ⚠️ |
| wiedza, matematyka, rozumowanie | ❌ (Gemma 270M: 0 zysku; [blog](https://rikiyat.github.io/blog/weight-space-programming/)) | ❌ | ❌ | ❌ | ❌ |
| przypadki szczególne | 48 warstw GDN + 16 atencji; edytować tylko writery (`ffn_down`, `ssm_out`, `attn_output`), nie wejścia GDN (α/β, qkv), które zmieniają rekurencję stanu `[INFERENCE]` | Orca rzutowała też blok MTP (warstwy 0–64) ([wiki](../../wiki/modele/uncensored-ablacja-kierunku.md)) | router MoE: **nie ruszać** (zmienia wybór ekspertów i balans); kierunek na wyjściu writerów jest agnostyczny co do eksperta | jak LFM; Neuron Tuning nie obsługuje warstw eksperckich bez zmian w kodzie | 26B-A4B ma gęste MLP obok MoE (`gemma4.cpp:272-324`), więc Neuron Tuning może celować w część gęstą `[INFERENCE]` |

### 4.3 Ryzyka

1. **MTP.** Edycja trunku zmienia rozkład docelowy (krótsze myślenie, mniej powtórek, które MTP łatwo trafia) i
   przesuwa `h_nextn`, z którego czyta głowica. Dobry precedens: Swift (RL fine-tune trunku Qwen3.8 z **nieruszoną**
   głowicą MTP) ma tę samą akceptację co ISTA, 0.55 vs 0.55 ([16e §1.4](16e-kwanty-kld.md)). Przy edycji 2 tensorów
   spodziewam się zmiany akceptacji o ≤ 1–2 pp `[SZACUNEK]`. Pętle są jednak „łatwe” dla MTP, więc t/s może spaść,
   choć czas do odpowiedzi skróci się przez mniej tokenów. Mierzyć **czas do odpowiedzi**, nie tylko t/s.
2. **Koszt runtime LoRA.** Rank-1 na 2 warstwach to ~6 dodatkowych węzłów grafu, pomijalne. Pokrętło odmowy na ~131
   writerach Qwena (rzutowanie każdego writera, wiki) to ~390 małych kerneli na token. Przy ~2 µs podłogi pakietu na
   XTX ([21b](21b-gpu-perf-zasoby.md)) daje to **~3–8% t/s** `[SZACUNEK]`. Do tego niewiadoma: czy nasze fuzje
   topka (PM4 replay, fuzje norm, łańcuch MTP) przechodzą z LoRA w grafie. Fallback: splice albo op „projection
   vector” z [przelaczanie-main-uncensored](../../wiki/produkt/przelaczanie-main-uncensored.md).
3. **Kwantyzacja.** Delta p50c to 8–11% normy macierzy, ponad szumem Q4, który między plikami wynosi 3–11%
   ([wiki](../../wiki/modele/uncensored-ablacja-kierunku.md)). Delta abliteracji (1.3–1.6%) jest poniżej szumu
   kwantu. W splice'ie liczyć deltę względem **zdekwantyzowanego** tensora, który serwujemy, a nie BF16.
4. **KLD / skutki uboczne.** Edycja p50c pogorszyła 84/1000 pytań MMLU-Pro i 35/198 GPQA, mimo że średnie wzrosły
   ([Honesty.Tools, Finding 1](https://www.honesty.tools/blog/weight-edits-and-the-evidence-for-understanding/)).
   Bramka: KLD na wiki, PL prozie i kodzie (harness z [16e](16e-kwanty-kld.md)) ≤ 2× podłoga Q8 (0.0038/0.0006)
   na tekście bez myślenia.
5. **Licencje.** Kierunek z diffu Swift − Qwen to pochodna wag Swift (OL 1.0, < $1M przychodu,
   [15e §2.3](15e-kwantyzacja-nowa.md)), więc do produktu tylko po decyzji. Kierunki z Orca (Apache 2.0) są czyste.
   Kierunki AtomicChat (licencja `lfm1.0`) to otwarte pytanie już opisane w wiki.

## 5. Praktyczny pipeline u nas

### 5.1 Narzędzia

| krok | narzędzie | wymaga BF16? | gdzie |
|---|---|---|---|
| generacja śladów + etykieta pętla/koniec (cut + udział zduplikowanych 8-gramów w ogonie ≥ 0.5, jak [OpenWSP](https://github.com/openwsp/openwsp/blob/main/replications/exp8/results/control2_mechanical/method.json)) | `llama-server` (topka) / llama.cpp CUDA | nie | XTX (gdy wolny) albo Vast 3090/4090 |
| aktywacje na parach „produktywne vs pętla” | `llama-cvector-generator --method mean` (pliki pozytywne/negatywne) albo hook `cb_eval` (jak `llama-eval-callback`) | nie | j.w. |
| budowa delty rank-1 (top-64 kolumny według \|uᵀW_j\|) | gguf-py + numpy, zdekwantyzowane `ffn_down` 2 warstw (5120×17408) | nie | CPU, sekundy |
| zapis jako adapter | GGUF LoRA (`adapter.type=lora`, tensory `.lora_a`/`.lora_b`, F32) | nie | CPU |
| alternatywnie splice do pliku | gguf-py: requant tylko edytowanych tensorów (Q4_K/Q5_K/Q6_K/IQ4_XS zgodnie z UD) | nie | CPU |
| Neuron Tuning (styl, wąska odmowa) | `make_edit.py` (+ eksport patcha jako LoRA rank-K) | **tak** (HF bf16, 54.66 GB) | Vast A100/H100 80 GB |
| ewaluacja | MATH-500 (podzbiór), IFEval, nasze 20 zadań × 2 seedy ([16e](16e-kwanty-kld.md)), zestaw pętli, KLD, `spec_sweep` | nie | Vast (przepustowość) + XTX (t/s, akceptacja MTP) |

### 5.2 Koszt (Vast, ceny z [10-post-training](10-post-training.md): A100 80 GB $0.73–0.80/h, A6000 48 GB $0.40/h, H100 $1.73–3.07/h)

- **Ewaluacja jednego ramienia** (MATH-500×200, IFEval 541, PL 40, zestaw pętli 100; myślenie do 16–32k):
  - objętość ≈ 5 M tokenów `[SZACUNEK]`;
  - XTX pojedynczy strumień ~100 t/s: ~14 h, nierealne przy jednym serwerze dla użytkownika;
  - llama.cpp CUDA na A100 z `-np 16`, przyjmując 400–800 t/s łącznie `[SZACUNEK]`: 2–3.5 h ≈ **$2–3 / ramię**.
- **Mechaniczny kierunek pętli (E2), razem: ~$5–15.** Generacja i etykiety ~1 h, aktywacje ~0.5 h, budowa delty na
  CPU, sweep α∈{1,2,4,6} × 2 pary warstw.
- **Neuron Tuning na 27B (E4):** A100 80 GB, ~1–3 h na zachowanie (selekcja + 2 lr + F) `[SZACUNEK z 10 min/lr na 3090
  dla 2B]` ≈ **$2–5 / zachowanie** plus pobranie 55 GB na instancji.
- **Agentowe WSP:**
  - editor: OpenWSP zapłacił $78 za 26 tur ([costs](https://github.com/openwsp/openwsp#cost-and-time)), więc 158 tur
    to ≥ ~$475 `[INFERENCE: liniowo; kontekst rośnie]`;
  - GPU: 50 przebiegów × ≤ 512 generacji × do 32k tokenów na 27B to setki GPU-h;
  - **nieopłacalne.**

### 5.3 Projekt A/B (format „baseline → teraz → przyrost %”)

Te same prompty i seedy, ≥ 2 próbki na zadanie, porównania sparowane. Cztery ramiona, bo kluczowe porównanie to
**A3 vs A1**, którego autorzy WSP nie zrobili:

| ramię | wagi | sampler |
|---|---|---|
| A0 | bazowe | obecny w Enigmie (do odczytania z aplikacji; serwer go nie wymusza, `run-llm.sh:109-110`) |
| A1 | bazowe | rekomendowany Qwena dla myślenia (T 1.0, top-p 0.95, top-k 20, presence 1.5) |
| A2 | + edycja | jak A0 |
| A3 | + edycja | jak A1 |

| metryka | baseline (A1) | teraz (A3) | przyrost % | bramka |
|---|---|---|---|---|
| zapętlenia (ucięte + duplikat ogona) | | | | ≥ −50% względnie |
| MATH-500 (200) | | | | ≥ 0 pp (CI sparowane) |
| IFEval strict | | | | ≥ 0 pp |
| PL 20 zadań × 2 seedy, pass + LanguageTool | | | | bez spadku |
| tokeny/odpowiedź: mediana i średnia | | | | mediana ±10%, średnia ↓ |
| czas do odpowiedzi (XTX, MTP) | | | | ↓ |
| t/s i akceptacja MTP (`spec_sweep`, ABBA) | | | | t/s ≥ −3% |
| KLD vs bazowy: wiki / PL proza / kod | | | | ≤ 2× podłoga Q8 |

## 6. Ranking eksperymentów (wartość oczekiwana / koszt)

| # | eksperyment | koszt | szansa na sukces | wartość, jeśli wyjdzie | uwagi |
|---|---|---|---|---|---|
| **1** | **E1: pomiar pętli na Qwen3.8 Q4: A0 vs A1 (+ `--reasoning-effort`)** | $0–5, 0.5 dnia | wysoka (to pomiar) | decyduje o wszystkim dalej; może sam zamknąć temat pętli (na Qwen3.8-Flash-Next presence 1.5 usunęło pętle w rozumowaniu, choć nie w długim ciele odpowiedzi, [Whallm #6](https://github.com/yanun0323/Whallm/issues/6)) | jedyny krok, który u autorów WSP by „unieważnił” połowę wyniku |
| **2** | **E3: pokrętło odmowy jako LoRA rank-1 z `r_qwen.npy` / `r_lfm.npy`**, s∈{0.25, 0.5, 0.75, 1.0}, skala per żądanie | $0–5 + ewaluacja odmów (~$3) | średnio-wysoka: kierunki i skale już znane ([wiki](../../wiki/modele/uncensored-ablacja-kierunku.md)) | jeden plik zamiast dwóch (−15.66 GiB Qwen, −16.10 GiB LFM), regulacja resztek nadmiernej odmowy, brak przeładowania przy przełączeniu | ryzyko: ~3–8% t/s przez ~131 adapterów i zgodność z fuzjami topka; fallback: op projekcji z wiki |
| **3** | **E2: mechaniczny kierunek pętli → LoRA rank-1 / splice na 2 warstwach `ffn_down`** (przepis Arditiego / control2) | $5–15, 1–2 dni | średnia (na 0.8B działało: 46.0%) | −10…−30% tokenów na zadaniach z pętlą `[SZACUNEK; Swift: −19…−32%]` | **tylko jeśli E1 zostawi ≥ 5% zapętleń**; warstwy wybrać sweepem po środku sieci (15/19 z 24 w 0.8B ≈ 40/50 z 64 `[INFERENCE]`) |
| 4 | E4: Neuron Tuning wąskiej nadmiernej odmowy / rejestru PL na Gemma 4 (natywnie) lub Qwen3.8 (A100) | $5–20 | średnia | mała: sufit = prompt systemowy | sensowne, gdy prompt systemowy użytkownika nadpisuje nasz |
| 5 | E5: low-rank diff Swift − Qwen jako „anty-overthinking” LoRA | $0–5 (pliki BF16 już liczone w 16e) | niepewna | jak E2 | licencja Swift OL 1.0, decyzja użytkownika |
| — | agentowe WSP z frontier modelem na 27B | $500+ | niska powtarzalność (12.3 / 14.1 / 48.1 w trzech przebiegach) | jak E2 | nie robić |

**Co bym zrobił najpierw:** E1 (bez wydawania pieniędzy, gdy XTX jest wolny, albo za kilka $ na Vast), równolegle
prototyp E3 na CPU, bo budowa adaptera z istniejących `r_*.npy` to skrypt gguf-py. E2 dopiero, gdy E1 pokaże pętle
odporne na sampler.

## 7. Do bazy wiedzy

- `lekcje/` (nowa) „Edycja kierunku = LoRA rank-1”: każda abliteracja/steering wpisany w writer to adapter
  `B = −s·r`, `A = rᵀW`; Neuron Tuning to LoRA rank-K z one-hot `A`. llama.cpp ładuje to w runtime per żądanie.
  BF16 nie jest potrzebne.
- `modele/qwen3-8-27b` (aktualizacja): pętle myślenia są głównie kwestią samplera i trybu. W WSP 0.8B wyłączenie
  myślenia (46.8%) dało tyle co edycja (50.6%).
- `research/` (nowa) „WSP = Arditi wykonany przez agenta”: kontrola mechaniczna 46.0% vs agent 50.6%; Gemma 270M bez
  zysku.
