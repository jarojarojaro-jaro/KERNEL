# 21e: KV cache między modelami (NVIDIA, arXiv 2608.03893): weryfikacja i co z tego mamy

Data: 2026-10-19. Analiza tylko na CPU (`nice -n 19`, 4 wątki, bez ładowania całych modeli; GPU nietknięte).
Źródło: Heo i in., „Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse”, https://arxiv.org/abs/2608.03893 (v1, 2026-08-04). Czytałem pełny TeX z https://arxiv.org/src/2608.03893 (rozpakowany w `/tmp/kvx`; ścieżki `sections/…`, `appendix/…` poniżej odnoszą się do niego).
Nasze skrypty i wyniki: `~/KERNEL/product/research/21e-skrypty/` (`ls.py`, `diff.py`, `abl.py`, `abl_sampled.py`, `abl_pl.py`, `*_diff.txt`, `*_abl*.txt`, `r_qwen.npy`, `r_lfm.npy`).

## TL;DR

1. **Paper jest uczciwie opisany, ale główna obietnica („mały → duży podnosi jakość”) nie wynika z jego własnych danych.** Brakuje bazy „zostań przy modelu źródłowym”. Policzyłem ją z ich tabeli: średnia z 5 benchmarków dla celu z przeniesionym KV jest **niższa od samego modelu źródłowego** we wszystkich 4 udanych parach (Qwen3 14B→32B 76.07 vs 14B 76.50; 8B→32B 67.59 vs 72.76; Llama 8B→70B 54.57 vs 63.71; Ministral 3B→8B 53.72 vs 65.64). Na GSM8K, jedynym zadaniu z generowaniem, transfer przegrywa ze źródłem w każdej parze (`appendix/F_extended_results.tex:23-40`).
2. **Liczby z abstraktu się zgadzają, ale są wąskie.**
   - „73–98% na 4/6 parach” to retencja względem celu, nieznormalizowana do poziomu losowego. Po normalizacji (floor-normalized): 63–96%. GSM8K: 18–96%.
   - „2.7–25×” zmierzono na 8×H100, bf16, eager, wejścia syntetyczne. Nie wliczono prefillu źródła, przesłania zmapowanego KV ani wczytania mappera (4–12 GB).
   - Ograniczenia „ta sama rodzina” i „tylko dense full-attention” są prawdziwe. Do tego dochodzi trzecie: wszystkie pary mają ten sam `n_kv` i `d_h` („matched-KV”).
3. **Wprost do nas nie pasuje.** Oba nasze modele to hybrydy (Qwen: 48 GDN + 16 attention; LFM: 30 shortconv + 10 attention). Nie mamy par „z jednej rodziny” przełączanych na jednym GPU. LFM ↔ Qwen to dwie różne rodziny z różnymi tokenizerami (128 000 vs 248 320 tokenów), więc ta metoda tu nie działa.
4. **Ciekawe okazało się pytanie o Main ↔ Uncensored.** Rozłożyłem różnice wag na CPU:
   - **Qwen3.8-27B-Uncensored (OrcaRouter) = Qwen3.8-27B z jedną, globalną, rank-1 ortogonalizacją kierunku r** we wszystkich „pisarzach” (writers) strumienia rezydualnego: `token_embd`, `attn_output`, `ssm_out`, `ffn_down`, także w bloku MTP. Skala s = 0.994–1.000 na 21 zbadanych tensorach z warstw 0–64. Czytający (`attn_q/k/v`, `attn_qkv`, `ffn_up/gate`, `ssm_alpha/beta`) różnią się wyłącznie szumem kwantyzacji. Wszystkie tensory F32 (normy, `ssm_a`, `ssm_conv1d`, `ssm_dt`) oraz `output.weight` są **bajtowo identyczne**.
   - **LFM2.5-Uncensored (AtomicChat) = LFM2.5 z rank-1 edycją `W ← (I − 1.75·r_l r_lᵀ)·W`, z osobnym kierunkiem w każdej warstwie 14–39.** Warstwy 0–13 i embedding nie są ruszone (s ≈ 0.000). Zgadza się to co do liczby z metadanymi GGUF `atomic.abliterate.layers=14-39`, `scale=1.75`.
   - To nie jest fine-tune, tylko analityczna edycja wag. KV transfer Main → Uncensored nie potrzebuje więc mappera: **near-identity jest naturalnym przypadkiem**, a istniejący `--slot-save-path` w llama.cpp przyjmuje plik stanu z drugiego modelu (sprawdza tylko kształty i typy).
5. **Większy wniosek produktowy: Uncensored nie musi być osobnym modelem.** Tę samą edycję można zrobić w locie: `y ← y − s·r(rᵀy)` na wyjściu każdego writera. Dla Qwena przy s = 1 wystarczy rzutować strumień rezydualny po każdym dodaniu. Matematycznie to dokładnie ten sam model co ortogonalizacja wag. Efekt:
   - przełączenie Main ↔ Uncensored trwa ~0 s zamiast przeładowania modelu i ~61.5 s prefillu przy 53k;
   - znika plik 15.66 GiB (Qwen) i 16.10 GiB (LFM);
   - Uncensored dostaje lepszy kwant Maina (UD z imatrix zamiast Q4_K_M bez imatrix).
   - Do zrobienia: E2 (KLD i „wyciek odmowy” przy identity transfer) oraz E3 (tryb w locie w forku).
