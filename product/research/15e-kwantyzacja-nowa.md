# 15e: Nowe formaty niskobitowe dla modeli klasy 27B na kartach 12–16 GB

Data: 2026-10-16. Autor: podagent ResQuant.

Zakres:
- Swift-1.5-Qwen3.8-27B-GSQ-RCO na tle ISTA GSQ-RCO, Underdog Saluki 27B i Ternary Bonsai 2 27B;
- `nvidia/Qwen3.8-Flash-Next-FP4-Local`, czyli „nowa technika NVFP4”;
- przegląd pozostałych metod niskobitowych z 2026 r., które mają wsparcie GGUF.

Nie używałem lokalnego GPU i nie wydałem ani dolara w chmurze. Wszystko poniżej pochodzi z:
- odczytów HTTP range nagłówków GGUF i safetensors;
- kodu źródłowego (ggml, FlashInfer b12x, GSQ, RCO);
- kart modeli i trzech eksperymentów CPU-offline (§4.4).

Skrypty leżą w `15e-skrypty/`.

Akapit o YAML z cytowanego posta nie dotyczy tematu, więc go pomijam.

---

## TL;DR

1. **„2-bit to szum” to fałsz w sensie dosłownym, ale 2 bity są wyraźnie stratne.**
   - ISTA GSQ-RCO IQ2_XS (2.50 bpw, 8.42 GB) ma KLD do BF16 0.194 (wiki, ctx 512) i 0.204 (ctx 2048, pomiar niezależny).
   - W zadaniach: AIME25 96.7 vs 100, GPQA-D 84.9 vs 89.9, LCB v6 76.6 vs 85.7.
   - Saluki (~2.35 bpw): AIME25 79.2 vs 96.7.
   - Model działa i jest użyteczny, tylko nie jest „prawie bezstratny”. Dla porównania UD-Q4_K_XL ma KLD 0.012.
2. **„GSQ-RCO to state of the art” jest prawdą tylko w wąskiej klasie:** skalarne typy GGUF/IQ, stock llama.cpp, ≤ 3 bpw, metryki zadaniowe.
   - Niezależne KLD na tym samym protokole (agentionai: 60×2048, BF16, llama.cpp `26bc85e42`) pokazuje, że GSQ-RCO IQ3_S (11.29 GiB) ma na wikitext **gorszy** KLD niż UD-IQ3_S tej samej wielkości: 0.0665 vs 0.0470.
   - Na tekście held-out GSQ wypada minimalnie lepiej: 0.0594 vs 0.0617.
   - Trellis z ik_llama (KTopt, 10.31 GB) ma KLD 0.043/0.066 (kod/proza), a GSQ IQ3_XXS (10.09 GB) 0.060/0.078.
   - Sam artykuł GSQ przyznaje, że GSQ jest za QTIP.
3. **Swift 1.5 to inny model, nie lepsza kwantyzacja.**
   - To fine-tune RL/OPD Qwen3.8-27B (UkisAI) na „krótsze myślenie”. Deklaracja: −41.9% średnio i −58.5% w medianie tokenów myślenia na GPQA-D przy +0.31 pp.
   - Kwanty GSQ-RCO Swifta to:
     - **dosłownie ta sama alokacja per tensor co ISTA** (zweryfikowałem `diff`: IQ2_XS i IQ3_S identyczne);
     - plus imatrix „V1MIX” i nieopublikowany skrypt refinementu GSQ (`refine_gguf_fast.py`).
   - Ich KLD (0.190 / 0.135 / 0.098 / 0.051) jest mierzony do **własnego** BF16 Swifta, a ISTA do BF16 Qwena. To nie jest porównanie jabłek z jabłkami.
   - **Głowica MTP Swifta jest bajtowo identyczna z głowicą Qwena** (porównałem po 2 × 1 MiB w trzech tensorach MTP; trunk i embeddingi się różnią). Nikt jej nie douczył po RL, więc akceptacja MTP na Swifcie jest niezmierzona i zagrożona.
   - Licencja: Swift Open License v1.0, czyli użycie komercyjne tylko poniżej US$1M przychodu rocznie. To ryzyko dla produktu.
4. **„Nowa technika NVFP4” to dwie rzeczy, obie poza naszymi kartami:**
   - (a) **CSF**, bezstratna kompresja skal bloków E4M3: 4-bitowe offsety od bazowego bajtu na wiersz plus wyjątki u32. Zmierzyłem 53–55% surowego rozmiaru skal, czyli −0.23 bpw z 4.5. Cały checkpoint jest mniejszy o 3.4%.
   - (b) **QAD**, destylacja świadoma kwantyzacji z lossem TV + hidden-state + „boundary losses”: GPQA-D 91.5 vs 92.2 BF16.
   - Sam model to Flash-Next, MoE 125B (+51B n-gram, +4B MTP), **96 GiB**. Działa tylko w kontenerach vLLM (RTX PRO 6000 96 GB, DGX Spark). Na 16/24 GB nie wchodzi.
   - Licencja: NVIDIA Open Model Agreement + Qwen Community License 1.0. Klauzula „Model as a Service / AI Work Assistant” wymaga osobnej licencji Qwen.
   - llama.cpp ma arch `qwen4exp`, ale nie dekoduje CSF.
5. **Nowe znalezisko z kodu: słaba jakość społecznościowych NVFP4 GGUF to w dużej mierze wada kwantyzatora ggml, a nie samego FP4.**
   - `quantize_row_nvfp4_ref` (`ggml-quants.c:384-417`) liczy `d = UE4M3(amax/6)` bez skali globalnej per tensor. `quantize_nvfp4` robi `GGML_UNUSED(quant_weights)`, czyli ignoruje imatrix.
   - Skutek w pliku, który mierzyliśmy na 5060 Ti (KLD 0.0865): w tensorach przekwantyzowanych przez `llama-quantize` **99.8–100% skal to subnormalne UE4M3**, a różnych wartości jest tylko 6–14.
   - Symulacja CPU na prawdziwych wagach BF16 Qwen3.8-27B: dodanie skali globalnej obniża względny MSE wag o **22–35%**, do 1–3% od ideału ze skalą float.
   - Poprawka to 1–2 osobodni. Graf już mnoży przez `*_s` (`llama-graph.cpp:1599-1601`).
6. **Najlepszy stosunek zysk/koszt na naszych kartach to nie nowy format, tylko MTP na istniejących 2-bitowych plikach dla 12 GB:**
   - Saluki z doszczepioną głowicą MTP (Kujira) na RTX 3080 12 GB: **41.2 → 66.2 t/s** (×1.61).
   - ISTA i Swift mają gotowe pliki `-mtp`.
   - Nasz pomiar 3060 (23.4 t/s, bez MTP) zostawił ten zysk na stole.
7. **Bezstratna kompresja skal (pomysł CSF) dla naszych K-quantów: odrzucone offline.**
   - Entropia rzędu 1 skal w UD-Q4_K_XL daje sufit oszczędności **2.19%** bajtów, czyli za mało na nowy typ ggml.
   - Dla NVFP4 w GGUF: −5.4% (CSF) do −8% (entropia). Odkładamy, bo NVFP4 w dekodowaniu nie jest naszą ścieżką.
8. **Rekomendacja dla 16 GB: zostać przy UD-Q3_K_XL albo przejść na AP-Q3_K_XL (te same bajty).**
   - Według agentionai AP-Q3_K_XL ma KLD held-out o 19.5% niższy.
   - GSQ-RCO IQ3_S jest 10% mniejszy, ale ma ~2× wyższy KLD na wikitext (0.0665 vs 0.0337), więc przegrywa na kryterium „najpierw jakość”.
   - Rozstrzygnie eksperyment E1 (§5), koszt ≈ $5–8 (wariant chmurowy) lub ≈ $2–3 + ~12–16 h CPU.

---

## 1. Audyt twierdzeń

Legenda werdyktów:
- **P**: wiarygodne;
- **PS**: wiarygodne tylko przy specjalnym obciążeniu;
- **N**: niewiarygodne;
- **U**: nie do zweryfikowania.

Pasma pamięci: 3060 360 GB/s, 3080 760 GB/s, 5060 Ti 448 GB/s, 3090 936 GB/s.

