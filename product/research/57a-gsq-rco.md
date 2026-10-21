# 57a. GSQ-RCO: co to jest, kto to zrobił, jak działa i czy da coś naszemu Qwen3.8-27B na XTX / 3090

Data: 2026-10-21. Autor: podagent ResGSQRCO. Tylko CPU, bez GPU. Przeczytałem: artykuły GSQ (arXiv 2604.18556 v2, HTML), RCO (2605.00649 v3, HTML) i SLQ (2605.02404 v2, HTML), abstrakt DQ (2609.26333), kartę `ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF` z plikiem alokacji IQ3_S, kartę `ISTA-DASLab/Qwen3.8-27B-3Bit-GSQ`, listę modeli HF (API) i profil GitHub `helcig`. Sklonowałem do `~/qwen-opt/research/` repo `IST-DASLab/GSQ` (`03fc164`, 2026-07-05, wszystkie gałęzie), `IST-DASLab/RCO` (`9a1e09c`, 2026-06-13), `IST-DASLab/SLQ` (`eb9f1f2`, 2026-10-08) i `IST-DASLab/gptq-gguf-toolkit` (`7a38bc5`, 2025-09-17).

**Ten raport to delta.** GSQ-RCO był już badany w R10, R15e i R16e (KLD 12 ramion, prędkość na 3060/5060 Ti) i ma notę [[ista-daslab]]. Tamtych pomiarów tu nie powtarzam, tylko je cytuję. Nowe są: identyfikacja autora biogramu, stan kodu (co naprawdę jest publiczne), liczby RCO przy 4 bitach, SLQ/EAR i przełożenie na reżim 24 GB (Q4_K_XL), czego 15e nie robił, bo dotyczył 12–16 GB.

Oznaczenia: `[INFERENCE]` = mój szacunek; `[niezweryfikowane]` = nie dało się sprawdzić u źródła.

## TL;DR

1. **GSQ-RCO to nie silnik, tylko przepis na pliki GGUF z dwóch metod ISTA-DASLab.** **GSQ** (Gumbel-Softmax Quantization) to PTQ, które uczy przypisań wag do siatki i skal grup. **RCO** (Riemannian Constrained Optimization) dobiera typ kwantu per tensor pod dokładny budżet rozmiaru. Wynik to zwykły GGUF z typami IQ/K, uruchamiany w llama.cpp bez zmian. Nazwa jest jednoznaczna. Jedyna kolizja, GSQ-Tuning (2502.12913, trening w formacie całkowitym), to inna grupa i inny temat.
2. **Autor biogramu to z dużą pewnością Michael Helcig** (X `@mhelcig`): student CS na ETH Zürich, visiting researcher w EPFL, student/współpracownik ISTA. Jest pierwszym autorem RCO i SLQ, współautorem GSQ i głównym autorem `gptq-gguf-toolkit`. Biogramu na X nie odczytałem (X blokuje odczyt automatyczny), więc samo dopasowanie tekstu jest `[niezweryfikowane]`. Wszystkie trzy człony („CS @ ETH Zurich”, „Research @ ISTA | EPFL”, GSQ+RCO) zgadzają się jednak z GitHubem, Scholar, alphaXiv i afiliacjami w pracach.
3. **Publiczny kod nie odtwarza plików GGUF.** `IST-DASLab/GSQ` (main i 5 gałęzi) nie ma ani jednej linii GGUF/K-quant. Wynik „Q2_K 50.03 → 56.28” jest tylko w README i artykule (App. E: kilka akapitów, bez kodu). `IST-DASLab/RCO` robi alokację bitów INT {2..8} dla checkpointów HF (compressed-tensors), nie typów GGML. Produkcyjny pipeline „baza GSQ per typ GGUF → RCO → sklejenie” jest nieopublikowany. Najbliższy publiczny odpowiednik to `gptq-gguf-toolkit` (GPTQ → Q2_K…Q6_K + EvoPress + `gguf_stitcher.py`), ale **bez pliku LICENSE**.
4. **Przy ~4 bitach przewaga GSQ-RCO znika, a my jesteśmy przy 4.96 bpw w MLP.** Liczby z ich własnych prac:
   - RCO na Qwen3-8B przy 4.0 bit: PPL FW 11.14–11.17 wobec EvoPress 11.16 (FP16 10.96). Przy 2.25 bit różnica wynosi 20.5 wobec 21.4.
   - GSQ na GGUF: Q2_K +6.25 pkt, Q3_K_M tylko +1.09 pkt. Q4_K nie testowali.
   - ISTA nie wydała żadnego tieru ≥ 4 bpw. Ich najwyższy, IQ3_S 3.5 bpw, ma w niezależnym KLD gorszy wynik niż UD-IQ3_S (0.0665 vs 0.0470, R15e) i 4.8× wyższy KLD-wiki niż nasz U4 (0.0733 vs 0.0153, R16e).
