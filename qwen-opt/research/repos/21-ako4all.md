# 21 — AKO4ALL (TongmingLAIC) + siostrzane AKO4X

Repo: https://github.com/TongmingLAIC/AKO4ALL (commit `bbd0e1c`, 2026-09-15). Przeczytałem też siostrzane repo
https://github.com/TongmingLAIC/AKO4X (archiwum kerneli, master/sub) oraz raport techniczny
https://tongminglaic.github.io/AKO/assets/ako-tech-report.pdf. Ścieżki `ako4x/...` poniżej odnoszą się do AKO4X.

## 1. Co to jest

AKO4ALL to **nie kod kerneli, tylko protokół dla agenta**: jeden `SKILL.md` (175 linii) dla Claude Code, szablony
`HINTS.md`/`ITERATIONS.md`, wrapper benchmarku i własny evaluator w stylu KernelBench (`bench/kernelbench/bench.py`,
1397 linii). Pętla to: profil → edycja → bench → wpis do logu → commit. AKO4X dokłada kampanie wielorundowe. W każdej
rundzie startuje świeży sub‑agent, który dziedziczy archiwum wariantów danego operatora. Master wybiera rodzica i
archiwizuje wynik, a w trybie 3 bramkuje zmiany harnessu na podstawie dowodów (raport, §2).

Stan repo: MIT, 374 gwiazdki, 32 forki, publiczna historia main ma 7 commitów (marzec–wrzesień 2026), 2 otwarte issues
(„Good job”). Sprzęt: **wyłącznie NVIDIA B200 na Modal** (raport, §3). Wymagania: „NVIDIA GPU with CUDA‑enabled
PyTorch”, `ncu` (`README.md:123-125`). „Cross‑GPU canonical sweep” jest w planach na przyszłość (raport, koniec §4).

## 2. Kluczowe techniki (z dowodami)

### 2a. Proces / harness (AKO4ALL)
| # | Technika | Dowód |
|---|---|---|
| H1 | **Iteracja = bench → wpis → commit jako DWA następne wywołania narzędzi**, bez analizy pomiędzy. „Most‑missed step in practice”: agent po wyniku od razu analizuje następny krok i zostawia dziury w logu | `SKILL.md:99-107` |
| H2 | **Sygnał vs werdykt.** Kolejne iteracje szereguje się po własnym `RUNTIME` rozwiązania (referencja jest niezmienna). Pełny przebieg z referencją, pełną liczbą prób i sprawdzeniem reward‑hacku dopiero przed commitem zwycięzcy. „Never change *what* you compare against to make the bench cheaper.” Reżim pomiaru stały przez cały przebieg | `SKILL.md:111-125`, `GUIDE.md:42-53` |
| H3 | **Reguła stagnacji.** 3 iteracje bez ≥3% → ponowny profil, przegląd logu („które osie już były”), web search. Zatrzymanie tylko przy: limicie iteracji, **twardym dowodzie podłogi** (rozdzielczość timera, pasmo, narzut uruchomień) albo ≥3 udokumentowanych różnych kierunkach | `SKILL.md:127-145` |
| H4 | **HEAD na najlepszej iteracji** przez `git checkout <sha> -- solution/`, a nie rekonstrukcję z pamięci, potem bench `final` | `SKILL.md:147-158` |
| H5 | **Evaluator przeciw oszustwom.** Świeże wejścia w każdej próbie (budowane poza oknem zdarzeń). **Mutation sentinel**: po pomiarze wejścia są losowane in‑place, a wynik musi dalej zgadzać się z referencją (`bench.py:820-869`). Ogon modułu rozwiązania (`get_inputs`) jest wycinany (`bench.py:997-1009`). Flaga przy >10× | `bench.py:14-23`, `README.md:238-246` |
| H6 | **DEVIATION tylko przy porażce.** „A margin printed on success would navigate an agent toward the tolerance edge” | `bench.py:24-28` |
| H7 | Pomiar: zdarzenia CUDA, **jedno wywołanie na parę zdarzeń**, przed każdą próbą flush L2 zapisem 256 MB, mediana z 50 prób | `bench.py:89-93`, `:138-160` |