6. **Hybrydy w ogólnym przypadku** (inny rozmiar, inny model):
   - LFM jest łatwy. Stan shortconv jest lokalny (kernel 3, 30 warstw, więc pole recepcyjne ≤ 60 tokenów), wystarczy dopisać „re-prefill ogona ≥ 61 tokenów”.
   - Qwen GDN jest trudny. Stan ma pamięć wykładniczą: połówkowy czas zaniku przy zerowym wejściu ma medianę 25 tokenów, ale 10% głowic przekracza 1 010 tokenów, a maksimum to 18 132. Trzeba by mapować sam stan albo przeliczać okno „gojące”.
   - Dla produktu dziś nieopłacalne.

## 1. Co dokładnie zmierzono w paperze

| element | wartość | źródło |
|---|---|---|
| pary | Qwen3 8B/14B→32B, Llama 3.1 8B→70B, Ministral 3 3B/8B→8B/14B; wszystkie 8 KV heads × 128 | `appendix/D_setup.tex` (tab. families) |
| architektura | dense full-attention; hybrydy wprost poza zakresem | `sections/04_experiments.tex` (Setup), `sections/05_discussion.tex:54-56` |
| mapper | per (warstwa celu, KV head) ridge λ = 0.01 na konkatenacji K (bez RoPE) lub V z top-k warstw źródła, potem ponowne RoPE celu | `sections/03_mapper_design.tex` |
| kalibracja | 500 × 1024 tokenów FineWeb-Edu, stride 4, ~128k obserwacji na głowicę | `appendix/E_run_info.tex:14` |
| koszt dopasowania | 47–87 min na parę, 8×H100 | `sections/03_mapper_design.tex:63`, `appendix/E_run_info.tex` |
| rozmiar mappera | 1.01–3.36 B parametrów, 4–12 GB | `appendix/D_setup.tex:93-100` |
| jakość | 5 benchmarków log-likelihood/8-shot (ARC-C, HellaSwag, WinoGrande, MMLU, GSM8K), PPL WikiText, CoQA multi-turn | `sections/04_experiments.tex:61-95` |
| kierunek L→S | tylko HellaSwag; Llama 70B→8B 37% retencji | `sections/04_experiments.tex` (§ What determines) |
| latencja | 8×H100 NVLink, bf16, eager, 50 rozgrzewek + 30 pomiarów, wejścia syntetyczne | `appendix/G_latency.tex` |

## 2. Weryfikacja twierdzeń

### 2.1 Arytmetyka zgadza się

- **Rozmiar mappera.** Wzór 2·L_t·n_kv·(k·n_kv·d_h)·d_h:
  - Qwen3 14B→32B, k = 8: 2·64·8·(8·8·128)·128 = 1.074 B (paper: 1.07 B);
  - Llama 8B→70B, k = 20: 2·80·8·(20·8·128)·128 = 3.355 B (paper: 3.36 B).
  - Storage „4 GB” dla 1.07 B daje 4 B/parametr, czyli wagi są **trzymane w fp32**. W bf16 byłoby o połowę mniej.
- **Koszt mappera vs prefill.** Mapper to ~2.15 GFLOP/token wobec ~64 GFLOP/token samego GEMM 32B, czyli ~30× mniej FLOP. Przy 32k dochodzi jeszcze atencja prefillu, więc 25× jest spójne z ich tabelą (278 vs 6 975 ms, `appendix/G_latency.tex:31`).
- **Prefill 32B przy 32k = 6 975 ms.** To ~3.2 PFLOP (GEMM + causal attention), czyli ~460 TFLOP/s na H100 bf16. Wiarygodne.

### 2.2 Co jest naciągane albo czego brakuje

1. **Brak bazy „zostań na źródle”.** To najważniejszy zarzut. Paper sprzedaje S→L jako „upgrade quality”, ale z ich tabeli per-family (`appendix/F_extended_results.tex:23-40`) wynika:

   | para | transfer, śr. 5 | źródło samo, śr. 5 | cel sam, śr. 5 | transfer, śr. 4 LL | źródło, śr. 4 LL |
   |---|---|---|---|---|---|
   | Qwen3 14B→32B | 76.07 | **76.50** | 78.20 | 72.34 | 71.88 |
   | Qwen3 8B→32B | 67.59 | **72.76** | 78.20 | 68.11 | 68.03 |
   | Llama 8B→70B | 54.57 | **63.71** | 76.00 | 64.52 | 65.61 |
   | Ministral 3B→8B | 53.72 | **65.64** | 72.22 | 59.44 | 61.77 |

   - Na benchmarkach log-likelihood najlepsza para zyskuje +0.46 pp względem źródła, czyli 22% luki do celu. 8B→32B zyskuje +0.08 pp, a Llama i Ministral tracą.
   - Na GSM8K (generowanie, najbliższe naszemu użyciu) transfer jest zawsze gorszy od źródła: 90.98 < 95.00, 65.50 < 91.66, 14.78 < 56.10, 30.86 < 81.12.
   - Wniosek: zmapowany KV daje model co najwyżej tak dobry jak źródło, a za to płaci się decodingiem większego modelu. „Upgrade” nie jest wykazany. Uzasadniony sens ma tylko L→S (obniżka kosztu), a to zmierzono wyłącznie na HellaSwag. Llama 70B→8B miała tam 37%.