5. **Dla XTX/ROCm i 3090 nie ma tu niczego „za darmo”.** Format to standardowe GGUF, więc wszystko się uruchomi, ale nie da nam ani szybszego kernela, ani lepszego Q4. Realne są trzy rzeczy, wszystkie tanie:
   - (a) **metryka EAR** z SLQ do naszego narzędzia KLD (interpretowalna „zgodność tokenów”);
   - (b) **eksperyment alokacji per tensor przy 24 GB** ograniczonej do typów, które mają nasze szybkie kernele MMVQ (Q4_K/Q5_K/Q6_K/IQ4_XS), z bramką kill;
   - (c) na wynajętej 3090 **opcjonalny punkt odniesienia**: `ISTA-DASLab/Qwen3.8-27B-3Bit-GSQ` w vLLM (Marlin/Humming, sm86).

   Refinement GSQ naszego Q4_K_XL „w formacie” odpada na teraz: kodu brak, a zysk przy ≥ 4 bitach jest niezmierzony.

## 1. Co to jest

- **GSQ** (arXiv 2604.18556, kwiecień 2026, v2 maj 2026): skalarna PTQ po warstwach.
  - Każda waga dostaje mały wektor logitów nad kandydatami siatki. Próbka Gumbel-Softmax daje „miękką” wagę, a strata rekonstrukcji wyjścia warstwy jest różniczkowalna względem przypisań **i** skal grup.
  - Temperatura opada, więc przypisania zapadają się do punktów siatki.
  - Format wyjściowy to symetryczna siatka z grupą 128 (zgodna z kernelami INT, Marlin/Humming). Druga ścieżka to „projekcja” z powrotem do tego samego typu GGUF K-quant, z którego startowano.
- **RCO** (arXiv 2605.00649, maj 2026, v3 27.09.2026): ogólny optymalizator przypisania „jedna z K opcji dla każdej z N grup” przy **dokładnym** budżecie kosztu i niedekomponowalnej stracie. Zastosowania: precyzja per warstwa/tensor, przycinanie ekspertów MoE.
- **GSQ-RCO GGUF** (karta ISTA): baza wariantów każdego tensora w każdym kandydackim typie GGUF (GSQ), potem RCO wybiera typ per tensor pod docelowe bpw, potem sklejenie w jeden GGUF. Pliki Qwen3.8-27B: IQ2_XS 2.50 / IQ2_S 2.75 / IQ3_XXS 3.00 / IQ3_S 3.50 bpw (8.4–11.8 GB) plus warianty `-mtp` (+0.35 GB z głowicą MTP).
- **Ekosystem:** z ~60 repozytoriów HF z „GSQ-RCO” w nazwie tylko 3 są od ISTA (27B 2026-08-28, Flash-Next 09-07, Flash-Next-Coder z przycinaniem ekspertów 09-26). Reszta to przeróbki społeczności: abliteracje, Swift, Strata-packi, NInfer, MLX, mieszanki DavidAU. Pobrania (API HF, 2026-10-21): 27B 1.29 M, Flash-Next 6.32 M, Coder 0.92 M.

## 2. Kto / skąd

### 2.1 Autor biogramu: kandydaci