### 2b. Proces / harness (AKO4X), czyli rzeczy nowe względem naszych dotychczasowych raportów
| # | Technika | Dowód |
|---|---|---|
| X1 | **Archiwum per rodzina operatora**: `README.md` (anchor + tabela historii rund: wariant, rodzic, wynik, notatka) + `TRAPS.md` + `variants/<nazwa>/{kernel, config, result.json, variance.json, parent.txt}` | `ako4x/CLAUDE.md:35-37`, `reference/*/` |
| X2 | **Nagłówek wariantu w 5 sekcjach**: Identity / Delta from prior anchor / Lessons (HOW, WHY, **WHEN narrow / WHEN broad**) / Dead‑ends („expectation priors… re‑verifiable”) / Open directions. Archiwizuje się też warianty **poniżej bazy**, jeśli „zamykają dźwignię” | `reference/gdn-decode/variants/cuda_bv32_register_resident/kernel.py:1-130`, `ako4x/templates/retrospective.md:60-83`, `master/MASTER.md:99` |
| X3 | **TRAPS jako Fact / Why / Seen in / How to apply.** „If a future session ‘discovers’ any of these on its own, that's a signal the warning didn't land — rewrite for clarity” | `reference/gdn-decode/TRAPS.md:52-60` |
| X4 | **Świeży sub na rundę** zamiast jednego długiego kontekstu („context degrades across many attempts”). Master **ramuje** kierunek (klasa algorytmu, zmiana dźwigni) i **nie przekazuje dalej** „Open directions” poprzednika jako checklisty. **Ograniczenia** (np. „nie wołaj bibliotek”) przekazuje natomiast dosłownie | raport §2, `MASTER.md:74`, `:113-120` |
| X5 | **Retrospektywa + bramka dowodowa harnessu (tryb 3).** Sub pisze `PROPOSALS.md` (scope, wskaźnik dowodu z sesji, patch). Master odrzuca: frozen scope, brak dowodu, **„generic‑knowledge”** (czy zapis zmieni przyszłe zachowanie?). Usuwanie jest pełnoprawną klasą propozycji. Nowa treść ma być wtopiona w istniejącą sekcję zamiast dopisywana obok. Decyzje trafiają do ledgera append‑only | `templates/retrospective.md:1-15`, `:11`, `MASTER.md:87-91`, `master/harness-ledger.md` |
| X6 | **Frozen = mało i nazwane**: tożsamość zadania + scoring/baseline. Reszta jest mutowalna | `templates/closed-loop-scope.md:51-61`, `CLAUDE.md:95` |
| X7 | **Empiryka harnessu.** 12 z 17 `HINTS.md` było pustymi szablonami, a 4‑poziomowy log iteracji dawał zero wpisów. Po uproszczeniu zostały jeden wiersz Summary i wolne `## Notes` z **`Expected:` przed benchem**. „Attention budget is finite”, „required‑substance, not required‑fields” | `CLAUDE.md:75-83`, `:107`, `templates/iterations.md:37` |
| X8 | **A/B w jednym kontenerze** (`--ab-compare <label>`), łańcuchowane między iteracjami. **Bezpośredni skumulowany A/B** przed promocją: suma A/B per iteracja zaniżyła wynik 2.3–2.7× w trzech sesjach | `scripts/bench_utils.py:1313-1396`, `reference/moe-fp8-block-scale/TRAPS.md:50-77`, `:389-419` |
| X9 | **Kwarantanna oszustw w archiwum.** Wariant MoE „1.407×” przeniósł routing poza przechwycony graf i pomijał replay przy tym samym wskaźniku. Zdegradowano go, uczciwy anchor ma 1.204× | `reference/moe-fp8-block-scale/README.md:15-33` |
| X10 | Szum Modal: ±5–15% między kontenerami vs ±1% w jednym. „Never trust a single‑session headline difference < 5%” | `reference/gdn-decode/TRAPS.md:145-171` |