2. **Retencja jest liczona bez podłogi losowej.** WinoGrande ma podłogę 50%, więc wynik 48.5 (gorszy niż losowy) liczy się jako 69.2% retencji (`appendix/F_extended_results.tex`, tab. metric_anchors). Autorzy sami podają wersję znormalizowaną: Avg_fn 96.3 / 80.7 / 62.9 / 65.9 (`:88-91`). Uczciwie, ale do abstraktu trafiła ładniejsza liczba.
3. **Wybór k na tych samych benchmarkach**, które potem raportują. Według nich zmienia to wynik o ≤ 2.49 pp (`appendix/H_k_selection.tex`). Akceptowalne, choć nie jest to wybór out-of-sample.
4. **Domena kalibracji ma znaczenie dla nas.** Kalibracja na CodeAlpaca zamiast FineWeb-Edu kosztuje −5.24 pp na HellaSwag (`appendix/C_ablation.tex:111`). Nasza praca to agentowy kod i polski, a tej kombinacji nikt nie mierzył.
5. **Latencja to pomiar bez narzutów.**
   - Nie wliczono przesłania zmapowanego cache do procesu celu (`appendix/G_latency.tex:58-59`).
   - Nie wliczono wczytania mappera. „80–480 ms” jest „computed, not measured” (`appendix/D_setup.tex:112-115`).
   - Nie wliczono kosztu prefillu źródła, który trzeba już mieć.
   - Dolne 2.7× pochodzi z Ministral 3B→8B (`appendix/G_latency.tex:35`), górne 25× z jednej pary przy 32k.
6. **Multi-turn** sprawdzono na jednej parze (Qwen3 14B↔32B), 100 rozmów CoQA, 10 tur. Dryf L→S rośnie liniowo o 0.33 pp/turę (`sections/04_experiments.tex:316`). W sesjach agentowych z setkami tur to się kumuluje.
7. **Flota mapperów rośnie kwadratowo:** P(P−1) kierunków po ~6.5 GB, czyli 39 / 79 / 131 GB dla 3 / 4 / 5 modeli (`appendix/D_setup.tex`, Serving cost).

**Werdykt:**
- „Liniowa struktura KV w rodzinie”: **wiarygodne** (R² i ablacje spójne).
- „2.7–25× szybciej niż re-prefill”: **wiarygodne jako czysty compute**, end-to-end **niezmierzone**.
- „73–98% retencji”: **prawdziwe, ale mylące** bez bazy źródła.
- „Podnosi jakość (S→L)”: **nie wykazane, wręcz zaprzeczone** przez ich tabelę.
- Metoda jest **stratna**, nie bit-exact.

## 3. Nasza analiza: czym naprawdę są modele Uncensored (CPU, bez GPU)

Metoda (`21e-skrypty/diff.py`, `abl.py`, `abl_pl.py`):
- dekwantyzacja par tensorów z obu GGUF (gguf-py), D = W_unc − W_main;
- energia top singular values D;
- cosinus wektorów singularnych między tensorami;
- skala s z modelu `W_unc = (I − s·r rᵀ)·W_main`.

Uwaga: oba pliki to różne kwanty (UD-Q4_K_XL z imatrix vs Q4_K_M bez imatrix; LFM Q5_K_M vs mieszanka Q8_0/Q5_K z imatrix), więc tło stanowi szum kwantyzacji rzędu 2–11% normy.

### 3.1 Qwen3.8-27B vs Uncensored (OrcaRouter)