| # | Twierdzenie (dokładnie) | Źródło | HW | Model / kwant | Obciążenie, batch, ctx | Baseline (strojony?) | Jakość mierzona? | Komenda? | Roofline / Amdahl | Werdykt |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | „2-bit is noise” (post użytkownika) | post | — | 2-bit 27B | — | — | — | — | IQ2_XS: KLD 0.19–0.20; top-1 dla 2 bitów nieopublikowane (AP-IQ3_XXS held-out 85.8%, a 2 bity niżej `[SZACUNEK]`); MMLU-Pro (70 pyt.) GSQ IQ2_S 75.7% (agentionai); AIME25 −3.3 pp, GPQA −5 pp, LCB −9 pp (ISTA) | **N** dosłownie. Stratne, ale nie szum |
| 2 | „GSQ-RCO is state of the art” | post; karta ISTA | H200/B300 (kwantyzacja) | GSQ-RCO 2.5–3.5 bpw | PPL wiki/C4/FW, 5 zero-shot, AIME25/GPQA/LCB, 1 run | UD-IQ2_S / UD-Q2_K_XL / UD-IQ3_S (UD 3.0, rozsądny baseline) | tak (PPL, zadania) | brak komend ewaluacji | n/d | **PS**: prawda przy tym samym rozmiarze wobec UD na metrykach zadaniowych przy ≤ 3 bpw; nieprawda dla KLD przy 3.5 bpw (0.0665 vs UD-IQ3_S 0.0470) i wobec trellis (KTopt) |
| 3 | „IQ3_S is task-lossless” (AIME25 100 = 100, LCB 85.71 = 85.71, GPQA −0.51) | karta ISTA | ? | GSQ-RCO IQ3_S 11.8 GB | AIME25 n=30 (BF16 = 100%, sufit), GPQA n=198 (1 pyt. = 0.505 pp), LCB n≈175 | BF16 | tak, 1 run | nie | KLD 0.052 (ctx 512) / 0.0665 (ctx 2048) ≫ UD-Q4_K_XL 0.012 | **PS**: bezstratny w zadaniach w granicach szumu i sufitu, nie w rozkładzie |
| 4 | „IQ2_XS zero-shot above BF16” (74.54 vs 74.34) | karta ISTA | ? | IQ2_XS | arc/hella/wino/piqa | BF16 | tak | nie | różnica 0.2 pp, w szumie; zero-shot MC jest mało czuły | **P** liczbowo, ale bez znaczenia |
| 5 | MTP: średnia akceptacja 54.2%, 3 tokeny draftu, ~100–118 t/s | wykres ISTA (`…mtp_speculative_decoding.png`) | **nieujawniony** | 4 kwanty -mtp | llama.cpp speed-bench, 5 próbek na kategorię | brak baseline bez MTP | — | nie | tok/krok ≈ 1 + 3·0.542 = 2.63 → 38–45 kroków/s → efektywnie 0.32–0.53 TB/s wag. Wymaga GPU klasy ≥ 3090; na 3060 sufit to ~43 kroki/s przy 100% pasma (realnie ~50%) | **PS / U** (sprzęt nieznany) |
| 6 | Swift: „58.5% fewer thinking tokens while scoring 0.35% higher … 1.95× speed-up” | karta BF16 Swift | vLLM 0.27.1, BF16 | Swift 1.5 BF16 | 8 benchmarków, 5 seedów, T=1, ctx 262k, effort xhigh | Qwen3.8-27B BF16, ten sam protokół | tak | ustawienia opublikowane, brak skryptów | 58.5% to **mediana GPQA-D**, średnia to 41.9%. Inne: IFBench −1.46 pp, ERQA −2.05, AIME26 −2.67, HMMT −2.0, LCB +4.95, TB2.1 +2.92 | **P** jako deklaracja vendora; niezależnie niezweryfikowane |
| 7 | „9.18× speed-up on several tasks” (karta GSQ) vs „1.95×” (karta BF16) | dwie karty UkisAI | — | — | 9.18 = 104.6 / 11.39 min, czyli **jedno demo** (gra 3D) | base Qwen | — | — | Amdahl: −58.5% tokenów daje ≤ 2.4×. 9.18× wymaga −89% tokenów albo zapętlenia bazy | **PS** (jeden prompt); karty są ze sobą niespójne |
| 8 | Kwanty Swift „improve KLD over matched Swift starting quants… not uniformly better than ISTA” | karta GSQ Swift, `evaluation/heldout-kld.tsv` | ? | 4 tiery | wiki dev (użyty do strojenia!) + 7 domen held-out, ctx 512, 25–100 chunków | ISTA (inny BF16), transplant Swifta | KLD | brak komend | Δ vs transplant: −2.5…−19%; vs ISTA: proza −2…−9%, matematyka **+4.9…+7.7%**, zh −18…−32% | **P** dla „refinement > zwykły imatrix”; **U** dla „lepszy niż ISTA” (różne referencje) |
| 9 | Saluki: tool calling 88 vs 84 (pełny model), parallel 42 vs 35, „96% retention” | karta Saluki | stock llama.cpp | IQ2-mix 7.89 GB | BFCL v4 120 zadań, thinking off, T=0 | Qwen3.8-27B własnym harnessem; reszta to „public” z innego harnessu | tak | nie | SE ≈ √(0.7·0.3/120) ≈ 4.2 pp → 88 vs 84 mieści się w szumie | **P** „zachowuje tool calling”; **N** „lepszy od pełnego” |
| 10 | Bonsai 2: „98.2% of FP16 intelligence”, 84.78 vs IQ2_XXS 72.59 | karta / whitepaper PrismML | M5 Max (prędkość) | PTQ1_0 5.95 GB | 14 benchmarków thinking | UD-IQ2_XXS | tak | whitepaper | nasz pomiar: PPL 8.62 vs Saluki 7.67, błędy w polskim | **PS** (miks benchmarków vendora) |
| 11 | Flash-Next FP4-Local: GPQA-D 91.5 vs 92.2, ToolEvalBench 88.7 vs 89.4 | karta NVIDIA | RTX PRO 6000, DGX Spark | QAD NVFP4 + MXFP8, 96 GiB | 2 benchmarki | BF16 | tak | kontenery | n/d (brak deklaracji prędkości) | **P**, ale nie dla naszych kart |
| 12 | CSF: „lossless”, skale 7.55 → 3.97 GB, checkpoint 106.33 → 102.76 GB | karta local-inference-lab, `nvfp4_csf.py` | — | Flash-Next NVFP4 | — | surowe skale E4M3 | bitowa rekonstrukcja (SHA-256) | `trellis_quant … verify` | mój odczyt nagłówka: down 54664/102400 B = 53.4%, gate 54.7%, up 53.7%; kodek całkowitoliczbowy | **P** (zweryfikowane konstrukcją i nagłówkiem) |
| 13 | GSQ: 6.2× przepustowości vs BF16 (Llama-70B, L40S, vLLM + Humming) | arXiv 2604.18556, Tab. 2 | L40S | uniform 2-bit | ShareGPT, batch serving, TPS na GPU | BF16 na **4 GPU** | — | — | sufit bajtowy 16/2 = 8×; normalizacja na GPU | **PS** (serwowanie batchowe, metryka na GPU) |
| 14 | Saluki + MTP (graft): 41.2 → 66.2 t/s, akceptacja 62–96% | karta Kujira | RTX 3080 12 GB, WSL2 | Saluki + głowica Q8_0 | 6 promptów, T=0, n-max 2, ctx 32k | ten sam plik bez MTP | nie (zastrzeżenie o rozjazdach greedy) | tak | 8.35 GB · 23–30 kroków/s = 25–33% pasma, a plain 41.2 t/s = 43% pasma (u nas na 3060 51%) | **P** |
| 15 | KTopt (ik_llama trellis) 10.31 GB: KLD 0.0429 / 0.0662 vs GSQ IQ3_XXS 0.0602 / 0.0783 | karta wiklif | ? | mix IQ2/3/4_KT | ctx 4096, kod 16 / proza 8 chunków | UD, ISTA, BF16 | KLD + zadania (z CI) | częściowo | n/d | **P** (jeden autor, tylko ik_llama) |
| 16 | AP-GGUF: „closest to Qwen at every size” | karta agentionai | ? | AP-* | 60×2048, 3 korpusy (held-out niejawny) | UD, ISTA, AtomicChat | KLD | **tak, dokładne komendy** | n/d | **P** dla wikitext i web (sprawdzalne); held-out nie do odtworzenia |

---

## 2. Mechanizm: co dokładnie robią te metody

### 2.1 GSQ (Gumbel-Softmax Quantization), ISTA-DASLab, arXiv 2604.18556

- PTQ warstwa po warstwie.
  - Inicjalizacja GPTQ (albo RTN).
  - Każda współrzędna wagi ma wektor logitów nad **małą** siatką: 2 poziomy dla znaku/maski tritów, 4 dla 2 bitów, 8 dla 3 bitów.
  - Próbka Gumbel-Softmax daje miękki one-hot. Temperatura τ maleje od wysokiej do niskiej, skala logitów κ rośnie od niskiej do wysokiej.
  - Loss to rekonstrukcja wyjścia warstwy na danych kalibracyjnych. Skale grup uczą się razem z przypisaniami (Lion/Adam).
  - Na końcu jest twardy argmax, czyli z powrotem zwykły skalarny format grupowy.
- Teza artykułu: luka między skalarnym a VQ/trellis (QTIP, AQLM) to w dużej części **luka optymalizacyjna**, nie reprezentacyjna. Mimo to GSQ dalej przegrywa z QTIP (artykuł, §4.2).
- GGUF:
  - README GSQ pokazuje refinement K-quantów in-format: Qwen3-8B Q2_K, średnia 50.03 → 56.28.
  - **Kod refinementu typów IQ (IQ1_S…IQ3_S) nie jest na `main`.** Na gałęzi `gsvq-iquant-qwen3-sweep-results` (`docs/gsvq_iquants.md`, commity `7235dadb4f`, `4acc593182`, 2026-05-16) jest GSVQ dla IQ-quantów: Gumbel-Softmax nad kandydatami z codebooka przy stałych skalach.
  - Wynik autorów: **MSE wag spadł o 2.6–2.7%, a KL end-to-end wzrósł o 1.9–4.2%** (Qwen3-4B UD-Q2_K_XL, wikitext 256 tok). Ich wniosek: potrzebna jest akceptacja aktywacyjna lub świadoma KL.
  - Produkcyjna ścieżka, którą zbudowano Qwen3.8-27B GSQ-RCO (2026-08-28), jest więc **nieopublikowana**.
  - UkisAI przy Swifcie używa `refine_gguf_fast.py` z „Astra IQ1 stage_objective patch” i TileLang backward (`RECIPE.txt`). Tego też nie ma publicznie (`gh search code refine_gguf_fast` zwraca tylko dokument osoby trzeciej).