### 2c. Techniki kernelowe z archiwum (B200; pomiary autorów, 3‑run variance‑check)
- **GDN decode** (`gdn_decode_qk4_v8_d128`, stan fp32 128×128): 1.18× ± 0.002 vs FlashInfer. Rozkład per B:
  **B=1 1.49×, B=4 1.33×, B=32 0.986×, B=64 0.999×** (`gdn-decode/.../kernel.py:6-9`). Mechanizmy:
  stan w rejestrach (`[V_PER_WARP][4]` na lane, redukcja `shfl_xor`), load stanu wydany jako pierwszy (`:200-226`),
  BV dobierane tak, żeby było ~1024 CTA na falę (`TRAPS.md:237-264`). Bloki tej samej (b,h) są sąsiednie w kolejności
  dispatchu („SWAP_GRID”), a dopiero na to nałożone hinty eviction (+0.5–1% przy dużym B). Bez sąsiedztwa hinty są
  ujemne (`TRAPS.md:62-89`). `ld.global.nc` pomaga tylko dla małych q/k, dla stanu 16 KB daje −1…−2% (`kernel.py:53-67`,
  `:113-116`). Zwykły store zamiast `evict_first` daje +0.6% (`:69-82`).
- **Martwe końce GDN**: staging stanu w SMEM −16% mimo prognozy NCU „+68%” (`TRAPS.md:208-235`). Zewnętrzna pętla
  persistent niszczy lokalność kolejności siatki: −24…−37% (`TRAPS.md:173-206`). `num_stages≥2` na krótkich pętlach
  RMW: −10…−28% (`TRAPS.md:91-119`).
- **GQA paged decode** 1.44×: PDL między split a reduce +10%, głęboki pipeline dla B=1 +20%. Redukcja „atomic
  last‑writer” w jednym launchu: −10…−15% (Triton nie wyciął martwej ścieżki). Persistent + work‑stealing zamknięte
  trzema przyczynami. Packed reduce schodzi poniżej 1 fali i przegrywa (`gqa-paged-decode-.../README.md:12-16`).
- **MoE FP8**: `sem="relaxed"` na atomikach scatter‑add to „single biggest lever” (`moe-fp8-block-scale/README.md:163`).
  Przy małym T alokator PyTorch kosztuje 5–7 µs na `torch.empty` (`:166`).
- **Wyniki zbiorcze** (raport, Tab. 1): DSA sparse attention 31.1×, MoE 1.20×, GDN decode 1.18×, GDN prefill 2.37×.
  Pozostałe cele: GQA 1.46×, MLA decode 1.45×, MLA prefill 1.44×, RMSNorm 1.16×, GEMM 1.00× („honest negative”).
  README AKO4ALL podaje inne liczby (1.36/1.21/1.50/1.12×, „Claude Opus 4.8”, `README.md:141-148`). Typowy przebieg:
  ~55 min, ~253k tokenów wyjścia (`README.md:152-156`).

### 2d. Wsparcie AMD/ROCm
Praktycznie brak. `--backend hip` to tylko etykieta: „`cuda` and `hip` are loader‑equivalent; the distinction is
informational only” (`GUIDE.md:106-118`, `bench.py:1015-1016`). Profilowanie wyłącznie przez `ncu`. Nie ma rocprof, gfx
ani skilla HIP (`ako4x/templates/skills/`: cuda, cute‑dsl, triton, tilelang, cpp, ncu, sanitizer). `[WNIOSEK]` Evaluator
ruszyłby na ROCm PyTorch, bo używa `torch.cuda.*` (`bench.py:612`), ale nie mierzy tego, co nas boli (§5).

## 3. Przeniesienie na AMD/HIP/RDNA3

