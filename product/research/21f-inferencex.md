# 21f — InferenceX / AgentX (SemiAnalysis) i „megakernel” Kimi K3 w vLLM: co z tego dla lokalnego single-user

Data: 2026-10-19. Tylko CPU, bez GPU i bez chmury. Klony: `/tmp/inferencex` (InferenceX @ `b9c6fc30`, 2026-10-18), `/tmp/inferencex-app` (dashboard), korpus AgentX v1.0 256k (`/tmp/agentx/traces.jsonl`, 569 MB z HF).
Skrypt tego raportu: `21f-agentx-stats.py` (statystyki śladów AgentX + model Amdahla lokalnego odtworzenia na XTX). Surowe wyjście: `21f-agentx-stats-out.txt` (Qwen i LFM).
Oznaczenia: `[SZACUNEK]` = nasz rachunek; `[NIEZWERYFIKOWANE]` = nie sprawdzone u źródła ani pomiarem; `[INFERENCE]` = wniosek bez pomiaru; **O** = porównanie orientacyjne (inne warunki).

## TL;DR

1. **arXiv 2605.08513 nie jest pracą o InferenceX.** To „A Single Neuron Is Sufficient to Bypass Safety Alignment in LLMs” (Kazemi, Chegini, Safi, 2026-05-08). Publicznej pracy naukowej o InferenceX/AgentX nie znalazłem. Metodologię opisują strona `/agentx/methodology`, kod w repo i SPEED-Bench (arXiv 2604.09557). Krótko o 2605.08513 w §9.
2. **Co mierzy AgentX.** Serwer odtwarza 393 sesje Claude Code z 06-2026. Zachowane są długości, współdzielenie prefiksów (hashe bloków 64 tokenów), drzewo subagentów i przerwy na narzędzia. Treść jest **syntetyczna**. Każdy punkt to jedna współbieżność na świeżym serwerze, okno pomiaru 1 h (minimum 900 s). Główna metryka „P90 interactivity” to `1 / p90(średnie ITL na zapytanie)` (`request_metrics.py:65-84`). Spekulację mierzą z **wymuszoną długością akceptacji** (golden AL z SPEED-Bench), nie z rzeczywistej.
3. **Najważniejsza wada z naszej perspektywy:** syntetyczna treść i wymuszona AL wyłączają z pomiaru dokładnie to, co u nas daje największy zysk: rzeczywistą akceptację MTP i ogon lookupu na edycjach kodu (×2.4 na `mvs`). Do tego **c=1 przez 1 h to na XTX ok. jedna sesja** (`[SZACUNEK]` ~20 s na zapytanie wobec mediany 174 zapytań na sesję), więc wynik zależy od seeda. „Throughput per GPU” w ~99% składa się z tokenów wejścia trafiających w cache (Kimi K3, c=1: 1554 tok/s/GPU łącznie, 10.1 wyjścia).
4. **Najcenniejsze dla nas są ślady, nie wyniki.** Puściłem korpus 256k przez model Amdahla z naszymi krzywymi XTX (`21f-agentx-stats.py`):
   - mediana wejścia to 88.8k tokenów, wyjścia 376; stosunek wejście:wyjście **117:1**;
   - przy limicie kontekstu 128k zostaje 66% zapytań, przy 64k 35%;
   - **Qwen na XTX:** w prawie lokalnym (`-np 1` + `--cache-ram`, polityka „cram”) prefill zajmuje **148 h z 256 h** zegara (58%), a decode 82 h (32%);
   - **×2 na decode skraca zegar sesji agentowej tylko o 10–26%** (zależnie od cache), a ×2 na prefillu o 18–37%;
   - współdzielenie prefiksu między subagentami (radix zamiast osobnego slotu na tor) tnie prefill 148 → 67 h;
   - **LFM:** przy dobrym cache (radix, lane, cram) decode to 52–62% zegara, a prefill 15–29%; przy jednym slocie bez RAM-cache decode 39–47%.
   Dla Qwena w pracy agentowej **więcej daje prefill i cache prefiksów niż kolejne kernele decode.**
5. **Werdykt o standardzie:** AgentX **nie** powinien zastąpić `spec_sweep` / `copy` / `mvs` / `long_ctx_bench`, bo nie mierzy akceptacji, jakości ani bitowości, a punkt trwa ponad 1.5 h. Przyjmujemy z niego trzy rzeczy:
   - (a) **rozkład kształtu** jako model priorytetów (zrobione, skrypt);
   - (b) okazjonalny **test systemowy** cache/slotów oficjalnym harnessem przy c=1, bez spekulacji (plan w §7);
   - (c) **własny „PodX”**: odtwarzanie o kształcie AgentX z **prawdziwą** treścią sesji omp (`~/.omp/agent/sessions`, 1.2 GB; mamy `capture_proxy.py`/`replay.py` z 16f), jako nowy poziom benchmarku agentowego.