| kandydat | ETH Zürich | ISTA | EPFL | GSQ / RCO | dopasowanie |
|---|---|---|---|---|---|
| **Michael Helcig** (`helcig`, X `@mhelcig`) | GitHub: „CS @ ETH Zurich”, Zurych; afiliacja „ETH Zürich” w GSQ, RCO i 2609.39560; e-mail `@ethz.ch` w RCO | Scholar: „Student, Institute of Science and Technology Austria”; członek org `IST-DASLab`; pierwszy autor RCO/SLQ z Alistarhem | alphaXiv: „Visiting Researcher: EPFL”; praca 2609.39560 z Martinem Jaggim (EPFL) | współautor GSQ (4. autor), **pierwszy i korespondencyjny autor RCO**; przypięte repo: RCO, GSQ, gptq-gguf-toolkit, SLQ | **wszystkie człony** |
| Maximilian Kleinegger (`mkleinegger`) | brak (TU Wien) | PhD @ ISTA | brak | współautor GSQ | słabe |
| Alireza Dadgarnia, Soroush Tabesh, Mahdi Nikdan | brak | ISTA | brak | główni autorzy kodu GSQ (25 + 21 commitów) | słabe (bez ETH/EPFL) |

Wniosek: biogram „CS @ ETH Zurich, Research @ ISTA | EPFL, Co-Creator of GSQ-RCO” to Michael Helcig. Tekstu biogramu na X nie widziałem `[niezweryfikowane]`. Link do X pochodzi z jego profilu GitHub.

### 2.2 Grupa i powiązane prace

DASLab, czyli grupa prof. Dana Alistarha (ISTA, także Red Hat AI). Prace Helciga:
- **RCO** (2605.00649, z Alistarhem);
- **SLQ, Statistically-Lossless Quantization** (2605.02404, COLM 2026, z Kurticiem i Alistarhem);
- **GSQ** (współautor);
- **gptq-gguf-toolkit** (2025, z Kleineggerem: GPTQ z eksportem K-quantów + EvoPress dla GGUF);
- poza kwantyzacją: „Self-Repulsive Sampling for Diffusion LMs” (2609.39560, z Jaggim, EPFL).

Szersza rodzina DASLab, sprawdzona przez API arXiv (autor pierwszy … ostatni):
- **GPTQ** 2210.17323 (Frantar … Alistarh);
- **AQLM** 2401.06118 (Egiazarian … Alistarh);
- **MARLIN** 2408.11743 (Frantar … Alistarh);
- **HIGGS** 2411.17525 (Malinovskii … Alistarh);
- **EvoPress** 2410.14649 (Sieberling … Alistarh);
- **MR-GPTQ / FP4** 2509.23202 (Egiazarian … Alistarh), z kernelami QuTLASS;
- **MatGPTQ** 2602.03537 (Kleinegger … Alistarh);
- **Disaggregated Quantization** 2609.26333 (Panferov, Kleinegger … Alistarh, NVIDIA+ISTA).

Korekta listy z zadania:
- **QuIP#** (2402.04396) to Cornell (Tseng … De Sa), nie ISTA.
- **MicroMix** (2508.02343, ICLR 2026) to Tianjin University (Liu … Ma), nie ISTA.

## 3. Jak działa technicznie

### 3.1 GSQ (artykuł §3, App. E; README `Mechanism in detail`)

- **Cel:** dla każdej warstwy liniowej `ŵ = argmin ||f(x;w̃) − f(x;w)||²` przy `w̃ ∈ C` (siatka). Kalibracja idzie warstwa po warstwie (blok po bloku, „within-block staging”, App. C), a poprzednie warstwy są już skwantyzowane.
- **Relaksacja:** każda waga ma logity nad małym zbiorem 𝒟:
  - ternary: osobne logity znaku i maski;
  - 2 bit: 4 poziomy {−2,−1,0,1}·s;
  - n bit („local shift”): przesunięcia {−2,−1,0,+1,…} wokół przypisania startowego, bo przy 3–4 bitach pełna siatka rośnie wykładniczo.

  Na tych logitach losowana jest próbka Gumbel-Softmax. Temperatura τ maleje (high → low), skala logitów κ rośnie (low → high).