| Technika | Przenośność | Jak u nas / dlaczego nie |
|---|---|---|
| H1 bench→log→commit | tak | Działa niezależnie od sprzętu. U nas odpowiada mu commit/łatka po każdym pomiarze agenta i wpis do NOTES. |
| H2 sygnał/werdykt | tak, już częściowo jest | Sygnał: rocprofv3 czas kernela albo `llama-bench` tg n=1/5. Werdykt: `spec_sweep` z przeplatanym A/B. Reguła „ten sam reżim w rankingu i werdykcie” jest u nas ważna, bo mikrobench myli się co do GLC/DLC (`NOTES.md:247-250`). |
| H3 stagnacja/stop | tak | Podłogę liczymy z bajtów/czasu (`kernel_bw.py`), bez PMC (rocprofv3 zwraca 0, `NOTES.md:256`). |
| H5 sentinel | tak, w formie testu grafu | Odpowiednik: **HIP graph reuse z tymi samymi wskaźnikami i innymi danymi**. AKO opisuje dokładnie ten błąd dla grafów kluczowanych wskaźnikiem (`gdn-decode/TRAPS.md:121-143`). Nakłada się z zatruwaniem buforów z raportu 04. |
| H7 pomiar 1 launch/zdarzenie + flush | **nie** | Przy kernelach 2–5 µs i granicy grafu ~2.5 µs (`NOTES.md:358`) pojedynczy launch mierzy narzut. Flush 256 MB > MALL 96 MB, więc sam flush by zadziałał, ale u nas liczy się czas w grafie. Patrz 04‑kernelbench. |
| X1–X3 archiwum + TRAPS | tak | Mamy zaczątek: `tools/fusion/gdn-pipeline-rejected.patch` (odrzucony wariant zachowany jako kod) i „Wyniki negatywne” w NOTES (bez „Why” i bez warunku odwrócenia). |
| X4 świeży sub + ramowanie | tak | Main już tak pracuje (LfmDecode3, Repo*). Brakuje jawnej reguły „ramuj, nie przekazuj Open directions; ograniczenia dosłownie”. |
| X5 bramka dowodowa | tak | Dotyczy `_BRIEF.md`, instrukcji agentów, NOTES, TRAPS. |
| X8 skumulowany A/B | tak, taniej niż u nich | Mamy przełączniki `GGML_HIP_*`/`LLAMA_*` w jednym binarium, więc „earliest reference” = wszystkie wyłączone, bez przebudowy. |
| SWAP_GRID (sąsiedztwo bloków tej samej głowy) | tak | Nasz GDN ma `blockIdx.x = głowa`, `blockIdx.z` = blok kolumn (`gated_delta_net.cu:53`, `:67`, `:388`). 8 bloków jednej głowy leży 48 pozycji od siebie w kolejności dispatchu. Zamiana osi daje sąsiedztwo i jest bitowo identyczna z konstrukcji. |
| Hinty eviction / `ld.global.nc` | częściowo | Odpowiedniki RDNA3: bity GLC/SLC/DLC w buffer loadach, `__builtin_nontemporal_load/store`. Ich lekcja „hinty dopiero po ustawieniu sąsiedztwa” pasuje do naszego negatywu „SLC/GLC osobno” (`NOTES.md:256`). |
| PDL split→reduce | **nie** | ROCm 10.0 nie ma PDL (07‑flashinfer, wiersz 20). Odpowiednik: ogon „ostatni blok + ticket” (~1 µs vs 2.5 µs granicy, `NOTES.md:358`). Ich regres „atomic last‑writer” wynika z Tritona (martwy kod), nie z mechanizmu. |
| SMEM staging, persistent outer loop (negatywy) | tak, jako ostrzeżenie | Persistent łamiący lokalność kolejności siatki pasuje do naszego „łańcuch faz w kernelu trwałym 8–11 µs/fazę” (`NOTES.md:358`). „Est. Local Speedup” z NCU nie ma u nas odpowiednika, ale lekcja „prognoza z obłożenia ignoruje koszt stagingu” dotyczy każdego naszego szacunku z `.vgpr_count`. |
| `sem=relaxed` atomiki | tak | W HIP `__hip_atomic_fetch_add(..., __ATOMIC_RELAXED, __HIP_MEMORY_SCOPE_AGENT)`. `[WNIOSEK]` Nasze tickety „ostatni blok” potrzebują acquire/release tylko na liczniku, a reszta zapisów może być relaxed. Do sprawdzenia w ISA, czy nie ma zbędnych `buffer_wbl2`/`s_waitcnt`. |

## 4. Pomysły dla nas