- **Metadane** (`ls.py`): te same hparams `qwen35` (65 bloków, 4 KV heads × 256, GDN 16/48 heads, state 128) i ten sam tokenizer (248 320 tokenów, merges identyczne). **Szablon czatu jest inny**: Orca ma starszy, bez łączenia wielu wiadomości system/developer i inaczej renderuje `tool_call.arguments`.
- **Bajtowo identyczne** są wszystkie tensory F32 (normy, `ssm_a`, `ssm_conv1d`, `ssm_dt.bias`, `ssm_norm`, normy nextn) oraz `output.weight` Q6_K (`21e-skrypty`, wynik `ls.py`).
- **Czytający różnią się tylko szumem.** Top-1 energia D ≤ 0.6%, s1/s2 ≈ 1.0–1.7. Dotyczy to `attn_k` (e1 0.0038 / 0.0029), `attn_v` 0.0062, `attn_q` 0.0007, `attn_qkv` 0.0008, `ffn_up` 0.0007 i `ffn_gate` 0.0009 (`qwen_diff.txt`).
- **Pisarze mają wyraźny składnik rank-1 (s1/s2 do 20.7) w jednym, wspólnym kierunku:** |cos| = 0.99–1.00 między `token_embd` a `attn_output` / `ffn_down` / `ssm_out` warstw 3–64 (`qwen_diff.txt`, macierz cos).
- **Skala** (`qwen_abl.txt`, `qwen_abl_s.txt`): s = 0.994–1.000 dla `token_embd` oraz writerów warstw 0, 1, 3, 7, 15, 31, 47, 62, 63, 64. `keep` = 0.05–0.09 to podłoga szumu. Wynik: **pełna ortogonalizacja (s = 1), jeden globalny kierunek, warstwy 0–64 łącznie z MTP.** `nextn.eh_proj` nie ruszony.
- **Wielkość edycji:** część rank-1 to ‖r rᵀW‖/‖W‖ ≈ 1.3–1.6% normy writera, np. `blk.63.ffn_down`: 0.0295·√0.2023 = 1.33%; `token_embd`: 0.0622·√0.0489 = 1.38%. Dla losowego kierunku w 5120 wymiarach oczekiwane jest 1/√5120 = 1.40%. Kierunek odmowy nie jest więc wyjątkowo energetyczny w wagach. Edycja jest **mniejsza niż różnica kwantów** między obydwoma plikami (rel 3–11%).

### 3.2 LFM2.5-24B-A2B vs Uncensored-AD (AtomicChat)

- Metadane: `atomic.abliterate.layers=14-39`, `scale=1.75`, `per_layer=true`, `writers=all`. Ten sam tokenizer i szablon (md5 identyczne). Router `ffn_gate_inp` (F32), `exp_probs_b`, `shortconv.conv` i wszystkie normy są bajtowo identyczne, więc to ten sam checkpoint bazowy mimo nazwy „Preview”.
- **Wynik `abl_pl.py`:**
  - warstwy 0–13: s = −0.002…0.003 (nieruszone);
  - warstwy 14–39: s = 1.745–1.760 jednocześnie dla `attn_output`/`shortconv.out_proj` i `ffn_down_exps`; `keep` = 0.746–0.761 = |1 − 1.75|.
  - Kierunki r_l różnią się między warstwami (sąsiednie |cos| 0.73–0.93). Wspólne r dla wszystkich 64 ekspertów warstwy: e1 konkatenacji 0.44–0.48.
  - `token_embd` nieruszony.
- Formalnie: W' = (I − 1.75·r_l r_lᵀ)·W, czyli składowa r_l w zapisie do strumienia jest **odwracana i skalowana do −0.75**. To odbicie z nadmiarem, nie zwykła projekcja.

### 3.3 Co z tego wynika dla KV

- **Qwen.** Wagi czytające są takie same. Różnica KV między Main a Uncensored bierze się tylko z tego, że strumień rezydualny Uncensored nie ma składowej r, a Main ma. Wszystkie dalsze efekty (normy, GDN, atencja) płyną z tej jednej składowej. Główny kandydat na „near-identity” jest prawdziwy, ale wielkość błędu i zachowanie na promptach odmownych trzeba **zmierzyć** (E2). `[INFERENCE: wielkość składowej r w aktywacjach nieznana bez uruchomienia modelu]`
- **LFM.** Strumień w warstwach 0–13 jest identyczny. Przy tych samych wagach (tryb w locie z §5) **KV warstw atencji 2, 6, 10 i stan shortconv warstw 0–13 są bit-identyczne** z tym, co policzyłby Uncensored. Przybliżone są tylko warstwy 14–39.

## 4. Mapowanie na nasze przypadki

### 4.1 Main ↔ Uncensored (Qwen i LFM): tani przypadek, ale nie przez paper

**Mechanika istnieje dziś.** `llama_state_seq_load_file` sprawdza tylko magic i wersję (`~/llama.cpp/src/llama-context.cpp:3204`). Odczyt KV sprawdza liczbę warstw, typy i rozmiary wierszy (`src/llama-kv-cache.cpp:2528-2640`), a odczyt stanu rekurencyjnego liczbę warstw, typy r/s i rozmiary (`src/llama-memory-recurrent.cpp:1095-1209`). **Nikt nie sprawdza tożsamości modelu.** Plik slotu Maina wczyta się więc do Uncensored, bo kształty są identyczne (§3.1). Dotyczy to też KV głowicy MTP i checkpointów GDN.

