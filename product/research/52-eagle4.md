# 52. EAGLE-4: co bierzemy do topki (XTX) i cuda-topka2

Data: 2026-10-21. Autor: podagent Res52Eagle4. Tylko CPU, bez GPU, bez wydatków.
Źródła:
- paper `EAGLE4_Paper.pdf` (repo `eagle-hq/EAGLE-4` @ `7b7b5a5`, 2026-10-20);
- kod `eagle_harness/` (`core/cost_model.py`, `vllm/depth_stop.py`, `vllm/tree_accept.py`, `models/low_rank_head.py`, profile MI355X);
- blog https://blog.eagle.ai/blog/introducing-eagle-4;
- HF `EAGLE-Corp/Qwen3.8-27B-EAGLE4`: `config.json` i nagłówek safetensors pobrane zakresem bajtów, do tego 4 wiersze `embed_tokens`/`lm_head` porównane z `Qwen/Qwen3.8-27B`;
- nasze raporty 10, 24p, 24q, 24s, 32b, 32f, 36, 40, 44 i upstream `~/llama.cpp/src/models/eagle3.cpp`.

`[INFERENCE]` = wniosek bez pomiaru.

## TL;DR

1. **Najwięcej realnej wartości ma u nas pomysł, nie drafter: EAGLE Efficient LM Head nałożony na naszą głowicę draftu MTP.** Low-rank r=128 wyszukuje kandydatów w pełnym słowniku 248k, potem przeliczamy dokładnie 128 wierszy `output.weight` (Q6_K, już w VRAM). Dwa efekty naraz:
   - taśma draftu −0.5 ms/krok (−1.9%), bo 4 × 178 MB głowicy 64k zamienia się na 4 × ~35 MB;
   - znika OOV 64k, a to 14% polskich pęknięć (sufit +4.5% tok/krok na E0, PL +6.8%, raport 40).

   Szacunek: **proza PL +3…6%, EN +2…3%, kod +1.5…2%** `[INFERENCE]`. Bezstratne, bo zmienia się tylko propozycja. Głowicy weryfikacji (1.23 ms) to nie dotyczy: EAGLE tego nie robi, a raport 36 pokazał, że dokładna wersja wymaga przybliżenia klasy Q8.
2. **Ich drafter dla Qwen3.8-27B istnieje i pasuje do naszego celu, ale do produktu się nie nadaje.**
   - Budowa: EAGLE-3.1, cechy z warstw 3/31/59, 1 warstwa 0.435 mld param., pełny słownik, 6.18 GB BF16.
   - Licencja „Eagle 4” obejmuje też wagi. Nasz produkt (szybki silnik inferencji) to najpewniej „Competing Offering” `[INFERENCE, nie porada prawna]`, czyli wolno nam go tylko ewaluować.
   - Akceptacji tego draftera nikt nie opublikował (paper celowo podaje tylko t/s). Jedyne porównanie łańcuch vs łańcuch MTP (Nemotron, C=1) daje **×1.14**.
   - U nas w łańcuchu oczekuję: proza PL **−3…+14%**, EN **0…+11%**, kod T=0 ≈ 0. To poniżej progu +25% nawet w optymistycznym scenariuszu `[INFERENCE]`.
3. **EAGLE-Harness to dla batch=1 nasz 24q/E5 plus automatyczna kalibracja kosztów.**
   - Reguła ΔA/ΔC ≥ τ z progiem rosnącym z głębokością jest tańsza od naszego kontrolera.
   - Nasze kluczowane próbkowanie Gumbela pozwala decydować z bieżącej rundy także przy T>0. EAGLE przy T>0 (SGLang) musi brać głębokość z poprzedniej rundy.
   - Nowe są dla nas tylko dwie rzeczy: tabela kosztów mierzona przy rozgrzewce (przyda się cuda-topka2 na wielu kartach) i ocena gałęzi iloczynem prawdopodobieństw draftu.
4. **961.6 t/s jest niesprawdzalne.**
   - Źródłem jest „PR #3”, którego nie ma w publicznym repo (0 PR, repo założone 2026-10-20). README mówi wprost: „No TokenSpeed throughput is claimed”.
   - Nawet gdyby było prawdziwe: runda (12 kroków draftu + 16 wierszy weryfikacji) kosztuje tam 4.93 ms, czyli 1.19× zwykłego tokenu. To efekt sprzętu (BF16 na 4×B300), nie draftera.