Nie powtarzam pomysłów, które już są: przeplatane A/B, A/A, bramka bitowa, diff histogramu kerneli, zatruwanie buforów
(04), `gate.sh`, ledger `experiments.jsonl` z prognozą, dedup po ISA (06), stan GDN fp16 (07, 11), sonda koalescencji
stanu GDN (14‑P1), złożenie FA combine (lfm‑decode‑round2 „not done”). Poniżej jest to, co dokłada AKO.

**P1. Ablacja „leave‑one‑out” całego stosu łatek przełącznikami (Qwen + LFM).** Źródło: X8.
- Co: skrypt nad `spec_sweep`/`llama-bench`, który w jednym binarium mierzy: wszystkie przełączniki ON, wszystkie OFF
  (stan „earliest reference”) i po kolei każdy jeden OFF (LOO). Przeplatane pary, 2 modele, dla Qwena tryb MTP n=4 i
  plain. Wynik: tabela marginalnego zysku każdej łatki **w obecności pozostałych** i suma marginesów vs bezpośredni
  ON−OFF.
- Zysk `[SZACUNEK]`: 0–1% t/s wprost (zdjęcie łatki z ujemnym marginesem). Główna wartość jest w utrzymaniu: przy 54
  łatkach na upstream każda łatka z marginesem ≈0 to koszt rebase'u bez zysku. Kandydaci do sprawdzenia `[WNIOSEK]`:
  `GGML_HIP_Q8_IDS` (0049) po `GGML_HIP_NORM_ROUTER` (0053), bo oba dotyczą q8_1 wejścia gate/up, oraz para
  `GGML_HIP_NORM_FAST` vs A6.
- Koszt: ~0.5 dnia na skrypt, ~2–3 h GPU na model. Ryzyko: przełączniki nie są ortogonalne (niektóre wymagają innych).
  Trzeba spisać zależności, a to też jest wartość.
- Pomiar: ms/krok i ms/token, liczba par wygranych, greedy md5 w każdej konfiguracji (każda kombinacja musi być
  bitowo równa bazie, inaczej przełącznik ma ukrytą zależność).

**P2. Archiwum per rodzina kerneli + TRAPS w formacie Fact/Why/Seen/How‑to‑apply/WHEN.** Źródło: X1–X3.
- Co: `research/archive/<rodzina>/` dla `mmvq-multicol`, `gdn`, `fattn-kvq`, `moe-lfm`, `mmq-prefill`, `small-kernels`.
  W każdym: `README.md` (anchor = commit + ms, tabela historii: runda, łatka, rodzic, wynik, notka) i `TRAPS.md`.
  Odrzucone warianty trzymamy jako `.patch` z 5‑sekcyjnym nagłówkiem, jak `tools/fusion/gdn-pipeline-rejected.patch`.
  „Wyniki negatywne” z NOTES przenieść do TRAPS z dopisanym **Why** i **warunkiem odwrócenia** (WHEN narrow/broad). Wtedy
  „nie wracać bez nowego pomysłu” staje się sprawdzalne. Uzupełnia ledger z 06‑P4: ledger to surowe próby, archiwum to
  kuratorowana synteza z kodem.
- Brief agenta kernelowego dostaje **tylko** archiwum swojej rodziny, a nie cały NOTES (X7, „attention budget”).
- Zysk: brak t/s. `[SZACUNEK]` mniej powtórzonych ślepych uliczek. Ten raport sam musiał sprawdzić 6 innych raportów,
  żeby nie dublować pomysłów (patrz P4).
- Koszt: ~1 dzień jednorazowo, potem utrzymanie przez Main. Ryzyko: rozjazd z NOTES. Reguła: NOTES = wyniki, archiwum =
  wiedza per rodzina.