- **Optymalizacja:** Lion z kosinusowym LR (ablacja Tab. 5 na Llama-3.1-8B 2 bit: Lion 65.54 vs AdamW 61.84 śr. zero-shot). Własny autograd odtwarza stan RNG w backwardzie (dokładne gradienty przez próbkę). Inicjalizacja to GPTQ albo istniejący GGUF; bez dobrego startu metoda nie działa (App. F). Opcjonalnie na końcu fine-tuning samych skal end-to-end (App. H).
- **GGUF K-quant (App. E, całość opisu):** start od kodów z publicznego GGUF (Unsloth). Dla typów o ≤ 4 wartościach (Q2_K) relaksacja obejmuje pełny zbiór, dla większych „local shift” wokół indeksu z GGUF. Na końcu następuje projekcja do tego samego formatu K-quant.

  Nie opisano, jak traktowane są 4/6-bitowe podskale i minima K-quantów (asymetria Q2_K/Q4_K/Q5_K), a kodu nie ma (§5).
- **Koszt:** 8×H200, Llama-3.1-8B 10 h, 70B 68 h, Kimi-K2.5 24 h (App. G.4, Tab. 10). README: 1×H100/A100 80 GB dla 8B, tylko Hopper testowany.

### 3.2 RCO (artykuł §2–3, README, `src/manifold.py`, `src/search/quant.py`)

- **Relaksacja:** `p_i = softmax(α_i)` per grupa (tensor). Koszt oczekiwany wynosi `C(α) = Σ_i w_i Σ_k p_ik c_k` (w_i = liczba parametrów, c_k = bpw opcji). Model jest interpolowany `Σ_k p_ik W_k` z bazy wcześniej skwantyzowanych wariantów.
- **Ograniczenie budżetu** `C(α) = B` to gładka rozmaitość w przestrzeni logitów. Normalna jest w postaci zamkniętej: `∂C/∂α_ik = w_i p_ik (c_k − E_p[c])`.
- **Krok:** gradient Adama rzutowany na przestrzeń styczną, potem retrakcja `α' = α + t·c`, gdzie t wyszukiwane binarnie (monotoniczne). Na końcu transport momentu przez ten sam iloczyn skalarny. Budżet trzyma się dokładnie w każdej iteracji, bez współczynników kary.
- **Dyskretyzacja:** Gumbel-STE plus dokładny plecak wielokrotnego wyboru (DP, `round_with_budget_dp`), który zwraca wykonalne przypisanie w forwardzie. DP w Pythonie zajmuje 8.3% czasu kroku dla Qwen3-8B (Tab. 4).
- **Wyniki (Tab. 2, Qwen3-8B, te same wagi GPTQ per bitwidth), PPL FineWeb-Edu:**

| bpw | RCO (g=16, T=200) | EvoPress (100 gen) | IMPQ |
|---|---|---|---|
| 2.25 | 20.47 | 21.40 | 24.18 |
| 4.0 | 11.16 | 11.16 | 11.42 |

  FP16 = 10.96. Czas: RCO 62–215 min, EvoPress 11–14 h. **Przy 4 bitach dobre alokatory remisują**, a wyraźna przewaga RCO jest tylko przy ≤ 2.5 bit.

### 3.3 Plik ISTA w praktyce (alokacja IQ3_S, 851 tensorów)

- Histogram typów: IQ3_S 144, IQ4_XS 96, IQ3_XXS 78, Q4_K 39, IQ2_S 17, Q2_K 13, IQ2_XS 9, IQ2_XXS 5, IQ1_M 1; BF16 96 (ssm_alpha/beta), F32 353.
- `output.weight` = **Q4_K** (u nas Q6_K, 1.043 GB, R18). `token_embd` = IQ2_S.
- Alokacja jest niejednorodna nawet w obrębie warstwy, np. `blk.0`: attn_qkv/attn_gate/ssm_out IQ4_XS, ffn_down IQ2_S, ffn_gate IQ2_XS, ffn_up IQ2_XXS.
- Imatrix ISTA: 1000 × 4096 tokenów, w repo jako `imatrix-qwen3.8-27b.gguf`.

### 3.4 SLQ (pokrewna praca Helciga, ważna dla nas koncepcyjnie)

