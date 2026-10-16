# 15d. Prefill i długi kontekst: PFlash v2, KVFlash, cache sesji a nasz stos

Data: 2026-10-16. Autor: agent ResPrefill. Zakres: Lucebox PFlash v2 (blog, PR #746, kolekcja HF), PFlash v1, KVFlash, dyskowy cache sesji Lucebox, przepis syv-ai/HyperQwen (prefix cache), nasze luki (prefill NVIDIA, dekodowanie przy 64k na 3090, pp4096 na XTX).
Metoda: kod i PR-y (git clone `Luce-Org/lucebox` @ `6f2b179`, 2026-10-15; `syv-ai/HyperQwen` @ `95ee3b6`), nagłówki GGUF (pobrane pliki), nasze drzewo `~/wt/3090-opt` (`cuda-3090-opt` @ `3da7a02ec`) i `amd-opt` @ `f61994f58`, upstream `ggml-org/llama.cpp` @ `f336359` (2026-10-16), issues/PR-y przez `gh api`. Lokalnego GPU nie używałem. Pilot PFlash liczyłem wyłącznie na CPU (Ryzen 7 5700X). Liczby bez źródła są oznaczone `[INFERENCE]` (rachunek) albo `[NIEZWERYFIKOWANE]`.

## TL;DR

1. **Nasza największa bezstratna strata przy długim kontekście na NVIDIA to kernel atencji, a nie prefill.** Na 3090 spadek dekodowania przy 64k co do milisekundy zgadza się z modelem „kernel vec czyta KV osobno dla każdej głowy Q w grupie GQA”: LFM przewidziane +3.05 ms/token, zmierzone +2.80 ms; Qwen przewidziane +7.7 ms przy 100% pasma, zmierzone +11.4 ms. Przy n ≥ 2 tokenach (weryfikacja MTP) Ampere idzie ścieżką MMA_F16, która **co krok konwertuje cały K/V warstwy do f16** (`fattn.cu:655-670`, `fattn-common.cuh:1041-1090`). Dekodowania MTP przy długim kontekście na NVIDIA **nikt u nas nie zmierzył**.
2. **Top bezstratny: port naszego kernela `kvq` (RDNA3) na CUDA**, czyli FA czytające KV q4_0/q8_0 bez konwersji, wszystkie głowy grupy GQA w jednym przejściu, n = 1..16. Szacunek: 3090 tg przy 64k Qwen 27.2 → ~37 t/s, LFM 147.7 → ~200 t/s (+36%) `[INFERENCE]`; MTP przy 64k +30–55% `[INFERENCE]`; do tego −0.27…−0.84 GB VRAM (bufor f16). Analog na XTX dał +65% przy 94k (43.0 → 70.9 t/s). Upstream CUDA tego nie zrobi: oba PR-y (#29827, #29846) zamknięte, maintainer: „Don't make new PRs for this. I'm not going to review them.” Metal właśnie dostaje to samo (PR #30645: 1.11–1.80× dla 4 głów KV / 6 głów Q, czyli kształt Qwen3.8-27B).
3. **PFlash v2 to tryb stratny i tak trzeba go sprzedawać.** Mechanizm: Qwen3.5-0.8B BF16 przelicza bloki 0–14 całego promptu. Trzy małe sieci na residualu po bloku 14 (sonda segmentów 263k parametrów, sonda żądania 265k, głowica Q/K 2.62M) tną prompt na całe jednostki i oceniają je względem pytania. Budżet: 31.5% przy 16K, 22.5% przy 120K. Cel prefilluje tylko zachowane jednostki, z markerami luk. Jakość: 92/124 vs 94 (6 zbiorów publicznych, CI −7…+3), LongBench-v2 4/12 vs 7/12, MTRAG 189/255 vs 197. TTFT ×3.7 na R9700, niezależnie powtórzone: ×3.3 przy 20K, ×4.0 przy 40K, ×5.4 przy 120K (issue #752).
4. **Dla naszego głównego obciążenia (agent kodujący) PFlash daje prawie zero.** Działa dopiero przy ≥16K *nowych, niecache'owanych* tokenów, historia agenta nigdy nie jest kompresowana, a nasze logi pokazują 91% trafień cache i medianę 25 nowych tokenów na turę. Cel to czat z długim dokumentem, RAG i duże wklejki.
5. **Pilot CPU ($0, ta sama kopia selekcji i te same GGUF-y): głowica PFlash działa po polsku, ale sonda żądania (trenowana po angielsku) nie.** Jednostkę z pytaniem jako top-1 wskazała w **1/10 przypadków PL i 10/10 EN**. W 9/10 PL za „żądanie” wzięła tytuł wklejonego dokumentu. Z poprawnym zapytaniem głowica stawia dowód na 1.–2. miejscu z 304 jednostek w 10/10 PL. Blend z release (stałe okna 50% + koniec promptu 25%) ratuje 10/10 PL, ale dowód spada na mediana ~10. miejsce (EN: 1.); bez blendu PL traci 4/10. Test był łatwy (BM25 też 10/10), więc to sygnał ryzyka, nie miara jakości odpowiedzi (§4).
6. **KVFlash nie jest dla nas.** „Bit-exact” dotyczy stronicowania, a atencja po 4K-slotowej puli jest stratna: igła 14/16 vs 16/16; zgodność tekstu GSM 8/10, MATH 4/10. Na hybrydzie, w której tylko 16 warstw ma atencję, większość jego zysku w dekodowaniu przy 64–128K odzyskuje bezstratnie punkt 2. Jego bazowy prefill (694 t/s przy 32K) jest wolniejszy od llama.cpp na tej samej karcie (1168 t/s, ich własny post PFlash).
7. **Dyskowy cache sesji to realny, bezstratny brak.** Lucebox: wznowienie 45K sesji agenta po restarcie w 2.6 s zamiast 56.2 s, bajtowo identyczna odpowiedź. llama-server ma tylko `--cache-ram` (RAM, ginie przy restarcie i przy zmianie modelu) i ręczne `/slots?action=save|restore`; checkpointy w pliku slotu są od #26004, który mamy. Upstreamowy `--cache-disk` (#28092) wisi, a ngxson pisze własną wersję. Dla produktu, który przełącza Qwen ↔ LFM, to −50…−120 s przy każdym powrocie do długiej sesji `[INFERENCE]`.
8. **Przepis syv-ai (22.4 → 0.56 s) to vLLM-owy prefix cache dla hybryd, który llama.cpp ma od dawna i domyślnie** (u nas na XTX: 27k dokument 31.9 s → 0.7 s). Nowe są dwie rzeczy z ich repo: dowód, że na 3090 da się trzymać MTP-3 przy 112k na 68.1 t/s (vLLM, KV fp8), oraz prefill vLLM 1595 t/s przy 16k wobec 1289 t/s llama.cpp na tej samej karcie (zapas MMQ ~20%).
9. **Prefill na NVIDIA:** fork traci 1.5–1.9% w llama-bench względem upstreamu z tymi samymi flagami. TTFT serwera jest za to o 4.8% gorszy od A1 i o 12% od A0. Większą część różnicy A0 → A1 robi narzut hooka MTP na prompt (150 ms przy 2k), który jest w upstreamie i u nas. Tani bisect (E4) plus złożenie hooka MTP w graf (L6) to razem ~5–7% TTFT.

## 0. Skąd biorą się milisekundy (nasze profile)

| platforma | pomiar | wartość | źródło |
|---|---|---|---|
| XTX, Qwen UD-Q4_K_XL | pp4096 llama-bench | 1115 t/s | `wiki/index.md` (stan 2026-10-15) |
| XTX | prefill serwera 6.6k / 29.5k / 94k | 962 / 943 / 767 t/s (94k = 123 s) | `wiki/kernele/prefill-mmq-fa.md` |
| XTX | podział 94k prefill | matmul ~70%, FA ~26% | `qwen-opt/research/v2/rr-prefill-kv.md:199-203` |
| XTX | MTP decode 1.7k / 94k | 92.9 / 70.9 t/s (po kvq) | `qwen-opt/NOTES.md:196-202` |
| 3090, Qwen (KV q4_0) | tg64 d0 / 8k / 32k / 64k | 39.3 / 37.7 / 32.3 / 27.2 | `BENCHMARKI-NVIDIA-2026-10-16.md:54` |
| 3090, LFM (KV q8_0) | tg64 d0 / 8k / 32k / 64k | 251.9 / 237.0 / 190.2 / 147.7 | tamże `:55` |
| 5060 Ti, Qwen (q8_0) | tg64 d0 / 64k | 28.9 / 20.2 | tamże `:97` |
| 5060 Ti, LFM (q8_0) | tg64 d0 / 64k | 198.8 / 114.7 | tamże `:98` |
| 3090, Qwen | pp512/pp4096 A0 / A1 / A2 | 1410/1396, 1404/1384, 1378/1363 | tamże `:31` |
| 3090, Qwen | prefill serwera 2k; TTFT | 1207/1075/1040 t/s; 2.14/2.29/2.40 s | tamże `:32-33` |
| XTX, agent omp (LFM) | trafienia cache | 91% tokenów, tura ~99.8%, mediana 25 nowych tok., prefill 3.8% czasu GPU; pełny prefill tylko na starcie sesji (7–10k tok.) | `qwen-opt/STATUS-NEXT.md:41` |

**Rachunek dla 3090 przy 64k (dekodowanie bez spekulacji).** Wszystkie liczby z nagłówków GGUF i specyfikacji (936 GB/s):
- Qwen3.8-27B: 16 warstw atencji × 4 głowy KV × 256 × (K+V) w q4_0 (18 B/32 wartości) = **18 432 B/token**. Przy 65 536 tokenach to 1.208 GB. Kernel vec czyta to 6× (GQA 6), więc 7.25 GB → **7.7 ms** przy pełnym paśmie. Zmierzony przyrost czasu tokenu 25.4 → 36.8 ms = **+11.4 ms** (68% pasma).
- LFM2.5-24B-A2B: 10 warstw GQA, 8 głów KV × 64 × 2 × 34/32 B = **10 880 B/token**, przy 64k 0.713 GB. ×4 (GQA 4) = 2.85 GB → **3.05 ms**. Zmierzone 3.97 → 6.77 ms = **+2.80 ms**.
- Jedno przejście po KV kosztowałoby 1.29 ms (Qwen) i 0.76 ms (LFM) przy 100% pasma. Realnie (75–80%): Qwen ~1.6 ms → **~37 t/s (+36%)**, LFM ~1.0 ms → **~200 t/s (+36%)** `[INFERENCE]`.

**Dlaczego vec czyta KV 6×:** `fattn-vec.cuh:108-111` (offset K/V liczony z `head / gqa_ratio`, jeden blok na głowę Q) i `:541` (`launch_fattn<D, cols_per_block, 1>`, czyli ncols2 = 1). **Dlaczego n ≥ 2 konwertuje:** na Ampere skwantyzowane KV trafia do VEC tylko przy `Q->ne[1] == 1` (`fattn.cu:660-663`), resztę bierze MMA_F16 (`:670`), które ma `need_f16_K/V = true` (`:743-748`), a `launch_fattn` przepisuje wtedy cały widok K/V do f16 (`fattn-common.cuh:1041-1090`). Na Ada/Blackwell granica to `ne[1] <= 2` (`:656-659`). Nasz `kvq` jest dostępny tylko dla `GGML_CUDA_CC_IS_RDNA3_0` (`fattn-kvq.cu:733-735`).

**MTP przy 64k na 3090 (szacunek, niezmierzone).** Weryfikacja 5 tokenów na warstwę: odczyt q4_0 75.5 MB, zapis f16 268 MB, a MMA z ncols2 = 2 czyta f16 3× (805 MB). Razem 1.15 GB × 16 warstw ≈ 18.4 GB, czyli **+20–24 ms/krok** przy 80–100% pasma. Krok rośnie z 38.4 ms do ~60–64 ms, co daje ~52–55 t/s przy niezmienionej akceptacji 3.31 tok/krok `[INFERENCE]`. Ten sam efekt widać na XTX przed kvq: d32768 n5 43.3 ms vs n1 31.1 ms; d98304 n5 68.2 → 36.7 ms po kvq (`NOTES.md:186,195`).

## 1. Audyt twierdzeń

R = roofline/Amdahl. „Bajtowo” = wyjście identyczne. HW = sprzęt.

| # | twierdzenie (dokładnie) | HW | model + kwant | obciążenie | batch | kontekst | baseline (strojony?) | wyjście / jakość | komenda | R | werdykt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | PFlash v2: „first token 3.7× sooner on average”, 4.7× przy 82–98K | R9700 32 GB | Qwen3.8-27B IQ4_XS (q4_0 KV), drafter Qwen3.5-0.8B BF16 | 6 zbiorów QA, greedy, bez myślenia | 1 | 16K–131K | pełny prefill w Lucebox (część „modeled” z innej karty, błąd <0.6%) | stratne; oficjalne metryki | tak (`luce_server … --prefill-compression auto`) | 90K: target ~21.6K tok. ≈ 19 s + drafter ~7 s + ~3 s = ~29 s vs 29.8 s ✓ | **wiarygodne** |
| 2 | „92 of 124 vs 94”; LongBench-v2 4/12 vs 7/12; pflash-bench 94/102 vs 98 | j.w. | j.w. | j.w. | 1 | 16K–98K | j.w. | 1 seed; CI −7…+3; prywatny zbiór niepowtarzalny | częściowo | — | **wiarygodne, ale w szumie**: w PR #746 (L40S) LongBench-v2 wypada 7/12 vs 6/12 *na korzyść* PFlash; autorzy: „About 1 answer in 10 flips between near-identical runs” |
| 3 | MTRAG: cała rozmowa 85 vs 160 s, 189 vs 197 trafień | R9700 | j.w. | 32 rozmowy, 255 tur, wklejka 44K | 1 | ~44–88K | **pełny prefill nie był uruchomiony na R9700, tylko zamodelowany** | sędzia LLM (Codex Sol 6.1) | nie | follow-up 5.4 vs 2.5 s (PFlash wolniejszy) | **wiarygodne tylko w specjalnym obciążeniu** (wklejka w środku czatu) |
| 4 | Dyskowy cache: 45K sesja agenta po restarcie: 2.6 s vs 56.2 s, „byte-identical” | R9700 | j.w. | wznowienie po restarcie | 1 | 45K | pełny prefill | bajtowo | brak skryptu w poście | 45K × ~22 KB + ~150 MB stanu ≈ 1.1 GB; NVMe 2–7 GB/s → 0.2–0.6 s + sufiks ✓ | **wiarygodne** |
| 5 | Niezależnie (#752, v2): 20K 18.9 → 5.7 s, 40K 45.9 → 11.5 s, 120K 233.3 → 43.0 s; drafter 11.09 s przy 120K | R9700 | j.w. | NIAH + ich prompty | 1 | 20–120K | ten sam serwer, krzywa release (efektywnie 0.317 przy 120K) | NIAH YES w obu | tak | drafter: ~252 TFLOP / 11.1 s ≈ 23 TFLOPS BF16 ✓ | **wiarygodne** (jakość potwierdzona tylko NIAH) |
| 6 | PFlash v1: „24.8 s vs ~257 s llama.cpp = ~10.4× at 128K” | RTX 3090 | Qwen3.6-27B Q4_K_M, drafter Qwen3-0.6B | NIAH single needle | 1 | 64K/128K | llama.cpp **zimny i „~”**; ich własny pomiar na ciepło 169.3 s; przy 64K baseline z FA off | NIAH 1/1 (test nasycony) | tak | keep 5% → ~6.5K tok.; ×6.8 vs ciepły baseline | **wiarygodne tylko w specjalnym obciążeniu** (NIAH, zimny baseline, keep 0.05) |
| 7 | KVFlash: „flat 38.6 tok/s from 64K to 256K”, 72 MiB KV na GPU | RTX 3090 | Qwen3.6-27B Q4_K_M, KV q8_0 | igła na głębokości 25%, 240 tok. | 1 | 32–256K | pełny cache w ich silniku | igła 14–15/16 vs 16/16 | `--longab` (test_kvflash) | pula 4K → atencja ≈ 0; AR na 3090 ~39–40 t/s ✓ | **szybkość wiarygodna; „accuracy unchanged” zawyżone** (n=10 na zestaw, zgodność tekstu GSM 8/10, MATH 4/10) |
| 8 | KVFlash: „prefill 2.8× at 256K (355 vs 999 s)” | j.w. | j.w. | j.w. | 1 | 256K | ich silnik: 32K pełny = 47.2 s (694 t/s) vs llama.cpp 28.1 s (1168 t/s) na tej samej karcie | prefill po puli = stratny | j.w. | — | **wiarygodne wobec słabego baseline'u; vs llama.cpp niezweryfikowane** |
| 9 | HyperQwen: „0.56 s TTFT on a follow-up turn against a 25k-token document instead of 22.4 s”, identyczne tokeny | RTX 3090 250 W | Qwen3.8-27B (vLLM, int4) | czat z dokumentem | 1 | 25K | vLLM bez prefix cache (domyślnie off dla hybryd) | bajtowo | tak (`labd_bench.py`) | restore zamiast 25K prefillu ✓ | **wiarygodne; dla nas nic nowego** (llama.cpp: 31.9 → 0.7 s na XTX) |
| 10 | HyperQwen: MTP-3 przy 112k: 68.1 t/s, 2.56 tok/krok; prefill 1k/16k/100k: 1812/1595/997 t/s | RTX 3090 250 W | j.w., KV fp8 | streaming, summarize/QA | 1 | 112K | — | bez zmian (spekulacja dokładna) | tak | 37.6 ms/krok; KV fp8 przy 112k ≈ 3.7 GB/forward → 3.9 ms ✓ | **wiarygodne** (zewnętrzny górny pułap dla 3090) |
| 11 | Upstream PR #29846: qwen35 27B, q4_0 KV, pp1024@d32768: ub2 ×1.21, ub4 ×1.18, ub8 ×1.10, ub512 ×1.02; tg bez zmian | RTX 3090 | qwen35 27B Q4_0 | llama-bench | ub 1–512 | 32K | master | test-backend-ops OK | tak | GQA 6 nadal czytane 3× (ncols2 = 2) → mały zysk ✓ | **wiarygodne** |
| 12 | Metal PR #30645: GQA-packed FA dla 1–4 tokenów: 1.11–1.80× przy 4 KV / 6 Q | M5 Pro | Qwen3.8-27B Q8_0 i in. | test-backend-ops + llama-bench | 1–4 | 8K–128K | master vec | test-backend-ops 5020/5020 | tak | redukcja ponownych odczytów KV ✓ | **wiarygodne** |

## 2. Mechanizm

### 2.1 PFlash v2: co dokładnie się dzieje (kod PR #746, `c2569a0`)

1. **Dopuszczenie** (`server/src/server/http_server.h:701-714`, profil `server/launch_profiles.h:332-351`). `PFLASH_ADMISSION=cache`: kompresja tylko wtedy, gdy cel musiałby prefillować ≥ `--prefill-threshold` (release: 16384) „droppable” tokenów, których żaden cache (RAM albo dysk: `DiskPrefixCache::longest_prefix`, `disk_prefix_cache.cpp:1064`) nie przywróci, i gdy cache trzyma mniej niż próg. Sesje z narzędziami są serwowane surowo (`:715-733`), chyba że `PFLASH_AGENT_PASTE=1`. W widoku unified (`PFLASH_UNIFIED=1`) stronicowana jest tylko najnowsza długa treść (wiadomość, wynik narzędzia), cięta w granicach linii.
2. **Drafter.** Qwen3.5-0.8B BF16 (unsloth, sha256 `cedf89af…`; head i sondy odmawiają innego pliku: `scoringhead.runtime_gguf_sha256`). Liczy się **tylko 15 bloków** (12 GDN i 3 pełnej atencji: 3, 7, 11), ubatch 1024 (`qwen35_drafter.cpp:170, 1285`). Koszt na token: ~0.31 G parametrów matmul (≈0.63 GFLOP, 77× mniej niż cel 48.6 GFLOP) plus atencja 24 576·n_kv FLOP `[INFERENCE z config.json]`. Przy 120K atencja dominuje. Sesje draftera są wznawialne co 8192 tokenów (`kScoringResumeGrid`) i trzymane w RAM, więc follow-up liczy tylko nowe tokeny.
3. **Tap:** residual po bloku 14 (`post_block14_residual_before_block15`).
   - **Sonda segmentów** (`segment-probe.gguf`, schema v2): LayerNorm(1024) → Linear(1024→256) → GELU(tanh) → 3 wiersze (unit, container, sub-unit). Każdy wiersz ma 5-tapowy splot symetryczny na logitach plus residual i sigmoid (`qwen35_drafter.cpp:1549-1669`). Cięcie zapada przy score > 0.8. Cięcia bliżej niż 32 tokeny od poprzedniego są scalane w przód. Jednostki dłuższe niż 512 tokenów dzielone są w granicach linii, najpierw po pustej linii (`pflash_selection.cpp:657-739`).
   - **Sonda żądania** (`request-probe.gguf`): LayerNorm → 1024→256 → GELU(erf) → 1 logit na token (`qwen35_drafter.cpp:1570-1583`). Jednostki ostatniej wiadomości użytkownika są rangowane maksimum logitu. Kandydat zapytania to ekstent tej wiadomości: jednostki powyżej największej luki wyników (`PFLASH_QUERY_CANDIDATES=1`). Jego masa jest mieszana z oknami stałymi (`tw_share` 0.5) i ostatnim tokenem promptu (`end_share` 0.25) (`pflash_query_candidates.h:13-26,102-104`). Jednostki top do 512 tokenów są zawsze zachowane dosłownie (`PFLASH_QUERY_PIN=512`).
   - **Głowica** (`seg-scoring-head.gguf`, `qwen3_5_0_8b_nope_qk_mass_v1`): wytrenowane Wq [1024→2048] i Wk [1024→512] w geometrii bloku 15. Liczenie: `x̂ = rms_norm(h14)·attn_norm15`, `Q = rms_norm(Wq x̂)·q_norm15`, `K = rms_norm(Wk x̂)·k_norm15`, softmax(QKᵀ/16) **bez RoPE**. Masa tokenu to suma po głowach i zapytaniach (`qwen35_drafter.cpp:1542-1544, 2296-2330`). Wynik jednostki to średnia masa (density).
4. **Selekcja:** pytanie, instrukcje, system prompt, definicje narzędzi i nagłówki ról są obowiązkowe. Resztę jednostek bierze się po gęstości aż do budżetu z krzywej `16384:0.315 32768:0.270 65536:0.270 120000:0.225`, w kolejności dokumentu. W miejscu luk wstawiany jest jednolinijkowy marker, a na górze notka, że tekst skrócono. Jeśli rozrzut trafności jest za płaski (`PFLASH_FALLBACK_SPREAD=0.11`, np. „wypisz wszystkie X”), idzie pełny prefill.
5. **Czat:** krótka nowa tura jest dopisywana dosłownie i trafia w cache. Pominięte linie wracają przez *recall*, gdy mają ≥ θ = 7.5% masy nowego pytania.
6. **Koszt i pamięć:** na 24 GB target i drafter się nie mieszczą (`--prefill-skip-park` mierzono na 32 GB). Bez tej flagi jest park/unpark celu (v1: ~3 s na żądanie). Na R9700 przy `--max-ctx 204800` szczyt to 30.6 z 31.9 GiB (PR #746).

**v1 → v2:** v1 używał Qwen3-0.6B, masy uwagi i rzadkiej atencji FlashPrefill/BSA (CUTLASS, sm_80+). Na ROCm BSA nie istniało, więc drafter liczył się gęsto: 343 s przy 120K i zysk tylko 1.38–1.51× (#752). v2 przechodzi na hybrydę Qwen3.5-0.8B (GDN liniowe, tylko 3 warstwy atencji w 15 blokach) i kompresja przy 120K spada do 11.3 s (30× szybciej, ten sam sprzęt).

### 2.2 KVFlash (`optimizations/kvflash/DESIGN.md`, `RESULTS.md`)
- Tensory KV są alokowane na pulę (np. 4K slotów). Pager mapuje pozycje logiczne na sloty w kawałkach po 64 tokeny. Zimne kawałki kopiowane są do RAM (0.6–1.3 ms/kawałek), a atencja liczy się po puli z maską ważności.
- Wybór rezydentów: LRU (0/16 poza oknem) albo drafter PFlash, który co 64 zdekodowane tokeny ocenia kawałki względem ogona (14–15/16).
- Prompt większy od puli → „pooled chunked prefill” z eksmisją w trakcie, czyli **prefill też jest stratny**.
- RoPE jest wpisane w K, więc relokacja jest legalna, a bajty wracają bit w bit. Stratność bierze się z tego, że atencja widzi 6–25% kontekstu.

### 2.3 Cache sesji: Lucebox vs llama-server (nasz)

| funkcja | Lucebox (`server/docs/PREFIX_CACHE.md`) | llama-server w `amd-opt` |
|---|---|---|
| prefiks w RAM | snapshoty na granicach tur (SHA-1 prefiksu), osobna pula „exact prefill” | slot + `--cache-ram` (domyślnie 8192 MiB, u nas 16384), wybór po LCP; wpis pomijany przy `f_keep < 0.25` (`server-task.cpp:1824`) |
| hybryda (stan rekurencyjny) | snapshot stanu przy każdej turze (#835) | checkpointy: start ostatniej wiadomości usera, starty co `-cms` (8192), n−4−ub i n−4 (`server-context.cpp:3979-4005`) |
| dysk | **automatycznie** przy eksmisji z RAM i przy zamknięciu (flush ≤120 s), budżet 128 GB, TTL 72 h, XXH64, identyfikacja modelu (path, size, mtime, SHA-1 1. i ostatniego MiB), typów KV, rotacji K, szablonu i draftu; zapis asynchroniczny (tmp+fdatasync+rename) | tylko ręcznie: `--slot-save-path` + `POST /slots/0?action=save|restore`; checkpointy w pliku od #26004 (jest w `amd-opt` i `cuda-v070`) |
| restore | przy lookupie: cały prompt, granice czatu i najgłębszy klucz na dysku; stan bit w bit | ręczny restore; nic automatycznego |
| przypięte nagłówki system/tools | tak (protected pins) | nie; współdzielony nagłówek trafia tylko przez żywy slot albo wpis z `f_keep ≥ 0.25` |

Upstream: `--cache-disk` (#28092, +1706 linii, open, „too complex” wg recenzenta). ngxson ma własną wersję na łańcuchowych hashach bloków tokenów. Sesyjny auto save/restore (#29738, open) wskazany do wstrzymania na tę wersję.

### 2.4 HyperQwen (syv-ai)
vLLM z `--enable-prefix-caching --mamba-cache-mode align`: przywraca KV prefiksu i stan GDN z ostatniej granicy bloku. Koszt: −16% puli KV (86 727 → 72 475 tokenów). Wynik: tury 2–4 przy 24k dokumencie trwają 1.15/0.85/0.89 s zamiast 23 s, tokeny identyczne (`single-user/README.md:153-168, 365-366, 506-508`). Mechanizmowo to samo co nasz slot + checkpointy.

## 3. Transfer na nasz stos i ranking

Wynik = (zysk na naszym wąskim gardle × pewność) / wysiłek. pd = osobodni.

### 3.1 Bezstratne (te same odpowiedzi albo różnica tylko w ostatnich bitach i bramka KLD)

| # | pomysł | atakowane ms | maks. zysk | pewność | wysiłek | platformy | ryzyko | wynik |
|---|---|---|---|---|---|---|---|---|
| L1 | **CUDA `kvq`**: FA na KV q4_0/q8_0 bez konwersji, GQA w jednym przejściu, n = 1..16, split-K + `flash_attn_combine_results` | 3090 przy 64k: +11.4 ms/token (Qwen), +2.8 ms (LFM); MTP: +20–24 ms/krok `[INFERENCE]` | tg@64k +36% (oba modele), MTP@64k +30–55%, VRAM −0.27 GB (64k) … −0.84 GB (204800) | wysoka dla tg (rachunek = pomiar), średnia dla MTP (baza niezmierzona) | 6–10 pd + ~$1.5 chmury | CUDA sm_80/86/89/120; HIP RDNA3 już jest; RDNA4 osobny port; Vulkan/Metal bez zmian | numeryka (f16 Q + mma zamiast q8_1 + dp4a): bramka KLD; md5 się zmieni | **1** |
| L2 | **Audyt cache agenta** (logi serwera, $0): skąd 7–10k pełnego prefillu na starcie sesji (zmienny system prompt? `f_keep < 0.25`? brak checkpointu?) i flagi `--cache-ram 32768 --ctx-checkpoints 96 -cms 2048` (już zalecane w `rr-prefill-kv.md:134-146`, niewdrożone) | start sesji agenta: Qwen XTX ~8–11 s, LFM ~1.7 s | → ~0.2–0.5 s na start sesji, jeśli prefiks jest stabilny `[INFERENCE]` | średnia (przyczyna nieustalona) | 0.5–1 pd | wszystkie | niskie; ewentualna zmiana szablonu (env → wiadomość usera, jak Strata #2175: 11.9 → 1.1 s) zmienia prompt | **2** |
| L3 | **Dyskowy cache sesji** (auto zapis przy eksmisji, przy zamknięciu i przy zmianie modelu; restore po hashu prefiksu; checkpointy w pliku) | restart lub przełączenie modelu: pełny prefill długiej sesji | 45K sesja Qwen na XTX ~48 s → ~1–2 s; 94k: 123 s → ~2–3 s `[INFERENCE]` | wysoka (mechanizm), średnia (częstość) | 4–7 pd albo przejęcie upstreamu | wszystkie | niskie (identyfikacja pliku: model, typy KV, szablon, draft) | **3** |
| L4 | **Hook MTP na prompt złożony w graf celu** + checkpoint n−4 ze snapshotu GDN zamiast osobnego dekodu (F3 w `rr-prefill-kv.md:148-172`) | prompt 2k: A0 → A1 = +150 ms TTFT na 3090; mały prompt: +40–80 ms + ~40 ms | TTFT −5–7% (2k), −40…−120 ms/żądanie | średnia | 3–5 pd | wszystkie | graf, rozjazd z upstreamem; bitowo (ta sama matematyka) | 4 |
| L5 | **Bisect regresji prefillu NVIDIA** (pp −1.5…−1.9% vs A1; TTFT +4.8%): kandydaci 0013 (prolog GDN, „nigdy nie uruchomione na NVIDIA” wg manifestu), 0045, 0043 | 3090: ~20–40 ms na 2k prompt | ≤2% pp, do ~5% TTFT razem z L4 | wysoka (znajdziemy), zysk mały | 1 pd + ~$0.2 | CUDA | niskie | 5 |
| L6 | **LFM `-b 2048 -ub 2048` w profilach** (MoE: mniej przejść po ekspertach) | prefill LFM | +56% pp4096 na 5060 Ti (4217 → 6587); XTX i 3090 niezmierzone | średnia | 0.5 pd | wszystkie | VRAM przy 131k; numeryka MMQ (podział batcha) → KLD | 6 |
| L7 | FA prefill na XTX: kafel GQA-6 (F6) | 94k: FA ~26% czasu | −6…−8% przy 94k, −3% przy 30k | średnia | 3–5 pd | HIP | kolejność akumulacji (lekcja 0043) | 7 |
| L8 | Głębokie MMQ na CUDA (vLLM na 3090: 1595 t/s przy 16k vs 1289 llama.cpp) | prefill matmul (~90% przy krótkim prompcie) | do ~+20% `[INFERENCE]` | niska | 10+ pd | CUDA | upstream to stroi | 8 |
| — | „Chunked prefill” w sensie vLLM | n/d: przy `-np 1` llama.cpp i tak dzieli prompt na ubatche; przeplatanie prefill/decode ma sens tylko przy współbieżności | 0 | — | — | — | — | odrzucone |
| — | GDN chunked (WY) dla prefillu | ≤2–3% (F9) | — | — | wysoki | — | — | odrzucone |

### 3.2 Stratne (osobny, jawnie opt-in tryb produktu; nigdy „te same odpowiedzi”)

| # | pomysł | zysk | koszt jakości | wysiłek | werdykt |
|---|---|---|---|---|---|
| Y1 | **PFlash v2** jako tryb „szybki odczyt długich dokumentów (przybliżony)” | TTFT przy ≥32K nowych tokenów: ×2.5–3.5 wobec *naszego* (szybszego) baseline'u na XTX `[INFERENCE]`; przy 120K nasz pełny prefill ≈ 165 s `[INFERENCE z NOTES]` vs ~50–55 s | −2/124 (publiczne), −4/102 (prywatne), −8/255 (MTRAG, późne tury), LongBench-v2 −3/12; sondy trenowane po angielsku | 15–25 pd (natywnie w llama-server) albo integracja ich serwera jako osobnego trybu | **pilot (E2), potem decyzja** |
| Y2 | KVFlash | dekodowanie płaskie przy ≥128K | igła 14/16; prefill po puli stratny | wysoki (pager w KV cache) | **nie**: L1 daje bezstratnie większość zysku do 128K |
| Y3 | Niższy kwant KV (KVarN k4v2, q3_K) | VRAM | HyperQwen: spekulacja przy 112k 2.13× wolniej (68.1 → 32.0 t/s), akceptacja −7% | — | nie |
| Y4 | Rzadka atencja prefillu celu (FlashPrefill/BSA w celu) | prefill O(S·k) | stratne, bez dowodu jakości na naszym modelu | wysoki | nie |
| Y5 | Eksmisja KV (StreamingLLM, H2O, SnapKV) | VRAM i dekodowanie | stratne | średni | nie |

**Jak PFlash wpiąłby się w llama.cpp, bez kodu Lucebox w ścieżce celu:**
1. Model: obcięty GGUF draftera (bloki 0–14, `output_norm` = 1), drugi kontekst `llama_context` w trybie embeddings (`pooling none`). Wykonalność na CPU sprawdziłem w pilocie (§4).
2. Sondy i głowica to ~3 matmule na token i jedna atencja zapytanie→kontekst (~13 MB wag). Można je liczyć w małym grafie ggml na tym samym backendzie.
3. Dopuszczenie w `server-context.cpp`:
   - po wyznaczeniu `n_past` (LCP + checkpoint) liczymy tokeny nowe = `n_prompt − n_past` dla najnowszej wiadomości;
   - jeśli ≥ 16384 i rozmowa nie ma narzędzi → kompresja;
   - wynikowy prompt i „widok” trzeba zapamiętać per rozmowa, żeby kolejna tura trafiła w cache. To jest najtrudniejsza część: template renderuje całą historię od nowa, więc widok musi zastępować treść tej wiadomości także przy następnych żądaniach.
4. VRAM na XTX: drafter BF16 1.5 GB + KV draftera ~6 KB/token (0.75 GB przy 128K). W trybie PFlash trzeba zejść z ctx 204800 do 131072 (−1.35 GB KV celu) albo parkować cel.

## 4. Pilot CPU: kopia selekcji PFlash v2 na polskim i angielskim tekście ($0)

**Cel:** czy sondy i głowica trenowane po angielsku znajdują pytanie i dowód w polskim tekście tak samo jak w angielskim? To główne ryzyko przeniesienia PFlash na nasz rynek.

**Ustawienie:**
- **Drafter:** `Qwen3.5-0.8B-BF16.gguf`, sha256 zgodne z `runtime_gguf_sha256` w trzech GGUF-ach PFlash. Obcięty do 15 bloków (`truncate_gguf.py`), tap liczony na CPU przez `llama-embedding --pooling none` (build `cuda-amdopt-cpu`).
- **Sondy, głowica i selekcja** odtworzone w numpy według kodu (§2.1).
- **Budżet:** krzywa release, ~30% tokenów przy 20–23K.
- **Pomijam** kandydatów zapytania z wielu wiadomości, recall i fallback spread. To uproszczenie.
- **Dokumenty:**
  - PL: 37 notatek wiki (`kernele/`, `lekcje/`, `eksperymenty/`), 50.5 KB = 22.9K tokenów;
  - EN: `rr-prefill-kv.md` + `rr-hip.md`, 53.5 KB = 19.8K tokenów.
- **Pytania:** 10 PL i 10 EN, faktograficzne, z jednoznacznym fragmentem-dowodem.
- **Ramiona:**
  - `head_probe`: zapytanie = jednostka top-1 sondy żądania, bez blendu (izoluje sondę);
  - `release_blend`: mieszanka zapytań z domyślnych wag release (`pflash_query_candidates.h:102-104`: `tw_share` 0.5, `end_share` 0.25): ekstent sondy przy największej luce wyników, okna ogona i głowy wiadomości, ostatni token promptu;
  - `head_oracle`: zapytanie = dokładne tokeny pytania;
  - `bm25`: BM25 po jednostkach z sondy segmentów;
  - `random`: losowe jednostki, 200 losowań.
- Metryka: czy cała jednostka z dowodem jest w zachowanym prompcie.
- Skrypty: [15d-pilot/](15d-pilot/) (`build_corpus.py`, `truncate_gguf.py`, `pilot.py`, `cases.json`, `results.jsonl`; ścieżki robocze w `/tmp/pflash/pilot`).

**Wyniki** (26 przypadków; ranga liczona od 0; pozycja 0 to zawsze ta sama jednostka startowa promptu, prawdopodobnie zlew uwagi `[INFERENCE]`):

| metryka | PL: dokument PL, pytanie PL (22.9K tok., budżet 29.7%, 304 jednostki) | EN: dokument EN, pytanie EN (19.8K tok., budżet 30.6%, 253 jednostki) |
|---|---|---|
| sonda żądania: top-1 jednostka = pytanie | **1/10** (9/10: tytuł pierwszej notatki „# 2026-10-12: cache promptu…”) | **10/10** |
| ekstent „gap” sondy zawiera pytanie | 8/10 | 10/10 |
| dowód zachowany, głowica z zapytaniem tylko z sondy (top-1) | **6/10** (rangi 1–275) | 10/10 (ranga 1) |
| dowód zachowany, blend release (25% ekstent sondy, 25% okno ogona 128, 25% okno głowy 256, 25% koniec promptu) | 10/10, rangi 1–25 (mediana ~10) | 10/10, rangi 1–2 |
| dowód zachowany, głowica z dokładnymi tokenami pytania (wyrocznia) | 10/10, rangi 1–2 | 10/10, ranga 1 |
| BM25 po tych samych jednostkach | 10/10 | 10/10 |
| losowe jednostki (średnia z 200 losowań) | 0.45 | 0.49 |
| czas tapu (15 bloków, BF16, CPU 16 wątków) | ~150 s (~150 tok/s) | ~124 s (~160 tok/s) |

Warianty krzyżowe (po 3 przypadki): pytanie PL do dokumentu EN: top-1 = pytanie 2/3. Pytanie EN do dokumentu PL: 1/3; w pozostałych wygrał tytuł dokumentu PL. Słabość zależy więc od obu czynników: od języka pytania i od polskiego tekstu, który „wygląda na prośbę”.

**Wnioski:**
1. Głowica Q/K przenosi się na polski: z poprawnym zapytaniem dowód jest pierwszą lub drugą jednostką treści w 10/10.
2. Słabym ogniwem jest sonda żądania. Release ma zabezpieczenie: 75% wagi zapytania nie zależy od sondy, a pin 512 tokenów i tak objął pytanie, bo było drugie w rankingu. Mimo to margines w PL jest ~10× mniejszy (ranga ~10 vs 1). Przy 120K (budżet 22.5%, więcej jednostek) i pytaniach parafrazowanych może to wyjść na jakości `[INFERENCE]`.
3. Tanie lekarstwo: dotrenować sondę żądania na polskich promptach. To LayerNorm + MLP 1024→256→1, 265k parametrów, na tapach liczonych na CPU. Eksporter GGUF jest w repo (`server/scripts/pflash/request_probe_gguf.py`); trenera Lucebox nie opublikował.
4. Test był łatwy: BM25 też 10/10, bo pytania dzielą słowa z dowodem. Nie mierzy przypadków bez wspólnych słów (NoLiMa), gdzie głowica ma wygrywać. Mierzy wyłącznie selekcję, nie odpowiedź celu.

**Ograniczenia:**
- n = 10 na język, po jednym dokumencie na język, różne typy dokumentów (notatki wiki vs raporty);
- uproszczona kopia: kandydaci zapytania i okna TW przybliżone, bez recall i bez fallbacku spread;
- długość ~20K, a nie 32–128K.

## 5. Projekty eksperymentów

### E1 (top bezstratny): CUDA `kvq`

**Hipotezy:**
- H1: na 3090 przyrost czasu tokenu przy 64k (Qwen +11.4 ms, LFM +2.8 ms) to w ≥80% ponowne odczyty KV przez vec (GQA 6/4).
- H2: weryfikacja MTP (n=5) przy 64k płaci +18–24 ms/krok za konwersję f16 i 3× odczyt.
- H3: kernel z jednym przejściem zbija przyrost do ≤2.5 ms (Qwen) / ≤1.3 ms (LFM).

**Fazy:**
- **Faza 0 ($0, lokalnie, bez GPU):**
  - kompilacja `nvcc` dla sm_86/89/120;
  - `cuobjdump -sass`: rejestry, spille, `LDG.E.128` dla wierszy K (wiersz q4_0 jednej głowy = 144 B = 9 × 16 B; stride 576 B, wyrównany);
  - tabela bajtów na wywołanie;
  - punkt startowy: loadery z PR #29846 (gałąź `Abai/llama.cpp:benchmark/cuda-fattn-mma-fused-dequant`, „bit-identical to master” dla dequantu kafli) plus pakowanie wierszy (token, głowa Q) jednej głowy KV jak w Metal #30645 i naszym `fattn-kvq.cu`.
- **Faza 1 (chmura, 3090, ~45 min, ~$0.25): baseline, którego nie mamy.** Wszystko z kolejnością ABBA i `-r 5`:
  1. `test-backend-ops perf -o FLASH_ATTN_EXT` dla hs=256, nh=24, nkv=4 (Qwen) i hs=64, nh=32, nkv=8 (LFM); kv ∈ {8192, 32768, 65536}; nb ∈ {1, 2, 5, 8}; KV q4_0 i q8_0;
  2. `llama-bench -fa 1 -ctk q4_0 -ctv q4_0 -d 0,32768,65536 -n 64 -p 5 -ub 5 -r 5` (pp5 ≈ krok weryfikacji);
  3. `nsys profile` 64 tokenów przy d65536: udział `flash_attn_ext_vec` / `convert` / `flash_attn_ext_f16`;
  4. `long_ctx_bench.py` z MTP n=4 przy promptach 8k/32k/64k (pierwszy w historii pomiar MTP przy długim kontekście na NVIDIA).
  - **Kill K1:** FA + konwersja < 20% czasu tokenu przy 64k (tg) **i** MTP@64k ≥ 70 t/s → E1 spada w priorytecie.
- **Faza 2 (lokalnie, 6–10 pd):** `fattn-kvq` dla CUDA:
  - mma.sync m16n8k16 f16, Q w rejestrach jako f16, dequant K do fragmentów;
  - V transponowane do smem jak w wersji HIP;
  - wiersze GQA × tokeny do 16 kolumn na kafel, split-K po KV z `flash_attn_combine_results`;
  - cp.async podwójne buforowanie (sm_80+);
  - wyłącznik `GGML_CUDA_KVQ=0`.
- **Faza 3 (chmura: 3090 + 5060 Ti, ~1.5 h, ~$0.6):**
  - **poprawność:** `test-backend-ops -o FLASH_ATTN_EXT` (wszystkie przypadki); KLD vs referencja f16-KV według `bramka-kld-kanarki`: KLD(nowy) ≤ KLD(stary vec q4_0) + 2σ, kanarki muszą FAIL;
  - **szybkość:** tg64 przy d 0/8k/32k/64k i pp5 przy tych samych głębokościach (ABBA, 5 powtórzeń); serwer MTP przy 32k/64k (3 seedy); `spec_sweep` krótki kontekst (regresja ≤1%); VRAM z logu.
- **Sukces:**
  - Qwen tg@64k ≥ +20% (cel ~37 t/s), LFM ≥ +20%;
  - MTP@64k ≥ +25%;
  - VRAM −≥250 MB przy 64k.
- **Kill:** < +10% przy 64k po strojeniu albo FAIL bramki KLD.
- **Koszt:** < $1.5 łącznie (3090 $0.20–0.31/h, 5060 Ti ~$0.15/h). **Wymaga zgody.**

### E2: pilot PFlash na naszym stosie

1. **Etap A (zrobiony, $0):** §4.
2. **Etap B ($0, CPU, ~1 dzień):**
   - rozszerzyć do ~60 przypadków PL+EN: wielokrokowe pytania, pytania „wypisz wszystkie X” (sprawdzenie fallbacku spread), kod;
   - zaimplementować kandydatów zapytania i pin dokładnie jak w `pflash_query_candidates.cpp`;
   - **dotrenować sondę żądania na PL** (pilot: top-1 trafia w pytanie 1/10 PL vs 10/10 EN): taps z CPU, etykiety = tokeny pytania w syntetycznych promptach PL/EN (dokument + pytanie na końcu, w środku i przed dokumentem), eksport `request_probe_gguf.py`. Kryterium: top-1 = pytanie ≥ 9/10 PL bez straty EN;
   - sprawdzić drafter Q8_0 zamiast BF16: zgodność selekcji ≥ 95% jednostek? To −0.7 GB VRAM.
3. **Etap C (chmura, ~$2):**
   - skompresowane prompty generujemy **offline na CPU** (nasza kopia), więc karta liczy tylko cel;
   - 3090 z naszym `llama-server` (Qwen3.8-27B UD-Q4_K_XL, KV q4_0, greedy, bez myślenia), dwa ramiona: pełny prompt vs skompresowany;
   - zbiory: LongBench-v2 (publiczne, ≥50 pytań zamiast 12), RULER QA, PL: ≥40 pytań do długich polskich dokumentów (publiczne teksty, nie wiki);
   - metryki: oficjalne metryki zbiorów; TTFT obu ramion; czas draftera zmierzony na GPU przez `llama-embedding` z obciętym GGUF-em.
   - **Hipoteza:** spadek trafień PL ≤ spadek EN + 3 pp; TTFT ×≥2.5 przy ≥32K.
   - **Kill:** spadek PL > 5 pp vs pełny prefill, spadek EN > 5 pp, albo TTFT < ×2 przy 64K.
4. **Etap D:** integracja tylko po pozytywnym C, jako opt-in tryb z jasnym opisem „odpowiedź z części dokumentu”.

### E3: audyt cache agenta ($0)
- Parsować `--log-file` serwera z sesji omp. Zbierać: LCP na starcie sesji, linie `restored context checkpoint`, `forcing full prompt re-processing`, odrzucenia `f_keep`, rozmiary checkpointów (`created context checkpoint … size =`).
- Hipoteza: pełne 7–10k na starcie sesji biorą się ze zmiennego nagłówka (data, cwd, git status w system prompcie), a nie z braku cache.
- Kill: LCP na starcie ≥ 90% nagłówka i mimo to pełny prefill → błąd w serwerze, osobne zadanie.

### E4: bisect prefillu NVIDIA (~$0.2)
- 3090, 30 min: `nsys` pp512 i pp4096 upstream A1 vs fork, różnica per kernel.
- Przełączniki `GGML_HIP_*` działające na CUDA, w tym prolog GDN 0013.
- Serwer: TTFT 2k z `--spec-type none` vs MTP, żeby rozdzielić hook MTP od kodu forka.
- Kill: różnica per kernel < 1% → zostawić.

## 6. Dowody zewnętrzne

- **PFlash v2 szybkość:** niezależne powtórzenie (#752, użytkownik `aiworkeryuan-chuxi`, R9700, ten sam dzień co release): ×3.3/×4.0/×5.4 przy 20K/40K/120K. Jakość tylko NIAH, a efektywny keep wyszedł 0.317 zamiast 0.225, więc krzywa nie zadziałała w pełni. **Jakości na LongBench/MTRAG nikt poza autorami nie powtórzył** `[NIEZWERYFIKOWANE]`.
- **PFlash v1:** issue #82 (RTX 5090): NIAH przy keep 0.05 i 128K najpierw zgłoszony jako niepowtarzalny, potem odwołany przez zgłaszającego. Issue #327: PFlash niszczył definicje narzędzi (6.5K → 277 tokenów); w v2 sesje z narzędziami są serwowane surowo.
- **Lucebox na gfx1100:** #457: `dflash_server` ~2× wolniejszy od llama.cpp, SIGSEGV przy długim kontekście (ROCm 6.4.1). Integracja ich serwera na naszym XTX nie jest „za darmo”.
- **Kernel GQA dla małych batchy:** Metal #30645 (1.11–1.80× przy 4/6 głowach); upstream CUDA odrzuca (#29827, #29846). Issue #29371 i #29826 (bufor konwersji f16 zjada 8.7–13.3% oszczędności VRAM z kwantyzacji KV przy 131k) są otwarte.
- **Pułap 3090:** HyperQwen (vLLM) MTP-3 68.1 t/s przy 112k. To mocny zewnętrzny dowód, że nasze (szacowane) ~52–55 t/s przy 64k to problem kernela, nie sprzętu.
- **Disk cache w llama.cpp:** #26004 scalony (checkpointy w pliku slotu, potwierdzony przez 10 osób na CUDA/Metal/Vulkan; 181.9 s → 4.7 s po restore na gfx1151). #28092 i #29738 otwarte.
- Co by potwierdziło lub obaliło E1: pomiar Fazy 1. Jeśli MTP@64k na 3090 już dziś ≥ 70 t/s, mój model konwersji jest zły.

## 7. Źródła

- Lucebox blog: https://www.lucebox.com/blog/pflash-v2 ; https://www.lucebox.com/blog/pflash ; https://www.lucebox.com/blog/kvflash
- PR #746: https://github.com/Luce-Org/lucebox/pull/746 (merge `c2569a0a57bdcec03994f064bb7b663b50bf66a2`, +27645/−2997, 125 plików)
- Repo `Luce-Org/lucebox` @ `6f2b17958ebb49f2b7060ac0a40ce6509aa90039`:
  - `server/src/pflash/qwen35_loader.cpp:28-47,103-123,154-252`;
  - `server/src/pflash/qwen35_drafter.cpp:170,1060-1107,1540-1720,2238-2330`;
  - `server/src/pflash/pflash_selection.cpp:657-739`;
  - `server/src/server/http_server.h:701-733`; `server/src/server/launch_profiles.h:325-364`;
  - `server/docs/PFLASH_CONFIGURATION.md`, `server/docs/PREFIX_CACHE.md:99-249`, `server/docs/SPEC_PREFILL.md`;
  - `optimizations/kvflash/RESULTS.md`, `optimizations/kvflash/DESIGN.md:111-201`.
- Issues Lucebox: #752 https://github.com/Luce-Org/lucebox/issues/752 ; #457 …/issues/457 ; #82 …/issues/82 ; #327 …/issues/327
- HF: https://huggingface.co/collections/Lucebox/pflash ; https://huggingface.co/Lucebox/pflash-segment-probe (sha256 `470b7b0e…`) ; https://huggingface.co/Lucebox/pflash-request-probe (`5915557d…`) ; https://huggingface.co/Lucebox/pflash-scorer-head (`95e13076…`) ; drafter https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF (BF16 sha256 `cedf89af31c9041b601fa58303285bc46d99c51baee1b13f5e919626ca526ee5`) ; config https://huggingface.co/Qwen/Qwen3.5-0.8B/blob/main/config.json
- HyperQwen @ `95ee3b64b0df7014ee2626529524d6b99c3dcdd1`: `single-user/README.md:149-168,357-369,506-508`; `docs/long-context.md:24-63`; `docs/benchmarks.md` — https://github.com/syv-ai/HyperQwen
- llama.cpp: PR #29846 https://github.com/ggml-org/llama.cpp/pull/29846 ; #29827 …/pull/29827 ; #30645 …/pull/30645 ; #28092 …/pull/28092 ; #29738 …/pull/29738 ; #26004 …/pull/26004 ; issues #29371, #29826, #27623, #27109
- Nasze drzewo `~/wt/3090-opt` (`cuda-3090-opt` @ `3da7a02ec`): `ggml/src/ggml-cuda/fattn.cu:634-670,743-752`; `fattn-vec.cuh:108-111,531-541`; `fattn-common.cuh:1041-1090`; `fattn-kvq.cu:1-30,726-755`. `amd-opt` @ `f61994f58`: `tools/server/server-context.cpp:1728-1742,3979-4005`; `tools/server/server-task.cpp:1804-1830`; `common/common.h:650-652`.
- Nasze pliki: `product/BENCHMARKI-NVIDIA-2026-10-16.md:17-62,94-98`; `qwen-opt/NOTES.md:182-213`; `qwen-opt/STATUS-NEXT.md:40-44`; `qwen-opt/research/v2/rr-prefill-kv.md`; `product/research/patch-manifest.json` (0013, 0043, 0045); `qwen-opt/research/strata/update-v0.1.44.md:128`.
- Specyfikacja GA102 (3090: 936 GB/s; INT8 tensor 284 TOPS dense): https://www.nvidia.com/content/PDF/nvidia-ampere-ga-102-gpu-architecture-whitepaper-v2.pdf

## Do bazy wiedzy

Notatki do dodania lub zmiany (główny agent; liczby ze źródłami):

1. **research/raport-15d-prefill-dlugi-kontekst.md** (nowa, `typ: research`). Streszczenie raportu:
   - na NVIDIA bezstratnie najwięcej daje port `kvq` na CUDA (3090 tg@64k: Qwen 27.2, LFM 147.7; rachunek ponownych odczytów GQA zgodny z pomiarem: LFM +3.05 ms przewidziane vs +2.80 ms zmierzone);
   - PFlash v2 to stratny tryb opt-in (92/124 vs 94; TTFT ×3.7 na R9700; niezależnie ×3.3/×4.0/×5.4 przy 20K/40K/120K, #752);
   - KVFlash: nie;
   - dyskowy cache sesji: tak, bezstratnie;
   - przepis syv-ai: nic nowego dla llama.cpp.
   - Źródło: ten plik §TL;DR, §0, §3.
2. **kernele/fattn-kvq.md** (aktualizacja). Dopisać sekcję „Luka na CUDA”:
   - vec czyta KV raz na głowę Q (`fattn-vec.cuh:108-111,541`);
   - na Ampere n ≥ 2 → MMA_F16 z konwersją całego K/V do f16 (`fattn.cu:655-670,743-748`; `fattn-common.cuh:1041-1090`);
   - 3090 tg64 przy 64k: Qwen 39.3 → 27.2, LFM 251.9 → 147.7 (`BENCHMARKI-NVIDIA-2026-10-16.md:54-55`);
   - szacunek po porcie: ~37 / ~200 t/s `[INFERENCE]`;
   - plan E1. `status: do-sprawdzenia` dla szacunków.
3. **nvidia/fa-kv-kwantyzowane-cuda.md** (nowa, `typ: nvidia`). Jak upstream CUDA wybiera kernel FA dla KV q4_0/q8_0:
   - VEC przy n=1 (Ampere) / n ≤ 2 (Ada+), inaczej MMA_F16 z buforem f16;
   - bufor f16 to 268 MB przy 64k i 839 MB przy 204800 dla Qwena;
   - upstream odrzucił #29827 i #29846 (maintainer: „Don't make new PRs for this”);
   - #29846 zmierzył dla qwen35 27B na 3090 ub2 ×1.21, ub4 ×1.18, ub512 ×1.02;
   - Metal #30645 robi pakowanie GQA (1.11–1.80× przy 4/6 głowach).
   - Linki: issues #29371, #29826.
4. **repo/lucebox.md** (aktualizacja; HEAD `6f2b179`, 2026-10-15):
   - PFlash v2 (PR #746, merge `c2569a0`): drafter Qwen3.5-0.8B BF16 (sha `cedf89af…`), 15 bloków, sonda segmentów (263k param.), sonda żądania (265k), głowica Q/K NoPE (2.62M), krzywa 16384:0.315 → 120000:0.225, próg 16K niecache'owanych tokenów, sesje z narzędziami surowo;
   - jakość 92/124 vs 94, LongBench-v2 4/12 vs 7/12 (w PR na L40S 7/12 vs 6/12, czyli szum), MTRAG 189 vs 197 (pełny prefill tylko modelowany);
   - KVFlash stratny (igła 14/16, GSM zgodność tekstu 8/10), baseline 694 t/s prefill;
   - dyskowy cache sesji: 45K po restarcie 2.6 s vs 56.2 s;
   - #457: na gfx1100 `dflash_server` ~2× wolniejszy od llama.cpp.
   - Werdykt bez zmian (średnia), ale „PFlash: pilot”.
5. **eksperymenty/2026-10-16-pflash-pilot-cpu.md** (nowa, `typ: eksperyment`). Pilot CPU kopii selekcji PFlash:
   - sonda żądania top-1 = pytanie: PL 1/10, EN 10/10;
   - dowód zachowany: głowica z zapytaniem z sondy PL 6/10, EN 10/10; blend release PL 10/10 (ranga mediana ~10) vs EN 10/10 (ranga 1); wyrocznia PL 10/10;
   - BM25 10/10 w obu (test łatwy);
   - tap na CPU ~150 tok/s.
   - Źródło: [15d-pilot/results.jsonl](../../product/research/15d-pilot/results.jsonl), §4 tego raportu.
6. **lekcje/lekcja-sondy-en-na-polskim.md** (nowa, `typ: lekcja`). Małe sondy trenowane po angielsku (request probe PFlash) mylą polski tytuł dokumentu z prośbą użytkownika (9/10). Przed przyjęciem cudzych klasyfikatorów na aktywacjach zawsze test PL vs EN na naszych tekstach; główna głowica może przenosić się dobrze, a pomocnicza nie.
7. **lekcje/lekcja-baseline-wlasnego-silnika.md** (nowa, `typ: lekcja`). „Nx szybciej” w postach Lucebox bywa liczone względem ich własnego silnika albo zimnego llama.cpp:
   - KVFlash: pełny prefill 32K 47.2 s = 694 t/s wobec 1168 t/s llama.cpp na tej samej 3090;
   - PFlash v1: „~257 s” na zimno vs 169.3 s na ciepło.
   - Zawsze sprawdzać baseline (`optimizations/kvflash/RESULTS.md`, blog PFlash v1).
8. **repo/hyperqwen.md** (nowa, `typ: repo`). `syv-ai/HyperQwen` @ `95ee3b6`, vLLM na RTX 3090 250 W:
   - prefix cache dla hybryd 22.4 → 0.56 s przy 25k (to samo co nasz slot + checkpointy);
   - MTP-3 przy 112k 68.1 t/s (2.56 tok/krok, KV fp8);
   - prefill 1k/16k/100k 1812/1595/997 t/s;
   - KVarN k4v2 spowalnia spekulację 2.13×.
   - Wartość: górny pułap dla naszego 3090.
9. **produkt/tryb-stratny-pflash.md** (nowa, `typ: produkt`, `status: do-sprawdzenia`). Propozycja: PFlash tylko jako jawny tryb opt-in „szybki odczyt długich dokumentów (przybliżony)”:
   - nie dla sesji agenta (≥16K nowych tokenów, historia surowa);
   - na XTX wymaga ctx 131072 zamiast 204800 albo parkowania celu;
   - decyzja po E2 etap C.
10. **eksperymenty/2026-10-12-cache-promptu-i-a7.md** (aktualizacja). Dopisać:
    - wpisy `--cache-ram` z `f_keep < 0.25` są pomijane (`server-task.cpp:1824`);
    - checkpoint startu pierwszej wiadomości usera powstaje zawsze, gdy lista jest pusta (`server-context.cpp:3979-3985`);
    - propozycja E3 (audyt startu sesji agenta) i Strata #2175 (env → wiadomość usera: 11.9 → 1.1 s).
11. **AUDYT.md**: dopisać nowe liczby z punktów 1–10 z wierszami źródeł (BENCHMARKI:54-55, NOTES:186-202, blog PFlash v2, issue #752, PR #746, RESULTS.md KVFlash, HyperQwen README:153-168, long-context.md:30-57).
