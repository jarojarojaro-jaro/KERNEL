# 10. Trening i post-training dla produktu: drafter, modele decyzyjne, kwanty, SFT

Stan na 2026-10-16. To raport tylko z badań: web plus pliki lokalne. Nie użyto GPU, nie wydano pieniędzy.

Oznaczenia:
- `[SZACUNEK]`: mój wniosek lub szacunek, niezmierzony.
- `[L]`: fakt sprawdzony lokalnie, w repo lub w notatkach.

Ceny Vast pochodzą z publicznego feedu z 2026-10-16 00:30 UTC (mediana bieżąca on-demand, w nawiasie minimum) ([vast-feed]):

| GPU | Cena Vast |
|---|---|
| RTX 3090 24 GB | $0.21/h (min $0.08) |
| RTX 4090 | $0.51 |
| RTX 5090 32 GB | $0.67 |
| RTX A6000 48 GB | $0.40 |
| L40S 48 GB | $0.69 |
| A100 80 GB PCIe | $0.73 (min $0.47) |
| A100 80 GB SXM | $0.80 (min $0.47) |
| H100 SXM | $3.07 (min $1.73; mediana z 15.10 to $2.20) |
| H200 | $4.00 |

H100 jest dziś wyraźnie droższe, niż sugerował raport 05. Do treningu najbardziej opłaca się **A100 80 GB lub A6000/L40S 48 GB**.

---

## TL;DR

1. **Najlepiej pasuje do obietnicy produktu trening draftera, nie modelu.** Najtańsza ścieżka to fine-tune własnej głowicy MTP Qwen3.8-27B przez **self-distillation na naszym trunku Q4**, z danymi PL i kodu.
   - Wynik jest bezstratny: target weryfikuje każdy token, wagi modelu zostają nietknięte, zmienia się tylko `blk.64.*`.
   - Dowody: Red Hat podniósł τ o +6.8% na natywnym MTP Qwen3-Next ([redhat-fastmtp]); FastMTP podniósł τ z 1.83 do 2.73 na MiMo, który nie był trenowany rekurencyjnie ([fastmtp]); TensorFold pokazał, że drafter trenowany na niekwantyzowanym modelu traci na kwantyzowanym trunku (4.2 → 3.0–3.3 tok/rundę) ([L] `tensorfold/qwen27.md:378`).
   - Oczekiwany zysk: **+10–17% tok/krok** na czacie i prozie PL `[SZACUNEK z training.md §1.6]`.
   - Koszt: **$0** na naszym 7900 XTX albo **~$3–4** na Vast (A6000 48 GB, ~8 h).
2. **EAGLE-3 i DFlash z treningu od zera: nie teraz.**
   - Natywny MTP Qwen3.8 ma τ 3.74 na MT-Bench. Publiczny EAGLE-3 dla tej rodziny ma τ 2.2–2.4.
   - TensorFold trenował draftery od zera na wynajętych H200 i dostał 3.8–5.1% akceptacji pierwszego tokenu. Fine-tune DFlash2 na 372k tokenów nie dał nic ([L] `tensorfold/qwen27.md:399-400`).
   - Koszt wynosi dziesiątki do setek GPU-h H100.
3. **Model decyzyjny w pętli spekulacji jest tani i robi się go na CPU, ale zysk jest mały i niepewny.** Chodzi o malutką regresję logistyczną lub MLP, która decyduje „draftuj dalej / stop / ile weryfikować”.
   - Literatura: SpecDec++ +7–11% nad stałym K ([specdecpp]), DISCO +10% nad najlepszym stałym SL ([disco]).
   - U nas heurystyka T2 dała **0%** ([L] NOTES:310-317). Wycena głębokości kosztem w TensorFold dała +6–7%, a ich wyrocznia +25–35% ([L] `tensorfold/spec-host.md:78`).
   - Oczekujemy **+0–5%** `[SZACUNEK]`. Najpierw liczymy wyrocznię w symulatorze offline z logów (za $0), dopiero potem piszemy C++.
4. **„Laya” i podobne typed-decision encodery (300–400M) nie nadają się do decyzji per-token.** Kosztują 7–14 ms (M3 Max), 33 ms (T4) i 193–464 ms na CPU, a budżet na decyzję to ≪0.1 ms. Krok Qwena trwa 27.8 ms, token LFM 3.4 ms.
   - Mają sens **raz na żądanie**: router myślenia, wybór modelu, wybór profilu spekulacji, routing narzędzi.
   - Najtańszy router to **liniowa sonda na hidden state z prefill naszego modelu** (prefill i tak liczymy), a nie osobny encoder `[SZACUNEK]`.
5. **QAT i niskobitowe odtwarzanie** (Bonsai, GSQ-RCO, Saluki) **zmieniają wyjścia**, więc to inna obietnica („Tryb maksymalny”). GSQ umie poprawić publiczny GGUF K-quant w tym samym formacie ([gsq]). Pilot PL-kalibrowanego Q2/Q3 to stretch: A100 przez ~8–20 h `[SZACUNEK]`.
6. **SFT/LoRA (PL) i RL/GRPO: tanio, ale poza obietnicą „ten sam model”.**
   - Qwen3.8-27B QLoRA mieści się w 24 GB, LoRA potrzebuje >36 GB ([unsloth-q38]).
   - Każdy SFT trunku psuje kalibrację MTP, więc musi go poprawić nasz pipeline MTP `[SZACUNEK]`.
7. **Ścieżka nauki:**
   1. <$1: MTP fine-tune Qwen3.5-0.8B przez speculators na 3090, plus QLoRA Unsloth na Qwen3.5-2B. Do tego zbieranie logów spekulacji i symulator na CPU.
   2. ~$3–4 albo $0 lokalnie: pilot MTP-PL dla Qwen3.8-27B na Q4.
   3. Stretch, $5–16: głowice MTP per kwant (Saluki IQ2, Q3 16 GB) i/lub głowica pod TV/rejection przy T=1.

---

## 1. Drafter do spekulacji (główny kandydat)

### 1.1 Co llama.cpp dziś uruchamia

Upstream (`docs/speculative.md` na master) ma typy:
- `draft-simple`, `draft-eagle3`, `draft-mtp`, `draft-dflash`, `draft-dspark`;
- `ngram-simple`, `ngram-map-k`, `ngram-map-k4v`, `ngram-mod`, `ngram-cache`.

Źródło: [llamacpp-spec].

Nasz fork (`~/llama-master`, f61994f58) ma tę samą listę ([L] `common/common.h:175-186`, `common/speculative.cpp:74-83`). Dodatkowo:
- `--spec-draft-vocab` i `--spec-draft-vocab-n` (zredukowany słownik draftu);
- `--spec-draft-head-type` / `--spec-mtp-type` (draft w IQ4_XS);
- `--spec-draft-adaptive` (T2, wycena głębokości kosztem).

[L] `common/arg.cpp:4239-4256`, `common/speculative.cpp:1391-1500`.