5. **Następny krok:** E52a, ≤10 min GPU. Zrzut cech celu z warstw 3/31/59 (i −1) na E0, a potem lustro CPU ich draftera i naszego MTP w tej samej metryce sprzężonej. Równolegle E52b (CPU): trening czynników low-rank dla naszej głowicy MTP i bramka recall top-20.

## 1. Co to jest (z kodu i wag, nie z bloga)

| element | fakt | źródło |
|---|---|---|
| Drafter Qwen3.8-27B | `LlamaForCausalLMEagle4`, 1 warstwa Llama, hidden 5120, **MHA 40/40 głów** ×128, FFN 16384, `sliding_window` 4096, RoPE θ=1e7 | `config.json` |
| Cechy celu | `eagle_aux_hidden_state_layer_ids` [3, 31, 59] (wyjścia warstw z 64), `fc` 15360→5120, **3 osobne RMSNorm** `fc_norm.{0,1,2}` (EAGLE-3.1), `norm_output` | config + nagłówek |
| Embed | `embed_tokens` [248320, 5120] **bitowo równy embedowi celu** (4/4 wiersze), więc można go współdzielić | range-request, `rowcmp.py` |
| LM head | własny `lm_head` [248320, 5120], **cos ≈ 0 z `lm_head` celu** (4/4 wiersze), więc NIE da się go współdzielić z `output.weight` | jw. |
| Efficient head | `efficient_lm_head_down_proj` [128, 5120] + `efficient_lm_head` [248320, 128], K = 128 kandydatów | nagłówek |
| Rozmiar | 6.18 GB BF16, 3.089 mld param. (warstwa 0.435, fc 0.079, embed 1.27, lm_head 1.27, low-rank 0.032) | nagłówek |
| Trening | TorchSpec (lightseekorg). Dwa etapy: gęsty drafter, potem tylko czynniki low-rank przy zamrożonym drafterze (`forward_kl`, r=128, top_k 128). **Dane i rewizja nieujawnione** („source bundle from the training maintainer”). | `docs/new-model.md` |
| Weryfikacja T>0 (vLLM) | Każdy wiersz drzewa dostaje token celu z Gumbel-max kluczowanego (seed, pozycja). Spacer po drzewie przyjmuje dziecko równe tokenowi celu. Wyjście = losowanie bez spekulacji z tym samym seedem. **To dokładnie nasze sprzężone próbkowanie (24p).** | `vllm/tree_accept.py:4-15` |
| Bramka greedy | „exact / near tie / fp32-tolerance” (np. 5 / 14 / 1 na 20 promptów), **nie bitowa**. Nasza bramka md5 jest ostrzejsza. | `docs/support-matrix.md` |
| Harness | ΔA/ΔC ≥ τ w 3 miejscach: (1) głębokość, τ_d rośnie z d; (2) liczba wierszy weryfikacji: dokładamy węzły po p̂, dopóki p̂ₙ₊₁ / Δc_ver ≥ τ_v; (3) szerokość z obciążenia (8 vs 4 gałęzie). p̂ = iloczyn prawdopodobieństw draftu na ścieżce (EAGLE-2). Przy T>0 (SGLang) głębokość rundy ustalana jest z poprzedniej rundy. | paper §3.1, Alg. 1; `depth_stop.py` |
| Koszty MI355X TP1 (BF16) | weryfikacja 1/8/16/32 tok. = 11.98 / 14.19 / 15.34 / 16.72 ms, czyli wiersz +0.31 ms (2.6%) do 8 i +0.22 ms (1.9%) do 16; krok draftu 0.35 ms (2.9%). **U nas wiersz 0.85 ms (3.1%), poziom 1.40 ms (5.1%).** | `core/profiles/mi355x-*/cost/bs_1` |