6. **Qwen3.8-27B jest na InferenceX** jako model eksperymentalny: bf16, 1×H100, vLLM + drafter DSpark k=7, 1k/1k na losowych tokenach. Przy c=1 mediana to **86.1 tok/s**, p90 67.4, AL ≈ 2.0 (run 35359530151, PR #3260, niescalony). Nasz XTX (Q4_K_XL + MTP4) daje 109.0 t/s na `spec_sweep` (`REKORDY.md:22`), czyli ~1.27× przy 3.2× mniejszej liczbie bajtów na token (**O**: inne kwanty, prompty i T).
7. **Kimi K3 „megakernel” to nie megakernel.** Ten sam PR opisano jako „Specialized Decode”: 23 → 13 kerneli na warstwę i 130 → 69 µs na warstwę. Na 16×GB300 krok B1 bez spekulacji spada z 7.38 do 3.90 ms (1.89×), co daje `[SZACUNEK]` 8% → 15% pasma HBM, więc to reżim latencji i komunikacji TP.
   - **842 t/s wymaga syntetycznej AL = 6.** Golden AL samego InferenceX dla K3 DSpark DL7 na kodzie to 3.78 (`kimik3_dspark.yaml:17`). Przy tej samej długości kroku daje to ~530 t/s, a PR przy ISL 32k i AL 3.78 podaje 483 t/s.
   - **„1.8× P90 interactivity na AgentX”** porównuje 16 GPU z 8 GPU.
8. **Fuzja decode na naszych kartach (jedno konsumenckie GPU):** ~70% technik K3 to fuzja z komunikacją multi-GPU, której nie mamy. Wnioski 15a/16a się nie zmieniają.
   - Pełny megakernel się nie opłaca: Qwen ma sufit +3–6% decode, czyli −1…−3% zegara sesji agentowej.
   - LFM: sufit +12–28% decode (15a), ale X1–X3 z 16a padły (~+3%).
   - Do przeniesienia: (i) specjalizacja kerneli pod szerokości weryfikacji M = 5…17 (MTP4 + ogon W16); (ii) reguła „przed czekaniem ładuj tylko statyczne wagi”; (iii) bramka numeryczna „szum 1-ulp”; (iv) RMSNorm liczony redundantnie w prologu konsumenta zamiast osobnego kernela. Minimalne eksperymenty w §8.5.
9. **Pełne pokrycie strony (§11):**
   - InferenceX nie mierzy żadnej karty konsumenckiej ani llama.cpp;
   - z 60 przykładów optymalizacji przenosi się 9 testów, na czele zapis przyrostowy do `--cache-ram`, tokenizacja per tura i stan MTP po przywróceniu;
   - golden AL Qwen3.8-27B (PR #3304: thinking on n=4 2.72, off 3.79) obejmuje nasze 3.0 tok/krok.

## 1. Co jest czym (źródła pierwotne)

| element | co to | źródło |
|---|---|---|
| InferenceX (dawniej InferenceMAX) | ciągły benchmark serwerowy: fixed-sequence 1k/1k, 1k/8k, 8k/1k (random tokens, `ignore_eos`) + AgentX; wyniki z publicznych GitHub Actions | https://inferencex.semianalysis.com/about; `inferencex-e2e/infx/bench/fixed_seq.py:40-47` |
| AgentX v1.0 | replay 393 sesji Claude Code (opt-in proxy), 64-tokenowe łańcuchowe hashe bloków, DAG agent → subagenci, 1 h profilowania, warmup od losowego punktu 25–75% sesji | https://inferencex.semianalysis.com/agentx/methodology |
| harness | `agentx-harness==1.0.11` (AIPerf, NVIDIA), wrapper `python3 -m infx.bench agentic` | `inferencex-e2e/docs/agentx-standalone.md`; `infx/bench/agentic/run.py`, `replay.py` |
| korpusy | `semianalysisai/cc-traces-weka-062126` (do 1M) i `…-256k` (zapytania z in+out ≤ 256k) | HF; `infx/bench/agentic/traces.py:1-21` |
| spekulacja | wymuszona AL z SPEED-Bench (kategoria coding) per model × drafter × długość draftu × thinking | `infx/golden_al_distribution/README.md`; methodology §„Synthetic payloads” |
| dashboard / API | Next.js, publiczne `GET /api/v1/views/inference?model=…&sequence=agentic-traces` | `/tmp/inferencex-app/packages/app/src/lib/api/api-route-catalog.ts:137-143` |
| vLLM blog K3 | „Hyper Optimizing Kimi K3 in vLLM” (B. Chislett, NVIDIA, 2026-10-16) + PR #61867 (scalony 2026-10-16, +12805 linii, 50 plików) | http://vllm.ai/blog/2026-10-16-kimi-k3-megakernel; https://github.com/vllm-project/vllm/pull/61867 |
| arXiv 2605.08513 | **inny temat** (bezpieczeństwo, pojedyncze neurony odmowy) | https://arxiv.org/abs/2605.08513 |

## 2. Co dokładnie mierzą (z kodu)

### 2.1 Metryki AgentX
- **ITL / interactivity:**
  - AIPerf zwraca dla każdego zapytania `inter_token_latency`; InferenceX liczy percentyle po zapytaniach (`request_metrics.py:120-128`);
  - `p90_intvty = 1 / p90_itl` (`request_metrics.py:65-84`);
  - to więc **średnie ITL zapytania z wolnego ogona (10% najwolniejszych zapytań)**, a nie ogon pojedynczych tokenów;
  - przy c=1 w ogonie lądują najgłębsze konteksty i krótkie odpowiedzi.
- **E2E-normalized interactivity:** `OSL / E2EL` per zapytanie, czyli z TTFT (`request_metrics.py:87-112`). Dla lokalnego użytkownika to metryka bliższa „ile czekam na turę agenta”.
- **Throughput:**
  - `(Σ input + Σ output) / czas` (`request_metrics.py:214-250`, linia 240);
  - **wliczają tokeny wejścia trafiające w cache prefiksu**;
  - przykład Kimi K3 na GB300 (16 GPU, c=1, 2026-10-18): `tpPerGpu` 1554 tok/s, ale `outputTputPerGpu` 10.1 (API `/api/v1/views/inference?model=Kimi-K3&sequence=agentic-traces`, zrzut `/tmp/ix_k3.json`).
- **Ważność biegu:**
  - ≥ 900 s, inaczej `--unsafe-override` i znacznik invalid (`replay.py:24,96`);
  - błędne zapytania ≤ 10% (`run.py:31`);
  - jedna współbieżność na jedno wdrożenie serwera (`run.py:79-87`);
  - cache-bust per replay (unikalny znacznik pierwszej tury);
  - przerwy „globalnie bezczynne” przycięte do 10 s.
- **Korpus 256k:** wybierany dla rodzin `dsr1`, `qwen3.5`, `qwen3.8next` (`traces.py:13`).

### 2.2 Spekulacja: wymuszona akceptacja
- Silniki dostały przełączniki: vLLM `rejection_sample_method: synthetic` + `synthetic_acceptance_length` (#40662), SGLang `SGLANG_SIMULATE_ACC_LEN`, TRT-LLM `TLLM_SPEC_DECODE_FORCE_NUM_ACCEPTED_TOKENS` (AL−1), ATOM `--spec-decode-acceptance-length` (`golden_al_distribution/README.md`).
- Uzasadnienie autorów: losowe tokeny psują akceptację, routing ekspertów i throughput (`README.md:9`). To prawda, ale skutek jest taki, że **AgentX mierzy koszt kroku przy założonej AL, a nie jakość draftera**. Lookup/n-gram po kontekście (nasz ogon W16) jest na syntetycznej treści niemierzalny.
- Golden AL na kodzie przy thinking on:
  - Qwen3.8-Flash-Next MTP n=4: 2.47 (`qwen3.8next_mtp.yaml:15`);
  - Kimi K3 DSpark DL7: 3.78 (`kimik3_dspark.yaml:17`).
  - Dla porównania nasz Qwen3.8-27B MTP4 na `spec_sweep`: 3.01–3.06 tok/krok przy T=1 (`lekcja-5-seedow.md:10`). **O**: inny model i inne prompty.

### 2.3 Fixed-sequence
- `--dataset-name random`, `--ignore-eos`, ISL/OSL 1k–8k (`fixed_seq.py:40-47`), czyli losowe tokeny.
- Ilustracja na Qwen3.8-27B: przy c=1 to tylko **10 zapytań** (`agg_bmk.json`, run 35359530151), więc percentyle p90/p99 przy c=1 nie mają mocy statystycznej.

## 3. Audyt tez

| # | Teza | Sprzęt / model / obciążenie | Baza | Nasz rachunek | Werdykt |
|---|---|---|---|---|---|
| 1 | „Trusted by GigaWatt token factories”; 1000+ punktów/tydzień | marketing | — | — | nieistotne dla nas |
| 2 | AgentX „replays real agent traffic” | 393 sesje Claude Code, CLI ≥ 2.1.139, ≤ 10 subagentów równolegle; treść syntetyczna | fixed-seq | kształt potwierdzony w danych: mediana in 88 768 / out 376 (256k), 99% cache hit w korpusie (methodology), nasze 96.2% (radix, §5) | **wiarygodne co do kształtu**; ruch jednego narzędzia (Claude Code) i modeli Anthropic, w tym 12% zapytań z Haiku (`21f-agentx-stats-out.txt`). Ruch omp może wyglądać inaczej `[NIEZWERYFIKOWANE]` |
| 3 | Mediana ratio hashy zrekonstruowanych do tokenów providera 1.004 | 135 282 zapytania | — | — | wiarygodne, ale to tokenizer Claude'a; dla Qwena długości w tokenach różnią się o nieznany procent `[NIEZWERYFIKOWANE]` |
| 4 | „P90 interactivity” jako metryka użytkownika | — | — | to `1/p90(ITL na zapytanie)` bez TTFT; dla agenta z 117:1 wejścia większość czasu na turę to prefill/TTFT (§5) | **myląca dla lokalnego użytkownika**; E2E-normalized jest lepsza i też jest w danych |
| 5 | Spekulacja z wymuszoną AL jest fair | wszystkie silniki | SPEED-Bench coding | uczciwe porównanie *silników*, ale wyłącza z rankingu jakość draftera i spekulację po kontekście | **uczciwe dla serwerów, bezużyteczne dla naszego głównego zysku** |
| 6 | Qwen3.8-27B bf16 H100 DSpark k=7: c1 med 86.1, p90 67.4 tok/s; TPOT 11.6 ms; 465 W | 1×H100, vLLM nightly `cd10ed6f9`, 1k/1k random, `max_model_len` 2304, `max_num_seqs` 16, KV fp8 | — | waga bf16 ≈ 54 GB `[SZACUNEK]` / 3.35 TB/s ≈ 16 ms → bez spekulacji ≤ ~62 t/s; AL z logów 1.59–2.47 (≈ 2.0) → krok ≈ 23 ms (target + drafter + weryfikacja 8 tokenów) | **wiarygodne**, ale tylko 10 zapytań przy c=1, losowe tokeny, PR niescalony („experimental”) |
| 7 | Saturacja Qwen 27B na H100 od c=16 (TTFT 6.7 s → 173 s przy c=128) | jw. | — | `max_num_seqs=16` w logu serwera, więc c>16 to kolejka, nie GPU | artefakt konfiguracji; nieistotne dla nas |
| 8 | Kimi K3 c=1 AgentX P90 interactivity 229.9 (8×GB300) / 423.7 (16×GB300) | GB300 NVL72, Dynamo vLLM, DCP8/16, offload KV | stock | output 10.1–16.5 tok/s/GPU przy c=1 | wiarygodne; skala obcą dla nas |
| 9 | Blog vLLM: 842 t/s batch 1, 16×GB300, DSpark DL7 | TP16, ISL 1, OSL 1k, **synthetic AL=6** | stock vLLM 488 | 842/6 = 140 kroków/s = 7.13 ms/krok; przy AL 3.78 (golden coding) ≈ 530 t/s; PR (ISL 32k, AL 3.78): 483 t/s | **przesadzone ~1.6×** w wartości bezwzględnej; wzrost względny wobec stock (1.71×) się trzyma |
| 10 | „1.5–2× decode” | TP8/TP16, B1–64, bez spekulacji | stock vLLM (słaby punkt startu) | TP16 B1: 7.38 → 3.90 ms; aktywne bajty K3 `[SZACUNEK]` ~77 GB/token (≈140B parametrów aktywnych MXFP4 + głowica BF16), czyli /16 = 4.8 GB/GPU → 0.60 ms przy 8 TB/s: stock 8%, nowe 15% pasma | **wiarygodne** (nsys + ITL, 3×4 runy), reżim latencji/komunikacji jak MonoKernel w 15a |
| 11 | „1.8× P90 interactivity na AgentX: 403.2 vs 223.7” | ours 16 GPU vs stock 8 GPU | — | to dwa różne rozmiary systemu; na tej samej liczbie GPU PR daje 1.58× (TP8 B1, bez spekulacji) | **nieuczciwe porównanie** (przyznane w tekście bloga) |
| 12 | Jakość bez zmian | AIME25/GPQA-D/GSM8k/MRCR v2 | stock | różnice w 1 SE; greedy probes do 245k: dryf = podłoga szumu 1-ulp; prefill bitowo jak stock | **wiarygodne**; dobry wzorzec walidacji dla zmian niebitowych |

## 4. Liczby z InferenceX istotne dla lokalnego single-user

| liczba | wartość | warunki | źródło | dla nas |
|---|---|---|---|---|
| Qwen3.8-27B bf16, 1×H100, c=1 | med 86.1 / p90 67.4 tok/s; TTFT 0.148 s; 465 W | vLLM + DSpark k=7, 1k/1k random | run 35359530151 `results_bmk/agg_bmk.json`; log `server.log:175-201` | **O**: XTX Q4_K_XL + MTP4 = 109.0 t/s `spec_sweep` (`REKORDY.md:22`), 3090 78.0 (`REKORDY.md:74`). Lekki kwant na tańszej karcie wygrywa w batch 1 z bf16 na H100 |
| AL DSpark k=7 na losowych 1k | 1.59–2.47 (≈ 2.0) | jw. | `server.log:175-201` | drafter DSpark na losowych tokenach ≈ nasza AL MTP na prozie PL |
| Golden AL coding | Qwen3.8-Flash-Next MTP4 2.47; K3 DSpark DL7 3.78; DSv4.1 DSpark5 4.07 / 3.51 | SPEED-Bench coding, 4096 tok | `golden_al_distribution/*.yaml` | punkt odniesienia do naszych tok/krok (3.0 przy T=1) |
| Kształt agenta | in p50 88.8k, p90 204k; out p50 376, p90 1845; 117:1 | korpus 256k, 68 266 zapytań | `21f-agentx-stats.py` | **główny wynik dla nas** (§5) |
| Trafienia cache w korpusie | 99% (korpus 8271 sesji), nasze 96.2% (radix) | proxy Anthropic | methodology; §5 | lokalny llama-server z 1 slotem ma tylko 79.4% (§5) |
| Przerwy na narzędzia | p50 2.1 s, p90 34.6 s, 15.8% > 10 s | think_time | `21f-agentx-stats.py` | wpływa na wygasanie cache i na planowanie odpowiedzi `[INFERENCE]` |

Fixed-sequence 8k/1k i 1k/8k dla dużych modeli (DSR1, Kimi, GLM itd.) dotyczą multi-GPU i dużego batcha, więc dla nas nic nie wnoszą.

## 5. Nasza analiza śladów AgentX (Amdahl dla lokalnego agenta)

**Metoda** (`21f-agentx-stats.py`, CPU, korpus 256k):
- Hashe są łańcuchowe, więc widziany blok oznacza, że widziany jest cały jego prefiks. Dla każdego zapytania liczę tokeny nietrafione w cache w trzech politykach:
  - **radix**: dowolne wcześniejsze zapytanie sesji, jak APC w vLLM/SGLang;
  - **lane**: poprzednie zapytanie tego samego toru (agent główny albo dany subagent);
  - **single**: poprzednie zapytanie w czasie, czyli `llama-server -np 1` bez cache RAM.
- Polityka **cram** to lane plus przywrócenie stanu z `--cache-ram` przy każdej zmianie toru. Koszt przywrócenia ~2.1 GB/s (16f E4: kopia 2.3 GB ≈ 1.1 s).
- Krzywe XTX z `~/qwen-opt/long_ctx.jsonl`:
  - **Qwen** (e2e-final): prefill 939/763 t/s przy 29.5k/94k, dopasowanie T(N) = aN + bN², a = 0.953 ms, b = 3.795 ns, więc krańcowo 584 t/s przy 100k i 405 t/s przy 200k (ekstrapolacja `[SZACUNEK]`); decode MTP4 T=0: 130.2 t/s przy 1.7k i 97.5 przy 94k, liniowo w ms/token.
  - **LFM** (lfm-base): prefill 5172/3709 t/s, decode 173.7/153.1 t/s.
- Przerwy na narzędzia przycięte do 10 s. Zapytania wykonywane sekwencyjnie, więc subagenci nie biegną równolegle (jak przy `-np 1`).

**Wyniki: Qwen3.8-27B na XTX** (`21f-agentx-stats-out.txt`):

| limit kontekstu (zapytań zostaje) | polityka | prefill | decode | narzędzia ≤10 s | ×2 decode → zegar | ×2 prefill → zegar |
|---|---|---|---|---|---|---|
| 200k (88.7%) | radix | 98 h (36%) | 140 h (52%) | 33 h (12%) | −25.8% | −18.1% |
| 200k | lane | 203 h (54%) | 140 h (37%) | 33 h | −18.6% | −27.0% |
| 200k | single | 495 h (74%) | 140 h (21%) | 33 h | −10.5% | −37.0% |
| 200k | **cram (nasz prod)** | 203 h + 9 h przywracania (21 486 zmian toru) | 36% zegara 385 h | | | |
| 128k (66.3%) | radix | 68 h (40%) | 82 h (48%) | 20 h | −24.2% | −20.0% |
| 128k | **cram** | 148 h + 6 h | 82 h (32% z 256 h) | 20 h | ≈ −16% | ≈ −29% |
| 64k (35.3%) | cram | 75 h + 2.7 h | 32 h (27% z 116 h) | 6 h | ≈ −14% | ≈ −32% |

Tokeny nietrafione w cache: radix 3.8% wejścia (p90 6.8k na zapytanie), lane 8.5% (p90 25.7k), single 20.6% (p90 71k).

**Wyniki: LFM2.5 na XTX** (`21f-agentx-stats-out.txt`, sekcja MODEL=lfm):
- przy radix, lane i cram decode to 52–62% zegara (cram 128k: 51.8%), a prefill 15–33%; przy single decode 39–47%;
- ×2 decode skraca zegar o 19–33%, ×2 prefill o 7–23%.

Wnioski `[SZACUNEK]` (zastrzeżenia niżej):
1. **Qwen, praca agentowa:**
   - prefill i cache są ważniejsze niż decode. Przy naszej konfiguracji (cram) prefill zajmuje ~58% zegara;
   - zysk lookup tail ×2.4 na edycjach dotyczy tylko części decode, która jest kopiowaniem, więc na całą sesję agentową to raczej −10…−20%;
   - wymiana polityki lane → radix (współdzielenie promptu systemowego między subagentami i sesjami) zabiera **−32% zegara** (128k: 148 → 68 h prefillu). To kierunek łatki `CACHE_SHARE_MIN` (16f E4) i E5, uogólniony na wiele torów.
2. **LFM:** decode dominuje, więc kernele decode (w tym fuzje z §8) ważą tu ~2× więcej niż w Qwenie.
3. **Interaktywność modelu** (decode na zapytanie, nasza AL na prawdziwym tekście): Qwen p50 102–116 t/s, wolny ogon p10 82–108 t/s. E2E-normalized p50 ~60 t/s, ale p10 8–10 t/s: krótkie odpowiedzi po długim prefillu dominują ogon.

Zastrzeżenia:
- (a) ruch Claude Code, nie omp; prompt systemowy i liczba narzędzi inne;
- (b) tokeny Claude'a zamiast Qwena;
- (c) krzywe ekstrapolowane poza 94k;
- (d) decode przy T=0 z AL na prawdziwym tekście; przy T=1 niższa (Qwen 109 t/s `spec_sweep`, 1.7k);
- (e) sekwencyjne wykonanie: przy kilku slotach i batchowaniu subagentów zegar sesji spadnie, ale cache będzie dzielony;
- (f) pojemność 16 GiB `--cache-ram` nie jest modelowana; 128k Qwena to ~5.7 GB stanu `[SZACUNEK]` (43 KB/token + 0.15 GB, z 16f E5), więc mieszczą się 2–3 tory.

## 6. Czy AgentX ma zostać naszym standardem?

| cecha | `spec_sweep` | `copy` / `mvs` / `long` | `long_ctx_bench` | AgentX (oficjalny) |
|---|---|---|---|---|
| treść | 6 promptów PL/EN, prawdziwa | prawdziwy kod i edycje, ~30k w `long` | prawdziwe dokumenty, 1.7k–94k | **syntetyczna** |
| co mierzy | ms/krok, tok/krok, t/s decode | zysk spekulacji po kontekście (lookup tail) | prefill i decode na głębokości, akceptacja | TTFT/ITL/E2E przy kształcie agenta: cache, sloty, kolejka, subagenci |
| spekulacja | prawdziwa | prawdziwa | prawdziwa | **wymuszona AL**; w llama.cpp nie ma przełącznika, więc wyszłaby AL na śmieciach |
| bitowość / jakość | greedy md5 osobno | greedy md5 | — | nie („does not support model-quality evaluation”) |
| czas na punkt | ~2 min (mediana 2.15 min, `spec-sweep.md`) | minuty | ~10 min (prefill 94k) | ≥ 15 min + dataset + warmup; oficjalnie 1 h, czyli 1.5–2 h na XTX |
| wariancja przy c=1 | 3–5 seedów | 2–3 seedy | 1 przebieg | ~1 sesja na godzinę (§7), duża |
| pokrywa ruch agentowy | nie | edycje tak | długi kontekst tak | **kształt tak** (jedyny) |

**Decyzja (rekomendacja):**
- AgentX **nie jest** naszym standardem pomiaru silnika.
- Przyjmujemy:
  1. **Model kształtu** (`21f-agentx-stats.py`) do ustalania priorytetów: kernel decode vs prefill vs cache.
  2. **Okazjonalny test systemowy** oficjalnym harnessem (c=1, spekulacja wyłączona albo raportowana osobno) do decyzji o slotach i cache: `-np`, `--cache-ram`, `CACHE_SHARE_MIN`, E5.
  3. **„PodX”**: własny replay o kształcie AgentX z prawdziwą treścią omp. Mierzy naraz akceptację MTP + lookup i cache, czyli cały zysk Podkręta w pracy agentowej. To kandydat na czwarty poziom standardu obok `spec_sweep`, `copy`/`mvs` i `long_ctx_bench`.

## 7. Jak uruchomić na XTX i konsumenckiej NVIDIA (plan adaptacji, teraz bez GPU)

### 7.1 Oficjalny harness przeciw naszemu llama-server (test systemowy)
- **Środowisko:** venv Python 3.12 w `/tmp/agentx-venv`, `pip install 'agentx-harness==1.0.11'` (`agentx-standalone.md`). Z HF tylko tokenizer `Qwen/Qwen3.8-27B` (bez wag). Rekonstrukcja datasetu jest ciężka dla CPU, więc `nice -n 19`, limity wątków i `AIPERF_DATASET_CONFIGURATION_TIMEOUT=1800` (about/FAQ).
- **Korpus:**
  - `semianalysis_cc_traces_weka_062126_256k`;
  - na XTX Qwen ctx 204800 (prod), więc `--max-context-length 196608`; dokładna semantyka (odcięcie czy pominięcie) `[NIEZWERYFIKOWANE]`;
  - test tańszy: limit 131072;
  - 5060 Ti 16 GB (Q3_K_XL): limit 65536, zostaje 35% zapytań i 23% tokenów wyjścia, czyli wynik mało reprezentatywny.
- **Serwer:** `run-llm.sh qwen` (`-np 1 --cache-ram 16384`, ctx 204800) + `--metrics`, `LLAMA_SERVER_CACHE_SHARE_MIN=1024`.
- **Komenda:** `agentx profile --url http://127.0.0.1:PORT --endpoint /v1/chat/completions --model … --tokenizer Qwen/Qwen3.8-27B --concurrency 1 --public-dataset semianalysis_cc_traces_weka_062126_256k --random-seed 42 --use-server-token-count --server-metrics http://127.0.0.1:PORT/metrics --benchmark-duration 1800 --output-artifact-dir …`.
- **Wymagania wobec serwera** (`[NIEZWERYFIKOWANE]` dla llama-server): streaming, `ignore_eos`, `max_tokens`, `stream_options.include_usage`. Thinking Qwena: tokeny `reasoning_content` liczyć po stronie serwera (`--use-server-token-count`).
- **Ramiona (ABBA, osobny świeży serwer na punkt, `run.py:79-87`):**
  - A = prod (`-np 1` + cram + `CACHE_SHARE_MIN`);
  - B = `-np 4 --kv-unified` (czy MTP/lookup w forku działa z wieloma slotami: `[NIEZWERYFIKOWANE]`, sprawdzić najpierw);
  - C = A + E5 (cache sesji na SSD).
  - Spekulacja w obu ramionach jak w prod, ale AL raportowana osobno i **nie** interpretowana.
- **Zbierać:** TTFT p50/p90, E2E-normalized p50/p10, prompt tokens przeliczone (metryka serwera) / Σ in, liczba zapytań w oknie, `submission_valid`.
- **Koszt:** 0.5–1 dnia ustawienia + ~1 h GPU na ramię (1800 s pomiaru + warmup: primer do ~200k przy ~500 t/s ≈ 6–7 min `[SZACUNEK]`).
- **Bezpieczeństwo sprzętu:**
  - ciągłe obciążenie 30–60 min na ramię pod `gpu-powercap.service`, jak długi `long_ctx_bench`;
  - SSD zużywa tylko jednorazowy zapis cache datasetu AIPerf (rozmiar `[NIEZWERYFIKOWANE]`) i ewentualnie E5 (zapisy stanu 2–5 GB na zmianę toru: przy 21 tys. zmian w pełnym korpusie to dziesiątki TB, więc **E5 tylko dla przerw > X s, nie dla każdej zmiany toru**);
  - RAM: 16 GiB cram + mmap datasetu.
- **Wymaga zgody na lokalne GPU** (dziś nie uruchamiane).

### 7.2 „PodX”: kształt AgentX z prawdziwą treścią (rekomendowany poziom standardu)
- **Źródło:** sesje omp (`~/.omp/agent/sessions`, 1.2 GB lokalnie) albo nagrania przez `~/wt/quickwins/qw/capture_proxy.py` (16f). Z sesji bierzemy pełne `messages` i narzędzia, czasy między turami (przycięte do 10 s) i tory subagentów. Treść zostaje lokalnie (prywatność).
- **Replay:** rozszerzyć `qw/replay.py`:
  - kolejne tury z prawdziwymi wiadomościami;
  - `max_tokens` = długość odpowiedzi z nagrania, T=0 i T=1;
  - generacji **nie** wymuszamy przez `ignore_eos`, kończy EOS albo limit: to zachowuje prawdziwą akceptację, kosztem innej długości wyjścia.
- **Metryki:** zegar sesji (Σ TTFT + decode), prefill przeliczony / Σ in, tok/krok, t/s decode na turę, greedy md5 tur przy T=0 (bitowość).
- **Reprezentatywność:** porównać rozkład z AgentX (in p50 ~89k, out p50 376, 117:1, subagenci w 44% sesji).
- **Koszt:** 2–3 osobodni CPU + 1–2 h GPU na pierwszą kalibrację. Działa tak samo na 3090/5060 Ti (ten sam serwer HTTP).

### 7.3 Eksperymenty (falsyfikowalne)
- **A1 (zrobione, CPU):** model Amdahla na śladach (§5). Wynik: Qwen prefill+cache ≥ decode, LFM decode > prefill.
- **A2 (GPU, zgoda, ~2 h):** harness §7.1 przy c=1, 1800 s, ramiona A/B.
  - Hipoteza: przeliczone tokeny prefillu / Σ in w A ≈ 8.5–20% (lane…single), w B ≥ 30% mniej niż w A, przy TTFT p50 −20%.
  - **Kill dla oficjalnego harnessu:** > 10% błędnych zapytań przeciw llama-server po 1 dniu poprawek (ich próg, `run.py:31`) albo brak zgodności ze streamingiem i `ignore_eos`. Wtedy zostaje tylko PodX.
- **A3 (walidacja modelu):** zmierzone per zapytanie (prefill, decode) z A2 vs predykcja `21f-agentx-stats.py`. **Kill/refit:** mediana błędu > 25%.
- **A4 (decyzja o standardzie):** jeśli PodX i zestaw `spec_sweep` + `mvs` + `long_ctx_bench` dają ten sam ranking dwóch konfiguracji w 3/3 przypadkach, PodX jest redundantny: tylko kwartalnie. Jeśli ranking się różni, PodX wchodzi do standardu przed decyzjami produktowymi.

## 8. vLLM Kimi K3 „megakernel”: techniki i przeniesienie na jedno konsumenckie GPU

### 8.1 Co zrobili (blog + PR #61867)
Ścieżka „latency_specialized” (opt-in `--additional-config '{"decode_backend": "latency_specialized"}'`): CuTe DSL dla GB300 TP8/TP16, B1–64, DSpark 3–7. Fallback do stock dla prefillu i mieszanych batchy. Kod lokalny w `vllm/models/kimi_k3/nvidia/`.
1. **Kształty pod batch:** małe macierze dla B1–2, split-K dla większych; KDA (Kimi Delta Attention) z harmonogramem pod B i głowice na GPU. Przy DCP: fuzja łączenia częściowych wyników z v-proj i gatingiem.
2. **Nakładanie liczenia i komunikacji:**
   - o_proj fuzowane z all-reduce i residualem;
   - producent publikuje częściowe wyniki do buforów NVLink bez fence; przy małym B producent i konsument w jednym kernelu;
   - przy dużym B dwustopniowa redukcja.
3. **MoE:** router i projekcja latentna rozłożone na ranki TP zamiast liczone wszędzie. Shared expert na osobnym strumieniu, nałożony na routing albo ekspertów routowanych.
4. **Prefetch wag do cache** dedykowanym kernelem na bocznym strumieniu w fazach, które nie wysycają pasma (komunikacja).
5. **Liczba kerneli:** 23 → 13 na warstwę, 130 → 69 µs na warstwę (rysunek z bloga). **To fuzja, a nie jeden trwały kernel** (13 × 93 warstwy ≈ 1200 launchy na krok).
6. **Walidacja:**
   - testy kerneli plus ewaluacje modelu: AIME25, GPQA-D, GSM8k, MRCR v2 128–256k;
   - greedy probes do 245k z dryfem równym podłodze szumu 1-ulp (stock z zaburzonymi o 1 ulp embeddingami);
   - błąd znaleziony audytem: **kompilator przeniósł odczyt aktywacji przed czekanie na synchronizację**. Naprawa: przed czekaniem wolno ładować tylko statyczne wagi.

### 8.2 Rachunek
- Bez spekulacji, TP16, B1: 7.38 → 3.90 ms (1.89×), TP8 B1 1.58× (blog, tabela; PR „Claims”).
- `[SZACUNEK]` aktywne bajty K3 z `config.json`:
  - eksperci: 16 z 896 × 3 × 7168 × 3584 ≈ 1.23B parametrów/warstwę; shared 2 × 3 × 7168 × 3072 ≈ 0.13B; 92 warstwy MoE → ~126B;
  - atencja i KDA ~14B, razem ~140B × 4.25 bita (MXFP4) ≈ 74 GB + głowica BF16 2.35 GB ≈ **77 GB/token**;
  - /16 GPU = 4.8 GB, czyli 0.60 ms przy 8 TB/s;
  - stock 8%, nowe **15%** pasma HBM. Ten sam reżim co MonoKernel w 15a (5–8% → 12–24%): zysk z latencji, launchy i komunikacji, nie z pasma.
- DSpark: 842 t/s przy AL 6 → 7.13 ms/krok (M = 8). Przy AL 3.78 (golden coding) ≈ 530 t/s. PR przy ISL 32k, AL 3.78, TP16+DCP16: 483 vs 276 t/s (1.75×).

### 8.3 Co z tego przenosi się na jedno konsumenckie GPU

| technika K3 | u nas | ocena |
|---|---|---|
| fuzja z all-reduce / NVLink, dwustopniowa redukcja, sharding routera po TP | brak multi-GPU | **nie dotyczy** |
| shared expert na bocznym strumieniu | LFM nie ma shared expert (15a §4.1), Qwen jest gęsty | **nie dotyczy** |
| prefetch wag do cache bocznym strumieniem | 16a X3 (MALL „touch”): 1–4 MiB +0.2…+0.6% (szum), 16 MiB −2.4% | **sprawdzone, KILL** na XTX; na Ada/Blackwell (32–72 MB L2) niesprawdzone; 3090 ma 6 MB L2, więc bez sensu |
| kernele pod kształt B1–2 vs split-K | nasza weryfikacja to M = 5 (MTP4) do 17 (ogon W16); po lookup tail weryfikacja M = 17 jest na ścieżce krytycznej code-edit | **warto zmierzyć**: czas kroku weryfikacji vs M (5/9/17) dla MMVQ/MMQ na XTX i 3090 |
| mniej kerneli (fuzje epilogów) | mamy fuzje (`rms_norm_mul` + kwant q8_1 dla MMVQ, `wt/fusion/ggml/src/ggml-cuda/norm.cu:168-172`) | kolejny krok: **RMSNorm liczony redundantnie w prologu konsumenta** (każdy blok matvec liczy normę wektora 2048 elementów sam, 8 KB), bez osobnego kernela i hand-offu (wzorzec „redundancja zamiast hand-offu” z MonoKernel, 15a §2.3) |
| „przed czekaniem tylko statyczne wagi” | nasze tickety i flagi (0051/0053/0054/0056/0057), PM4-PDL w 16a | **przyjąć jako regułę** w każdym kodzie ze spinem |
| bramka „szum 1-ulp” + długi kontekst | `kld_gate.py`, greedy md5 | **przyjąć** dla zmian niebitowych (np. kvq na CUDA, gdzie KLD zależy od kolejności sumowania, `lekcja-kld-szum-kolejnosci.md`) |

### 8.4 Czy fuzowana ścieżka decode jest wykonalna i opłacalna u nas?
- **Qwen3.8-27B:**
  - plain decode ma już 76–77% pasma na XTX i 3090 (15a §3.2–3.3); sufit megakernela +3–6% decode (15a);
  - na sesji agentowej decode to 32–52% zegara (§5), więc −1…−3% zegara;
  - **nie warto.**
- **LFM2.5:**
  - pula „DRAM bezczynny” to 36% (15a §3.1), sufit dataflow +12–28%;
  - realne próby padły: PM4-PDL ~+3%, MALL w szumie (16a); na RDNA3 hand-off kosztuje tyle co granica (`lekcja-handoff-rdna3.md`);
  - decode to ~52–62% zegara agentowego, więc sufit −6…−15% zegara, a realnie `[SZACUNEK]` −1…−3%.
  - Pełny megakernel (25–35 osobodni na backend, 15a §4.4): **nie.**
- **NVIDIA Ampere (3090, bez PDL):** granica grafu wyższa (15a §3.3), więc fuzje epilogów i prolog-norm mają tu relatywnie więcej do wzięcia niż na XTX z PM4 `[INFERENCE]`.

### 8.5 Minimalne eksperymenty
- **K1 (CPU, teraz):** z istniejącej taśmy PM4 LFM (`~/wt/lfm4-prof/c2_tr_1.txt`) policzyć czas `rms_norm` + granice przed konsumentami.
  - 15a podaje `rms_norm` 126 µs + `norm_router_topk` 198 µs na 3404 µs; z samego `rms_norm` i ~38 granic × 0.6 µs wychodzi ≤ 150 µs ≈ 4.4% `[SZACUNEK]`.
  - **Kill:** < 3% tokenu.
- **K2 (GPU, zgoda, 2–3 dni):** prolog RMSNorm w MMVQ n=1 dla in_proj LFM, z redukcją w tej samej kolejności co `rms_norm_mul_f32`, żeby wynik był bitowy.
  - **Kill:** < +2% tg128 ABBA albo jakakolwiek zmiana hashu logitów/greedy md5.
- **K3 (GPU, zgoda, 0.5 dnia):** czas kroku weryfikacji Qwen przy M = 5/9/17 (MTP4 z ogonem i bez) z `GGML_HIP_PM4_DEBUG=3`, z rozbiciem na klasy kerneli.
  - **Kill dla kerneli specjalizowanych pod M:** koszt M=17 ≤ 1.15 × M=5 (wtedy szerokość jest prawie darmowa i nie ma czego stroić).

## 9. arXiv 2605.08513 (krótko, inny temat)
„A Single Neuron Is Sufficient to Bypass Safety Alignment in Large Language Models” (Kazemi, Chegini, Safi; 2026-05-08):
- dwa systemy neuronów: odmowy (bramkujące) i pojęć (wiedza);
- wyłączenie jednego neuronu odmowy omija alignment, a wzmocnienie neuronu pojęcia wywołuje szkodliwe treści z niewinnych promptów;
- 7 modeli z 2 rodzin, 1.7B–70B, bez treningu.

Dla nas: zero wpływu na wydajność. Produktowo przypomina, że modyfikacje wag (nasze kwanty, warianty „Uncensored”) mogą zmieniać zachowanie bezpieczeństwa, a KLD tego nie łapie `[INFERENCE]`. Niska istotność.

## 10. Źródła
- InferenceX: https://inferencex.semianalysis.com/ (strona główna, `/about`, `/agentx`, `/agentx/methodology`, `/agentx/optimizations`, `/agentx/optimizations/vllm`, `/agentx/telemetry`, `/cache-reuse`, `/first-token`, `/reliability`, `/agentic-workload-explorer`, `sitemap.xml`).
- Repo: https://github.com/SemiAnalysisAI/InferenceX @ `b9c6fc3020f9` (2026-10-18), m.in.:
  - `inferencex-e2e/infx/bench/agentic/run.py:31,79-87`, `replay.py:24-25,96`, `traces.py:1-21`;
  - `infx/results/agentic/request_metrics.py:65-112,214-250`, `common.py:1-33`;
  - `infx/bench/fixed_seq.py:40-47`;
  - `infx/golden_al_distribution/README.md`, `kimik3_dspark.yaml:17`, `qwen3.8next_mtp.yaml:15`, `dsv41flash_dspark.yaml`;
  - `docs/agentx-standalone.md`.
- Dashboard: https://github.com/SemiAnalysisAI/InferenceX-app: `packages/constants/src/models.ts:17-23`, `packages/app/src/lib/catalog/data-mappings.ts:245-265`, `packages/db/src/etl/normalizers.ts:105-110`; API `/api/v1/views/inference` (zrzuty `/tmp/ix_k3.json`, `/tmp/ix_q27_*.json`; Qwen3.8-27B: 0 punktów oficjalnych).
- Qwen3.8-27B na H100: PR https://github.com/SemiAnalysisAI/InferenceX/pull/3260 (i #3261–#3263, otwarte), run https://github.com/SemiAnalysisAI/InferenceX/actions/runs/35359530151 (artefakty `results_bmk/agg_bmk.json`, `server_logs_…conc1…/server.log:7,175-201`).
- Korpus: https://huggingface.co/datasets/semianalysisai/cc-traces-weka-062126-256k (README, `stats.txt`, `traces.jsonl`); nasz skrypt `21f-agentx-stats.py`.
- SPEED-Bench: https://arxiv.org/abs/2604.09557. AIPerf: https://github.com/ai-dynamo/aiperf.
- vLLM: http://vllm.ai/blog/2026-10-16-kimi-k3-megakernel; https://github.com/vllm-project/vllm/pull/61867 (opis, tabele „Claims”, „Performance Validation”, „Full matrix”); RFC https://github.com/vllm-project/vllm/issues/59665, /61698; DSv4.1 https://github.com/vllm-project/vllm/pull/61868.
- Kimi K3 config: https://huggingface.co/moonshotai/Kimi-K3/resolve/main/config.json (hidden 7168, 93 warstwy, 896 ekspertów, top-16, 2 shared, MXFP4 g32).
- arXiv: https://arxiv.org/abs/2605.08513.
- Nasze:
  - `~/qwen-opt/long_ctx.jsonl` (e2e-final, lfm-base), `~/qwen-opt/run-llm.sh:109`;
  - `~/llama-master/common/common.h:650-653` (`n_ctx_checkpoints` 32, `checkpoint_min_step` 8192, `cache_ram_mib` 8192);
  - `product/research/15a-monokernel.md` §1–4, `16a-pm4-pdl.md:9-23`, `16f-xtx-szybkie.md:16,159-190,192-215`;
  - `wiki/REKORDY.md:22,74`, `wiki/lekcje/lekcja-5-seedow.md:10`, `wiki/lekcje/lekcja-handoff-rdna3.md`;
  - `~/wt/quickwins/qw/capture_proxy.py`, `replay.py`; `~/wt/fusion/ggml/src/ggml-cuda/norm.cu:168-172`.
- Pełne pokrycie (§11): `sitemap.xml` (1426 stron EN + tyle samo `/zh`), teksty stron w `~/qwen-opt/research-src/inferencex-data/pages/`, API v1 (`views/options`, `availability`, `benchmarks?model=…`, `datasets`, `views/ubenchx`), golden AL `golden_al/*.yaml`, notatki `notes-opt.txt`; PR-y InferenceX #3262, #3304, #3305 (GitHub API, `gh_*.json`).

## 11. Pełne pokrycie strony (A–Z)

Stan na 2026-10-19. Dane: `~/qwen-opt/research-src/inferencex-data/` (wszystko < 3 MB). Strony to głównie powłoki Next.js renderowane po stronie klienta, więc liczby brałem z API, a nie z HTML.

### 11.1 Inwentarz stron

| strona (liczba) | co tam jest | dla nas | liczby / akcja |
|---|---|---|---|
| `/`, `/overview`, `/inference/{16 modeli}`, `/inference/agentic` | dashboard: throughput/chip vs interactivity, AgentX i 8k/1k (1k/1k i 1k/8k oznaczone jako deprecated) | niska: serwery | — |
| `/compare` (408), `/compare-per-dollar` (408), `/chips` (22), `/gpu-specs`, `/rankings` (33), `/run/{model}-on-{gpu}` (106) | pary GPU, koszt, rankingi; generowane szablonem | brak: zero kart konsumenckich | sprzęt: §11.2 |
| `/compare-precision` (43) | FP4 vs FP8/BF16/INT4 przy tej samej karcie | niska (formaty Blackwell/CDNA, nie GGUF) | — |
| `/compare-spec-decode` (67) | MTP vs brak, interpolowane przy tej samej interaktywności | **średnia**: jedyny wpis bliski konsumenckiemu (RTX PRO 6000) | §11.3 |
| `/calculator`, `/historical`, `/fleet`, `/profit-estimator(-per-gigawatt)`, `/whitepaper` (MI355X K3: $32.6B przychodu/GW-rok) | TCO, koszt chip-godziny (H100 $1.17, RTX PRO 6000 $0.68/h), przychód z GW | brak | — |
| `/evaluation`, `/reliability`, `/submissions`, `/current-inferencex-image`, `/ai-chart`, `/operatorx` (GEMM/MoE/attention), `/collectivex` (EP/KV/swap) | jakość, odsetek udanych biegów, obrazy kontenerów, mikrobenchmarki | niska | `views/ubenchx`: mem-bw, odległość SM–L2, „tpc-skyline”, tylko dla GPU z centrów danych |
| `/model/{12}` | karty modeli z architekturą | średnia dla Qwen3.8-Flash-Next | §11.3 |
| `/agentx/*` (16: methodology, telemetry, quickstart, 2 strony korpusów, 10 stron optymalizacji) | metodologia (pokryta w §2) i optymalizacje | **wysoka**: §11.4–11.5 | — |
| `/blog` (36) | 10 krótkich wpisów AgentX, artykuły o przyroście wydajności, TileRT, Engram, TPU | średnia: przykłady optymalizacji | §11.4 |
| `/glossary` (195) | definicje; `unofficial-run` = nakładka biegu CI spoza opublikowanej bazy | niska | — |
| `/api` (dokumentacja OpenAPI 3.1, 45 endpointów) | `views/*`, `benchmarks`, `availability`, `datasets`, `pareto`, `tco-feed`, `server-log*`, `request-timeline`, `trace-*` | narzędzie | `robots.txt` blokuje `/api/` dla crawlerów, ale publiczny GET działa bez klucza |
| `/quotes`, `/about`, `/land-acknowledgement` | marketing, FAQ, lista SKU | brak | — |

Changelog serwisu jest w `GET /api/v1/workflow-info` (bez parametru zwraca pustą odpowiedź, 33 B) i w polu `changelog` PR-ów recept, a nie na osobnej stronie.

### 11.2 Sprzęt, modele, silniki (`views/options`, `availability`: 6880 konfiguracji)
- **Sprzęt:** VR200, H100, H200, B200, B300, GB200, GB300, MI300X, MI325X, MI355X, RTX PRO 6000, TPU7x, Jalapeño. **Nie ma żadnej karty konsumenckiej ani RDNA** (brak 7900 XTX, W7900, R9700, 4090, 5090).
  - Najbliżej nas jest RTX PRO 6000 (GB202, 96 GB, 600 W, ten sam chip co 5090): **2 konfiguracje**, Qwen3.5-397B FP4, SGLang, 8k/1k (2026-07-30).
  - AMD to wyłącznie CDNA3/4.
- **Modele:** DSv4-Pro, DSv4.1-Flash, Kimi-K3, MiniMax-M3, GLM-5.2/5.3, Qwen3.5-397B-A17B, Qwen3.8-Flash-Next, Muse-Spark-Open, starsze (DSR1, gpt-oss, Llama-70B, Kimi-K2.5, MiniMax-M2.5).
  - Qwen3.8-27B i 27B-Eager: kategoria „experimental”, **0 wierszy** w `benchmarks` (sprawdzone 2026-10-19).
  - LFM: brak.
- **Silniki:** vLLM v0.32.0, SGLang v0.5.22 (`framework-releases`), TRT-LLM, ATOM, Dynamo (vLLM/SGLang/TRT), llm-d, MoRI-SGLang/vLLM, Mooncake-ATOM, TileRT, Teacup.
  - **llama.cpp, Ollama, ExLlama i GGUF nie występują nigdzie na stronie** (grep wszystkich 300+ stron tekstowych).
- **Spekulacja:** `mtp` 804 konfiguracje, `draft_model` 43 (DSpark/DFlash), `none` 6033.

### 11.3 Liczby istotne dla nas (surowe wiersze API)

| pomiar | wartość | warunki | źródło | dla nas |
|---|---|---|---|---|
| RTX PRO 6000 ×4, Qwen3.5-397B FP4, c=1 | bez spekulacji 78.3 tok/s (TPOT 12.8 ms) → MTP **153.6** (6.5 ms) = **1.96×**; c=4: 53.4 → 91.6; c=64: 10.8 → 12.5 | SGLang v0.5.16-cu130, TP4 przez PCIe (bez NVLink), 8k/1k, TTFT 0.80 s | `api_benchmarks_qwen35.json` | 17B aktywnych × ~4.5 bita ≈ 9.6 GB/token, /4 = 2.4 GB na GPU → 1.3 ms przy 1.79 TB/s, czyli ~10% pasma `[SZACUNEK]`. **TP na konsumenckim PCIe przy B=1 to reżim latencji**, w którym weryfikacja jest prawie darmowa i MTP daje ~2×. Na jednym XTX MTP daje mniej, bo decode jest bliżej pasma (76–77%, 15a). Czy AL w tych biegach był wymuszony: `[NIEZWERYFIKOWANE]` |
| Qwen3.8-Flash-Next AgentX, c=1 | B200 FP4: mediana interaktywności 292 tok/s, p90 259; TTFT med 0.48 s przy medianie wejścia 72k; 560 zapytań/h; trafienia GPU 96.3% (teoretycznie 94.3%) | SGLang MTP, 1 GPU, bez offloadu | `api_benchmarks_model_Qwen3.8-Flash-Next.json` | trafienia ≈ nasze radix 96.2% (§5). **p90 jest niestabilne**: B300 c=1 p90 37.9 przy medianie 290, H100/H200 c=1 p90 15–16 przy medianie 240–244 (średnie ITL 23 ms przy medianie 4 ms). To potwierdza tezę 4 z §3 na ich własnych danych |
| Qwen3.8-27B natywne MTP, golden AL | thinking off n=1…4: **1.90 / 2.68 / 3.28 / 3.79** (AR 90/84/76/70%); thinking on: **1.73 / 2.21 / 2.52 / 2.72** (AR 73/61/51/43%); FP8 = BF16 ±0.01 | H200 TP1, SPEED-Bench coding (80 promptów), 16k ctx, wyjście 4096; głowica MTP BF16 (checkpoint FP8 kwantyzuje MTP, więc ładują oryginał) | PR #3304 (zamknięty, YAML niescalony) | **zgodne z naszymi pomiarami**: MTP4 przy T=1 daje 3.01–3.06 tok/krok (`lekcja-5-seedow.md:10`), czyli między ich „on” i „off”; kwant Q4 nie obniża AL wyraźniej niż FP8. Przy thinking on n=3 → 4 dodaje tylko +0.20 AL (+8%), a koszt pasa MTP to ~0.8 ms z ~37–41 ms kroku (`stepcost.md`), więc n=4 nadal się opłaca |
| Golden AL innych modeli (coding, thinking on, n=4) | Qwen3.5-397B 3.97; Kimi-K3 DSpark 3.22 (n=7 3.78); GLM-5.2 3.33; MiniMax-M3 EAGLE3 3.11; Muse-Spark DFlash2 3.44; DSv4-Pro MTP 2.54 (plateau od n=3); Qwen3.8-Flash-Next 2.47 | B300/B200, vLLM/SGLang | `golden_al/*.yaml` | Qwen3.8-27B (2.72) i Flash-Next (2.47) mają najniższe AL przy thinking on. Plateau DSv4 to przykład, że głębokość ponad 3 nie zawsze coś daje |
| DSpark dla Qwen3.8-27B | k=7 (trenowany blok; k=4 i k=6 wolniejsze), losowanie draftu „probabilistic” ~23% szybsze od greedy; adaptacyjna weryfikacja odrzucona przez backend GDN w vLLM | H100 bf16, vLLM nightly | PR #3262 | już w `drafters.md`: DSpark na czacie nie jest lepszy od MTP; probabilistyczne MTP u nas bez zysku (`NOTES.md:159`, głowica przekonana o sobie, `mtp-train/RESULTS.md:82`) |

Niespójności po stronie InferenceX:
- karta Qwen3.8-Flash-Next podaje AL 3.24 dla MTP=3 przy thinking off, a `qwen3.8next_mtp.yaml` ma tylko thinking on (2.32 dla n=3);
- strona MoRI UMBP podaje medianę 142K wejścia i 444 wyjścia na turę, a blog DSv4 i nasz korpus 256k 88k/413 i 88.8k/376 (inny korpus 1M albo inne ważenie `[INFERENCE]`);
- blog v3 mówi o „70+” PR-ach, a strona optymalizacji o „50+”.

### 11.4 Katalog optymalizacji A–Z

Kategorie: **C** cache/KV, **S** harmonogram/serwer, **K** kernel, **P** spekulacja, **Q** kwantyzacja/format, **R** równoległość/komunikacja, **F** frontend/tokenizacja, **X** poprawność. „Nas” = jeden użytkownik, llama.cpp (fork), XTX i konsumenckie NVIDIA, Qwen3.8-27B (hybryda GDN) i LFM2.5.

| # | projekt / PR | co zrobiono | zysk (warunki) | nas? |
|---|---|---|---|---|
| 1 | vLLM #43447 #44774 #45444 #42258 #44082 | **C** selektywne zachowanie checkpointów SWA na granicach replay; blok lookahead spekulacji w zachowanym prefiksie | hit > 95% (14 równoległych, ctx do 1M) | **tak, częściowo już jest**: llama-server robi checkpointy przy granicy wiadomości użytkownika i końcu promptu (`server-context.cpp:3980-4058`, `-cms` 8192, 32 na slot) → test T3 |
| 2 | vLLM #37160 #40549 #42296 #42828 | **C** CPU offload KV dla modeli hybrydowych (SimpleCPU connector, ROCm) | +81.7% wyjścia, −46.6% E2E vs przeliczanie (DSv4) | odpowiednik już jest: `--cache-ram` zapisuje KV, stan rekurencyjny i draft |
| 3 | vLLM #41289 #46412 #46906 | **C** węższy zapis: pomijać duplikat w locie, **zapisywać tylko deltę**, nie zależeć od rezydencji w HBM | — (koszt przeniesiony ze ścieżki zapisu) | **tak**: `server_prompt_cache::alloc` pomija tylko prompt w pełni zawarty; przedłużony prompt zapisuje **cały stan od nowa** (`server-task.cpp:1722-1760`) → T2 |
| 4 | vLLM #45659 #45969 #45971 #46188 | **S** asynchroniczny lookup cache, klucze zero-copy, równoległy odbiór | — | nie (1 slot, lookup to LCP po tokenach) |
| 5 | vLLM #44103 #45371 #46855 #45340 #49069 #49071 | **X** zdarzenia cache per grupa; **stan EAGLE gubiony przy offloadzie** | poprawność | **sprawdzić**: checkpointy niosą `data_dft` i `data_spec` (`server-context.cpp:2575-2578`), ale draft jest „dropped”, gdy nie pasuje (`:2700-2706`) → T1 |
| 6 | vLLM #51183 | **K** KDA decode pisze wprost do bufora wyjścia (−1 kopia/warstwę) | mały | **tak**: audyt kopii po GDN (`cpy`/`cont` na token) → T6 |
| 7 | vLLM #51714 | **K** wybór dedykowanego kernela sparse-MLA zamiast generycznego | +5.22% wyjścia AgentX | zasada „generyczna ścieżka = zły kernel” → T6 |
| 8 | vLLM #51713 | **K** strojone GEMM dla projekcji atencji | +2.3% fixed-seq, **znika w szumie AgentX** | lekcja metodyczna: zysk kernela < 3% nie jest widoczny na zegarze agenta (zgodne z §5) |
| 9 | vLLM #45879 #45720 #45546 | **X** asercja NIXL block_len (gsm8k = 0); dtype fp8 fnuz na gfx942; brak interfejsu EAGLE3 w pliku modelu AMD | poprawność dnia zero | lekcja: osobne pliki/ścieżki per backend rozjeżdżają się; nasze `*_parity` i greedy md5 to pokrywają |
| 10 | SGLang #26907 #27210 #29369 #30339 | **C** alokator SWA: zwalniać strony wychodzące z okna, limit blokad do 1 okna, sprzątać stare wpisy; poprawka ring-cache ROCm | pojemność, poprawność | nie (Qwen3.8 bez SWA; LFM ma krótki conv-state) |
| 11 | SGLang #29417 #28534 #29735 | **C** HiCache: offload pełnej atencji, okno SWA odbudowywane; checkpointy GDN (FlashInfer) | 47 771 → 53 004 tok/s/GPU przy 92.4% hit | idea już u nas (stan rekurencyjny w checkpointach) |
| 12 | SGLang #30255 | **S/K** długość kontekstu jako skalar w runtime → jedna kompilacja zamiast osobnej na długość | +26.75% wyjścia, −36.25% TTFT (c=384) | **sprawdzić**: czy graf HIP/CUDA w llama.cpp przechwytuje się ponownie przy zmianie długości KV albo batcha weryfikacji → T7 |
| 13 | SGLang #30365 | **S** usunięty synchronizowany D2H długości sekwencji co krok | bąbel decode | już badane (PM4-PDL, `stepcost.md` #6–7) |
| 14 | SGLang #26091 #26245 #26293 #26387 #26579 | **S** routing DP z afinicją cache i balansowaniem | — | tylko przy `-np` > 1: przypinanie toru subagenta do slotu (ramię B w §7.1) |
| 15 | SGLang #30461 #30497 #31294 #33662 #32042 #32196 | **P** transfer okna draftu w disagg, overlap scheduling, usunięta pusta renormalizacja EAGLE, brak syncu hosta w prefillu EAGLE | — | częściowo: sync w prefillu MTP → T6 (profil) |
| 16 | SGLang #30545 #30762 #32368 #34216 | **X** staging świadomy radix w heterogenicznym disagg | igły 2/128 → 128/128 przy 127.5k; +9.61% na użytkownika | nie (disagg) |
| 17 | TRT-LLM #17462, #16231 | **F** **przyrostowa tokenizacja z cofnięciem o 1 token** (BPE łączy przez złączenie), render szablonu poza głównym wątkiem | **185.1 → 11.3 ms/turę**, zgodna na 1087 przejściach (trace Qwen3.5) | **tak**: llama-server renderuje szablon jinja i tokenizuje cały prompt (~100k) przy każdym zapytaniu → T4 |
| 18 | TRT-LLM #17518 #17428 | **R** koalescencja deskryptorów KV w disagg | p99 26.74 s → 125 ms (c=5) | nie |
| 19 | TRT-LLM #17473, #16876 | **K** CUDA graph dla stabilnych producentów sparse, atencja zależna od zapytania eager | +12.58% na użytkownika | pośrednio: graf dla części stałej, eager dla zmiennej → T7 |
| 20 | TRT-LLM #17316 | **K** kandydaci CuTeDSL w autotunerze MXFP8 | +7–10% przy niskim c | nie (format) |
| 21 | TRT-LLM #17105 | **X** usunięte błędne taktyki split-K MoE (5/7 biegów padało) | stabilność | lekcja: autotuner wybierze „szybkie i złe”; każda taktyka musi przejść parity (mamy `mmvq_il_parity`) |
| 22 | TRT-LLM #16279 #17278 | **S** zapas slotów przy nakładaniu się kończącego i nowego zapytania | stabilność | nie |
| 23 | TRT-LLM #15727 #17526 (otwarte) | **R** potokowy transfer KV per chunk prefillu | — | idea → T8 (warstwowe ładowanie z RAM) |
| 24 | ATOM #1640 | **C** zachowanie rzadkich checkpointów DSv4 SWA | hit 5.6% → 96.45%; straty na bramce SWA 91.35% → 0.16% (c=48) | jak #1 → T3 |
| 25 | ATOM #902 #939 #1345 | **X/K** trafienia z puli wolnych niszczyły wpisy; przywrócony hashing prefiksu; prefill po trafieniu na zoptymalizowanym kernelu | 0 → pełne użycie prefiksu | lekcja: **sprawdzić, czy prefill po trafieniu (krótki suffix przy długim KV) idzie właściwą ścieżką FA** → T6 |
| 26 | ATOM #1771 | **C** checkpointy stanu rekurencyjnego adresowane treścią; po wygenerowanej turze reuse 512 tokenów i 2-tokenowy suffix; bezwarunkowe publikowanie kosztowało **−17.5%** na ruchu bez trafień, więc odstęp co N tokenów | 1k/1k bez zmian | **tak**: koszt naszych checkpointów (Qwen ~0.15 GB stanu `[SZACUNEK]` z 16f) przy każdej wiadomości użytkownika → T3 |
| 27 | ATOM #1318 #1406 #1725 #1807 | **C** offload: przeładowanie 32k z CPU 0.32 s vs 2.5 s przeliczenia (8×); **promocja przywróconych bloków do indeksu GPU** | brak ponownego transferu | u nas przywrócony stan zostaje w slocie, więc działa `[INFERENCE]`; koszt zmiany toru liczony w §5 |
| 28 | ATOM #869 #919 #1699 | **S** routing świadomy cache, sticky z wygasaniem | — | jak #14 |
| 29 | ATOM #1737 #1331 #1647 | **R** disagg mieszanych cache, KV draftu EAGLE, backpressure | — | nie |
| 30 | ATOM #1220 #1701 #1746 #1552 | **R** prefill context-parallel (−35…−43% TTFT, +49% przy 64k); chunked PP prefill (TTFT 28.6 → 8.7 s, 3.68× bloków KV) | multi-GPU | nie (1 GPU); na 2 GPU konsumenckich PP prefill to temat poza zakresem |
| 31 | AITER #3728 #3267 | **R/K** grupy PCP, indeksowanie wierszy > 131k | — | nie |
| 32 | AITER #2893 #4474 #4680 | **X** adresowanie 64-bit dla pul > 2–4 GB (ciche złe wiersze) | poprawność | niskie ryzyko: KV u nas to osobne tensory na warstwę (~0.3 GB przy 200k) `[INFERENCE]`; zostaje needle przy 200k w `long_ctx_bench` |
| 33 | AITER #3459 | **K** persistent MLA decode pod 64/128 głowic (decode i weryfikacja MTP) | — | jak 21f §8.5 K3 (kernele pod szerokość weryfikacji) |
| 34 | Dynamo #10540 #10836 #11095 | **S** batchowane dopasowanie KV w routerze | +22.2% (c=512) | nie |
| 35 | Dynamo #11503 #11508 #12329 | **S** leasy zamiast liczników na blok | −23.71% czasu replay (vLLM) | nie |
| 36 | Dynamo #10521 #10676 #11644 #10645 #12158 | **S** kubełkowe wygasanie, sprzątanie tylko delty, kompresja ścieżek promptów (−35.3% CPU frontendu) | +13.7% | nie |
| 37 | Dynamo #10437 #11104 #11539 #11574 #11569 #10433 | **F** MessagePack, zero-copy ramek, bez metryk ITL na każdy token | +8.1% tput, −9.7% TTFT | marginalnie: koszt SSE/JSON na token w llama-server → T9 |
| 38 | Dynamo #11820 #12161 #12999 | **F** statyczne filtry logów (932 → 1133 rps), metryki detokenizacji raz na odpowiedź (~½ CPU frontendu) | — | jak #37 → T9 |
| 39 | LMCache #3382 | **C** rezerwacja per chunk zamiast całego ładowania (deadlock po 28 zapytaniach) | 120 zapytań | nie |
| 40 | LMCache #3635 #3869 #3908 | **C** zapisywać tylko użyteczne części grup hybrydowych (~20× mniej na token), prefetch tylko żywego okna | — | jak #3: **czy cache-ram zapisuje coś zbędnego** (np. checkpointy razem ze stanem, `checkpoints_size` w `alloc`) → T2 |
| 41 | LMCache #4524 (otwarte) | **X** blokady per chunk współdzielone między zapytaniami → uszkodzone generacje przy eviction | poprawność | nie (1 slot) |
| 42 | LMCache #3092 #3101 #3843 #4273 #4363 | **K** Triton block-sparse attention zamiast FlashInfer, backend hipFile GDS, koło ROCm | dostępność na AMD | nie |
| 43 | LMCache #3561 | **C** offload świadomy DCP | > 30 000 trafień CPU | nie |
| 44 | Mooncake #2225 #3184 #3338 | **R** GPU-direct RDMA przez HIP dmabuf, koło ROCm | — | nie |
| 45 | MoRI UMBP, SGLang #37578 #38269 #39911 #41024 #35619 | **C** pula DRAM poza procesem (przeżywa restart silnika), **ładowanie warstwa po warstwie z obliczaniem w trakcie**, deduplikacja kopii TP 8 → 1 | +8.3% tput, −35% P90 TTFT przy DRAM < 1% tokenów; +26–34% tput/GPU na 12 zamiast 16 GPU | **tak**: (a) cache-ram poza procesem = nasze E5 (cache sesji na SSD, 16f); (b) warstwowe przywracanie → T8 |
| 46 | SGLang #20736 | **K** shared expert jako ekspert top-K+1 w jednym wywołaniu MoE | +4.6% tput, −4% TPOT (c=16) | nie (LFM bez shared expert, Qwen gęsty) |
| 47 | SGLang #21188 | **K** GemmaRMSNorm na AMD szedł **natywnym fallbackiem**; po fuzji: c=1 **−23.1% E2E, +30% tput** | 8×MI355X, 8k/1k | **tak, jako audyt**: każdy op Qwen/LFM ze ścieżką generyczną zamiast fuzowanej → T6 |
| 48 | SGLang #21421 | **K** fused_topk z AITER (1.31–6.29× kernel) | +1.9% e2e | LFM: `norm_router_topk` 198 µs na 3404 µs tokenu (15a) → T10 |
| 49 | vLLM #35850 | **K** MLA przy 8 głowicach/rank: powtórzenie głowic do 16, żeby użyć gotowego kernela ASM zamiast fallbacku Triton | TPOT 152–199 → 13–43 ms (Kimi K2.5) | wzorzec: dopasować kształt do szybkiego kernela zamiast pisać nowy (np. M weryfikacji 5…17, 21f §8.5 K3) |
| 50 | SGLang 0.5.6 (blog) | **S/K** piecewise CUDA graph, wspólna pętla zdarzeń, JIT | **1.79× przy c=4**, 1.03–1.16× przy dużym c | potwierdza, że przy małym batchu stały koszt kroku dominuje; u nas to PM4/grafy (16a) |
| 51 | SGLang #21511 | **K/Q** FP8 KV i fuzja rope+concat+zapis+kwant w jednym kernelu | > 5% MI355, > 10% MI300 | gfx1100 nie ma FP8; idea „zapis KV fuzowany z RoPE” → T6 |
| 52 | AMD DSv4 (31 PR-ów, 110×) | **K** fuzje RoPE+Hadamard (−1 launch po stronie CPU), layernorm+kwant FP8, rmsnorm+kwant, greedy sample w AITER, fuzja zapisu cache; usunięte fallbacki Torch/Triton | 110.5× w 26 dniach (start z fallbacków) | lekcja jak #47; u nas mamy już `rms_norm_mul` + q8_1 |
| 53 | DSv4 TRT (blog) | **X** kernel mHC na sztywno pod hidden 4096 dawał śmieci dla 7168 | poprawność | bramka greedy md5 i KLD na każdym nowym modelu |
| 54 | TileRT (blog) | **K** cały decode jako jeden trwały kernel, specjalizacja per GPU, komunikacja w kafelkach | GLM-5 FP8 8×B200 **340 tok/s/użytk.** vs 113.6 (3.0×), kosztem throughputu (160 vs 240 tok/s/GPU) | ocena bez zmian (15a, §8.4): zysk TileRT bierze się z synchronizacji 8 GPU i TPOT < 3 ms; na jednym GPU przy TPOT 8–10 ms sufit +3–6% (Qwen) |
| 55 | wide EP / DBO (blogi GB200) | **R** EP 8–32 na NVLink, nakładanie all-to-all | 3.1–4.4× | nie |
| 56 | GB300 tail tax (blog v3) | **S** w mieszanym batchu decode atencja najdłuższych zapytań to 8.4 z 9.8 ms; dzielenie batcha według długości KV (otwarte) | — | tylko przy `-np` > 1 z subagentami: krótkie tory czekają na długi → do ramienia B w §7.1 |
| 57 | MTP przy dużym batchu (blog DSv4) | **P** MTP pogarsza wynik przy dużym batchu (compute-bound) | — | nie dotyczy (B=1) |
| 58 | Engram / n-gram embedding (blog, Qwen3.8-Flash-Next) | **C/Q** tablica 51B (Flash-Next) / 189 GiB (DSv4.1-Flash) adresowana ID tokenów, więc prefetch z DRAM/mmap SSD w trakcie wcześniejszych warstw | lepiej niż w HBM na większości Pareto | obserwacja modelu: Flash-Next ma 125B rdzenia (Q4 ≈ 70 GB `[SZACUNEK]`), więc na 24 GB tylko z ekspertami w RAM; poza zakresem |
| 59 | TPU (blog) | **C** GDN: osobne sloty na odczyt checkpointu i zapis żywego stanu, checkpointy na wyrównanych granicach | prefix caching hybryd | jak #1/#26; u nas checkpoint to kopia, nie slot `[INFERENCE]` |
| 60 | DSpark (PR #3262) | **P** losowanie draftu probabilistic +23% vs greedy (k=7) | vLLM, T>0 | **znane**: `drafters.md:11,67` (DSpark/DFlash2 probabilistycznie to osobny projekt); dla MTP zero zysku (`NOTES.md:159`) |

### 11.5 Ranking tego, co się przenosi, i testy

Kolejność według oczekiwanego zysku na zegarze sesji agentowej (§5) do kosztu. Wszystkie testy GPU wymagają zgody; T2 i T4 można zacząć na CPU.

| ranga | test | z czego (#) | oczekiwany zysk | kill |
|---|---|---|---|---|
| 1 | **T2: zapis przyrostowy do `--cache-ram`.** Zmierzyć czas `prompt_save` i `prompt_load` przy zmianie toru (Qwen, 32k/94k/128k) w logach serwera; potem prototyp „dopisz tylko nowe wiersze KV + bieżący stan rekurencyjny” zamiast pełnej kopii | 3, 40, 45a | §5 liczył tylko przywracanie (cram 128k: 6 h na 256 h). Jeśli zapis kosztuje tyle samo (~1.1 s na 2.3 GB, 16f E4), to drugie ~2–3% zegara `[SZACUNEK]`; delta tnie zapis do ~ułamka | zapis < 0.2 s na zmianę toru przy 94k albo < 1% zegara z modelu §5 |
| 2 | **T4: tokenizacja i szablon per tura.** CPU: czas `llama-tokenize` (słownik Qwen 248k) i renderu jinja dla rozmowy 100k tokenów; potem w serwerze `t_tokenize` przy turze z pełnym trafieniem cache | 17 | TRT: 185 → 11 ms/turę przy ~100k. U nas TTFT tury z krótkim wynikiem narzędzia to kilkaset ms, więc 100–200 ms by się liczyło `[NIEZWERYFIKOWANE]` (próba pomiaru nie ruszyła: kolejka `cpuheavy` i brak `libhipblas` w `LD_LIBRARY_PATH`) | tokenizacja + render < 30 ms przy 100k |
| 3 | **T1: akceptacja po przywróceniu stanu.** Ta sama sesja w 3 wariantach: ciągły slot / przywrócenie z `--cache-ram` / przywrócenie z checkpointu; porównać tok/krok MTP w turze N+1 | 5 | vLLM gubił stan EAGLE po offloadzie po cichu. U nas stan draftu jest zapisywany, ale może zostać odrzucony (`server-context.cpp:2700-2706`) | różnica tok/krok < 2% we wszystkich wariantach |
| 4 | **T3: koszt i trafność checkpointów GDN.** Z logów (`created/restored context checkpoint`) policzyć przeliczone tokeny po restore i czas tworzenia checkpointu; ramiona `-cms` 8192 / 2048 i checkpoint po końcu odpowiedzi asystenta | 1, 24, 26, 59 | ATOM: zły odstęp kosztował −17.5%, dobry dał 5.6% → 96% trafień. U nas zysk to część „lane” 8.5% nietrafionych (§5) | przeliczone po restore < 2% tokenów prefillu i koszt checkpointów < 1% zegara |
| 5 | **T6: audyt fallbacków i kopii w grafie decode** (Qwen i LFM): op-level profil tokenu, szukać ścieżek generycznych, `cpy`/`cont` po GDN, prefill krótkiego suffixu przy długim KV | 6, 7, 25, 47, 51, 52 | SGLang: jeden fallback RMSNorm = +30% przy c=1. U nas 15a nie pokazał dużego fallbacku, więc realnie 0–3% `[INFERENCE]` | brak opu spoza matvec/FA/GDN > 2% czasu tokenu |
| 6 | **T7: ponowne przechwytywanie grafu** przy zmianie długości KV i szerokości weryfikacji (MTP 1…5 + ogon lookup) | 12, 19, 50 | SGLang: +26.75% po usunięciu rekompilacji per długość. U nas na tokenie raczej < 1% `[INFERENCE]` | liczba przechwyceń/aktualizacji grafu na 1000 tokenów < 5 albo < 0.1 ms/token |
| 7 | **T8: warstwowe przywracanie z RAM nakładane na prefill suffixu** | 23, 45b | chowa do ~1.1 s na zmianę toru; 2.3% zegara cram 128k (6/256 h) | po T2 zysk < 1% zegara |
| 8 | **T10: router LFM** (`norm_router_topk` 198 µs/token): porównać z dolną granicą pasma i z fuzją softmax+top-k | 48 | ≤ ~150 µs z 3404 (≤ 4%) `[SZACUNEK]` | kernel w granicach 2× dolnej granicy |
| 9 | **T9: koszt strumienia SSE/JSON na token** (stream vs bez stream, `--metrics` on/off) | 37, 38 | < 1% przy ~110 tok/s `[INFERENCE]` | różnica < 1% |

Nie przenosi się (z powodem): disagg, wide EP/DP/TP/PCP/DCP, routing klastra, RDMA, koła i obrazy (#4, 16, 18, 22, 28–31, 34–36, 39, 41–44, 55); formaty FP8/MXFP8 bez wsparcia na gfx1100 (#20, 51); SWA (#10); duży batch (#57).

### 11.6 Weryfikacja wobec naszych pomiarów
- **Potwierdzone:**
  - AL Qwen3.8-27B (PR #3304) obejmuje nasze 3.0 tok/krok (MTP4, T=1);
  - trafienia cache w biegach AgentX 92–96% ≈ nasze radix 96.2%;
  - zysk pojedynczych kerneli znika w szumie AgentX (#8), co zgadza się z §5;
  - persistent kernel (TileRT) nie zmienia oceny 15a dla jednego GPU.
- **Doprecyzowane:**
  - §2.2: Qwen3.8-Flash-Next n=4 2.47 dotyczy thinking on; karta modelu podaje 3.24 dla n=3 przy thinking off bez pokrycia w YAML;
  - TL;DR pkt 6 i §3 #6: Qwen3.8-27B nadal ma 0 oficjalnych punktów. Są nieopublikowane biegi natywnego MTP z wymuszonym AL 2.51 (H100 BF16, 1k/1k run 35495270307, 8k/1k run 35501338930, PR #3305), do odczytu jako „unofficial overlay”.
- **Bez konfliktu z bazą wiedzy:** nic na stronie nie dotyczy llama.cpp ani kart konsumenckich, więc żadna liczba nie podważa REKORDY.md. Jedyna porównywalna karta (RTX PRO 6000) działała w TP4 na modelu 397B.

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie 1 linia | kluczowe liczby (źródło) |
|---|---|---|---|
| research | Raport 21f: InferenceX / AgentX i Kimi K3 w vLLM (`raport-21f-inferencex.md`) | AgentX mierzy serwer przy kształcie ruchu agenta na syntetycznej treści z wymuszoną AL; dla nas cenny kształt, nie wyniki; standardem zostaje nasz zestaw + PodX | mediana in 88.8k / out 376, 117:1 (`21f-agentx-stats.py`); Qwen XTX cram 128k: prefill 148 h vs decode 82 h (58% vs 32%) (`21f-agentx-stats-out.txt`); K3 842 t/s przy AL 6 vs golden 3.78 (`kimik3_dspark.yaml:17`) |
| metody | Kształt ruchu agentowego wg AgentX (`ksztalt-ruchu-agentowego.md`) | Ślady Claude Code: długie wejścia, krótkie wyjścia, 96% trafień cache przy współdzieleniu prefiksów, subagenci w 44% sesji | in p50 88 768, p90 204 288; out p50 376, p90 1845; limit 128k zostawia 66.3%, 64k 35.3%; nietrafione: radix 3.8%, lane 8.5%, single 20.6% (`21f-agentx-stats.py`) |
| lekcje | Na sesji agentowej prefill waży więcej niż decode (`lekcja-agent-prefill-nie-decode.md`) | Dla Qwena na XTX ×2 decode skraca zegar sesji agentowej o 10–26%, a zmiana polityki cache lane → radix o 32%; dla LFM odwrotnie (decode 52–62% przy dobrym cache) | Qwen cram 128k: ×2 decode −16%, ×2 prefill −29%; radix 68 h vs lane 148 h prefillu; LFM decode 51.8% (`21f` §5) |
| narzedzia | AgentX harness (`agentx-harness.md`) | `agentx-harness==1.0.11` (AIPerf), c = żywe drzewa sesji, ≥ 900 s, 1 h oficjalnie, P90 interactivity = 1/p90 ITL na zapytanie, throughput liczy tokeny z cache | `run.py:31,79-87`; `replay.py:24,96`; `request_metrics.py:65-84,240` |
| modele | Qwen3.8-27B na InferenceX (`qwen38-27b-inferencex.md`) | Eksperymentalny wpis: bf16, 1×H100, vLLM + DSpark k=7, 1k/1k random; c=1 med 86.1 / p90 67.4 tok/s, AL ≈ 2.0; nasz XTX Q4 + MTP4 109.0 (O) | run 35359530151; PR #3260 (otwarty); `REKORDY.md:22` |
| repo | vLLM Kimi K3 specialized decode (`vllm-kimi-k3-specialized-decode.md`) | Fuzja CuTe DSL z komunikacją TP na GB300: 23 → 13 kerneli/warstwę, B1 7.38 → 3.90 ms; nie megakernel; dla jednego GPU przenosi się reguła „tylko statyczne wagi przed czekaniem” i bramka 1-ulp | PR #61867; blog vLLM 2026-10-16; `[SZACUNEK]` 8% → 15% pasma HBM (`21f` §8.2) |
| research | arXiv 2605.08513 to nie InferenceX (`single-neuron-safety-2605-08513.md`) | Praca o omijaniu alignmentu jednym neuronem; zero wpływu na wydajność | 7 modeli, 1.7B–70B (arXiv 2605.08513) |
| research | InferenceX: katalog optymalizacji AgentX i przeniesienie na llama.cpp (`inferencex-optymalizacje.md`) | 60 przykładów z 10 stron optymalizacji i blogów. Przenosi się 9 testów: zapis przyrostowy cache-ram, tokenizacja per tura, stan MTP po restore, checkpointy GDN, audyt fallbacków; reszta to multi-GPU i serwer | TRT tokenizacja 185 → 11 ms/turę (#17462); ATOM checkpointy −17.5% przy złym odstępie, hit 5.6 → 96.45% (#1771, #1640); SGLang fallback RMSNorm +30% przy c=1 (#21188) (`21f` §11.4–11.5) |
| modele | Qwen3.8-27B: golden AL natywnego MTP (`qwen38-27b-golden-al.md`) | SPEED-Bench coding, H200; zgodne z naszym 3.0 tok/krok przy MTP4 | off n=1…4: 1.90/2.68/3.28/3.79; on: 1.73/2.21/2.52/2.72; FP8 = BF16 (PR #3304) |
| sprzet | InferenceX nie mierzy kart konsumenckich (`inferencex-sprzet.md`) | Brak XTX, RDNA, 4090 i 5090. Najbliżej jest RTX PRO 6000 (GB202): Qwen3.5-397B FP4 TP4 przez PCIe | c=1: 78.3 → 153.6 tok/s z MTP (1.96×), TPOT 12.8 → 6.5 ms (`api_benchmarks_qwen35.json`) |
| lekcje | llama-server zapisuje do cache-ram pełny stan zamiast delty (`lekcja-cache-ram-pelny-zapis.md`) | `server_prompt_cache::alloc` pomija tylko prompt w pełni zawarty; przedłużony prompt to pełna kopia KV + stanu rekurencyjnego + draftu + checkpointów | `server-task.cpp:1722-1760`; do zmierzenia w T2 (`21f` §11.5) |
