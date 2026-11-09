# 69a. DSpine dla Qwen3.8-27B: wydanie Tencenta, port llama.cpp (Ajay9o9) i rachunek na XTX / Enigma NVIDIA

Data: 2026-11-09. Autor: podagent R69a_DSpine. Tylko CPU i sieć: bez GPU, bez buildów, bez pobierania wag. Sklonowane: `~/src/research69/ajay-llama-dspine` (gałąź `dspine`, `--depth 60`) i `~/src/research69/tencent-dspine` (`--depth 1`). Nagłówek GGUF pobrany Range-em (9 MB, plik usunięty; nie wystarczył, bo tokenizer zajmuje > 9 MB, więc typów tensorów nie odczytałem).

Oznaczenia: **NOWE** = brak w KB przed tym raportem; **ZNANE** = już w `21a`, `67b`, `68b`, `68d`, wiki. `[INFERENCE]` = mój wniosek, nie pomiar. Liczby producenta lub autora portu są zawsze podane z warunkami pomiaru.

Skróty źródeł:
- `F:` = fork `~/src/research69/ajay-llama-dspine/<plik>:<linia>` (commit `d493f84`);
- `T:` = repo Tencenta `~/src/research69/tencent-dspine/<plik>` (commit `0cc92d8`);
- `HF-T` = https://huggingface.co/tencent/Qwen3.8-27B-DSpine-b16 (sha `ea909c0`) i jej `config.json`;
- `HF-A` = https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF (sha `62e9241`); `HF-A v1` = pierwsza wersja karty (commit `b16fdf0`);
- `SS` = `~/qwen-opt/spec_sweep.jsonl`, wiersz `kvq-md5-P-1` (2026-11-07 23:37, T=1, mediana 118.2 t/s, produkcja topka-q63).

---

## TL;DR

1. **Werdykt XTX: nie zastąpi MTP4 ani ogona W16. Ma sens tylko jako drafter klasy „nowy kod” przy kontekście ≤ 16k, a i to dopiero po tanim teście τ na GPU (T1).** Wniosek 21a się trzyma. Zmieniły się dwie rzeczy: koszt portu i pierwsza bramka.
   - **Koszt portu (NOWE).** Port Ajaya to 1 commit (+323 linie, 8 plików), wyłącznie graf. Nie ma nowych kerneli. Lattice DFlash2 i sampler są z upstreamu. Nasz fork ma już ścieżkę lattice DFlash2 i wszystkie użyte op-y ggml, więc port do topki to ~1–2 dni `[INFERENCE]`, a nie 5–7 jak w 21a.
   - **Pierwsza bramka (NOWE).** Zamiast 5–7 dni portu wystarczy zbudować fork Ajaya pod HIP (bez zmian w kodzie) i zmierzyć τ per klasa (T1).
2. **Model na XTX** (krok MTP4 26.9 ms z `SS`, krok DSpine = V16(ctx) + D, D = 7.5–10.5 ms) daje krok DSpine **37.5–43.5 ms przy 2k**. Żeby wyjść na zero, DSpine potrzebuje **1.39–1.62× τ MTP4**.
   - Szacunek per klasa przy 2k: en-code **+9…+57%**, pl-kod −14…+33%, en-tech −45…−15%, en-chat −48…−23%, pl-tech −58…−30%, pl-proza **−67…−40%**.
   - Code-edit (`mvs`, ~400 t/s): przegrywa, bo sufit to 16 tok / 37.5 ms ≤ 427 t/s przy 100% akceptacji (ZNANE, 21a §4.3).
3. **Liczby z portu (RTX 3090) są arytmetycznie spójne, ale baza jest słaba.**
   - „28.2 t/s” to dekodowanie **bez żadnej spekulacji (bez MTP)** na 3090, czyli ~31% wolniej niż nasze AR na 3090 (40.93 t/s, kampania 67).
   - MTP w porównaniu nie występuje, choć upstream je ma.
   - Krok DSpine wynosi ~59–60 ms na każdej klasie, czyli **1.68× krok AR**. Szeroka weryfikacja na upstreamowej CUDA (Ampere) **nie jest tania**: stosunek jest taki sam jak przewidziany dla XTX (NOWE).