- Koszt: README GSQ podaje 1× H100/A100 80 GB dla 8B i 4× H100 dla 70B. Wyniki z artykułu to „single run per configuration” (§4.1).

### 2.2 RCO (Riemannian Constrained Optimization), arXiv 2605.00649, `IST-DASLab/RCO`

- Problem: każdy z N tensorów dostaje jeden z K typów kwantu przy budżecie średnich bitów. Loss całego modelu nie rozkłada się na tensory.
- Mechanizm (`src/search/quant.py`):
  - Softmax nad typami daje interpolowany model Σ p_k·W_k, gdzie W_k to wcześniej skwantyzowane warianty, „baza danych” z GSQ.
  - Loss to KL lub CE do nauczyciela.
  - Gradient jest rzutowany na płaszczyznę styczną ograniczenia budżetu, potem krok Adama.
  - Retrakcja to binary search przesunięcia logitów wzdłuż wektora kosztów (`retract`, `init_alpha_to_bits`).
  - Na koniec DP plecakowe po budżecie (`round_with_budget_dp`, `quant.py:362`) wymusza twardy budżet.
- Wynik zapisuje się jako plik alokacji `tensor-allocation/*.rco-allocation.txt`, czyli lista `tensor: typ`.
  - Każdy może go odtworzyć przez `llama-quantize --tensor-type-file`. Tak zrobił UkisAI.
  - Same wagi GSQ wymagają jednak kodu z §2.1.
- Przykładowa alokacja IQ2_XS (ISTA): `token_embd` IQ1_M, `output` IQ4_XS, `ssm_alpha/beta` BF16, a `ffn_gate` w warstwie 0 IQ1_S. Histogram typów jest w §3.

### 2.3 Swift 1.5 (UkisAI): co dodaje

- **Fine-tune trunku:** NOTICE mówi, że wagi Swift 1.0 „further adapted… using additional post-training methods”. Karta: RL + OPD, kara za tokeny związane z „pathological overthinking”. Dane: `ukisai/Qwen3.8-27B-multi-turn-agent-sft` (przepróbkowane).
  - Config jest identyczny z Qwenem (`qwen3_5`, 64 warstwy).
  - Zweryfikowałem, że `embed_tokens` i `layers.10.mlp.down_proj` różnią się od Qwena.
- **Głowica MTP nieruszona:** `mtp.fc`, `mtp.layers.0.mlp.down_proj`, `mtp.layers.0.self_attn.q_proj` mają identyczne SHA-256 dwóch próbek po 1 MiB (początek i środek tensora) w obu repo.
  - `mtp_use_dedicated_embeddings=false`, więc głowica MTP Qwena dostaje hidden state i embeddingi **zmienione** przez RL.
  - Wniosek `[INFERENCE]`: akceptacja MTP na Swifcie jest raczej niższa niż na Qwenie. Karta przyznaje: „MTP decoding speed and quality have not been separately evaluated”.
- **Kwanty GSQ-RCO:**
  1. Alokacja ISTA użyta 1:1 (`diff` alokacji IQ2_XS i IQ3_S: identyczne, 851 tensorów).
  2. imatrix V1MIX: fineweb-edu 30 / OpenThoughts3 30 / multilingual wiki 20 / code 12 / Platypus 8, 309 × 4096 tokenów. Nagłówek GGUF: `quantize.imatrix.chunks_count = 2472`.
  3. Refinement GSQ: 512 × 2048 tokenów, 3 epoki, `--lr-scale-iq 1e-3`.
  4. Pliki `-mtp` dostają głowicę Q6_K/F32 (`blk.64`, 15 tensorów), czyli głowicę Qwena (patrz wyżej).
  - Zysk samego imatrixa V1MIX vs imatrix ISTA: −0.8…−1.3% KLD (wiki). Zysk refinementu vs „transplant” (kwant Swifta tym samym przepisem bez refinementu): −2.5…−19% zależnie od domeny (`heldout-kld.tsv`).
- **Pliki** (nagłówki range-read): IQ2_XS 8.42 GB / 2.502 bpw; IQ2_S 9.26 / 2.751; IQ3_XXS 10.09 / 2.999; IQ3_S 11.77 / 3.498. Wersje `-mtp` są większe o +0.35 GB.
  - Arch `qwen35`, ten sam tokenizer i szablon (8952 znaki).
- **Licencja:** Swift Open License v1.0.
  - Apache-podobna, z §5 „Commercial Use Limitation”: prawa komercyjne tylko przy przychodzie brutto < US$1M (łącznie z podmiotami powiązanymi). Powyżej trzeba kupić „Swift Enterprise License”.
  - §12: automatyczne wygaśnięcie licencji przy naruszeniu.
  - Dla produktu, który ludzie i firmy pobierają, jest to klauzula, której nie da się egzekwować po stronie użytkownika. Ryzyko dla B2B.
- **Istnieje też `ukisai/Swift-Bonsai-2-GGUF`** (PTQ1_0 5.95 GB, Apache-2.0), czyli ta sama obróbka na Bonsai 2. Według analizy osoby trzeciej (yamadori) karta przyznaje „little token saving” `[NIEZWERYFIKOWANE]`.

### 2.4 Saluki i Bonsai (krótko, reszta w raporcie 09)

- **Saluki:** nagłówek ma `general.name = "Qwen3.8-27B GSQ-RCO"`, `quantized_by = ISTA DASLab`, imatrix ISTA (1000 chunków).
  - To plik z potoku ISTA z **własną, niższą alokacją** (~2.35 bpw, IQ2_XXS na 34% elementów) poniżej najmniejszego tieru ISTA.
  - „Strojenie pod tool calling” nie jest opisane `[NIEZWERYFIKOWANE]`.
  - Brak głowicy MTP. Graft od Kujiry (`Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF`, 8.35 GB, `graft_mtp.py`) dokłada głowicę Qwena w Q8_0.
- **Bonsai 2:** trity g128 w bazie Hadamarda (blok 1024). PQ2_0 7.21 GB / 2.13 bpw, PTQ1_0 5.95 GB / 1.75 bpw. Metoda treningu nieujawniona, Apache-2.0.
  - Na 3060 PTQ1_0 daje 44.75 t/s, czyli 266 GB/s ≈ 74% pasma. To najlepsza efektywność wśród 2-bitowych.

### 2.5 Dlaczego 2-bitowe IQ są wolne na 3060 (łączy się z naszym profilem)

- Raport 09 (§8): Saluki to ~95% MMVQ i-quantów przy **~180 GB/s (~50% z 360)**. Dekodowanie siatek (IQ2_XXS 31% czasu, IQ3_S 13%, IQ1_S 9%…) jest **ograniczone obliczeniami**.
- Pliki GSQ/Swift mają podobny miks typów (IQ2_XS: IQ2_XXS 18%, IQ2_S 14.7%, Q2_K 12.4%, IQ2_XS 12.7%, IQ1_M 10.6%, IQ1_S 9.6%, IQ3_XXS/IQ3_S po ~7.5%, IQ4_XS 6.6%). Należy się więc spodziewać tej samej efektywności, czyli dla IQ2_XS 8.42 GB ~21–22 t/s bez MTP `[SZACUNEK]`.
- To tłumaczy, dlaczego na 12 GB dźwignią jest MTP (więcej tokenów na krok) i długość myślenia (mniej tokenów), a nie kolejny format.

### 2.6 NVFP4 „nowe”: CSF + QAD (Flash-Next FP4-Local)

- **CSF**, kodek `byte-window4-fixed-stream-u24-exceptions/1` (`flashinfer/experimental/b12x/_lib/quant/nvfp4_csf.py`, commit `fc8fdc17f7` 2026-10-06):
  - Dla każdego wiersza skal jest 1 bajt bazy, a każda skala E4M3 to 4-bitowy offset od bazy, `fixed` = `rows/16 × 16·(1 + cols/2)` bajtów.
  - Skale spoza okna [base, base+15] trafiają do listy wyjątków u32: 24 bity pozycji + 8 bitów wartości, posortowane, podzielone na partycje po 128 wierszy.
  - Dekodowanie to arytmetyka na bajtach (`values = spread(nibbles) + base*0x01010101`; baza ≤ 240, więc bez przeniesień).
  - W runtime jeden grid rozwija skale **tylko aktywnych ekspertów** (`decode()` z `mode 0/1/2`, a dla długiego prefill `decode_all`) do scratch w natywnym układzie `F8_128x4`. Potem GEMM czyta zwykłe skale.
  - Zysk polega więc na **pojemności** (VRAM i dysk). Dla dekodowania to zysk tylko pośredni: mniej bajtów skal z HBM, w zamian dodatkowy kernel i zapis do scratch (L2).
  - W `nvfp4_csf_inline` (IndexedNvfp4Plane) jest też wariant „inline” w GEMM.
  - Mój odczyt nagłówka safetensors (shard 1): `down_proj` [2560×640]: surowe skale 102400 B → fixed 53760 + wyjątki 904 B = **53.4%**; gate 54.7%; up 53.7%. Skale NVFP4 kosztują 0.5 bpw, a po CSF ~0.27 bpw, czyli **4.5 → ~4.27 bpw (−5%)** na tensorach eksperckich.
  - Ekspertów MTP, wizji i skal globalnych nie kompresuje się.
