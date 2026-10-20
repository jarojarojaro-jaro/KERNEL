# 32f — NInfer, tqLLM, DFlash2: czy rekordy z LocalMaxxing są porównywalne z naszymi i co z nich wziąć

Data: 2026-10-20. Autor: agent Res32fNInfer. Tylko CPU: bez GPU, bez wynajmu, bez konta.
Zakres to **delta** względem R32d (LocalMaxxing), R15c (audyt tqLLM 273.1), R16i (sufit bloku u Magnitude), R24s (koszt wiersza), R24q (głębokość MTP), `wiki/modele/drafter-dflash.md` i `NOTES.md:148-160` (DFlash vs MTP na XTX). Opisu architektury DFlash2 nie powtarzam, jest w R15b §3.
Próbka:
- 2 nowe GET do API LocalMaxxing (`leaderboard?hfId=Qwen3.8-27B&verifiedRun=true`, `?engineName=ninfer`), plus surowe pliki R32d (`/tmp/res-localmaxxing/`);
- klony `Neroued/ninfer` @ `a928f899` (gałąź `dev`, 2026-10-21 +0800) i `turbo-tan/tqllm` @ `d617986` (2026-10-17). Leżą w `/tmp/res32f/` (poza repo).

Konwencje: `[INFERENCE]` oznacza wniosek własny, niezmierzony. „mal” to średnia liczba tokenów na przebieg targetu. „Krok” (u nich „runda”) to jeden przebieg weryfikacji razem z draftem.

## TL;DR