- **Pipeline:** GPTQ asymetryczny g128 dla każdego bitu 2..8, wrażliwość Shapleya w wielu bitwidthach, ILP (albo RCO) i wyszukiwanie binarne budżetu do celu jakości.
- **EAR (Expected Acceptance Rate)** = maksymalne prawdopodobieństwo zgodności tokenu przy optymalnym sprzężeniu = Σ_v min(p_v, q_v) = 1 − TV(p, q). Jest to dokładnie akceptacja spekulacji, w której model skwantyzowany byłby drafterem modelu BF16. „Distribution-lossless” oznacza EAR ≥ 0.99.
- **Prawo γ²:** symetryczna siatka zwiększa wariancję szumu γ² razy względem asymetrycznej. Asymetria jest warunkiem wierności rozkładu, ale nie wyniku zadań.
- **Obserwacja empiryczna (Fig. 1b):** dokładność zero-shot jest płaska do KL ≈ 0.01 i spada dopiero wyraźnie powyżej.

## 4. Liczby (wszystkie z GPU autorów, nie nasze)

| co | wynik | sprzęt / protokół | źródło |
|---|---|---|---|
| GSQ 2 bit vs najlepszy skalarny (EfficientQAT) | +4.76 (8B) / +4.14 (70B) pkt śr. zero-shot; do QTIP brakuje 1.33 / 1.68 | Llama-3.1-Instruct, 5 zadań, 1 run | 2604.18556 §1, §4.2 |
| GSQ na GGUF Qwen3-8B | Q2_K: 50.03 → 56.28 śr. (AIME25 38.67 → 52.00); Q3_K_M: 60.52 → 61.61; BF16 65.16 | Unsloth GGUF jako start; AIME25 ×10, GPQA ×5 | Tab. 4 |
| Przepustowość GSQ 70B | 2-bit 374 TPS/GPU = 6.2× vs BF16 na 4 GPU | L40S, vLLM + Humming, ShareGPT, metryka per GPU | Tab. 2 |
| Koszt GSQ | 8B 10 h, 70B 68 h na 8×H200 | — | Tab. 10 |
| ISTA Qwen3.8-27B GSQ-RCO IQ3_S | wiki PPL 7.07 (BF16 7.05); AIME25 100 = 100; LCB 85.71 = 85.71; GPQA 89.39 vs 89.90 | GPU nieujawnione, 1 run | karta HF |
| ten sam plik, KLD niezależnie | 0.0665 (ctx 2048) vs UD-IQ3_S 0.0470; KLD-PL 0.057 vs U3 0.032 | agentionai 60×2048; nasz E1 (Vast/RunPod) | R15e, R16e |
| nasz U4 (UD-Q4_K_XL) dla skali | KLD wiki 0.0153, PL proza 0.0073, same-top PL 96.2% | nasz E1 | R16e §2.1 |
| ISTA Qwen3.8-27B 3Bit-GSQ (vLLM) | AIME25 100/100; GPQA-D 91.41 vs 89.90; 11.83 GB z wizją | xhigh thinking, **1 run** | karta HF |
| SLQ Qwen3.5-27B | TL 3.30 bpp, rec. 0.991; DL 5.19 bpp, rec. 0.997; oficjalny GPTQ-Int4 (4.1) rec. 0.999 | 7 benchmarków, 3 seedy | 2605.02404 Tab. 1 |
| SLQ vs QTIP (Llama-3.1-8B) | GPTQ 4.16 bpp: KL 0.028, EAR 0.938; QTIP ~4: 0.017 / 0.952; SLQ 5.59: 0.004 / 0.994 | — | Tab. 5 |
| SLQ przepustowość | Qwen3-8B TL 4.72 bpp: 1.94×; Llama-70B TL 3.59: 3.68× TPS/GPU | L40S, Humming | Tab. 3 |
| RCO vs EvoPress | patrz §3.2; 3–16× krótszy czas | Qwen3-8B, 4×A100 | Tab. 2, Tab. 4 |

Uwaga do SLQ Tab. 1: oficjalny GPTQ-Int4 Qwen3.5-27B ma recovery 0.999 przy 4.1 bit, czyli lepiej niż SLQ-TL. Benchmarki zadaniowe przy ~4 bitach nie rozróżniają kwantów. Dlatego przy 24 GB liczy się KLD/EAR, nie AIME.

## 5. Licencja / dostępność

