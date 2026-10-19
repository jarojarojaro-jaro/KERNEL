# 21o — gemma.ai: techniki inferencji Gemma 4 a nasz silnik (MTP, klastrowa głowica, KV)

Data: 2026-10-19. Tylko CPU, bez pobierania modeli. Źródła: 28 stron gemma.ai z mapy strony (99 URL; wszystko, co dotyczy inferencji: `get-started/capabilities/mtp`, `get-started/qat`, `best-practices`, `models/gemma-4` + karta modelu, `models/gemma-3n`, `models/diffusiongemma` (4 strony), `deployment/{llamacpp,litert,vllm,sglang,ollama,mlx,huggingface}`, `tutorials/visual-guides/{mtp,gemma-4,gemma-4-12b,diffusiongemma}`, `gemma-explained/{gemma-2,gemma-3,recurrentgemma}`, `models/releases`), `config.json` 8 modeli z HF (kilka KB), kod upstream llama.cpp (snapshot 2026-10-09 w `~/llama-master`). Symulacje: `~/qwen-opt/re/cluster_head_sim{,2}.{py,md,json,log}`.

## Werdykt
1. **Klastrowa głowica w wersji Gemmy nie zastąpi naszego słownika 64k.** Wersja wierna Gemmie (2048 zbalansowanych klastrów, top‑32, ~5.9k wierszy) traci 4–11% trafień d1 względem 64k. Oszczędza tylko ~2.3% kroku, więc wychodzi na minus.
2. **Działa natomiast hybryda: słownik 64k plus klastry tylko dla ogona OOV** (183k tokenów, 2048 klastrów, k=8). Kosztuje +4.2% wierszy głowicy, czyli ~0.07 ms/krok (0.25%). Odzyskuje 35% luki 64k→pełny słownik na ukrytym stanie celu i 50–55% na prawdziwym ukrytym MTP. Szacunek netto: **+0.8…+1.4% t/s** `[INFERENCE]`. Pełna głowica z 24b (+5.6% kosztu) dawała tu minus. To jest kandydat nr 1.
3. **Współdzielenie KV celu przez drafter (Gemma) nasz MTP *nie* robi.** Ma własny KV (q4_0), wypełniany hakiem w prefillu i catch‑upem. Zysk po przeuczeniu głowicy byłby mały (dekodowanie ≤ +0.7%, TTFT −2.2–2.6%, −75 MB przy 64k), więc odpada.
4. **Gemma 4 dla produktu:** Qwen3.8‑27B zostaje flagowcem 24 GB (LCB v6 90.3 vs 80.0, GPQA 89.2 vs 84.3, HLE 30.8 vs 19.5; zestawienie BenchLM z danych producentów). Gemma 4 zostaje w katalogu dla 8/12 GB (E4B, 12B), wizji i wielojęzyczności. Znaleźliśmy dla niej **tani zysk silnikowy**: llama.cpp trzyma K i V osobno w globalnych warstwach K=V, choć dałoby się trzymać jedno (31B przy 64k: −2.7 GB i +6.8…11.8% t/s).

