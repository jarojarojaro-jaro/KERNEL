# 60b. Silniki Apple (oMLX 0.7.2, Locals), konkurs Bonsai 2 9B (cuda.fast / mlx.fast), Flapping Airplanes, blog o CUDA

Data: 2026-10-24. Autor: podagent ResAppleEngines. Tylko CPU, bez GPU, bez pobierania wag.

Źródła, które przeczytałem:
- **oMLX:** notatki wydania 0.7.2 i repo `jundot/omlx` (klon `~/qwen-opt/research/omlx`, `c4bb311e`, 2026-10-24): commit wprowadzający Lightning MTP, `batch_policy.py`, `qwen35_model.py`, konfiguracja DeepSeek V4.1, `docs/`.
- **Locals:** `Generated-Computers/Locals` (klon `c0f9baa`, 2026-10-24): README, `docs/why-faster`, `docs/runtime`, `gdn_kernel.py`; abstrakt arXiv 2610.09139.
- **Konkurs:** oba repozytoria konkursowe, `Layr-Labs/cudafast-bonsai2-9b-engine` (`759629b`) i `Layr-Labs/mlxfast-bonsai2-9b-engine` (`8cee3ef`). Opisy wszystkich PR pobrałem przez `gh pr list` (237 + 659 PR, kopia robocza w `/tmp/bonsai/`). Czytałem tablice wyników na yukon.org.
- **Pozostałe:** strona flappingairplanes.com (tekst wyciągnięty z bundla JS) i TechCrunch o rundzie; blog thelastone07.

Oznaczenia: `[INFERENCE]` = mój wniosek lub szacunek, `[niezweryfikowane]` = nie znalazłem tego u źródła.

## TL;DR

1. **Najcenniejszy jest konkurs Bonsai 2 9B, a w nim tor CUDA, bo to llama.cpp (fork PrismML) z weryfikacją DFlash2 na 16 wierszach, czyli nasza architektura.** Wynik na DGX Spark: decode **85.9 → 576.7 tok/s**, 10.3 tok/rundę. Prawie każda zmiana jest bitowo dokładna i ma w PR pełny opis z pomiarem.
   - Około połowę zysku dała sama spekulacja: deklaracja DFlash2 przy głębokości 15 to +117% (davidtai).
   - Resztę dały kernele i scheduling.
   - Seria ArthurOstapenko z 17.10 podniosła rekord ze 150.6% do **316.2%** (decode **284.3 → 513.4 tok/s**).
2. **Większość technik zwycięzców już mamy:**
   - leniwe cofanie GDN przez przeliczenie (u nas S4, [[gdn-replay]]);
   - fuzja norma + q8_1;
   - wskazówki cache na wagach (`glc dlc`);
   - słownik draftu 64k i głowica draftu IQ4_XS;
   - wielokolumnowe MMVQ;
   - adaptacyjna głębokość (zbadana, zmienia md5).

   Konkurs niezależnie potwierdza, że ta ścieżka jest właściwa. Nie wnosi jednak dużego, nieznanego nam zysku dla Qwen3.8-27B na XTX.