| artefakt | licencja | co jest | czego brak |
|---|---|---|---|
| `IST-DASLab/GSQ` | Apache-2.0 | kwantyzacja INT/ternary → compressed-tensors (vLLM), wrappery Qwen3.5/3.6 (hybryda), Kimi | **zero kodu GGUF/K-quant** na wszystkich gałęziach (grep `gguf`/`Q2_K`/`Q4_K` w `src/`, `main.py`, `scripts/`, `configs/`: 0 trafień); IQ-refinement tylko na gałęzi `gsvq-iquant-qwen3-sweep-results` jako eksperyment (pogarszał KL, R15e) |
| `IST-DASLab/RCO` | Apache-2.0 | `manifold.py`, wyszukiwanie bitów INT {2..8}, przycinanie MoE, budowa HF | typów GGML i sklejania GGUF |
| `IST-DASLab/SLQ` | Apache-2.0 | GPTQ wielobitowy, Shapley, ILP, `eval/run_ear.py` (EAR, top-K KL) | — |
| `IST-DASLab/gptq-gguf-toolkit` | **brak pliku LICENSE** (API GitHub: `license: null`) | GPTQ z eksportem Q2_K…Q6_K, EvoPress, `gguf_splitter.py`/`gguf_stitcher.py` | licencji (domyślnie wszystkie prawa zastrzeżone), typów IQ, aktywności od 2025-09 |
| wagi ISTA GGUF | Apache-2.0 (dziedziczą po Qwen3.8-27B) | 4 tiery + `-mtp`, imatrix, alokacje | tieru ≥ 4 bpw |

## 6. Co z tego dla nas

Kontekst: XTX gfx1100, topka, UD-Q4_K_XL 17.55 GB (MLP 4.96 bpw, głowica Q6_K), KV q4_0, MTP + lookup, proza ~79 t/s, czat ~95–104 t/s. Dekodowanie ogranicza pasmo: krok MTP n=4 czyta ~16.9 GB wag (R18).

| # | pomysł | zysk `[INFERENCE]` | pewność | koszt | ryzyko | dotyczy |
|---|---|---|---|---|---|---|
| 1 | **EAR w naszym KLD.** Do `llama-perplexity --kl-divergence` (pełne logity bazy już są) dopisać Σmin(p,q) obok KLD i same-top; przeliczyć pliki R16e | 0 t/s; lepsza, interpretowalna metryka „% zgodnych tokenów” do bramek jakości i prognozy akceptacji MTP vs BF16 | wysoka (definicja z SLQ, wzór trywialny) | 0.5 dnia CPU (kod) + przeliczenie przy najbliższym jobie KLD | brak | wszystkie karty |
| 2 | **Alokacja per tensor 24 GB, tylko typy z szybkim MMVQ** ({IQ4_XS, Q4_K, Q5_K, Q6_K, Q8_0}). Wrażliwość per tensor (KLD-PL po obniżeniu jednego tensora o typ), plecak DP jak `round_with_budget_dp`, `llama-quantize --tensor-type` z imatrixem ISTA albo PL. Cel: rozmiar U4 −1.0…−1.5 GB przy KLD-PL ≤ 1.1 × U4, albo ten sam rozmiar przy niższym KLD | −6…−9% bajtów na krok → **+4…+7% t/s** plain i MTP; albo wyższa akceptacja przy tym samym rozmiarze | **niska-średnia**: RCO przy 4 bit remisuje z EvoPress; UD już jest dynamiczne; ISTA przy 3.5 bpw przegrywa z UD w KLD | 2–3 dni CPU (skrypty) + ~4–6 h XTX (pomiary KLD per tensor dla ~400 tensorów MLP/attn to za dużo; grupować po typie roli × co 8 warstw → ~60 przebiegów) | kill, jeśli 3 kolejne warianty nie pobiją U4 na froncie (bajty, KLD-PL) | XTX, 3090 |
| 2b | w ramach 2: **asymetria (SLQ γ²)**. A/B części MLP Q3_K/IQ4_XS (symetryczne) → Q4_K (asymetryczny z minimami) przy kontroli bajtów | akceptacja MTP +0.5…1 pp? | niska (teza teoretyczna, niesprawdzona na GGUF) | w koszcie #2 | — | XTX, 3090 |
| 3 | **3090 (wynajem): punkt odniesienia vLLM 3Bit-GSQ.** `ISTA-DASLab/Qwen3.8-27B-3Bit-GSQ` (11.8 GB, vLLM 0.27.1 + łatka embeddingu, Marlin WNA16 sm86) vs nasz llama.cpp U4 na tej samej karcie: t/s c=1, KLD niemierzalny (inna ścieżka) | wiedza: czy 3-bit INT + Marlin na Ampere bije nasz Q4 GGUF w t/s; produktowo nic (to nie GGUF) | średnia | 1–1.5 h wynajmu (~$0.3–0.5) | łatka vLLM; README GSQ: serwowanie tylko Hopper/Ampere, a Ada się wywraca | 3090 |
| 4 | **Refinement GSQ naszego Q4_K_XL „w formacie”** (te same bajty, lepsze kody) | jakość: KLD −?; t/s 0 | niska: kodu brak, przy Q3_K_M zysk już ~1 pkt, Q4_K nietestowany | 10–20 osobodni (implementacja od zera + podskale/minima K-quantów) + ~50–150 GPU-h H100 | duże | wszystkie |
| 5 | Pliki ISTA GSQ-RCO jako trunk na XTX | **nie dotyczy**: 24 GB mieści U4 z KLD 4.8× niższym; tylko tier 16 GB (już zamknięte w R16e: kill) | — | — | — | — |
| 6 | Orca (OrcaCyber-Nano, Qwen3.5-27B) + DFlash2: przeszczep alokacji ISTA (jak Swift) | **nie dotyczy** przy 24 GB. Jedyny sens to zrobienie miejsca na drafter + KV kosztem ~4× KLD; nie polecam | — | — | — | — |
| 7 | Disaggregated Quantization (Kleinegger/Panferov): prefiller NVFP4 + ODP (1.78× TTFT @8K w llama.cpp, Qwen3.8-27B GGUF) | **nie dotyczy** XTX/3090 (brak FP4). Pomysł „osobne wagi do prefillu ze SSD” zanotować dla Blackwella | — | — | — | RTX 50xx |