**P3. Retrospektywa agenta + bramka dowodowa dla naszych instrukcji i briefów.** Źródło: X5–X6.
- Co: każdy agent kernelowy kończy pracę sekcją „Propozycje harnessu” (scope = plik: `_BRIEF.md`, szablon briefu,
  `TRAPS.md`, skrypt pomiaru; dowód = konkretny pomiar, commit lub wywołanie z tej sesji). Main bramkuje według reguł AKO:
  - odrzuca frozen (sposób liczenia ms/krok, zestaw promptów `spec_sweep`, bramka bitowa);
  - odrzuca brak dowodu i „generic‑knowledge”;
  - przyjmuje propozycje usunięcia;
  - wtapia nową treść w istniejącą sekcję zamiast dopisywać.
  Każda decyzja to jedna linia w `research/harness-ledger.md`.
- Zysk: pośredni. Koszt: 1 h (szablon). Ryzyko: rozrost briefów. Przeciwdziałanie to klasa „deletion” i limit długości.
- Pomiar: liczba zdublowanych pomysłów i powtórzonych negatywów w kolejnych rundach.

**P4. (Przykład P3 na tej sesji) Indeks pomysłów `research/repos/_IDEAS.md`.** Dowód z tej sesji:
- Stan GDN w 16 bitach proponują niezależnie 07‑flashinfer (#18', „raczej nie”) i 11‑vllm‑xpu (P1, „+0.5–1%”).
- Przeplatane A/B/ledger pojawiają się w 04, 06 i strata.
- Sonda stanu GDN jest w 14‑P1, a sąsiedztwo siatki GDN wynika z tego raportu.

Każdy nowy agent repo musi to dziś odkrywać grepem. Main prowadzi jedną tabelę: pomysł, raporty źródłowe, status (nowy /
w kolejce / zrobiony / negatywny + link), a brief każe ją przeczytać przed pisaniem. Koszt: 1–2 h. Zysk: mniej
dubli i sprzecznych szacunków dla tego samego pomysłu.

**P5. GDN: zamiana osi siatki (sąsiedztwo bloków jednej głowy), bitowo identyczne.** Źródło: §2c SWAP_GRID.
- Co: w `ggml/src/ggml-cuda/gated_delta_net.cu:388` siatka `(S_v/(cpw·nw), n_seqs, H)` zamiast `(H, n_seqs, …)` i
  odpowiednio `h_idx`/`col` (`:53`, `:67`). Arytmetyka per blok bez zmian. Wtedy 8 bloków jednej głowy czyta w
  kolejności dispatchu 64 KB ciągłego stanu zamiast 8 KB skoków co 64 KB. Dopiero potem, osobnym krokiem,
  `__builtin_nontemporal_store` dla zapisu stanu (AKO: hinty pomagają tylko po ustawieniu sąsiedztwa).
- Zysk `[SZACUNEK]`: 0–3% czasu kernela GDN (638 µs na weryfikację, `NOTES.md:292`), czyli ≤0.02 ms/krok. Ich zysk
  sąsiedztwa to +0.58% przy B≥32. Na GDDR6 strona 2 KB jest i tak w pełni zużywana przez blok 8 KB, więc oczekuję
  bliżej zera. Robić tylko razem z 14‑P1, bo to ten sam pomiar.
- Koszt: 30 min. Ryzyko: brak (bitowo). Pomiar: rocprofv3 `gated_delta_net_cuda` przy weryfikacji n=5, przeplatane.

**P6. Reguły procesu do szablonu briefu agenta kernelowego.** Źródło: H1–H4, X4, X7. Każda reguła to jedna linia:
- (a) po każdym pomiarze najpierw wpis i commit, dopiero potem analiza;
- (b) `Expected:` z mechanizmem i przewidywaną deltą przed pomiarem (zgodne z 06‑P4);
- (c) stop tylko z dowodem podłogi (bajty/czas vs zmierzony dach) albo po ≥3 udokumentowanych kierunkach;
- (d) przy zakończeniu przywrócić najlepszy wariant przez `git checkout <sha> -- plik`, nie z pamięci;
- (e) Main przekazuje następnemu agentowi **ramę**, a ograniczenia (bitowo, bez GPU współdzielonego, przełącznik
  `GGML_HIP_*=0`) **dosłownie**;
- (f) przy zmianach niebitowych (np. stan GDN fp16) agent widzi tylko PASS/FAIL bramki KLD, a margines dopiero przy
  FAIL (H6), żeby nie stroił pod próg.

Koszt: 30 min. Zysk: pośredni.

**Outside the box.** Ich wynik GDN B=1 1.49× przy ~1.0× dla B≥32 pokazuje `[WNIOSEK]`, że u nich zysk przy małym batchu
pochodzi z usunięcia narzutu hosta (graf kluczowany wskaźnikiem), a nie z kernela. Nasz odpowiednik ten narzut już
usunął (grafy HIP, asynchroniczne wejścia, K3). Prawdziwa lekcja kernelowa dla RDNA3 jest więc negatywna: przy stanie
fp32 RMW (nasz GDN, stan 3 MiB/warstwę `[WNIOSEK z 07/11]`) „register‑resident + jedna fala bloków” to już sufit
struktury. Poniżej sufitu zostaje tylko zmniejszenie bajtów (fp16 stanu, 11‑P1) albo usunięcie granic kernela, a nie
dalsze strojenie układu.

## 5. Krytyka

- **Brak AMD.** Etykieta `hip` niczego nie robi. Cały aparat diagnostyczny (ncu, Est. Local Speedup, sanitizer) jest
  NVIDIA‑only, a dla nas liczniki PMC i tak są martwe.
- **Evaluator nie nadaje się do kerneli decode LLM.** Jeden launch na parę zdarzeń plus flush L2 (`bench.py:138-160`) dla
  kerneli 2–5 µs mierzy narzut uruchomienia. SKILL sam to przyznaje jako warunek stopu („min runtime at cuda‑event timer
  resolution”, `SKILL.md:142`). Referencja PyTorch eager zawyża przyspieszenia (jak w 04).
- **Bramka dowodowa w praktyce nic nie odrzuciła.** W `master/harness-ledger.md` jest 35 decyzji i wszystkie to
  `accepted` (taksonomia odrzuceń istnieje tylko w opisie). Dowody „dwóch pilotów” to sami autorzy, którzy przyznają
  „the evidence is two pilots, not a fully‑scaled result” (raport §3).
- **A/B „w jednym kontenerze” uruchamia B, potem A**, bez przeplotu i bez A/A (`bench_utils.py:1381-1396`). Nasz proces
  jest mocniejszy. Ich obserwacja „suma A/B zaniża 2.3–2.7×” to częściowo artefakt metryki: sumują przyrosty średniego
  *speedupu* (stosunku). Wygrane z różnych reżimów (mały T vs duży T) w średniej stosunków nie są addytywne. W
  milisekundach (nasza jednostka) addytywność jest naturalna, ale bezpośredni pomiar skumulowany i tak jest słuszny.
- **Nagłówki liczb nie są spójne**: README AKO4ALL (Opus 4.8: 1.36/1.21/1.50/1.12×) vs raport AKO4X (Opus 4.6/4.7:
  1.46/1.45/1.44/1.16×). „31× na DSA sparse attention” jest względem eksperta FlashInfer w tym konkretnym zestawie
  obciążeń. To nie jest wydajność względem dachu sprzętu (brak SOL).
- **Ich wnioski kernelowe są w dużej części o ograniczeniach Tritona 3.6** (pipeliner, DCE, spill przy BV=32), a nie o
  sprzęcie (`gqa.../README.md:22`). Nie przenosić jako praw ogólnych.
- Tryb „agent może zmienić język”, `pip install` i `--dangerously-skip-permissions` (`README.md:128`, `:176-180`) kłócą
  się z naszymi zasadami (sprzęt chroniony, bez instalacji).

## 6. Werdykt

**Średnia (tylko proces).** Kerneli do przeniesienia na RDNA3 brak, a archiwum GDN potwierdza, że nasz kernel ma już
właściwą strukturę. Warto natomiast przejąć tanie elementy organizacji pracy agentów, których jeszcze nie mamy:
- archiwum per rodzina z TRAPS „Why/WHEN”;
- retrospektywę z bramką dowodową dla briefów;
- świeżego agenta na rundę z ramowaniem zamiast przekazywania checklisty;
- ablację LOO całego stosu 54 łatek przełącznikami.