**Zysk (XTX, sesja 53k):**
- Dziś przełączenie to przeładowanie modelu `[niezmierzone w tym raporcie]` plus pełny prefill **~61.5 s** (`16f-xtx-szybkie.md:199`).
- **Wariant A (identity przez plik slotu):** restore **2.51 s** (tamże). Oszczędność ~59 s na przełączenie (×24.5 na samym stanie). Zapis pliku po stronie Maina to 1.99 s, wykonywany i tak przez wrapper z 16f E5.
- **Wariant B (tryb Uncensored w locie, §5):** zero przeładowania i zero prefillu (KV Maina używany wprost). Oszczędność ~61.5 s + przeładowanie.

**Zastrzeżenia:**
- To **nie jest bit-exact**. Uncensored z KV Maina ≠ Uncensored z własnym prefillem. W UI musi być „szybkie przełączenie (przybliżone)” obok „dokładne (przelicz kontekst)”.
- **Wyciek odmowy.** Najczęstszy realny scenariusz to „Main odmówił, przełącz na Uncensored”. Jeśli odpowiedź z odmową jest już w kontekście, przeważy treść, nie KV. Wrapper musi więc obciąć KV do początku tury asystenta. Robi to dopasowanie prefiksu w llama-server: inny prompt oznacza rollback do najbliższego checkpointu i re-prefill reszty. Czy klucze i wartości Maina (zawierające W_k·r(r·h)) przenoszą „flagę odmowy” do Uncensored, trzeba zmierzyć (E2, metryka refusal rate).
- **Różny szablon czatu Orca.** Przy wariancie A oba serwery muszą renderować tym samym szablonem, np. `--chat-template-file` z szablonem Maina. Inaczej wspólny prefiks tokenów się skończy i nastąpi częściowy re-prefill, co jest bezpieczne, ale wolne. W wariancie B problem znika.
- **Bezpieczeństwo poprawności.** Skoro llama.cpp nie sprawdza modelu, restore pliku z innego modelu o tych samych kształtach (np. innego fine-tune 27B) „zadziała” i da śmieci. Hash z projektu E5 (ścieżka + rozmiar + mtime modelu, `16f:203`) jest właściwą blokadą. Dla par Main ↔ Uncensored potrzebna jest jawna allowlista, a nie zdjęcie blokady.

### 4.2 LFM ↔ Qwen

Nie stosuje się:
- inne rodziny, inne tokenizery (128 000 vs 248 320), więc inna liczba tokenów i nawet T się nie zgadza;
- inne KV (LFM 8 × 64, 10 warstw; Qwen 4 × 256, 16 warstw);
- przestrzeń cross-family to otwarte pytanie także w paperze (`sections/05_discussion.tex`, future work 3).

Przełączenie Qwen → LFM → Qwen rozwiązuje bezstratnie dyskowy cache sesji (16f E5). Problemem jest tylko pierwsze wejście drugiego modelu do rozmowy, a tu jedyną opcją pozostaje prefill. LFM robi go szybko: ~12.2 s przy 53k.

### 4.3 KV draftera

- Tu stratny transfer byłby **bezstratny dla wyjścia**, bo weryfikacja poprawia błędy, a cierpi tylko akceptacja. To jedyne miejsce, gdzie „73–98% retencji” jest akceptowalne bez zmiany polityki bit-exact.
- U nas nie ma jednak bólu do leczenia:
  - KV głowicy MTP to jedna warstwa liczona w prefillu Maina;
  - DFlash2 i tak warunkuje się na hidden states celu (to w praktyce wytrenowany cross-model KV injection);
  - lookup nie ma stanu.
- Przy Main ↔ Uncensored KV MTP przechodzi razem ze slotem. W trybie w locie MTP może nawet zostać nieablowany: to drafter, więc wyjście się nie zmieni, a akceptacja co najwyżej lekko spadnie `[INFERENCE]`.

### 4.4 Routing między rozmiarami

- **W produkcie nie występuje.** Jeden konsumencki GPU nie trzyma naraz dwóch rozmiarów. Podkręt wybiera model pod sprzęt, a nie per zapytanie.
- **Jedyna para w paperowym sensie, jaką mamy na dysku: LFM2.5-2.6B ↔ LFM2.5-24B-A2B.**
  - Za: identyczny tokenizer i szablon (sprawdzone: tokens, merges, template = True), matched-KV 8 × 64, RoPE base 1e7.
  - Przeciw: 8 vs 10 warstw atencji i dense vs MoE.
  - Z §2.2 wynika, że cel z KV ze źródła nie bije samego źródła. Dla 2.6B → 24B nie ma więc sensu, a 24B → 2.6B to tani prefill (2.6B), który nie wymaga mapowania.
  - **Nie robić.**

### 4.5 Co byłoby potrzebne dla hybryd (nasze modele)

Paper mapuje KV atencji token po tokenie. Hybryda ma dodatkowo stan rekurencyjny, który nie jest per-token.