Kolejność: #1 teraz (tanie, CPU). #2 tylko jako zadanie poboczne przy najbliższym oknie GPU, z bramką kill. #3 dołożyć do skryptu 3090, jeśli zostanie czas. #4 dopiero po publikacji kodu K-quant przez ISTA (sygnał w CompWatch).

Zarys #2 (do przygotowania na CPU, bez uruchamiania): `kt`-job z wariantami `U4`, `R-0.8GB`, `R-1.3GB`, `R-eq` (ten sam rozmiar). Metryki: KLD/EAR na PL prozie, czacie i kodzie (protokół R16e), t/s E0 i czat z MTP. Bramka: front Pareto (GB, KLD-PL) musi pobić U4 co najmniej w jednym punkcie o ≥ 5% bajtów przy ≤ +10% KLD-PL.

## 7. Do bazy wiedzy

- **Fakt:** GSQ-RCO = GSQ (Gumbel-Softmax PTQ: przypisania do siatki + skale, Lion, start z GPTQ/GGUF) + RCO (typ per tensor pod dokładny budżet, rozmaitość Riemanna w logitach, Gumbel-STE + plecak DP). Wynik to standardowy GGUF. ISTA-DASLab (Alistarh).
- **Fakt:** biogram „CS @ ETH Zurich, Research @ ISTA | EPFL, Co-Creator of GSQ-RCO” = Michael Helcig (X `@mhelcig`, GitHub `helcig`), pierwszy autor RCO (2605.00649) i SLQ (2605.02404), współautor GSQ. Tekst samego biogramu `[niezweryfikowane]`, X niedostępny.
- **Fakt:** publiczne repo GSQ (`03fc164`, wszystkie gałęzie) nie ma kodu GGUF/K-quant. RCO (`9a1e09c`) robi tylko bity INT dla HF. Pipeline plików GSQ-RCO GGUF jest nieopublikowany.
- **Fakt:** RCO, Qwen3-8B, 4.0 bit: PPL FW 11.14–11.17 = EvoPress 11.16 (FP16 10.96). Przewaga RCO jest tylko ≤ 2.5 bit (20.47 vs 21.40 @2.25).
- **Fakt:** GSQ na GGUF Qwen3-8B: Q2_K +6.25 pkt, Q3_K_M +1.09 pkt. Q4_K nie badano. ISTA nie wydało tieru ≥ 4 bpw.
- **Fakt:** plik ISTA IQ3_S ma `output.weight` w Q4_K, `token_embd` w IQ2_S i typy mieszane w obrębie warstwy (histogram w §3.3).
- **Fakt:** SLQ: EAR = Σmin(p,q) = 1 − TV, czyli akceptacja „kwant jako drafter BF16”. Accuracy jest płaskie do KL ≈ 0.01. Symetryczne siatki mają γ² większą wariancję (asymetria potrzebna do wierności rozkładu). Qwen3.5-27B: TL 3.30 bpp, DL 5.19 bpp.
- **Fakt:** `gptq-gguf-toolkit` (Helcig/Kleinegger, 2025) = GPTQ → Q2_K…Q6_K + EvoPress + stitcher GGUF, ale bez licencji.
- **Korekta:** QuIP# to Cornell, MicroMix to Tianjin University, nie ISTA.
- **Wniosek:** dla 24 GB GSQ-RCO nie daje nic gotowego. Jedyny transfer to metryka EAR oraz ewentualnie własna alokacja per tensor ograniczona do typów z szybkim MMVQ (eksperyment z bramką kill, zysk ≤ +7% t/s `[INFERENCE]`).
- **Śledzić:** publikację kodu K-quant/IQ w `IST-DASLab/GSQ`; nowy tier ≥ 4 bpw od ISTA-DASLab na HF.
- Wersje bazowe: `IST-DASLab/GSQ@03fc164`, `IST-DASLab/RCO@9a1e09c`, `IST-DASLab/SLQ@eb9f1f2`, `IST-DASLab/gptq-gguf-toolkit@7a38bc5`.