Wniosek z ostatniego wiersza: na jednym GPU (MI355X TP1) wiersz jest tylko 1.2–1.6× tańszy względnie niż u nas. Drzewo 12-4-32 daje tam 3.49× (SPEED-Bench z myśleniem). Bariera drzew u nas to więc nie tylko sprzęt. Decydują też: słabsza akceptacja na prozie i brak weryfikacji drzewa dla GDN w forku (24s).

## 2. Tabela tez

| # | teza | warunki / co sprawdziłem | werdykt |
|---|---|---|---|
| T1 | 961.6 t/s, Qwen3.8-27B, TokenSpeed | Blog: BF16, 4×B300 TP4, C=1, T=0, SPEED-Bench 88 rozmów / 117 tur, **myślenie xhigh**, ≤4096 tok./turę, seed 721, drzewo 12/4/16, **akceptacja 4.745/rundę** (SGLang ref. 837.6 / 4.784). T=1: 734.2 / 3.598. Runda 4.93 ms vs zwykły token 4.16 ms. PR #3 nie istnieje publicznie (`gh api …/pulls` = 0). README: „No TokenSpeed throughput is claimed”. | **Niesprawdzalne**, wewnętrznie spójne. Nieporównywalne z nami: zysk pochodzi z darmowych wierszy na 4×B300 i reasoningu |
| T2 | EAGLE-4 1.62× nad MTP przy C=1 | Tabela 2: 863.8 vs 534.5 (T=0), 608.6 vs 369.1 (T=1). MTP to łańcuch 7-1-8 bez drzewa i harnessu, a EAGLE-4 to drzewo 12-4-16 z harnessem. Długości akceptacji świadomie pominięte („we focus on overall throughput”). Jedyne porównanie łańcuch vs łańcuch: Nemotron 647 vs 568 (**×1.14**), T=1 563 vs 500 (×1.13). | **Częściowo.** Sam drafter daje w łańcuchu ≲ ×1.14 (na innym celu). Reszta to drzewo przy taniej weryfikacji |
| T3 | Telefon: 166 vs 356 mJ/tok., 14 vs 43 s | Arytmetyka się zgadza: ~1000 tokenów w obu wariantach; moc 8.3 W → 12.4 W. Ale: drafter Gemma-4-E2B i ich fork llama.cpp nie są opublikowane (HF EAGLE-Corp ma 2 modele: Qwen, Nemotron). Bazą był upstream llama.cpp **bez** ich optymalizacji ARM (pula wątków, FP16, NEON BF16, mały kernel uwagi), więc część zysku to inżynieria. T=0, chłodne urządzenie. | **Spójne, niereplikowalne.** Mieszanka draftera i optymalizacji CPU |
| T4 | Harness profiluje koszty przy rozgrzewce i dobiera głębokość, szerokość i budżet weryfikacji | Potwierdzone w kodzie: tabele `cost/bs_N/{model,query,cache}_{llm,slm}`, `live_costs.py`, `depth_stop.py` (reguła z §1). SGLang mierzy koszty na żywo, vLLM wymaga `eagle-harness calibrate`. | **Prawda.** Dla batch=1 to wariant naszego 24q/E5 (§4.3) |
| T5 | Efficient LM Head: draft 574 → 255 µs | Arytmetyka: head 375 µs → 46 µs (r=128), reszta ~200–209 µs stała; 375 µs na 2.54 GB BF16 = 6.8 TB/s, czyli profil na 1×B300 `[INFERENCE]`. Recall top-1 w 128 kandydatach: 98.2% po treningu vs 91.5% z SVD. Samo SVD obniża akceptację o 0.48 tok./rundę. | **Prawda jako optymalizacja draftu.** Dokładne są tylko logity w C (§3) |
| T6 | Shortlist + dokładne przeliczenie jest „dokładne” | Ani ograniczenia, ani fallbacku: token spoza C nie może być zaproponowany. Wyjście jest jednak bezstratne przy każdym T, bo C wpływa tylko na propozycję. Przy rejection q = softmax po C jest poprawnym rozkładem, przy spacerze Gumbela q w ogóle nie wchodzi. | **Bezstratne dla wyjścia, nie dokładne wobec pełnego draftu.** Prior art: SVD-softmax (Shim i in. 2017), tqLLM (32f/36) |
| T7 | Jeden drafter na cel, na każdy sprzęt i batch | Wagi te same, konfiguracje różne: 12-4-16 (C=1), 15-1-16 (C=512), 12-4-32 (MI355X), a każdy sprzęt wymaga kalibracji (paczka profili tylko dla MI355X i vLLM TP4). | **Prawda dla wag**, nie dla konfiguracji |
| T8 | Wsparcie llama.cpp | Upstream EAGLE-3 (#18039, 2026-06) jest w naszej bazie (`src/models/eagle3.cpp`). Do checkpointu EAGLE-4 brakuje: 3 osobnych `fc_norm` (upstream ma jeden `norm_before_fc` na 15360), `norm_output`, głowicy low-rank + gather (nowe), nazwy arch w konwerterze. Konwencja indeksów: EAGLE-4 podaje wyjścia warstw, upstream qwen35 wyciąga wejścia, więc pewnie +1. Ścieżka `draft-eagle3` omija nasz graf MTP 0020, sprzężone GPU verify i słownik 64k. | **Nie działa bez łatek.** 3–5 dni do topki `[INFERENCE]` |
| T9 | Licencja | „Eagle 4 Source-Available” obejmuje kod **i wagi**. Commercial Use do $20 M przychodu, chyba że to Competing Offering: „incorporates material Eagle 4 technology into a … inference … acceleration … framework that competes”. Definicja „Eagle 4” obejmuje „technology … EAGLE-Harness and EAGLE Efficient LM Head”. Licencja patentowa wąska. | **Produkt: nie bez licencji komercyjnej** `[INFERENCE, nie porada prawna]`. Ewaluacja wewnętrzna: tak. Własna implementacja: clean-room z prior art |

## 3. Efficient LM Head: matematyka i nasze dwie głowice

Ich wersja: z̃ = A(Bh) (A: V×r, B: r×d), C = TopK(z̃, K), z_C = W_C h. Koszt O(dr + Vr + Kd) zamiast O(Vd). Czynniki A, B trenowane wyłącznie do wyszukiwania (forward KL na top-K) przy zamrożonym drafterze. Inicjalizacja: SVD ważone częstością tokenów, D = freq/mean + 10 (`low_rank_head.py`).

**3.1 Nasza głowica draftu (64k IQ4_XS, 178 MB na przebieg, 4 przebiegi):**
- Zamiast niej: A w Q8_0 (248320×128 ≈ 34 MB) + B (0.65 M) + top-128 po 248k + `get_rows` 128 wierszy `output.weight` Q6_K (0.54 MB) + mul_mat 128×5120.
  - Głowica MTP Qwena **współdzieli `output.weight` celu**, więc dokładne przeliczenie nie kosztuje VRAM.
  - Zwalnia się kopia 64k (178 MB) i wiersze `token_embd` 64k z łatki 0020 (180 MiB).
- Pasmo: −143 MB na przebieg ≈ −0.16 ms. Po odjęciu top-k (+~0.03 ms) przy n=4 to **−0.5 ms/krok = −1.9%**.
  - Na 4060 Ti głowica 64k kosztuje 0.655 ms × 4 (31-4060ti). Zysk ~2.1 ms ≈ 3.6% `[INFERENCE]`.
- Akceptacja: pełny słownik usuwa OOV (PL 6.7% tokenów, 14% pęknięć). Przy recall top-20 ≥ 98% odzysk to 35–70% sufitu +4.5% (PL +6.8%) `[INFERENCE]`.
- Sprzężone próbkowanie: draft filtruje top-k 20 → top-p → min-p. Przy K=128 ≥ 20 wynik jest identyczny z pełnym słownikiem, jeśli top-20 draftu siedzi w C. Wyjście bezstratne w każdym przypadku. **md5 T=0 bez zmian** `[INFERENCE]`: szerokość weryfikacji stała, zmienia się tylko propozycja, jak w 24p. Bramka potwierdzi.

**3.2 Głowica weryfikacji (Q6_K 1043 MB, 1.23 ms):**
- EAGLE stosuje sztuczkę tylko w drafcie. W celu shortlist zmienia p.
- Raport 36: certyfikat dokładności przechodzi dopiero przy przybliżeniu Q8_0, które jest większe niż Q6_K. Wariant stratny Q4_K + top-64 daje +1.3–2.0%.
- **Nic nowego; zostaje kill z 36.**

## 4. Przeniesienie na nas (liczby)

Model kosztu (36/40): krok(n) = 21.78 + n·1.40 ms (n=4 → 27.38), poziom = przebieg draftu 0.55 + wiersz 0.85.
Akceptacja warunkowa MTP na E0: PL 0.635/0.461/0.350/0.296, EN 0.677/0.546/0.457/0.440.
Skrypt: `/tmp/e4model.py` (wynik niżej, n=3 i n=4).

### 4.1 Ich drafter zamiast MTP (łańcuch, bez drzewa)

- Koszt przebiegu na XTX `[INFERENCE]`:
  - warstwa Q4_K 0.245 GB + low-rank 34 MB + KV SWA (MHA: 20 KB/tok. BF16, ≤ 84 MB przy 4k) ≈ 0.55 ms (jak MTP); w Q8_0 ≈ 0.80 ms;
  - `fc` raz na krok (15360×5120) ≈ +0.05 ms;
  - zrzut 3 cech celu na przyjęty token: pomijalny.
- VRAM: warstwa 0.25–0.46 + fc 0.04–0.08 + **własny lm_head 0.71 (Q4_K) – 1.35 GB (Q8_0)** (rezydentny dla gather) + low-rank 0.03–0.06. Embed współdzielony, MTP zwolnione. Razem **+1.0…1.9 GB**.

| scenariusz (proza T=1) | warunkowa poz. 1–4 | n=3 tok/krok, t/s | n=4 tok/krok, t/s | vs MTP n=3 |
|---|---|---|---|---|
| PL, MTP (E0, model) | 0.635 / 0.461 / 0.350 / 0.296 | 2.030, 78.1 | 2.061, 75.3 | – |
| PL, EAGLE-4 pesymistycznie (dane bez PL) | 0.60 / 0.45 / 0.35 / 0.30 | 1.965, 75.5 | 1.993, 72.7 | **−3%** |
| PL, EAGLE-4 optymistycznie (TTT domyka ~1/3 luki do wyroczni na poz. 2–4, pełny słownik) | 0.69 / 0.56 / 0.49 / 0.45 | 2.266, 87.0 | 2.351, 85.7 | **+11…14%** |
| EN, MTP (E0) | 0.677 / 0.546 / 0.457 / 0.440 | 2.216, 85.3 | 2.290, 83.6 | – |
| EN, EAGLE-4 optymistycznie | 0.72 / 0.62 / 0.56 / 0.53 | 2.416, 92.8 | 2.549, 92.9 | **+9%** |

- Kod T=0: produkcję niesie lookup (mvs 14.2 tok/krok) i MTP n=5 (routing 44). Drafter EAGLE ruszyłby tylko kod nie-kopiowy: 0…+10% `[INFERENCE]`.
- Rozdzielenie drafter vs sprzęt:
  - ich ×1.62 nad MTP przy C=1 to głównie drzewo 16 wierszy. Na B300 TP4 runda z 16 wierszami kosztuje 1.19× tokenu, u nas 11 dodatkowych wierszy to +9.4 ms (+34%);
  - w łańcuchu sam drafter (Nemotron) daje ×1.14, a łańcuch miał głębokość 15 z dynamicznym stopem vs stałe 7.
- **Wniosek:** nawet optymistycznie poniżej +25% (raport 40). Wartość ich draftera dla nas: punkt odniesienia „ile da EAGLE-3.1 + TTT na tym celu” przed treningiem własnego.

### 4.2 Efficient head na naszej głowicy draftu: §3.1. Proza PL +3…6%, EN +2…3%, kod +1.5…2%.

### 4.3 Harness vs nasze sprzężenie + routing (44) + adaptacyjna głębokość (24q/E5)

| element harnessu | u nas | co nowego |
|---|---|---|
| ΔA/ΔC dla głębokości, τ_d rośnie z d | `LLAMA_SPEC_DEPTH_ADAPT` (24q: symulacja czat +2.6…3.1%, krótkie dokumenty +7…8%). Bez bitexact łamie md5, z bitexact (−0.6%, 32b) netto czat +2.0…2.5% | Próg rosnący z głębokością i p̂ = iloczyn prawdopodobieństw draftu po filtrach (tani, bez głowicy pewności z 32b #5) |
| Budżet weryfikacji (top-n węzłów) | Dla łańcucha to to samo co głębokość | – |
| Szerokość z obciążenia | batch = 1 | – (serwer wielu użytkowników: kiedyś) |
| Kalibracja przy rozgrzewce | Stałe 0.85/1.40 ms ręcznie z ABBA na XTX. cuda-topka2: DRAFT_N ręcznie per karta | **Tak:** auto-tabela c_draft, c_ver(n) przy starcie serwera (~2 s), szczególnie dla floty cuda-topka2 (3060…5090) |
| Głębokość przy T>0 z poprzedniej rundy (żeby nie zaburzyć rozkładu) | Gumbel kluczowany (seed, pozycja) + bitexact: tekst nie zależy od szerokości także przy T>0 (32b) | **My mamy lepiej:** decyzja z bieżącej rundy |
| Routing per żądanie (44) | profile edit/code/chat/prose | Harness go nie zastępuje. Routing ustawia sufit, harness dobiera w kroku |

Ograniczenie u nas: graf 0020 łączy 4 przebiegi draftu w jeden. Stop w środku grafu oznacza synchronizację z hostem (~0.1–0.2 ms) albo warunkowy no-op w kernelach. Taniej jest decydować o głębokości *następnej* rundy z pewności bieżącej, czyli wariant EAGLE-T>0, który u nas jest bezstratny dla rozkładu i (z bitexact) dla md5.

## 5. Ranking do przeniesienia

| # | element | proza | kod | praca | bezstratność | decyzja |
|---|---|---|---|---|---|---|
| 1 | **Low-rank retrieval + dokładne przeliczenie w głowicy draftu MTP** (pełne 248k, gather z `output.weight`) | PL +3…6%, EN +2…3% | +1.5…2% (cuda-topka2 4060 Ti ~+3.6%) | 0.5–1 dnia CPU (czynniki) + 1–2 dni kernel/graf (top-128 po 248k już mamy dla samplera) | rozkład: tak; md5 T=0: tak `[INFERENCE]` | **TAK**, clean-room z SVD-softmax |
| 2 | Reguła ΔA/ΔC + auto-kalibracja kosztów na bitexact (E5) | +1…2% ponad n=3 z routingu | czat/dok. +2…7% (24q/32b) | 1–2 dni po naprawie bramki E5 | rozkład: tak; md5: z bitexact | **TAK**, po E5; na cuda-topka2 auto-tabela per karta |
| 3 | Drafter EAGLE-4 jako wyrocznia jakości (lustro offline) | −3…+14% (niewiadoma PL) | ≈0 | E52a 10 min GPU + 3.6 GB pobrania + skrypt lustra (~0.5 dnia) | – | **TAK, tylko ewaluacja** (licencja) |
| 4 | Własny drafter EAGLE-3.1 (cechy 3 warstw, TTT, pełny słownik, lm_head = `output.weight` celu, zamrożony) | jeśli #3 ≥ +15% | ≈0 | 30–60 GPU-h (raport 10) + integracja 3–5 dni | tak | tylko gdy #3 pokaże ≥ +15% w lustrze |
| 5 | Weryfikacja drzewa dla GDN (`kernels/gdn_tree*.py` jako opis algorytmu) | 24s: +3.9…4.7% | ? | 10+ dni | tak | **NIE teraz**; czytać tylko jako referencję (licencja) |
| 6 | Shortlist w głowicy weryfikacji | +1.3–2% stratnie | – | – | stratne | **NIE** (36) |

## 6. Następne kroki

### 6.1 E52a: GPU ≤10 min (cechy celu na E0), potem lustro CPU

Przygotowanie na CPU przed kolejką:
1. **Rozszerzyć `mtp_extract.cpp`** o `--aux-layers 2,3,30,31,58,59` (dwie konwencje indeksów): `cb_eval` na tensorach `l_out-N` (`src/models/qwen35.cpp:199`), zapis `aux.f16` [n_tok, 6, 5120] (18.4k tok. ≈ 1.1 GB). Zbudować tak jak `mtp_extract_topka`:
   `cd ~/qwen-opt/mtp-train && LLAMA_SRC=<źródła topki> LLAMA_LIB=$HOME/llama-topka/bin bash build_extract.sh && cp mtp_extract ~/qwen-opt/prose-accept/mtp_extract_topka_aux`
2. **Pobrać drafter bez `embed_tokens`** (embed = embed celu, sprawdzone), ~3.6 GB zakresami bajtów. Przekracza „małe pobrania”, więc wymaga zgody Main/użytkownika. Ścieżka `~/models/draft/eagle4-qwen38/`.
3. `eagle4_mirror.py` (nowy, obok `pa_offline.py`):
   - drafter w PyTorch na CPU (BF16), teacher-forcing po całej sekwencji;
   - głębokości 2–4 rekurencyjnie na własnym hidden (`norm_output`), głowica low-rank K=128 jak w checkpoincie;
   - estymator sprzężony z `pa_offline.py` (top-k 20 / top-p 0.95 / min-p 0.05, DT=1).

Zadanie do kolejki (`~/qwen-opt/queue/`, plik `e52.jobs`):
```
# report 52: aux hidden states (l_out 2,3,30,31,58,59) on E0 outputs for the EAGLE-4 drafter mirror
e52-aux|600|~/qwen-opt/prose-accept|export GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0; export LD_LIBRARY_PATH=$HOME/llama-topka/bin:/opt/rocm/core-10.0/lib; pkill -f 'llama-topka/bin/llama-server' && sleep 5 || true; $HOME/qwen-opt/lookup/vram_ok.sh && time ./mtp_extract_topka_aux -m $HOME/models/Qwen3.8-27B-UD-Q4_K_XL.gguf --vocab $HOME/models/draft/draft_vocab_qwen38.txt --in e0x/seqs.bin --out e0x-aux -c 8192 --kv q4_0 --kv-dft q4_0 --parity-seqs 0 --aux-layers 2,3,30,31,58,59
```
Czas: jak `p40-extract` (1.7 min) + zapis 1.1 GB, razem < 4 min.

Po zadaniu (CPU, ~20–40 min):
```
cd ~/qwen-opt/prose-accept
~/qwen-opt/mtp-train/.venv/bin/python eagle4_mirror.py --aux e0x-aux --layers 3,31,59 --draft ~/models/draft/eagle4-qwen38 --seqs e0x --out off_e0_eagle4.json
~/qwen-opt/mtp-train/.venv/bin/python eagle4_mirror.py --aux e0x-aux --layers 2,30,58 --draft ~/models/draft/eagle4-qwen38 --seqs e0x --out off_e0_eagle4_m1.json
```
- Bramki:
  - lepsza z konwencji indeksów musi mieć tok/krok ≫ 1. Akceptacja ≈ 1 znaczy złe warstwy (tak ostrzega `docs/new-model.md`);
  - porównanie z `off_e0_base.json` (MTP, lustro sprzężone 2.244).
- Decyzja:
  - **≥ +15% tok/krok** (PL i EN osobno) → plan treningu własnego draftera (#4);
  - **< +8%** → zamykamy temat draftera EAGLE i zostaje #1 + #2.

### 6.2 E52b: CPU, głowica low-rank dla naszego MTP (bez GPU)
- Dane: hidden MTP na wszystkich pozycjach łańcucha z lustra (`ext_head.py --head` na `e0x` + `ext_p1`, ~100k stanów) i pełne logity z `output.weight` (dequant Q6_K).
- Inicjalizacja: SVD ważone częstością (`torch.svd_lowrank`, q=256 → r=128) na `output.weight`. Częstości z wyjść celu E0 + `ext_p1`.
- Trening: A, B (32 M param.), forward KL na top-128 + kara za brak top-20 w C. MTP zamrożone. CPU 1–2 h albo pod ~$1.
- Bramka: recall top-20 ≥ 99% i top-1 ≥ 99.5% na odłożonych E0. Tok/krok w lustrze sprzężonym ≥ dziś + odzysk ≥ 35% sufitu OOV.
- Potem GPU (≤10 min): bramka md5 `c4708318`/`6f14e814` + ABBA E0 seedy 1,2 (`pa_arm.sh`), jak w 40 §3.3.

### 6.3 Plan treningu, jeśli ich draftera nie da się użyć (licencja; a #3 ≥ +15%)
- Architektura: EAGLE-3.1 jak u nich (3 cechy, `fc_norm`×3, 1 warstwa). Ale:
  - **GQA 8 KV** zamiast MHA (KV draftu 8× mniejsze);
  - `lm_head` = zamrożony `output.weight` celu (zero VRAM, gather z Q6_K);
  - low-rank r=128.
- Dane: plan 40 §5.2, czyli 20 M tokenów on-policy z naszego celu Q4 (PL 40%, EN 35%, kod 25%; 70% bez myślenia), a do tego cechy 3 warstw (31 KB/tok. → 0.6 TB na 20 M; liczone w locie w podzie).
- Trening: SpecForge/TorchSpec (sprawdzić licencję TorchSpec), TTT K=4, strata TV na filtrowanych rozkładach (to, co nagradza sprzężenie). 30–60 GPU-h A100/H100 ≈ $25–50 (raport 10).
- Bramka offline: lustro §6.1 na E0.
- Integracja: `src/models/eagle3.cpp` + per-chunk `fc_norm` + low-rank + nasza ścieżka sprzężonego GPU verify, 3–5 dni.

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| wyniki-negatywne | Drafter EAGLE-4 dla Qwen3.8-27B nie wchodzi do produktu | Licencja „Eagle 4” obejmuje wagi; silnik inferencji to Competing Offering. W łańcuchu na XTX oczekiwane −3…+14% PL, ≤ +9% EN (raport 52 §4.1). Jedyne porównanie łańcuch vs łańcuch MTP (Nemotron C=1): ×1.14 |
| metody | Efficient LM Head = retrieval low-rank + dokładne przeliczenie K wierszy | z̃ = A(Bh), C = TopK(z̃,128), z_C = W_C h. Czynniki trenowane tylko do recall (forward KL), MTP zamrożone. SVD r=128: recall top-1 91.5%, po treningu 98.2%. Bezstratne dla wyjścia, bo dotyczy tylko propozycji (raport 52 §3) |
| lekcje | Shortlist w drafcie jest bezstratny, w głowicy celu nie | W drafcie C zmienia tylko propozycję (sprzężenie Gumbela i rejection nadal dają rozkład celu). W celu shortlist zmienia p, a dokładny certyfikat wymaga Q8 (raport 36) |
| eksperymenty | Plan E52a/E52b | E52a: zrzut `l_out` 2,3,30,31,58,59 na E0 (<4 min GPU) + lustro CPU draftera EAGLE-4. E52b: low-rank r=128 dla głowicy MTP, bramka recall top-20 ≥ 99% (raport 52 §6) |
| metody | Harness EAGLE-4 dla batch = 1 | ΔA/ΔC ≥ τ_d (rosnące z głębokością) z p̂ = iloczyn prawdopodobieństw draftu i tabel kosztu z rozgrzewki. U nas Gumbel kluczowany + bitexact pozwala decydować z bieżącej rundy przy T>0, a EAGLE bierze poprzednią (raport 52 §4.3) |
| lekcje | „Lossless” w EAGLE-4 nie znaczy md5 | Bramka greedy: exact / near tie / fp32-tolerance (np. 5/14/1 na 20 promptów). Nasza bramka md5 jest ostrzejsza; ich liczb nie porównywać z naszymi bez tej różnicy |
| metody | Koszt wiersza weryfikacji na MI355X TP1 (BF16) | 1/8/16/32 tok. = 11.98/14.19/15.34/16.72 ms, czyli +0.31 ms (2.6%) na wiersz do 8. XTX: 0.85 ms (3.1%). Bariera drzew to nie tylko sprzęt (raport 52 §1) |

ZRODLA: wiersze „EAGLE-4 (paper, github eagle-hq/EAGLE-4, blog)” w sekcji *Prace naukowe* i „EAGLE-Corp/Qwen3.8-27B-EAGLE4” w sekcji *Modele, kwanty i drafery*. CompWatch: `eagle-hq/EAGLE-4`, tier A.