- **LFM (shortconv, `l_cache=3`).**
  - Stan to 2 ostatnie wejścia konwolucji na warstwę.
  - Wyjście tokenu T zależy przez ścieżkę konwolucyjną od tokenów ≥ T − 2·30 = T − 60. Wszystko starsze płynie tylko przez KV atencji.
  - Wystarczy więc zmapować KV 10 warstw atencji i przeliczyć celem **ostatnie ≥ 61 tokenów** od zerowego stanu konwolucji. Stan conv wyjdzie wtedy dokładny względem zmapowanego KV, a koszt jest pomijalny.
  - **Hybrydy konwolucyjne są dla tej metody łatwiejsze niż dense.**
- **Qwen (Gated DeltaNet, 48 warstw, stan 48 heads × 128 × 128 f32 = 151 MB).**
  - Policzyłem zanik przy zerowym wejściu `exp(ssm_a·softplus(ssm_dt))` dla 2304 głowic. Połówkowy czas zaniku: p50 = 25.5, p75 = 274, p90 = 1 010, p99 = 2 574, max 18 132 tokenów. 9.8% głowic > 1024, 0.3% > 4096.
  - Gate zależy też od wejścia (`alpha` z `ssm_alpha`), więc to tylko orientacja `[INFERENCE]`.
  - **Opcje:**
    - (i) stan zerowy + re-prefill okna W (przybliżenie „sliding-window GDN”; przy W = 8k zostaje ~11% pamięci głowic o połowicznym czasie 2.5k);
    - (ii) mapowanie samego stanu S_B ≈ M_k·S_A·M_vᵀ per głowica, poprawne tylko przy zgodnych gate i β, czyli nie dla innego rozmiaru;
    - (iii) zapis per-token wejść GDN źródła (q, k, v, g, β, ~10.3k elementów na warstwę na token, czyli **~14× więcej** niż KV atencji) i ponowny scan w celu.
  - Wszystkie trzy to projekt badawczy z nieznaną retencją. Dla produktu nieopłacalny, bo brak przypadku użycia (§4.4).
- **Wariant „gojenia” dla near-identity (Main → Uncensored):**
  - restore pełnego stanu Maina, potem rollback do checkpointu z pozycji T − W i re-prefill ostatnich W tokenów modelem docelowym;
  - KV ostatnich W tokenów będzie dokładne, a błąd stanu GDN wygasa z gate'ami;
  - koszt przy W = 4096 i pp ~1 110 t/s (`modele/qwen3-8-27b.md`) to ~3.7 s;
  - mechanizm już istnieje (`--ctx-checkpoints`, `common/arg.cpp:1695`);
  - warto tylko wtedy, gdy E2 wykaże, że czysty identity jest za słaby.

## 5. „Uncensored jako tryb”: plan adopcji

**Pomysł.** Edycje z §3 są liniowe i dotyczą wyjść writerów. Dla każdego writera W' x = W x − s·r(rᵀ·Wx), więc identyczną funkcję uzyskamy, zostawiając wagi Maina i dodając w grafie korektę na wyjściu writera.

- **Qwen (s = 1, wszystkie writery, embedding):** równoważnie można rzutować strumień rezydualny `h ← h − r(r·h)` po embeddingu i po każdym dodaniu. Indukcyjnie h ⊥ r, więc wynik jest ten sam. Miejsca w grafie: `src/models/qwen35.cpp:180` (attn residual), `:195` (ffn residual), MTP `:603`, `:618`. Bez `eh_proj`, który Orca zostawiła.
- **LFM (s = 1.75, kierunek per warstwa):** korekta musi iść na wyjściu writera przed dodaniem, bo nie jest idempotentna. Dotyczy 26 warstw × 2 writery.
- Istniejący `--control-vector` w llama.cpp jest tylko addytywny (`src/llama-adapter.cpp:22-25`), więc potrzebny jest nowy, mały mechanizm „projection vector”.
- Najtaniej wpiąć korektę w istniejące fuzje add + rms_norm forka: zero dodatkowych launchy.

**Szacowany zysk:**
- Przełączenie Main ↔ Uncensored w trakcie sesji: 0 s zamiast przeładowania i ~61.5 s prefillu (Qwen @53k) albo ~12.2 s (LFM @53k).
- Mniej plików do pobrania i trzymania: −15.66 GiB (Qwen) i −16.10 GiB (LFM).
- Prędkość:
  - Uncensored-Qwen dziś: 115.5 t/s (Q4_K_M, mniejszy plik); Main 109.0 t/s (`modele/qwen3-8-27b-uncensored.md:15`, `modele/qwen3-8-27b.md:20`). Tryb w locie dałby Uncensored z prędkością Maina (−5.6%) minus narzut. Narzut bez fuzji: ~130 małych kerneli × ~4 µs ≈ 0.5 ms na krok 27.7 ms, czyli ~2%; z fuzją ≈ 0 `[INFERENCE: nie mierzone]`.
  - LFM-Uncensored dziś: 267.3 t/s; LFM 293.7 t/s (`modele/lfm2-5-uncensored.md:15`, `modele/lfm2-5-24b-a2b.md:16`). W trybie w locie Uncensored zyskałby **~+10%**, bo AtomicChat ma cięższe tensory Q8_0.
