# 21g — Nowe silniki: inferrous, TensorFold 1.1.0 + aplikacja Beta 8, Project Maya 1.1.14–1.1.15, Strata 0.1.44.1–0.1.45 (bez KV na dysku)

Data: 2026-10-19. Sprawdzone tylko na CPU: czytanie kodu, release notes, issues/PR i API GitHuba. Nic nie było budowane pod GPU ani uruchamiane na GPU. Jedyny wyjątek to kompilacja dwóch 10-linijkowych kerneli testowych do asemblera gfx1100 (`hipcc -S`, bez uruchamiania; §5.3).

Klony (blobless) leżą w `~/qwen-opt/research-src/`:
- `inferrous` @ `405bfd3`;
- `tensorfold-new` @ `d46d17a7`;
- `project-maya` @ `a4e1ff0` (v1.1.15);
- `strata-new` @ `477ac13c` (= v0.1.45 = HEAD `main`).

Notatki robocze z pełnymi tabelami i wszystkimi źródłami są w `21g-notatki/`:
- `tf-delta.md`: TensorFold;
- `maya.md`: Maya;
- `strata-release-notes-0.1.44.1-0.1.45.md`;
- `tensorfold-board-2026-10-19.json`: zrzut tablicy wyników;
- `k.s` / `k2.s`: asembler barier.

Zakres Straty jest uzgodniony z 21d (ResKvDurability). 21d bierze cache rozmów, checkpointy, warstwę plikową i tożsamość odpowiedzi. Tutaj jest reszta: wydajność, kernele, HIP, wiele slotów, społeczność.

Oznaczenia: `[INFERENCE]` = mój rachunek albo wniosek, niezmierzony. Werdykty: **wiarygodne / wątpliwe / błędne**.

---

## 0. Najważniejsze w 12 punktach

