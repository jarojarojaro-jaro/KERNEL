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