4. **„1.75× nad DFlash2”** = 90.1/51.7 (T=0, 10 promptów, w tym 4 kod + 2 matematyka). Przy T=1 to **1.59×**, przy głębokości 8–32k **1.11–1.36×** (pojedyncze przebiegi).
   - Baza DFlash2 była uruchomiona z blokiem 8 i ma krok ~88 ms (v1: 58.2 t/s przy ~5.1 tok/krok), czyli wolniej niż DSpine-16. Wygląda to na wolną ścieżkę 8-kolumnową MMQ na Ampere (PR #31533: DFlash2 na 3090 Ti 58.9 ms/krok) `[INFERENCE]`.
   - **„3.3×”** to liczba Tencenta: WorkBuddy Web xhigh 840.14 / 252.26 = 3.33× nad AR. Zmierzono ją w SGLang przy **współbieżności 8**, w BF16, z FA3, czyli nie w batch 1.
   - **„94–132 t/s”** nie występuje w żadnej wersji karty ani w tweetach. Karta v2 podaje 90.1 (mieszanka) i 122.8–128.7 (matematyka/kod), v1 podaje 104.8.
5. **Enigma NVIDIA: nie jako domyślny drafter.**
   - Na 24 GB DSpine-15 obcina kontekst do 64k (q8_0 KV, upstream z kopią stanu GDN na każdy token draftu), a Enigma sprzedaje 245–262k.
   - Proza i PL są gorsze niż MTP.
   - Fork jednego autora, bez PR w upstreamie.
   - Ewentualnie opcjonalny profil „kod” na 5090 po teście T5.
6. **Pobranie do testu: tylko `Qwen3.8-27B-DSpine-b16-Q4_K_M.gguf` = 1 257 892 896 B (1.26 GB / 1.17 GiB).** Cel: lokalny `~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf` (bazowy Qwen3.8-27B, na którym trenowano DSpine). Q8_0 (2.20 GB) i BF16 (4.06 GB) są zbędne.

---

## 1. Fakty ze źródeł

### 1.1 Wydanie Tencenta (HF-T, T:)

| fakt | wartość | źródło | status |
|---|---|---|---|
| data | HF repo 2026-11-07 14:20 UTC; README Tencenta „[2026-11] Added support for Qwen3.8-27B inference” | HF API `createdAt`; `T:README.md:24` | ZNANE (67b: 11-07) |
| architektura | `DFlashDraftModel`, 5 warstw, hidden 5120, FFN 17408, 32/8 głów, head_dim 128, `block_size` 16, `mask_token_id` 248070, vocab 248320 | `HF-T config.json` | NOWE (szczegóły 27B) |
| **atencja draftu** | **wszystkie 5 warstw `sliding_attention`, `sliding_window` 8192** | `HF-T config.json` (`layer_types`, `sliding_window`) | **NOWE**: 21a zakładało pełną atencję (jak 8B) i liczyło KV draftu 1.18 GB przy 200k q4_0. Przy SWA 8192 i q4_0 jest to ~47 MB (10 240 el./token × 0.5625 B × 8192) |
| warstwy celu | `target_layer_ids` [1, 16, 31, 46, 61] z 64 | `HF-T config.json` | NOWE |
| refinement | `code_bridge_second_pass`: `serial_table`, `first_exact` 4, `head_topk` 16; `selected_prefix_last_write_refine.kind = exact_sender` | `HF-T config.json` | ZNANE co do mechanizmu (21a §1.3) |
| rozmiar | `model.safetensors` 4 051 831 880 B BF16 ≈ 2.03 B parametrów (bez embeddingu i LM head celu) | HF API tree | NOWE |
| dane treningowe 27B | **nieujawnione** na karcie (8B: Open-PerfectBlend, EN) | HF-T | NOWE (luka) |
| kod treningu | opublikowany w SpecForge (PR sgl-project/SpecForge#1038) | `T:README.md:26,136` | **NOWE** (21a: „kodu treningu nie ma”) |
| MLX | wsparcie Apple (mlx-lm, SGLang-MLX); Qwen3-8B na M4 Pro: 4.09× AR przy c=1 | `T:README.md:25`, `T:dspine_mlx/README.md:89-99` | NOWE, bez znaczenia dla nas |
| warunki ewaluacji | SGLang 0.5.22, BF16, FA3, **współbieżność 8**; DSpine z dynamiczną weryfikacją DSpark (tabela SPS) i ReplaySSM; DFlash2 oficjalny **blok 8** vs DSpine **blok 16**; GPU nie podany | HF-T „Evaluation” | NOWE |
| SPS | tuner wybiera **jednolitą szerokość weryfikacji 4/8/12/16** dla batchy 1–7. Producent sam przyznaje, że pełne 16 nie zawsze się opłaca | `T:docs/sps_tuning.md:3-6,47-49` | NOWE (zgodne z naszą lekcją o koszcie szerokości) |

Akceptacja z karty (τ = średnia długość akceptacji, ta sama konfiguracja SGLang; DSpine b16 vs DFlash2 b8):

| zadanie | DFlash2 T=0 | DSpine T=0 | Δ | DFlash2 T=1 | DSpine T=1 | Δ |
|---|---|---|---|---|---|---|
| GSM8K | 5.69 | 7.20 | +26.5% | 5.45 | 6.31 | +15.8% |
| MATH-500 | 5.49 | 6.49 | +18.2% | 5.27 | 5.66 | +7.4% |
| HumanEval | 4.87 | 5.71 | +17.2% | 4.34 | 4.71 | +8.5% |
| MBPP | 5.04 | 6.14 | +21.8% | 4.79 | 5.41 | +12.9% |
| MT-Bench | 4.11 | 4.48 | +9.0% | 3.89 | 4.03 | **+3.6%** |

- Agent (T=1, low/xhigh): τ DSpine 4.77–5.63 vs DFlash2 3.95–4.70, czyli +16…+33%. Przepustowość e2e przy c=8: DSpine 2.71–3.84× AR, DFlash2 2.33–3.17× AR (HF-T). ZNANE w skrócie z 67b („4.5–7.2 vs 4.1–5.7”). Rozbicie i warunki są NOWE.
- **Interpretacja** `[INFERENCE]`: przewaga 27B to w dużej części **szerszy blok** (16 vs 8 ⇒ sufit τ 16 vs 8), a nie sam „kręgosłup”. Na czacie przy T=1 (MT-Bench) zostaje +3.6%, tyle samo co na 8B przy tych samych danych (+3.7…+6.9%, ZNANE 21a). Karta nie porównuje z MTP Qwena.

### 1.2 Port llama.cpp (Ajay9o9/llama.cpp, gałąź `dspine`)

| pytanie | odpowiedź | źródło | status |
|---|---|---|---|
| baza | **jeden commit** `d493f84` (2026-11-08) na upstream `a691b23` (ggml-org master 2026-11-08, „webgpu : add COUNT_EQUAL support (#31578)”) | `git log` w klonie | NOWE |
| zakres | 8 plików, +323 linie: konwerter (`conversion/qwen.py` +69), `gguf-py` (+42), `llama-arch` (+18), `llama-model.h` (+10), `llama-quant.cpp` (+5), `src/models/dflash.cpp` (+179) | `git show --stat d493f84` | NOWE |
| op-y GGML | tylko istniejące: `mul_mat`, `rms_norm`, `l2_norm`, `sum_rows`, `sqr`, `sqrt`, `scale`, `get_rows`, `concat`, `view`/`cont`/`reshape`, `sigmoid`, `add`, `mul`, `pad_ext`, `pad`, `repeat_4d`, `top_k`, `fill`, `cast` | `F:src/models/dflash.cpp:793-924` | NOWE |
| backendy | **brak kodu specyficznego dla backendu.** CUDA `supports_op` obsługuje wszystkie te op-y (`F:ggml/src/ggml-cuda/ggml-cuda.cu:6153-6372`), a HIP kompiluje ten sam kod. Autor testował tylko CUDA (3090). HIP nietestowany `[INFERENCE: powinien działać]` | HF-A „Build” (`-DGGML_CUDA=ON`) | NOWE |
| graf draftu | graf DFlash z upstreamu (5 warstw, cechy 5 warstw celu przez `fc`, atencja przyczynowa z `is_causal`, SWA przez iSWA KV) plus `build_dspine_write` po każdej warstwie i `build_dspine_lattice` po LM head | `F:src/models/dflash.cpp:1329,1393`; `F:conversion/qwen.py:902-915` | NOWE |
| lattice | `top_k(16)` z **pełnych logitów** 248 320 dla 16 wierszy. Ostatni zapis bridge przeliczany dla 16 kandydatów poprzednika (3840 wierszy). Tabela 16×16 na pozycję pakowana jak lattice DFlash2 w `t_h_nextn`. TG/TSV nie są budowane, wszystko liczy się w locie (tak jak proponowało 21a, I3) | `F:src/models/dflash.cpp:856-924` | NOWE |
| sampler | DSpine **udaje DFlash2**: konwerter zapisuje `selector_top_k`, więc `is_dflash2 = selector_top_k > 0` i działa istniejący spacer po lattice. Domyślnie draft jest zachłanny, a cel robi sample-and-match. `--spec-draft-sampling probabilistic` próbkuje łańcuch z softmaksu top-16 i przekazuje q do rejection samplingu | `F:common/speculative.cpp:1069-1070,1385-1452` | NOWE |
| bezstratność | **tak, rozkładowo**: zachłanny draft + dopasowanie do próbki celu albo `min(1, p/q)` + rezyduum `max(0, p−q)` (`F:common/sampling.cpp:733-819`). Przy T=0 ten sam token co bez spekulacji (z dokładnością do numeryki szerokiej weryfikacji). Przy T>0 **nie bitowo** względem przebiegu bez spekulacji (inne zużycie RNG) | j.w. | NOWE (u nas sprzężone Gumbel daje md5, ZNANE 16k) |
| KV | KV draftu: zwykły cache iSWA llama.cpp (okno 8192), typ z `--spec-draft-type-k/v`. Cel w upstreamie trzyma **kopię stanu rekurencyjnego na każdy token draftu** (~150 MB na kopię, wg autora), stąd limit kontekstu | HF-A „Maximum context” | NOWE (u nas S4/T1 lag+replay GDN tej kopii nie robi, ZNANE) |
| kwantyzacja | tensory `dspine_*` zostają nieskwantowane (BF16), poza `dspine_codebook` | `F:src/llama-quant.cpp:374-376` | NOWE |
| upstream | brak PR. Wyszukiwanie `repo:ggml-org/llama.cpp dspine` (2026-11-09) daje tylko niezwiązany #25187 | GitHub API | NOWE |

### 1.3 Pomiary autora portu (HF-A, HF-A v1, tweety)

**Sprzęt i warunki (HF-A „Test machine”):**
- 1× RTX 3090 24 GB (limit mocy nie podany), Ryzen 9 9900X, sterownik 595.91, CUDA 12.0, gałąź `dspine`;
- cel `Qwen3.8-27B-Q4_K_M.gguf` 17.1 GB (tweet: „UD-Q4_K_M”);
- KV q8_0 dla celu i draftu, `-fa on`, `-np 1`, `--fit off`.

**Test per zadanie:**
- 10 promptów: 2 matematyka, 2 pisanie, 2 streszczenie/tłumaczenie, 4 kod (Python/C++/JS/SQL);
- ≤ 1024 tokenów, thinking wyłączony, ~6000 tokenów na setup, jeden przebieg;
- T=1 z `top_p 0.95, top_k 20` i probabilistycznym draftem.

| setup | T=0 t/s | T=1 t/s |
|---|---|---|
| bez spekulacji | 28.2 | 28.2 |
| DFlash2 Q4_K_M, n 7 | 51.7 | 50.6 |
| DSpine Q4_K_M, n 15 | 90.1 | 80.4 |
| DSpine Q8_0, n 15 | 86.3 | – |

| zadanie (T=0) | DSpine t/s | tok/krok | ms/krok (moje: 1000·tok/krok ÷ t/s) | DFlash2 t/s |
|---|---|---|---|---|
| kod | 128.7 | 7.6 | 59.1 | 63.3 |
| matematyka | 122.8 | 7.3 | 59.4 | 64.2 |
| streszczenie/tłumaczenie | 62.0 | 3.6 | 58.1 | 43.0 |
| proza/opowiadanie | 41.6 | 2.5 | 60.1 | 30.2 |

Wnioski z arytmetyki (NOWE):
- **Krok DSpine ≈ 59–60 ms niezależnie od treści**, a krok AR = 1000/28.2 = 35.5 ms, więc **krok DSpine = 1.68× AR**. Dla porównania H100 u Tencenta: 1.36× (ZNANE, 21a), XTX w naszym modelu: 1.64–1.90× V1 (§3). Lekcja [[lekcja-akceptacja-h100-nie-przenosi-sie]] dostaje pierwszy niezależny dowód z NVIDIA consumer.
- **Baza 28.2 t/s jest słaba:** nasze AR na 3090 (UD-Q4_K_XL, 340 W, KV q4_0, pin b11856) to 40.93 t/s (`67-nvidia-vast-kampania.md:15`), a `mmvq-n1-wiersze` daje tg128 40.1→43.0. Ich 3090 dekoduje 17.1 GB × 29.5 t/s ≈ 504 GB/s, czyli 54% pasma 936 GB/s, wobec ~68% u nas. Przyczyna nieznana (limit mocy? zegary?) `[INFERENCE]`. Mnożnik „3.2×/4.5×” jest więc liczony od zaniżonej bazy.
- **Brak MTP jako bazy.** Upstream ma `draft-mtp` (Enigma używa go na pinie b11856). Właściwe pytanie, „DSpine vs MTP n3 na tym samym buildzie”, nie zostało zmierzone.
- **DFlash2 jako baza jest podejrzanie wolny:** v1: 58.2 t/s przy ~5.1 tok/krok, czyli **87.6 ms/krok = 2.5× AR**, wolniej niż DSpine-16. Zgodne z PR #31533: na 3090 Ti DFlash2 n 7 na masterze ma 58.87 ms/krok, a z few-row MMQ 43.81 ms. Część przewagi „1.75×” wynika więc z wolnej ścieżki 8 kolumn w upstreamowej CUDA na Ampere `[INFERENCE]`.
- **Głębokość** (llama-benchy, `--tg 256 --runs 1`, pojedyncze przebiegi):

  | korpus, kontekst | AR | DFlash2 | DSpine | DSpine/AR | DSpine/DFlash2 |
  |---|---|---|---|---|---|
  | proza, 8k | 28.1 | 26.6 | 35.6 | 1.27× | 1.34× |
  | proza, 32k | 23.8 | 28.0 | 31.1 | 1.31× | 1.11× |
  | wyjaśnianie kodu, 8k | 27.4 | 28.4 | 35.2 | 1.28× | 1.24× |
  | wyjaśnianie kodu, 63.5k | – | – | 47.8 | – | – |

  Ostatni wiersz jest outlierem większym niż przy 0k (41.6), czyli szumem. Na tych korpusach autor sam podaje „~2.5–3.5 tokens per verify”.
- **Okno SWA 8192:** v1 przy prompcie 13k: 62 t/s i ~4.1 tok/krok, wobec ~6.3 średnio na krótkich, czyli −35% τ po wyjściu poza okno. Treść inna, więc to `[INFERENCE]`, ale ryzyko dla agentów (p50 wejścia 88k) jest realne.
- **Maks. kontekst 24 GB (q8_0):** bez spekulacji 176 128, DFlash2-7 102 400, **DSpine-15 65 536**, DSpine-7 98 304, DSpine Q8_0-15 40 960.

Sprawdzenie twierdzeń z zadania:

| twierdzenie | co jest w źródle | ocena |
|---|---|---|
| „baseline 28.2 t/s” | HF-A v2: bez spekulacji, 3090, T=0 i T=1 | **prawda, ale to nie MTP**, a 3090 autora jest ~31% wolniejsza od naszej |
| „DFlash2 50.6” | HF-A v2, T=1 (T=0: 51.7) | prawda; baza podejrzanie wolna (2.5× AR na krok w v1) |
| „DSpine 94–132” | nie znalazłem. v2: 90.1 / 80.4 (mieszanka T=0/T=1), 122.8–128.7 (matematyka/kod T=0); v1: 104.8 (4 prompty) | **nie do zweryfikowania**; najbliższe liczby jak obok |
| „7.3–7.6 tok/krok na math/code” | HF-A v2, T=0, krótki kontekst, thinking off, 2+4 prompty | prawda w tych warunkach; proza 2.5, streszczenie 3.6 |
| „1.75× nad DFlash2” | 90.1/51.7 = 1.74 (T=0, mieszanka z 60% kod+matematyka); T=1 1.59; kod 2.03, proza 1.38; głębokość 8–32k 1.11–1.36 | **zawyżone warunkami**: DFlash2 blok 8 na wolnej ścieżce MMQ, mieszanka promptów pod kod |
| „3.3×” | HF-T: WorkBuddy Web xhigh 3.33× AR (SGLang, BF16, H-class GPU [INFERENCE], **c=8**); HF-A: 3.19×/2.85× (T=0/T=1, 3090, od bazy 28.2) | nie dotyczy batch 1 (to samo zauważył w odpowiedzi na tweet Levi Qiao) |

---

## 2. NOWE vs ZNANE (zbiorczo)

| temat | ZNANE (gdzie) | NOWE (ten raport) |
|---|---|---|
| mechanizm DSpine | 21a §1 | 27B: SWA 8192, warstwy [1,16,31,46,61], 2.03 B parametrów |
| τ vs DFlash2 | 8B: +3.7…+6.9% przy tych samych danych (21a); 27B „4.5–7.2 vs 4.1–5.7” (67b) | rozbicie 27B: T=1 MT-Bench +3.6%, kod +8.5…+12.9%, matematyka +7.4…+15.8%; blok 16 vs 8 jako konfounder |
| koszt szerokości | XTX V16/V1 1.34–1.61, H100 1.04 (lekcja) | 3090 upstream: krok DSpine 1.68× AR; CUDA 8 kolumn wolne do czasu PR #31533 |
| llama.cpp | „brak, port 5–7 dni” (21a §6) | port Ajaya: 323 linie, tylko graf, op-y obecne w naszym forku (`ggml_fill`, `ggml_pad_ext`, `ggml_repeat_4d`, `ggml_top_k`, `ggml_l2_norm` w `~/wt/topka-q63/ggml/include/ggml.h`; lattice DFlash2 w `~/wt/topka-q63/src/models/dflash.cpp:473-560`; `is_dflash2` w `common/speculative.cpp:1057`), więc ~1–2 dni `[INFERENCE]` |
| bezstratność | 21a: rejection standardowy (SGLang) | llama.cpp: sample-and-match albo rejection (`F:common/sampling.cpp:733`), rozkładowo bezstratne |
| VRAM | 21a §7.2: KV draftu 1.18 GB przy 200k (pełna atencja) | SWA: ~47 MB (q4_0). Wagi 1.26 GB + bufory ~0.2–0.4 GB `[INFERENCE]` > zapas 1193 MiB przy 262k (`wiki/eksperymenty/2026-11-06-ctx-262k-fit.md:10`) |
| PL | 21a §5: ryzyko ≥ 80% | dane 27B nieujawnione; kod treningu jest (SpecForge #1038), więc PL-fine-tune możliwy, ale wymaga $ i zgody |
| MTP baza | 68b: „przy T=1 na czacie nie biją MTP” | port nie porównuje z MTP; nasze MTP4 dziś ma **2.79 tok/krok na pl-proza** (`SS`), a nie 1.97 jak w 21a (3090, 16i), więc próg dla DSpine na prozie jest jeszcze wyżej |

---

## 3. Model na naszym pudle (XTX, topka-q63, Uncensored/Qwen3.8-27B Q4)

Założenia:
- **MTP4 (pomiar, `SS`):**

  | klasa | tok/krok | ms/krok | t/s |
  |---|---|---|---|
  | pl-proza | 2.791 | 27.11 | 103.0 |
  | pl-tech | 3.288 | 27.03 | 121.6 |
  | pl-kod | 3.243 | 26.87 | 120.7 |
  | en-chat | 2.608 | 26.86 | 97.1 |
  | en-tech | 3.380 | 26.96 | 125.4 |
  | en-code | 3.117 | 26.94 | 115.7 |

- **Krok MTP4 przy ctx** = 26.9 + (V5(ctx) − V5(2k)) z [[koszt-szerokosci-weryfikacji]]: 26.9 / 27.2 / 28.4 / 30.0 ms przy 2k / 8k / 32k / 64k.
- **Krok DSpine** = krok MTP4 − D_MTP (3.3 ms) + ΔV(5→16, ctx) + D. ΔV liczę na dwa sposoby:
  - z llama-bench: 6.40 / 7.13 / 9.50 / 12.45 ms;
  - serwerowo: +3.0 ms, bo 24k zmierzył 5→16 ≈ 9.4 ms z głową LM, replayem GDN i kopią logitów.
- **D (draft DSpine-27B)** = 7.5–10.5 ms `[INFERENCE]`. Bazą jest DFlash2-27B n=15 zmierzony u nas: 8.6 ms (21a §4.1, `15b:21`). Do tego:
  - +10% wag (1.17 vs 1.06 GiB);
  - lattice 3840 wierszy: ~14 GFLOP na BF16 i ~80 MB pośrednich f32, czyli ~1–1.5 ms;
  - odpada selektor DFlash2.

  **SWA 8192, więc D nie rośnie powyżej 8k** (NOWE vs 21a, które dodawało +1–2 ms przy 64k).

| ctx | krok MTP4 | krok DSpine (llama-bench / serwer) | wymagany τ_DSpine / τ_MTP4 |
|---|---|---|---|
| 2k | 26.9 | 37.5–40.5 / 40.5–43.5 | **1.39–1.62** |
| 8k | 27.2 | 38.6–41.6 / 41.6–44.6 | 1.42–1.64 |
| 32k | 28.4 | 42.1–45.1 / 45.1–48.1 | 1.48–1.69 |
| 64k | 30.0 | 46.6–49.6 / 49.6–52.6 | **1.56–1.76** |

Stosunek „krok DSpine / AR” na XTX = 37.5–43.5 / 22.83 = 1.64–1.90 (vs 1.68 zmierzone na 3090 u Ajaya, §1.3).

τ DSpine per klasa przy T=1 `[INFERENCE]`:
- źródło: Ajay T=0 (kod 7.6, matematyka 7.3, streszczenie 3.6, proza 2.5) × T=1/T=0 z karty Tencenta (0.83–0.90) i z Ajaya (80.4/90.1 = 0.89);
- PL: DFlash2 pl-proza 1.32 (ZNANE 16i);
- przyjęte zakresy: pl-proza 1.5–2.3, pl-tech 2.2–3.2, pl-kod 4.5–6.0, en-chat 2.2–2.8, en-tech 3.0–4.0, en-code 5.5–6.8.

| klasa | MTP4 t/s (2k) | DSpine t/s 2k | Δ 2k | Δ 8k | Δ 32k (bez kary SWA) | wymagany τ przy 2k |
|---|---|---|---|---|---|---|
| pl-proza | 103.0 | 34.5–61.3 | **−67…−40%** | −67…−41% | −68…−44% | 3.86–4.48 |
| pl-tech | 121.6 | 50.6–85.3 | −58…−30% | −59…−31% | −60…−34% | 4.56–5.29 |
| pl-kod (nowy) | 120.7 | 103.4–160.0 | −14…+33% | −15…+31% | −18…+25% | 4.53–5.25 |
| en-chat | 97.1 | 50.6–74.7 | −48…−23% | −49…−24% | −50…−28% | 3.64–4.22 |
| en-tech | 125.4 | 69.0–106.7 | −45…−15% | −46…−16% | −47…−20% | 4.70–5.45 |
| en-code (nowy) | 115.7 | 126.4–181.3 | **+9…+57%** | +8…+54% | +4…+47% | 4.34–5.03 |

- Przy 32k realnie gorzej, bo τ spada poza oknem 8192 (v1: −35% przy 13k). Przy −35% τ en-code przy 32k daje 74–105 t/s, czyli **−32…−4%**.
- **Code-edit (`mvs`, T=0, ~400 t/s):**
  - sufit DSpine to 16/37.5 ms = 427 t/s przy p = 1;
  - przy p = 0.97–0.99 wychodzi 296–396 t/s, czyli −26…−1%;
  - ogon W16 kosztuje 0 ms draftu (ZNANE 21a §4.3, 24j). **Kill.**
- **Sesja agenta (120.8 t/s):** udział tokenów „nowego kodu” f ≈ 0.2–0.3 (ZNANE 21a §4.4), p50 kontekstu 88k ([[ksztalt-ruchu-agentowego]]), DSpine sensowny tylko ≤ 16k. Oczekiwany zysk na mieszance to **+0…+4%** `[INFERENCE]`, mniej niż 21a (+2…+7%), bo MTP4 zrobiło się szybsze (26.9 ms, 2.6–3.4 tok/krok).
- **Ruch PL:** żadna klasa PL poza pl-kod nie ma realnej szansy. Proza PL wymaga τ ≥ 3.9, a Ajay mierzy 2.5 na prozie EN przy T=0.

### 3.1 Bramki z 21a (G0–G4) po tym raporcie

| bramka | stan | kill |
|---|---|---|
| G0 config | **zrobione**: SWA 8192 (problem VRAM KV draftu znika), blok 16, warstwy [1,16,31,46,61], Apache-2.0, kod treningu jest, dane 27B nieujawnione | brak killa; dopisać limit ctx z VRAM (§4) |
| G1 τ offline | **zamienić na T1** (HIP build forka Ajaya, prawdziwy serwer, τ per klasa). Szybciej i dokładniej niż teacher-forcing na CPU | K1 (z 21a): przewidywane t/s < MTP na wszystkich klasach poza nowym kodem **i** zysk na nowym kodzie < +15% przy 8k |
| G2 port | 1–2 dni zamiast 5–7 (cherry-pick `d493f84` + adaptacja do starszego `dflash.cpp`) `[INFERENCE]` | test: wybory tokenów nasz graf vs fork Ajaya = 100% przy T=0 na tych samych promptach |
| G3 D(ctx) | z T1/T2 (logi czasu draftu) | K2: D(2k) > 10 ms (górny koniec mojego zakresu już go dotyka); D(64k) ≈ D(8k) z SWA |
| G4 ABBA | po G2 | K3: < +10% t/s na pl-kod/en-code przy 8k albo regresja > 1% gdziekolwiek z kontrolerem; md5 T=0 ≤ 7 propozycji = plain |

---

## 4. Istotność

### 4.1 XTX (nasz silnik)
- **Drafter per klasa ruchu (kod/matematyka) w kontrolerze: tak, jako kandydat, nie jako decyzja.**
  - Klasa „nowy kod” przy ctx ≤ 16k to jedyne miejsce z dodatnim zakresem. Na pl-kod zakres przechodzi przez zero.
  - Kontroler musi wykrywać klasę przed krokiem: np. po treści draftu MTP lub po narzędziu agenta (`write`) `[INFERENCE]`.
  - Pierwszeństwo dla ogona W16, gdy lookup ma ciąg ≥ 8 (ZNANE 21a §7.1).
- **VRAM:** przy 262k zapas 1193 MiB, a DSpine (MTP zostaje rezydentne) potrzebuje ~1.45–1.7 GB `[INFERENCE]`. Ctx trzeba zbić o ~30–40k tokenów q4_0 (18 KiB/token) **albo** ładować DSpine tylko w profilu kodu z ctx ≤ 196k. Test T4.
- **Uncensored:** DSpine trenowany na stanach bazowego Qwen3.8-27B. Na fine-tunie Uncensored cechy warstw są przesunięte, więc τ może spaść `[INFERENCE]`. T1 robić na bazie (`~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf`), a jeśli przejdzie, to T1b na Uncensored.

### 4.2 Enigma NVIDIA (3090/4090/5090)
- **Założenie „V16 tańsze na NVIDIA” nie jest potwierdzone dla upstreamowej CUDA na Ampere:** krok DSpine-16 = 1.68× AR na 3090 (Ajay), DFlash2-8 na 3090 Ti 58.9 ms/krok (PR #31533, master). Po PR #31533 (otwarty) przejście 16 kolumn ma być 1.13–1.18× szybsze (llama-bench, 3090 Ti/5090), a 8 kolumn 1.17–1.42×. Krzywej V(w) dla CUDA dalej nie mamy (67c C14).
- **Nie jako domyślny drafter Enigmy:**
  1. kontekst: DSpine-15 na 24 GB = 64k (q8_0) wobec 245–262k w przepisach; przy q4_0 szacuję ~70–100k `[INFERENCE: +~3.4 GB = 1.26 GB wag + kopie stanu GDN 16 × ~150 MB + bufory]`;
  2. proza/czat: na 3090 Ajaya proza 41.6 t/s = 1.47× AR, a nasze upstreamowe MTP n3 na 3090 daje 1.50× AR na całym `spec_sweep` (61.49/40.93, `67:15`). Na samym kodzie DSpine wygrywa wyraźnie (4.56× AR przy T=0) `[INFERENCE: inne prompty i karty]`;
  3. utrzymanie: jeden autor, fork bez PR do upstreamu, a Enigma pinuje upstream (b11856/b12110).
- **Ewentualnie:** opcjonalny „profil kod” na 5090 (32 GB) z ctx ≤ 128k, po teście T5.

---

## 5. Testowalne pomysły

Wszystkie wymagają GPU, więc kolejka po obecnych testach. Build forka Ajaya to CPU ~15–25 min, więc nie teraz.

| # | pomysł | oczekiwany zysk na XTX (model V(w,ctx)) | dokładny test | kill | pobranie |
|---|---|---|---|---|---|
| T1 | **τ DSpine per klasa na XTX bez portu**: fork Ajaya `d493f84`, `cmake -B build -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx1100`, cel bazowy UD-Q4_K_XL | rozstrzyga −67…+57% z §3 | `llama-server -m ~/models/Qwen3.8-27B-UD-Q4_K_XL.gguf -md Qwen3.8-27B-DSpine-b16-Q4_K_M.gguf --spec-type draft-dflash --spec-draft-n-max 15 -ngl 999 --spec-draft-ngl 999 -fa on -c 32768 -np 1 -ctk q8_0 -ctv q8_0 --spec-draft-type-k q8_0 --spec-draft-type-v q8_0` + ramię `--spec-type draft-mtp --spec-draft-n-max 4` w tym samym buildzie. `spec_sweep` 6 klas T=1 seed 1 + T=0 + `mvs`; zapisać tok/krok i ms/krok per klasa. Ramiona DSpine n 7 i probabilistic osobno | τ_DSpine/τ_MTP4 (ten sam build) < 1.55 na en-code **i** pl-kod → kill portu (próg serwerowy z §3, 2k–8k) | **1.26 GB** (Q4_K_M) |
| T2 | D(ctx) DSpine na HIP | potwierdza D = 7.5–10.5 ms | w T1: `ms/krok_DSpine − ms/krok` weryfikacji W16 (llama-bench `-p 16 -d 2k/8k/32k`) przy 2k/8k/32k | K2: D(2k) > 10 ms | 0 |
| T3 | port do topki za `LLAMA_SPEC_DSPINE=1` + kontroler „kod” (≤ 16k, ogon ma pierwszeństwo) | en-code +9…+57%, pl-kod −14…+33%, agent +0…+4% `[INFERENCE]` | G2 test zgodności tokenów vs fork Ajaya (T=0), potem ABBA `spec_sweep` 6×3 T=1 + `mvs` + replay agenta | K3 (§3.1) | 0 |
| T4 | VRAM z DSpine + MTP przy dużym ctx | – | fill test (jak `2026-11-06-ctx-262k-fit`) przy 196 608 i 229 376 | OOM przy 196k → profil kod tylko ≤ 131k | 0 |
| T5 | Enigma: DSpine vs MTP n3 na wynajętym 3090 i 5090 | – | fork Ajaya CUDA (i z PR #31533) vs pin Enigmy: `spec_sweep` T=1 + kod T=0 przy `-c 32768`, KV q4_0; fill test maks. ctx dla DSpine n 15 i n 7 | dla domyślnego: mediana `spec_sweep` < MTP n3 **albo** maks. ctx 24 GB < 200k. Dla „profilu kod”: < +25% na kodzie | 1.26 GB (na wynajmie) |
| T6 | lattice z głowy 64k (`draft_vocab_qwen38`) zamiast pełnej 248k | −0.8…−1.0 ms D (−0.75 GB odczytu Q6_K) `[INFERENCE]`, tylko klasa kod | po T3: ramię z przyciętą głową, ABBA kod | < +2% na en-code albo zmiana md5 | 0 |
| T7 | DSpine z polskimi danymi (SpecForge #1038) | jedyna droga do PL | poza zakresem: wymaga wynajmu GPU i stanów 27B | decyzja użytkownika ($) | – |

---

## 6. Ryzyka

- **Polski:** dane 27B nieujawnione, 8B tylko EN. Proza PL realnie −40…−67% (§3). Nigdy jako domyślny drafter PL.
- **Okno 8192:** agent ma p50 88k. τ poza oknem spada (v1: ~4.1 przy 13k). Zysk na kodzie znika powyżej ~16–32k.
- **Uncensored vs baza:** drafter trenowany na cechach bazowego Qwena. Fine-tune może obniżyć τ `[INFERENCE]`.
- **Bit-exact:** W16 > 8 kolumn wychodzi poza `LLAMA_SPEC_BITEXACT` (ZNANE 21a §7.1). Na CUDA szerokość zmienia md5 na 1/6 promptów (24e).
- **Fork:** jeden commit jednego autora (7 gwiazdek), bez testów `test-backend-ops` dla nowych tensorów i bez PR w upstreamie. Nazwy tensorów GGUF mogą się zmienić przy ewentualnym upstreamie, a GGUF-y Ajaya przestaną się wtedy ładować.
- **Liczby autora:** pojedyncze przebiegi, 10 promptów pod kod/matematykę, słaba baza AR i DFlash2, brak MTP (§1.3).
- **Klasyfikacja zmiany:** DSpine to drafter, więc wynik jest **bezstratny** (rozkładowo; T=0 identyczne tokeny modulo numeryka szerokiej weryfikacji). To optymalizacja szybkości, nie zmiana modelu.

---

## 7. Do ZRODLA (propozycje wierszy; wiki nie edytowałem)

| źródło | wersja | raport | werdykt | liczba | następnym razem |
|---|---|---|---|---|---|
| DSpine-27B (HF tencent/Qwen3.8-27B-DSpine-b16; github Tencent/DSpine) | HF `ea909c0` (11-07), repo `0cc92d8` (11-08) | R69a | SWA 8192, b16 vs DFlash2 b8; c=8 SGLang; kod treningu w SpecForge #1038; dane 27B nieujawnione | τ T=1 vs DFlash2: MT-Bench +3.6%, kod +8.5…+12.9% | dane treningu / wersja PL |
| Ajay9o9/llama.cpp `dspine` + HF aj9o9/Qwen3.8-27B-DSpine-b16-GGUF | `d493f84` na upstream `a691b23`; HF `62e9241` | R69a | 323 linie, tylko graf, lattice DFlash2; baza bez MTP, AR 3090 zaniżone | 3090: AR 28.2, DFlash2 50.6, DSpine 80.4 (T=1) / 90.1 (T=0); kod 128.7 przy 7.6 tok/krok; krok ≈ 1.68× AR | PR do upstreamu; wynik T1 na HIP |
| llama.cpp PR #31533 (few-row MMQ, CUDA) | otwarty (11-09) | R69a | weryfikacja 8–16 kolumn na NVIDIA tańsza | 3090 Ti DFlash2 58.87 → 43.81 ms/krok | merge → przeliczyć przepisy Enigmy |

---

## 8. Źródła

- https://huggingface.co/tencent/Qwen3.8-27B-DSpine-b16 (karta, `config.json`, tree API: `model.safetensors` 4 051 831 880 B)
- https://github.com/Tencent/DSpine (`0cc92d8`): `README.md:24-26,86-138`, `docs/sps_tuning.md`, `sglang_dspine/verification/calibration.json`, `dspine_mlx/README.md:75-99`
- https://github.com/Ajay9o9/llama.cpp/tree/dspine (`d493f84`; baza `a691b23`): `src/models/dflash.cpp:399-426,793-924,1329,1393`; `conversion/qwen.py:902-915,923-950`; `src/llama-quant.cpp:374-376`; `common/speculative.cpp:1069-1070,1385-1452`; `common/sampling.cpp:733-819`; `ggml/src/ggml-cuda/ggml-cuda.cu:6153-6372`
- https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF (v2 `62e9241`, v1 `b16fdf0` = `https://huggingface.co/aj9o9/Qwen3.8-27B-DSpine-b16-GGUF/raw/b16fdf0712/README.md`); pliki: Q4_K_M 1 257 892 896 B, Q8_0 2 201 447 456 B, BF16 4 061 850 656 B; `benchmark.png`
- Tweety autora: https://x.com/ItsmeAjayKV/status/2119440847720866213, https://x.com/ItsmeAjayKV/status/2119471531709608029; odpowiedź o c=8: https://x.com/guannanjiayou/status/2119453694219460770
- https://github.com/ggml-org/llama.cpp/pull/31533 (few-row MMQ, otwarty)
- https://github.com/sgl-project/SpecForge/pull/1038 (trening DSpine; nie czytałem treści PR, tylko odwołanie z README Tencenta)
- Nasze: `product/research/21a-dspine.md:13-35,116-161,261-282`; `wiki/metody/koszt-szerokosci-weryfikacji.md:12-24`; `wiki/lekcje/lekcja-akceptacja-h100-nie-przenosi-sie.md:10`; `product/research/67-nvidia-vast-kampania.md:13-15`; `wiki/produkt/final-recipes-nvidia.md:12,27-28`; `product/research/67c-nvidia-backlog-testow.md:130-131`; `product/research/67b-wybor-modeli-nvidia.md:102`; `product/research/68b-spekulacja-nowe.md:28`; `product/research/68d-swieze-od-spolecznosci.md:117,126`; `wiki/eksperymenty/2026-11-06-ctx-262k-fit.md:10`; `~/qwen-opt/spec_sweep.jsonl` (`kvq-md5-P-1`); `~/wt/topka-q63/src/models/dflash.cpp:35,473-560`; `~/wt/topka-q63/common/speculative.cpp:1057`
