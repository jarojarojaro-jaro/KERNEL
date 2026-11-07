# 68b. Spekulacja bezstratna: co nowego od września do listopada 2026 i co z tego bierzemy na XTX

Data: 2026-11-07. Autor: podagent R68b_SpecDecode. Praca tylko na CPU (bez GPU, bez pobierania wag, bez buildów). Trzy własne analizy offline (`nice -n 19`, łącznie ~2 min CPU) na danych z raportu 24s i na prawdziwej sesji omp z 2026-11-06. Skrypty i wyniki: [`68b-skrypty/`](68b-skrypty/).

Punkt odniesienia (final mode, `~/wt/topka-q63`, Qwen3.8-27B-Uncensored Q4_K_M, MTP n=4 + słownik draftu 64k + głowica IQ4_XS, ogon lookup W16, sprzężone próbkowanie, GPU verify, PM4 replay): sesja agentowa 120.8 t/s, spec_sweep T=1 118.3 t/s przy 26.9 ms/krok, akceptacja MTP 0.45–0.8 (`wiki/REKORDY.md:154-158`).

Oznaczenia: **NOWE** = brak w wiki i w raportach 10–67; **znane (X)** = już opisane w X; `[SZACUNEK]` = arytmetyka, nie pomiar; `[INFERENCE]` = wniosek bez pomiaru; „sym.” = nasza symulacja offline na CPU. Liczby producentów i autorów prac podaję osobno od naszych.

## TL;DR