## 8. Źródła

- GSQ: https://arxiv.org/abs/2604.18556 (HTML v2: §1, §3, §4.2, Tab. 2, 4, 5, 10; App. C, E, F, G.4) · https://github.com/IST-DASLab/GSQ (README; gałęzie `fix/qwen`, `gsvq-iquant-qwen3-sweep-results`, `new_calib_data`, `feature/aln-binary-fixed-ternary`, `sharded-mlp-forward`)
- RCO: https://arxiv.org/abs/2605.00649 (HTML v3: Tab. 2–4) · https://github.com/IST-DASLab/RCO (README, `src/manifold.py`, `src/search/quant.py`)
- SLQ: https://arxiv.org/abs/2605.02404 (HTML v2: Tab. 1, 3, 5; Fig. 1b) · https://github.com/IST-DASLab/SLQ · https://openreview.net/forum?id=Xq1atP3a6S
- https://github.com/IST-DASLab/gptq-gguf-toolkit (README; API GitHub: brak licencji)
- Disaggregated Quantization: https://arxiv.org/abs/2609.26333
- Karty HF: https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF (README, `tensor-allocation/Qwen3.8-27B-GSQ-RCO-IQ3_S.rco-allocation.txt`) · https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-3Bit-GSQ · https://huggingface.co/collections/ISTA-DASLab/gsq-rco-gguf · API `huggingface.co/api/models?search=GSQ-RCO` (2026-10-21)
- Autor: https://github.com/helcig (X: https://x.com/mhelcig) · https://scholar.google.com/citations?user=7dWcmfcAAAAJ · https://www.alphaxiv.org/ja/@michael-helcig · https://arxiv.org/html/2609.39560v1 (afiliacja ETH, współautor z EPFL) · https://github.com/mkleinegger
- Weryfikacja prac DASLab (API arXiv): 2210.17323, 2401.06118, 2408.11743, 2411.17525, 2410.14649, 2509.23202, 2602.03537. Atrybucje spoza ISTA: 2402.04396 (QuIP#, Cornell), 2508.02343 (MicroMix, TJU).
- Kolizja nazwy: https://arxiv.org/abs/2502.12913 (GSQ-Tuning, inna grupa)
- Nasze: R15e (`15e-kwantyzacja-nowa.md`), R16e (`16e-kwanty-kld.md` §2.1), R18 (`18-nastepna-fala.md` §3.1), [[ista-daslab]]