| Rodzaj draftera | llama.cpp upstream | Nasz fork | Uwagi |
|---|---|---|---|
| MTP (natywna głowica) | tak (`draft-mtp`) | tak + vocab 64k, IQ4_XS, jeden graf, adaptacja | rejection sampling przy T>0 działa ([L] NOTES:144) |
| EAGLE-3 | tak (`draft-eagle3`, konwerter dla formatów SpecForge i vLLM/AngelSlim, d2t) | tak; ekstrakcja warstw w `qwen35.cpp`, `lfm2.cpp`, `lfm2moe.cpp` ([L] grep `layer_inp`) | potrzebuje 3 warstw docelowych |
| DFlash / DFlash2 | tak (`draft-dflash`, #22105) | tak | **weryfikacja tylko przez dopasowanie, bez rejection** → słabe przy T=1 ([L] NOTES:158) |
| DSpark | tak (#25173) | tak | łańcuch Markowa greedy w grafie |
| Medusa / Hydra | **nie** | nie | wymaga drzew; zastąpione przez EAGLE/MTP |
| Drzewa (EAGLE-2, Medusa) | **nie** w serwerze; jest tylko stary `examples/speculative` z `p_split` | nie | dla GDN potrzebne stany per gałąź (§6b) |

### 1.2 Porównanie kierunków (target Qwen3.8-27B)

| Kierunek | Oczekiwany zysk akceptacji (dowody) | Sprzęt i czas dla 27B | Dane | Dojrzałość narzędzi | Uruchomi się w llama.cpp? |
|---|---|---|---|---|---|
| **MTP fine-tune / self-distill** | Red Hat: τ 3.09 → 3.30 (+6.8%), zysk rośnie z głębokością (+0.015/+0.05/+0.13 warunkowo) ([redhat-fastmtp]). FastMTP: 1.83 → 2.73 średnio (od głowicy nietrenowanej rekurencyjnie) ([fastmtp]). Nasz model: **+10–17%** chat/PL `[SZACUNEK]` | 0.42 B trenowalnych: pełny Adam ≈ 7 GB, razem 10–12 GB ([L] training.md §1.4). **24 GB**: trunk Q4 (llama.cpp) i trening na zmianę. **48 GB**: oba naraz. **80 GB**: trunk bf16 w vLLM + speculators. Pilot 2 M tokenów: ~3–6 GPU-h; pełny 12 M: ~15–25 GPU-h `[SZACUNEK]` | 2–15 M tokenów odpowiedzi wygenerowanych przez *nasz* target (PL 40%, EN 35%, kod 25%) | speculators ma MTP: convert → train → stitch, β=0.6 ([spec-mtp]). SpecForge: MTP przez `merge_mtp_to_base.py` ([specforge]). Oba zakładają target bf16 w vLLM/SGLang | **tak**: łatka bajtów `blk.64.*` w tym samym GGUF, zero zmian w C++ ([L] training.md §1.5 p.7) |
| EAGLE-3 od zera | paper: do 6.5× i ~1.4× nad EAGLE-2 ([eagle3]). Dla tej rodziny publiczny EAGLE-3 ma τ 2.2–2.4 vs MTP 3.74 ([L] training.md §2) | ~0.6–0.8 B + head 32k. Cechy 31 KB/token. 50 M+ tokenów: 30–60 GPU-h H100/A100 `[SZACUNEK]` ≈ $25–50 na A100 | dziesiątki mln tokenów, regenerowane | najdojrzalsze: SpecForge, speculators, oficjalne repo SafeAILab/EAGLE | tak (`draft-eagle3`), ale **przegra z natywnym MTP** |
| DFlash / DFlash2 | DFlash2 MT-Bench 4.10 vs MTP 3.74 (T=1, z rejection, H200) ([L] drafters.md). U nas greedy przegrywa (58 vs 60 t/s) | 1.9 B: pełny Adam ~30 GB → **48/80 GB**. Od zera: 800 K próbek × 6 epok (paper); RedHat DSpark ~14 B tokenów → setki GPU-h | jw. | NeMo AutoModel ma recepty DFlash/DFlash2/Domino/JetSpec, cel m.in. `Qwen/Qwen3.8-27B` ([nemo-dflash]). Speculators: DFlash2 „experimental”, bo cel treningu nie jest publiczny ([spec-train]) | tak, ale bez rejection przy T>0; TensorFold: fine-tune 372k tokenów = 0 zysku |
| Medusa | Medusa-1 >2.2×, Medusa-2 2.3–3.6× (Medusa-2 zmienia backbone) ([medusa]) | małe głowice | jw. | stare, porzucone na rzecz EAGLE | **nie** (brak drzew i typu) |
| Własne dane (PL, kod, ślady agentów) | język i domena mają znaczenie: drafter per język ([yi-multilingual]); offline > online o 11–25%; logity > tokeny o 2–10%; syntetyczne prompty dają 80–93% korzyści prawdziwych ([domain-drafter]) | jw. | prompty z WildChat (`language=='Polish'`), oasst2 `pl`, aya PL, PLLuMIC; nasze logi tylko za zgodą | — | — |
| Zredukowany słownik draftu | u nas 64k: +7.5% ([L] NOTES:86-88); Strata: FR 0.51 → 0.60 akceptacji, +11% ([L] strata/spec-host) | CPU (liczenie częstości) | korpus docelowy | nasze `build_draft_vocab.py` | tak (fork) |

**Własne MTP, liczby lokalne.**

| Pomiar | Wynik |
|---|---|
| tok/krok, pooled po S2 | 3.06 → 3.01 ([L] NOTES:286) |
| długi kontekst | 3.31 / 2.98 ([L] NOTES:327) |
| MTP n=5, T=1, pl-proza / en-chat | 63.9 / 60.4 t/s; kod 80.5 t/s (przed późniejszymi łatkami) ([L] NOTES:154) |

PL i czat są wyraźnie słabsze od kodu. Tam jest zapas.

Spoza 64k pochodzi tylko 3.5% tokenów prozy PL ([L] NOTES:145), więc ograniczeniem jest jakość głowicy, nie słownik.

### 1.3 Pilot: MTP-PL dla Qwen3.8-27B (cel mierzalny)

- **Hipoteza:** fine-tune `blk.64.*` (FastMTP, rekurencja K=5, β 0.6–0.7, strata 0.9·TV + 0.1·CE na top-20 teachera) na hidden states z **naszego Q4_K_XL** podnosi warunkową akceptację na głębokościach 2–4.
- **Cele** (spec_sweep, 6 promptów × 3 seedy, n=4 i n=5, T=1 i T=0):
  - pl-proza: **≥ +10% tok/krok**;
  - en-chat: **≥ +5%**;
  - kod i technika: **≥ −2%** (bez regresji);
  - ms/krok bez zmian, bo typy kwantów są te same.
- **Bramka offline przed zapisem do GGUF:** na held-out 5% przewidywane tok/krok (1 + Σ Π a_j) rośnie o ≥ +5%, a nie spada na żadnej klasie.
- **Kroki** (szczegóły w [L] training.md §1.5):
  1. prompty;
  2. generacja `llama-server -np 8` z naszym samplerem;
  3. ekstraktor C++ (`llama_set_embeddings_nextn`, top-20 teachera);
  4. moduł PyTorch MTP z bramką parytetu ≤1e-2 do logitów llama.cpp;
  5. trening;
  6. ewaluacja offline;
  7. kwantyzacja do Q6_K/Q8_0 przez `ggml_quantize_chunk` i nadpisanie bajtów;
  8. spec_sweep ABBA.
- **Gdzie liczyć:**

  | Opcja | Sprzęt | Czas | Koszt |
  |---|---|---|---|
  | A | 7900 XTX (PyTorch-ROCm, na zmianę z ekstrakcją) | 6–8 h | **$0** |
  | B | Vast A6000 48 GB: llama.cpp CUDA Q4 (18 GB) i trening (12 GB) naraz | ~6–8 h | **≈ $3–4** z dyskiem `[SZACUNEK]` |
  | C (kontrola, opcjonalna) | speculators na trunku bf16, A100 80 GB | 6–8 h | ~$5–7 |

  Opcja C sprawdza, ile daje trening na Q4 vs bf16.

### 1.4 Gotowe, pretrenowane komponenty do douczania (HF, 2026-10-16)

| Model | Co jest | Gdzie |
|---|---|---|
| Qwen3.8-27B | natywny MTP (w GGUF); DFlash2 (z-lab/incoai); DSpark: RedHatAI (0.1 CE + 0.9 TV), RadixArk, DimInfer (trenowany na Q4_K_M); **brak EAGLE-3 i Medusy**; EAGLE-3 tylko dla Qwen3.6-27B (Dogacel/specdrift, PRISM-EAGLE3), co najwyżej jako ciepły start | [L] drafters.md |
| Qwen3.5-9B | natywny MTP (`unsloth/Qwen3.5-9B-MTP-GGUF`); DFlash (`z-lab/Qwen3.5-9B-DFlash` + wiele GGUF); EAGLE-3 (`yuyijiong/Qwen3.5-9B-Eagle3`, `dobriak/…`, `BLR2/…`) | HF API [hf-api] |
| Saluki 27B / GSQ-RCO | GGUF-y ISTA mają pliki alokacji z sufiksem `-mtp`. Istnieje `Kujira/Underdog-Saluki-27B-1.0-MTP-…-GGUF` | [gsq-rco], [hf-api] |
| Bonsai 27B (v1) | społeczny DSpark (`Danny-Dasilva/Ternary-Bonsai-27B-antidoom-DSpark`) | [hf-api] |
| LFM2.5-24B-A2B | **brak draftera**. Jest tylko DFlash dla LFM2.5-1.2B / VL-3B i zabawkowy `qtris123/lfm2-eagle3-head` | [hf-api] |
| Małe LM jako `draft-simple` | Qwen3.5-0.8B/2B/4B (ten sam słownik 248320): koszt ≈ MTP, akceptacja niższa ([L] drafters.md) | — |
| Predyktory akceptacji z papierów | SpecDec++ (głowica akceptacji dla Llama-2; kod publiczny), DISCO (klasyfikator dla par Intel), DynaSpec (meta-klasyfikatory słownika). **Wszystkie są per para modeli i nie przenoszą się.** Ale są małe, więc da się je odtworzyć na naszych logach na CPU | [specdecpp], [disco], [dynaspec] |

---

## 2. Model decyzyjny w pętli spekulacji („custom decision model”)

### 2.1 (a) Predyktor akceptacji i dynamiczna długość draftu

| Praca | Mechanizm | Wynik |
|---|---|---|
| SpecDec++ ([specdecpp]) | głowica akceptacji na drafterze; polityka progowa (z MDP) | 2.04× Alpaca (**+7.2%** nad zwykłym SD), GSM8K +9.4%, HumanEval +11.1% |
| DISCO ([disco]) | klasyfikator „draftuj dalej?” | **+10%** nad najlepszym stałym SL, tekst identyczny |
| AdaEAGLE ([adaeagle]) | Lightweight Draft Length Predictor | 1.62× nad AR, lepiej niż stała długość |
| BanditSpec ([banditspec]) | bandyta UCB/EXP3 wybiera konfigurację online, bez treningu | blisko wyroczni najlepszej konfiguracji |
| EAGLE-2 ([eagle2]) | pewność draftera ≈ akceptacja (dobrze skalibrowana) → dynamiczne drzewo | +20–40% nad EAGLE-1 |
| TensorFold ([L] tensorfold/spec-host.md:78-86, qwen27.md:369) | reguła głębokości wyceniana kosztem + kalibracja per głębokość | +6–7% (Nemotron); kalibracja wyników drzewa na ~1500 rundach: +6.5% zaakceptowanych; wyrocznia +25–35%. Iloczyn pewności zawyża akceptację ~2.5× |
| Strata DraftPolicy ([L] strata) | E[tok]/koszt z EMA; wybór lookup vs MTP | kod +6–11%, reszta 0 |
| **Nasz T2** ([L] NOTES:310-317) | segmenty łańcucha, kalibracja koszyków pewność × głębokość na żywo, tabela kosztów weryfikacji | **0%** (103.6 vs najlepsze stałe n 103.5); czat i proza −5 t/s względem n=4. Wyłączony |

**Granica zysku u nas (arytmetyka).** Głębokość kosztuje ~1.6 ms/poziom: 0.65 ms draftu i ~1 ms kolumny weryfikacji ([L] NOTES:309). Przy n=4 krok trwa ~28.9 ms i daje ~3.0 tok/krok, czyli średnio ~2 zaakceptowane z 4.
- Wyrocznia, która zatrzymuje się dokładnie na pierwszym odrzuceniu, oszczędza średnio ~2 poziomy ≈ 3.2 ms/krok, czyli **≤ +11%**.
- Gdy wszystko by przeszło, wyrocznia idzie głębiej (do 7). To daje razem rząd **+12–20%** `[SZACUNEK]`, zgodnie z +25–35% u TensorFold.
- Realna polityka łapie zwykle 20–40% wyroczni, czyli **+3–6%**.
- Zastrzeżenia:
  - zmiana szerokości weryfikacji bez cache grafu kosztuje 1.6 ms (T2 ma już graf per szerokość);
  - T2 pokazał, że łatwo nic nie zyskać.

**Czy wyjście zostaje bez zmian?** Target dalej weryfikuje każdy token, więc rozkład wyjścia jest ten sam. Bitowa identyczność przy T=0 zależy od row-invariance kerneli weryfikacji przy różnej szerokości. U nas zmiana draftów daje inny tekst przy remisach ([L] NOTES:287). Obietnica z PLAN §2 („te same odpowiedzi co tryb standardowy”) jest zachowana w sensie rozkładu.

#### Pipeline danych (całość na CPU, bez nowego GPU)

**Logowanie.** Nowy przełącznik, np. `LLAMA_SPEC_LOG=plik.bin`, w pętli `common/speculative.cpp` (MTP draft chain). Jeden rekord na **poziom draftu**, ~64 B binarnie:
- `req_id`, `step`, `n_past`, `depth k`, `n_max`, `T`;
- klasa promptu i język (z routera §3 albo z heurystyki);
- cechy draftu: p top-1 i top-2 po softmax top-10 (ten sam, który sampler draftu już liczy), entropia top-10, iloczyn pewności do k;
- kontekst: entropia i p top-1 targetu na ostatnim zaakceptowanym tokenie (z logitów weryfikacji), liczba zaakceptowanych w poprzednim kroku, EMA akceptacji z 8 kroków;
- czy istnieje dopasowanie n-gram i jak długie;
- klasa tokenu: spacja, interpunkcja, identyfikator, cyfra;
- **etykieta:** zaakceptowany (warunkowo na k−1 zaakceptowanych);
- czasy: draft ms, weryfikacja ms, szerokość.

Opcjonalnie wektor h z MTP (5120 × fp16 = 10 KB/poziom) do sondy liniowej. Robić tylko w labie, 1 M rekordów ≈ 10 GB.

Prywatność: token id to treść, więc logi zostają lokalne. Do chmury idą co najwyżej wagi modelu decyzyjnego albo liczby, zgodnie z L2 w PLAN §4.3.

**Zbieranie danych.**
- spec_sweep na stałym **n_max=7**, żeby widzieć etykiety do głębokości 7;
- 6 klas promptów × wiele seedów + nasze normalne użycie;
- ~200 k kroków w dzień pracy serwera.

**Dokładny symulator offline (bez kosztownej heurystyki).** Dla tekstu wygenerowanego greedy uruchamiamy MTP **teacher-forced z każdej pozycji** (prefill i 7 przejść MTP batchowanych przez API `llama_set_embeddings_nextn`). Dostajemy wtedy, dla każdej pozycji p, długość zgodności łańcucha draftu z kontynuacją targetu.

Replay dowolnej polityki:
- start w p;
- polityka wybiera w;
- tokeny = min(A_p, w) + 1;
- koszt = baza + draft(w) + kolumny(w) (+ kara za zmianę szerokości);
- p += tokeny.

Przy T=0 to jest dokładne. Przy T=1 przybliżone przez prawdopodobieństwa akceptacji. Koszt liczenia: jeden przebieg naszego GPU, $0.

**Trening (sklearn, CPU, sekundy–minuty):**
- regresja logistyczna per głębokość, ~16 cech;
- alternatywnie GBDT lub MLP 16→32→1;
- kalibracja izotoniczna;
- porównanie Brier i log-loss z iloczynem pewności oraz z koszykami T2.

**Polityka:** jak w T2 (cena kosztowa), tylko z `p_accept` z modelu zamiast z koszyków.

**Bramka:** w symulatorze ≥ +3% nad najlepszym stałym n **na każdej klasie** i ≥ 30% luki do wyroczni. Inaczej stop i wpis negatywny.

**Integracja w llama.cpp.** W `draft_adaptive()` zastępujemy `depth.calibrate(conf, c)` ([L] `speculative.cpp:2159-2184`) ewaluacją modelu. Wagi trzymamy w małym pliku albo w GGUF kv. To ~100 linii.

Koszt inferencji:

| Wariant | Koszt na decyzję |
|---|---|
| logreg na 16 cechach | ~16 FMA ≈ 10–20 ns |
| MLP 16→32→1 | ~600 FLOP, <1 µs |
| sonda na h (5120-dim) | jedna kolumna matvec w grafie draftu, ~µs |

Wszystkie ≪ 0.1 ms.

**Re-kalibracja per build i per GPU:** tabela kosztów kolumn i tak jest mierzona przy starcie (T2). Model p_accept zależy od głowicy, więc po treningu MTP (§1.3) trzeba go douczyć. To tanie.

**Wariant prostszy, prawdopodobnie zbierający większość zysku `[SZACUNEK]`: stałe n per klasa żądania.** Dane:
- Qwen n=4/5/6 daje średnio 102.7/103.0/103.5, ale czat preferuje n=4, a kod wyższe n;
- Uncensored: n=5 108.4, ale proza 96.5 → 89.3 ([L] NOTES:308, 317).

Wybór n na żądanie (kod / proza / PL) to **+1–3%** na ruchu mieszanym prawie za darmo. Taką decyzję podejmuje router z §3.

### 2.2 (b) Dynamiczne drzewa tokenów

- EAGLE-2 rozwija drzewo według pewności draftera ([eagle2]). C2T uczy klasyfikator przycinania drzewa ([c2t]).
- **llama.cpp nie weryfikuje drzew w serwerze.** Dla hybryd GDN gałęzie potrzebują osobnych stanów rekurencyjnych i historii conv. LumoTree (2026-09) opisuje taki serwer na DGX Spark ([lumotree]).
- Dowody dla naszego MTP są przeciw:
  - Strata: drugi kandydat MTP był celem w 0/14 odrzuceń ([L] strata/README §5);
  - TensorFold: drzewa wygrywają dla DFlash2 (4.0–6.4 tok/rundę przy 12 wierszach), ale nie dla łańcuchów MTP.
- Werdykt: **nie teraz**. Bardzo duży koszt C++, zysk tylko przy innym drafterze.

### 2.3 (c) Uczony słownik draftu per kontekst

- DynaSpec: meta-klasyfikatory wybierają klastry tokenów per kontekst. Odzyskuje 98.4% AL pełnego słownika wobec 93.6% dla stałej listy; do 2.23× vs 1.91× na danych z rzadkimi tokenami ([dynaspec]).
- Podobnie NanoSpec i SpecVocab ([nanospec], [specvocab]).
- U nas tylko 3.5% tokenów prozy PL leży poza 64k. Górna granica zysku dla PL to więc rząd **+2–4% tok/krok** `[SZACUNEK]`.
- Tańsza wersja: **2–3 warianty 64k wybierane per żądanie po języku** (PL / EN+kod / CJK). Dowód: Strata `--draft-vocab fr` dał +11% dla francuskiego przy 23.8% braków, a CJK dał +15–38%.
- Dane to zliczenia częstości z logów (CPU).
- Koszt: +~180 MiB VRAM na wariant, jeśli trzymamy kilka naraz ([L] NOTES:237). Lepiej przebudowywać przy zmianie języka.
- Priorytet niski, zysk głównie dla języków spoza EN/PL.

### 2.4 (d) Uczone samplery i polityki dekodowania, które ZMIENIAJĄ wyjście

**Inna obietnica produktu.**

Przykłady:
- temperatura adaptowana entropią;
- contrastive decoding;
- typical acceptance z Medusy;
- verifier-guided decoding;
- routing myślenia (§3).

Mogą przyspieszyć albo poprawić jakość, ale łamią „te same odpowiedzi”. Tylko jako jawny tryb opt-in z KLD i ewaluacją zadaniową. Nie mieszać z L1–L3.

---

## 3. Modele decyzyjne na poziomie żądania („laya” i podobne)

### 3.1 Czym jest „laya”

- **Laya** (Convai Innovations, Apache-2.0): nieautoregresywny „System 1” decision model. Wejście to stan plus pytania typowane (`choice` / `score` / `noul` = P(true)). Wyjście to skalibrowane prawdopodobieństwa w jednym przejściu ([laya]).
  - Checkpointy: ModernBERT-large 421M (EN, 512 tok.), mmBERT-base 322M (100+ języków, 1024–8192 tok.), typed-decisions 421M.
  - Trening: RLCD, czyli REINFORCE z bazą grupową i regułami właściwego punktowania.
  - Czasy: ~33 ms na T4, **193–464 ms na CPU**.
  - Fine-tune: notebook na Kaggle 2×T4. Typed-decisions 0.766 vs 0.362 dla bazy na tym samym benchmarku.
- **laya-mlx** (mizorewww, Apache-2.0) to port MLX: **13.4 ms** (421M) i **7.4 ms** (322M) P50 na M3 Max ([laya-mlx]).
- Inne „decision models”:
  - Liquid **d1** (3B, na LFM2.5-VL-3B) ([ollama-d1]);
  - NVIDIA `prompt-task-and-complexity-classifier` (DeBERTa, 184M, licencja `other` = NVIDIA Open Model License) ([nv-ptcc]);
  - **Arch-Router-1.5B** (Katanemo, licencja Katanemo Research/Community) ([arch-router]);
  - routery **RouteLLM** (matrix factorization, BERT, causal-LLM; Apache-2.0; ponad 2× mniejszy koszt bez spadku jakości) ([routellm]);
  - **mmBERT** small/base (MIT, 1800+ języków, ONNX gotowe) ([mmbert]);
  - **Polish ModernBERT** (2026-09) ([pl-modernbert]).

### 3.2 Dlaczego NIE per-token w pętli dekodowania (liczby)

| Budżet | Wartość |
|---|---|
| Krok Qwen3.8-27B (MTP n=4) | **27.8 ms** ([L] NOTES:375) |
| Token LFM2.5-24B-A2B | **3.40 ms** ([L] NOTES:375) |
| Poziom draftu MTP | ~0.65 ms; decyzja musi być **≪ 0.1 ms** (≤1–3% poziomu) |
| Laya-multilingual na M3 Max | 7.4 ms = **27% całego kroku Qwena**, **2.2× token LFM**, ~74× budżetu 0.1 ms |
| Laya na T4 / CPU | 33 ms / 193–464 ms = 330× / 2000–4600× budżetu |

Druga przeszkoda: wejściem jest **tekst** (tokenizacja, do 1024 tokenów, pełny encoder), a nie hidden state, który już mamy w GPU. Każde wywołanie to osobny forward ~300M parametrów i synchronizacja host–GPU.

Dla porównania logreg na 16 cechach to ~20 ns.

Wniosek: **per-token tylko malutkie modele na cechach już policzonych** (§2.1).

### 3.3 Gdzie pasują: jedna decyzja na żądanie (~10 ms jest OK)

| Zastosowanie | Co decyduje | Dowody | Zmienia wyjście? |
|---|---|---|---|
| (a) **Router myślenia** (thinking on/off, effort) | trudność promptu | ThinkSwitcher: −20–30% kosztu przy zachowanej dokładności na trudnych ([thinkswitcher]). Thinkless: −50–90% użycia długiego CoT ([thinkless]). AdaptThink: −53% długości, +2.4% dokładności ([adaptthink]). Learning When to Think: −41% tokenów na MATH500, −76% na GSM8K ([lwtt]). Bonsai: `medium` „thinks noticeably less… about as accurate” ([bonsai-docs]) | **tak** (inny tekst). Opt-in „Szybkie odpowiedzi”. Mierzymy *czas do odpowiedzi*, nie t/s (PLAN §2: użytkownik czuje czas ukończenia) |
| (b) Router mały ↔ duży model | czy prompt jest „łatwy” | RouteLLM: >2× taniej przy tej samej jakości ([routellm]) | tak (inny model). U nas tylko przy dwóch modelach w VRAM lub szybkim przełączaniu; na 24 GB rzadko się opłaca `[SZACUNEK]` |
| (c) **Profil spekulacji** per żądanie | kod / proza / PL / agent | §2.1: +1–3% z wyboru n; lookup/n-gram dla edycji kodu: Strata +6–11% | **nie** (lossless) |
| (d) Routing kontekstu i narzędzi u agentów | które narzędzia, ile kontekstu | Arch-Router SOTA w dopasowaniu do preferencji ([arch-router]) | tak (inne wejście) |

**Najtańszy router `[SZACUNEK]`: sonda na naszym własnym prefill.**
- Prefill i tak liczymy, a `llama_get_embeddings_nextn` daje hidden state ostatniego tokenu promptu.
- Sonda logreg (5120 → k klas) kosztuje µs.
- Przełącznik myślenia w szablonie Qwen jest na samym **końcu** promptu. Można więc policzyć prefill do granicy, odpytać sondę i dopiero dokleić sufiks.
- Bez osobnego modelu, bez VRAM, bez 7–30 ms.
- Encoder typu Laya ma sens, gdy decyzja musi zapaść **przed** wyborem modelu (np. router mały ↔ duży) albo w aplikacji bez dostępu do hidden states.

**Fine-tune routera (Laya, mmBERT, Polish ModernBERT).**
- Dane: nasze logi (za zgodą) + syntetyczne prompty PL/EN/kod. Etykiety z eksperymentu:
  - „thinking off dał tę samą ocenę” (sędzia LLM albo test);
  - „najlepsze n dla tego promptu” (z symulatora §2.1).
- Koszt: mmBERT-small/base albo Laya-multilingual, 10–50 k przykładów, 1–3 epoki. **CPU (godziny) albo 1× 3090 przez ~1 h ≈ $0.21** `[SZACUNEK]`. Kaggle 2×T4 za darmo (notebook Laya).
- Uruchomienie poza Apple: PyTorch/ONNX (`laya[onnx]`, `onnx-community/mmBERT-*-ONNX`) albo **llama.cpp** (`src/models/modern-bert.cpp`) jako embedding + nasza głowica logreg.

---

## 4. QAT i odtwarzanie niskich bitów (inna obietnica: zmienia wyjście)

- **Ternary Bonsai 2 27B** (PrismML, Apache-2.0): Qwen3.8-27B w trytach {−1,0,+1} z FP16 skalą na grupę 128, w obróconej bazie Hadamarda (blok 1024). 1.76 bpw, 5.93 GB, 98.2% średniej FP16 na 20 benchmarkach. IQ2_XXS (7.3 GB) daje 88.4% ([bonsai-wp], [bonsai-docs]).
  - **Metoda treningu nie jest ujawniona.** Whitepaper opisuje format, kernele i ewaluację, nie recepturę `[L: grep whitepaper]`.
  - Wymaga forka llama.cpp dla PQ2_0/PTQ1_0. Upstream od b11555 obsługuje `Q2_0`.
- **ISTA GSQ-RCO:**
  - GSQ to PTQ: inicjalizacja GPTQ, potem Gumbel-Softmax po przypisaniach do siatki i skalach, warstwa po warstwie, optymalizator Lion. Format zostaje skalarny i kompatybilny z GGUF K-quant.
  - **Umie dopracować publiczny GGUF K-quant w tym samym formacie**: Qwen3-8B Q2_K 50.03 → 56.28 ([gsq]).
  - RCO przydziela typ kwantu per tensor pod budżet rozmiaru ([gsq-rco]).
  - Narzędzie testowano na H100; Llama-8B na 1× 80 GB, 70B na 4× H100.
- **Underdog Saluki 27B** (Conway/Underdog, Apache-2.0): IQ2-mix 7.89 GB na bazie GSQ-RCO, „tuned to keep tool calling intact”. BFCL-120: 88 vs 84 pełny model; AIME 2025: 79.2 vs 96.7 ([saluki]).
- **QAT w narzędziach:**
  - torchao + Unsloth QAT: odzyskuje do 66.9% degradacji INT4 ([torchao-qat], [unsloth-qat]);
  - Google publikował Gemma 3 QAT Q4_0 GGUF.
  - QAT pod typy K/IQ GGUF wymaga fake-quant dokładnie tych typów. Nie znalazłem gotowego narzędzia; GSQ jest najbliżej `[SZACUNEK]`.
- **Czy zrobimy lepszą wersję 27B na 12/16 GB?**
  - Realnie: GSQ + RCO z **kalibracją PL** (FineWeb-2 PL, nasze prompty), target IQ3/Q3 ~11–13 GB.
  - Koszt `[SZACUNEK]`: 1× A100 80 GB, 8–20 h ≈ **$6–16**; najpierw próba 2 warstw (`--max-layers 2`).
  - Metryki:
    - KLD do BF16 (lub Q8_0) na korpusie PL+EN+kod, z podłogą „ten sam silnik dwa razy” i skalą (Q2 vs IQ3), jak Strata ([L] strata/method.md:51);
    - top-1 agreement;
    - PPL PL;
    - zadania: IFEval, HumanEval+/MBPP+, BFCL podzbiór, polski benchmark (np. PLLuM/Bielik eval);
    - **akceptacja MTP** na nowym kwancie (prawie pewny spadek; §6 stretch).
  - To produkt dla „Trybu maksymalnego”, nie dla L1–L3.

---

## 5. SFT / LoRA / QLoRA (polski, umiejętności)

Narzędzia:
- **Unsloth** (Qwen3.8-27B oficjalnie, architektura `qwen3_5`, kernele FLA, eksport GGUF/NVFP4/FP8; Studio z eksportem) ([unsloth-q38]);
- Axolotl, TRL (SFTTrainer, GRPO), LLaMA-Factory, torchtune;
- Liquid ma oficjalny przewodnik Unsloth dla LFM ([liquid-unsloth]).

| Model | QLoRA VRAM | LoRA 16-bit VRAM | Karta Vast | Czas na 5 M tokenów `[SZACUNEK]` | $ |
|---|---|---|---|---|---|
| Qwen3.5-9B | 6.5 GB | 24 GB ([unsloth-req]) | 3060/3090 (QLoRA), A6000 (LoRA) | ~0.5–1 h | **$0.1–0.4** |
| Qwen3.8-27B | **24 GB** (QLoRA „works with 24GB”) | **>36 GB** (guide); 64 GB (ogólna tabela) ([unsloth-q38], [unsloth-req]) | 3090/4090 ciasno, **A6000/L40S** wygodnie; LoRA: A100 80 GB | ~2–4 h | **$1–3** |
| LFM2.5-24B-A2B (MoE) | QLoRA dla MoE **niezalecane** (BnB) ([unsloth-q36]) | ~48 GB wag bf16 + aktywacje `[SZACUNEK]` | A100 80 GB | ~1–2 h (2B aktywnych) | **$1–2** |

**Eksport:** `save_pretrained_gguf(..., "q4_k_m")` albo merge → `convert_hf_to_gguf.py` → `llama-quantize` z naszym imatrix.

**Uwaga dla nas:** LoRA zmienia trunk, więc głowica MTP (trenowana na starym trunku) traci akceptację. **Każdy wydany SFT musi przejść przez pipeline MTP z §1.3** `[SZACUNEK]`.

## 6. RL / GRPO (krótko)

- Unsloth: RL dla Qwen3.8-27B na 24 GB (ścieżka Qwen3.5, bez fast vLLM) ([unsloth-q38]).
- Koszt dominują rollouty: dziesiątki GPU-h na 27B `[SZACUNEK]`.
- Dla produktu ma sens tylko jako trening routera myślenia wewnątrz modelu (Thinkless, AdaptThink), a to zmienia model.
- **Niski priorytet.** Zewnętrzny router z §3 robi to taniej i bez dotykania wag.

---

## 7. Licencje i etykieta HF

| Baza | Pochodne wolno publikować? | Warunki |
|---|---|---|
| **Qwen3.8-27B**, Qwen3.5 | tak, Apache-2.0 ([L] 06:353) | LICENSE i NOTICE, oznaczyć zmiany. Uwaga: **Qwen3.8-Flash-Next** to Qwen Community License (MaaS / „AI Work Assistant” wymaga zgody) ([L] 06:354) |
| **LFM2.5** (LFM Open License v1.0) | **tak**: modyfikacje i dystrybucja dozwolone, bez copyleftu ([lfm-guide]) | Pochodne zostają pod LFM License. Próg **$10M rocznego przychodu** dotyczy *każdej* firmy używającej komercyjnie (także klientów). Dołączyć licencję i NOTICE, oznaczyć zmienione pliki. Licencja wygasa automatycznie przy naruszeniu. Bez marki Liquid poza „uses Liquid AI models” |
| **Gemma 4** | tak, Apache-2.0 ([L] 06:356) | standard |
| Gemma 3 i starsze (Gemma Terms) | tak, z ograniczeniami | use restrictions jako wykonalny zapis, plik Notice ([gemma-terms]) |
| Bonsai 2, GSQ-RCO, Saluki | Apache-2.0 | kredyt łańcucha (`base_model` lista) |

**Etykieta HF** ([hf-cards]):
- YAML z `license` (`other` + `license_name: lfm1.0` + `license_link` dla LFM);
- `base_model` z pinem rewizji w opisie;
- `base_model_relation` (`finetune` / `adapter` / `quantized` / `merge`; Hub zgaduje, lepiej ustawić jawnie);
- `datasets`, `language: [pl, en]`, `library_name: gguf`;
- tagi `speculative-decoding`, `mtp`.

W karcie:
- jak trenowano;
- dane i ich licencje (aya Apache-2.0, oasst2 Apache-2.0, WildChat ODC-BY);
- **ewaluacja**: tok/krok per język i klasa, sprzęt, commit llama.cpp, n, T;
- ograniczenia.

Nie podszywać się pod oficjalne org (nazwa „…-PL-MTP”, nie „Qwen/…”). Kredyt dla autorów bazy, sha256 plików.

Dla repo z samą głowicą MTP: jasno opisać, że to podmiana `blk.64.*` w konkretnym GGUF (sha bazy).

---

## 8. Strata i TensorFold: czy trenują?

| | Strata ([L] strata/*) | TensorFold ([L] tensorfold/*) |
|---|---|---|
| Draftery | **nie trenuje**. Natywny MTP + zredukowany słownik z korpusu (`tools/draft_vocab.py --corpus --coverage`): FR +11%, CJK +15–38% | trenował **od zera na wynajętych H200: 3.8–5.1% akceptacji 1. tokenu (porażka)**; fine-tune DFlash2 na 372k tokenów: **0**; „drafter trained on the model's own replies” na liście „not yet proven” |
| Modele decyzyjne / kalibracja | DraftPolicy E/koszt z EMA (heurystyka). Gumbel-coupled drafts (+akceptacja, prędkość w szumie) | **offline izotoniczne tabele kalibracji** z logów (`tools/fit_draft_calibration.py`): +6.5% zaakceptowanych; reguła głębokości kosztowa +6–7%; potęga 2 na iloczynie pewności. Pomysł „recordera” (#620): zapis tapów i top-k z ruchu serwera jako dane treningowe |
| Kwanty | nie robi własnych; używa **ISTA GSQ-RCO** (Q2_0/IQ2_XS/IQ3_S, Coder z przyciętymi ekspertami) i fine-tune'u UkisAI Swift 1.5; bramki KL z podłogą | publikuje własne **oQ2/oQ4** (MLX) i NVFP4; EXL3 obniżył akceptację DFlash2 (4.2 → 3.0–3.3) |
| Trening w produkcie | brak | **„Living/Sliding Weights”** (Nemotron): online uczenie wag output projection z faktów, 1.5–3 min/fakt na M3 Ultra/GB10. Zmienia wyjścia |

Wniosek: nikt z nich nie ma działającego treningu draftera dla 27B. **Self-distilled MTP na kwantyzowanym trunku to wolne miejsce**, a ich porażki (od zera, fine-tune DFlash2) potwierdzają wybór: douczać głowicę, która już działa.

---

## 9. Czy to ma sens? (werdykt)

| | Kierunek | Zysk oczekiwany | Dowody | Koszt inżynierski | Ryzyko | Łączenie z kernelami |
|---|---|---|---|---|---|---|
| **1** | **(B) Lepszy drafter: MTP self-distill na Q4, PL+kod** | **+10–17% tok/krok** chat/PL; więcej przy T=1 z TV `[SZACUNEK]` | Red Hat +6.8% τ, FastMTP, TF (kwant psuje drafter) | ekstraktor C++ ~200 l., trener PyTorch, łatka GGUF; **0 zmian w silniku** | średnie (mały zapas, bo Qwen już trenował MTP wielokrokowo); bramka offline to tani test | **mnożnikowo**: t/s = tok/krok ÷ ms/krok; kernele obniżają ms, drafter podnosi tok |
| **2** | (A1) Decyzje per żądanie: profil spekulacji, n/vocab per klasa | +1–3% ruch mieszany; lookup dla kodu +6–11% (Strata) | NOTES n-sweep, Strata | mały (sonda albo heurystyka) | niskie | addytywnie |
| **3** | (A2) Model decyzyjny per-token (stop/szerokość) | **+0–5%** `[SZACUNEK]`; papiery +7–11%; nasz T2 0% | SpecDec++, DISCO, TF +6–7% | logowanie + symulator (CPU) + ~100 l. w T2 | wysokie (T2 już nic nie dał) | wymaga re-kalibracji kosztów przy każdym buildzie (T2 mierzy przy starcie); wartość rośnie, gdy kolumna weryfikacji tanieje względem bazy |
| 4 | (A3) Router myślenia (opt-in) | −20–76% tokenów na łatwych promptach | ThinkSwitcher, Thinkless, AdaptThink, LWTT | sonda / mmBERT + UI | **zmienia odpowiedzi** | niezależne; największy *odczuwalny* zysk (czas do odpowiedzi) |
| 5 | (C) Self-speculation / layer-skip | SWIFT 1.3–1.6× ([swift]), Kangaroo 1.68× ([kangaroo]), LayerSkip do 2.16× ([layerskip]) | — | duży | Qwen3.8 ma już MTP z jedną warstwą, a layer-skip to ~50% forwardu na token draftu → **gorsze**. LayerSkip wymaga treningu wag (inny model). Jedyny sensowny cel to LFM2.5 bez draftera, ale weryfikacja MoE czyta więcej ekspertów ([L] NOTES:341) | — |
| 6 | (D) Uczony sampler | n/d | — | — | **zmienia odpowiedzi** | — |
| 7 | EAGLE-3 / DFlash od zera | ujemny vs MTP dla Qwen3.8 | §1.2 | $25–150+ | wysokie | — |
| 8 | QAT/GSQ PL 12–16 GB | jakość, nie prędkość | Bonsai, GSQ | $6–16 | inna obietnica | trzeba na nowo stroić drafter |

**Odpowiedź wprost.** „Trening + optymalizacja w jednym” ma rację bytu, ale głównie w postaci **(B)**, czyli trenowania tego, co weryfikuje target. Daje to więcej niż model decyzyjny i nie zmienia ani bajtu trunku.

Model decyzyjny per-token jest uzasadniony tylko wtedy, gdy symulator offline pokaże ≥ +3% nad stałym n. Jego największa wartość produktowa to **automatyczna kalibracja per GPU i per użytkownik** (L2 w PLAN). Kształt kosztu kolumn różni się między 3060 a 4090, więc najlepsze n się zmienia.

Encodery typu Laya służą do decyzji raz na żądanie. Tam najsilniejszy efekt (router myślenia) zmienia odpowiedzi, więc trafia do osobnego, jawnego trybu.

---

## 10. Pierwsze eksperymenty z kosztem (Vast)

| # | Eksperyment | Sprzęt | Czas | $ |
|---|---|---|---|---|
| E0 | Logowanie spekulacji + symulator replay + sklearn (§2.1) | nasz 7900 XTX + CPU | 1–2 dni pracy | **$0** |
| E1a | Toolchain MTP: speculators, **Qwen3.5-0.8B** (natywny MTP), offline: regeneracja 2–5k próbek vLLM → hidden states → `speculators train` (MTP) → stitch → `convert_hf_to_gguf.py` → `llama-server --spec-type draft-mtp`, tok/krok przed/po na PL | Vast **RTX 3090** | ~2–3 h | **~$0.5–0.7** |
| E1b | Toolchain SFT: Unsloth QLoRA **Qwen3.5-2B** na aya/oasst2 PL (1–2k kroków) → `save_pretrained_gguf` → llama.cpp | ten sam 3090 | ~1 h | **~$0.25** |
| E2 | **Pilot MTP-PL Qwen3.8-27B na Q4_K_XL** (§1.3) | lokalnie 7900 XTX **albo** Vast **A6000 48 GB** | 6–8 h | **$0** / **~$3–4** |
| E2c | (kontrola) to samo przez speculators na bf16 | A100 80 GB | 6–8 h | ~$5–7 (RunPod) |
| E3a | Głowice MTP **per kwant**: Saluki IQ2 (8 GB) i Q3 (16 GB). Trunk niżej = większy zapas | 3090 / A6000 | 4–6 h każda | **~$1–3 każda** |
| E3b | Głowica TV dla `probabilistic` przy T=1 | jak E2 | +2–4 h | ~$1–2 |
| E3c | Router (sonda prefill albo mmBERT-small) na etykietach z E0 | CPU / 3090 1 h | — | $0–0.2 |
| E3d | GSQ PL dla 27B (Tryb maksymalny) | A100 80 GB | 8–20 h `[SZACUNEK]` | $6–16 |

Disk: hidden states 10 KB/token (5120 × fp16). Pilot (2 M tokenów) = 20 GB, więc na Vast wziąć **≥100 GB dysku**. Koszt dysku jest mały, ale płatny także przy zatrzymanej instancji `[SZACUNEK]`.

---

## 11. Ścieżka dla początkującego (krok po kroku)

**Krok 0, tylko CPU, $0 (uczy danych i ewaluacji, nie wymaga GPU w chmurze):**
1. Dodać do forka `LLAMA_SPEC_LOG` (rekord z §2.1) i zebrać logi spec_sweep z `n_max=7`.
2. Skrypt `replay.py`: wczytuje logi i tabelę kosztów (ms weryfikacji per szerokość z T2, draft ms/poziom), liczy tok/ms dla stałych n=3..7, dla reguły T2, dla wyroczni i dla modelu.
3. `train_policy.py`: sklearn `LogisticRegression` per głębokość + `IsotonicRegression`; raport Brier i log-loss; wynik replay.
4. Decyzja: jeśli learned − best_fixed < 3%, zapisać wynik negatywny i iść dalej.

**Krok 1, < $2: nauka toolchainu (E1a + E1b na jednym 3090, ~3–4 h, ~$1).**

Komendy z oficjalnych tutoriali: speculators `prepare-data` → `launch_vllm.py Qwen/Qwen3.5-0.8B --target-layer-ids <ostatnia>` → `generate-offline-data` → `train` (MTP) → stitch ([spec-train]). Unsloth: przepis SFT z [unsloth-q38] z mniejszym modelem.

Kryterium sukcesu: llama.cpp ładuje oba wyniki, a tok/krok MTP na PL zmienia się mierzalnie.

**Krok 2, pilot: E2 (MTP-PL 27B).**
- Najpierw bramka offline: per-głębokość akceptacja **dostarczonej** głowicy na naszym Q4, czyli ile realnie jest do wzięcia. To ~1 h GPU.
- Potem pełny pilot.
- Cel: pl-proza ≥ +10% tok/krok, en-chat ≥ +5%, kod bez regresji.
- Lokalnie $0, na Vast A6000 ~$3–4.

**Krok 3, stretch.**
- E3a: głowice per kwant. To produkt „ten sam plik modelu + nasz dostrojony drafter” dla 8/16 GB.
- E3b: TV i T=1.
- Router myślenia jako opt-in (E3c).
- Po E2 douczyć model decyzyjny z kroku 0 na nowej głowicy.

---

## Źródła

Lokalne:
- `~/KERNEL/qwen-opt/NOTES.md` (linie cytowane w tekście)
- `~/KERNEL/qwen-opt/research/training.md`, `drafters.md`
- `~/KERNEL/qwen-opt/research/strata/{README,spec-host,method}.md`
- `~/KERNEL/qwen-opt/research/tensorfold/{README,qwen27,spec-host,issues}.md`
- `~/KERNEL/product/PLAN.md`
- `research/05-chmura-gpu-do-testow.md`, `06-produkt-ux-prawo-biznes.md`
- `~/llama-master` @ f61994f58: `common/common.h`, `common/speculative.cpp`, `common/arg.cpp`, `src/models/*.cpp`

Web:
- [vast-feed] https://storage.googleapis.com/vast-public-gpu-pricing/gpu-pricing-public.json (2026-10-16T00:30Z)
- [llamacpp-spec] https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md
- [fastmtp] https://arxiv.org/abs/2509.18362 · https://github.com/Tencent-BAC/FastMTP
- [redhat-fastmtp] https://developers.redhat.com/articles/2026/09/08/optimize-vllm-speculative-decoding-fastmtp-heads
- [spec-mtp] https://github.com/vllm-project/speculators/blob/main/docs/user_guide/algorithms/mtp.md
- [spec-train] https://github.com/vllm-project/speculators/blob/main/docs/user_guide/tutorials/train.md
- [specforge] https://sgl-project.github.io/SpecForge/ · https://arxiv.org/abs/2603.18567
- [nemo-dflash] https://docs.nvidia.com/nemo/automodel/recipes-e2e-examples/dflash-speculative-decoding
- [eagle3] https://arxiv.org/abs/2503.01840 · https://github.com/SafeAILab/EAGLE
- [eagle2] https://arxiv.org/abs/2406.16858
- [medusa] https://arxiv.org/abs/2401.10774
- [yi-multilingual] https://arxiv.org/abs/2406.16758
- [domain-drafter] https://arxiv.org/abs/2503.07807
- [specdecpp] https://arxiv.org/abs/2405.19715
- [disco] https://proceedings.mlr.press/v262/mamou24a.html
- [adaeagle] https://arxiv.org/abs/2412.18910
- [banditspec] https://arxiv.org/abs/2505.15141
- [c2t] https://arxiv.org/abs/2502.13652
- [lumotree] https://arxiv.org/abs/2609.23900
- [dynaspec] https://arxiv.org/abs/2510.13847
- [nanospec] https://arxiv.org/abs/2605.26444
- [specvocab] https://aclanthology.org/2026.findings-acl.2000
- [swift] https://arxiv.org/abs/2410.06916
- [kangaroo] https://arxiv.org/abs/2404.18911
- [layerskip] https://arxiv.org/abs/2404.16710
- [laya] https://huggingface.co/convaiinnovations/laya
- [laya-mlx] https://github.com/mizorewww/laya-mlx
- [ollama-d1] https://registry.ollama.com/library/d1:3b-q8_0
- [nv-ptcc] https://huggingface.co/nvidia/prompt-task-and-complexity-classifier
- [arch-router] https://arxiv.org/abs/2506.16655 · https://huggingface.co/katanemo/Arch-Router-1.5B
- [routellm] https://arxiv.org/abs/2406.18665 · https://huggingface.co/papers/2406.18665
- [mmbert] https://arxiv.org/abs/2509.06888 · https://huggingface.co/onnx-community/mmBERT-base-ONNX
- [pl-modernbert] https://arxiv.org/abs/2609.01379
- [llamacpp-modernbert] https://github.com/ggml-org/llama.cpp/blob/master/src/models/modern-bert.cpp
- [thinkswitcher] https://arxiv.org/abs/2505.14183
- [thinkless] https://arxiv.org/abs/2505.13379
- [adaptthink] https://arxiv.org/abs/2505.13417
- [lwtt] https://arxiv.org/abs/2608.20256
- [bonsai-docs] https://docs.prismml.com/models/bonsai-2-27b
- [bonsai-wp] https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-27b-whitepaper.pdf
- [gsq] https://github.com/IST-DASLab/GSQ · https://arxiv.org/abs/2604.18556
- [gsq-rco] https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF
- [saluki] https://huggingface.co/ConwayResearch/Underdog-Saluki-27B-1.0
- [torchao-qat] https://pytorch.org/blog/quantization-aware-training-in-torchao-ii
- [unsloth-qat] https://unsloth.ai/docs/blog/quantization-aware-training-qat
- [unsloth-q38] https://unsloth.ai/docs/models/qwen3.8/train.md
- [unsloth-req] https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements
- [unsloth-q36] https://unsloth.ai/docs/models/qwen3.6.md (QLoRA dla MoE niezalecane)
- [liquid-unsloth] https://docs.liquid.ai/lfm/fine-tuning/unsloth
- [lfm-guide] https://docs.liquid.ai/lfm/help/model-license · https://www.liquid.ai/lfm-license
- [gemma-terms] https://ai.google.dev/gemma/terms
- [hf-cards] https://huggingface.co/docs/hub/model-cards
- [hf-api] https://huggingface.co/api/models?search=… (zapytania z 2026-10-16: „Qwen3.5-9B eagle3”, „Qwen3.5-9B DFlash”, „Qwen3.5-9B mtp”, „LFM2 eagle3”, „LFM2.5 dflash”, „laya”, „saluki”)