1. **Nie ma nowego „przełomu” dla jednego zapytania na naszej karcie.** Wszystkie duże liczby z okresu (SpecPilot 10.87×, HybridSpec 1.30×, DLoop +5…41%, Gumbo +26.7%, AgSpec 4.37×) liczą się względem słabszych baseline'ów (stockowy DFlash bez drzewa, sampler EAGLE-3 bez sprzężenia, weryfikacja GDN ze snapshotem po każdym tokenie). Te braki u nas już załatane: sprzężone próbkowanie (24p), lag/replay GDN (S4), ogon lookup (16b), K/V-only catch-up MTP (`src/llama-context.cpp:308-325`).
2. **Najlepszy nowy kandydat: głębokość MTP wybierana w bieżącym kroku z luki Gumbela** (różnica dwóch najlepszych zaburzonych wyników draftu, znana już w chwili draftu dzięki sprzężeniu). Sym. na 36 270 startach z 24s: **+3.9% t/s (wszystko), en-czat +2.9%, pl-czat +4.8%, proza +3.1…4.3%**, ale **tylko z wczesnym wyjściem z grafu łańcucha draftu**. Gdy łańcuch zawsze liczy 5 przejść, a skraca się tylko weryfikacja: ~0% (§2.2).
3. **Blokadą tego (i każdej zmiany polityki draftu) jest nasza bramka „md5 identyczne z topką”, nie rozkład wyjścia.** SpecPilot (arXiv 2611.02501) proponuje bramkę „token forcing”: wskaźnik niezgodności z argmaxem referencji liczony token po tokenie, plus test zdarzeń z dużym marginesem. Ta bramka odróżnia zmiany bezstratne od wadliwych, a dokładność zadań tego nie potrafi. To NOWA metoda dla nas; odblokowuje 24q (dziś martwe tylko przez md5) i pkt 2.
4. **Drzewo w stylu Gumbo na sprzężonym łańcuchu się nie opłaca przy dzisiejszym koszcie wiersza.** Sym.: +1.4…1.6% (wszystko), en-czat +2.4% przy 0.85 ms/wiersz. +3.1% wymaga 0.57 ms/wiersz, +4.0% wymaga 0.40 ms. Werdykt: czekać na tańszy wiersz weryfikacji (§2.1).
5. **Globalny cache sufiksów (raport 18 #6, AgSpec) zabity na naszych danych.** Na prawdziwej sesji omp korpus 400 wcześniejszych sesji (49.8 M tokenów słownych) dokłada 0.1% tokenów w ogonie poza zasięgiem MTP-4. Lookup z bieżącej sesji daje tam 9.1% (§2.3). Pomysł AgSpec z „formatem emisji” też odpada: Qwen3.8 ma surowe parametry XML, a edycja omp to surowe `old_string`/`new_string` (72.7% tokenów edycji przewiduje już lookup z sesji).
6. **Tańszy krok weryfikacji:** jedyny nowy, osiągalny kawałek to **GDN weryfikacji w formie chunkwise/WY w fp32** (HybridSpec, SpecPilot, ReplaySSM). Dziś `gdn` zajmuje 0.715 ms na krok przy podłodze ~0.16 ms (`~/qwen-opt/xtxroadmap/burst_decomp.txt`, wiersz verify). Szacunek **+1…1.7%** na każdym kontekście `[SZACUNEK]`. W 66 „chunked GDN” trafiło do stratnych tylko przez wariant bf16 z TokenSpeed; wariant zgodny z fp32 to klasa „kolejność floatów” (§1.1).
7. **Douczanie głowicy MTP (plan #19) ma nowe dowody przeciw:** retrening głowicy natywnej Qwen3.8-27B (rwmacy v8, 4.35 M pozycji on-policy) dał na ruchu agentowym parytet, L 3.01 vs 3.00. Nowe straty z artykułów (WTV, VAT, SpecOPD: +11…41% AL) mierzono na drafterach równoległych i małych celach, nie na pojedynczej głowicy MTP 27B.

## 0. Czego nie powtarzam (stan wiedzy przed 68b)

| temat | gdzie | stan |
|---|---|---|
| sprzężone próbkowanie Gumbela przy T=1 | 24p, `metody/sprzezone-probkowanie-draftu` | w produkcji, +3.5% |
| drzewa MTP (statyczne, dynamiczne, sprzężone statyczne) | 24s, 36 L1, 66d C, `metody/drzewo-weryfikacji-gdn-wy` | sufit +4.7% (niesprzężone), +0.3% (sprzężone statyczne) |
| adaptacyjna głębokość z historii, bramka ogona | 24q, łatka 0039 | martwe przez md5 |
| shortlist low-rank, rerank głowicy, certyfikowany head | 52, 53, 36 §3, 66d B | recall nie przeszedł; certyfikat wymaga klasy Q8 |
| słownik draftu 16k/32k/64k/96k, pełny słownik dla OOV | 07 (0004), 24b | 64k optimum |
| DFlash/DFlash2/DSpark/DSpine/EAGLE-4 | 32f, 52, 57e, 58, 63d, 67b | przy T=1 na czacie nie biją MTP |
| lookup, ogon W16, „zastąp gdy pewny”, globalny cache sufiksów | 15b, 16b, 18 #6, 66 #13 | ogon w produkcji; #6 nietestowany |
| ReplaySSM (lag/replay GDN), conv-lag | S4, `kernele/gdn-replay`, 66b §188 | w produkcji |
| K/V-only catch-up MTP, lean reserve | 65, `src/llama-context.cpp:308-325` | w produkcji |
| samodestylacja głowicy MTP | 11, 40, plan #19 | pilot negatywny; propozycja TV na 20 M tokenów |
| block verification, typical acceptance | 18 #10, `qwen-opt/research/algorithms.md` | #10 niezmierzone; typical = stratne |

## 1. Ustalenia per źródło

### 1.1 arXiv / alphaXiv

**SpecPilot (arXiv 2611.02501, 2026-11-02; kod github.com/StargazerX0/SpecPilot; omówienie sysnote 2026-11-05).** Pętla agentów (Claude Opus 5.5 w Claude Code) stroi cały stos spekulacji pod jedno wdrożenie. Liczby autorów: Qwen3.8-27B + DFlash2, jedno zapytanie, 4.46× → 10.87× nad AR na RTX PRO 6000 i 8.86–9.41× na H100. Wobec DDTree to tylko 1.84×. Wynik to ~15 zmian złożonych razem, a największa z nich to weryfikacja dwupoziomowa.
- **W12** (bezstratny 12-bitowy zapis BF16) i **TLV** (przejście Q po 8-bitowym widoku wag, potem jedno przejście dokładne). U nas nie do przeniesienia: wagi to już Q4_K_M, a druga kopia celu nie zmieści się w 24 GB przy 262k kontekstu. Autorzy sami podają, że TLV przy batchu na BF16 27B jest **13% wolniejsze**.
- **Certyfikowany head INT8** (granica Cauchy'ego-Schwarza, dokładne przeliczenie ocalałych): znane (36 §3). U nas certyfikat wymaga przybliżenia klasy Q8, więc netto ≈ 0.
- **Drzewo dla hybryd GDN** (ścieżkowy kernel GDN bit w bit z łańcuchem; kernel WY z podziałem stanu fp32 na 3× BF16, „w granicach 1 ulp BF16”): znane jako kierunek (66d C, TreeWY w 36). **NOWE** jest to, że da się zbudować kernel WY zgodny z fp32. Dotyczy to też pkt 4 tabeli.
- **Token forcing — NOWE (metoda).** Wyjście systemu przechodzi przez cel z FP32 LM head w trybie teacher-forced. Token, który nie jest argmaxem referencji, to niezgodność. Odrzuca się system, którego wskaźnik niezgodności przekracza stock o > 0.5 pp (95% ufności), albo który ma nadmiar niewyjaśnionych zdarzeń z marginesem > 2δ. Stock ma 0.72% niezgodności (prawie same remisy). Wadliwy system z biasem logitu +2 ma 2.0–2.4%, a dokładność zadań go nie wykrywa (−1.6 pp, CI zachodzi na zero). Dla nas to bramka dla zmian, które przesuwają szerokość weryfikacji (patrz §3, poz. 2).

**HybridSpec (arXiv 2611.04055, 2026-11-02, Meta/NYU).** Liczby autorów: GDN+MoE (Qwen3.5/3.6-35B-A3B, 122B-A10B) z DFlash na A100 dają 1.30–1.33× nad DFlash.
- Długość weryfikacji wybierana na GPU kryterium Dinkelbacha: maksymalizacja przepustowości łącznej, a nie średniej stosunków per runda. Prawdopodobieństwa akceptacji pochodzą z kalibrowanej pewności top-1 i entropii draftera. Bez kopiowania długości na CPU (warunkowy węzeł grafu).
- Korekta na granicy routera MoE: u nas nie dotyczy (gęsty 27B).
- Blokowo-równoległy kernel GDN: rozwiązanie trójkątne w×w, przechowuje tylko czynniki (z, k, g), jeden kernel commit odtwarza stan przyjęty we wszystkich warstwach. W izolacji 1.54–4.04× szybszy niż SGLang, który zapisuje stan po każdym tokenie. U nas ten baseline już nie istnieje (lag/replay), więc realny zysk jest mniejszy (§3, poz. 4).
- Ablacja: sam wybór długości daje 1.19× nad stałą długością 7, ale na MoE, gdzie weryfikacja rośnie o 71% między długością 4 a 16. U nas wiersz kosztuje 0.85 ms (~3.2%), więc efekt będzie mniejszy, zgodnie z 24q.

**DLoop (arXiv 2610.07659, 2026-10-06, v2 10-21; NAVER; kod zapowiedziany naver-ai/DLoop).** Kilka etapów draftu przed jedną weryfikacją, dopóki drafter jest pewny. Autorzy: +5…41% wall-clock bezstratnie, także dla modułów MTP, ale z treningiem „loop-aware”. Dla naszego autoregresyjnego łańcucha MTP to po prostu adaptacyjna głębokość: **znane (24q, 0039)**. Nowa jest tylko kalibracja pewności, a tę w §2.2 robię luką Gumbela.

**Gumbo (NeurIPS 2026 poster 150279, OpenReview jLWQiUQcDp; Yi, Fu, Wang) + Gumbel-max list sampling (arXiv 2506.05632).** Wielodraftowe uogólnienie sprzężenia Gumbela (Daliri i in.): drafter-invariant, O(|V|) zamiast O(|V|^k), drzewo rozwijane i rerankowane wynikami Gumbela. Autorzy: do +26.7% przy T=1 wobec samplera EAGLE-3.
- Dla nas: **częściowo znane.** Mamy sprzężenie, a statyczne drzewo z rangą Gumbela policzono w 24s (`24s-drzewa/tree_ceiling.py:75-113`). Dynamiczne drzewo z luki Gumbela sprawdziłem w §2.1: ≤ +1.6% przy dzisiejszym koszcie wiersza.
- Korekta do wiki: `metody/drzewo-weryfikacji-gdn-wy.md:12` mówi, że przy T>0 potrzebna jest rejekcja SpecInfer. **Przy naszej weryfikacji sprzężonej („losuj i dopasuj”) każde drzewo jest bezstratne bez SpecInfer** (24s:33-35; Gumbo). Wiki nie edytuję, uwaga dla Main.

**ReplaySSM (arXiv 2610.13778, 2026-10-09; blog dao-lab.ai i NVIDIA 10-12; vLLM PR #66318 na Triton/ROCm, 11-06).** Bufor ostatnich wejść SSM zamiast stanu, weryfikacja „output-only”, zapis stanu tylko przy opróżnieniu bufora. Liczby autorów: przy batchu 256 1.20–1.47× dekodowania i 1.8× spekulacji. **Znane (66b: „ReplaySSM już mamy, `rs_lag`”).** Dla batcha 1 zostaje tylko pomysł obliczania wyjść bez materializacji stanów (§3, poz. 4). Zapis stanu raz na k kroków zamiast co krok oszczędza ~0.08 ms/krok (~0.3%) `[SZACUNEK: 151 MB stanu, 926 GB/s]`.

**TreeWY (arXiv 2608.20961, 2026-08-21) i Bole (arXiv 2608.01651, 2026-08-03).** Weryfikacja drzew dla GDN bez snapshotów. Autor TreeWY sam pisze: szersze drzewo „not yet a throughput win”. **Znane (36 L1, 66d C).**

**AgSpec (arXiv 2610.01108, 2026-10-01, v2 10-06).** Lookup dla agentów kodujących z trzech korpusów: sesja, przestrzeń robocza i korpus globalny. Pliki są indeksowane „w formacie emisji” (prefiksy diff, escapowanie JSON przy zapisie przez tool call), a limit długości draftu ustalany per agent. Autorzy: do 4.37× nad AR przy batchu 1. Dla nas: korpus sesji = nasz lookup (znane). Globalny korpus i format emisji zmierzyłem na naszej sesji (§2.3): oba **kill**.

**Hybrid Spark (arXiv 2611.05611, 2026-11-03).** Co krok drafter modelowy (DSpark) i n-gramowy (z kalibrowaną akceptacją), wygrywa lepszy łańcuch po „cenie wiersza”. Autorzy: 1.10–1.62× na edycji kodu przy batchu 4, czat T=0 0.97–1.01×. Dla nas **znane** (ogon W16 za MTP, 16b; „zastąp gdy pewny”, 66 #13; lekcja `lekcja-mtp-juz-kopiuje`).

**Trening draftu: SpecOPD (arXiv 2611.02846, 11-02), Acceptance-Aware Training (WTV/EAL, arXiv 2609.24150, 09-21), VAT (arXiv 2608.30135, NeurIPS 2026).** Straty celowane w długość akceptacji (TV okna przy próbkowaniu, wagi do pierwszego odrzucenia, klasyfikator weryfikacji). Autorzy: AL +11.4% (VAT), do +41% (SpecOPD), wszystko na drafterach EAGLE-3/DFlash/DSpark. To ta sama kategoria co plan #19 (40: strata TV na rozkładach filtrowanych). Nic nowego do zrobienia bez $ (wynajem GPU). Dowody przeciw w §1.3.

**Nie dla nas:**
- One Call Ahead / Packed-SS (arXiv 2610.33379): modele z trybem AR i dyfuzji.
- Beneath the Tokens (arXiv 2609.35188): A10G, tylko potwierdza amortyzację.
- Adversarial Speculative Reasoning (arXiv 2611.05345): trening draftu „do odrzucenia” dla jakości agentów, nie dla prędkości.
- Rank-Aware Speculative Sampling (arXiv 2610.02251): modele dyfuzyjne obrazu.

### 1.2 GitHub: llama.cpp i forki

| PR / issue | co robi | dla nas |
|---|---|---|
| ggml-org #31750 (otwarty, 2026-11-05) | K/V-only graf catch-up MTP; W7800 Vulkan 131k: −2.19% ms/krok, akceptacja i tokeny bez zmian | **już mamy** (`src/llama-context.cpp:308-325`, `LLAMA_MTP_LEAN_RESERVE`) |
| #30141 (scalony 2026-11-03) | zapis/odczyt `pending_h` MTP w checkpointach; autor: 32/32 wektorów logitów draftu inne bez łatki, 0/32 zmian top-1, akceptacja bez zmian | już przeniesione (`c0576e3e8` w topka-q63) |
| #31037 (otwarty, 10-23) | głowica MTP przycięta do K pierwszych id; Swift-1.5 SYCL +7.4% | znane (0004, słownik 64k) |
| #30663 (zamknięty 10-28) i #27694 | probabilistyczny draft DFlash2/MTP + rejekcja; 5090 Qwen3.8-27B T=1 +4.2% t/s | znane; nasze sprzężenie daje +3.5% przy T=1 (24p) i nie potrzebuje q |
| artykuł freenode 10-28 („+20…43%”) | to samo co #30663 z progiem p_min 0.75 | liczba względem mastera z p_min; u nas p_min = 0 w łańcuchu |
| PrismML #320 (10-05) | `--spec-draft-window`: KV draftu tylko N ostatnich wierszy; draft bez limitu głębokości | nie dotyczy (draftujemy na każdej głębokości; KV draftu q4_0, 65) |
| #31660 (scalony 11-05) | snapshoty conv MTP jednym `set_rows` | mamy conv-lag (0038) |

### 1.3 Hugging Face, Reddit, repozytoria społeczności (akceptacja MTP Qwen3.x)

- **rwmacy/qwen3.8-27b-mtp-head-v8-b70** (commit `c18ff99`, ~sierpień 2026). Retrening natywnej głowicy MTP Qwen3.8-27B-FP8 (SpecForge TTT 4, start od głowicy fabrycznej, 4.35 M pozycji on-policy, 9 domen, ~50/50 myślenie).
  - Holdout L 2.801.
  - **Replay prawdziwego ruchu agentowego: parytet (L 3.01 vs 3.00, +0.20 t/s, 14/28 wygranych).** Autor: „the shipped head was already at its ceiling on that mix”.
  - Trzeci niezależny wynik zgodny z naszym pilotem (11) i ±2% z `glowica-mtp`. Obniża szanse planu #19 na ruchu agentowym `[INFERENCE]`.
- **adrienbrault R572** (2026-09-19, Flash-Next na 2×5090). Kwantyzowane KV celu (8-bit) zabiera 0.2–0.3 przyjętego draftu na rundę: kod 1.566 → 1.771, proza 1.547 → 1.833 przy KV FP16; najmocniej na najgłębszej pozycji (0.33 vs 0.44). Precyzja KV samego draftu (Q8 vs FP16) nic nie zmienia.
  - Dla nas to wyjaśnienie części luki akceptacji (KV q4_0). Zmiana KV celu to jednak zmiana kwantu, więc **zaparkowane** (§4).
- **FrostDFlash** (ModelScope cicalooo, 10-28). DFlash2 z mieszanym kwantem i wariantem d2t 32k dla tej samej rodziny Uncensored. Autor: akceptacja 0.517 przy n=3 na 5090. Gorzej niż nasze MTP, nie zmieniamy.
- Reddit r/LocalLLaMA (październik–listopad: wątki 16 GB/24 GB z MTP n=2–3, sudoingX/qwen38-mtp). Same konfiguracje flag, nic poza 63d §4 (n zależne od karty).

### 1.4 Blogi AMD ROCm

- **SSD na MI300X** (rocm.blogs.amd.com, 2026-05-29; arXiv 2603.03251). Spekulacja spekulacji: drafter na osobnym GPU liczy z wyprzedzeniem drafty dla kilku możliwych wyników weryfikacji. Liczby autorów: TP=4 1.64× nad SD. **Nie dla nas** (wymaga drugiego urządzenia). Jednokartowy odpowiednik („d1 draftu w grafie weryfikacji”) to znane 18 #11 i plan #11.
- Megakernele MI355X i Hyperloom: znane (66c, 13).

### 1.5 HN / X

- X @li_kunjun 2026-11-04 (SpecPilot) i @lhyTHU 2026-11-04 (Adversarial Speculative Reasoning): treść jak w artykułach.
- HN: wątki o MTP w llama.cpp (item 48025248) bez nowych technik.

## 2. Nasze analizy offline (CPU, ten raport)

### 2.1 Drzewo Gumbo na sprzężonym łańcuchu: rodzeństwo z luki Gumbela (`68b-skrypty/gumbo_sim.py`)

Dane, estymator i model kosztu jak w 24s:
- 57 odpowiedzi celu Q4, T=1, top-k 20 / top-p 0.95 / min-p 0.05, rozumowanie low, 36 270 startów;
- 64 próbki szumu a posteriori na pozycję;
- 27.6 ms przy 5 wierszach, +0.85 ms za wiersz.

Polityka: łańcuch-4, a na głębokości k liść-rodzeństwo (2. kandydat po zaburzonym wyniku), gdy luka 1.–2. < τ. Decyzja zapada przy drafcie, przed weryfikacją. Kontrola: sprzężony łańcuch-4 daje 2.5887 tok/krok na prozie, 24s miał 2.5866.

| zestaw | najlepsze τ | wiersze | Δ tok/krok | netto t/s przy 0.85 ms/wiersz | przy 0.57 | przy 0.40 |
|---|---|---|---|---|---|---|
| wszystko (36 270) | 1.5–2.0 | 6.2–6.5 | +5.4…6.2% | **+1.57%** | +3.06% | +3.99% |
| en-czat | 2.0 | 6.49 | +7.1% | +2.41% | +3.91% | +4.84% |
| proza (pl+en) | 1.5–2.0 | 6.3–6.6 | +5.8…6.6% | +1.57% | +3.18% | +4.19% |

Werdykt: **przy dzisiejszym koszcie wiersza poniżej progu +3%.** Wrócić, gdy wiersz 5→8 spadnie do ≤ 0.57 ms (24k #1: kernel 9–16 kolumn). Koszt implementacji pozostaje 1–2 tygodnie (maska przodków w `kvq`, stan GDN wg rodzica).

### 2.2 Głębokość MTP z luki Gumbela w bieżącym kroku (`68b-skrypty/gap_depth.py`)

Przy sprzężeniu szum pozycji t jest kluczowany i znany w chwili draftu, więc luka między dwoma najlepszymi zaburzonymi wynikami draftu jest pewnością, którą da się policzyć przed weryfikacją. Pomysł był w 52 TL;DR 3, ale bez liczb. Polityka: draftuj do głębokości dmin, potem kontynuuj, dopóki luka ≥ τ (maks. 5). Gdy po filtrach zostaje jeden kandydat, luka = ∞. Głębokości są niezależne przy danej ścieżce, więc próbki szumu są parowane po głębokościach.

| zestaw | A: wczesne wyjście z łańcucha (−1.6 ms/poziom = przejście MTP + wiersz) | B: łańcuch zawsze 5 przejść, skraca się tylko weryfikacja |
|---|---|---|
| wszystko | **+3.90%** (2..5, τ=2, śr. głębokość 3.31) | +0.07% |
| en-czat | +2.87% (2..5, τ=1.5–2) | ≤ 0 |
| pl-czat | +4.84% (2..5, τ=2) | +1.60% |
| en-proza / pl-proza | +3.10% / +4.28% | ≤ 0 |

Porównanie: kontroler z historii w 24q dał w symulacji +2.6…3.1% na czacie. Luka Gumbela daje podobnie albo lepiej, a decyduje z bieżącego kroku. **Warunek: wczesne wyjście w grafie łańcucha draftu pod PM4** (dziś jeden graf `draft_greedy_chain` liczy n przejść; 58 §1). Bez tego zysk znika (kolumna B).

### 2.3 Prawdziwa sesja agentowa omp z 2026-11-06 (`68b-skrypty/suffix_cov.py`)

Sesja na `Qwen3.8-27B-Uncensored-Q4_K_M.gguf`, 101 odpowiedzi asystenta, 89 017 tokenów słownych wyjścia (proxy: regex, nie BPE). Treść sesji nie jest publikowana, tylko agregaty.

| kategoria wyjścia | udział | przewidziane lookupem z sesji (3-gram) | tylko z korpusu globalnego | ogon > 4 (poza MTP-4): sesja / tylko globalny |
|---|---|---|---|---|
| myślenie | 59.5% | 21.5% | 4.3% | 4.1% / 0.0% |
| `write` (zawartość plików) | 14.2% | 39.4% | 6.5% | 11.6% / 0.2% |
| `edit` (`old_string`/`new_string`) | 11.2% | 72.7% | 1.1% | 29.8% / 0.0% |
| `bash` | 10.7% | 48.8% | 5.4% | 15.4% / 0.2% |
| tekst odpowiedzi | 4.1% | 17.0% | 2.2% | 1.8% / 0.1% |
| **razem** | 100% | 32.5% | 4.3% | **9.1% / 0.1%** |

Wnioski:
- (a) Korpus globalny (400 wcześniejszych sesji, 49.8 M tokenów) trafia głównie w krótkie frazy, które MTP i tak łapie (P(MTP | lookup) = 0.97, `lekcja-mtp-juz-kopiuje`). W ogonie dokłada 0.1%, więc **18 #6 / AgSpec: kill.** Ograniczenie: wcześniejsze sesje to głównie inne modele i inne zadania.
- (b) Format emisji nie psuje lookupu. Szablon Qwen3.8 ma surowe parametry `<parameter=…>` (metadane GGUF `tokenizer.chat_template`), a edycja omp to surowy tekst. **Kill.**
- (c) Prawie 60% wyjścia to myślenie, więc liczy się akceptacja MTP na rozumowaniu, a nie lookup. Tę akceptację wspiera §2.2.

## 3. Pomysły testowalne (bezstratne)

| # | pomysł | NOWE / znane | oczekiwany zysk u nas i dlaczego | wysiłek | dokładny test na naszym boxie | kill | ryzyko |
|---|---|---|---|---|---|---|---|
| 1 | **Głębokość MTP z luki Gumbela w bieżącym kroku**, z wczesnym wyjściem z łańcucha draftu (dmin=2, dmax=5, τ≈2) | częściowo NOWE (idea w 52, kontroler z historii w 24q, liczby nowe §2.2) | sym. A: +3.9% (wszystko), en-czat +2.9%, pl-czat +4.8%. Sesja agentowa +2…3% `[INFERENCE]`, bo 60% wyjścia to myślenie z akceptacją bliską czatu. Bez wczesnego wyjścia ~0 | 3–5 d: luka liczona w op `GUMBEL_MAX` łańcucha; wyjście jako osobne grafy przejść albo warunek PM4; grafy weryfikacji per szerokość już są w cache (24k) | (1) `spec_sweep.sh "LLAMA_SPEC_DEPTH_GAP=0" "LLAMA_SPEC_DEPTH_GAP=2"` (nowy przełącznik do dodania, domyślnie 0), `--temps 1.0 --seeds 1..8`, 6 promptów, ABBA; (2) `long_ctx_bench.py` 1.7k/94k/199k; (3) bramka #2 + KLD; (4) ms/krok draftu w rocprofv3 (czy wyjście nie dodaje luk hosta) | spec_sweep T=1 < +1.5% albo sesja agentowa (replay) < +1%; token forcing ponad progiem | wczesne wyjście pod PM4 replay; md5 zmienia się z konstrukcji (inna szerokość weryfikacji) |
| 2 | **Bramka „token forcing” (SpecPilot) dla zmian polityki draftu** w miejsce „md5 = topka” | **NOWE (metoda)** | 0% sama; odblokowuje #1, 24q i DRAFT_N per klasa. Ogon W16 już dziś zmienia szerokość weryfikacji zależnie od tekstu, więc „różna szerokość” to klasa kolejności floatów, dopuszczona regułą z 63 | 1 d: skrypt teacher-forced (wyjście greedy kandydata → logity referencji z `llama-perplexity`/`llama-eval-callback` z FP32 head), wskaźnik niezgodności + zdarzenia o marginesie > 2δ | kalibracja: topka vs topka (szum), DRAFT_N=5 (bezstratne) i wstrzyknięty bias logitu (wadliwe) na 6 promptach × 2k tokenów T=0 | bramka nie rozdziela wadliwego od bezstratnego | decyzja użytkownika o zmianie bramki md5 → token forcing + KLD |
| 3 | **GDN weryfikacji w formie chunkwise/WY w fp32** (rozwiązanie trójkątne w×w, czynniki (z,k,g), bez materializacji stanów; HybridSpec §3.4, SpecPilot §4.2) | częściowo NOWE (ReplaySSM i lag mamy; „chunked GDN” zaparkowane w 66 tylko w wariancie bf16; gdn-fast DPP wyszedł w szumie) | `gdn` 0.715 ms/krok przy podłodze ~0.16 ms (burst_decomp, verify) → −0.3…0.45 ms = **+1.1…1.7%** na każdym kontekście `[SZACUNEK]`; dodatkowo tańszy wiersz dla #1 i drzew | 3–5 d (kernel HIP, WMMA bf16×3 albo fp32 FMA) | `test-backend-ops perf -o GATED_DELTA_NET` (n_tokens 5/8/16, kształt Qwen) vs dziś; rocprofv3 kroku weryfikacji; `spec_sweep` ABBA; KLD (`llama-perplexity --kl-divergence`) i md5 plain | kernel < 1.5× szybszy albo e2e < +0.7%; KLD > szum | numeryka (kolejność sum), stan w VGPR (plan #21) |
| 4 | **Drzewo Gumbo na sprzężonym łańcuchu** (rodzeństwo z luki Gumbela) | częściowo znane (24s statyczne, 66d C) | sym.: +1.4…1.6% (wszystko), +2.4% en-czat przy 0.85 ms/wiersz; +3.1% przy 0.57; +4.0% przy 0.40 | 1–2 tyg. | najpierw tylko koszt wiersza: `llama-bench -p 5,6,7,8 -n 0` i rocprofv3; drzewo dopiero przy ≤ 0.57 ms | **dziś kill** (< +3%) | maska przodków w `kvq`, stan GDN wg rodzica |
| 5 | Dinkelbach + kalibrowana akceptacja jako reguła wyboru głębokości (HybridSpec §3.3) | NOWE (reguła); znana klasa (0039, EAGLE-4 harness w 52) | wliczone w #1: τ dobierane jedną regułą „G − ρ·C” zamiast siatki | 0.5 d (offline na danych §2.2) | `gap_depth.py` z regułą Dinkelbacha vs siatka τ | < siatka τ | brak |
| 6 | Globalny cache sufiksów (18 #6, AgSpec) | znane | **zmierzone: 0.1% tokenów w ogonie** (§2.3) | — | zrobione (`suffix_cov.py`) | **kill** | — |
| 7 | Lookup w formacie emisji (AgSpec) | NOWE | 0: parametry XML Qwen3.8 i edycje omp są surowe (§2.3) | — | zrobione | **kill** | — |
| 8 | Douczenie głowicy MTP nowymi stratami (WTV, VAT, SpecOPD) | znane (plan #19, 40) | 0…+5% `[INFERENCE]`; rwmacy v8: parytet na ruchu agentowym | wysoki, $ | jak 40: lustro offline E0 + agent replay, potem spec_sweep | lustro < +3% tok/krok | wynajem GPU, licencja danych |

Kolejność: #2 (1 d CPU) → #5 offline (0.5 d) → #1 (kod, potem 30–40 min GPU) → #3 równolegle z planem #21. #4 czeka na tańszy wiersz.

## 4. Zaparkowane (stratne, bez rankingu)

| pomysł | źródło | dlaczego odpada | liczby (informacyjnie) |
|---|---|---|---|
| Nucleus Speculative Decoding (akceptuj, gdy token w jądrze celu) | arXiv 2610.07822 (2026-10-06) | TV na krok = nadmiar draftu w jądrze; rozkład zmieniony | do 3.15× nad SD (autorzy, matematyka/kod) |
| Rozluźniona weryfikacja (cała klasa) | arXiv 2610.23818 (2026-10-16) | dowód przeciw: ×1.34 akceptacji, ale ×1.54 dłuższe odpowiedzi (rozumowanie się wydłuża) | 12 par cel-drafter |
| Weryfikacja dwupoziomowa (TLV) i W12 | SpecPilot | TLV jest bezstratne, ale wymaga drugiej kopii wag celu (VRAM); W12 dotyczy BF16. Wpis tutaj tylko jako „nie da się u nas bez zmiany kwantu” | 10.87× (autorzy) |
| KV celu w wyższej precyzji dla akceptacji MTP | adrienbrault R572 (2026-09-19) | zmiana kwantu KV (reguła 2026-11-05) | +0.2…0.3 przyjętego draftu na rundę przy KV FP16 vs 8-bit |
| GDN chunkwise w bf16 (wariant TokenSpeed) | 66b §3.8 | numeryka bf16; wariant fp32 to #3 w §3 | — |

## 5. Źródła (z datami)

Prace (arXiv, daty v1):
- SpecPilot https://arxiv.org/abs/2611.02501 (2026-11-02); kod https://github.com/StargazerX0/SpecPilot; omówienie https://sysnote.net/news/specpilot-a-claude-code-agent-pushed-speculative-decoding-to-10-87-over-autoregr (2026-11-05).
- HybridSpec https://arxiv.org/abs/2611.04055 (2026-11-02).
- DLoop https://arxiv.org/abs/2610.07659 (2026-10-06, v2 10-21).
- Gumbo https://neurips.cc/virtual/2026/poster/150279 (NeurIPS 2026); Gumbel-max list sampling https://arxiv.org/abs/2506.05632.
- ReplaySSM https://arxiv.org/abs/2610.13778 (2026-10-09); https://dao-lab.ai/blog/2026/replayssm/ ; vLLM PR https://github.com/vllm-project/vllm/pull/66318 (2026-11-06).
- TreeWY https://arxiv.org/abs/2608.20961 (2026-08-21); Bole https://arxiv.org/abs/2608.01651 (2026-08-03).
- AgSpec https://arxiv.org/abs/2610.01108 (2026-10-01).
- Hybrid Spark https://arxiv.org/abs/2611.05611 (2026-11-03).
- SpecOPD https://arxiv.org/abs/2611.02846 (2026-11-02); Acceptance-Aware Training https://arxiv.org/abs/2609.24150 (2026-09-21); VAT https://arxiv.org/abs/2608.30135 (2026-08-31).
- One Call Ahead https://arxiv.org/abs/2610.33379 (2026-10-24); Beneath the Tokens https://arxiv.org/abs/2609.35188 (2026-09-28); Adversarial Speculative Reasoning https://arxiv.org/abs/2611.05345 (2026-11-03); RASS https://arxiv.org/abs/2610.02251 (2026-09-30).
- Nucleus SD https://arxiv.org/abs/2610.07822 (2026-10-06); Acceptance Is Not Speed https://arxiv.org/abs/2610.23818 (2026-10-16).

GitHub:
- llama.cpp #31750 https://github.com/ggml-org/llama.cpp/pull/31750 (2026-11-05); #30141 https://github.com/ggml-org/llama.cpp/pull/30141 (scalony 2026-11-03); #31037 https://github.com/ggml-org/llama.cpp/pull/31037 (2026-10-23); #30663 https://github.com/ggml-org/llama.cpp/pull/30663 (2026-10-16 … 10-28); lista MTP https://github.com/ggml-org/llama.cpp/pulls?q=is%3Apr+MTP+in%3Atitle (stan 2026-11-07).
- PrismML #320 https://github.com/PrismML-Eng/llama.cpp/pull/320 (2026-10-05 … 10-27).
- R572 https://github.com/adrienbrault/qwen3.8-flash-next-2x-rtx5090/blob/main/bench/results/r572-mtp-acceptance.md (2026-09-19).

Hugging Face / inne:
- https://huggingface.co/rwmacy/qwen3.8-27b-mtp-head-v8-b70 (commit `c18ff99`).
- https://modelscope.cn/models/cicalooo/Qwen3.8-27B-FrostDFlash-GGUF (2026-10-28).
- https://freenode.net/article/llama-cpp-skips-draft-probability-floor-for-faster-mtp-and-dflash2 (2026-10-28).
- https://rocm.blogs.amd.com/artificial-intelligence/ssd_mi300x/README.html (2026-05-29).

Nasze pliki:
- `~/qwen-opt/xtxroadmap/burst_decomp.txt` (koszt `gdn` 0.715 ms w kroku weryfikacji);
- `product/research/24s-drzewa/tree_ceiling.py:75-113` (estymator sprzężony);
- `~/wt/topka-q63/src/llama-context.cpp:308-325` (K/V-only catch-up);
- `wiki/REKORDY.md:154-158`;
- sesja omp `~/.omp/agent/sessions/-tmp/2026-11-06T18-01-51-894Z_…jsonl` (tylko agregaty);
- skrypty i wyniki w `68b-skrypty/`.

### Wiersze do `wiki/ZRODLA.md` (dla Main; wiki nie edytowałem)

| Źródło | wersja / data | raport | werdykt | liczba | przy następnym podejściu |
|---|---|---|---|---|---|
| SpecPilot (arXiv 2611.02501, github StargazerX0/SpecPilot) | v1 2026-11-02; sysnote 11-05 | R68b §1.1 | Bierzemy bramkę token forcing; W12/TLV nie dla Q4 i 24 GB; certyfikowany head = 36 §3 | 10.87× vs stock, 1.84× vs DDTree (autorzy) | wydanie pętli i scorera token forcing |
| HybridSpec (arXiv 2611.04055) | v1 2026-11-02 | R68b §1.1 | Reguła Dinkelbacha + GDN chunkwise fp32; korekta MoE nie dotyczy | 1.30–1.33× vs DFlash (A100, MoE) | kod kerneli GDN |
| DLoop (arXiv 2610.07659, naver-ai/DLoop) | v2 2026-10-21 | R68b §1.1 | = adaptacyjna głębokość (24q) | +5…41% (autorzy) | kod |
| Gumbo (NeurIPS 2026, OpenReview jLWQiUQcDp) + Gumbel list sampling (2506.05632) | poster 2026-12 | R68b §1.1, §2.1 | Drzewo na sprzężonym łańcuchu: sym. +1.6% przy 0.85 ms/wiersz → czekać | +26.7% vs sampler EAGLE-3 | koszt wiersza ≤ 0.57 ms |
| ReplaySSM (arXiv 2610.13778, dao-lab blog) | v1 2026-10-09 | R68b §1.1 | Mamy (lag/replay); zostaje output-only GDN | 1.20–1.47× przy batchu 256 | — |
| AgSpec (arXiv 2610.01108) | v2 2026-10-06 | R68b §1.1, §2.3 | Korpus globalny i format emisji: kill na naszej sesji | ogon +0.1% (nasze) | — |
| Hybrid Spark (arXiv 2611.05611) | v1 2026-11-03 | R68b §1.1 | = ogon W16 / „zastąp gdy pewny” | 1.10–1.62× edycja przy batchu 4 | — |
| SpecOPD / WTV / VAT (2611.02846, 2609.24150, 2608.30135) | 2026-08-31 … 11-02 | R68b §1.1 | Plan #19 ($) | AL +11…41% (draftery) | wynik na głowicy MTP 27B |
| rwmacy/qwen3.8-27b-mtp-head-v8-b70 | `c18ff99` | R68b §1.3 | Retrening głowicy MTP: parytet na ruchu agentowym | L 3.01 vs 3.00 | — |
| adrienbrault R572 (MTP vs KV quant) | 2026-09-19 | R68b §1.3 | KV celu 8-bit −0.2…0.3 draftu/rundę; zaparkowane (kwant) | 1.566 → 1.771 (kod) | — |
| llama.cpp #31750, #30141, #31037, #30663; PrismML #320 | 2026-10-05 … 11-05 | R68b §1.2 | Mamy albo nie dotyczy | #31750 −2.19% ms/krok (W7800) | — |
| FrostDFlash (ModelScope cicalooo) | 2026-10-28 | R68b §1.3 | Gorszy od MTP | akceptacja 0.517 przy n=3 | — |
| Nucleus SD (2610.07822), Acceptance Is Not Speed (2610.23818) | 2026-10-06, 10-16 | R68b §4 | Stratne / dowód przeciw stratnym | ×1.54 dłuższe odpowiedzi | — |
| SSD na MI300X (ROCm blog, arXiv 2603.03251) | 2026-05-29 | R68b §1.4 | Wymaga 2. urządzenia | 1.64× vs SD (TP=4) | — |