- **QAD**: nauczycielem jest BF16, który generuje odpowiedzi i daje cele per token (prawdopodobieństwa + hidden states).
  - Loss: **total variation** na rozkładzie next-token + dopasowanie hidden state + osobne straty dla końca odpowiedzi i końca myślenia („boundary losses”).
  - 500M tokenów × 3 epoki; 2 500 kroków trunku + 1 500 kroków wspólnego refinementu (z tabelami n-gram i symulowanym MXFP8 dla shared experts). Attention zamrożona w MXFP8.
  - To samo podejście co oficjalny LFM2.5 QAD-Q4_0, który zmierzyliśmy: KLD 0.203 ≈ Q4_K_M.
- **Model:** `Qwen4ExpForConditionalGeneration` (`qwen4_exp`): 48 warstw, hidden 2560, 512 ekspertów / top-10, PLE n-gram (51B), hyper-connections (`hc_count 4`), Qwen Sparse Attention (indexer).
  - 21 shardów ≈ 102.9 GB (96 GiB). Nie wchodzi w 16/24 GB. Nawet sama aktywna ścieżka (6B × ~4.3 bit ≈ 3.2 GB/token) wymaga całego modelu w pamięci albo offloadu ekspertów.
  - llama.cpp upstream ma `qwen4exp` (commity `37b53fd45` hc ops, `c061df198` MTP, `3cf03257f` sparse FA). `convert_hf_to_gguf.py` nie zna `weight_scale_encoding: csf` (grep: 0 trafień), więc najpierw trzeba odtworzyć standardowe skale (`trellis_quant… restore` albo prosty dekoder).

### 2.7 Wada kwantyzatora NVFP4 w ggml (znalezisko tego raportu)

- `ggml-quants.c:384-417` `quantize_row_nvfp4_ref`: `ue = ggml_fp32_to_ue4m3(amax/6)`. Nie ma skali per tensor. `quantize_nvfp4` (`:2309-2313`) ignoruje imatrix.
  - UE4M3 ma najmniejszą wartość normalną 2⁻⁶ = 0.0156. Subnormalne to `man·2⁻⁹`, man 1…7 (`ggml-impl.h:541-551`).
  - Wagi Qwen3.8-27B mają std ≈ 0.011–0.016, więc amax bloku 16 / 6 ≈ 0.004–0.01 i **niemal wszystkie skale lądują w 3–5 kodach subnormalnych**. Krok kwantyzacji skali to 2⁻⁹ ≈ 20–50% wartości.
- Prawdziwe checkpointy ModelOpt mają `weight_scale_2` (FP32 per tensor). llama.cpp przy konwersji ModelOpt/compressed-tensors zapisuje je jako `*.scale`, a graf mnoży wynik matmula przez `w_s` (`llama-graph.cpp:1599-1601`).
  - Problem dotyczy więc **tylko tensorów przekwantyzowanych przez `llama-quantize`**.
- Dowód w pliku, który mierzyliśmy (esatapedico VERY-LOW, KLD 0.0865):
  - `blk.30.ffn_down` (natywny z ModelOpt, ze skalą): 0% subnormalnych, 29 wartości.
  - `blk.30.attn_qkv` (przekwantyzowany z BF16): **99.8% subnormalnych, 14 wartości**.
  - `blk.60.ffn_up`: **100%, 6 wartości**.
- Upstream:
  - PR #22897 (skala globalna MSE-optymalna + `.scale`) zamknięty jako duplikat.
  - PR #25153 (scale search świadomy imatrix + ftype NVFP4) jest **otwarty** od 2026-06-30. Mieszane wyniki: KLD −1.6%, PPL +0.57% na Qwen3.6-35B-A3B.
  - PR #26556 (WhiskyAKM: LFM NVFP4, który zmierzyliśmy, KLD 1.18) zamknięty bez merge'a.

### 2.8 Pozostałe metody 2026 z GGUF (skrót; szczegóły z podagenta, źródła w §7)