1. **Strata 0.2.0 nie istnieje.** API releases (2026-10-19) kończy się na v0.1.45 (opublikowana 2026-10-17 06:53 UTC). Tag `v0.1.45` = `477ac13c` = HEAD `main`, po nim zero commitów. Repo było ostatnio pushowane 10-17 06:50.
2. **inferrous** to badawczy silnik w Ruście: wszystkie kernele w Ruście (cuda-oxide), tylko Qwen3-8B W8A8, tylko RTX PRO 6000 (SM120). 182 t/s to 80% pasma, czyli rzetelna robota. Porównanie jest jednak tylko z vLLM, bez llama.cpp. Do tego ich własna bramka zgodności z PyTorch **nie przechodzi** (rel. L2 logitów 9–11%). Dla nas: zero produktu. Dwie lekcje: „prefetch wag w oknach, gdzie DRAM stoi” (na NVIDIA) i „bitowa zgodność z samym sobą ≠ wierność modelowi”.
3. **TensorFold 1.1.0:** 901 commitów od 1.0.12, z czego **HIP: 6 plików, +12/−9, zero zmian funkcjonalnych**. Serwer HIP po cichu ignoruje `--drafter` (#1001), a tablica wyników odrzuca paragony ROCm. **AMD dalej jest nasze.** Na NVIDIA już nie: Qwen3.8-27B + DFlash2 na CUDA jest wydany. RTX 5090 robi chat T0 263 / code T0 367 t/s; po przeliczeniu na pasmo XTX to ≈ 141 / 196 `[INFERENCE]`, wobec naszych 103–130 (różne prompty).
4. **Aplikacja TensorFold Beta 7/8 (tylko Mac):**
   - profile per model (mały/duży kontekst, sampling, drafting);
   - wbudowane benchmarki z przełącznikiem **„Serial baseline”**, czyli bez spekulacji;
   - porównanie dwóch modeli na jednym prompcie;
   - 14 języków UI, w tym polski;
   - konektory (Gmail, Slack, Telegram…);
   - „klastry” służą tylko do zarządzania, rozproszonej inferencji nie ma.

   **Polski jest maszynowy.** Większość „could not…” wyszło jako bezosobowe „Nie utworzono podglądu.” (zamiast „Nie udało się…”), a zdanie uzasadniające rekomendację modelu zostało po angielsku.
5. **Tablica wyników TensorFold:** 45 przebiegów, wszystkie na silniku 1.0.12, 0 AMD, 0 przebiegów z „serial baseline”. W każdej klasie jest jeden angielski prompt (kod = Fibonacci), komórki idą blokami, bez przeplotu. Na stronie głównej wisi „874 t/s” z wydania 1.0.6 na najlepszym prompcie. Liczba **wiarygodna, ale wybrana pod efekt**.
6. **Maya** to silnik jednego modelu (GLM-5.3-Flash, 321B/18B aktywnych), pochodna Straty, nie fork llama.cpp. Eksperci są w trzech warstwach: VRAM → przypięty RAM → NVMe (O_DIRECT). Liczby z README są wiarygodne, ale to wybór najlepszych wierszy z różnych wersji, a **llama.cpp nie pojawia się w nich nigdzie**. Wskaźnik „97.7–99.2% dokładności FP8” to marketing (5 testów MC po 400 pytań). Uczciwa liczba to KL 0.428 i 83% tego samego top-1 dla Maya-S, czyli poziom ~q2_K.
7. **Maya v1.1.14, Pascal:** 38 linii, w tym `-Xptxas -dlcm=ca`, bo Pascal nie trzyma loadów globalnych w L1. Na P40 dekod jest ×1.7–3.0. **P100 (sm_60) najpewniej się nie skompiluje:** surowe `__dp4a` wymaga CC 6.1, a setup przyjmuje CC 6.0 `[INFERENCE]`. Q6_K_XL/Q8_0 eksperci to nowy typ 8 w kernelach ekspertów.
8. **Domyślne wyjście Mai nie jest deterministyczne:** przy domyślnych ustawieniach tylko 17/70 par restartów dało identyczne tokeny, a v1.1.13 i v1.1.15 zmieniły domyślne tokeny. Nasze md5-bit-exact nie ma tam odpowiednika.
9. **Strata 0.1.45** to głównie ścieżka Qwen3.6-35B-A3B (GDN + MoE). Dekod na R9700 83.2 → 117.8 t/s (×1.42; llama.cpp 82), bitowo jak stare kernele. Fuzje (norma + q8_1, router + top-k, gate + up + SwiGLU + q8_1, koniec MoE + q8_1 następnej warstwy) to **dokładnie nasze łatki 0049/0051/0053/0056**: niezależne potwierdzenie naszej drogi, nic nowego dla nas. Do tego obsługa wielu żądań naraz (`--parallel`, ×1.14–1.61 nad `llama-server -np`) i przełączniki dla serwerów wielu użytkowników.
10. **Najlepszy pomysł do przeniesienia, bitowo identyczny i tani:** PR społeczności #3064 Straty, bariery „tylko LDS” na RDNA. Sprawdziłem asembler gfx1100. `__syncthreads()` kompiluje się do `s_waitcnt lgkmcnt(0); s_barrier; buffer_gl0_inv`, a bariera z płotem `__builtin_amdgcn_fence(…, "workgroup", "local")` do samego `s_waitcnt lgkmcnt(0); s_barrier`, bez unieważniania L0 (`21g-notatki/k.s:27-29` vs `k2.s:33-34`). Nasze GDN nie ma barier (same redukcje warpowe), więc celem są kernele z barierami w pętlach: `fattn-kvq` (5), `fattn-tile` (8), `fattn-vec` (6), `mmq` (12).
11. **Konkurencja produktowa:** Strata uruchamia Qwen3.8-Flash-Next (125B MoE) na **naszej karcie** (XTX + 96 GB RAM) z ~80 t/s dekodu (MTP) i 1810 t/s prefillu przy 98K (#2938). To większy model niż nasz 27B przy podobnej prędkości, dla użytkowników z dużym RAM-em. Silniki jednego modelu (Strata, Maya) mają świetne pętle społecznościowe (`--bench` → `--report` → issue → tabela).
12. **Ranking pomysłów (szczegóły w §6):**
    1. bariery LDS-only (HIP);
    2. przełącznik pełnej głowicy draftu, gdy kontekst wychodzi poza słownik 64k (PL);
    3. pomiar wielu slotów dla równoległych agentów omp;
    4. rozgrzewka cache ekspertów z profilu + auto-wyłączanie MTP przy ekspertach z RAM (LFM na 12 GB);
    5. prefetch L2 w oknach latencyjnych na sm_120.

    Produkt: przełącznik „bez przyspieszenia” w aplikacji jako przed → po; schemat paragonu; API Anthropic; natywny polski; kontrola zegarów GPU podczas dekodu.

---

## 1. inferrous (bitemyapp/inferrous)

### 1.1 Co to jest
- „LLM inference in Rust with GPU kernels written in Rust via cuda-rust”, Apache-2.0/MIT, autor Chris Allen. **2 commity** (`67db7bf` „Initial public release” i `405bfd3` „Migrate to NVIDIA cuda-rust”, oba 2026-10-07), 3 gwiazdki ([repo](https://github.com/bitemyapp/inferrous)). Historia jest zgnieciona, więc rund optymalizacji nie da się odtworzyć z gita, tylko z dokumentów.
- Jeden silnik, `crates/inferrous-qwen3`, ok. 4.9 tys. linii Rusta, z czego `kernels.rs` ma 2389. **31 kerneli `#[kernel]` w Ruście**, kompilowanych przez cuda-oxide (Rust → PTX, `--arch sm_120`, `docs/migrations/cuda-rust.md:19`). Nie ma CUDA C++, cuBLAS-a ani bibliotek atencji. Jest za to inline PTX: `griddepcontrol.wait/launch_dependents` (`kernels.rs:181-182`), `prefetch.global.L2` (`kernels.rs:233,263`), `redux.sync`, `cvt.rni` (`kernels.rs:31,43,51`).
- Model: Qwen3-8B, wagi INT8 per kanał + dynamiczne aktywacje INT8 per token (W8A8). KV i głowica w BF16. Dekod na **DP4A**, czyli rdzeniach CUDA, nie tensorowych (`kernels.rs:3,286`); prefill na INT8 tensor cores.
- Ograniczenia z README: jedno żądanie naraz, tylko greedy, kontekst ≤ 4096, „research-grade code, not an accuracy-certified model server”.
- Następny model to Qwen3.6-35B-A3B FP8 (GDN + MoE + MTP), na razie tylko plan (`docs/plans/qwen3.6-35b-a3b-fp8.md`).

### 1.2 Weryfikacja deklaracji

| Deklaracja | Co zmierzono | Arytmetyka | Werdykt |
|---|---|---|---|
| **182.3 / 178.2 / 170.5 t/s** dekodu (prompt 5 / 129 / 512), „faster than the best stock W8A8 configuration” (vLLM + Humming INT8: 144.4 / 143.3 / 142.9) (README; `docs/qwen3-8b-w8a8/benchmarks.md:11-15`) | RTX PRO 6000 **Max-Q, 300 W**, dokładnie **32 tokeny wyjścia**, EOS ignorowany, 3 rozgrzewki + 20 pomiarów, finał A/B/B/A po 40 żądań (`benchmarks.md:3,9`). vLLM nie był powtórzony w rundzie 6 (`benchmarks.md:25`) | Krok czyta 7.88 GB: ciało INT8 6.95 GB + głowica 12-bit (`optimization/round-6.md:17`). 7.88 GB × 182.3 = **1.44 TB/s = 84% z 1.71 TB/s** (szczyt NCU przy 13.35 GHz pamięci) i 80% z 1.79 TB/s specyfikacji. Ich własna podłoga: 5.0 ms/krok, czyli ~200 t/s | **Wiarygodne** jako pomiar. **Wybrany baseline:** brak llama.cpp, który dla W8A8 ma ten sam schemat (q8_1 × Q8_0 na DP4A, mmvq). Szacunek llama.cpp Q8_0 na tej karcie: plik 8.71 GB, czytane ≈ 8.05 GB/token, sprawność 60–75% (llama 7B Q4_0: 279 t/s × 3.82 GB = 1.07 TB/s = 60% przy 600 W, [llm-tracker](https://llm-tracker.info/RTX-PRO-6000)) → **133–167 t/s** `[INFERENCE]`. Przewaga nad llama.cpp to więc zapewne +9…+37%, nie „+26% nad najlepszym stock” |
| „Every optimization preserves the complete-vocabulary logit hashes” (README) | Hashe wszystkich logitów i ID tokenów wobec **własnego** pierwszego buildu, 4416 hashy na implementację (`round-6.md:77`) | — | **Wiarygodne, ale wąskie:** to bit-exact wobec siebie. Niezależna bramka z PyTorch **nie przechodzi**: rel. L2 logitów **9–11%** przy tym samym argmax pierwszego tokenu, rozjazd od warstwy 4 (`discrepancies.md:7-9`). Jakość modelu nie była oceniana (README) |
| Runda 6, „keep DRAM busy”: +7.0 / +7.8 / +6.5% (`round-6.md:73`) | Ślad: 364 kernele/krok; gate/up 2276 µs (1592 GB/s), O+down 1652, QKV 609, głowica 574 (92% szczytu), **252 kernele latencyjne = 642 µs**; ~830 µs/krok bez strumieniowania wag (`round-6.md:9-17`) | 830 / 5755 µs = 14.4% kroku z DRAM w bezczynności. Odzyskali 325 µs (5755 → 5430 µs grafu, `round-6.md:73`), czyli 39% tej dziury | **Wiarygodne**, z dobrą metodą: mikrobench, odrzucone warianty spisane w tabeli (`round-6.md:53-61`) |
| Bezstratne pakowanie głowicy BF16 do 12 bitów: 943 404 322 B vs 1 244 659 712 B = 75.8% (`round-3.md:24`) | 99.985% wartości ma wykładnik 109–123, więc wystarcza 4-bitowy selektor + bajt znak/mantysa i tablica wyjątków. Pełny test wszystkich 65 536 wzorców BF16 (`round-3.md:24-26`) | Głowica 574 µs przy 92% szczytu, czyli zysk ≈ 25% bajtów głowicy ≈ 3% kroku. Zmierzone: ~5 ms na żądanie z 32 tokenami (`round-3.md:32`) | **Wiarygodne.** To wariant DFloat11 o stałej długości kodu |
| PDL („programmatic graph edges”): 174.40 → 177.44 t/s osobno (`round-6.md:38`); „PDL saves ~0.5 µs per boundary, only with early trigger” (`round-6.md:26`) | Mikrobench SM120 | 364 granice × 0.5 µs ≈ 0.18 ms/krok ≈ 3% | **Wiarygodne.** Zgodne z naszym pomiarem PM4-PDL na XTX: −0.11 µs, kill (`wiki/eksperymenty/2026-10-18-pm4-pdl-x1.md`) |

### 1.3 Co nowe wobec llama.cpp i naszego forka
- **PDL:** nic nowego. llama.cpp CUDA ma PDL od Hoppera wzwyż, włącznie z konsumenckim sm_120 (`~/llama-master/ggml/src/ggml-cuda/common.cuh:124-142,1820-1826`).
- **Prefetch wag do L2 z małych kerneli i „hoist cold loads”:**
  - W llama.cpp CUDA tego nie ma.
  - Na XTX już to próbowaliśmy: „touch” do MALL, X3, wynik w szumie (`wiki/lekcje/lekcja-prefetch-mall-xtx.md`). `hipLaunchAttributeExtDynDataPrefetch` nie działa poniżej gfx12.5 (`wiki/rocm/hip-dyn-data-prefetch.md`).
  - „Wszystkie loady przed sumami” znamy z TensorFold (`wiki/repo/tensorfold.md`).
  - Nowe jest tylko **na NVIDIA**: 16 dodatkowych CTA z `prefetch.global.L2`/`cp.async.bulk.prefetch.L2` w kernelu latencyjnym chowa 80–85% jego czasu (`round-6.md:23`). Ważne zastrzeżenie: pod PDL ten prefetch trzeba robić tylko tam, gdzie poprzednik nie nasyca DRAM (`round-6.md:42-45`).
- **Bezstratna głowica 12-bit:** nie dla nas. Nasze głowice i embeddingi w GGUF są kwantyzowane, a w kwantach K/IQ nie ma redundancji wykładnika BF16 `[INFERENCE]`.
- **Dokładna akumulacja FP8 w liczbach całkowitych** (plan Qwen3.6: iloczyn E4M3 × E4M3 jest wielokrotnością 2⁻¹⁸, więc blok 128 sumuje się dokładnie w i64; `plans/qwen3.6-35b-a3b-fp8.md:51`): niezmienniczość względem batcha i kolejności za darmo. To ta sama idea co nasze q8_1 × Qx_K na DP4A. Koncepcyjnie warta zapamiętania na wypadek FP8 na RDNA4.
- **Proces:** A/B/B/A, odrzucone eksperymenty spisane z danymi, wyrocznia hashy na każdym biegu. Robimy to samo (ABBA, md5, KLD), my dodatkowo z bramką KLD wobec referencji, której oni nie mają.

**Werdykt:** dla produktu **brak** (SM120, 8B, greedy, 4K kontekstu). Dla metody jedna przestroga: hash wobec własnego baseline'u nie łapie błędu wierności. U nas pilnuje tego KLD wobec upstream i kanarki.

---

## 2. TensorFold 1.1.0 i aplikacja Beta 7 / Beta 8

Poprzedni stan: v1.0.12 = `833bbfcb` (raport 15c §2.4/§3.4, `wiki/repo/tensorfold.md`). Tu opisuję wyłącznie deltę. Pełne tabele: `21g-notatki/tf-delta.md`.

### 2.1 Skala delty
- **901 commitów** v1.0.12..v1.1.0, w tym 394 jednego dnia (10-16), plus 3 commity po tagu. Kod spoza aplikacji: 1285 plików, +140 tys. linii. Kernele: CUDA 76 plików (+12.6k), Metal 35 (+5.3k), **HIP 6 plików, +12/−9**: tylko refaktor `clock_gettime` dla Windows i poprawka puli grafów Flash Next (#963) (`tf-delta.md:11-19`).
- Odpowiedzi opiekuna w issues podpisuje „Ash's AI Assistant Synthena” (#918, #1001, #426). Projekt prowadzi agent AI w tempie ~400 commitów/dzień.
- Tagi: `v1.0.0-beta.7` = `46a08c18` (10-16), `v1.1.0` = `76aafcf2` (10-18), `v1.0.0-beta.8` = `b7ce8121` (10-18). Release: https://github.com/ashhart/TensorFold/releases/tag/v1.1.0.

### 2.2 Silnik 1.1.0: co nowego (źródła w `tf-delta.md:26-81`)
- **Qwen3.8-27B na CUDA** (#836): graf CUDA per kształt dekodu, DFlash2 w łańcuchach i drzewach, mieszane szerokości MLX 2–8 bit, `--kv-cache fp8` (e4m3 + skala fp32 per wiersz), pinned host prompt cache 8 GiB. Do tego Qwen3.6-35B-A3B i Flash Next na CUDA (z MTP), Nemotron Bolt 74B na **własnych kernelach mma.sync dla bloków GGML IQ2_XXS/Q8_0**, Gemma 4 i Step-5 na Metal.
- **Metal 27B:** autotuning podziału K mierzony na *różnych* macierzach wszystkich warstw („a matrix called again sits in the system cache and misleads”). Krok GDN z jednym wierszem ma 3 dispatche zamiast 5 (1.75 → 1.19 ms/token). Atencja dekodu w kawałkach 128/512 zależnie od pozycji; tu uwaga: **„replies can differ from 1.0.12's”**, czyli bitowa zgodność obowiązuje w obrębie wydania, nie między wydaniami.
- **Nemotron Super: głowica draftu z podzbiorem słownika i przełącznikiem pokrycia** (#1011). Strumień drafuje na głowicy FP8 z 49 152 tokenami, dopóki ostatnie 16 tokenów kontekstu mieści się w tym podzbiorze; w przeciwnym razie przechodzi na pełną głowicę (`zig/src/families/nemotron/draft_ids.zig`, `Coverage.recent = 16`). Wynik: angielski i kod +5…+17%, inne języki ~0%. Pomiar ABBABA, mediany z 9 przebiegów (#1011).
- **Przepis na trening draftera z nagranego ruchu** (`docs/recipes/training-a-drafter.md`). Wnioski:
  - KL ważony 0.8^j daje ~2× zysku L1+CE;
  - pominięcie niemieckiego w jednym batchu = −18% akceptacji po niemiecku;
  - pokrycie słownika draftu ogranicza akceptację;
  - na MoE głębokość 4 jest wolniejsza niż 2.
- **Pierwszy token wysyłany przed przygotowaniem draftów** (#932): TTFT 131.9 → 119.1 ms (−9.7%).
- **Kontrakty kerneli zapisywane per wersja nvcc** (#945).
- `tensorfold merge` (scalanie LoRA): domyślna metoda „fold” zachowuje **0.1%** efektu adaptera, ponowna kwantyzacja 99.6%. Domyślne ustawienie jest nie do obrony (#710).
- **AMD:** jedyny nowy artefakt to paragon zgodności 1.0.12 na Strix Halo (gfx1151, 27B 13.06 t/s plain = 77% z 256 GB/s). Serwer HIP przyjmuje `--drafter` i go ignoruje (#1001). Nowych liczb dla W7800, R9700 ani XTX nie ma.
- **LFM2.5-24B-A2B:** bez zmian w silniku, dalej tylko Mac, bez ścieżki CUDA (README:132).

### 2.3 Weryfikacja deklaracji (wybór; pełne C1–C15 w `tf-delta.md:83-101`)

| Deklaracja | Arytmetyka / dowód | Werdykt |
|---|---|---|
| Strona główna: **874 t/s**, Nemotron 3.5 Lightning, RTX PRO 6000, greedy kod z draftingiem, oznaczone „Release 1.0.6” ([tensorfold.dev](https://tensorfold.dev/)) | ≈ 3.23 mld aktywnych parametrów → 1.82 GB/token przy 4.5 bpw. Plain na 5090 (to samo pasmo 1.79 TB/s) to 274–283 t/s = 28% pasma (#610). 874 t/s wymaga ~4–5 tok/krok, co pasuje do promptu Fibonacciego; na prozie ten sam przebieg dał 607 | **Wiarygodne, ale wybrane pod efekt:** najlepszy prompt i stara wersja |
| 27B na M5 Ultra 1.1.0: proza 116 → 126, kod **386 → 432** t/s (release notes) | Krok ≈ 27 ms, więc 432 t/s ≈ **11.8 tok/krok z maks. 16**. Na tablicy 1.0.12 na tym samym chipie kod T0 to 211.5, czyli ich „baseline 1.0.12” (386) jest 1.8× wyższy. Niezależne A/B na M3 Ultra: natywny silnik 1.0.12 płasko 28.6 t/s vs 86.2 ich starego silnika Python (#918) | **Proza wiarygodna, kod wątpliwy** (prompty nieopublikowane) |
| Tablica: 27B CUDA, **RTX 5090 chat T0 263.0 / code T0 366.8**; RTX PRO 4500 142.4 / 198.5, na buildzie własnym 152.9 / 206.8 (sprawdzone w API, `21g-notatki/tensorfold-board-2026-10-19.json`) | Plain roofline 5090 ≈ 1792 / 15 GB ≈ 119 t/s, więc 263 t/s to ≳ 3.5 tok/krok przy realnej sprawności. Przeliczenie na pasmo XTX (960/1792): **≈ 141 chat / 196 code** `[INFERENCE]`. Nasz XTX: MTP n=4 T=0 przy 1.7k = 130.2 t/s (`BENCHMARKI-PRZED-PO-2026-10-19.md:33`), spec_sweep T=1 109.0 (tamże :25). Różne prompty: ich czat to jedno angielskie zdanie o mnożeniu macierzy | **Wiarygodne.** Przewaga DFlash2 nad naszym MTP po przeliczeniu to +8% (T=0, czat) do +40% (inne zestawy). Notatka TfDelta mówiła o „~1.4×”, ja daję przedział, bo nasze 130 przy T=0 to porównanie uczciwsze |
| Spread w komórkach tablicy | Przy T=0 pięć powtórzeń daje identyczne tokeny (5090 chat T0 262.6–263.2), więc mierzy się jitter timera, nie zmienność obciążenia. Przy T=1 rozrzut jest ogromny: code T1 187–299 t/s | Metoda **słaba**: blokowo, bez przeplotu, jeden prompt na klasę, bez liczby akceptacji |
| LFM2.5 na M5 Ultra 4-bit: chat T0 263.0 | 1.388 GB × 263 = 365 GB/s = **30% z 1.2 TB/s**. Nasz XTX Q5_K_M: ≈ 1.70 GB × 293.7 = 499 GB/s = **52%** | **Wiarygodne.** Na LFM jesteśmy szybsi absolutnie i na GB/s |
| „Drafted == plain” na wszystkich rodzinach | Prawda w obrębie wydania. Na HIP drafting nie działa, więc tam tego nie sprawdzono | **Wiarygodne z tym zakresem** |

### 2.4 Aplikacja Beta 7 / Beta 8: co NOWE dla UX (`tf-delta.md:103-140`)
- **Tylko Mac** (Electron). `recommendEngineModel` zwraca `unsupported` dla wszystkiego poza darwin/arm64 (`app/src/lib/model-recommendation.ts:86`).
- **Profile per model** (Beta 7): „Add small context / Add large context / Create profile”, zaawansowany sampling i przełącznik spekulacji.
- **„Compare models”:** dwa modele na jednym prompcie, oba z czasami, po wszystkim przywracany poprzedni model.
- **Wbudowane benchmarki** (Beta 8): suite community-v1 przy kontekście 4096, 4 rozgrzewki + 20 pomiarów, przełącznik **„Serial baseline”** (drafting off), eksport paragonu, nic nie jest publikowane automatycznie (`app/docs/benchmarks.md`).
- **Klastry:** tylko zarządzanie (SSH, instalacja headless, paragony). Rozproszonej inferencji w aplikacji nie ma (`app/docs/clustering.md`, „Current engine support”).
- **Konektory:** Gmail, Calendar, Slack, Discord, Telegram, a w katalogu dalej WhatsApp, iMessage, Matrix… (`app/shared/connector-catalog.ts`). TensorFold idzie w stronę ogólnego agenta-asystenta.
- **Wybór modelu:** 4 modele z kuratorskiej listy, ranking po regexie nazwy chipa, preflight w silniku (format, minimum pamięci, dysk), awaryjnie mniejszy model. Uzasadnienie to jedno zdanie po angielsku. **Brak przewidywanej prędkości.**
- **i18n:** 14 języków UI, w tym polski, 100% kluczy (`app/src/lib/preferences/packs/pl/*.json`). Wybór języka jest na ekranie powitalnym przed konfiguracją modelu. Ocena polskiego (moja kontrola na próbce potwierdza notatkę):
  - **Błąd systemowy:** „could not …” wychodzi jako bezosobowy czas przeszły. Przykłady: „The preview could not be built.” → „Nie utworzono podglądu.”, „The mobile connection could not start.” → „Nie uruchomiono połączenia mobilnego.” Czyta się to jak „nie zrobiono”, a nie „nie udało się”. Grep po tłumaczeniach: 34 × „Nie …ono” vs 14 × „Nie udało się”.
  - Niezręczności: „w Odkrywaj”, „tok./s”, „Szeregowy pomiar bazowy” (zamiast np. „bez spekulacji”), „Living Weights” bez tłumaczenia.
  - **Luka:** zdanie uzasadniające rekomendację modelu i etykieta sprzętu („… with 64 GiB memory”, liczby w formacie en-US) są poza katalogiem tłumaczeń (`ModelRecommendationPanel.tsx:23,27`). Najważniejsze zdanie onboardingu zostaje po angielsku.
  - **Dobry trik:** liczba mnoga jest omijana wzorcem „Etykieta: {count}”, np. „Znalezione modele: {count}”.
  - Werdykt: maszynowy, poprawny gramatycznie, ale nienatywny. Sama Beta 8 przyznaje, że „translation quality can vary”.

### 2.5 Tablica społeczności (/benchmarks)
45 przebiegów, 9 kontrybutorów, 5 typów sprzętu (M5 Ultra 16, M5 Max 14, RTX PRO 4500 9, RTX 5090 3, GB10 3). Wszystkie na 1.0.12, 7 z buildów własnych. **0 AMD:** ROCm jest odrzucany (`docs/community-benchmarks.md:109`). **0 przebiegów „serial baseline”.**

Paragon (schema v1) zawiera sprzęt, repo + rewizję + sha256 configu i tokenizera, backend, ustawienia, sha suite'u i per próbka TTFT, prefill, t/s oraz sha tokenów. Nie ma promptów, wyjść, liczby akceptacji, mocy ani pamięci. Statystyki przelicza serwer, a niepełne komórki nie trafiają do agregatu. Wszystko jest „self-reported” (`docs/community-benchmarks.md:66`).

### 2.6 Wnioski: TensorFold
- **Dla silnika:**
  - przełącznik pokrycia słownika draftu (§6, pozycja 2);
  - lekcje treningu głowicy draftu: polski w każdym batchu, KL 0.8^j, MoE głębokość ≤ 2;
  - autotuning na różnych macierzach (Infinity Cache 96 MB myli pomiar powtarzanej macierzy);
  - pierwszy token przed draftami;
  - md5-baseline per wersja ROCm/hipcc.
- **Odrzucam:**
  - port DFlash2 jako „nowość”: mierzyliśmy, na PL/EN T=1 przegrywa z MTP (71.9 vs 81.1 t/s; po polsku 65 vs 78) (`wiki/modele/drafter-dflash.md`); kierunek drafterów prowadzi 21a (DSpine);
  - LoRA fold, konektory, klastry, Living Weights, fp8 KV (mamy kvq).

---

## 3. Project Maya v1.1.14 (+ v1.1.12–1.1.15)

Pełne notatki: `21g-notatki/maya.md`. Repo: https://github.com/mw00/project-maya (1037★, 51 wydań w 10 dni: v1.0.0 2026-10-07 → v1.1.15 2026-10-16, 404 commity).

### 3.1 Co to jest
- **Silnik jednego modelu** dla GLM-5.3-Flash: 321B, ~18B aktywnych. 45 warstw: 34 KDA (atencja liniowa) i 11 MLA + DSA (rzadka), 288 ekspertów routowanych + 1 współdzielony, top-8, blok NextN/MTP. Eksperci to 95% wag (`docs/GLM5-FLASH.md:19-34`).
- **Pochodna Straty, nie fork llama.cpp:** projekt CMake dalej nazywa się `strata`, a zmienne to `STRATA_GLM_*` (`CMakeLists.txt:11`). Z llama.cpp (przypięty `3cf03257`) bierze tylko układy bloków i codebooki, dot producty CPU z ggml-cpu, MMQ do prefillu (z własną łatką fused-SwiGLU) i mtmd do obrazów (`maya.md:10-16`).
- **Trzy warstwy ekspertów:** pula VRAM per warstwa → przypięty RAM (`cudaHostAlloc`/mlock) → **NVMe przez O_DIRECT**. Migracja LRU na żywo, ruchy w tle na strumieniu kopii (`glm_fast_path.cu:4628-4800`).
- **„CPU lane”:** część pominiętych ekspertów liczy CPU *równolegle* z wysyłką przez PCIe. Podział jest kalibrowany per maszyna i mierzony ponownie w trakcie dekodu (`glm_fast_path.cu:2600-2663`).
- **Profil ekspertów** (`data/expert-profile-glm.bin`, 13 248 par) ustala kolejność rozgrzewki: świeży start 35.4 → 40.7 t/s, trafienia 89 → 96% (`docs/SETTINGS.md:127-150`).
- **MTP tylko na ≥ 2 GPU** (pipeline). Na jednym GPU MTP jest celowo wyłączone, bo „each token needs mostly different experts” (#43). Wyjątek: APU gfx115x, gdzie wszystko jest rezydentne.

### 3.2 v1.1.14 i okolice (`CHANGELOG.md:7-109`)
- **v1.1.14: Pascal (eksperymentalnie, #212/#214).** Zmiana ma 38 linii:
  - wmma w `mla_attn_tc*` wyłączone poniżej sm_70;
  - `__nanosleep` zastąpione pętlą;
  - **`-Xptxas -dlcm=ca` dla sm_6x** (`CMakeLists.txt:84-98`), bo GP102/GP104 cache'ują loady globalne tylko w L2.

  Profil przed: `mv_kernel_t<14>` (Q6_K) zjadał 51% czasu GPU, „ćwierć z 347 GB/s”. Wyniki: P40 Maya-L 5.8 → 9.9 (×1.7), S24 5.3 → 15.6 (×2.9), 2×P40 S24 9.4 → 28.0 (×3.0). Weryfikacja to 3 prompty greedy ≤ 200 tokenów „identyczne co do znaku”, a SASS sm_70+ jest identyczny.

  **P100 nie był testowany.** Moja ocena `[INFERENCE]`: najpewniej się nie skompiluje, bo kernele dekodu wołają surowe `__dp4a` (`native_mmvq.cu:168`, `iq_kernels.cu:53`, 73 użycia w `glm_fast.cu`), które wymaga CC 6.1. ggml ma fallback poniżej 610 (`~/llama.cpp/ggml/src/ggml-cuda/common.cuh:51,733-738`), Maya nie, a setup przyjmuje CC 6.0 (`maya.py:81-82`).
- **v1.1.14: eksperci Unsloth UD-Q6_K_XL / Q8_0** (typ 8 dodany do kerneli ekspertów, #216).
- v1.1.13: LRU przy jednej rozmowie (3×V100 24.8 → 26.5), tabela hipBLASLt dla ROCm 10, Strix Halo na Windows. **„Answers can differ from v1.1.12.”**
- v1.1.15: EXL3 + DFlash2 (3090 + 8×5060 Ti 71 → 81), AVX-512 VBMI dla IQ2_XXS na CPU (+6–8% na Zen 5), EXL3 na AMD („tests pass on a 7900 XTX”). **„Three default paths now sum in a different order, so tokens differ from v1.1.14”** (`CHANGELOG.md:33-36`).

### 3.3 Weryfikacja deklaracji (`maya.md:66-87`)

| Deklaracja | Arytmetyka | Werdykt |
|---|---|---|
| **81 t/s RTX PRO 6000, Maya-M 116 GB** (#172) | 87% ekspertów w VRAM, 98% trafień. ≈ 9.1 GB/forward × 81 = 737 GB/s = **41% z 1.79 TB/s**. Bez draftowania: DFlash2 przegrał 67.1 vs 79.3 | **Wiarygodne, uczciwe.** To przypadek „prawie wszystko w VRAM”, warstwowanie ekspertów praktycznie nie gra |
| **118 t/s 4×4090** (#89) | 100% ekspertów w VRAM (96 GB), MTP w pipeline na 4 kartach. Najlepszy z kilku przebiegów (110.8–118). Realne obciążenie agentowe: 96.8–98.3 | **Wiarygodne, ale „best-of”** |
| **26–27 t/s, 1×3090** (#157) | EPYC **8-kanałowy DDR4 (111 GB/s)**. CPU lane ≈ 20 z ~37 ms/token. Na desktopie z 2 kanałami pamięci ≈ 17–20 t/s `[INFERENCE]` | **Wiarygodne, ale na sprzęcie klasy stacji roboczej** |
| **30+ t/s RTX 5090** (#43) | Wolny tekst, bez linii benchmarku i bez wersji. Mój sufit: 40–50 t/s. Drugi wiersz z 5090 w README: 23.0 | **Słaby dowód** |
| **„prompts 4–9× faster at 512K on 3090”** (`--kv-streaming`) | Baseline miał 714 slotów ekspertów (~17 na warstwę), więc każdy chunk promptu strumieniował ekspertów od nowa | **Mechanizm prawdziwy, baseline patologiczny, liczba wybrana pod efekt** |
| **„Same answers” z MTP/DFlash2** | Test (#225) wymagał przypiętego podziału i planu CPU. Przy domyślnych ustawieniach **17/70** par restartów dało identyczne tokeny: CPU (ggml Q8_K, blok 256) i GPU (q8_1, blok 32) zaokrąglają inaczej, a routing top-8 to wzmacnia (`SETTINGS.md:187-216`) | **Prawdziwe tylko wąsko.** Brak odpowiednika naszego md5 |
| **„97.7–99.2% of FP8 zero-shot accuracy”, „same next token 83%”** | 5 testów MC × 400 pytań → SE ≈ 2 pp na test, więc S i L są nierozróżnialne. KL liczony tylko po top-64 (dolne ograniczenie), referencją jest FP8, nie BF16. **Maya-S: KL 0.428, top-1 83.3%; L: 0.188 / 90.0%** | **Marketing.** Uczciwa jest tabela KL: S ≈ poziom q2_K (Llama-3-8B q2_K 0.445 / 71%), daleko od q4_K_M (0.031 / 92%) i od naszego kanarka KV q4_0 (0.128 / 85%) |
| **„RX 7900 XT / XTX”** (`docs/AMD_MAYA.md`) | Mierzone na **7900 XT 20 GB**: ~15 → 16.4 t/s (Maya-S), z R9700 ~33. XTX tylko „EXL3 tests pass”. Nasz box (XTX + 64 GB DDR4 2 kanały) → ~8–14 t/s Maya-S24 `[INFERENCE]` | **XTX niezmierzony** |
| `--parallel`: ×1.41 (2 sekw., V100 z RAM), ×2.02 (4 sekw., Gorgon Halo, wszystko w pamięci GPU) | Wszystko rezydentne: ideał ×2.2 (ciało czytane raz), zmierzone ×2.02 | **Wiarygodne.** To zwykłe batchowanie, llama.cpp `-np` robi to samo |

### 3.4 Bezpieczeństwo sprzętu
- **Odczyty z SSD nie zużywają NAND.** Tylko „read disturb” i odświeżanie, pomijalne. Ryzyko to temperatura dysku przy ciągłym odczycie 3–7 GB/s bez radiatora, a Maya jej nie monitoruje `[INFERENCE]`.
- **Zapisy:** slot rozmowy przy każdej zmianie rozmowy. 0.18 GB przy 2K tokenów, ~1.3–1.6 GB przy 100K `[INFERENCE]`, co dla agenta daje ~150–450 GB/dzień `[INFERENCE]`. Na QLC to ma znaczenie (szczegóły tematu w 21d). Wyłącznik: `STRATA_GLM_SLOTS=0`.
- **RAM:** przypina wszystko poza ~6 GB (`README.md:126`). Desktop z trzema monitorami swapował przy 12 GB zapasu (#77).
- **CPU:** podczas dekodu jeden wątek na rdzeń fizyczny kręci się na 100%.
- Podkręt powinien robić odwrotnie: nie zawłaszczać RAM-u, nie zapisywać bez potrzeby, pokazywać temperatury.

### 3.5 Nowe wobec llama.cpp i naszego forka
- **llama.cpp ma od 2026-10-07 `--moe-cache-mib`:** cache LRU ekspertów z RAM na jednym GPU ([PR #29887](https://github.com/ggml-org/llama.cpp/pull/29887), port qvac-fabric). 4090 Flash-Next Q4_0 25.0 → 40.7 t/s, 5090 30.8 → 67.8. Jest to w bazie naszego forka (`~/llama-master/common/arg.cpp:2795`). Niezależne A/B na V100 przez PCIe Gen3 ×4: Strata ~2.4× szybsza niż llama.cpp z tym cache, 1.5× bez MTP (Strata #3082). **Sam „cache ekspertów w VRAM” nie jest już unikalny.**
- Co Maya wciąż ma ponad llama.cpp:
  - CPU lane równolegle z PCIe;
  - warstwa NVMe przez O_DIRECT;
  - rozgrzewka z profilu i budżety slotów per warstwa;
  - promocje w tle, które nie blokują trasy;
  - model kosztów podziału na ≤ 16 różnych GPU;
  - MTP w pipeline na 2 GPU i wniosek, że spekulacja przegrywa na jednym GPU zasilanym z RAM;
  - `--calibrate`.
- **RDNA3:** kernele IQ2_XXS/IQ2_S/IQ3_XXS z „packed sign expansion” są o 26–35% szybsze per kernel, bitowo identyczne. Cały model na 7900 XT: 15.1 → 16.4 (`docs/AMD_EXPERT_KERNELS.md:17-23,90-113`). Ma to znaczenie tylko dla kwantów IQ, nie dla naszego LFM Q5_K_M ani Qwena Q4_K_XL.

---

## 4. Strata: v0.1.44.1 i v0.1.45 (części poza KV na dysku)

Źródła: release notes (`21g-notatki/strata-release-notes-0.1.44.1-0.1.45.md`), commity, `docs/QWEN36.md`, issues/PR. Liczby z gita: v0.1.44 → v0.1.44.1 to 11 commitów; v0.1.44.1 → v0.1.45 to 264 commity, 267 plików, +30 785/−1 289. Autorzy: Niko1221 123 commity bez merge'y, havok2-htwo 29, Rafa 15, libratechw 12…

### 4.1 v0.1.44.1 (2026-10-14): hotfix (`strata-release-notes…:67-77`)
- **Procesory bez AVX2** padały na SIGILL przed pierwszą linią logu: tablica NVFP4 budowana statycznie w plikach kompilowanych z AVX2/AVX-512. Naprawa: tablica liczona w czasie kompilacji. Serwer już nie ponawia startu po sygnale crasha i podaje flagi CPU.
- **CUDA 12.0/12.1:** `__ushort_as_half` w kodzie hosta. Naprawione ręcznym poszerzeniem bitów, sprawdzonym na wszystkich 65 536 wejściach.
- **Apple M2:** `gdn_step` potrzebuje 512 wątków, a kompilator dawał 448, więc warianty wielotokenowe **po cichu się nie uruchamiały** i były śmieciowe wyniki. Teraz każdy dispatch Metal porównuje limit wątków pipeline'u z rozmiarem uruchomienia i zatrzymuje silnik z komunikatem.
- **Lekcja dla nas:** „cichy brak uruchomienia kernela” to klasa błędu, przed którą chroni tylko twarde sprawdzenie przy dispatchu. To analogia do tego, że TensorFold „poisons outputs to catch dispatches that write nothing” (#908).

### 4.2 v0.1.45 (2026-10-17): ścieżka Qwen3.6-35B-A3B
- **Szybszy dekod, bitowo jak stare kernele** (`c9e7f6dd`). Zmiany:
  - Q8_0 shared expert i k/v po jednym warpie na wiersz, z siatką ograniczoną do 1024 warpów („2048 warps took 21 µs, 1024 took 5 µs” na gfx1201);
  - shared gate + up + SwiGLU + q8_1 w jednym launchu;
  - `k_moe_out` na 1024 wątkach + obraz q8_1 następnej warstwy;
  - add + norm + q8_1 w jednym;
  - router top-k + grupowanie w jednym.

  R9700 UD-Q4_K_XL: **82.5 → 120.6 t/s** (commit), w release notes 83.2 → 117.8 (5/5 par; llama.cpp 82). `--mtp 2` 167.7 → 183.7. `STRATA_Q36_VERIFY=1` porównuje stare i nowe kernele na prawdziwych aktywacjach: 0 niezgodności w 18 360 porównaniach (`docs/QWEN36.md:130-142`).

  **To są dokładnie nasze fuzje LFM:** 0049 norma → q8_1, 0051 down + ważenie + residual, 0053 norma + router + top-k, 0056 gate + up → q8_1 (`wiki/kernele/fuzje-lfm-moe.md`). Niezależne potwierdzenie kierunku, dla nas nic nowego.

  Arytmetyka: duże iloczyny Q8_0 (atencja, projekcje GDN, głowica) to 1.9 GB/token (`QWEN36.md:136-137`), plus eksperci Q4_K ≈ 0.6 GB `[INFERENCE]`, razem ≈ 2.5 GB/token. R9700 ma ~640 GB/s ([AMD](https://www.amd.com/en/products/graphics/workstations/radeon-ai-pro/ai-9000-series/amd-radeon-ai-pro-r9700.html)), więc sufit ≈ 256 t/s. 117.8 t/s = **~46% pasma**, llama.cpp 82 = ~32%. Dla porównania nasz LFM na XTX: 52–54%. **Werdykt: wiarygodne.** Wzór „upstream HIP MoE zostawia 30–70%” zgadza się z naszym LFM (upstream 169.3 → fork 289.7 tg128, `BENCHMARKI-PRZED-PO-2026-10-19.md:56`).
- **Prefill GDN** (`6f4697f6`, `55bae973`): delta rule ładuje wejścia tokenu t+1 podczas liczenia t i ma 2 bariery na token zamiast 3. Bitowo identyczne, 913 → 885 ms dla 3000 tokenów przy chunku 512. U nas prefill GDN idzie innym kernelem (chunked), a ten pomysł dotyczy sekwencyjnego skanu, więc dla nas niski priorytet.
- **Domyślny chunk promptu 512 → 4096/2048/1024** (`93f0f48f`, „owner decision”): R9700 pp4096 3390 → 5750 t/s. **Łamie bitową tożsamość** długich promptów (KL 0.004 vs chunk 512). Opisane uczciwie, ale to odstępstwo od ich własnej reguły „wszystko, co zmienia bity, jest opt-in” (`wiki/repo/strata.md`). Ten sam kompromis znamy z LFM `-ub 2048` (`wiki/modele/lfm-czulosc-na-podzial-batcha.md`).
- **Wiele żądań naraz** (`--parallel N`, ≤ 8; `docs/QWEN36.md:65-73`). R9700, 128 tokenów, 5 przeplatanych par:

  | N | Strata | llama.cpp `-np N` | × |
  |---|---|---|---|
  | 1 | 83.9 | 73.8 | 1.14 |
  | 2 | 173.5 | 107.4 | 1.61 |
  | 4 | 252.0 | 165.0 | 1.53 |
  | 8 | 325.4 | 208.1 | 1.56 |

  **Wątpliwość:** wiersz N=1 (83.9) to ścieżka batchowa `--batch 8 --mtp 0`, nie solo 117.8 z tej samej wersji. Skok N=1 → 2 o ×2.07 (nadliniowy) pokazuje, że wiersz N=1 jest upośledzony. Przewaga nad llama.cpp przy N ≥ 2 (×1.5–1.6) jest wiarygodna, bo dzielą wagi i ekspertów, ale porównanie N=1 jest bez sensu.

  `--batch-mtp` (`QWEN36.md:94-99`): N=1 ×1.60, N=2 ×1.20, N=4 ×1.10, N=8 ×0.99 („no row to spare”). Na kartach, które nie mieszczą wszystkich ekspertów, sloty zabierają cache ekspertów: solo −4…−30%, a N razem dają tylko ×0.76–1.15 wobec solo z MTP (`QWEN36.md:113-121`). Uczciwie napisane: „worth it for several users or agents at once, not for one chat”.
- **Przełączniki dla serwerów wielu użytkowników** (#2364; opt-in): 4×R9700 IQ3_S, 16 użytkowników 207 → 324 t/s (×1.56), TTFT p50 20.6 s → 2.0 s (`strata-release-notes…:13-21`). Dla nas nie dotyczy (single-user).
- **PR-y społeczności z deklaracjami prędkości:** zbudowane, sprawdzone na 4 kartach, domyślnie tylko to, co daje te same odpowiedzi (`strata-release-notes…:23-35`).
  - Długie prompty na AMD (#1749, #1943): 131K +8.7%, 500K +79%. Dotyczy rzadkiej atencji QSA Flash-Next, nie naszego modelu.
  - `STRATA_HIP_WMMA=1` na R9700: +44% prompt, opt-in.
  - Seria Volta/Pascal przesunięta na 0.1.46 (−4% na 3060 po długim prompcie).
- **Ślepa uliczka z naszej perspektywy:** KV w ścieżce Qwen3.6 jest **fp32** (45 KB/token, `QWEN36.md:103-104`). PR #3084 proponuje FP16 domyślnie.

### 4.3 Po wydaniu: otwarte issues/PR (2026-10-16…19), wybrane
- **#3064 (bsorensen110, otwarte), bariery „tylko LDS” w kernelach weryfikacji GDN.** Na RDNA3/4 `__syncthreads()` = pełny płot pamięci grupy roboczej, który drenuje loady globalne i unieważnia L0. Zamiana na barierę tylko LDS plus podwójne buforowanie (5 → 3 bariery na token) daje −1.3…−5.0% czasu weryfikacji (R9700, mikrobench 36 warstw, 5 par) przy 100% parytecie bitowym. **Sprawdziłem na gfx1100 (§5.3); przenośne do nas.**
- **#3066: dekod 2× wolniejszy pod frontendami agentowymi** (RTX 3060, Windows). Przy chybieniach ekspertów GPU spada do zegara bazowego 850–900 MHz. `nvidia-smi -lgc 2000,2000` daje 15 → 25 t/s (+60%). To jeden komputer, a przyczyną źródłową jest głód danych z PCIe. **Lekcja produktowa:** Podkręt powinien w trybie pomiaru logować zegar i P-state podczas dekodu. Na XTX odpowiednik to `power_dpm_force_performance_level` / profil COMPUTE, ale go nie mierzyliśmy, więc to tylko `[INFERENCE]`.
- **#2940: domyślny `presence_penalty 1.5` z karty modelu przy thinking off** obciął dekod o ~25% (4×7900 XT, okna 32 → 47 ms: draft i commit przestały się chować). **Lekcja:** penalty w samplerze psuje nakładanie spekulacji. Trzeba sprawdzić, co wysyła omp i co ustawia nasz `run-llm.sh` (raport SamplerFastPath).
- **#3058: tabela hipBLASLt dla gfx1101** (RX 7800 XT): prompt +14 / +52 / +72% przy 1K / 8K / 24K. Strata ma już tabelę dla gfx1100. U nas prefill kwantów idzie przez MMQ, nie hipBLASLt, więc zysk zależy od tego, ile GEMM-ów f16/bf16 przechodzi przez hipBLAS `[INFERENCE: mało]`.
- **#1297 (zamknięty): autotuning na urządzeniu dla gfx1100.** Uczciwy wynik zerowy: „the shipped defaults already win on every IQ3_S shape”. Jedyny zysk dało `--spec-min-p 0.70` (+10%). Kolejne potwierdzenie raportu 02: duże „przed → po” robi praca w labie, nie strojenie u użytkownika (`wiki/research/raport-02-autotuning.md`).
- **Liczby na naszej karcie (konkurencja):**
  - #2938: XTX + Ryzen 9950X + 96 GB DDR5, Flash-Next IQ3_S (83.9 GB), MTP spec 4. Dekod 82.5 t/s przy 1.5K, 77.4 przy 98K, 79.9 przy 260K (1 przebieg); prefill 1809.5 t/s przy 98K. Eksperci w RAM: arena 46.8 GiB.
  - #2828: XTX na Windows, IQ3_XXS: czat 91.1, sesja agentowa 104.8 t/s (68.8% trafień cache).

---

## 5. Szczegóły dwóch pomysłów, które sprawdziłem sam

### 5.1 inferrous: prefetch L2 w „oknach latencyjnych” na NVIDIA
U nich 252 małe kernele zajmują 642 µs na 5755 µs kroku (11%), a prefetch z 16 dodatkowych CTA chowa 80–85% czasu takiego kernela (`round-6.md:15,23`).

U nas na NVIDIA ten udział zależy od modelu `[INFERENCE]`:
- **LFM na 5060 Ti** (448 GB/s): 1.52 GB/token, czyli ≥ 3.4 ms przy 100% pasma; zmierzone 207.86 t/s = 4.81 ms/token (`BENCHMARKI…:99`). Około 1.4 ms/token poza strumieniowaniem wag. Gdyby prefetch odzyskał 30% tego, to ≈ 0.4 ms, czyli **+9%**.
- **Qwen 27B na 5060 Ti:** udział okien latencyjnych dużo mniejszy, ≈ +1–2%.
- **Kill:** na XTX analogiczny „touch” do MALL dał szum. Jeżeli na 5060 Ti nsys pokaże, że kernele latencyjne LFM zajmują < 15% kroku, zamykamy temat.

### 5.2 TensorFold: przełącznik pokrycia słownika draftu (#1011)
Mamy głowicę draftu na 64k tokenach (łatka 0004: 32k +7%, 64k +7.5%, 96k +6%; `wiki/latki/latki-spekulacji.md:14`). Polskie teksty mogą częściej zawierać tokeny spoza 64k. Wtedy draft na pozycji takiego tokenu musi chybić, a potem każdy kolejny draft w łańcuchu też.

Przełącznik „pełna głowica, gdy w ostatnich 16 tokenach jest token spoza podzbioru” kosztuje (0.675 − 0.18) GB ≈ 0.5 ms na poziom draftu, czyli ~2 ms/krok przy n=4 (`tf-delta.md:200`, `[INFERENCE]`, ≈ −7% gdy nic nie zyskuje). Zysk pojawia się tylko wtedy, gdy na takich odcinkach akceptacja rośnie o > 7%.

**Pierwszy test bez GPU:** odsetek 4-tokenowych okien z tokenem spoza 64k na naszych wyjściach PL ze spec_sweep. Kill przy < 5%.

### 5.3 Strata #3064: bariera tylko LDS na gfx1100: sprawdzenie ISA
Kompilacja `hipcc --offload-arch=gfx1100 -O3 --cuda-device-only -S` (AMD clang 23.0.0git), pliki w `21g-notatki/`:
- `__syncthreads()` → `s_waitcnt lgkmcnt(0)` / `s_barrier` / **`buffer_gl0_inv`** (`k.s:27-29`).
- Bariera z płotami `__builtin_amdgcn_fence(__ATOMIC_RELEASE, "workgroup", "local")` + `__builtin_amdgcn_s_barrier()` + `__builtin_amdgcn_fence(__ATOMIC_ACQUIRE, "workgroup", "local")` → `s_waitcnt lgkmcnt(0)` / `s_barrier` (`k2.s:33-34`), **bez `buffer_gl0_inv`**. Load globalny za barierą nie czeka na unieważnienie L0.
- Wersja z płotami „local” jest **poprawna względem modelu pamięci**: kompilator wie, że porządkujemy tylko LDS. Goła `s_barrier` z ręcznym `s_waitcnt` (jak w PR-ze) działa, ale pozwala kompilatorowi przenosić dostępy LDS przez barierę, więc wolę wersję z płotem.
- Gdzie u nas: `fattn-kvq.cu` (5 × `__syncthreads`), `fattn-tile.cuh` (8), `fattn-vec.cuh` (6), `mmq.cuh` (12); `gated_delta_net.cu` (0, same `warp_reduce_sum`) (zliczenia w `~/llama-master/ggml/src/ggml-cuda`, gałąź `amd-opt`). Warunek: między barierami nie ma komunikacji przez pamięć globalną. W fattn/mmq dane przechodzą przez LDS, ale każdą barierę trzeba przejrzeć osobno.

### 5.4 Mapowanie „nowe vs llama.cpp vs nasz fork”: jedna tabela

| Pomysł | Skąd | llama.cpp upstream | Nasz fork |
|---|---|---|---|
| Fuzje MoE (norma + q8_1, router + top-k, gate + up + q8_1, down + residual) | Strata 0.1.45 | nie | **mamy** (0049/0051/0053/0056) |
| Słownik draftu MTP podzbiorem | Strata `--draft-vocab`, TF #1011 | nie | **mamy** (0004, 64k) |
| …z przełącznikiem pokrycia | TF #1011 | nie | **nie**: pomysł 2 |
| PDL | inferrous | **ma** (Hopper+) | XTX: PM4 (16a) |
| Prefetch L2 w oknach latencyjnych | inferrous | nie | XTX: szum (X3); NVIDIA: nie próbowane |
| Bariera tylko LDS (RDNA) | Strata #3064 | nie | **nie**: pomysł 1 |
| Cache ekspertów w VRAM (LRU) | Maya, Strata | **ma** (`--moe-cache-mib`, #29887) | mamy (baza) |
| Rozgrzewka z profilu / CPU lane / NVMe | Maya | nie | nie |
| Wiele slotów z MTP w batchu | Strata `--batch-mtp` | `-np` bez MTP w batchu `[INFERENCE]` | niezmierzone |
| DFlash2 + drzewa | TF (CUDA, Metal) | częściowo | mierzone, przegrywa z MTP na PL/T=1 |
| Bezstratna głowica 12-bit | inferrous | nie | n/d (głowice skwantowane) |

---

## 6. Pomysły do przeniesienia: ranking

Wynik = zysk × pewność / wysiłek. Eksperymenty na GPU tylko za zgodą, kill ustalony przed startem.

| # | Pomysł | Źródło | Wysiłek | Spodziewany zysk (arytmetyka) | Minimalny eksperyment | Kill |
|---|---|---|---|---|---|---|
| 1 | **Bariera tylko LDS** w `fattn-kvq`/`fattn-tile`/`fattn-vec`/`mmq` na gfx11 (makro `GGML_LDS_BARRIER()` z płotami „local”, wyłącznik env) | Strata #3064; ISA §5.3 | S (1–2 dni) | U nich −1.3…−5% czasu kerneli z 3–5 barierami/token. U nas `[INFERENCE]`: kvq attention przy 64k to znaczna część kroku dekodu, więc 1–3% kroku przy długim kontekście; MMQ prefill 0–2%. **Bitowo identyczne** (ta sama arytmetyka) | rocprofv3: czas `fattn-kvq` przy 64k i `mmq` pp4096, A/B wyłącznikiem, 5 par; md5 greedy + logity | < 1% czasu kernela albo jakakolwiek różnica md5 |
| 2 | **Przełącznik pełnej głowicy draftu** przy tokenie spoza 64k w ostatnich 16 | TF #1011 | S–M | PL: tylko jeśli akceptacja na takich odcinkach rośnie o > 7% (koszt ≈ 2 ms/krok, §5.2) | CPU: pokrycie 64k na wyjściach PL ze spec_sweep; potem ABBABA na GPU | < 5% okien z tokenem spoza 64k; albo PL t/s < +3% |
| 3 | **Wiele slotów dla równoległych agentów omp** (LFM i Qwen, `llama-server -np 2/4`) | Strata `--parallel`, Maya ×2.02 | S (pomiar); M–L (MTP w batchu) | Wszystko rezydentne: wagi czytane raz, ideał ×(1.5–2) łącznej przepustowości dla 2–4 agentów. Koszt: KV × N, solo −x% | Replay 2–4 równoległych sesji omp: łączne t/s i solo t/s vs `-np 1` | Łącznie < ×1.2 przy N=2 albo solo < −5% |
| 4 | **LFM na 12 GB NVIDIA: `--moe-cache-mib` + rozgrzewka z profilu + auto-off MTP przy ekspertach z RAM** | Maya (`SETTINGS.md:127-150`), PR #29887 | S–M | LFM Q4_K_M 14.5 GB nie mieści się w 3060 12 GB. Rozgrzewka u Mai: +15% na świeżym starcie, a to ważne dla krótkiego pomiaru „po”. Auto-off MTP chroni przed −15…−30% (Maya #157, #172) | 3060: tg pierwszych 256 tokenów + trafienia z rozgrzewką i bez; MTP on/off przy cache 25/50/75% | < 5% na pierwszej odpowiedzi; MTP nigdy nie przegrywa |
| 5 | **Prefetch L2 w oknach latencyjnych (sm_120)** dla LFM na 5060 Ti | inferrous runda 6 | M (CUDA) | ≈ +9% `[INFERENCE]` (§5.1) | nsys: udział kerneli latencyjnych w kroku LFM | < 15% kroku |
| 6 | **Autotuning na różnych macierzach** (IC 96 MB na XTX myli pomiar powtarzanej macierzy) | TF 1.1.0 Metal | S | 1–3% `[INFERENCE]` | Ponowny pomiar strojonych kształtów rotacją macierzy wszystkich warstw | Te same zwycięskie konfiguracje |
| 7 | **md5-baseline per wersja ROCm/hipcc i CUDA** | TF #945 | S | 0% prędkości. Chroni deklarację „bit-exact” przed aktualizacją ROCm u użytkownika | 2 wersje ROCm w CI | — |
| 8 | Pierwszy token przed draftami | TF #932 | S | TTFT −1 poziom draftu (kilka ms) | TTFT z MTP i bez | Δ < 5 ms |
| 9 | `-Xptxas -dlcm=ca` dla sm_6x | Maya v1.1.14 | XS | Tylko jeśli Pascal wejdzie do zakresu (dziś nie ma go na liście MVP) | tg128 na wynajętym P40 | < 3% |
| 10 | Lekcje treningu głowicy draftu: PL w każdym batchu, KL 0.8^j, MoE głębokość ≤ 2 | TF `training-a-drafter.md` | S (config w `~/qwen-opt/mtp-train`) | +0.05…0.075 zaakceptowanych tokenów na rundę (ich dane) | Jedno ramię treningu vs obecny przepis | < +0.05 na PL |

**Odrzucone** (z powodem):
- bezstratna głowica 12-bit (nasze głowice są skwantowane);
- PDL na NVIDIA (upstream ma);
- port DFlash2 jako „nowość” (zmierzony, przegrywa na PL/T=1; temat 21a);
- warstwa NVMe ekspertów (dopiero gdy pozycja 4 pokaże sens; dziś modele mieszczą się w VRAM+RAM);
- przybliżenia Mai (`MISS_SKIP` itd., stratne);
- przełączniki wielu użytkowników Straty;
- LoRA fold TF;
- tabela hipBLASLt (nasz prefill idzie przez MMQ).

---

## 7. Notatki o konkurencji dla Podkręta

### 7.1 Kto co obiecuje

| | TensorFold 1.1.0 / Beta 8 | Maya 1.1.15 | Strata 0.1.45 | inferrous |
|---|---|---|---|---|
| Obietnica | „Run LLMs fast on the GPUs you own”, Mac + NVIDIA, agent-asystent | „321B model na Twoim GPU” | „Flash-Next na dowolnym sprzęcie”, jeden klik | badania |
| AMD | **HIP zamrożony**, drafter ignorowany, ROCm odrzucany na tablicy | eksperymentalnie, XTX niezmierzony | **tak**, w tym XTX (społeczność) | nie |
| Format | MLX 4-bit (nie GGUF) | własne kwanty GLM, EXL3 | GGUF wybranych modeli | własny bundle |
| Bit-exact domyślnie | w obrębie wydania | **nie** (17/70) | tak dla Flash-Next; Qwen3.6 chunk zmienia bity | wobec siebie |
| Porównanie z llama.cpp | brak | brak | **tak** (A/B przeplatane, np. `-np`) | brak (tylko vLLM) |
| Pętla społeczności | tablica + paragony | `--bench` → `--report` → issue → README | `strata_bench` → issue → `COMMUNITY_BENCHMARKS.md` | brak |
| Polski | maszynowy | brak | brak (jest PR z arabskim, #1152) | — |

### 7.2 Zagrożenia
1. **NVIDIA:** TF 27B CUDA + DFlash2 po przeliczeniu na pasmo ≈ 141 chat / 196 code t/s na XTX-ekwiwalencie, nasze 103–130 (§2.3). **Zanim ogłosimy przewagę „przed → po” na NVIDIA:** przeplatane A/B na wynajętej 3090 (TF 1.1.0 vs nasz fork) na spec_sweep PL/EN + copy/code-edit. Koszt chmury ≈ $1–2 `[INFERENCE]`. Nasza karta przetargowa to lookup tail ×2.4 na code-edit, której TF nie ma.
2. **Duże MoE z RAM na naszej karcie:** Strata Flash-Next 125B na XTX ≈ 80 t/s przy 96 GB RAM (#2938). Użytkownik z dużym RAM-em może woleć większy model. Podkręt powinien w rekomendacji uczciwie pokazać tę alternatywę albo wesprzeć ten scenariusz (pozycja 4).
3. **Tempo:** TF ~400 commitów/dzień (AI), Maya 51 wydań w 10 dni, Strata ~260 commitów/wydanie. W 1.1.1 TF zapowiada PR-y od ThinkOffApp na HIP (#1001), więc trzeba ponownie sprawdzić „HIP ignoruje `--drafter`” i tablicę ROCm.

### 7.3 Co skopiować do produktu
- **Przełącznik „bez przyspieszenia”** w aplikacji (TF „Serial baseline”). U nas jako „przed → po” wobec *tuned upstream llama.cpp* na tych samych promptach, z md5/KLD. Ich test to tylko spec on/off.
- **Paragon ze ścisłym schematem:** rewizja checkpointu, sha configu, wersja silnika, bez promptów i wyjść, przeliczany po stronie serwera, niepełne komórki nigdy w agregacie (TF). Plus przycisk „Udostępnij wynik” → gotowy tekst issue (Maya `--report`).
- **Profile per model** (mały/duży kontekst) i **porównanie dwóch modeli** na jednym prompcie (TF).
- **Kuratorska lista + preflight z modelem zapasowym** (TF), u nas dodatkowo przewidywane t/s z rooflinu, a potem zmierzone.
- **API Anthropic** (`/v1/messages`): mają je TF, Maya i Strata. Dla użytkowników Claude Code to warunek wejścia.
- **Kalibracja, która zostawia funkcję tylko tam, gdzie wygrywa** (Maya: DFlash2 i MTP per maszyna), z przeplotem i progiem > 3%.
- **Kontrola zegara / P-state GPU** podczas pomiaru i serwowania (Strata #3066) oraz **ostrzeżenie o penalty w samplerze** (Strata #2940).
- **Polski natywny:** „Nie udało się …”, odmiana liczebników, wzorzec „Etykieta: {count}” tam, gdzie nie chcemy odmieniać (TF), i żadnego angielskiego w onboardingu.

### 7.4 Na czym się wyróżnić
- **AMD natywnie:** jedyny poważny gracz z kernelami pod RDNA3 dla *dowolnego* GGUF.
- **Bit-exact domyślnie + tryb szybki z bramką KLD**, stabilne między wydaniami.
- **Porównanie z tuned upstream**, którego nie robi nikt poza Stratą.
- **Gotowe binarki:** Maya buduje 20–40 min ze źródeł.
- **Nie zawłaszczamy RAM-u** (Maya przypina wszystko poza 6 GB).
- **Wieloklasowy benchmark PL+EN** (nowy tekst vs kopia/edycja), przeplatany. TF ma jeden angielski prompt na klasę, a kodem jest Fibonacci.

---

## 8. Źródła (zbiorczo)
- inferrous:
  - https://github.com/bitemyapp/inferrous (`405bfd3`);
  - `docs/qwen3-8b-w8a8/benchmarks.md`, `optimization/round-3.md`, `optimization/round-6.md`, `discrepancies.md`;
  - `docs/plans/qwen3.6-35b-a3b-fp8.md`, `docs/migrations/cuda-rust.md`;
  - `crates/inferrous-qwen3/src/kernels.rs`;
  - llm-tracker RTX PRO 6000: https://llm-tracker.info/RTX-PRO-6000.
- TensorFold:
  - https://github.com/ashhart/TensorFold/releases/tag/v1.1.0, /tag/v1.0.0-beta.8, /tag/v1.0.0-beta.7;
  - issues/PR #610, #710, #836, #918, #932, #945, #1001, #1011;
  - https://tensorfold.dev/, `/api/benchmarks/v1/results?limit=50` (zrzut w `21g-notatki/tensorfold-board-2026-10-19.json`);
  - `app/src/lib/preferences/packs/pl/*.json`, `app/src/lib/model-recommendation.ts`;
  - pełna lista: `21g-notatki/tf-delta.md`.
- Maya:
  - https://github.com/mw00/project-maya (`a4e1ff0`);
  - `CHANGELOG.md:7-109`, `README.md`, `docs/SETTINGS.md`, `docs/AMD_MAYA.md`, `docs/AMD_EXPERT_KERNELS.md`, `CMakeLists.txt:84-98`;
  - issues #43, #77, #89, #157, #172, #212, #214, #225;
  - pełna lista: `21g-notatki/maya.md`.
- Strata:
  - https://github.com/Niko1221/Strata/releases/tag/v0.1.45, /tag/v0.1.44.1;
  - commity `c9e7f6dd`, `6f4697f6`, `55bae973`, `93f0f48f`;
  - `docs/QWEN36.md:65-142`;
  - issues/PR #1297, #2828, #2938, #2940, #3058, #3064, #3066, #3082, #3084;
  - API releases: https://api.github.com/repos/Niko1221/Strata/releases.
- llama.cpp:
  - https://github.com/ggml-org/llama.cpp/pull/29887;
  - `~/llama-master/common/arg.cpp:2795`, `~/llama-master/ggml/src/ggml-cuda/common.cuh:124-142`.
- Nasze:
  - `BENCHMARKI-PRZED-PO-2026-10-19.md:25,33,56,99`;
  - `wiki/kernele/fuzje-lfm-moe.md`, `wiki/latki/latki-spekulacji.md:14`, `wiki/modele/drafter-dflash.md`;
  - `wiki/lekcje/lekcja-prefetch-mall-xtx.md`, `wiki/rocm/hip-dyn-data-prefetch.md`.
- ISA: `21g-notatki/k.hip`, `k.s:27-29`, `k2.hip`, `k2.s:33-34`.

---

## Do bazy wiedzy

| Folder | Tytuł | Kluczowe liczby (źródło) |
|---|---|---|
| `repo/` (nowa) | inferrous (bitemyapp) | Qwen3-8B W8A8, RTX PRO 6000 Max-Q: 182.3 / 178.2 / 170.5 t/s vs vLLM Humming 144.4 / 143.3 / 142.9 (`benchmarks.md:11-15`); 7.88 GB/krok, 84% z 1.71 TB/s (`round-6.md:17`); 31 kerneli w Ruście, dekod DP4A; bramka Torch nie przechodzi, rel. L2 logitów 9–11% (`discrepancies.md:7`); głowica 12-bit = 75.8% bajtów (`round-3.md:24`); runda 6 prefetch + PDL +6.5…7.8% (`round-6.md:73`); brak llama.cpp w porównaniu. Werdykt: brak dla produktu |
| `repo/tensorfold.md` (aktualizacja) | TensorFold 1.1.0 + Beta 7/8 | 901 commitów od 1.0.12, HIP +12/−9 bez zmian funkcjonalnych (`tf-delta.md:11-19`); `--drafter` ignorowany na HIP (#1001); 27B CUDA DFlash2: 5090 chat T0 263.0 / code T0 366.8, PRO 4500 142.4 / 198.5 (tablica, `tensorfold-board-2026-10-19.json`); 874 t/s na stronie = Lightning, prompt Fibonacci, wydanie 1.0.6; tablica 45 przebiegów, 0 AMD, 0 serial-baseline; przełącznik pokrycia słownika draftu #1011 (+5…17% EN/kod, 0% inne języki); LoRA fold zachowuje 0.1% efektu (#710); aplikacja tylko Mac, 14 języków, polski maszynowy |
| `repo/` (nowa) | Project Maya (mw00) | GLM-5.3-Flash 321B/18B, pochodna Straty; 3 warstwy ekspertów VRAM / RAM / NVMe (O_DIRECT); 81 t/s RTX PRO 6000 = 41% BW (#172); KL Maya-S 0.428 / top-1 83.3%, L 0.188 / 90.0% (`bench/results/MAYA-*.md`); domyślnie deterministyczne tylko 17/70 restartów (`SETTINGS.md:187-216`); Pascal v1.1.14: `-dlcm=ca`, P40 ×1.7–3.0 (#212); P100 prawdopodobnie się nie kompiluje (`__dp4a`) `[INFERENCE]`; przypina RAM poza 6 GB |
| `repo/strata.md` (aktualizacja) | Strata 0.1.44.1–0.1.45 (bez KV) | Brak 0.2.0 (API, 2026-10-19); Qwen3.6-35B-A3B R9700 dekod 83.2 → 117.8 (llama.cpp 82), bitowo (`c9e7f6dd`, release notes); fuzje = nasze 0049/0051/0053/0056; `--parallel` vs `-np`: ×1.14 / 1.61 / 1.53 / 1.56 dla N = 1 / 2 / 4 / 8 (`QWEN36.md:68-73`; N=1 to ścieżka batchowa); domyślny chunk 4096 zmienia bity (KL 0.004); XTX Flash-Next 125B ≈ 80 t/s, prefill 1810 t/s przy 98K (#2938) |
| `kernele/` (nowa) | Bariera tylko LDS na RDNA3 | `__syncthreads` → `s_waitcnt lgkmcnt(0); s_barrier; buffer_gl0_inv`; z `__builtin_amdgcn_fence(…,"workgroup","local")` bez `buffer_gl0_inv` (`21g-notatki/k.s:27-29`, `k2.s:33-34`); Strata #3064: −1.3…−5% weryfikacji GDN na R9700, bitowo; kandydaci u nas: fattn-kvq 5, fattn-tile 8, fattn-vec 6, mmq 12 barier; GDN 0 |
| `lekcje/` (nowa) | Bit-exact wobec siebie ≠ wierność | inferrous: wszystkie hashe zachowane, a bramka Torch nie przechodzi (rel. L2 9–11%); Maya: „same answers” tylko przy przypiętym stanie warstw (17/70) — dlatego md5 zawsze w parze z KLD wobec upstream/referencji |
| `research/` (nowa) | Raport 21g — nowe silniki | Ranking: 1) bariera LDS-only, 2) przełącznik pokrycia słownika draftu PL, 3) wiele slotów dla agentów omp, 4) LFM 12 GB: moe-cache + rozgrzewka z profilu + auto-off MTP, 5) prefetch L2 sm_120 (LFM 5060 Ti ≈ +9% `[INFERENCE]`); konkurencja: TF AMD zamrożone, NVIDIA 27B DFlash2 wymaga A/B na 3090; Strata Flash-Next na XTX |
| `ludzie-firmy/` lub `produkt/` | Llama.cpp `--moe-cache-mib` | PR #29887 scalony 2026-10-07, port qvac-fabric; 4090 Flash-Next Q4_0 25.0 → 40.7 t/s, 5090 30.8 → 67.8; w bazie forka (`~/llama-master/common/arg.cpp:2795`); Strata vs llama.cpp z cache na V100 (PCIe Gen3 ×4): ~2.4× (#3082) |