## Ranking technik (gemma.ai → my)
| # | technika (strona) | dotyczy nas? | zysk (arytmetyka) | test CPU / następny krok | kryterium odrzucenia |
|---|---|---|---|---|---|
| 1 | Hybryda: słownik 64k + klastrowy ogon OOV (z „Efficient Embedder”, `visual-guides/mtp`) | Qwen MTP: tak | Luka trafień d1 64k→pełny: 0.8504→0.8696. Hybryda k=8 daje 0.8571 (35%), na ukrytym MTP 50–55%. Sufit 24b +3.06% tok/krok × 0.35–0.55 = +1.1–1.7%. Koszt: 2725 wierszy × 4 przebiegi × 2.7 ns/wiersz plus ~3 kernele/przebieg ≈ 0.07 ms = 0.25%. Netto **+0.8…+1.4%** | Faza 0 zrobiona (sim). Dalej: offline akceptacja 4 głębokości w `mtp_torch.py` na CPU (podzbiór 10k pozycji). Potem GPU: `mul_mat_id` z klastrami jako „ekspertami” i wiersze w kolejności klastrów (jak `MASKED_EMBD_ORDERING`) | offline Δtok/krok < +0.5% albo GPU netto < +0.3% |
| 2 | K=V w globalnych warstwach Gemmy 4 (`visual-guides/gemma-4`, configi) | produkt (Gemma w katalogu) | Upstream liczy `Vcur = rms_norm(K_raw)` i zapisuje K i V osobno (`src/models/gemma4.cpp:244-266`). Wystarczy trzymać V i w FA wyliczać K = RoPE(w_knorm ⊙ V) (p‑RoPE 0.25, czyli obracane jest tylko 128 z 512 wymiarów). 31B: 10 warstw globalnych × 4 głowy KV × 512, czyli 80 KB/tok f16 → 40 KB. Przy 64k: −2.68 GB, odczyt 25.4→22.7 GB/krok, **+11.8% t/s** (KV q8_0: +6.8%), przy 8k +1.6%. 26B A4B przy 64k: odczyt 3.95→3.28 GB/krok (~2.3 GB aktywnych wag Q4 + 1.34 GB KV globalnego + 0.31 GB SWA), czyli +20% przy f16 i ~+12% przy q8_0 `[INFERENCE]` | wariant FA w ggml‑cpu + `test-backend-ops` na losowych tensorach (tolerancja f16), potem GPU XTX | < +3% t/s przy 32k (31B) albo KLD > 1e‑4 |
| 3 | „Efficient Embedder” dla asystentów E2B/E4B w llama.cpp (`mtp`, `#24282`) | produkt, tier 6–8 GB | Upstream odfiltrowuje tensory `masked_embd` przy konwersji i liczy pełną głowicę 262144×256 (67M z 76M parametrów draftera). Klastry: 2048 + 32×128 = 6144 wiersze (−97.7%). Szacunek: −~5% kroku E4B `[INFERENCE]` | wymaga GGUF asystenta (zakaz pobierania), więc później | przyspieszenie < 2% |
| 4 | Drafter czyta KV celu, ta sama pozycja dla wszystkich draftów (`mtp`, `speculative.cpp:1834,2059`) | Qwen MTP: nie robi tego dziś | Odpada catch‑up (0.2 ms ≈ 0.7%), hak MTP w prefillu (65/186/768 ms przy 2k/8k/32k, czyli 2.2–2.6% TTFT) i 1152 B/tok KV (1/17 KV). Wymaga przeuczenia uwagi MTP (Q‑only na KV warstwy 63) na GPU | brak sensownego testu na CPU bez treningu | spadek tok/krok > 0.7% po przeuczeniu (prawdopodobny) |
| 5 | Pełna klastrowa głowica jak w Gemmie zamiast 64k | Qwen MTP | Router C=2048, k=32: 5.9k wierszy, −0.65 ms/krok (+2.3%). Trafienia d1 0.755 vs 0.850 (cel), 0.682 vs 0.711 (MTP), czyli **−4…−11% d1** | sim zrobiona | **odrzucone** |
| 6 | Heurystyczna długość draftu +2/−1 (`mtp`, transformers) | Qwen | już testowane: T2 103.6 vs 102.7 (proza −5 t/s), `p-cum` 80.5 vs 80.3 | — | odrzucone wcześniej |
| 7 | „MoE przy bs=1: drafter 26B A4B może nie przyspieszać” (`mtp`) | LFM2.5 | Zgodne z naszym modelem u(N)=64(1−(60/64)^N). Potwierdza niski priorytet EAGLE‑3 dla LFM (raport 18) | — | — |
| 8 | QAT Q4_0 (`qat`): GGUF `-qat-q4_0-gguf`, asystent z `-qat-q4_0-unquantized-assistant` | katalog Gemmy | jakość przy 4 bitach, nie szybkość. Dla Qwena brak QAT | KLD QAT Q4_0 vs UD‑Q4_K_XL po zgodzie na pobranie | KLD QAT ≥ UD |
| 9 | Budżet tokenów obrazu 70–1120 (`best-practices`) | produkt (Qwen‑VL, `--image-max-tokens`) | 1120→280 to −75% tokenów obrazu w prefillu | domyślne wartości w UX | — |
| 10 | Bez myślenia w historii, z wyjątkiem tur z narzędziami (`best-practices`) | agent / cache prefiksu | usuwanie myśli unieważnia cache od pierwszej przyciętej tury `[INFERENCE]` | sprawdzić szablony Qwen/Gemma na trafienia cache w pętli agenta | — |
| 11 | PLE na hoście, MatFormer, warunkowe ładowanie (`gemma-3n`) | nie (Qwen/LFM tego nie mają). PLE z prefetchem już jest upstream (#29599) | — | — | — |
| 12 | 5:1 lokalne/globalne, SWA 512/1024, GQA 8:1 + 2× wymiar K, p‑RoPE 0.25, QK‑norm (`gemma-4`, `gemma-3`) | architektura (trening) | tylko jako kryterium wyboru modelu | — | — |
| 13 | DiffusionGemma: płótno 256 tokenów, 12–16 kroków, 15–20 tok/przebieg, >1100 t/s (H100 FP8) | brak w llama.cpp | jakość vs AR 26B A4B: LCB 69.1/77.1, AIME 69.1/88.3, Tau2 56.2/68.2 | — | za słaby dla agenta |
| 14 | 12B bez enkodera (35M zamiast 550M ViT), LiteRT MTP 2.2× GPU / 1.5× CPU na telefonie | projekt telefonu / wizja | — | — | — |

## (a) Klastrowa głowica a słownik 64k: symulacja CPU
Proxy: ukryty stan celu h_p (po `output_norm`, `ext_p1`, 69 207 pozycji; test na nieparzystych sekwencjach, 34 501 pozycji) oraz pełna macierz `output.weight` (Q6_K→f16). Kontrola: argmax = top‑1 llama w 98.0% przypadków. Głowica na podzbiorze daje ten sam draft co pełna wtedy, gdy pełny argmax leży w podzbiorze (**agree**). **hit** to P(argmax podzbioru == faktyczny następny token). Walidację zrobiliśmy na prawdziwym ukrytym stanie MTP: `d1h`, 1536 pozycji, 3 sekwencje, głównie PL proza, więc mała próba. Klastry liczone k‑means na wierszach `output.weight` (rzut 256‑d) i dodatkowo „router”, czyli centroidy douczone na połowie treningowej.

| schemat | wiersze/przebieg | agree (cel) | hit (cel) | hit (MTP d1h) |
|---|---|---|---|---|
| pełna głowica | 248 320 | 1 | 0.8696 | 0.7240 |
| **słownik 64k (dziś)** | 65 536 | 0.9731 | 0.8504 | 0.7109 |
| słownik 16k | 16 384 | 0.8381 | 0.7473 | 0.6406 |
| Gemma: 2048 klastrów zbalans., top‑32, k‑means | 5 875 | 0.7855 | 0.6934 | 0.5111 |
| Gemma: to samo, router | 5 936 | 0.8459 | 0.7552 | 0.6823 |
| **64k + ogon 2048 klastrów, k=8 (k‑means)** | 68 261 | 0.9825 | 0.8571 | 0.7174 |
| 64k + ogon, k=8 (router) | 68 298 | 0.9818 | 0.8564 | 0.7181 |
| 64k + ogon, k=32 (k‑means) | 70 354 | 0.9842 | 0.8584 | 0.7188 |
| 16k + ogon 2048, k=32 (k‑means) | 22 004 | 0.9336 | 0.8188 | 0.6849 |

Wnioski. Klastry zastępują słownik tylko przy małym budżecie: router przy 4–6k wierszy bije słownik 16k. Przy naszym koszcie głowicy (~2% kroku) liczy się jednak akceptacja, a tę daje słownik. Pełne pokrycie małym kosztem daje dopiero ogon klastrowy *na wierzchu* 64k. Większość dodanych wierszy to 2048 centroidów, więc C=512 i k=2 (~1.2k wierszy) warto sprawdzić następne. Router z małych danych (6k pozycji z masą w ogonie) nie pomaga, więc wystarczą k‑means. Na ukrytym MTP odzysk jest większy (50–55%), bo MTP częściej trafia poza 64k (agree 0.963 vs 0.973).

## (b) Czy nasz MTP współdzieli KV z celem?
Nie. Qwen3.8 MTP (`blk.64`) ma własne `wk/wv` i własny cache (q4_0, przy 94k q4_0 vs f16 97.5→100.6 t/s). Cache wypełnia hak MTP w prefillu i catch‑up po weryfikacji. Współdzielimy tylko `token_embd` (kopia 64k wierszy, +180 MiB, patch 0020) oraz `output` (podzbiór 64k). Asystent Gemmy ma tylko `wq/wo` (`gemma4-assistant.cpp:59-151`) i czyta ostatnią lokalną i ostatnią globalną warstwę KV celu. Wszystkie drafty idą na tej samej pozycji, więc niczego nie zapisuje do KV. U nas dałoby to tylko pozycje z tabeli (#4), a wymaga treningu na GPU. Nie robimy.

## (c) Gemma 4 jako model produktu
- **llama.cpp:** jest arch `gemma4` i asystent MTP (#23398 z 2026‑06‑07, E2B/E4B od #24282). Jest DSpark z backbone Gemma4 (#29226) i EAGLE‑3 od RedHatAI. „Efficient Embedder” nie jest zaimplementowany. K=V jest trzymane podwójnie. DiffusionGemma nie jest obsługiwana.
- **Wymiary drafterów (config):** 31B: 4 warstwy, hidden 1024, wspólny KV, bez klastrów (`use_ordered_embeddings: false`). Głowica 262144×1024 ≈ 268M to ponad połowa draftera, więc zysk z #3 dotyczy głównie E2B/E4B. E2B/E4B: hidden 256, 2048 centroidów, top‑32.
- **Tiery:** 8 GB → E4B (QAT Q4_0 4.5 GB z narzutem). 12 GB → 12B (6.7 GB, jest już w `models.tsv` z drafterem). 16 GB → 26B A4B Q3/Q4 (14.4 GB), bez MTP przy bs=1 (#7), za to z #2. 24 GB → Qwen3.8‑27B zostaje flagowcem (109–130 t/s z naszym MTP), a Gemma 31B to opcja do wizji i wielu języków; przy długim kontekście potrzebuje #2. Gemma nie publikuje akceptacji drafterów; jedyne liczby to LiteRT 2.2×/1.5× na telefonie.
- **Do zmierzenia (CPU, bez modelu):** tokeny na słowo PL dla tokenizera Gemmy (262k) wobec Qwena (2.69). Wymaga ~30 MB `tokenizer.json`, więc czeka na zgodę.

## Do bazy wiedzy
| folder | tytuł | treść |
|---|---|---|
| `eksperymenty/` | 2026-10-19 klastrowa głowica draftu (Gemma 4) vs słownik 64k | Gemma‑wierna (2048×~121, top‑32, 5.9k wierszy) traci 4–11% trafień d1, czyli odrzucone. Hybryda 64k + 2048 klastrów ogona, k=8: +4.2% wierszy, odzysk 35% (cel) / 50–55% (MTP) luki do pełnej głowicy. Szacunek +0.8…1.4% t/s; `~/qwen-opt/re/cluster_head_sim2.md` |
| `kernele/` lub `pomysly/` | K=V Gemmy 4: llama.cpp trzyma K i V osobno | V = rms_norm(K_raw), K = RoPE(w⊙V). Trzymanie samego V daje −50% KV globalnego. 31B przy 64k: −2.68 GB, +6.8…11.8% t/s |
| `modele/` | Gemma 4: architektura i draftery | 31B: 60 warstw (10 globalnych, 4 KV × 512, K=V, p‑RoPE 0.25), SWA 1024. 26B A4B: 30 warstw, 128 ekspertów (8 + 1 wspólny). Drafter: 4 warstwy, bez własnego KV, E2B/E4B mają 2048 centroidów i top‑32. Efficient Embedder nie jest w llama.cpp |
| `lekcje/` | Klastry bez słownika częstości nie wygrywają u nas | Głowica to ~2% kroku, akceptacja waży więcej. Klastry opłacają się tylko na ogonie OOV |
| `ludzie-firmy/` lub `zrodla/` | gemma.ai | mapa 99 stron; inferencja: `capabilities/mtp`, `qat`, `visual-guides/{mtp,gemma-4,gemma-4-12b}`, `diffusiongemma/*`, `deployment/*` |