1. **Wszystkie cztery liczby są fizycznie wiarygodne, ale żadna nie jest porównywalna z naszymi nagłówkami.** Wszystkie mierzono przy T=0 na kanonicznym `reasoning-v1`. To telegraficzny angielski tekst myślenia („We need answer user's four parts…”), tylko 320–512 tokenów wyjścia. Nasze 62.6 t/s (5060 Ti) i 93.3 t/s (3090) to czat T=1 na 6 promptach PL/EN. Na ich warunkach nasza topka z MTP n=4 dałaby szacunkowo **~82 t/s na 5060 Ti, ~125 na 3090 i ~147 na XTX** `[INFERENCE]`. Luka do tqLLM (×1.9 na 5060 Ti, ×2.2 na 3090) rozkłada się tak:
   - mniej bajtów na krok: ×1.24–1.37 (TQ_S 12.55 GB / TQ3_4S 13.9 GB, a u nas IQ4_XS 14.25 / Q4_K_XL 17.56 GB). KLD TQ_S to 0.055, UD-Q4_K_XL 0.012, więc to gorsza jakość, nie lepsza technika;
   - mal: ×1.52–1.54 (6.15–6.23 wobec ~4.05).
2. **NInfer 510.7 na 5090 to nie Qwen3.8-27B, tylko checkpoint QAT (QUASAR-QAT NVFP4), który pisze myślenie innym stylem.** Output zaczyna się od „Let me work through each part carefully. **Part 1…**”, a oficjalne wagi od „We need answer user's…”. PPL tego checkpointu jest gorsza (4.375 vs 4.321). Commitu `7d08406d` nie ma na GitHubie (HTTP 422), a konwerter był łatany lokalnie.
   - Dla oficjalnych wag NInfer daje **334.4** (mal 5.17, 15.5 ms/krok).
   - Różnica 510.7 / 334.4 = ×1.53 to ×1.32 z mal (inny tekst) i ×1.15 z mniejszych wag.
3. **Przewaga mal na tym prompcie to głównie głębokość draftu, a nie lepszy drafter.** Na tym samym `reasoning-v1` przy T=0:
   - MTP K=7–8 ma mal 5.54–5.93 (llama.cpp na MI210, vLLM na Arc);
   - DFlash2 przy K=3 w upstream llama.cpp ma 3.67, a MTP przy K=3 ma 3.54 (+4%);
   - nasze MTP n=4 ma sufit 5.

   Czyli **najtańszy transfer to MTP n=6–7 dla klasy T=0/reasoning**, bez nowego kodu. Szacunek: +12–17% t/s na tej klasie, 0 na czacie T=1 (R24q: n=6 +0.8%).
4. **DFlash2 klasy NInfer bije nasze MTP n=4 tylko przy T=0 na angielskim kodzie i myśleniu: +26–32% t/s (łańcuch K=7), drzewo +31–37%.** Warunek: krok musi być ≤ +7–12% droższy od MTP4, a tyle osiąga NInfer (17.3 vs 16.2 ms, +7%).
   - Nasza dzisiejsza ścieżka llama.cpp ma krok +38% (3090: 64 vs 46.5 ms). Powód: cechy targetu wracają przez hosta (`speculative.cpp:1208-1238`), a wybór ścieżki jest na CPU (`:1298-1325`). Przy takim kroku zysk spada do ~+2%.
   - **Przy T=1 na naszym zestawie PL/EN wychodzi −10…+1%.** Polska proza ×0.67 tok/krok (R16d). NInfer sam przy T=0.6 pokazuje Story −3%, a całość korpusu +23%. Szerokość K=9 nam nie służy: 9. wiersz na XTX to +1.37 ms (MMVQ→WMMA), CUDA MMVQ ma ≤ 8 kolumn, a NInfer z K=9 zamiast K=7 dostał tylko +3.5%.
5. **„Zredukowany słownik” nie jest dla nas nowością.** NInfer ma shortlistę 131 072 wierszy Q4, tqLLM listę 65 536 (`atx_65536.txt`), my MTP 64k + głowice iq4_xs. Nowy jest **dwustopniowy head weryfikacji z tqLLM**: najpierw 4-bitowy przebieg po całym słowniku, potem dokładne przeliczenie top-16 (`qwen35.cpp:1548-1551`). Szacunek +1.4–1.9% na każdej klasie i karcie, 1–2 dni pracy `[INFERENCE]`.

## 1. Twierdzenia i werdykty

| # | twierdzenie | źródło | próba obalenia | werdykt | dowód |
|---|---|---|---|---|---|
| C1 | tqLLM, RTX 5060 Ti: **156.2 t/s** verified (code-v1 100.5) | LocalMaxxing `cmv2vel9u00jnmr011nbtgqet` / `…jqmr01qffc4j23`, 2026-10-10 | model: base Qwen3.8-27B ✓; kwant **TQ_S 12.55 GB, KLD 0.055** (karta HF YTan2000) wobec naszego IQ4_XS 14.25 GB; **T=0**, thinking on, 320 tok, kontekst 32k, KV tq3; embeddingi i head int8 w RAM hosta; czas silnika `(n−1)/decode`, a nie klienta; zgłaszający YTan2000 to **autor silnika**; `decodeCeiling: null` (kontroli sufitu nie było); 5 runów 151.4–164.6. Fizyka: ~12.2 GB/krok w 39.9 ms = 68% z 448 GB/s, więc wiarygodne. Ich README podaje dla tej karty **77–95 t/s na streszczeniach** | **prawdziwe dla klasy „T=0, myślenie EN, 320 tok”**; z naszym 62.6 (T=1, czat PL/EN) nieporównywalne | notes runu; `tqllm/README.md:235`; commit `75d449a` jest publiczny (gh API, 2026-10-10) |
| C2 | NInfer, RTX 5090: **510.7 t/s** verified | `cmvfhjc4t0177rf0137adcri2`, 2026-10-19 | **model nie jest bazowy:** QUASAR-QAT NVFP4 z innym stylem myślenia (outputSample) i PPL 4.375 vs 4.321; „artifact converted with a local fix”; commit `7d08406d` nieobecny na GitHubie; `decodeCeiling: null`; 5 runów 485–561. Te same oficjalne wagi: **334.4** (`cmvfgq0ng016zrf01jr8e8oh3`), code-v1 211.8 | **częściowo**: 334.4 to liczba dla Qwen3.8-27B; 510.7 dotyczy innego modelu (×1.32 mal z innego tekstu, ×1.15 z mniejszych wag: VRAM 23.1 vs 26.9 GB) | notes obu runów; `gh api …/commits/7d08406d` → 422 |
| C3 | „DFlash2 width 9 + reduced vocab” | notes C2 | kod: blok W=K+1, K=1..15 (`docs/maintainer/dflash.md:34-38`); head propozycji to **shortlista 131 072 tokenów wg częstości, Q4 g64 fp16, A16Only**, a target weryfikuje pełnym headem (`tools/convert/proposal.py:45-117`, `docs/weight-conversion.md:46-49`). Ta sama sesja: K=9 vs K=7 to 334.4 vs 323.0 (**+3.5%**) na oficjalnych wagach i 510.7 vs 458.9 (+11%) na QAT | **prawdziwe, ale mało warte**: słownik jak nasz 64k, a K=9 to kilka % | — |
| C4 | exllamav3 + DFlash2, 3090: **242.1 t/s** | `cmumr2ok90jn1lq01i5j6gwt1`, 2026-09-29 | EXL3 4.00 bpw (~14 GB), drzewo 8 wierszy (anchor + 7), krok ~25.0 ms, mal 6.04; **jedyny z tej czwórki z działającą kontrolą sufitu** (util 0.68); run 2: 228.9; KV 3-bit, ctx 262k; fork z 41 łatkami; zgłaszający gildrb nie jest zweryfikowany | **prawdziwe** dla klasy T=0 reasoning | `decodeCeiling.status = available` |
| C5 | tqLLM, 3090: **273.1 t/s** | R15c, `cmuspkbsg008erx01bvmv1y6l` | delta do R15c: README autora podaje „240–270” i „256 (mediana z 3)” dla tego promptu oraz **131–155 t/s na streszczeniach**; MTP depth 4 greedy 155 t/s przy 1.6K (prompt nieznany) | **prawdziwe dla klasy**, rekord z górnej części rozrzutu | `tqllm/README.md:218-236,388-390,227-228` |
| C6 | „mal 6–6.8 na tekście myślenia vs ~4 u nas z MTP” | R32d §4.1 | **ten sam prompt, T=0:** MTP K=4 4.04 (exl), 4.18 (llama.cpp MI210), 3.94–4.00 (vLLM Arc); **MTP K=7–8 5.54 / 5.68 (llama.cpp MI210), 5.93 (vLLM Arc)**, ale 4.37 (vLLM H200); DFlash2 K=3 3.67 vs MTP K=3 3.54 (upstream, 3090) | **prawdziwe, ale źle przypisane**: ~70% luki zamyka sama głębokość MTP 7–8; drafter daje +4% na głębokość, drzewo +5–7% | leaderboard verified (zapytanie 2026-10-20, 99 wierszy) |
| C7 | DFlash2 > MTP także przy T>0 | własny korpus NInfer (`docs/performance/qwen3.8-27b.md:111-145,178-183`), T=0.6 / top-k 20 / presence 1.0 (`methodology.md:25`) | NVFP4, C=1: korpus **207.9 vs 168.6 (+23%)**; długie AIME +24–56%; Code +39%; Translation +30%; Structured +63%; **Story 129.2 vs 132.6 (−3%)**. U NInfer DFlash2 przy T>0 ma prawdziwe q = softmax(E/T) po top-16 selektora i rejection `min(1, p/q)` (`dflash.md:190-239`) | **prawdziwe dla EN**, przy prozie zero; u nas brak PL w treningu draftera daje ×0.67 na pl-prozie (R16d) | — |
| C8 | Koszt kroku DFlash2 ≈ koszt MTP | NInfer, ta sama tabela | runda DFlash2 K=7 (AIME 15, 3.47 tok/rundę, 200.4 t/s) = **17.3 ms**; MTP3 (2.72 tok, 161.7 t/s) = **16.2 ms**; plain 13.5 ms. Czyli DF2 K=7 = **1.07× MTP3** i 1.28× plain | **prawdziwe u nich** (wszystko na urządzeniu, graf CUDA); u nas dziś 1.38× (3090, R16d) | wyliczone z t/s ÷ tok/rundę |
| C9 | (zastrzeżenie R32d) „ciepła mapa n-gramów zawyża” | R32d §3 | komendy wszystkich czterech runów nie mają lookupu; nonce w każdym żądaniu; drafter DFlash2 nie ma stanu między żądaniami; prefix cache NInfer jest włączony, ale nonce go unieważnia | **nie dotyczy** tych runów | `engineFlags.commandSnippet` |
| C10 | „Greedy output identyczny z plain” (NInfer, tqLLM, exl) | notes | nie weryfikowałem; tqLLM naprawił exactness dopiero `7d7382b` (10-13, R15c), a 273.1 to run z 10-03 | **niezweryfikowane** | — |

## 2. Porównanie jabłko do jabłka

Pod klasę `reasoning-v1`, T=0, thinking on, ~350 tokenów promptu, 320–512 tokenów wyjścia. „Nasz najbliższy pomiar” to najbliższa klasa, jaką faktycznie zmierzyliśmy. „Nasz szacunek” to mal 4.05 (MTP n=4 na tym prompcie wg C6) ÷ nasz zmierzony ms/krok `[INFERENCE]`.

| karta | ich wynik (warunki) | ms/krok, mal | nasz najbliższy pomiar | nasz ms/krok | **nasz szacunek na ich warunkach** | rozkład luki |
|---|---|---|---|---|---|---|
| 5060 Ti 16 GB | tqLLM 156.2 (TQ_S 12.55 GB, drzewo 8) | 39.9 · 6.23 | 62.6 t/s czat T=1 (3.05 tok/krok); decode po 512 tok **T=0: 74.0** (`31-5060ti.md:59-61`), IQ4_XS 14.25 GB | 48.8–49.3 | **~82** (80–85) | ×1.90 = ×1.24 krok (bajty 15.7 vs ~12.2 GB/krok) × ×1.54 mal |
| 3090 | tqLLM 273.1 (TQ3_4S 13.9 GB) | 22.5 · 6.15 | czat **T=0 103.4** (3.35 tok/krok), T=1 93.3; UD-Q4_K_XL 17.56 GB (`27-3090-final.md:20-21`) | 32.4 | **~125** (122–130) | ×2.18 = ×1.44 krok (~19.0 vs 13.9 GB/krok, my 63% / oni 66% pasma) × ×1.52 mal |
| 3090 | exllamav3 242.1 (EXL3 4.0 bpw ~14 GB, drzewo 8) | 25.0 · 6.04 | j.w. | 32.4 | ~125 | ×1.94 = ×1.30 krok × ×1.49 mal |
| 3090 | vLLM MTP 105.4 (W4A16, K=4) | — | j.w. | 32.4 | ~125 | **my szybsi o ~19%** `[INFERENCE]` |
| 3090 | llama.cpp upstream MTP n=3 80.4 / DFlash2 n=3 81.9 (Q4_K_XL) | 44.1 · 3.54 | U1 (upstream + MTP n=4): czat T=0 76.7 | 43.4 | — | zgodne z naszym U1 (+5% na korzyść ich promptu) |
| 5090 | NInfer 334.4 oficjalne NVFP4 (K=9); **510.7 = inny model (QAT)** | 15.5 · 5.17 (QAT 13.4 · 6.83) | **brak pomiaru na 5090** | — | — | NInfer MTP K=3 na tym samym prompcie przy 1024 tok: 164–185 vs DF2 K=7 246–309 (notes C2) |
| XTX | **brak verified** (R32d); R9700 hipfire 111.6 | 56.8 · 6.34 | long_ctx 1.7k T=0 **136.5** (sam MTP4, `REKORDY.md:107`) | 27.6 | **~147** (143–152) | na AMD prowadzimy (R32d) |

Uwagi do tabeli:
- Nasze `predicted_per_second`, tak jak u tqLLM i NInfer, jest liczone po stronie serwera. exllamav3 i CLI LocalMaxxing liczą po stronie klienta, więc wychodzi 5–15% mniej (R32d §3).
- Przy kroku nie da się jeszcze oddzielić „kwantu” od „silnika”. Na 5060 Ti czytamy 318 GB/s efektywnie (71%), tqLLM ~305 GB/s (68%). **Per bajt jesteśmy na parytecie albo lekko lepsi** (jak R15c dla plain). Narzut kroku spekulacji względem plain: u nas 1.27× (XTX), 1.30× (5060 Ti), 1.39× (3090), 1.52× (4060 Ti); tqLLM 3090 1.25×, NInfer 1.07–1.28×. Nadwyżka na 3090 to znany problem MMVQ Q6_K przy K=5120 (59% pasma, R31-3090).

## 3. Co jest w kodzie (delta)

### 3.1 NInfer: DFlash2
- **Jedno przejście na blok.** Wejście draftera to `[anchor, MASK×K]` w tych samych pozycjach absolutnych, z atencją nieprzyczynową. Zmiana W zmienia wszystkie propozycje (`dflash.md:84-130`).
- **Selektor.** Top-16 z headu propozycji, potem warunkowy marsz `E_i[p,c] = u_i[c] + Σ_r W_pred[pred,r]·g_i[r]·W_succ[C_i[c],r]` (rank 256). Przy T≤0 bierze argmax. **Przy T>0 losuje z q_i = softmax(E/T) i trzyma prawdziwe q do weryfikacji.** Target akceptuje z `min(1, p/q)`, a przy odrzuceniu losuje z reszty `max(p−q, 0)` (`dflash.md:173-239`).
  - **U nas** (`~/wt/cuda-topka2/common/speculative.cpp:1298-1325`) jest tylko argmax na CPU po kracie odczytanej z `h_nextn`, bez q. Przy T=1 akceptacja to więc p(d), a nie Σ min(p, q). Zgadza się to z `NOTES.md:156-158` (DFlash T=1 71.9 vs MTP 81.1).
- **Cechy targetu zostają na GPU.** Pending features materializują się leniwie przed następną propozycją (`dflash.md:258-270`), a pierścień KV draftera ma 40 MiB.
  - **U nas** dla każdego przyjętego tokenu idzie kopia 5 warstw × 5120 fp32 do hosta (`llama_get_embeddings_layer_inp`). Potem jest `memcpy` i osobny `llama_process` wstrzykujący (`speculative.cpp:1208-1238`), a po nim drugi `llama_process` na blok i odczyt kraty na CPU.
  - To trzy synchronizacje na krok. `[INFERENCE]` To one tłumaczą +17.5 ms/krok na 3090 (64 vs 46.5 ms, R16d), bo bajtowo drafter to tylko ~1.5 ms.
- **Kernele.** Commity z 2026-09-04…06 (`git log --all`): fused rmsnorm+rope, w8 attention/feature/SwiGLU dla zmiennej liczby kolumn, selektor kandydatów, materializacja kontekstu KV, równoległa akceptacja. Nic z tego nie dotyczy AMD ISA. Wniosek jest architektoniczny (wszystko w grafie, zero round-tripów), a nie kernelowy.
- **Pamięć.** DFlash2 K=7 dokłada 2.4 GiB do wag (18.98 → 21.38 GiB NVFP4: drafter Q8 + head propozycji) (`qwen3.8-27b.md:38-42`). U nas plik Q4_K_M to 1.06 GiB (`drafter-dflash.md`), w tqLLM TQ3 0.79 GB.

### 3.2 tqLLM
- **Szerokość:** „hybrid Qwen3.5/3.8 models verify at most 8 columns, so 7 is the effective maximum” (`README.md:306`). exllamav3 ma tak samo 8 wierszy. NInfer K=9 wychodzi poza ten limit i zyskuje +3.5%.
- **Dwustopniowy head weryfikacji:** head Q6_K zamieniony na int8 + skale fp16 per 16. Dekodowanie i weryfikacja czytają najpierw kopię 4-bitową (0.64 GB zamiast 1.27 GB int8), a potem przeliczają dokładnie top-16 z int8, nawet z pamięci hosta mapowanej do GPU (`src/qwen35.cpp:1530-1551,1778-1792`). Przy T>0 head zwraca top-16 z dokładnymi logitami, a rejection liczy host. Jest to aproksymacja rozkładu poza top-16.
- **Drzewo:** best-first po kracie kandydatów DFlash2 (notes C5), 8 węzłów. Drzewo nie kosztuje dodatkowych przejść draftera, bo kraty top-16 są za darmo. Dla hybrydy GDN potrzebne są kernele drzewa (R18: 10+ dni).
- **`--mtp-from N`:** długie prompty draftuje MTP, krótkie DFlash2 (`README.md:334`). To pośredni sygnał, że okno 2048 draftera przegrywa na długim kontekście. Zgadza się z NInfer: przy 1024 tok DF2 K=7 246–309, przy 512 tok 323.

## 4. Arytmetyka transferu: DFlash2 vs nasze MTP n=4

Model kosztu (`[INFERENCE]`, parametry ze źródeł):

| karta | krok MTP4 (zmierzony) | +1 poziom MTP | +1 wiersz weryfikacji | jedno przejście DF2 K=7 (1.14 GB + head 64k + wstrzyknięcie na GPU) | krok DF2 łańcuch K=7 | krok DF2 dziś (×1.38) |
|---|---|---|---|---|---|---|
| XTX | 27.6 ms (R24s) | 0.8 (0.65–0.9, R24q) | **0.85** (R24s; 9. wiersz 1.37) | ~2.5 | **29.5** (+7%) | 38.1 |
| 3090 | 32.4 (R27) | ~0.8 | ~1.5 (= (32.4−23.3−3.2)/4) | ~2.6 | **36.2** (+12%) | 44.7 |
| 5060 Ti | 49.3 (R31) | 1.1 (R31 §profil) | 1.5 (+6.0 ms dla n=1→5; kwanty „i”) | ~4.1 | **53.5** (+9%) | 68.0 |

**Klasa reasoning-v1, T=0** (mal: MTP4 4.05, MTP7 5.5 [5.0–5.9], DF2 łańcuch K=7 5.7 [5.2–6.0], DF2 drzewo 8 6.1; drzewo +1–1.5 ms):

| karta | MTP n=4 (dziś) | **MTP n=7** | DF2 łańcuch K=7, ścieżka dzisiejsza | **DF2 łańcuch K=7 na GPU** | DF2 drzewo 8 |
|---|---|---|---|---|---|
| XTX | 147 | **169 (+15%)** [154–181] | 150 (+2%) | **194 (+32%)** [177–204] | 200 (+37%) |
| 3090 | 125 | **140 (+12%)** [127–150] | 127 (+2%) | **157 (+26%)** [143–166] | 164 (+31%) |
| 5060 Ti | 82 | **96 (+17%)** [88–103] | 84 (+2%) | **107 (+30%)** [97–112] | 111 (+35%) |

**Nasz czat T=1 (spec_sweep, 6 promptów PL/EN):** stosunki tok/krok DF2/MTP4 przyjąłem z NInfer T=0.6 (przeliczone z MTP3 na MTP4, ÷1.06) i z Magnitude (R16d):
- pl-proza 0.67, en-chat 0.95, en-code 1.37, pl-tech 0.9, en-tech 1.2, pl-kod 1.35;
- średnia harmoniczna 1.007, a krok jest droższy o 7–12%;
- **wynik netto: −6% (XTX), −10% (3090), −7% (5060 Ti)**;
- router z wyrocznią (DF2 tylko tam, gdzie wygrywa) daje +8–10%, ale potrzebuje obu drafterów w VRAM;
- **na 5060 Ti przy 32k zostaje 472 MiB zapasu**, a drafter ma 1.06 GiB, więc się nie zmieści bez cięcia kontekstu.

**Czy to się składa z tym, co mamy:**
- **GPU verify (`LLAMA_GPU_VERIFY=1`):** tak, dla łańcucha (ta sama weryfikacja łańcucha K tokenów). Dla drzewa potrzebny jest nowy kernel akceptacji po ojcach.
- **Sprzężone próbkowanie (`LLAMA_SPEC_COUPLED`):** w zasadzie tak. Gumbel-max po top-16 selektora z szumem kluczowanym (seed, pozycja, id tokenu), tym samym co u targetu, zamiast losowania z q. To daje sprzężenie jak przy MTP (+3.7–4.2% tok/krok, R24p) `[INFERENCE]`. Dzisiejszy argmax po kracie tego nie umożliwia.
- **Lookup W16:** tak. tqLLM ma `--lookup`, które dzieli budżet weryfikacji. Przy limicie 8 wierszy ogon lookupu i blok DF2 konkurują o miejsce, a na edycji kodu i tak wygrywa lookup (R24j).
- **Bramka md5 (GPU verify off/on przy stałej szerokości):** stała głębokość n=7 i stałe K=7 ją spełniają. Zmienna szerokość nie (R24q pkt 2).

**Odpowiedź na pytanie z zadania:**
- przy T=0 (reasoning/kod EN) drafter klasy DFlash2 bije MTP n=4 o +26–32%, ale **tylko z draftem całkowicie na GPU**. Z dzisiejszą ścieżką llama.cpp wychodzi ~+2%;
- połowę tego zysku (+12–17%) daje samo MTP n=7 bez kodu;
- przy T=1 na naszym zestawie PL/EN DFlash2 przegrywa (−6…−10%).

## 5. Co przejąć (ranking)

| # | pomysł | zysk | nakład | ryzyko / uwagi |
|---|---|---|---|---|
| 1 | **Profil głębokości MTP n=6–7 dla klasy T=0/reasoning** (stała głębokość per klasa, ≤ 8 wierszy) | +12–17% t/s na reasoning-v1 T=0 `[INFERENCE]`; 0 na czacie T=1 | 0 kodu (`--spec-draft-n-max 7`), 0.5 dnia na profil w `run-topka.sh` / Podkręcie | n=8 wypada z MMVQ 2–8 (`NOTES.md:143`). Nadaje się do runów verified z R32d E1 |
| 2 | **Dwustopniowy head weryfikacji** (4-bit po całym słowniku + dokładne przeliczenie top-16/32 oryginalnym Q6_K) | **+1.4–1.9% na wszystkich klasach i kartach** (−~0.35 GB/krok: XTX −0.4 ms, 3090 −0.46, 5060 Ti −0.9) `[INFERENCE]` | 1–2 dni (nowy op: przybliżony head + top-K + gather/rescore), HIP i CUDA | argmax inny tylko, gdy prawdziwy top-1 wypada z 4-bit top-16. Przy T=1 przeliczać ≥ top-k samplera (20). VRAM +0.7 GB na kopię 4-bit, chyba że oryginał zastąpi int8 jak w tqLLM |
| 3 | **DFlash2 na urządzeniu** (cechy w grafie bez D2H, krata i wybór ścieżki na GPU, q przy T>0 albo Gumbel ze sprzężeniem), łańcuch K=7 | +26–32% na T=0 kod/reasoning EN; **−6…−10% na naszym czacie T=1** → tylko jako tryb dla klasy (router) | 3–5 dni; +0.8–1.1 GB VRAM (nie dla 5060 Ti przy 32k) | drafter bez PL (R16d). Najpierw E2 |
| 4 | Drzewo 8 węzłów z kraty DF2 | +4–5% nad łańcuchem DF2 | 10+ dni (kernele drzewa GDN, R18) | odłożyć; wymaga #3 |
| 5 | Mniejsze kwanty jako jawny wybór (TQ-podobne 12.5–14.5 GB) | krok ×1.24–1.37 na 3090 | 0 (katalog już ma IQ4_XS / Q3_K_XL) | KLD: TQ_S 0.055 vs UD-Q4_K_XL 0.012. W porównaniach normalizować per bajt |
| — | Zredukowany słownik draftu | 0 | — | **już mamy** (64k + iq4_xs) |
| — | K=9 | ≤ +3.5% u NInfer; u nas ujemne | — | 9. wiersz +1.37 ms na XTX, CUDA MMVQ ≤ 8 kolumn |

## 6. Eksperymenty ≤ 10 min (GPU uruchamia Main; ja nie mam GPU)

| # | eksperyment | przełączniki | czas | kryterium |
|---|---|---|---|---|
| E1 | XTX, `reasoning-v1` T=0 thinking on, **świeży serwer**, MTP n=4 / 5 / 6 / 7, po 3 nonce | `run-topka.sh qwen` + `LLAMA_SPEC_LOOKUP=0`, `--spec-draft-n-max {4..7}`, skrypt `lmx_submit.py` z R32d §6 (tylko pomiar, bez wysyłki) | 8 min | mal i ms/krok z `timings`. **n=7 ≥ +8% t/s vs n=4 → profil „reasoning T=0” (#1)**. Przy okazji powstaje kandydat na verified z R32d E1 |
| E2 | XTX, ten sam prompt, **DFlash2 n=7 dzisiejszą ścieżką** vs MTP4 | `run-llm.sh qwen dflash` (`--spec-draft-n-max 7`) | 6 min | prawdziwe mal_DF2 i narzut kroku na naszym buildzie. **mal_DF2 ÷ mal_MTP4 ≥ 1.35 i narzut ≥ +25% → uzasadnia #3**. Jeśli mal < 1.25×, #3 skreślić |
| E3 | XTX `test-backend-ops -o MUL_MAT perf`: head 248320×5120 Q6_K vs Q4_0 vs IQ4_XS przy n=1 i n=5 | — | 3 min | Δms × kroki. **≥ 0.35 ms/krok przy n=5 → implementować #2**, inaczej skreślić |
| E4 (przy najbliższej kampanii NVIDIA) | 3090 / 5060 Ti: E1 + E2 tym samym skryptem | cuda-topka2 `2a261101b` | 5 min na kartę | 3090: n=7 ≥ 135 t/s (cel z §4). 5060 Ti: n=7 ≥ 92 t/s. DF2: tylko na 3090, bo na 5060 Ti nie mieści się w VRAM przy 32k |
| E5 (CPU, 0 GPU) | offline: per-głębokość akceptacja warunkowa MTP na tekście myślenia z E1 (lustro `mtp_torch.py`, jak R24s) | `24s-drzewa/tree_extract.py` na odpowiedzi greedy z E1 | ~30 min CPU | przewiduje n=6 vs 7 bez GPU; uzasadnia limit 8 wierszy |

## Do bazy wiedzy

Proponowane wiersze `wiki/ZRODLA.md`:

| źródło | wersja / commit | data | raport | werdykt | następnym razem |
|---|---|---|---|---|---|
| NInfer (github.com/Neroued/ninfer) | `dev` @ `a928f899` (master `64d10fbf`), 3 105★, Apache-2.0; run 5090 z nieopublikowanego `7d08406d` | 2026-10-20 | R32f | 5090 NVFP4: oficjalne wagi 334.4 t/s (K=9, mal 5.17, 15.5 ms/krok); **510.7 to QAT QUASAR, inny styl myślenia**. DF2 przy T>0 ma prawdziwe q i rejection; cechy i krata na GPU; runda DF2 K=7 = 1.07× MTP3. Korpus T=0.6: DF2 +23%, Story −3%. Shortlista 131k Q4 = nasz 64k | czy wyjdzie build dla RTX 30/40 albo ROCm (dziś tylko sm_120a/121a); nowe wiersze `docs/performance/qwen3.8-27b.md` |
| tqLLM (github.com/turbo-tan/tqllm) **5×** | `d617986` (publiczny 1.0.0+), run 5060 Ti `75d449a` (publiczny) | 2026-10-20 | R15b, R15c, R15f, R23e, R32f | 5060 Ti 156.2 (TQ_S 12.55 GB, KLD 0.055, T=0) to klasa reasoning; ich README: 77–95 na streszczeniach. **Dwustopniowy head weryfikacji** (4-bit + int8 rescore top-16, `qwen35.cpp:1548-1551`) do przejęcia. Limit 8 kolumn na hybrydzie | czy publiczny build odtwarza 273/156; MTP depth 4 155 t/s na 3090 – na jakim prompcie? |
| exllamav3 fork r0b0tlab (DFlash2 + 41 łatek) | `355c6ee` + łatki | 2026-09-29 | R32f | 3090 242.1 verified, jedyny z działającą kontrolą sufitu (util 0.68), drzewo 8, ~25 ms/krok | czy łatki drzewa trafią do upstream exllamav3 |
| QUASAR-QAT/Qwen3.8-27B-QUASAR-NVFP4 (HF) | — | 2026-10-19 | R32f | checkpoint QAT zmienia styl myślenia (bardziej przewidywalny tekst: mal 6.83 vs 5.17), PPL 4.375 vs 4.321. **Nie porównywać z Qwen3.8-27B** | KLD wobec BF16 |
| LocalMaxxing (localmaxxing.com) **5×** | API 1.7.0 | 2026-10-20 | R04, R06, R15b, R15c, R32d, R32f | na `reasoning-v1` T=0 MTP K=7–8 ma mal 5.5–5.9, a DF2 K=3 ≈ MTP K=3 +4%: **przewaga DF2 to głównie głębokość** | verified XTX z E1 |

Proponowany wpis do `wiki/lekcje/`: **„Rekord T=0 na tekście myślenia ≠ czat T=1”**. Ta sama para karta/model daje 77–95 (streszczenia) i 156 t/s (reasoning-v1) w jednym silniku (tqLLM 5060 Ti). Liczby z LocalMaxxing porównywać tylko z naszym pomiarem na tym samym kanonicznym prompcie i przy tym samym T.

## Źródła

- LocalMaxxing API (GET, 2026-10-20): `/api/leaderboard?hfId=Qwen3.8-27B&verifiedRun=true&limit=100`, `/api/leaderboard?engineName=ninfer&limit=100` (`/tmp/res32f/lmx/`). Runy: `cmvfhjc4t0177rf0137adcri2`, `cmvfgq0ng016zrf01jr8e8oh3`, `cmvfgrfj30172rf01eftylc1b`, `cmvfhkqm4017arf01f5n9y82q`, `cmv2vel9u00jnmr011nbtgqet`, `cmv2velwc00jqmr01qffc4j23`, `cmumr2ok90jn1lq01i5j6gwt1`, `cmuspkbsg008erx01bvmv1y6l`, `cmtmo9qv2000mlt01mrrhog30`, `cmtmo9u6p000vlt01sjmhhfm9`, `cmudefavb0awelq010gc9r5lw`, `cmu7s0k6k08jilq01kndf3eyg`, `cmu7rdk9508jblq015lqby9om`, `cmv9l58ei00wmle01or2l2v41`, `cmtrfjhhv00dcpa013a8uyn0j`
- https://github.com/Neroued/ninfer @ `a928f899`: `README.md` (tabele wydajności), `docs/performance/qwen3.8-27b.md:12-17,38-42,57-64,111-145,178-183`, `docs/performance/methodology.md:20-35`, `docs/maintainer/dflash.md:34-38,84-130,173-270`, `docs/weight-conversion.md:46-49`, `tools/convert/proposal.py:45-117`, `git log --all` (commity DFlash2 2026-09-04…06); `gh api repos/Neroued/ninfer/commits/7d08406d…` → 422
- https://github.com/turbo-tan/tqllm @ `d617986`: `README.md:186-236,300-310,334,373-390`, `CHANGELOG.md` (1.0.0, Unreleased), `src/qwen35.cpp:1514-1551,1770-1792`; `gh api repos/turbo-tan/tqllm/commits/75d449a` (2026-10-10)
- Nasze: `~/wt/cuda-topka2/common/speculative.cpp:1208-1238,1298-1325` (`2a261101b`); `product/research/31-5060ti.md:59-99`, `27-3090-final.md:16-66`, `24s-proza-drzewa.md:10-16,47-52,80-85`, `24q-adaptacyjna-spekulacja.md:11-25,44`, `16d-magnitude-vs-nasz.md:14,135`, `32d-localmaxxing.md:84-101`; `qwen-opt/NOTES.md:139-160`; `wiki/REKORDY.md:107`; `wiki/modele/drafter-dflash.md`; `wiki/lekcje/lekcja-drafter-gleboki-vs-mtp.md`; KLD z `wiki` (raport 15e: UD-Q4_K_XL 0.0122, UD-Q3_K_XL 0.0337)