3. **Nowe i tanie do sprawdzenia (szacunki dla nas, każdy ≤ +2%):**
   - (a) **sito głowicy draftu**: pół K na całym słowniku draftu, potem dokładne przeliczenie 128 kandydatów (spariev);
   - (b) **taśma delt GDN**: weryfikacja zapisuje `delta` i `g`, więc przeliczenie zatwierdzonych wierszy nie liczy już iloczynów k·S;
   - (c) **polityka L2 `evict_first` na strumieniu wag** na 3090 (sm_80+): +3.3% na GB10;
   - (d) **audyt „sufitu wzorca” i układu wag kafelkami** (R18 #12): na GB10 ciągły strumień dał 230–236 GB/s wobec 200–210.
4. **Drzewo 15 węzłów w tej samej 16-wierszowej weryfikacji (kaankolcu) to najciekawsza nowość algorytmiczna.**
   - Daje 122 → 113 rund (−7.4%) przy tych samych 16 wierszach.
   - Gałęzie GDN restartują od zapisanego stanu pośredniego, a temperatura drzewa jest dobierana per blok.
   - U nas opłaca się dopiero na ścieżce DFlash2 W16, która po polsku przegrywa z MTP (57e). Wymaga kernela drzewa GDN. Niski priorytet.
5. **oMLX:**
   - **Lightning MTP** to natywne MTP głębokości k: łańcuch draft/verify, jedna synchronizacja hosta na cykl, adaptacyjna głębokość z mierzonych kosztów (z parkowaniem MTP, gdy przegrywa), osobne kernele qmm pod kształt weryfikacji.
   - **CED** to *Causal Encoder-Decoder* DeepSeek V4.1: w prefillu połowa dekodera liczy tylko ogon okna.
   - Oba nie dotyczą Qwen3.8-27B na llama.cpp.
6. **Locals:**
   - Przełom w złożoności dotyczy **automatów gramatyki** (osiągalność w grafach o niewielu ścieżkach w O(log² n / log log n) pamięci), **a nie DeltaNet**.
   - Po stronie GDN jest tylko jeden kernel Metal na krok dekodu (konwolucja + norma + rekurencja + gated norm) wart 1–2%. My mamy odpowiednik w HIP od dawna. Na nasze kernele GDN nic tu nie przenosi.
7. **Flapping Airplanes** to laboratorium efektywności AI (Ben i Asher Spector, Aidan Smith; seed $180M, seria A $1B). Na stronie chwali się „najpełniejszym frameworkiem megakerneli”. Kodu publicznego brak. Dla nas to sygnał rynkowy, nie technika.
8. **Blog „Making CUDA less overwhelming”** to wstęp do H100/CUDA dla początkujących. Dla nas nic nowego.

## 1. Co to jest

| element | czym jest |
|---|---|
| oMLX 0.7.2 | Serwer LLM na Apple Silicon (MLX), aplikacja w pasku menu, ciągłe batchowanie, cache prefiksu RAM + SSD, klaster Maców. Wydanie 2026-10-21 ([release](https://github.com/jundot/omlx/releases/tag/v0.7.2)). |
| Lightning MTP | Nazwa oMLX dla natywnego, wielotokenowego dekodowania spekulacyjnego głowicą MTP checkpointu. Do 2026-07-12 nazywało się „Native MTP” (commit `56f08fdb`). |
| CED | *Causal Encoder-Decoder*, cecha architektury DeepSeek-V4.1-Flash ([arXiv 2609.19969](https://arxiv.org/abs/2609.19969)). oMLX ma przełącznik `deepseek_v41_ced_prefill_enabled`. |
| oQ | Własne kwanty oMLX (oQ2e…oQ4e, MXFP). `-mtp` w nazwie oznacza zachowaną głowicę MTP (`docs/oQ_Quantization.md:86`). |
| Splash 1.4.0 | Zewnętrzny silnik (incoai) podpinany do oMLX. Uruchamia GGUF Qwen3.8-Flash-Next z draftem DFlash2 `incoai/Qwen3.8-Flash-Next-DFlash2` i strumieniuje ekspertów z SSD. |
| Locals | Serwer MLX „dla agentów”: małe batche 2–16, gramatyka i wywołania narzędzi na GPU, cache rozmów ([repo](https://github.com/Generated-Computers/Locals), Apache-2.0). |
| cuda.fast / mlx.fast (Bonsai 2 9B) | Tygodniowy konkurs Yukon (Layr Labs) z PrismML: przyspieszyć pojedynczy strumień Ternary Bonsai 2 9B. CUDA na DGX Spark (llama.cpp PrismML), MLX na M5 Max (mlx-swift). Zamknięty 2026-10-22. |
| Flapping Airplanes | Laboratorium badawcze „efektywności AI” z San Francisco. |
| thelastone07 blog | Wpis z 2026-10-20: wprowadzenie do sprzętu H100 i pisania kerneli CUDA. |

## 2. Kto / skąd

- **oMLX:** Jun Kim (`jundot`), Korea. Kernele qmm pod kształt weryfikacji wzięte z MTPLX (Youssof Altoukhi, Apache-2.0; commit `8a9b1972`).
- **Locals:** Generated Computers. Praca: Arip Asadulaev, „Breaking the Space Barrier and its Application to Language Model Inference” ([arXiv 2610.09139](https://arxiv.org/abs/2610.09139), 2026-10-06, cs.CC).
- **Konkurs:**
  - Organizacja: David Tai (Layr Labs / Yukon), partner PrismML. Ogłoszenie wyników: Kydo (`@0xkydo`, [X](https://x.com/0xkydo/status/2113382850687009185)). Nazwy zmiennych `DARKBLOOM_BONSAI_*` wskazują na serwowanie w Darkbloom.ai `[INFERENCE]`.
  - Zwycięzcy: **dadon** (CUDA, 421.5%) i **kaankolcu** (MLX, 471%).
  - Kluczowi autorzy technik: ArthurOstapenko (CUDA i MLX), newjordan, spariev, GordoAR, pratikgx, pepedesigner, sambitcreate.
  - Niemal każde zgłoszenie deklaruje, że pisały je agenty: Claude Opus 5.5 w Claude Code albo GPT-6.1 Sol w Codex, często kilka instancji pod koordynatorem.
- **Flapping Airplanes:** założyciele Aidan Smith (Thiel fellow, wcześniej Neuralink), Asher Spector (PhD statystyka, Stanford) i Ben Spector (PhD CS Stanford, założyciel Prod). Seria A $1B przy wycenie ~$6B, współprowadzona przez Index i Lux ([TechCrunch, 2026-10-21](https://techcrunch.com/2026/10/21/year-old-ai-lab-flapping-airplanes-raises-1b-at-a-6b-valuation/)). Powiązanie Bena Spectora z megakernelami Hazy (ThunderKittens) to mój wniosek z nazwiska i opisu `[niezweryfikowane]`.
- **Blog:** autor „thelastone07”, twórca produktu tryvirgil.org.

## 3. Jak działa technicznie

### 3.1 oMLX: Lightning MTP

Źródło: commit `8a9b1972` (#2113, 2026-07-08) i `omlx/patches/mlx_lm_mtp/`, łącznie 12 072 linie.

- **Łańcuch głębokości k.** Głowica MTP draftuje k tokenów łańcuchowo, potem jedna weryfikacja celu. Jest jedna synchronizacja hosta na cykl.
- **„Sharp draft sampler”.** Akceptacja stochastyczna zachowuje rozkład celu. Przy samplerach celu typu temp 0.6 rozkład draftu jest ostrzejszy niż rozkład celu (`batch_generator.py:907`).
- **Adaptacyjna głębokość z pomiaru** (`batch_policy.py`).
  - Polityka należy do kohorty żądań, nie do modelu.
  - Koszt to zmierzony czas całego wywołania batcha. Bazą jest zwykły dekod mierzony osobno.
  - Akceptacja jest liczona per pozycja prefiksu.
  - Gdy MTP cztery razy z rzędu daje < 0.9 oczekiwanych tokenów/ms zwykłego dekodu, polityka „parkuje” MTP (cooldown 128).
- **Cofanie GDN (Qwen3.5/3.6).** Prefiks potwierdzony i sufiks draftu idą jako dwa kawałki. Między nimi zapisywany jest snapshot `(conv_state, ssm_state)`. Przy odrzuceniu `mtp_partial_rollback` odtwarza snapshot i przelicza zachowany prefiks (`qwen35_model.py:237-337, 642-685`). Wariant DFlash robi „GDN state replay” (`docs/experimental/dflash_mlx_integration.md:43`).
- **Wyniki z commitu** (M3 Ultra, greedy): Qwen3.6-27B 42.8 → 55.1 tok/s, Qwen3.6-35B-A3B 85.2 → 140.4 tok/s.
- **0.7.2 dodaje:**
  - Lightning MTP przy podziale PP/TP między Macami (#4732). Synchronizację robi `cluster/mtp_sync.py`.
  - Współdzielenie pracy w weryfikacji między sprawdzanymi tokenami (#4722).

### 3.2 oMLX: CED, SpecPrefill, cache dla Claude Code

- **CED.** W DeepSeek-V4.1-Flash dekoder (warstwy po połowie) bierze globalne KV z rzutu końcowego stanu enkodera, liczonego w warstwie środkowej CSA2.
  - W prefillu pół dekodera może więc przejść tylko ostatnie `window_size` tokenów (`patches/deepseek_v41/config.py:103-106, 255-271`).
  - Warunki: parzysta liczba warstw, warstwa środkowa jest źródłem KV i indeksera, kompresja 1 w całej połowie dekodera.
  - Praca DeepSeek: 8B aktywnych parametrów na token w prefillu wobec 16B w dekodzie ([arXiv 2609.19969](https://arxiv.org/abs/2609.19969)).
  - Nasze modele nie mają tej architektury.
- **SpecPrefill.** Rzadki prefill: mały model wybiera ważne tokeny promptu, cel prefilluje tylko je. To podejście stratne. W 0.7.2 są poprawki RoPE przy żądaniach dekodujących obok i podwójnego ostatniego tokenu w modelach z oknem przesuwnym (#4688).
- **Claude Code (#4712).** Notatki, które Claude Code dokleja po wyniku narzędzia (hook context, reguły, przypomnienia), zostają na miejscu. Wcześniej były przenoszone do początkowego bloku system, co zmieniało prefiks i wymuszało pełny prefill rozmowy w każdej turze.
  - Sprawdziłem `tools/server/server-chat.cpp:348-545` w topce: llama-server niczego nie przenosi do system, a nagłówek `x-anthropic-billing-header` normalizuje już dla cache (`:312-346`), więc prefiks jest stabilny.
  - Przestawia jednak kolejność: tekst z wiadomości `user` trafia **przed** wiadomości `tool` z tej samej tury (`:524-542`). To kwestia poprawności szablonu, nie szybkości `[INFERENCE]`.

### 3.3 Locals: co naprawdę jest „przełomem”

- **Złożoność dotyczy gramatyki.**
  - Automat wymuszający format JSON lub wywołanie narzędzia ma tę własność, że z każdego stanu każdy token prowadzi jedną ścieżką.
  - Praca dowodzi, że osiągalność w grafach o niewielu ścieżkach (z weryfikacją tej własności) mieści się w ReachUL, LOGDCFL, C=L i SC² i wymaga O(log² n / log log n) pamięci, poniżej granicy Savitcha ([abstrakt](https://arxiv.org/abs/2610.09139)).
- **W silniku daje to:**
  - tokeny wymuszone przez format są wypisywane bez modelu;
  - maska jest liczona na GPU bez tabel (3 MB zamiast do 1.5 GB);
  - mały stos dla formatów rekurencyjnych;
  - niezależne pola są dekodowane równolegle.
- **DeltaNet: żadnego nowego algorytmu.** `gdn_kernel.py` to jeden kernel Metal na krok dekodu (S ≤ 16):
  - konwolucja + SiLU, RMS norm q/k, rekurencja delta-rule (16 wierszy stanu na simdgroup), gated RMS norm;
  - wariant `states=True` zapisuje stan po każdym tokenie do cofania draftu;
  - ograniczenie do `Dk == Dv == 128` (`docs/runtime/README.md:107-127`).
  
  Zysk według ich ablacji wynosi **1–2%** (`docs/why-faster/README.md:103-108`).
- **Skąd naprawdę są 3×** (M2 Pro, Qwen3.5-4B, 8 żądań; `why-faster:31-41`):
  - kernele 4-bit matmul pod 2–16 wierszy (bez nich 272.7 → 119.2 tok/s);
  - fp16 zamiast bf16 na M1/M2 (bez tego 97.9);
  - fuzja projekcji (246.8);
  - pipelining CPU/GPU (236.5).
- **„Where Locals is not faster”** (README:175-188):
  - jedno żądanie bez nic do ponownego użycia (64 vs 61 tok/s);
  - praca ograniczona promptem (8 × 8k prompt: 57 tok/s);
  - formaty spoza strojonych kerneli, tylko affine 4-bit g64 (mxfp4 = prędkość mlx-lm);
  - M5 z akceleratorami neuronowymi (1.5× zamiast 3×).

### 3.4 Konkurs Bonsai 2 9B: zasady

- **Model:** Ternary Bonsai 2 9B, geometria Qwen3.5-9B: 24 warstwy GDN + 8 pełnej uwagi, hidden 4096, PQ2_0 z Hadamardem, jedna warstwa MTP w Q8_0. Drafter DFlash2 w Q8_0.
- **Wynik:** `prefill_gain^0.25 × decode_gain^0.75` względem referencji na tej samej maszynie, pojedynczy strumień.
- **Tolerancja:** ≤ 40 rozbieżności na 1000 tokenów, każda musi być drugim wyborem referencji przy względnej luce ≤ 0.01. Prompty są ukryte i rotowane, ranking końcowy na odłożonej puli ([README CUDA](https://github.com/Layr-Labs/cudafast-bonsai2-9b-engine)).
- **Sprzęt:**
  - CUDA: DGX Spark (GB10, sm_121, CUDA 13.0); edytowalne `llama.cpp/`, `harness/` i deklaracja spekulacji (MTP 1–6 albo DFlash 1–15).
  - MLX: cztery M5 Max 128 GB (`mlxfast…/README.md:544`).
- **Tablice końcowe:**

| tor | decode ref → rekord | prefill | tok/rundę | lider | źródło |
|---|---|---|---|---|---|
| CUDA | 85.9 → 576.7 tok/s (+421.5%) | 6852.6 tok/s | 10.3 | dadon | [cudafast?benchmark=bonsai2-9b](https://www.yukon.org/cudafast?benchmark=bonsai2-9b&platform=cuda) |
| MLX | 144.8 → 959.6 tok/s (+471%) | 6851.6 tok/s | 9.5 | kaankolcu | [mlxfast?benchmark=bonsai2-9b](https://www.yukon.org/mlxfast?benchmark=bonsai2-9b&platform=mlx) |

### 3.5 Tor CUDA (llama.cpp): techniki ArthurOstapenko i reszty

Wszystkie poniższe zmiany są bitowo dokładne, chyba że zaznaczono inaczej. Pomiary to pary lokalne na GB10, w nawiasie numer PR.

**A. Leniwe cofanie GDN (#9, `729988a7`).**
- Stan bazy:
  - weryfikacja 16 tokenów zapisywała pełny stan (32 głowy × 128 × 128 × 4 B = 2 MiB) po **każdym** tokenie, czyli 32 MiB na warstwę na rundę;
  - następny ubatch czytał 1 z 16 slotów;
  - Nsight: **34.6 MB zapisów** na wywołanie.
- Zmiana:
  - writer zapisuje stan końcowy (slot 0), stan na początku okna (slot 1) i rekord na blok: k, v, aktywowane g i beta dla tokenów okna, magic, W, hash bazy;
  - reader, gdy rollback wskazuje slot r ≥ 1 i rekord się zgadza, przelicza `W − r` tokenów tymi samymi wyrażeniami (`kv += s·k`, `delta = (v − g·kv)·beta`, `s = g·s + k·delta`);
  - razem ~4.5 MiB zamiast 32 MiB.
- Wynik: GDN w dekodzie **129.5 → 36.4 ms** na 888 wywołań, decode **+7.5–8.3%**.
- **U nas to już jest:** S4 / `GATED_DELTA_NET_LAG`, 720 MiB zapisów mniej na weryfikację ([[gdn-replay]]).

**B. Seria 11 zmian (#74, `2dad498a`)** na bazie #73 (`21706133`: kernel GDN pod 8–16 tokenów `gated_delta_net_l8v`, fuzja wyjścia GDN, front-end konwolucji GDN, scalony K/V inject draftera, staged uploads, stabilny cache grafów CUDA).

| # | zmiana | zmierzony zysk |
|---|---|---|
| 1 | Konwolucja blokowa draftera DFlash2 jako jeden op `GGML_OP_DFLASH2_CONV` (~168 kerneli → 24 na rundę, 12 dodawań residualnych mniej) | decode ×1.0218 |
| 2 | RMSNorm q/k + multi-section RoPE + zapis K/V cache w jednym kernelu (2 launche zamiast 6 na warstwę); bramka sigmoid uwagi wewnątrz kwantyzacji FWHT `wo` | ×1.0030 (szum) |
| 3 | Granica warstwy weryfikacji (ADD + RMSNorm + waga + znaki + Hadamard 4096 + kwantyzacja q8) jako jeden kernel dla ≤ 16 wierszy | ×1.0103 |
| 4 | Glue GDN: alpha/beta jednym klastrowym launchem; front-end conv sam zbiera wiersz stanu i składa L2 q/k; **brak zapisu stanu końcowego w leniwej weryfikacji** (flaga `GDN_LAZY_NOFINAL`, następny ubatch przelicza okno od slotu 1); zerowanie świeżej komórki przy ładowaniu; prefill GDN z `cp.async` | prefill ×1.0408, decode ×1.0143 |
| 5 | **„Bulk-copy ring”**: matmul J=16 na układzie wag dekodu; jeden wątek strumieniuje kroki (wagi + q8_1 aktywacji) przez `cp.async.bulk` (TMA) do pierścienia S etapów w SMEM, mbarrier na etap | Q8 ×1.0068, + PTQ1 ×1.0087 |
| 6 | Prefill 2-bit stream-k: kafel aktywacji jedną kopią bulk na blok K, skale transponowane w SMEM | (prefill) |
| 7 | Czyszczenie pamięci między żądaniami tylko w zakresach zapisanych przez poprzednie żądanie | (każde żądanie) |
| 8 | Dwa koszty pierwszego użycia usunięte (liczba slotów grafu draftera raz, stan schedulera rezerwowany przy starcie) | (każde żądanie) |
| 9 | **L2 `evict_first`** na kopiach wag w pierścieniu (`createpolicy.fractional.L2::evict_first`, `cp.async.bulk … .L2::cache_hint`); ~11 MB wag na launch nie wypycha już z 24 MB L2 aktywacji, KV i stanu | decode ×1.0331 (5.52 → 5.35 ms/token lokalnie) |
| 10 | Dodawanie residualne prefillu złożone w zapisy i fixup stream-k | (prefill) |
| 11 | `free_decode_begin` odpowiada po przejściu draftera przez prompt (~6 ms przeniesione z okna dekodu do odpowiedzi) | – |

- **Wynik oficjalny:** #73 + #74 = rekord 150.6% → **316.2%**, decode 284.3 → 513.4 tok/s (tablica CUDA, wpis „×7” z 2026-10-17).
- Twierdzenia z posta na X („11 zmian bit-exact… decode 93 → 677 tok/s”) nie znalazłem ani w PR, ani na tablicy. Liczby 93 i 677 są `[niezweryfikowane]`.

**C. Kopie wag w układzie kafelkowym (#24, `08b5a97a`).**
- Wzorzec bazy: warp czytał ~32–34 ciągłe bajty na wiersz wagi na krok K, co na GB10 daje ~200–210 GB/s. Długi ciągły strumień tych samych bajtów daje 230–236 GB/s.
- Zmiana: przy ładowaniu powstaje druga kopia wag PQ2_0/Q8_0 w układzie `[tile][step][row]`, gdzie jeden krok CTA (128 wierszy) to ciągłe 4352 B lub 17408 B. To czysta permutacja bloków.
- Koszt: **+3.4 GiB** VRAM.
- W tym samym PR: PDL dla reszty kerneli dekodu, embedding tokenów na GPU, przekazanie celu do draftera bez hosta.

**D. Ruch danych między grafami i chunked GDN w prefillu (#147, `78b8587b`).**
- Ruch danych:
  - Runda to trzy grafy CUDA: weryfikacja 16 wierszy, enkoder DFlash2, drafter.
  - Uploady wejść hosta idą na pomocniczy strumień, jeden kernel gather zastępuje 8 kopii i permutację, wyniki slotów są czytane w miejscu.
  - Przerwy między grafami **141.7 → 36.3 µs** na rundę ~18.5 ms, decode ×1.003–1.004.
- Chunked GDN w prefillu: algorytm chunkwise (C = 32), trójkątna odwrotność, potem dokładny ogon K tokenów starym kernelem.
  - Op ×1.37 / ×1.26, prefill ×1.0283.
  - **Niebitowe:** błąd 3e-8 na wyjściach i 2.4e-7 na stanie. Opiera się na regule near-tie.

### 3.6 Tor MLX: drzewo draftu, drafter W4, delta replay, sito słownika

**Drafter 4-bit (pratikgx, #227, `14defb84`).**
- Liniowe draftera DFlash2 są w pamięci przekwantowane z Q8 do affine 4-bit g64.
- Dla każdej grupy wybierany jest czynnik zakresu z {1.0, 0.95, 0.90, 0.85, 0.80, 0.75} o najmniejszym błędzie rekonstrukcji.
- Aktywacje int8, matmul na jednostkach tensorowych M5 (NAX).
- To zmiana **stratna tylko dla draftera**: o tokenach decyduje cel.
- Wynik oficjalny **3.3405 → 3.8411** (+15%), co potwierdza opis następcy w #231.
- Później kaankolcu (#421) ułożył kody, skale i offsety w ciągłe kafle po 1152 B (32 wiersze × 64 kolumny), tak że jeden load simdgroupy to ciągłe 512 B. Bitowo bez zmian.

**Drzewo 15 węzłów w jednej 16-wierszowej weryfikacji (kaankolcu, #424, `705fd6c2`).**
- Budowa drzewa:
  - selektor DFlash2 ma już dla każdej z 15 pozycji top-16 kandydatów z wynikiem unarnym i krawędziowym;
  - zamiast zachłannego łańcucha rozwija węzeł o największym prawdopodobieństwie ścieżki (softmax T = 0.8), aż powstanie 15 węzłów;
  - wiersze idą w kolejności DFS, więc drzewo-łańcuch ma układ rodzica;
  - deskryptor int32 zawiera rodzica, głębokość i przodków.
- Cel weryfikuje drzewo trzema podmianami tekstu kerneli:
  - RoPE według głębokości;
  - uwaga po kluczach własnej ścieżki;
  - GDN: tapy konwolucji od przodków, rekurencja wzdłuż ścieżki.
- Commit: wiersze KV ścieżki przesuwane na zatwierdzone sloty, stan GDN przeliczany wzdłuż ścieżki.
- Lokalnie (starszy GPU Apple, 1024 tokeny): **122 → 113 rund weryfikacji**, emitowane tokeny identyczne.

**Restart gałęzi od zapisanego stanu (#433, `620538da`).**
- Kernel wybiera w prologu jeden wiersz, którego zapis oszczędza najwięcej powtórzonych kroków, i zapisuje jego stan w trakcie skanu.
- Powtórzone kroki przodków spadają z **8.5 do 1.5** na rundę drzewa, skan z ~24.5 do ~17.5 kroków szeregowych na warstwę.
- Finał #624: commit rundy też startuje od tego stanu.

**Temperatura drzewa per blok (#428, `c7d90163`).** Jeśli udział top-1 pierwszej pozycji przy T = 1 jest < 0.8, cały blok budowany jest przy T = 1 (więcej rozgałęzień przy korzeniu), w przeciwnym razie przy T = 0.8.

**GDN SG16 + delta replay (ArthurOstapenko, #467, `a5ff…`).**
- Jedna grupa 512 wątków na głowę w weryfikacji 16 wierszy.
- Weryfikacja zapisuje taśmę `delta` (128 wartości na głowę) i `g` w układzie `[1, S, Hv, 129]`, czyli 264 192 B na warstwę.
- Commit to samo `s *= g; s = fma(k, delta, s)` w tej samej kolejności, bez ponownego liczenia iloczynów k·S i bramek.
- Decode **×1.0205** na 39 promptach (×1.0350 na 15 „hidden-like”), ale zysk jest skupiony w dwóch promptach (×1.385 i ×1.153).

**Sito głowicy draftu (spariev, #431, `f152dfdc`; kaankolcu #523: 13 z 32 grup).**
- Głowica draftu: 98 304 wiersze `lm_head`, ~100 MB słów + 6 MB skal na rundę.
- Najpierw iloczyn na pierwszej połowie K dla wszystkich wierszy, potem top-128 na pozycję i dokładne przeliczenie tych 128 tą samą arytmetyką.
- Zmienia tylko propozycje, gdy prawdziwe top-16 wypada poza sito.

**Metoda spariev.** Łączy odrzucone zgłoszenia, które na graderze mierzyły się szybciej od rekordu (#397, #419). Podobnie jak ich load-time bit-checki: każda fuzja przy starcie porównuje się z wersją bazową na prawdziwych wagach i bez zgodności wraca do rodzica.

### 3.7 Flapping Airplanes i blog

- **Flapping Airplanes.** Strona to tylko animacja i kilka akapitów (tekst z `assets/index-DtZtnXfl.js`):
  - „radical new techniques to improve the efficiency of AI”, współewolucja modeli i systemów;
  - „world’s most complete megakernel framework”: dziwne architektury i optymalizatory, nakładanie dekodu ograniczonego pamięcią z treningiem ograniczonym obliczeniami w jednym kernelu, trening + inferencja + gra w jednym kernelu;
  - inwestorzy Index, GV, Sequoia, Lux, NVIDIA i inni; wspierają ich m.in. Jeff Dean, Andrej Karpathy, Chris Ré.
  
  Kodu i liczb brak.
- **Blog** ([link](https://thelastone07.github.io/blog/making_cuda_less_overwhelming/)): hierarchia H100, PTX/SASS, banki SMEM, koalescencja, cp.async → TMA, swizzle, roofline, matmul od naiwnego do float4 (za siboehm). Materiał szkoleniowy na poziomie wstępu.

## 4. Liczby (z warunkami pomiaru)

| liczba | warunki | źródło |
|---|---|---|
| DS-V4.1-Flash oQ3e: decode MTP off 22.9 → 42.7 tok/s; MTP + CED 49.4 → 68.2; prefill 700 → 949 | M3 Ultra 512 GB, checkpoint `-mtp`, prompt 16K | [oMLX 0.7.2](https://github.com/jundot/omlx/releases/tag/v0.7.2) |
| Lightning MTP przy TP: GLM-5.3 Flash oQ4e 13.7 → 27.7 tok/s (+102%) | 2× M3 Ultra, TCP przez Thunderbolt, sampled T=1, 512 tok | jw. |
| Qwen3.6-27B 42.8 → 55.1 tok/s z Lightning MTP | M3 Ultra, greedy | commit `8a9b1972` |
| Locals vs mlx-lm, 8 żądań: 87 → 271 tok/s; 1 żądanie 61 → 64 | M2 Pro 16 GB, Qwen3.5-4B 4-bit g64 | Locals README:120-124 |
| Locals, Qwen3.8-27B, 8 żądań: 25 → 78 tok/s | M2 Max 96 GB | README (wykres modeli) |
| Kernel GDN w Locals: 267.6 → 272.7 tok/s (+1.9%) | jw., 8 żądań | why-faster:31-39 |
| Bonsai CUDA 85.9 → 576.7 tok/s, 10.3 tok/rundę | DGX Spark, ranking na odłożonej puli | yukon.org |
| Bonsai MLX 144.8 → 959.6 tok/s, 9.5 tok/rundę | M5 Max 128 GB | yukon.org |
| Deklaracja DFlash15 (davidtai): +117.3%, decode 235.9 tok/s | DGX Spark | tablica CUDA |
| Seria ArthurOstapenko #73 + #74: 150.6% → 316.2%, decode 284.3 → 513.4 | jw. | tablica CUDA |
| Leniwe cofanie GDN: decode +7.5–8.3%, zapisy GDN 34.6 MB → ~4.5 MiB na wywołanie | GB10, pary lokalne | cudafast #9 |
| L2 evict_first na wagach: decode ×1.0331 | GB10 (L2 24 MB) | cudafast #74, zm. 9 |
| Ciągły strumień wag 230–236 vs 200–210 GB/s | GB10, J=16 | cudafast #24 |
| Chunked GDN w prefillu: op ×1.37, prefill ×1.028 (niebitowo) | GB10, T = 512 | cudafast #147 |
| Drzewo 15 węzłów: 122 → 113 rund | Apple GPU starszej generacji, 1024 tok | mlxfast #424 |
| Drafter W4: wynik 3.3405 → 3.8411 | M5 Max, ranking | mlxfast #227, #231 |
| Delta replay + SG16: decode ×1.0205 (39 promptów) | M5 Max (grader) | mlxfast #467 |

## 5. Licencja / dostępność

| projekt | licencja | uwagi |
|---|---|---|
| oMLX | Apache-2.0 | macOS 15+, tylko Apple; kernele qmm z MTPLX (Apache-2.0) |
| Locals | Apache-2.0 | macOS 14+, M1+, tylko modele MLX |
| cudafast-bonsai2-9b-engine | MIT (Copyright GumbiiDigital); vendored llama.cpp (MIT) | kod PR publiczny; wagi Bonsai Apache-2.0 (nie pobierałem) |
| mlxfast-bonsai2-9b-engine | MIT (Copyright Layr Labs) | mlx-swift / mlx-swift-lm vendored |
| Flapping Airplanes | brak kodu | – |
| blog | brak licencji na stronie | tylko do czytania |

## 6. Co z tego dla nas

Kontekst: Qwen3.8-27B Q4 na XTX jest ograniczony pasmem. Krok weryfikacji MTP4 to 5 wierszy, a wiersz kosztuje ~0.85 ms ([[koszt-szerokosci-weryfikacji]]). Bonsai 9B ma ~2 GB wag, więc na Sparku był ograniczony narzutem. Dlatego część ich zysków (launche, przerwy między grafami) u nas już zniknęła dzięki PM4 replay.

| pomysł | XTX/ROCm | 3090 (wynajem) | szac. zysk / nakład | ranking |
|---|---|---|---|---|
| Sito głowicy draftu (pół K + dokładne top-128) na słowniku draftu 64k | tak | tak | +0.5–1.5% t/s `[INFERENCE]`: głowica IQ4_XS 64k × 5120 ≈ 178 MB na token draftu, sito oszczędza ~45% tych bajtów / 1–2 dni | **1** |
| L2 `evict_first` (`createpolicy` + `ld.global.L2::cache_hint`) na wagach w MMVQ/MMQ | nie dotyczy (mamy `glc dlc`, 23b2) | tak, sm_80+, L2 6 MB | +0.5–2% `[INFERENCE]` (GB10: +3.3%) / 0.5–1 dnia | **2** |
| Taśma delt GDN (weryfikacja zapisuje `delta` i `g`, przeliczenie zatwierdzonych wierszy bez k·S) | tak, rozszerzenie S4 | tak | +0.3–0.8% `[INFERENCE]` (GDN ~14.5 µs × 48 warstw ≈ 0.7 ms/krok) / 2–3 dni, bitowo | 3 |
| Audyt „sufitu wzorca” + układ wag kafelkami (R18 #12) | tak, ale bez drugiej kopii (27B nie zmieści duplikatu) | tak | 0–10% `[INFERENCE]` / 1 h audytu, potem 8 dni | 4 (audyt najpierw) |
| Drzewo w stałej szerokości W16 dla DFlash2 + restart od zapisanego stanu + T per blok | tylko jeśli DFlash2 wygra z MTP | jw. | −7% rund przy W16 / 10+ dni (kernel drzewa GDN, R18) | 5 |
| Chunked GDN w prefillu (niebitowy) | nie (Strata: −39% na gfx1100) | może | +1–3% prefill `[INFERENCE]` / 3–5 dni | 6 |
| Fuzja konwolucji draftera DFlash2 (jeden op) | tylko ścieżka DFlash2 | jw. | ~+2% na tej ścieżce / 2 dni | 7 |
| Leniwe cofanie GDN / NOFINAL | już mamy (S4) | już mamy | – | – |
| Drafter / głowica draftu w 4 bitach | już mamy (`--spec-draft-head-type iq4_xs`, `--spec-mtp-type iq4_xs`) | jw. | – | – |
| Adaptacyjna głębokość z pomiaru (Lightning MTP, parkowanie) | zbadane w 24q: zmienia md5 | – | – | – |
| Locals: kernel GDN w jednym launchu | już mamy | – | – | – |
| Locals: gramatyka na GPU, tokeny wymuszone bez modelu | nie dotyczy t/s (produkt: agenci, JSON) | – | – | – |
| CED, SpecPrefill, Splash, klaster Maców | nie dotyczy | nie dotyczy | – | – |
| LFM / Flint | Idee draftu (sito, drzewo) dotyczą tylko modeli z drafterem; dla LFM bez MTP nie dotyczy | – | – | – |

Wnioski procesowe:

- **Agentowy styl pracy zwycięzców jest zbieżny z naszym:** wiele instancji Opus 5.5 / GPT-6.1 pod koordynatorem, przełącznik na każdą zmianę, test równoważności bit w bit na każdą fuzję, pary ABBA. Nowe dla nas są dwie rzeczy:
  - (a) **bit-check przy starcie na prawdziwych wagach z automatycznym powrotem** do kernela rodzica: odporność na nieznane GPU klientów;
  - (b) **łączenie odrzuconych, ale szybszych zgłoszeń** w jedno (spariev).
- **3090 a kod CUDA z konkursu.** Kernele są pod GB10 (sm_121: TMA `cp.async.bulk`, klastry, PDL). Na sm_86 przenosi się:
  - leniwe cofanie (mamy);
  - fuzje glue GDN i granicy warstwy;
  - układ kafelkowy wag;
  - `L2::evict_first` (sm_80+).
  
  Nie przenosi się: pierścień TMA, klastry, DSMEM, PDL `[INFERENCE]` (PTX ISA).

## 7. Do przetestowania

1. **T1. Sito głowicy draftu (XTX, potem 3090).**
   - Pomiar: w `llama-mtp` / ścieżce `--spec-draft-vocab` zmierz czas matvec głowicy draftu na krok (rocprofv3). Jeśli ≥ 0.5 ms/krok, zaimplementuj:
     1. MMVQ na pierwszych 10 z 20 superbloków K;
     2. top-128;
     3. dokładne dot dla 128 wierszy.
   - Bramka: tok/krok bez spadku > 0.5% na prozie i mvs, t/s ≥ +0.5%.
   - Ryzyko: md5 może się zmienić, bo inne drafty dają inne szerokości weryfikacji (patrz 24q). Akceptowalne tylko przy T=1 albo jeśli przy stałej głębokości md5 = baza.
   - Koszt: 1–2 dni + 20 min GPU.
2. **T2. `L2::evict_first` na wagach w MMVQ (3090).**
   - Jeden przełącznik `GGML_CUDA_WEIGHT_EVICT_FIRST`, wagi przez `ld.global.L2::cache_hint` z polityką `createpolicy.fractional.L2::evict_first`.
   - Bramka: md5 = baza (to tylko wskazówka cache), ABBA +0.5%.
   - Koszt: ~0.5 dnia + 30 min wynajmu 3090.
3. **T3. Taśma delt GDN (XTX).**
   - W `GATED_DELTA_NET_LAG` zapisuj w weryfikacji `delta` (S_v) i `g` per wiersz oczekujący. Przeliczenie w następnej weryfikacji robi tylko `s = g·s + k⊗delta`, bez redukcji k·S.
   - Bramka: tbo `GATED_DELTA_NET*`, md5 c4708318 / 6f14e814, rocprof GDN ≥ −20%, t/s ≥ +0.3% (inaczej kill wg [[lekcja-wyrazna-wygrana-albo-nic]]).
   - Koszt: 2–3 dni.
4. **T4. Audyt sufitu wzorca (R18 #12) na XTX.**
   - Mikrobench: czysty odczyt ffn 5120 × 17408 (Q4_K / Q5_K / IQ4_XS) wzorcem produkcyjnym MMVQ n=5 vs ciągłe przebiegi 4–16 KB na CTA.
   - Kill: < 5% różnicy.
   - Koszt: 1 h GPU.
5. **T5. Audyt API Anthropic w llama-server (CPU).** Czy tekst `user` umieszczany przed wiadomościami `tool` (`server-chat.cpp:524-542`) łamie szablon Qwen3.8 albo stabilność prefiksu w drugiej turze. Zysk: TTFT agentów, poprawność. Koszt: 1 h.
6. **T6 (warunkowo). Drzewo W16 dla DFlash2.** Tylko jeśli kiedyś DFlash2 / W16 wygra z MTP po polsku. Najpierw offline symulacja z logów kraty top-16 (jak 24s) z regułą T per blok. Koszt symulacji: 0.5 dnia CPU.

## 8. Do bazy wiedzy

- Notatki: [[omlx]], [[locals]], [[bonsai-fast-contest]], [[flapping-airplanes]], [[raport-60b-apple-bonsai]].
- Uzupełnienia: [[gdn-replay]] (odpowiedniki z konkursu), [[bonsai]] (Bonsai 2 9B, konkurs), [[ZRODLA]].
- CompWatch: `jundot/omlx` (B), `Generated-Computers/Locals` (C), `Layr-Labs/cudafast-bonsai2-9b-engine` (A), `Layr-Labs/mlxfast-bonsai2-9b-engine` (B).
- Pomysły T1–T6 trafiły do `product/DO-PRZETESTOWANIA.md`.

## 9. Źródła

- oMLX 0.7.2: https://github.com/jundot/omlx/releases/tag/v0.7.2 ; repo https://github.com/jundot/omlx (Lightning MTP: commit `8a9b1972`, rename `56f08fdb`; `omlx/patches/mlx_lm_mtp/batch_policy.py`, `qwen35_model.py`; CED: `omlx/patches/deepseek_v41/config.py`, `omlx/model_settings.py:387-390`; `docs/experimental/dflash_mlx_integration.md`; `docs/Splash.md`)
- DeepSeek-V4.1-Flash (CED): https://arxiv.org/abs/2609.19969 ; vLLM: https://vllm.ai/blog/2026-10-07-deepseek-v41-flash
- Locals: https://github.com/Generated-Computers/Locals (README, `docs/why-faster/README.md`, `docs/runtime/README.md`, `locals/gdn_kernel.py`); praca https://arxiv.org/abs/2610.09139
- Konkurs:
  - repozytoria: https://github.com/Layr-Labs/cudafast-bonsai2-9b-engine , https://github.com/Layr-Labs/mlxfast-bonsai2-9b-engine
  - PR CUDA: #9, #24, #73, #74, #147 (https://github.com/Layr-Labs/cudafast-bonsai2-9b-engine/pull/74 itd.)
  - PR MLX: #214, #227, #231, #397, #419, #421, #424, #428, #431, #433, #467, #523, #624 (https://github.com/Layr-Labs/mlxfast-bonsai2-9b-engine/pull/424 itd.)
  - tablice: https://www.yukon.org/cudafast?benchmark=bonsai2-9b&platform=cuda , https://www.yukon.org/mlxfast?benchmark=bonsai2-9b&platform=mlx
  - wyniki: https://x.com/0xkydo/status/2113382850687009185
  - PrismML: https://prismml.com/news/bonsai-2-family
- Flapping Airplanes: https://flappingairplanes.com/ ; https://techcrunch.com/2026/10/21/year-old-ai-lab-flapping-airplanes-raises-1b-at-a-6b-valuation/
- Blog: https://thelastone07.github.io/blog/making_cuda_less_overwhelming/
- Nasze: `~/wt/topka-int/tools/server/server-chat.cpp:312-545` (`d5839abfb`); [[gdn-replay]]; [[raport-24s-drzewa-proza]]; [[raport-24q-adaptacyjna-spekulacja]]; [[koszt-szerokosci-weryfikacji]]; `product/research/23b2-re-kernele-amd-bariery.md`; `product/research/18-nastepna-fala.md:426-436`; `qwen-opt/research/strata/prefill.md:173-174`; `product/research/15c-nowe-silniki.md:270`