- **Jakość:** Uncensored dostaje kwant Maina (UD-Q4_K_XL z imatrix; LFM Q5_K_M) zamiast Q4_K_M bez imatrix (Orca: brak `quantize.imatrix.*` w metadanych).

**Do decyzji użytkownika (nie techniczne):**
- **Licencja i proweniencja wektorów.** Kierunki r wyciągnęliśmy z cudzych GGUF. Qwen/Orca: Apache 2.0. LFM-Uncensored: licencja `lfm1.0`, a metadane AtomicChat wskazują ich własny proces. Czy dystrybuować wektory jako część produktu, czy liczyć własne (metoda Arditi i in. 2024, https://arxiv.org/abs/2406.11717, wymaga zbioru promptów harmful/harmless i jednego przebiegu modelu)?
- Prędkość Q4_K_M (Uncensored Orca 115.5) vs jakość UD (109.0). Można też ablować w locie mniejszy kwant Maina.

## 6. Eksperymenty (kolejność, koszty, kill criteria)

**E0, zrobione (CPU, ~10 min łącznie):** dekompozycja wag (§3). Kierunki zapisane: `21e-skrypty/r_qwen.npy` (5120, z różnicy embeddingu) i `r_lfm.npy` (40 × 2048; warstwy 0–13 to szum, nie używać). Szczegółowo zbadano tylko próbkę: 21 z ~131 writerów Qwena i wszystkie 40 warstw LFM (writer główny + ffn_down_exps). Pełny skan Qwena przerwałem z powodu obciążenia CPU; wynik próbki jest jednoznaczny.

**E1 (CPU, 15 min, bez ładowania modelu): kontrola, że tryb w locie odtwarza wagi Orki.**
- Dla każdego writera porównać ‖W_main − s·r rᵀW_main − W_unc‖ z ‖W_main − W_unc‖. Oczekiwane: spadek do podłogi szumu kwantów (resid ~0.95–0.98 jak w `qwen_abl_s.txt`).
- Kill: jakikolwiek writer z s poza 0.97–1.03 (Qwen), poza 1.72–1.78 (LFM 14–39) albo |s| > 0.02 (LFM 0–13) oznacza, że edycja nie jest czysto rank-1 i trzeba ją rozpoznać od nowa.

**E2 (GPU XTX, ~1 h, zero zmian w kodzie): identity transfer Main → Uncensored.**
- Sesje 8k / 32k / 53k z korpusu agentowego 16f E5 oraz 50 promptów „harmful” wstrzykniętych w środek sesji.
- `run-llm.sh qwen` z `--slot-save-path`, `save`; potem `run-llm.sh uncensored` (z szablonem Maina), `restore`.
- Porównanie z Uncensored po własnym prefillu:
  - (a) KLD na 512 tokenach teacher-forced (mały program na `llama_state_seq_get_data/set_data` + logity, ~0.5 dnia; wersja zastępcza: top-20 `n_probs` z serwera);
  - (b) greedy agreement;
  - (c) refusal rate na 50 promptach (KV od Maina vs własny prefill).
- Bramka: KLD ≤ 0.01 (rząd podłogi Q8_0 vs BF16 = 0.0038 wiki, `16e-kwanty-kld.md:49`; dla porównania U3 vs BF16 PL to 0.032, `:24`) oraz różnica refusal rate ≤ 5 pp.
- Kill: KLD > 0.05 albo różnica refusal > 10 pp. Wtedy tylko wariant „gojenia” (W = 4096, +3.7 s) albo pełny prefill.
- To samo dla LFM: oczekiwana mniejsza KLD, bo 14/40 warstw jest identycznych.

**E3 (fork, 2–3 dni): tryb w locie.**
- Op w grafie przy `qwen35.cpp:180/195` i w writerach LFM, z wyłącznikiem. Przy wyłączonym trybie graf musi być bitowo identyczny (md5 greedy jak w 16f E4).
- Walidacja:
  - (a) KLD(Main + tryb vs Orca Q4_K_M) ≈ KLD(Main vs Orca-bez-ablacji). Proxy: KLD między dwoma kwantami tego samego modelu, rząd ~0.03;
  - (b) refusal rate na 50 promptach równy Orce ±10 pp;
  - (c) t/s: narzut ≤ 2% bez fuzji, ≤ 0.5% z fuzją.
- Kill: (b) nie przechodzi (np. Orca robiła coś poza rank-1, czego nie widać w próbce) albo narzut > 3% bez możliwości fuzji.

**E4 (opcjonalnie, tylko jeśli kiedyś pojawi się routing rozmiarów):** paperowy ridge dla par hybrydowych. Kalibracja na CPU wykonalna: 16 warstw, d_s = 8192, N = 128k daje 1.4·10¹⁴ FLOP, czyli ~5 min. Zbieranie KV obu modeli to prefill 512k tokenów na model, ~8 min na XTX. Bramka z §2.2: transfer musi pobić **model źródłowy**, nie tylko „retencję celu”. Dziś nie planować.

## 7. Bezpieczeństwo sprzętu i ryzyka

- **SSD:** wariant A zapisuje ~2.28 GiB na każde przełączenie Qwena (`16f:199`). Przy 20 przełączeniach dziennie to ~45 GiB/dzień, poniżej 0.1 DWPD dla dysku 1 TB `[INFERENCE: typowy TBW konsumenckich NVMe 600 TBW/TB]`. Wariant B nie zapisuje nic.
- **Termika i stabilność:** bez zmian. Mapper paperowy dodałby 0.5–1 GB VRAM (bf16), czego na 24 GB z modelem 16 GB + KV nie mamy w zapasie.
- **Poprawność:** brak sprawdzania tożsamości modelu w restore llama.cpp (§4.1). Blokada hashem w wrapperze jest obowiązkowa.

## Źródła

- Paper: https://arxiv.org/abs/2608.03893, TeX https://arxiv.org/src/2608.03893. Linie TeX jak w tekście (`sections/03_mapper_design.tex:63`, `sections/04_experiments.tex:61-95,239,316`, `sections/05_discussion.tex:54-56`, `appendix/C_ablation.tex:111`, `appendix/D_setup.tex:93-115`, `appendix/E_run_info.tex:14-15`, `appendix/F_extended_results.tex:23-40,88-91`, `appendix/G_latency.tex:31-35,58-59`).
- DroidSpeak (współdzielenie KV między fine-tune'ami tej samej architektury, selektywne przeliczanie kilku warstw; „~3.1× szybszy prefill” wg abstraktu, nie weryfikowałem): https://arxiv.org/abs/2411.02820.
- Ablacja kierunku odmowy w locie ≡ ortogonalizacja wag: Arditi i in. 2024, https://arxiv.org/abs/2406.11717.
- llama.cpp (upstream `~/llama.cpp` @ `b356fa262`): `src/llama-context.cpp:3204`, `src/llama-kv-cache.cpp:2528-2640`, `src/llama-memory-recurrent.cpp:1095-1209`, `src/llama-adapter.cpp:22-25`, `src/models/qwen35.cpp:180,195,373,603,618`, `common/arg.cpp:1695`.
- Nasze: `16f-xtx-szybkie.md:194-215` (E5), `16e-kwanty-kld.md:24,49`, wiki `modele/qwen3-8-27b*.md`, `modele/lfm2-5-*.md`, `21e-skrypty/*`.

## Do bazy wiedzy

Folder `research/`. Tytuł: **„Raport 21e: KV między modelami (NVIDIA 2608.03893) i Uncensored jako edycja rank-1”**:
- Paper: ridge per head, top-k warstw, KV bez RoPE; 73–98% retencji na 4/6 parach (`sections/04_experiments.tex:90-93`), 2.7–25× vs re-prefill na 8×H100 (`appendix/G_latency.tex:31-35`). Tylko dense full-attention i matched-KV, mapper 4–12 GB fp32.
- Brak bazy „zostań na źródle”. Transfer < źródło na średniej z 5 benchmarków we wszystkich 4 udanych parach (Qwen3 14B→32B 76.07 vs 76.50; `appendix/F_extended_results.tex:23-40`). Na GSM8K zawsze gorszy.
- Dla nas nie do użycia wprost (hybrydy, brak par z rodziny, LFM ↔ Qwen to różne tokenizery).

Folder `modele/` (dopisać do stron Uncensored). Tytuł: **„Uncensored = Main + rank-1 edycja writerów”**:
- Qwen Orca: jeden globalny kierunek, s = 0.994–1.000, writery warstw 0–64 + embedding (`21e-skrypty/qwen_abl_s.txt`). Czytający i F32 bez zmian, `output.weight` bajtowo identyczny.
- LFM AtomicChat: kierunek per warstwa, s = 1.745–1.760 w warstwach 14–39, warstwy 0–13 nieruszone (`21e-skrypty/lfm_abl.txt`).

Folder `produkt/`. Tytuł: **„Przełączanie Main ↔ Uncensored”**:
- llama.cpp przyjmuje slot innego modelu o tych samych kształtach (`llama-context.cpp:3204`, `llama-kv-cache.cpp:2528-2640`). Restore 2.51 s vs prefill 61.5 s @53k (`16f:199`).
- Tryb Uncensored w locie (`h ← h − r(r·h)`) usuwa plik 15.66 / 16.10 GiB i czas przełączenia. Czeka na E2 (KLD ≤ 0.01, refusal ±5 pp) i E3.

Folder `kernele/` albo `modele/qwen3-8-27b`. Tytuł: **„Pamięć stanu GDN”**: połówkowy czas zaniku przy zerowym wejściu p50 25 / p90 1 010 / p99 2 574 / max 18 132 tokenów (2304 głowice).