- **ik_llama.cpp `IQ*_KT`** (trellis całkowitoliczbowy, nie QTIP-kompatybilny):
  - bpw: IQ1_KT 1.75, IQ2_KT 2.125, IQ3_KT 3.125, IQ4_KT 4.0. Superbloki 256, skale 4-bit na 32, float na wiersz.
  - Pełne wsparcie tylko CPU i CUDA. Vulkan ma tylko IQ4_KS/IQ4_KT, HIP idzie ścieżką dp4a (testowano gfx1030), Metal IQ4_KT odpada. HEAD `8d21687c` (2026-10-16).
  - **Port IQK do upstream odrzucony** (PR #19726, zamknięty 2026-02-23, powody licencyjno-osobowe).
  - Najlepszy publiczny plik: wiklif KTopt 10.31 GB, KLD 0.043/0.066 (ctx 4096) vs UD-IQ3_XXS 0.049/0.078 vs GSQ IQ3_XXS 0.060/0.078.
  - Wzorzec portu: `lrozewicz/kt-llama-cpp` (`6f526e454`, `ggml_row_meta_size`).
- **Unsloth Dynamic 3.0** (27B od 2026-08-19): nowy imatrix (agentic/chat/multilingual), czyste PTQ, metryka „Divergence-300 @32”. KLD publikowane tylko na wykresach.
- **EXL3** (QTIP-pochodny, v1.6.2 `4c842731`): ROCm in-tree od 2026-10.
  - Qwen3.8-27B 4.0 bpw na gfx1100 ~15 t/s decode (PR #283 `[NIEZWERYFIKOWANE]`).
  - W niezależnym teście (xenodeve, 4070S + 5060 Ti) EXL3 4.0 bpw ukończył 6/6 zadań kodowych, GSQ IQ3_S-MTP 5/6, NVFP4 3/6.
  - Na ~140k kontekstu GSQ i NVFP4 psuły tajski (litery, łacińskie podstawienia).
- **Inne standardowe GGUF z KLD:** AP-GGUF (agentionai, Apache-2.0, 505k pobrań), APEX (mudler), BuffedMod (GSQ IQ3_S z `output` w Q6_K: KLD 0.0555 → 0.0517 za +0.2 GB), ByteShape (tylko metryki zadaniowe).

---

## 3. Tabela porównawcza (najpierw jakość)

Uwaga: KLD z różnych protokołów **nie są porównywalne**. Ten sam plik ISTA IQ3_S ma 0.0519 przy ctx 512 (protokół ISTA/Swift) i 0.0665 przy ctx 2048 (agentionai). Dlatego podaję osobne kolumny:
- **[A]** agentionai: wiki.test.raw, ctx 2048, 60 chunków, ref Qwen BF16;
- **[S]** protokół ISTA/Swift: wiki, ctx 512, 100 chunków, ref = **własny** BF16;
- **[W]** wiklif: ctx 4096, kod/proza, ref BF16;
- **[N]** nasz: wiki 64×512 PPL (3060) albo KLD vs Q8_0 20×512 (5060 Ti).

| Plik | GB | bpw | [A] KLD wiki / held-out | [S] KLD | [W] KLD kod/proza | [N] | Prędkość 3060 / 5060 Ti (publiczna albo nasza) | Runtime | Licencja |
|---|---|---|---|---|---|---|---|---|---|
| Qwen BF16 | 54.66 | 16 | 0 | 0 | 0 | — | nie mieści się | wszystkie | Apache-2.0 |
| UD-Q4_K_XL | 17.56 | 5.14 | 0.0122 / 0.0117 | — | — | — | (XTX 109 t/s MTP) | wszystkie | Apache-2.0 |
| AP-Q4_K_XL | 17.56 | 5.14 | 0.0118 / 0.0111 | — | — | — | = UD (te same typy) | wszystkie | Apache-2.0 |
| UD-IQ4_XS | 14.25 | ~4.2 | 0.0252 / 0.0276 | — | 0.0138 / 0.0187 | — | — | wszystkie | Apache-2.0 |
| NVFP4 VERY-LOW (esatapedico) | 14.86 | 4.35 | — | — | — | KLD 0.0865 (vs Q8_0) | 5060 Ti: tg 26.6, pp4096 1747; MTP 54.0 (greedy) | CUDA (FP4 TC: sm_120 prefill) | Apache-2.0 |
| **UD-Q3_K_XL** (nasz 16 GB) | 13.15 | 3.85 | 0.0337 / 0.0421 | — | 0.0228 / 0.0287 | KLD 0.0265 (vs Q8_0) | 5060 Ti: **51.7 MTP** / 28.9 plain (nasze) | wszystkie | Apache-2.0 |
| AP-Q3_K_XL | 13.15 | 3.85 | 0.0352 / **0.0339** | — | — | — | = UD | wszystkie | Apache-2.0 |
| UD-IQ3_S | 12.04 | 3.52 | **0.0470** / 0.0617 | — | 0.0330 / 0.0507 | — | — | wszystkie | Apache-2.0 |
| ISTA GSQ-RCO IQ3_S (-mtp) | 11.77 (12.12) | 3.50 | 0.0665 / 0.0594 | 0.0519 | — | — | RX 7800 XT Ollama 23.9 (llm-bench); 3060/5060 Ti: brak | wszystkie (typy standardowe) | Apache-2.0 |
| Swift GSQ-RCO IQ3_S | 11.77 | 3.50 | — | 0.0513 (vs Swift BF16) | — | — | brak | wszystkie | **Swift OL 1.0 (< $1M)** |
| UD-IQ3_XXS | 10.93 | 3.20 | — | — | 0.0487 / 0.0781 | — | — | wszystkie | Apache-2.0 |
| KTopt (wiklif) | 10.31 | ~3.06 | — | — | **0.0429 / 0.0662** | — | 4070 Ti S 38.5 t/s @64k | **tylko ik_llama** (CPU/CUDA) | Apache-2.0 `[NIEZWERYFIKOWANE]` |
| ISTA GSQ-RCO IQ3_XXS | 10.09 | 3.00 | 0.1063 / 0.1123 | 0.0981 | 0.0602 / 0.0783 | — | brak | wszystkie | Apache-2.0 |
| Swift GSQ-RCO IQ3_XXS | 10.09 | 3.00 | — | 0.0978 (vs Swift BF16) | — | — | brak | wszystkie | Swift OL |
| ISTA GSQ-RCO IQ2_S | 9.26 | 2.75 | 0.1470 / 0.1541 | 0.1351 | — | — | brak | wszystkie | Apache-2.0 |
| Swift GSQ-RCO IQ2_S | 9.26 | 2.75 | — | 0.1348 (vs Swift BF16) | — | — | brak | wszystkie | Swift OL |
| ISTA GSQ-RCO IQ2_XS | 8.42 | 2.50 | 0.2036 / 0.2263 | 0.1940 | — | — | brak | wszystkie | Apache-2.0 |
| Swift GSQ-RCO IQ2_XS | 8.42 | 2.50 | — | 0.1900 (vs Swift BF16) | — | — | brak (szac. 3060 ~21–22 plain) | wszystkie | Swift OL |
| UD-IQ2_S | 8.37 | 2.49 | — | — | — | — | — | wszystkie | Apache-2.0 |
| **Saluki IQ2-mix** | 7.90 | 2.35 | — | — | — | PPL 7.67 | 3060: **23.4** (nasze); 3080: 41.2 → 66.2 z MTP (Kujira) | wszystkie | Apache-2.0 |
| UD-IQ2_XXS | 7.27 | 2.16 | — | — | — | — | — | wszystkie | Apache-2.0 |
| **Bonsai 2 Q2_0** (repack) | 7.63 | 2.25 | — | — | — | PPL 8.62 | 3060: **35.5** (nasz fork) | upstream ≥ b11555 | Apache-2.0 |
| Bonsai 2 PTQ1_0 | 5.95 | 1.75 | — | — | — | PPL 8.62 | 3060: **44.75** (prism) | fork prism (CUDA/Metal) | Apache-2.0 |

Czego brakuje (i dlatego potrzebny jest E1):
- KLD Saluki i Bonsai w jakimkolwiek protokole;
- KLD po polsku dla czegokolwiek;
- KLD przy długim kontekście;
- prędkość GSQ/Swift na 3060 i 5060 Ti z MTP.

---

## 4. Transfer na nasz stos

### 4.1 Gdzie idą milisekundy

- **3060 + Saluki:** 46.2 ms/token (fork), z tego GPU busy 43.8 ms, ~95% to MMVQ i-quantów przy 50% pasma, a luka hosta 2.4 ms (5.2%).
  - Zmiana formatu w obrębie IQ2/IQ3 przesuwa ms proporcjonalnie do **liczby wag × koszt dekodowania siatki**, nie do bajtów.
  - Dźwignie: (a) tokeny/krok (MTP), (b) liczba tokenów odpowiedzi (Swift), (c) efektywniejszy format (PTQ1_0: 74% pasma).
- **5060 Ti + Q3_K_XL:** 35.3 ms/token plain przy 85% pasma. MTP: 48.6 ms/krok przy 2.48 tok/krok.
  - Format 10% mniejszy (GSQ IQ3_S) daje ≤ +10% decode, ale kosztem ~2× KLD.
  - Prefill: NVFP4 daje +65–69% pp. To jedyna dźwignia formatu na nasz słaby punkt TTFT, warunkowana naprawą jakości (§2.7).
- **Długi kontekst** (−30–41% przy 64k na 3090) jest ortogonalny do formatu wag. Format tego nie naprawi.

### 4.2 Ranking pomysłów: (zysk na wąskim gardle × pewność) / koszt

| # | Pomysł | Zysk na naszym profilu | Pewność | Koszt (osobodni / $) | Ryzyko (bit-exact / KLD) | Platformy | Wynik |
|---|---|---|---|---|---|---|---|
| 1 | **MTP na 2-bitowych 27B dla 12 GB**: Saluki-MTP (graft Kujira), ISTA/Swift `-mtp` + nasz stos MTP (draft vocab 64k, głowica iq4_xs) | 3060: ×1.4–1.6 decode `[SZACUNEK]`, z 3080 ×1.61 przy 43% pasma; nasz stos na 5060 Ti dał ×1.17 ponad flagi upstream | średnio-wysoka | 0.5 osobodnia + ~$1 | wyjście = ten sam model (graft nie zmienia trunku); greedy zmienia się przez batch verify (Kujira 5/6 rozjazdów przy near-tie), KLD do sprawdzenia | wszystkie (MTP w upstream); nasze łatki HIP/CUDA | **1** |
| 2 | **Podmiana kwantu przy tych samych bajtach**: AP-Q3_K_XL za UD-Q3_K_XL (16 GB), AP-Q4_K_XL za UD-Q4_K_XL (XTX) | jakość: held-out KLD −19.5% / −4.4%, wiki remis; prędkość 0 | średnia (vendor, ale komendy opublikowane) | 0.3 osobodnia + KLD-gate (w E1) | inny plik = inne md5; KLD gate | wszystkie (te same typy) | **2** |
| 3 | **Swift 1.5 jako tryb „krótkie myślenie”** | time-to-answer −25…−45% przy tym samym t/s, jeśli deklaracja przeniesie się na PL/czat `[SZACUNEK]` | nisko-średnia (jeden vendor, głowica MTP niedouczona, licencja) | 1 osobodzień + $2–3 | inny model; licencja < $1M | wszystkie | **3** (warunkowo: decyzja licencyjna) |
| 4 | **Naprawa kwantyzatora NVFP4 w ggml** (skala globalna per tensor → `.scale`, plus imatrix search z PR #25153) | jakość NVFP4 GGUF: rel-MSE wag −22…−35% (zmierzone CPU); otwiera prefill +65% na 5060 Ti przy akceptowalnym KLD `[SZACUNEK]` | średnia | 1–2 osobodni, $0 (CPU-KLD na małym modelu) | zmienia tylko kwantyzację (nowe pliki); kernele bez zmian | skala to `ggml_mul`, więc wszystkie; korzyść FP4 TC tylko sm_120 | **4** |
| 5 | GSQ-RCO IQ3_S zamiast Q3_K_XL na 16 GB | decode ≤ +10% (−1.38 GB) | niska dla jakości (KLD wiki 2×) | 0 (sam download) | KLD ↑ | wszystkie | 5: tylko jeśli E1-PL odwróci obraz |
| 6 | PL-imatrix + alokacja ISTA (przepis Swifta bez GSQ) | KLD-PL −2…−8% `[SZACUNEK]` (Swift: imatrix sam w sobie −0.8…−1.3% wiki) | niska | 1 osobodzień + ~$0.5 (imatrix na 24 GB) | inny plik | wszystkie | 6 |
| 7 | Port trellis KT (ik → nasz fork, wzór kt-llama-cpp) | jakość ~10 GB: KLD −29% vs GSQ IQ3_XXS; dekodowanie trellis jest obliczeniowe, a 3060 już jest compute-bound w IQ, więc prędkość niepewna | niska-średnia | 10–20 osobodni | nowy typ ggml, poza upstream (odrzucony) | CUDA (HIP dp4a niesprawdzone), bez Vulkan/Metal | 7 |
| 8 | Własny GSQ-refinement IQ (PL) | jakość | niska (kod IQ nieopublikowany; publiczny GSVQ pogarszał KL) | 5–15 osobodni + $6–16 | inny plik | wszystkie | 8 |
| 9 | Bezstratna kompresja skal K-quantów (CSF-like) | **≤ 2.19% bajtów** (zmierzony sufit) | wysoka (że mało) | 5+ osobodni | bit-exact | — | **odrzucone** |
| 10 | CSF dla NVFP4 w GGUF | −5.4% bajtów NVFP4, decode ≤ 5% tylko na plikach NVFP4 | średnia | 3–5 osobodni | bit-exact | CUDA | odłożone |

### 4.3 Co musiałoby się zmienić w llama.cpp i naszym forku

- **#1:**
  - Nic w ggml. W produkcie: profil 12 GB = plik z `blk.64` + `--spec-type draft-mtp --spec-draft-n-max 2..3` + nasze `--spec-draft-vocab` / `--spec-draft-head-type iq4_xs`.
  - Sprawdzić, czy łatka 0032 (requant głowicy do IQ4_XS) działa, gdy głowica jest Q8_0 (Kujira) albo Q6_K (ISTA).
  - VRAM 12 GB: ctx ≤ 32k (Kujira przy 64k spada do 24–29 t/s).
- **#2:** nic w kodzie. Manifest modeli + KLD gate.
- **#3:**
  - Nic w kodzie, za to warstwa produktu: osobny wpis modelu i informacja o licencji.
  - Ewentualnie douczenie głowicy MTP pod Swifta: nasz pipeline z raportu 11, ale pilot PL wyszedł negatywnie, więc niski priorytet.
- **#4:**
  - `ggml-quants.c`: wariant `quantize_row_nvfp4_impl(x, y, k, qw, g)` z prescale 1/g, gdzie g = amax_tensor / (6·448).
  - `llama-quant.cpp`: dla tensorów NVFP4 emitować `<name>.scale` (F32 scalar) jak konwerter. Loader i graf już to obsługują (`build_lora_mm` → `ggml_mul(res, w_s)`).
  - Uwaga z `llama-graph.cpp:1854-1857`: `*_s` koliduje z architekturalnymi skalami i nie działa z LoRA/bias. Trzeba sprawdzić per arch (qwen35: brak biasów w FFN/attn).

### 4.4 Eksperymenty CPU-offline wykonane w ramach raportu ($0)

1. **Entropia skal K-quantów** (`15e-skrypty/scale_entropy.py`, UD-Q4_K_XL, próbka 200k bloków na tensor, 10.68 GB):

   | Typ | Narzut skal (bpw) | Sufit oszczędności (H1) |
   |---|---|---|
   | Q4_K | 0.500 | −2.88% |
   | Q5_K | 0.500 | −2.38% |
   | Q6_K | 0.5625 | −1.33% |
   | IQ4_XS | 0.250 | −1.60% |
   | **razem** | | **−2.19%** (0.234 GB) |

   Skale 6-bitowe mają H0 ≈ 5.1–5.2 bit/skala, czyli są prawie nieściśliwe. `d`/`dmin` f16 mają H ≈ 7–9 bit. **Kill:** nie budujemy kompresji skal K-quantów.
2. **Ściśliwość skal NVFP4 w GGUF** (`nvfp4_scale_entropy_remote.py`, esatapedico VERY-LOW, 128 wierszy × 3 warstwy):
   - duże tensory: H1 1.3–3.6 bit/skala; kod CSF-like 4.01–4.17 bit/skala (wyjątki 0–0.5%), czyli **4.5 → ~4.26 bpw (−5.4%)**;
   - entropia daje sufit ~4.14 bpw (−8%);
   - małe `ssm_beta` [5120×48]: 37% wyjątków (CSF się nie opłaca).
3. **NVFP4 ze skalą globalną i bez** (`nvfp4_global_scale_sim.py`, 512 wierszy prawdziwych BF16 z `Qwen/Qwen3.8-27B`):

   | Tensor | A: ggml (bez skali globalnej) | B: + skala globalna | C: skala float | Q4_0 RTN | % subnormalnych w A |
   |---|---|---|---|---|---|
   | L29 `linear_attn.in_proj_qkv` | 0.0114 | 0.0089 | 0.0087 | 0.0079 | 99.9% |
   | L31 `self_attn.q_proj` | 0.0130 | 0.0089 | 0.0087 | 0.0080 | 99.9% |
   | L30 `mlp.up_proj` | 0.0138 | 0.0090 | 0.0088 | 0.0077 | 100% |
   | L60 `mlp.down_proj` | 0.0131 | 0.0090 | 0.0088 | 0.0075 | 100% |
   | L5 `linear_attn.out_proj` | 0.0116 | 0.0090 | 0.0088 | 0.0076 | 99.9% |

   Wnioski:
   - (a) Brak skali globalnej kosztuje +28…+55% błędu wag.
   - (b) Nawet po naprawie NVFP4 RTN jest o 12–17% gorszy od Q4_0 RTN przy tych samych 4.5 bpw. Jedynym argumentem za NVFP4 zostaje prefill na sm_120.
4. **Weryfikacje bajtowe:**
   - alokacja Swift = ISTA (`diff`);
   - głowica MTP Swift = Qwen (SHA-256 próbek);
   - geometria CSF z nagłówka safetensors.

---

## 5. Projekty eksperymentów

### E1 (główny). Swift-1.5 vs Saluki vs Bonsai vs Q3_K_XL, z bramką KLD

**Hipotezy:**
- H1: na 12 GB plik GSQ/Swift `-mtp` z naszym MTP daje ≥ 1.3× t/s Saluki-plain przy KLD ≤ Saluki.
- H2: Swift skraca liczbę tokenów do odpowiedzi o ≥ 20% na naszym zestawie PL/EN bez spadku pass-rate > 3 pp.
- H3: na 16 GB GSQ-RCO IQ3_S przegrywa z UD/AP-Q3_K_XL w KLD-PL, a wygrywa ≤ 10% w t/s.

**Ramiona:**
- 12 GB (RTX 3060):
  - S0 Saluki (7.90);
  - S1 Saluki-MTP Kujira (8.35);
  - B0 Bonsai Q2_0 repack (nasz fork);
  - B1 Bonsai PTQ1_0 (prism, tylko prędkość);
  - I2 ISTA IQ2_S-mtp (9.61, kontrola Qwen);
  - W2 Swift IQ2_S-mtp (9.61);
  - W1 Swift IQ2_XS-mtp (8.77);
  - W3 Swift IQ3_XXS-mtp (10.44; tylko jeśli przy 16k mieści się ≤ 11.8 GB).
- 16 GB (RTX 5060 Ti):
  - U3 UD-Q3_K_XL (13.15, MTP, obecny default);
  - A3 AP-Q3_K_XL;
  - I4 ISTA IQ3_S-mtp (12.12);
  - W4 Swift IQ3_S-mtp (12.12).

**Jakość (KLD), sprzętowo niezależna.** Szum fork vs upstream to 6·10⁻⁴ ≪ efekty 0.03–0.2, więc całość liczymy na jednej maszynie:
- Referencje: `Qwen3.8-27B-BF16.gguf` (convert z rewizji `1d4bf0f2`, 54.66 GB) i `Swift-1.5-BF16.gguf` (convert z `ukisai/Swift-1.5-Qwen3.8-27b`). Swift dostaje dwa KLD: do własnego BF16 (wierność kwantu) i do Qwen BF16 (jak bardzo to inny model; to nie jest metryka jakości).
- Korpusy, każdy z md5 w raporcie:
  - (1) `wiki.test.raw` (zgodność z ISTA/AP);
  - (2) PL proza: FineWeb-2 `pol_Latn`, seed 0, 800k znaków;
  - (3) PL czat: odpowiedzi BF16 na 6 promptów `spec_sweep` + 30 promptów PL z IFEval-pl/GSM8K-pl, teacher-forced;
  - (4) kod: 14 repo z 2026 (jak wiklif, żeby uniknąć kontaminacji);
  - (5) długi kontekst: 2 chunki × 16384 PL (sprawdzenie problemu „korupcji języka przy 140k” z xenodeve, w skali pośredniej).
- Komenda (jak agentionai, upstream `llama-perplexity`):
  ```
  llama-perplexity -m REF.gguf -f C.txt --kl-divergence-base base-C.bin -c 2048 --chunks 32 -ngl 99 -fa on
  llama-perplexity -m Q.gguf  --kl-divergence --kl-divergence-base base-C.bin -c 2048 --chunks 32 -ngl 99 -fa on
  ```
  Dla (5): `-c 16384 --chunks 2`. Base zajmuje ~0.5 MB na oceniany token, czyli ~16 GB na korpus (2048×32) i 8 GB na (5).
- Metryki: mean KLD, 99% KLD, same-top-p, PPL(Q)/PPL(ref).
  - Podłoga: ten sam plik, fork vs upstream (raport 09: 0.0006).
  - Skala: UD-Q4_K_XL (0.012) i UD-Q3_K_XL (0.034).

**Zadania** (bo Swift to inny model; na kartach docelowych naszym silnikiem):
- 20 promptów PL/EN z automatyczną oceną:
  - 8 matematyka z odpowiedzią liczbową;
  - 6 kod z testami (`merge_intervals`, `lfu_cache`, `tree_codec`…);
  - 6 PL instrukcje z checkerem formatu + LanguageTool-pl (błędy na 1k słów).
- 2 seedy, T=0.6, top-p 0.95, top-k 20, thinking on, limit 8192.
- Mierzymy: pass-rate, tokeny myślenia i odpowiedzi, **time-to-answer = tokeny / t/s**.
- Porównania parami: W* vs I* (ten sam tier, różny model) oraz S1 vs S0 (ten sam model, MTP).

**Prędkość:**
- `spec_sweep` 6 promptów × 3 seedy, ABBA, świeży serwer na rundę.
- plain i MTP (`--spec-draft-n-max 2` i `3`); llama-bench tg128 / pp4096 / tg@d16384.
- VRAM przy 16k i 32k (KV q8_0); ms/krok, tok/krok, akceptacja.

**Bramka (przejście do produktu):**
- 12 GB: KLD-wiki ≤ 0.15 (poziom ISTA IQ2_S [A]), KLD-PL ≤ 1.3 × KLD-wiki, LanguageTool-pl ≤ Saluki, t/s ≥ 1.25 × S0.
- 16 GB: KLD-PL ≤ U3 + 10%, t/s ≥ U3 − 3%.

**Kill criteria:**
- **Swift:** odrzucamy, jeśli redukcja tokenów do odpowiedzi vs I* tego samego tieru < 15%, albo pass-rate spada > 5 pp, albo akceptacja MTP W* < 0.8 × I*. Niezależnie od wyniku decyzja licencyjna jest bramką przed produktem.
- **MTP na 12 GB:** odrzucamy, jeśli S1 < 1.25 × S0 na 3060 (compute-bound IQ zjada zysk weryfikacji).
- **GSQ na 16 GB:** zostajemy przy U3/A3, jeśli KLD-PL(I4) > 1.5 × U3 albo zysk t/s < 8%.
- **AP:** odrzucamy, jeśli KLD-PL(A3) ≥ U3 (zysk vendora nie przenosi się na PL).

**Koszt** (ceny Vast z raportu 09: 3060 $0.12/h, 5060 Ti $0.20/h z dyskiem; A100/H100 `[SZACUNEK]`):

| Wariant | Co | Czas | Koszt |
|---|---|---|---|
| A: chmura | 1× A100 80 GB (lub H100), ~400 GB dysku: 2 convert BF16, 10 base, ~12 kwantów × 5 korpusów | ~3–4 h | **~$3–5** `[SZACUNEK: $0.8–1.3/h]` |
| | 3060: download ~65 GB + prędkość + zadania 12 GB | ~4–5 h | ~$0.6 |
| | 5060 Ti: download ~50 GB + prędkość + zadania 16 GB | ~4 h | ~$0.8–1.0 |
| | **razem A** | | **≈ $5–8** |
| B: $0 KLD | KLD na naszym CPU (16 rdzeni, 62 GB RAM), ref = Q8_0 zamiast BF16 (BF16 54.7 GB nie zmieści się bezpiecznie z OS); APEX: Q6_K vs BF16 0.0021 | ~12–16 h CPU `[SZACUNEK]` | $0 |
| | + 3060 i 5060 Ti jak wyżej | | **≈ $1.5–2** |

Budżet: Vast zostało ≈ $2.23 z $5, RunPod ≈ $3.86 z $6. **Wymaga zgody użytkownika.** Rekomenduję wariant B dla KLD (CPU nie łamie zakazu lokalnego GPU) i wynajem kart tylko na prędkość i zadania.

### E2. Naprawa kwantyzatora NVFP4 ($0, CPU)

- **Hipoteza:** skala globalna per tensor + emitowanie `.scale` obniży KLD NVFP4 GGUF o ≥ 25% vs obecny `llama-quantize NVFP4` (lub PR #25153).
- **Prototyp:** łatka w `ggml-quants.c` + `llama-quant.cpp` (jak w §4.3). Test na Qwen3.5-0.8B i LFM2.5-1.2B na CPU: `llama-quantize --tensor-type '.*=nvfp4'`, potem `llama-perplexity --kl-divergence` vs BF16, wiki 20×512.
- **Pomiar:** KLD, same-top-p, % subnormalnych skal (skrypt z §4.4). Bitowo: dla tensorów skonwertowanych z ModelOpt wynik ma być identyczny (ścieżka konwersji bez zmian).
- **Kill:** poprawa KLD < 15%, albo #25153 bez skali globalnej daje to samo.
- **Następny krok:** PR upstream (uzupełnienie #25153). Dopiero potem test prefill na 5060 Ti (pp +65% przy KLD ≤ UD-Q3_K_XL?), ~$0.4.

### E3. Akceptacja MTP na Swifcie (w ramach E1, $0 dodatkowo)

- **Hipoteza:** głowica Qwena na trunku Swifta ma akceptację ≥ 10% niższą niż na ISTA tego samego tieru.
- **Pomiar:** `spec_sweep` z `--spec-draft-n-max 3`; akceptacja i tok/krok W2 vs I2.
- **Kill:** różnica < 5%, wtedy nic nie robimy. Jeśli > 10%: kandydat do self-distill głowicy (raport 10 E1), z zastrzeżeniem negatywnego pilota PL.

### E4 (zamknięty offline). Kompresja skal K-quantów

- Sufit zmierzony (−2.19%) jest poniżej progu sensowności (≥ 5% na nowy typ ggml). Zamknięte bez kosztów.

---

## 6. Dowody zewnętrzne: co potwierdza, co obala, czego brak

- **Niezależne KLD na tym samym protokole:**
  - agentionai AP-GGUF: komendy, rewizja BF16 i build są jawne; held-out niejawny. Autor jest konkurentem, ale mierzy też wbrew sobie: na wiki UD-IQ3_S wygrywa z AP-IQ3_S.
  - wiklif KTopt (ctx 4096, kod/proza, z CI na zadaniach).
  - tooltd BuffedMod (ISTA IQ3_S: 0.0555).
  - Wszystkie zgodnie pokazują, że **GSQ-RCO nie dominuje KLD przy ≥ 3 bpw**.
- **Niezależny test end-to-end:** xenodeve (`docs/results/20-gsq-time-quality-2026-09-20.md`), 9 przebiegów, ~140k kontekstu: EXL3 6/6, GSQ IQ3_S-MTP 5/6, NVFP4 3/6. Korupcja tajskiego w GSQ i NVFP4. Mała próba, inny język, ale to jedyny test głębokiego kontekstu, a ISTA/Swift mierzą tylko ctx 512.
- **Swift:**
  - Analiza osoby trzeciej (yamadori `docs/research/SWIFT-1.5.md`) potwierdza identyczność alokacji i niespójność 9.18× vs 1.95×.
  - Strata wspiera Swifta od v0.1.1 (`6801c77f`), więc jest adopcja, ale bez pomiaru jakości.
  - **Brak** niezależnej ewaluacji zadaniowej kwantów GSQ Swifta i pomiaru akceptacji MTP.
- **Saluki:** graft MTP Kujiry (3080: ×1.61) to jedyny zewnętrzny pomiar prędkości. **Brak** KLD.
- **Leaderboardy:** llm-bench.io (`qwen3-8-27b-gsq-rco`, 10 przebiegów, LLM-judge, sprzęt AMD/Apple). Nie ma 3060 ani 5060 Ti, a dane są słabe (różne kwanty i konteksty).
- **Upstream:**
  - PR #25153 (NVFP4 imatrix search) otwarty;
  - #22897 (skala globalna) zamknięty jako duplikat;
  - #19726 (IQK) odrzucony;
  - `qwen4exp` zmergowany, CSF nie.
- **Co by rozstrzygnęło:**
  - KLD Saluki i Bonsai [A]-protokołem (my w E1);
  - akceptacja MTP Swifta (E3);
  - pomiar ISTA MTP z ujawnionym GPU;
  - task-eval Swift GSQ IQ2/IQ3 z ≥ 3 seedami;
  - merge #25153 + skali globalnej.

---

## 7. Źródła

**Swift / UkisAI:**
- https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF (sha `d74895bbe5db…`, 2026-09-24): `README.md`, `RECIPE.txt`, `SHA256SUMS`, `NOTICE`, `LICENSE`, `evaluation/heldout-kld.tsv`, `evaluation/report.json`, `evaluation/data-screening.json`, `release-manifest.json`, `tensor-allocation/*.rco-allocation.txt`.
- https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27b (`README.md`, `config.json`, `model.safetensors.index.json`; MTP: `mtp.*` w safetensors).
- https://huggingface.co/ukisai/Swift-1.5-Qwen3.8-27B-GGUF; https://huggingface.co/ukisai/Swift-Bonsai-2-GGUF.

**ISTA-DASLab:**
- https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF (`README.md`, `assets/plots/Qwen3.8-27B-mtp_speculative_decoding.png`, `tensor-allocation/`).
- GSQ: https://arxiv.org/abs/2604.18556 (Tab. 2 speedup, §4 single-run); https://github.com/IST-DASLab/GSQ (README; gałąź `gsvq-iquant-qwen3-sweep-results`, `docs/gsvq_iquants.md`, commity `7235dadb4f`, `4acc593182`, `c93f2e81a1`).
- RCO: https://arxiv.org/abs/2605.00649; https://github.com/IST-DASLab/RCO `src/search/quant.py` (retrakcja, `round_with_budget_dp` :362).

**Saluki:**
- https://huggingface.co/ConwayResearch/Underdog-Saluki-27B-1.0 (karta = lokalna kopia `~/qwen-opt/cloud/runs/3060/pre/saluki-README.md`; nagłówek `saluki-head.txt`).
- https://huggingface.co/Kujira/Underdog-Saluki-27B-1.0-MTP-GGUF.

**Bonsai:** `~/qwen-opt/cloud/runs/3060/pre/bonsai-README.md`; whitepaper https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-27b-whitepaper.pdf.

**NVIDIA / CSF:**
- https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local (`README.md`, `config.json` `weight_scale_encoding: "csf"`, `tensors/model-00001-of-00021.safetensors` nagłówek).
- Obraz: https://pbs.twimg.com/media/HUsk6ZeW8AAhz7a (zrzut karty: „NVFP4 scale factors … new lossless compression format … use one of the containers”).
- https://huggingface.co/local-inference-lab/Qwen3.8-Flash-Next-NVFP4-MXFP8-CSF-QAD (`README.md`: kodek, 73 728 macierzy, weryfikacja SHA-256).
- https://github.com/flashinfer-ai/flashinfer/blob/main/flashinfer/experimental/b12x/_lib/quant/nvfp4_csf.py (commit `fc8fdc17f7`, 2026-10-06).
- Licencja Qwen Community 1.0: https://huggingface.co/Qwen/Qwen3.8-Flash-Next/blob/main/LICENSE (§1 100M MAU / $20M, §2 MaaS / AI Work Assistant).

**llama.cpp** (lokalnie `~/llama-master` @ `f61994f58`):
- `ggml/src/ggml-quants.c:384-417, 589-612, 2309-2313`;
- `ggml/src/ggml-impl.h:512-565`;
- `ggml/src/ggml-common.h:222-226, 327-368, 454-460`;
- `src/llama-graph.cpp:1595-1601, 1854-1875`;
- `tools/perplexity/perplexity.cpp:1732-1738`;
- commity `609290be6` (#28636), `e9f824d8c` (#24364), `5eae9cb1d` (#19769), `c061df198` (qwen4exp MTP).
- PR: https://github.com/ggml-org/llama.cpp/pull/25153, /pull/22897, /pull/26556, /pull/19726.

**NVFP4 GGUF (pomiar):** https://huggingface.co/esatapedico/Qwen3.8-27B-NVFP4-MTP-GGUF (`Qwen3.8-27B-NVFP4-MTP-VERY-LOW.gguf`, README §konwersja).

**Unsloth:** https://huggingface.co/unsloth/Qwen3.8-27B-GGUF (rozmiary, nagłówki UD-Q3_K_XL / IQ3_XXS / IQ2_XXS / IQ2_S); https://unsloth.ai/docs/basics/dynamic-3.0-ggufs.

**Niezależne KLD i testy:**
- https://huggingface.co/agentionai/Qwen3.8-27B-AP-GGUF;
- https://huggingface.co/wiklif/Qwen3.8-27B-KTopt-GGUF;
- https://huggingface.co/tooltd/Qwen3.8-27B-GSQ-RCO-BuffedMod-GGUF;
- https://huggingface.co/mudler/Qwen3.8-27B-APEX-GGUF;
- https://github.com/xenodeve/Qwen-3.8-27B-Tuning/blob/main/docs/results/20-gsq-time-quality-2026-09-20.md (i `19-gsq-screen-…`);
- https://github.com/thejustinwalsh/yamadori/blob/main/docs/research/SWIFT-1.5.md;
- https://llm-bench.io/models/qwen3-8-27b-gsq-rco.

**ik_llama / EXL3** (z podagenta, nie weryfikowane przeze mnie ponad to, co cytuję):
- https://github.com/ikawrakow/ik_llama.cpp (HEAD `8d21687c`, `examples/quantize/quantize.cpp:56-99`);
- https://github.com/lrozewicz/kt-llama-cpp (`6f526e454`);
- https://github.com/turboderp-org/exllamav3 (v1.6.2 `4c842731`);
- https://huggingface.co/ubergarm/Qwen3.8-27B-GGUF.

**Nasze:**
- `~/KERNEL/product/research/09-chmura-3060.md:21-62, 109-127, 161-191`;
- `09-chmura-5060ti.md:63-85, 148, 170-188, 258-290`;
- `10-post-training.md:327-347`;
- `~/KERNEL/qwen-opt/research/strata/timeline.md:43,55`.

**Skrypty tego raportu:** `~/KERNEL/product/research/15e-skrypty/` (`ggufhead.py`, `scale_entropy.py`, `nvfp4_scale_entropy_remote.py`, `nvfp4_global_scale_sim.py`).

---

## Do bazy wiedzy

| Folder | Tytuł (plik) | Streszczenie 1 linią | Kluczowe liczby (źródło) |
|---|---|---|---|
| research | `raport-15e-kwantyzacja-nowa` (nowa) | Nowe formaty niskobitowe dla 27B na 12–16 GB: GSQ-RCO tylko „SOTA” w wąskiej klasie, Swift to fine-tune z niedouczoną głowicą MTP, CSF/QAD poza naszymi kartami, a największy zysk to MTP na 2-bitowych plikach. | ranking §4.2; E1 $5–8 lub $1.5–2 + CPU (ten raport §5) |
| modele | `swift-1-5` (nowa) | UkisAI Swift 1.5: RL/OPD fine-tune Qwen3.8-27B na krótsze myślenie; kwanty GSQ-RCO z alokacją ISTA 1:1; licencja < $1M. | −41.9% śr. / −58.5% mediana tokenów GPQA-D, +0.31 pp (karta BF16); KLD vs własny BF16 0.190 / 0.135 / 0.098 / 0.051 przy 8.42 / 9.26 / 10.09 / 11.77 GB (`heldout-kld.tsv`, `RECIPE.txt`); głowica MTP = Qwen (SHA-256 próbek, ten raport §2.3) |
| modele | `saluki` (aktualizacja) | Dodać: nagłówek = potok ISTA (`quantized_by ISTA DASLab`), ~2.35 bpw; istnieje graft MTP Kujira. | 3080 12 GB: 41.2 → 66.2 t/s z MTP, 8.35 GB, VRAM 11.5 GB, ctx ≤ 32k (karta Kujira) |
| modele | `kwanty-gguf` (aktualizacja) | Dodać tabelę niezależnych KLD [A] oraz to, że protokoły KLD są nieporównywalne. | UD-Q3_K_XL 0.0337, UD-IQ3_S 0.0470, GSQ IQ3_S 0.0665, AP-Q3_K_XL held-out 0.0339 vs 0.0421 (agentionai, 60×2048) |
| ludzie-firmy | `ista-daslab` (aktualizacja) | Dodać: refinement IQ nieopublikowany; publiczny GSVQ pogarszał KL; RCO = softmax po typach + rzut na budżet + DP; KLD przy 3.5 bpw gorszy niż UD. | GSVQ: MSE −2.6%, KL +1.9…+4.2% (`docs/gsvq_iquants.md`); ISTA IQ3_S KLD 0.0519 @512 vs 0.0665 @2048 |
| ludzie-firmy | `ukisai` (nowa) | Autor Swift 1.0/1.5 (fine-tune na krótsze myślenie), Swift Open License v1.0 z progiem US$1M przychodu. | 23 modele na koncie (yamadori); licencja §5 (LICENSE) |
| nvidia | `nvfp4` (aktualizacja) | Dodać: kwantyzator ggml NVFP4 nie ma skali globalnej ani imatrix, więc skale wpadają w subnormalne UE4M3; CSF; QAD Flash-Next; 96 GiB. | 99.8–100% subnormalnych, 6–14 wartości (esatapedico VERY-LOW); sim rel-MSE 0.0114–0.0138 → 0.0089–0.0090 (§4.4); CSF 53–55% skal (nagłówek NVIDIA shard 1) |
| eksperymenty | `2026-10-16-kompresja-skal-offline` (nowa) | Bezstratna kompresja skal: K-quanty ≤ 2.19% (kill), NVFP4 −5.4% (CSF) / −8% (entropia). | `15e-skrypty/scale_entropy.py` na UD-Q4_K_XL; `nvfp4_scale_entropy_remote.py` |
| eksperymenty | `2026-10-16-nvfp4-skala-globalna-sim` (nowa) | CPU-sim NVFP4 na prawdziwych wagach Qwen3.8-27B: skala globalna −22…−35% błędu; NVFP4 nadal 12–17% gorszy od Q4_0 RTN. | §4.4 tabela 3 |
| repo | `ik-llama-cpp` (aktualizacja; status → aktualne) | Stan 2026-10-16: HEAD `8d21687c`, typy KT (bpw), backendy, odrzucony port IQK #19726, KTopt KLD. | IQ2_KT 2.125 / IQ3_KT 3.125 / IQ4_KT 4.0 bpw; KTopt 10.31 GB KLD 0.043/0.066 (wiklif) |
| repo | `exllamav3` (nowa) | QTIP-pochodny EXL3 z ROCm in-tree od 2026-10, ma Qwen3.8-27B; w teście xenodeve najlepszy end-to-end przy 140k. | v1.6.2 `4c842731`; 6/6 vs GSQ 5/6 vs NVFP4 3/6 (xenodeve) |
| lekcje | `lekcja-kld-protokoly` (nowa) | KLD z różnych ctx/referencji/korpusów różni się o 30%+ i nie wolno go mieszać; Swift mierzy do własnego BF16. | ISTA IQ3_S 0.0519 (ctx 512) vs 0.0665 (ctx 2048); Swift vs ISTA różne referencje (`report.json` „reference”) |
| decyzje | (propozycja, do decyzji użytkownika) `swift-licencja` | Czy dopuszczamy w produkcie modele z licencją z progiem przychodu (Swift OL < $1M)? | LICENSE §5, §12 |
