# 39c. „DeepSeek V4.1 Flash: praktyka wdrożenia inferencji na dużą skalę” (Zhihu): delta wobec 32b i co z tego bierzemy

Data: 2026-10-20. Autor: podagent Res39cDeepSeekDeploy. Tylko CPU (vocab-only, build `~/wt/topka/build-cpu`, gałąź `safe-special` `b659634fd`; wyłączony przełącznik daje bajt w bajt `9056cea22`), `nice -n 19`, bez GPU.

Źródła:
- artykuł: tłumaczenie wklejone przez użytkownika (oryginał https://zhuanlan.zhihu.com/p/2095560295930508953 zwraca 403 dla automatu; wpis https://x.com/latentspacepod/status/2112588380416647205 to tylko udostępnienie, X blokuje odczyt). Wklejka ma ucięte akapity (`…`), m.in. liczbę „+6% online” dla DSpark, więc tej liczby nie da się sprawdzić w tekście;
- kod: `deepseek-ai/deepseek-recipe` `935817c` i `deepseek-ai/DeepInfer` `774ce24` (płytkie klony z 32b w `/tmp/res-deepinfer/`);
- llama.cpp upstream: PR #29307 „chat : implement token aware parsing” (otwarty, aldehir, head `2f910999a`, 2026-09-28) i scalony do topki #29876 (`18b5f8b18`).

Narzędzia i surowe wyniki: `~/qwen-opt/dsdeploy/` (`segbench.cpp`, `parsebench.cpp`, `plainmarker.cpp`, `grammarbench.cpp` + logi `*.txt`). Odnośniki `R:` = recipe, `T:` = topka (`~/wt/topka`), `[INFERENCE]` = mój szacunek, niezmierzony.

**Co już było w KB (nie powtarzam):** 32b (kod DeepInfer: DSpark z bigramem Markowa i głowicą pewności, varlen −1.5% przy 16 seq/rank, ZOS, SWA bounded replay stratny, batch-invariance, wstrzykiwanie tokenów specjalnych), 32e (`LLAMA_SERVER_SAFE_SPECIAL`), 24i (`LLAMA_SERVER_TOK_CACHE`, render 63 ms przy 91k), 35 E2 (checkpointy GDN w TTFT), 36 (budżet kroku). Nowe w artykule wobec 32b to głównie część „DeepSeek Recipe” (tokenizer, parser strumieniowy) i opis KVCache Storage. Reszta to klaster (LB, autoskalowanie, 3FS).

## TL;DR

1. **Największa rzecz z artykułu to bezpieczeństwo, nie prędkość. Parser wyjścia topki działa na tekście, więc znacznik złożony ze zwykłych tokenów działa jak prawdziwy. Potwierdzone na CPU na Qwen3.8.**
   - Model pisze w treści przykład formatu `<tool_call>…<function=bash>…rm -rf build…` zwykłymi tokenami (np. tłumacząc format albo cytując dokumentację). Serwer zwraca wtedy **prawdziwe wywołanie narzędzia `bash {"command":"rm -rf build"}`**.
   - Dosłowne `</think>` w rozumowaniu (np. rozmowa o szablonach) ucina `reasoning_content`. Reszta, razem z prawdziwym `</think>`, trafia do `content`. To samo dzieje się na LFM2.5.
   - Recipe dopasowuje znaczniki z rodzajem tokenu (`R: output_parser.rs:366-373`). Upstream ma na to gotowy, otwarty PR #29307, a jego fundament (#29876) jest już w topce.
   - To lustrzane odbicie dziury z 32e/SAFE_SPECIAL po stronie wyjścia. Jest bezstratne: tekst generacji się nie zmienia, zmienia się tylko jego klasyfikacja.
2. **Segmentowa tokenizacja jest dokładna i daje −55 ms TTFT przy 91k. Ponad recipe dokładam bezpieczne cięcie dużych segmentów.**
   - Wynik jest bitowo identyczny na **148/148 prawdziwych promptach omp** (Qwen3.8 i LFM2.5, 8–158k).
   - Czasy przy 8 wątkach: 91k **64.8 → 9.6 ms**, 158k **121.9 → 17.6 ms**, 32k 29.5 → 4.7 ms.
   - Sama segmentacja recipe (równolegle tylko po segmentach między tokenami specjalnymi) zatrzymuje się na prawie Amdahla. Największy segment (system prompt / definicje narzędzi, 14–30 KiB) to 5–34% promptu Qwena i 7–64% promptu LFM. Dlatego przy 14k zostaje 4.6 ms, a z cięciem segmentów na granicach pre-tokenizera 2.2 ms.
   - Topka dziś tokenizuje cały prompt w **każdej** turze: `TOK_CACHE` nie jest włączony w `run-topka.sh` i nie działa z zakresami SAFE (32e). Zysk dotyczy więc każdej tury agenta: ~4% TTFT ciepłej tury przy 91k [INFERENCE]. Na zimnym prompcie to 0.05% (prefill ~119 s).
3. **Strumieniowy parser z KMP nic nam nie da na prędkości.** Topka parsuje cały wygenerowany tekst przy każdym tokenie (O(n²)): 0.07 → 0.52 ms/token przy 1k → 12.8k tokenów, łącznie 3.5 s CPU na 12.8k-tokenowe wywołanie `write`. Dzieje się to jednak w wątku HTTP (`T: server-queue.cpp:631`), równolegle do pętli GPU. Opóźnienie strumienia pojawiłoby się dopiero przy ~750 KB wyjścia [INFERENCE]. Buforowanie UTF-8 już mamy (`T: server-context.cpp:2008`).
4. **DSpark, ZOS i structured output: brak delty wobec 32b.** Przy c=1 na naszym budżecie kroku:
   - Wyrocznia długości weryfikacji (DSpark idealny) ma sufit **+13.7%**, ale realny kontroler to +0.1% (E5/L2) do +3% (symulacja 24q).
   - ZOS to dalej L11: sufit +1.4%.
   - Gramatyka narzędzi w llama.cpp kosztuje 3–4 µs/token i 0.17 ms kompilacji, więc maska à la xgrammar niczego nie wnosi.
5. **KVCache Storage: główną mechanikę już mamy, a zostają dwa drobne pomysły.**
   - „L − 134” i snapshoty co 128 tokenów to nasze checkpointy `n−4−ub`/`n−4` oraz checkpointy na początkach wiadomości użytkownika (`T: server-context.cpp:4055-4084`).
   - Pierwszy pomysł: chronić checkpoint końca system promptu przed ewikcją „najstarszy pierwszy” (`T: server-context.cpp:2573-2581`). Działa tylko przy >32 checkpointach na slot, więc najpierw pomiar.
   - Drugi pomysł: nakładać H2D warstwami dopiero **po** przejściu na pamięć przypiętą. Restore 2.3 GB przy pageable 2.1 GB/s trwa 1.1 s, a przy przypiętej szacuję ~0.1 s [INFERENCE].
   - Decyzja „KV tylko w RAM” niczego tu nie blokuje.

## Tabela twierdzeń artykułu

| # | twierdzenie (artykuł) | werdykt | dowód |
|---|---|---|---|
| 1 | Segmenty zwykłego tekstu między tokenami specjalnymi można kodować BPE niezależnie i równolegle | **potwierdzone, trywialnie dokładne** | HF i llama.cpp już wydzielają tokeny dodane przed BPE (`T: llama-vocab.cpp:3589`, pętla po fragmentach `:3662-3677`), więc zmienia się tylko kolejność pracy. Pomiar: 148/148 promptów identycznych (`segbench`, A) |
| 2 | …i to skraca latencję długich promptów | **potwierdzone, z zastrzeżeniem Amdahla** | recipe równolegli tylko po segmentach (`R: tokenizer.rs:93-103`, `encode_batch_fast`). Na promptach omp największy segment to 5–34% bajtów (Qwen), więc przy 14k: 12.2 → 4.6 ms (A8) zamiast 2.2 ms (B8, cięcie segmentów) |
| 3 | Znaczniki w treści (`<｜User｜>` itd.) są kodowane jako zwykły tekst | **potwierdzone** (32b/32e) | `R: tokenizer.rs:36-117`, u nas `LLAMA_SERVER_SAFE_SPECIAL` |
| 4 | Wyjście: `</think>`/DSML rozpoznawane po ID tokenu, a ten sam tekst ze zwykłych tokenów zostaje treścią | **potwierdzone w kodzie recipe; u nas brak** | `R: output_parser.rs:366-373` (`ChunkKind::PlainTokens` dopasowuje tylko bajty niespecjalne). Topka: `plainmarker` pokazuje fałszywy koniec rozumowania i fałszywy tool call (§2.2). PR #29307 otwarty |
| 5 | Parser strumieniowy: bufor UTF-8 między chunkami, KMP, brak ponownego skanowania | **potwierdzone w kodzie** | `R: decoder.rs:11-23,147-204`, `output_parser.rs:603-651,704-770`. llama.cpp ma bufor UTF-8, ale parsuje wszystko od nowa (`T: server-task.cpp:167-177`) |
| 6 | Argumenty narzędzi strumieniowane bez budowania pełnych obiektów | **potwierdzone (recipe)**; funkcjonalnie llama.cpp też strumieniuje delty | `parsebench`: 11 843 delty na 12 839 tokenów, ale co token buduje pełny `common_chat_msg` i robi diff |
| 7 | DSpark: bias low-rank od poprzedniego tokenu, głowica pewności, varlen | **potwierdzone (32b)**; „+6% online” ucięte we wklejce | 32b: `dflash.py:310-312`, `mtp_varlen.hpp:146-271`; Q&A: −1.5% (16 seq/rank) … +5.4% (60) |
| 8 | ZOS: GPU nie stoi podczas schedule/post-process | **potwierdzone (32b)** | `compute_seqlens_k_zos.py:10-30` |
| 9 | KV: bloki 128 tok., dopasowanie łańcuchem hashy, TTL 3 d (agent) / 7 d (czat), 3 d obniża trafienia czatu o 0.5–1% | **deklaratywne, niesprawdzalne** (kodu KV brak, README:38-43) | – |
| 10 | Na ścieżce krytycznej tylko metadane, KV przenoszone async do shm, H2D warstwami | **deklaratywne** | brak kodu. U nas restore z `--cache-ram` to synchroniczna kopia pageable ~2.1 GB/s (16f E4) |
| 11 | SWA: pierścień 134 = okno 128 + cofnięcie spekulacji 6; trafienie ≤ L−134; zapis co 128 tok. z kopią w VRAM podczas dekodu | **spójne z kodem DeepInfer** (`cache_engine.py:88-94`, 32b) | nasze odpowiedniki: `n_rs_seq`, checkpoint `n−4−ub`, CkptVram |
| 12 | SWA KV: TTL ~180 s, trafienia > 98% | **deklaratywne** | – |
| 13 | SO kompilowane asynchronicznie na osobnej maszynie | **potwierdzone (xgrammar w DeepInfer, 32b)**; u nas zbędne | `grammarbench`: gramatyka omp 9.3 KB, kompilacja 0.17 ms |
| 14 | 155 bln tokenów/dzień na klaster, 38 $/kartę/h | **niesprawdzalne**, nie dotyczy | – |

## 1. Tokenizacja segmentowa: dokładność i zysk

### 1.1 Warunki dokładności (BPE z pre-tokenizerem regex)

BPE nie łączy merge'ami przez granice pre-tokenów. Cięcie tekstu w punkcie p jest więc dokładne, gdy (a) żaden pre-token pełnego tekstu nie przecina p i (b) podział lewej części nie zależy od tego, co leży za p. Regexy też muszą to zapewniać: żadnego lookbehindu ani lookaheadu przez p.

- **Granice tokenów specjalnych (wariant A, jak recipe):** zawsze dokładne, bo llama.cpp i HF tną na tokenach dodanych **przed** regexem. Jedyny warunek: segmentacja musi powtarzać `tokenizer_st_partition` (najdłuższe najpierw, od lewej) i atrybuty LSTRIP/RSTRIP. W naszych słownikach żaden token specjalny nie zmienia otoczenia (wynik A identyczny na 148/148).
- **Cięcie wnętrza segmentu (wariant B, nasze):** regex Qwen3.8 (`qwen35`, `T: llama-vocab.cpp:392-397`) i LFM2.5 (`lfm2` → `LLAMA3` z `ignore_merges`, `:2297-2300`):
  - **reguła 1:** `\n` + litera ASCII. `[^\r\n\p{L}\p{N}]?\p{L}+` nie może zacząć się od `\n`, a wszystkie gałęzie, które mogą zawierać `\n` (`\s*[\r\n]+`, `…[\r\n]*`, `\s+`), kończą się przed literą. `\s*[\r\n]+` stoi w alternacji przed `\s+(?!\S)`, więc lookahead nie ma znaczenia;
  - **reguła 2:** litera + spacja + litera, cięcie przed spacją. Ciąg liter kończy się na spacji, a ` abc` zaczyna nowy pre-token w obu kontekstach;
  - `ignore_merges` w LLAMA3 działa per pre-token, więc niczego nie zmienia;
  - reguły są sprawdzone tylko dla `qwen2`/`qwen35`/`llama3`. Inne pre-typy wymagają osobnej analizy, a SPM/UGM (Gemma itp.) odpadają.

### 1.2 Pomiar (`segbench`, 1 vs N wątków, best of 3, `bodies_huge.jsonl` 13 promptów + `bodies_w13.jsonl` 61 tur, Ryzen 7 5700X 8C/16T)

Dokładność: **A i B = pełna tokenizacja `common_tokenize(…, true, true)` na 74/74 promptach Qwen3.8 i 74/74 LFM2.5** (`huge-*-r2.txt`, `w13-*-r2.txt`: „mismatches A=0 B=0”; B przy `SB_CHUNK=2048 SB_RULE2=1`). Po drodze była jedna pułapka: LFM dokleja BOS (`add_bos`), więc konkatenacja musi go dodać, tak jak robi to `add_special`.

| prompt Qwen3.8 (tokeny) | największy segment | dziś (1 wątek) | A8 (recipe) | B8 (+cięcie) | B16 | zysk B8 |
|---|---|---|---|---|---|---|
| 14 017 | 14 KiB (34%) | 12.2 ms | 4.6 | **2.2** | 1.9 | −10 ms |
| 32 873 | 19 KiB (18%) | 29.5 | 6.6 | **4.7** | 3.9 | −25 ms |
| 56 297 | 30 KiB (20%) | 40.3 | 8.0 | **6.3** | 5.1 | −34 ms |
| 91 005 | 22 KiB (9%) | 64.8 | 9.6 | **9.6** | 8.1 | **−55 ms** |
| 158 287 | 22 KiB (5%) | 121.9 | 17.4 | **17.6** | 15.1 | **−104 ms** |
| 200k (ekstrapolacja 0.77 µs/tok) | – | ~154 | – | ~22 | – | **~−132 ms** [INFERENCE] |

LFM2.5 (84.6k): 34.9–47.6 (szum obciążenia) → 6.8 ms. Własne cięcie na tokenach specjalnych kosztuje 0.35 ms przy 91k. W pomiarze wątki są tworzone przy każdym wywołaniu (16 × std::thread), więc stała pula da trochę mniej.

### 1.3 Co to znaczy dla TTFT

- Tokenizacja biegnie w wątku HTTP przed kolejką (`handle_completions_impl`, 32e), więc jest szeregowo w TTFT.
- **Zimny prompt:** 91k × 766 t/s ≈ 119 s prefillu, więc −55 ms to 0.05%. Pomijalne.
- **Ciepła tura agenta** (trafienie w cache, sufiks ~600 tokenów):
  - dziś 0.5–1.2 s `prompt_ms` przy 8k (35 E2), przy 91k zakładam ~1.2–1.5 s [INFERENCE];
  - do tego render 63 ms + tokenizacja 65 ms = 128 ms hosta, czyli ~9% tury;
  - −55 ms to **~4% TTFT tury**, a po poprawkach E2 (−0.3…−0.45 s) ~5–6%.
- **Razem z natywnym rendererem ChatML (32b nr 3)** host przy 91k schodzi ze 128 do ~12 ms, czyli **−116 ms na turę**.
- Alternatywa `TOK_CACHE` (24i) daje 0.5–2.5 ms na turę, ale nie działa z zakresami SAFE i nie pomaga przy zmianie sesji. Segmentacja działa zawsze i z SAFE.
- Najlepsze połączenie [INFERENCE]: memo tokenów per fragment (hash bajtów fragmentu → tokeny). Jest dokładne, bo tokenizacja fragmentu to czysta funkcja jego bajtów. Kolejne tury schodzą wtedy do ~1 ms także z SAFE.

**Gdzie wdrożyć:** `llama_vocab::impl::tokenize`, gałąź BPE (`T: llama-vocab.cpp:3644-3683`):
- po `tokenizer_st_partition` (zakresy SAFE bez zmian) fragmenty > 8 KiB cięte regułami 1–2, tylko dla pre-typów `QWEN2`/`QWEN35`/`LLAMA3`;
- tokenizacja na statycznej puli wątków, każdy z własnym `llm_tokenizer_bpe_session`, potem konkatenacja;
- próg ≥ 64 KiB tekstu;
- przełącznik `LLAMA_TOKENIZE_THREADS` (0 = wył.).

Działa dla Qwena, LFM, CUDA i Maca jednakowo, bo to CPU.

## 2. Parser wyjścia

### 2.1 Koszt (`parsebench`: prawdziwy szablon i parser PEG serwera, `chat_format peg-native`, tokeny Qwen3.8 jeden po drugim, `common_chat_parse(is_partial)` + `compute_diffs` jak w `update_chat_msg`)

| wyjście | tokeny | ostatni parse | łącznie CPU |
|---|---|---|---|
| rozumowanie 2.6 KB + `write` z argumentem 41.7 KB | 12 839 | 0.52 ms/token | 3.49 s |
| rozumowanie + proza 43.8 KB | 13 804 | 0.34 ms/token | 2.59 s |
| ta sama proza, LFM2.5 | 13 804 | 0.36 ms/token | 2.70 s |

- Koszt jest liniowy w długości (~12 ns/B na token), czyli O(n²) na odpowiedź.
- Biegnie w `server_res_generator` (wątek HTTP, `T: server-queue.cpp:631`), nie w pętli dekodu. **Wpływ na t/s: 0** [INFERENCE: 8 rdzeni, `-np 1`].
- Strumień zacząłby się opóźniać, gdy parse > odstęp tokenów (~9 ms przy 3 tokenach na 27 ms krok), czyli przy ~750 KB wyjścia.
- Przepisanie na KMP/inkrementalnie da tylko ~3 s CPU na bardzo długą odpowiedź. **Nie robić dla prędkości.**

### 2.2 Luka poprawności (`plainmarker`, prawdziwy parser serwera, tokeny „zwykłe” z `llama_tokenize_plain_ranges`, żeby nic nie było tokenem specjalnym)

| przypadek (Qwen3.8-27B, omp `b0.jsonl`) | wynik topki | poprawny wynik (recipe/PR #29307) |
|---|---|---|
| rozumowanie zawiera dosłowne `</think>` ze zwykłych tokenów, potem prawdziwe `</think>` | `reasoning` = „The Qwen template closes reasoning with a ”, reszta rozumowania razem z prawdziwym `</think>` w `content` | całe rozumowanie w `reasoning`, `content` = „Answer.” |
| treść zawiera przykład `<tool_call>…bash…rm -rf build…</tool_call>` ze zwykłych tokenów | **`tool_calls: 1 bash {"command":"rm -rf build"}`**, treść ucięta | brak wywołania, przykład zostaje w `content` |
| kontrola: prawdziwe tokeny `<tool_call>` | `tool_calls: 1` | to samo |

- LFM2.5 ma ten sam błąd z `</think>`. Format wywołań LFM (`<|tool_call_start|>`) jest inny, więc przypadek 2 tam nie pasuje.
- W Qwen3.8 `<think>`, `</think>`, `<tool_call>`, `</tool_call>` to tokeny USER_DEFINED (32e). `<function=`/`<parameter=` w ogóle nie są tokenami, więc znaczniki parametrów pozostają czysto tekstowe także po poprawce. Tak samo jest w recipe, gdzie granice wyznacza `｜DSML｜`.
- Skala: w 6/74 tur omp wynik narzędzia zawierał dosłowne `<think>`/`</think>` (32e). Model, który pracuje nad szablonami i parserami (nasza codzienność), będzie je cytował.
- **Naprawa:** upstream PR #29307 (otwarty). Mapa tokenów długości tekstu jest już w topce (`T: peg-parser.h:186-201`, `chat.cpp:1630`), ale `peg-parser.cpp` jej nie czyta. Bezstratne dla generacji: nie zmienia tokenów ani md5, zmienia tylko podział na `reasoning`/`content`/`tool_calls` w przypadkach brzegowych.

## 3. DSpark ponad 32b, przeliczone na krok z raportu 36

Artykuł nie dodaje mechaniki ponad kod opisany w 32b. Przy c=1:
- **Bias Markowa od poprzedniego tokenu** naprawia spójność *równoległych* draftów bloku (DFlash). Nasz MTP jest łańcuchem autoregresyjnym, więc ten problem u nas nie istnieje. Dotyczy tylko gałęzi DFlash/FlashMap (39b).
- **Wyrocznia długości** (weryfikuje dokładnie przyjęte + 1): przy n=4 i 2.63 tok/krok marnujemy 4 − 1.63 = 2.37 poziomu × 1.40 ms (wiersz 0.85 + przebieg MTP, 36 §1.1) = 3.3 ms. Krok 27.38 → 24.1 ms daje sufit **+13.7%**, nieosiągalny.
- **Realnie:** 24q symulacja +2.6…3.1% (czat), E5/L2 zmierzone +0.1% (pl-proza). Varlen DSpark na c=1 to ten sam kontroler z wytrenowaną głowicą. Bezstratność jest rozkładowa, a md5 zostaje tylko z bitexact (L2). **Nic nowego do zrobienia.**

## 4. ZOS (async scheduling)

- Nasza luka hosta to 0.49 ms/krok, z czego ~0.1 ms jest nieusuwalne (36 §1.1).
- Sufit to 0.39/27.38 = **+1.4%**, a po przełącznikach 24o (−0.3 ms szac.) zostaje ~+0.7%.
- Ich kolejność (launch_forward(N+1) przed post-process(N)) wymaga, żeby wejścia N+1 powstawały na GPU. Mamy GPU verify (24m), więc przyjęte tokeny i ich liczba są już na urządzeniu.
- Przeszkody: re-capture przy n_kv co 256 tok. (24o), pozycje i maska w argumentach taśmy PM4, rollback GDN.
- To jest L11 z 36 (#4 w kolejności), bez nowej informacji. md5 bez zmian.

## 5. KV cache: pomysły dla `--cache-ram` i checkpointów (RAM, bez SSD)

| pomysł z artykułu | co mamy | delta dla nas |
|---|---|---|
| bloki 128 tok. + łańcuch hashy | LCP po całych wpisach `--cache-ram` | brak zysku: 8–16 wpisów × ≤ 200k porównań int to ≤ ~0.5 ms [INFERENCE] |
| snapshot SWA co 128 tok. + trafienie ≤ L − 134 | checkpointy na starcie wiadomości użytkownika (`T: server-context.cpp:4055-4063`) + `n−4−ub`, `n−4` (`:4065-4084`), min. odstęp 8192, maks. 32 (`T: common.h:654-656`) | mechanika ta sama. Nasze punkty są semantyczne, nie co 128 |
| długi TTL dla gorących prefiksów | ewikcja checkpointów „najstarszy pierwszy” (`:2573-2581`) usuwa najpierw checkpoint końca system promptu | **ochrona kotwicy:** nie usuwać pierwszego checkpointu startu użytkownika. Nowy subagent omp ze wspólnym system promptem ~7.3k tok. przy chybieniu liczy go od nowa: ~7.6 s (35 E2, S1-start). Działa tylko przy > 32 checkpointach na slot, a częstość nieznana → X3 |
| kopia okna do strefy w VRAM podczas dekodu | CkptVram (w toku), 35 E2 nr 3 | bez delty |
| H2D warstwami nakładane na liczenie | restore 2.3 GB ≈ 1.1 s z pageable (2.1 GB/s, 16f E4) | najpierw pamięć przypięta (wymóg z decyzji RAM/SVM): ~0.1 s przy ~22–25 GB/s [INFERENCE]. Nakładanie warstwami dałoby potem ≤ 0.1 s, czyli niski priorytet |
| tylko metadane na ścieżce krytycznej, KV async do shm | – | przy `-np 1` i jednym procesie odpowiednikiem jest async D2H zapisu starego slotu (35 E2 nr 2/3). Bez delty |

## 6. Reszta artykułu

- **Structured output** (xgrammar, kompilacja async): gramatyka wywołań omp w topce ma 9.3 KB, kompiluje się w 0.17 ms, a sprawdzenie tokenu (`LLAMA_SAMPLER_FAST_GRAMMAR`) z accept kosztuje 3.3 + 0.9 µs/token. Tylko odrzucony token spada na pełny słownik: 23 ms (`grammarbench`). W próbce 12.2k tokenów poprawnego wywołania nie było odrzuceń. Maska bitowa à la xgrammar ma sens dopiero przy częstych odrzuceniach (nieznane, T=1).
- **Prefill LB z odwracaniem kwadratowego modelu kosztu** na chunk o stałym budżecie czasu: sens przy mieszaniu dekodu wielu żądań. U nas `-np 1`, więc nie dotyczy. Pomysł zostaje dla produktu przy -np > 1.
- **Decode LB, EPLB (moe_lb 1.03–1.09), autoskalowanie, 3FS EC 10+2, wymuszanie EP po awarii:** klaster, nie dotyczy.

## Co się do nas stosuje (ranking)

| # | pomysł | zysk | wysiłek | bezstratność | uwagi |
|---|---|---|---|---|---|
| 1 | **Parsowanie wyjścia świadome tokenów** (PR #29307 albo własna łatka: literał znacznika = 1 token o tym ID) | bezpieczeństwo agenta: brak fałszywych tool calli i ucinania rozumowania; 0 t/s | 0.5–1 dnia (cherry-pick + konflikty z parserem topki) + testy | **md5 identyczne** (zmienia się tylko klasyfikacja tekstu) | domyka SAFE_SPECIAL z drugiej strony; ważne dla produktu (Podkręt) |
| 2 | **Równoległa tokenizacja segmentowa z cięciem segmentów** (B) | TTFT −25 / −55 / −104 / ~−132 ms przy 32k / 91k / 158k / 200k, **w każdej turze**; ~4–6% ciepłej tury przy 91k | 0.5–1 dnia + parzystość na 148 promptach + `test-tokenizer-0` | **tokeny identyczne** (148/148) | działa z SAFE, Qwen i LFM, ROCm, CUDA i Mac |
| 3 | Natywny renderer ChatML (32b nr 3) razem z #2 | host przy 91k 128 → ~12 ms | 2–3 dni | tokeny identyczne (złote testy) | już w 36 L14 |
| 4 | Memo tokenów per fragment | kolejne tury ~1 ms także z SAFE | +0.5 dnia na #2 | identyczne | zastępuje `TOK_CACHE` |
| 5 | Ochrona checkpointu kotwicy system promptu | do −7.6 s na nową sesję subagenta, **tylko jeśli** ewikcja się zdarza | kilka linii w `create_checkpoint` | md5 | najpierw X3 |
| 6 | ZOS-lite (L11) | ≤ +1.4% dekodu | 1–3 dni | md5 | bez zmian wobec 36 |
| – | DSpark varlen / głowica pewności | realnie ≤ +1…3% | – | rozkład (md5 tylko z bitexact) | = L2/E5, bez delty |
| – | parser KMP inkrementalny | 0 t/s, −3 s CPU na 13k-tokenową odpowiedź | 2+ dni | – | kill |
| – | xgrammar | 0 przy rzadkich odrzuceniach | duży | – | kill do czasu pomiaru odrzuceń |

NVIDIA/Mac: pozycje 1–4 to CPU i serwer, więc przenoszą się 1:1 (Mac M: 8–12 rdzeni wydajnych, podobny zysk [INFERENCE]).

## Eksperymenty (≤ 10 min każdy)

CPU, już zrobione (powtarzalne, ~10 s każde):
```
cd ~/qwen-opt/dsdeploy
SB_CHUNK=2048 SB_RULE2=1 nice -n 19 ./segbench ~/qwen-opt/agentpath/bodies_huge.jsonl 3 -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf --jinja --reasoning-effort low
SB_CHUNK=2048 SB_RULE2=1 nice -n 19 ./segbench ~/qwen-opt/agentpath/bodies_w13.jsonl 1 -m ~/models/lfm/LFM2.5-24B-A2B-Q5_K_M.gguf --jinja   # ostatnia linia: mismatches A=0 B=0
nice -n 19 ./plainmarker b0.jsonl -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf --jinja --reasoning-effort low                                  # fałszywy tool call
nice -n 19 ./parsebench b0.jsonl out_tool.txt 2000 -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf --jinja --reasoning-effort low
```

XTX (GPU, w kolejce, przy wyłączonym serwerze użytkownika):
1. **X1: udział hosta w ciepłej turze przy 60k.** `~/qwen-opt/agentpath/arm.sh x39c-host ~/llama-topka rr=w2big.json` (AP_TIMING=1 jest w skrypcie), potem `grep " ap " ~/qwen-opt/agentpath/logs/x39c-host.server.log` i zestawienie template + tokenize z `prompt_ms` per tura.
   - Próg: (render + tokenizacja) ≥ 5% `prompt_ms` tury przy ≥ 60k, wtedy wdrażamy #2 (+#3). Poniżej 3%: tylko #2, bo jest tani.
   - Uwaga: `arm.sh` przypina serwer do 4 rdzeni (`taskset -c 2-5`), więc dla #2 liczy się kolumna A4/B4 (91k: 16.3 ms), a nie B8. Produkcja nie jest przypięta.
2. **X2: bramka #1 po cherry-picku PR #29307.** CPU `plainmarker` → oczekiwane `tool_calls: 0` w przypadku 2 i pełne `reasoning` w przypadku 1. GPU: `~/qwen-opt/greedy_check.sh ~/wt/topka/inst/bin ~/wt/topka/inst/lib /tmp/x39c-tok` → Qwen plain `c4708318`, MTP `6f14e814`, LFM `894e56e4` (prompt bramki nie ma znaczników).
3. **X3: czy kotwica system promptu ginie.** `~/qwen-opt/agentpath/arm.sh x39c-ckpt ~/llama-topka rr=w13.json`, potem `grep -c "erasing old context checkpoint" ~/qwen-opt/agentpath/logs/x39c-ckpt.server.log` (poziom WRN) oraz liczba tur z `n_past` restore ≤ 8k przy nowej sesji. Wynik 0 oznacza kill pozycji 5.
4. **X4 (po implementacji #2): bramka md5 i TTFT.** `LLAMA_TOKENIZE_THREADS=8` vs `=0` na `greedy_check.sh` (md5 jak wyżej) + `ttft.py` 32k ×3 ABBA. Oczekiwane: md5 równe, TTFT −25 ms ± szum.

## Do bazy wiedzy

Wiersze ZRODLA:

| źródło | wersja / data | raport, notatka | werdykt (≤12 słów) | kluczowe liczby | następnym razem sprawdź |
|---|---|---|---|---|---|
| Artykuł DeepSeek „V4.1 Flash Large-Scale Inference Deployment Practice” (zhuanlan.zhihu.com/p/2095560295930508953; x.com/latentspacepod/status/2112588380416647205) | 2026-10-20 (tłumaczenie użytkownika, ucięte akapity) | R39c | Nowe tylko recipe: parsowanie po ID tokenu, tokenizacja segmentowa; reszta klaster. | KV TTL 3 d/7 d, SWA TTL 180 s / 98%, moe_lb 1.03–1.09, ring 134 | pełny oryginał (ucięte „+6% online”, kopia VRAM SWA); czy opublikują kvcache-store |
| deepseek-recipe (aktualizacja wiersza z R32b) | `935817c` | R32b, R39c | Parser wyjścia dopasowuje znaczniki z rodzajem tokenu (KMP); równoległość tylko per segment. | `output_parser.rs:366-373,704-770`; `tokenizer.rs:93-103` | – |
| llama.cpp PR #29307 „chat : implement token aware parsing” (aldehir) | otwarty, head `2f910999a` 2026-09-28 | R39c | Gotowa poprawka fałszywych `</think>`/`<tool_call>` ze zwykłych tokenów; brać. | topka: plain `<tool_call>` → wykonany `bash rm -rf build` | czy scalony; konflikty z parserem topki |

Wiki:
- **lekcje / „Znaczniki wyjścia ze zwykłych tokenów”:** parser llama.cpp (PEG, tekstowy) traktuje `</think>` i `<tool_call>` złożone ze zwykłych tokenów jak tokeny specjalne. Skutki: ucięte rozumowanie i wykonany fałszywy tool call (Qwen3.8, CPU `plainmarker`). Mapa tokenów jest w topce od #29876, ale parser jej nie czyta. Naprawa: PR #29307.
- **metody / „Równoległa tokenizacja segmentowa”:** cięcie na tokenach specjalnych + (`\n`|litera␠) + litera ASCII dla `qwen2`/`qwen35`/`llama3`. 148/148 identycznie. 91k: 64.8 → 9.6 ms (8 wątków). Sama segmentacja per segment (recipe) jest ograniczona największym segmentem (5–64% promptu).
- **wyniki-negatywne:** parser strumieniowy KMP (koszt O(n²) topki = 3.5 s CPU na 12.8k tok., poza pętlą GPU), xgrammar (gramatyka omp 0.17 ms kompilacji, 4 µs/token), DSpark varlen przy c=1 (sufit wyroczni +13.7%, realnie = L2).
