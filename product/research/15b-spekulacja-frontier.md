# 15b. Frontier spekulacji: lookup z kontekstu, szeroki blok weryfikacji, DFlash2, bit-exact

Data: 2026-10-16. Autor: podagent ResSpecFrontier. Bez użycia lokalnego GPU, bez chmury.
Eksperyment CPU-offline: skrypty w [15b-sim/](15b-sim/), wyniki zbiorcze w [15b-sim/results.txt](15b-sim/results.txt).
Prace wcześniejsze, na których buduję (nie powtarzam): `qwen-opt/research/v2/rr-engines-drafters.md` (hybryda n-gram + MTP w llama.cpp), `qwen-opt/research/strata/spec-host.md`, `qwen-opt/research/tensorfold/spec-host.md`, `qwen-opt/research/repos/22-lucebox.md`, `30-hipfire.md`, `qwen-opt/research/qwen-round5.md`, raport 12 (bit-exact).

## TL;DR

1. **Mechanizm HyperQwen (dawniej syv-ai/qwen38-27b-rtx3090) to nie „lepszy drafter”, tylko darmowe drafty z kontekstu plus dłuższy blok weryfikacji.** Kernel Triton szuka najdłuższego sufiksu (6–12 tokenów) w historii żądania i kopiuje to, co nastąpiło po nim. Pozycje 8–15 bloku 16 wypełnia tylko lookup; drafter DFlash2 dalej daje swoje 7. Długi blok jest planowany dopiero po 2 nasyconych krokach i trzymany jeszcze 3 kroki. Pozycje z lookupu dostają w rejection samplerze rozkład punktowy, więc wynik jest bezstratny rozkładowo, ale **nie bitowo**: zmiana szerokości bloku zmienia zaokrąglenia (sami to zmierzyli).
2. **381 t/s to prawda, ale tylko dla kopiowania dokumentu słowo w słowo.** Bench to 25k-tokenowy dokument złożony z dokumentacji ich własnego repo, powtórzonej, plus duńskie polecenie „przepisz pierwsze 60 linii”: 14.97 tok/krok przy 39.3 ms/krok. Na zwykłym czacie pozycje 7–14 dają **0.65%** przyjętych tokenów (ich własny pomiar), a 133 vs 131 t/s mieści się w szumie ±3–5%.
3. **Kluczowy wynik offline: nasza głowica MTP już kopiuje.** Na 69 207 pozycjach odpowiedzi Qwen3.8-27B z prawdziwymi łańcuchami draftów MTP (ext_p1) zachodzi P(MTP d1 trafia | lookup trafia) = **0.968** (bazowo 0.765), a łańcuch 4 draftów na długich kopiach trafia w 93.5%. Lookup daje nam więc tylko **ogon za pozycją 4** oraz ewentualnie pominięcie kosztu draftu, a nie lepszą głowę. Wariant HyperQwen, w którym lookup nadpisuje głowę, jest dla nas **ujemny**: −1…−2% na czacie i kodzie przy prawdziwych draftach, do −4% na tekście agenta.
4. **Ile kopiowalnych spanów mają nasze workloady** (symulacja dokładna dla exact-match verify):
   - czat, proza, kod z `spec_sweep`/WildChat/aya (Qwen3.8 T=1): lookup trafia 1–17% pozycji, run ≥8 tylko 0–5%, zysk **≈0%**;
   - wyjścia agenta omp (7.2 M tokenów, tokenizer Qwena): edycje hashline 58% / 26%, `str_replace` 60% / 38%, bash 51% / 20%, `write` 27% / 7%, tekst 16% / 2.5%.
5. **Oczekiwany zysk t/s na XTX dla najlepszego wariantu, „EXT”** (MTP zostaje głową, lookup tylko dokleja ogon, gdy 4 drafty MTP zgadzają się z kontekstem; do tego łańcuchy bez draftera):
   - krótki kontekst: edycje hashline **+8%**, `str_replace` **+23%**, bash +4%, mieszanka agenta **+2.9%**, czat 0%;
   - kontekst ~32k: edycje +2% (W=8); mieszanka +0.2% przy W=8 i −3.8% przy W=16, bo każde dodatkowe 16 wierszy kafla FA kvq kosztuje u nas ok. 3.5 ms;
   - bloki 32/64 dodają tylko +0.3 pp na naszej mieszance agenta.
   Werdykt: **mały, workload-specyficzny zysk**. Uzasadnia tani prototyp (EXT-W8 + logowanie „shadow”), a nie przebudowę wokół bloku 16.
6. **Szeroki blok na naszych kernelach** (llama-bench, d=2048, `k4/vcost_qwen-k4b.csv`): V(8) = V(5) + 2.48 ms, V(16) = V(5) + 7.09 ms (+29% weryfikacji), skok 8→9 wynosi +1.82 ms. Przy długim kontekście kvq czyta KV raz na kafel 16 wierszy (`ceil(6·W/16)` kafli: W5 = 2, W8 = 3, W16 = 6), więc W=16 przy 32k szacuję na +14 ms więcej [INFERENCE]. HyperQwen ma 1 kafel do 21 tokenów (128 wierszy).
7. **DFlash2 n=15 u nas** (spec_sweep T=1, już zmierzony w rundzie 5): akceptacja **rośnie** na kodzie (pl-kod 4.21 → 5.67 tok/krok), ale krok rośnie 32.9 → 39.1 ms, a czat i proza tracą. Średnio 97.9 vs MTP 108.8 t/s. Artykuł DFlash (Tab. 8) potwierdza, że drafter b8 użyty z blokiem 16 ma niższe τ niż przy b8.
8. **tqLLM „identyczne wyjście ze spekulacją i bez”**:
   - działa tylko dla greedy i jest naprawione dopiero 2026-10-13 (commit `7d7382b`);
   - mechanizm: każdy blok wielkości weryfikacji, łącznie z dekodowaniem N=1, idzie przez te same kernele;
   - matvec jest testowany bitowo na niezależność od szerokości 1..16 kolumn, a podział atencji zależy tylko od pozycji zapytania;
   - to jest nasza opcja (b) z raportu 12. Nowa jest metodyka testu: end-to-end na prompcie 3.7k tokenów, z przemiataniem `ubatch`/kontekstu, bo błąd wychodził tylko przy `-ub 4096`.
9. **Ranking dla nas:**
   - (1) shadow-log lookupu w serwerze, 0.5 osobodnia;
   - (2) EXT-W8 + łańcuchy, 2 osobodni, zgodne z trybem BITEXACT (≤8 kolumn);
   - (3) EXT-W16 dopiero po pomiarze V(W) przy 32k;
   - nie robić: nadpisywania głowy (HYB), DFlash2+lookup, bloków 32/64.

## 1. Audyt twierdzeń

Roofline: RTX 3090 936 GB/s. Cel HyperQwen W4A16 ≈ 13.3 GB korpusu + 0.65 GB lm_head int4 (+ 1.19 GB drafter DFlash2 W4A16, + KV bf16: 16 warstw × 4 głowy KV × 256 × 2 × 2 B = 64 KiB/token, czyli 1.64 GB przy 25k) [INFERENCE z config i `docs/optimizations.md`].

| # | Twierdzenie (dokładnie) | Sprzęt | Model + kwant | Workload / prompt | Batch | Kontekst | Baseline (strojony?) | Wyjście identyczne / jakość | Komenda | Roofline | Werdykt |
|---|---|---|---|---|---|---|---|---|---|---|---|
| H1 | „~82 → 114 t/s (optimized MTP)” | 3090 @250 W | Qwen3.8-27B W4A16 AutoRound + lm_head GPTQ int4 + MTP GPTQ int4 („fast variant”) | 8 promptów `bench/prompts_real.jsonl` (EN/DA/kod), odpowiedzi 1024 tok., T=1/top-p .95/top-k 20 i greedy | C1 | krótki (45–300 tok. promptu) | ich wcześniejszy stan (84 t/s, commit `9850338` 08-17); vLLM bez spec. 46 t/s | spec. dokładna rozkładowo; kwantyzacja zmienia cel: PPL 8.095 vs 8.045 (+0.6%), GSM8K 96.5% | `bench/run_benchmarks.sh single` | ≈14.5 GB/krok → ≥15.5 ms; zmierzone 24.8 ms × 2.8–3.0 tok/krok → 113–121 t/s ✓ | **plausible** (powtarzalne 111.1 / 120.0; liczby z vLLM 0.27.1, „cztery piny temu”) |
| H2 | „138 t/s (DFlash2 + lookup)” | j.w. | j.w. + DFlash2 W4A16 1.19 GB | j.w. | C1 | krótki | MTP 111–115 / 115–124 | j.w.; tekst greedy różni się między sesjami | j.w. | 26.5 ms/krok × 3.3–3.6 tok/krok → 125–136 ✓ | **plausible, ale wybrany najlepszy przebieg** (133.8/138.5 „best runs”; typowo 121.8/131.2) |
| H3 | „~381 t/s, 15 z 16 tokenów przyjętych na blok 16” | j.w. | j.w., `DFLASH_TOKENS=15`, `LOOKUP=1`, sticky 3 | `bench/labd_bench.py`: dokument 25k = **docs repo sklejone i powtarzane** do ≥200k znaków (`labd_bench.py:42-47`), polecenie po duńsku „przepisz pierwsze 60 linii”, greedy, bez thinking, ≤512 tok. | C1 | 25k | ten sam serwer, `DFLASH_TOKENS=7` (260) i bez lookupu (159) | GSM8K 96.5%; 7/9 długich promptów greedy identycznych z `LOOKUP=0` (2 flipy przy remisie) | `labd_bench.py <tag> --ctx 20000` | 14.97 tok/krok ÷ 381 t/s = 39.3 ms/krok vs dolna granica ≈ 18 ms (≈17 GB) → 25.5 kroku/s ✓ | **plausible tylko dla specjalnego workloadu** (kopia verbatim; na czacie pozycje 7–14 = 72/11 069 = 0.65% przyjętych tokenów, `single-user/README.md:510-516`) |
| H4 | „~133 t/s na zwykłym czacie” | j.w. | j.w. | 8 promptów, greedy, jedna sesja | C1 | krótki | `DFLASH_TOKENS=7`: 131 | j.w. | j.w. | ✓ | **plausible; wkład bloku 16 (+1.5%) mieści się w szumie ±3–5%** |
| H5 | „prefix-cache TTFT 22.4 s → 0.56 s” | j.w. | j.w. | druga tura nad tym samym dokumentem 25k | C1 | 25k | ten sam serwer bez `PREFIX_CACHE` | „odpowiedzi identyczne token w token” | `PREFIX_CACHE=1` | 25k / 22.4 s = 1.1k t/s prefill ✓ | **plausible**, standardowy prefix caching (mamba align). U nas to samo już działa: 27k, 31.9 s → 0.7 s (`qwen-opt/NOTES.md:206-213`) |
| H6 | „kwantyzowane KV / głowy / aktywacje bez straty jakości” | j.w. | stan GDN fp16; lm_head/embed int8 → lm_head GPTQ int4; MTP int4; INT8_ACT (W4A8) prefill; KV bf16 / fp8 / int8_per_token_head / KVarN 4/2-bit | PPL (33k tok. EN/DA/kod), GSM8K 200, IFBench | – | – | W4A16 | stan fp16: PPL bez zmian (8.044); lm_head int4 GPTQ: +0.6%; INT8_ACT: PPL +4.1%, GSM8K 95.0 vs 96.5; KVarN: połowa decode przy >100k | `bench/quality_battery.py` | – | **plausible z kosztami, które sami podają**. Słowo „lossless” dotyczy tylko spekulacji względem już zkwantyzowanego celu |
| D1 | DFlash: „>6× lossless”, „2.5× ponad EAGLE-3” | H200 (Transformers), B200 (SGLang FA4) | Qwen3-4B/8B bf16, Coder-30B-A3B, LLaMA-3.1-8B | math/code/chat, thinking off, ≤2048 tok. | 1 (Tab. 1); 1–32 (Tab. 3) | krótki | HF AR (niestrojony), EAGLE-3 z drzewem 16/60 (τ ≈ 3.0–3.5) | bezstratne rozkładowo | brak w artykule | B200: 4B bf16 = 8 GB przy 8 TB/s → AR ≤ ~1000 t/s; baseline SGLang 316 t/s = 32% roofline | **plausible tylko dla specjalnego workloadu** (math τ 6.5–7.9; MT-Bench τ 4.24 → 2.75×) |
| D2 | NVIDIA Muse-Spark-Open DFlash2: AL 3.75 (T=0) / 3.31 (T=1), draft 7 | GB300, TP4+EP4 | Muse-Spark-Open-816B-A42B NVFP4; drafter 4.38B bf16, SWA 2048, 5 warstw | MT-Bench, SPEED-Bench, reasoning xhigh, 4096 tok. | C32 | do 32k (SPEED throughput: AL 3.25/2.90, high_entropy 2.44) | brak (tylko AL) | – | `vllm serve … dflash, num_speculative_tokens 7, probabilistic` | – | **plausible** (sam AL, pomiar dostawcy, wydane dziś, bez surowych logów) |
| T1 | tqLLM: „Output stays identical with/without spec decode” | 3090, 5060 Ti, GB10 | Qwen3.8-27B TQ3_4S/TQ_*, DFlash2 Q4_K_M, MTP | `test-dflash-exact`: 1 prompt code-review 3.7k tok., 512 tok. wyjścia, drzewo i łańcuch; `test-native-mtp`; `test-tree` | 1 slot | 16k (i 64k po D1) | plain greedy tego samego silnika | greedy token w token; sampling nie jest deklarowany jako identyczny | `ctest` (`tests/dflash_exact.cpp`) | – | **plausible dla greedy, 1 slot, formatów KV z „tree”**. Naprawione 2026-10-13 (`7d7382b`); DSpark-tree na GB10 MoE nadal nie jest dokładny (`src/qwen35.cpp:3101`) |
| T2 | tqLLM: 240–270 t/s (LocalMaxxing reasoning, „approved” 273.1) | 3090 | TQ3_4S-v2 (~14.5 GB), KV BF16, DFlash2 Q4_K_M, drzewo | LocalMaxxing reasoning-v1, thinking on, T=0, 320 tok., mediana 5 | C1 | 32k | – | greedy jak plain (T1) | `bench/relbench.py` | ≈15.6 GB/krok → ≥16.7 ms; 273 t/s ⇒ ≥4.6 tok/krok (realnie ≥6) | **plausible tylko dla specjalnego workloadu** (rozumowanie o niskiej entropii, krótkie wyjście, wagi ~3.5 bpw) |
| X1 | 0x7067 (llama.cpp, 3090): `draft-mtp,ngram-mod` 108.8 → 260.8 t/s | 3090 | UD-Q4_K_XL, KV q4_0 | 8-turowa sesja edycji plików, T=0, `n-match 32` | 1 | do 131k | ten sam serwer bez ngram | „same lossless verify” | `tools/session_bench.py` | 260.8 ⇒ ≥4.5 tok/krok | **plausible dla specjalnego workloadu** (pliki emitowane ponownie w całości; drafty do 64 tok.). [NIEZWERYFIKOWANE: surowe logi nieczytane] |
| X2 | LukasParke (5090, llama.cpp): kaskady ngram→DFlash2 −8…−64%, ogony z kontekstu −21% | 5090 | IQ4_XS + DFlash2 | ich zestaw | 1 | 131k | DFlash2 n7 | – | repo | – | **niezweryfikowalne** (kontrprzykład dla workloadów ogólnych) |

Wątek Reddit `r/LocalLLaMA/comments/1vtup5s/`: 403 dla czytnika i API. Łańcuch 82 → 114 → 138 → 381 potwierdza post na X (https://x.com/Oluwaphilemon1/status/2108729001762079052) oraz historia git:
- 08-17 `9850338`: 66 → 84;
- 08-18 `e964409`: 114/124;
- 08-19 `f05ab55`: lookup v1;
- 08-20 `407771b`: blok 16.

[NIEZWERYFIKOWANE: treść samego wątku].

## 2. Mechanizm: HyperQwen LABD (lookup-augmented block drafting)

Źródło: `patches/dflash2-lookup-drafting.patch` (HyperQwen @ `95ee3b6`), domyślne wartości w `patches/speed-knobs-envs.patch:34-89`.

**2.1 Wyszukiwanie** (`_suffix_lookup_kernel`, patch:346-413):
- jeden program Triton na żądanie, brute force po całej historii tokenów (int32 UVA, którą vLLM i tak trzyma), bloki po 1024 kandydatów;
- najpierw tani test NMIN tokenów, potem rozszerzenie do NMAX = 12;
- wynik to `len·2^32 + end`, więc jeden `max` daje „najdłuższy, przy remisie najnowszy”;
- dopasowanie może nachodzić na własny sufiks, więc okresowe wzorce (wcięcia, znaczniki list) też są proponowane;
- `valid = min(k, koniec_sufiksu − end)`: kopiuje tylko tokeny, które już istnieją.

NMAX = 12, a nie 32, bo dłuższy limit faworyzuje stare długie dopasowania; na zadaniu „cytuj i wyjaśnij” daje to 3.21 vs 2.69 tok/krok (komentarz patch:867-870).

**2.2 Fuzja** (`_fuse_draft_kernel`, patch:417-500):
- głowa (pozycje < 7, które proponuje drafter): lookup zastępuje token draftera, gdy `match ≥ NSTRONG = 6`, albo gdy `match ≥ NMIN = 6` i drafter zgadza się na pierwszych `AGREE` tokenach. Domyślnie AGREE = 0, mierzone 3.33 vs 3.27 tok/krok na C1;
- ogon (pozycje ≥ 7): wypełniany, gdy `match ≥ NMIN_TAIL = 4` i lookup jest właścicielem głowy;
- flaga `take_flags` mówi „mam czym wypełnić ogon” (`match ≥ LONGMIN = 6`, `valid > 7`).

**2.3 Bezstratność** (`_point_mass_draft_logits_kernel`, patch:504-540):
- dla pozycji z lookupu q = δ(token), więc akceptacja wynosi p(x), a residuum to p z wyciętym x;
- greedy w ogóle nie czyta q;
- to ta sama konstrukcja co w Strata (`STRATA_SPEC_PROB`, lookup jako masa punktowa).

**2.4 Planowanie długiego bloku** (`next_num_draft_tokens`, patch:948-996):
- scheduler dostaje 7 draftów, a pełne 15 tylko gdy przez **2 kolejne kroki** (a) była flaga ogona i (b) krok wyemitował ≥ 8 tokenów;
- flaga jest czytana z przypiętej kopii D2H z poprzedniego kroku: odczyt synchroniczny kosztował 5%;
- STICKY = 3 trzyma długi blok jeszcze 3 kroki, ale tylko przy 1 żądaniu: z wieloma żądaniami szerokość zależy od czasu przybycia innych, więc zmienia się zaokrąglenie i tekst greedy (`labd_soak.py`, patch:916-935);
- grafy CUDA są przechwytywane dla obu długości zapytania (8 i 16); bez tego krótki krok szedł piecewise i tracił 8% (25.9 vs 27.9 ms, `single-user/README.md:246-249`).

**2.5 Jak weryfikowane jest 16 tokenów:**
- to jeden forward V2 runnera z `num_query = 16` dla żądania;
- GEMM W4A16 Marlin dzieli wymiar M na kafle po 16 wierszy, więc 16 tokenów to wciąż jeden kafel M, a 17. token kupuje drugi blok M we wszystkich 64 warstwach (`docs/gotchas.md:253-263`);
- atencja weryfikacji to ich split-KV Triton (`patches/spec-decode-attn.patch`): `q_len·G` wierszy (G = 6) w kaflu 128 wierszy, czyli do 21 tokenów na jedno czytanie KV; mierzone 250/583/1132 µs na warstwę przy 8/16/32 zapytaniach i 25k (FA2: ~2 ms);
- GDN: tryb `mamba-cache-mode align` rezerwuje stronę stanu na każdą pozycję spekulacji, więc k=15 to 1.66 GiB vs 0.88 GiB na żądanie i 4 sloty zamiast 8 (`docs/optimizations.md:343-349`);
- kroki 8 vs 16 przy 25k: 7.83/260 → 30.1 ms, 14.97/381 → 39.3 ms (+31%). Ich szacunek: „+27% na krok przy 25k, +6% przy 1.5k”.

**2.6 Łańcuchy** (`dflash2-ngram-chains.patch`, `VLLM_DFLASH2_CHAIN`, domyślnie wyłączone):
- dopóki kopia ląduje cała, cały blok pochodzi z historii i forward draftera jest pomijany do pierwszego odrzucenia;
- +7% na kopii (256.9 → 276 t/s przy bloku 7), bez zmian na prozie;
- tylko greedy, bo przy próbkowaniu q punktowe wypiera lepsze drafty (−8% C1).

Drafter kosztuje u nich 2.85 ms na krok (10.7% kroku C1, issue #38).

**2.7 Numeryka kwantyzacji** (`docs/quality.md`):
- stan GDN fp16: PPL 8.044 vs 8.045;
- lm_head/embed int8 g128: ~0.6% błędu round-trip;
- lm_head GPTQ int4 skalibrowany na własnych hidden states: PPL +0.6%, a sam RTN int4 +1.5%;
- drafter MTP/DFlash2 int4: tylko akceptacja (DFlash2 int4 3.2 vs 3.4 tok/krok przy samplingu, 0 przy greedy);
- INT8_ACT (W4A8 Marlin) tylko w prefill: PPL +4.1%;
- prefill int8-QK (SageAttention-like, wygładzenie K średnią per głowa) zachowuje softmax (cos > 0.99999).

Bit-exactness: brak. Sami piszą: „greedy text flips at near-ties between sessions”.

## 3. Mechanizm: DFlash / DFlash2 (artykuł 2602.06036 i drafter NVIDIA)

- **Drafter:** 5 warstw (8 dla Coder), blok 16 (10 dla LLaMA). Cechy z 5 warstw celu są **wstrzykiwane w K/V każdej warstwy draftera** i trzymane w jego KV cache, a nie tylko w wejściu jak w EAGLE-3 (§4, A.3). Jeden przebieg niekauzalny na blok masek; trening zaczyna od losowej kotwicy, a strata jest ważona malejąco z pozycją.
- **Rozmiar bloku przy treningu i inferencji (Tab. 8, 8 warstw):**
  - b8 trenowany, test b16: τ 5.02 / 4.28 / 3.09 (Math500 / HumanEval / MT-Bench);
  - b8 trenowany, test b8: τ 5.21 / 4.61 / 3.29;
  - wniosek: **wydłużenie bloku ponad trening obniża τ**.
  Nasz pomiar DFlash2 (z selektorem) przy T=1 daje wzrost na kodzie (pl-kod 4.21 → 5.67 tok/krok, `qwen-opt/spec_sweep.jsonl`, `DRAFT_N=15 LABEL=q5`), ale spadek na prozie (2.59 → 2.43). Lucebox raportuje „draft 16 / verify 8 lepiej niż draft 8” (`repos/22-lucebox.md:17`). Dowody są mieszane; zależy od selektora i klasy tekstu.
- **Długi kontekst (Tab. 4):** bazowy drafter Qwen3.5-27B traci powyżej 4k (gov_report 4.53 → 2.09 przy 32k); fine-tune „Long” trzyma 3.56. NVIDIA Muse-Spark: 32k AL 3.25/2.90, high-entropy 2.44 (SWA 2048).
  To jest główny powód, dla którego lookup tak bardzo pomaga **DFlash2** przy 25k: drafter nie widzi dokumentu. Nasza głowica MTP ma pełną atencję. Próba okna MTP (S3) obniżyła u nas akceptację 3.31 → 2.78, więc to okno nie jest naszym ograniczeniem.
- **DFlash2 vs DFlash:** dwukranowa konwolucja w bloku wokół każdej podwarstwy i selektor parowy rank-256 po top-16 kandydatach na pozycję (`config.json` NVIDIA: `conv_kernel_size 2`, `selector_rank 256`, `selector_top_k 16`, `block_size 8`). To drafter **8 pozycji**; blok 16 to ekstrapolacja.

## 4. Mechanizm: dokładność tqLLM i jak to się ma do raportu 12

Źródło: https://github.com/turbo-tan/tqllm @ `23af3c9`.

- **Jedna arytmetyka atencji:**
  - każdy blok wielkości weryfikacji (dekodowanie N=1, łańcuch, MTP, drzewo, krótkie chunki prefillu) idzie przez dwuczęściowe kernele (`src/qwen35.cpp:2243-2246`, commit `7d7382b`);
  - punkt podziału zależy tylko od pozycji zapytania: `tq_split_point(qpos) = (qpos−15)/32·32` (`kernels/common.cuh:67-71`);
  - kafle są przeplatane po splitach według pozycji klucza, więc „wynik zapytania jest ten sam dla każdej szerokości weryfikacji” (`kernels/attention.cu:438-447`).
- **Matvec niezależny od szerokości:**
  - reguły w `kernels/formats/matvec_rules.hpp` dopuszczają tylko kandydatów przetestowanych bitowo, a wybór kernela jest stały per (cc, kształt), nigdy mierzony w runtime;
  - testy `tests/quant.cu:187-302, 1392-1402` porównują `memcmp` kolumny przy 1..16 kolumnach z wywołaniem wąskim.
- **Historia błędu (D1):**
  - prompt 3.7k tokenów dawał inną odpowiedź z drafterem, także w starszym wydaniu (`946b683`);
  - przyczyny: atencja jednoczęściowa vs dwuczęściowa (`7fb94d7`, `b6c95ad`, `7d7382b`) oraz wybór kernela prefillu dla 9–12 kolumn przy `-ub 4096` (`8bb1119`, wycofany w `015a14a` tego samego dnia);
  - **błąd wychodził tylko przy niektórych `ubatch`/kontekstach.**
- **Porównanie z nami:** to ta sama zasada co nasza opcja (b) w raporcie 12 (N=1 liczy arytmetyką kerneli wielokolumnowych plus stały split FA). Oni wymuszają ją testami CI; my mamy dowód symboliczny na ISA dla MMVQ/GDN i otwarty problem `kqv_out-3`.
- **Do przeniesienia:**
  - test end-to-end jak `test-dflash-exact`: długi prompt, 512 tokenów, przemiatanie `ubatch` ∈ {64, 512, 4096} i kontekstu ∈ {16k, 64k}, bo wybór kernela zależy od tych parametrów;
  - test `memcmp` per kolumna 1..16 dla K4 WMMA, co jest warunkiem bitexact dla W > 8.
- **Ograniczenia ich twierdzenia:**
  - greedy, 1 slot;
  - formaty KV z obsługą „tree” (inne idą starą ścieżką);
  - DSpark-tree na GB10 nie jest dokładny i jest przełączany na łańcuch;
  - brak deklaracji dla `--np > 1` i samplingu.

## 5. Porównanie z notatkami Lucebox / Strata / TensorFold / hipfire (bez powtórek)

| Silnik | Lookup | Szeroki blok | Wynik na kopii | Uwaga dla nas |
|---|---|---|---|---|
| Strata | SuffixDrafter (trigramy, 4 ostatnie pozycje), okno lookupu zastępuje MTP, gdy pierwszy token = draft MTP i polityka przewiduje więcej | ≤ 8 (`kVerifyMaxT`) | „edycje kodu +6–11%, reszta bez zmian” (`bbe8944e`); lookup-chain netto ujemny na Strix Halo | zgodne z naszą symulacją (hashline +4–8%) |
| TensorFold | okna kopii 16 → 64 wiersze, stany Mamby co 8. wiersz | do 64 | przepisanie pliku 3.7× (Flash Next), edycja kodu 1.4× (M5); dla samego 27B kopie lądują rzadziej niż drzewo DFlash2: 138 vs 146 t/s | bloki 32/64 opłacają się tylko przy przepisywaniu całych plików |
| Lucebox | – | draft 16, verify ≤ 16; przy > 8k verify 8 | – | – |
| hipfire | – | DFlash B = 16 na gfx1100 | 307.9 t/s na krótkim kodzie | to samo XTX, ale kod T=0 |
| HyperQwen | sufiks 6–12, fuzja z draftem, ogon tylko z lookupu, adaptacja + sticky | 16 (koszt schodkowy: 16 i 21) | 381 t/s na kopii verbatim | ich ogon to nasz EXT; ich nadpisywanie głowy jest dla nas szkodliwe (§6.3) |

## 6. Eksperyment CPU-offline: ile kopiowalnych spanów mają nasze workloady

### 6.1 Metoda

- **Tokenizer:** `tokenizer.json` z Qwen3.5-0.8B (`~/qwen-opt/mtp-train/smoke/qwen35-0.8b-hf/`). Słownik sprawdzony z nagłówkiem GGUF `Qwen3.8-27B-UD-Q4_K_XL.gguf` przez gguf-py: 248 070 / 248 070 identycznych id, 250 pustych slotów paddingu, pre = `qwen35`. Ponowne kodowanie tekstu odpowiedzi daje te same id w 38/57; reszta to niekanoniczne podziały samego modelu, nie błąd tokenizera.
- **Dane Qwena** (natywne `resp_ids`, T=1 top-k 20 top-p .95, reasoning low): `mtp-train/data/gen_p1.jsonl` (57 odpowiedzi, 69 207 tok.), `pod-results/data/gen_val.jsonl` (159, w tym 18 odpowiedzi na prompty `spec_sweep`, 33 selfoss-kod, WildChat EN/PL, aya, oasst2), `gen_train.jsonl` (481 PL). Łącznie 524 743 tokenów odpowiedzi. `gen_ds.jsonl` pominięty: to odpowiedzi off-policy, nie Qwena.
- **Agent:** 221 plików sesji omp (`~/.omp/agent/sessions`, 527 MB). Strumień jest renderowany jak kontekst Qwena: user, tekst asystenta, wywołania narzędzi w formacie XML `<tool_call><function=…><parameter=…>` (surowe stringi, bez escapowania JSON), wyniki narzędzi. Thinking jest pominięty, a kompakcja restartuje strumień. Okno lookupu to ostatnie 131 072 tokeny.
  - Symulowane wyjścia: 7.2 M tokenów: `edit` hashline 1.05 M, `edit` z `old_string` (str_replace) 27 k, `write` 2.26 M, `bash` 1.98 M, inne wywołania 1.41 M, tekst 0.47 M.
  - Do raportu trafiają tylko statystyki zbiorcze.
  - Zastrzeżenie: te wyjścia pisał model Claude, nie Qwen; protokół narzędzi, a więc i kopiowanie, jest ten sam [INFERENCE].
- **Lookup jak w HyperQwen:** najdłuższy sufiks 4..12 tokenów (najnowszy przy remisie), do 64 kandydatów, nakładanie dozwolone, kontynuacja do 15 tokenów (63 w wariancie długich łańcuchów).
- **Dlaczego to dokładna symulacja, a nie szacunek:** przy exact-match verify (greedy albo sample-and-match z jednym losowaniem RNG na wyemitowany token, czyli jak w llama.cpp) trajektoria nie zależy od draftów. Teacher-forced replay na zrealizowanym tekście jest więc dokładny w rozkładzie.
- **MTP:**
  - (a) **prawdziwe łańcuchy** produkcyjnej głowicy (greedy, 4 drafty, słownik 64k) dla każdej pozycji `gen_p1` z `mtp-train/data/ext_p1/chain.bin`; wyrównanie sprawdzone: `cum@1..4` = 0.779/0.565/0.404/0.293, zgodnie z `mtp-train/RESULTS.md`;
  - (b) dla reszty model skalibrowany na (a): P(draft ok | lookup ok do tej głębokości) = 0.968/0.969/0.974/0.984, w pozostałych przypadkach c dobrane tak, że 1+c+…+c⁴ = zmierzone tok/krok klasy (`spec_sweep` final-qwen: pl-proza 2.77, pl-tech 3.29, pl-kod 3.47, en-chat 2.43, en-tech 3.00, en-code 3.05; dla agenta założone 3.2).
- **Koszt kroku (XTX, ROCm, PM4):**
  - MTP n=4 = 27.74 ms (zmierzone), z czego draft 3.62 ms (S2), V(5) = 24.12 ms;
  - V(W) = V(5) + [vcost(W) − vcost(5)] z `qwen-opt/k4/vcost_qwen-k4b.csv` (llama-bench, d=2048);
  - plain 23.15 ms (tg128 43.2 t/s);
  - długi kontekst: +3.5 ms na każdy kafel kvq ponad 2 (`ceil(6W/16)`); kalibracja z d32768: n1 28.1 vs n5 33.8 ms, minus koszt kolumn matmul [INFERENCE].

### 6.2 Kopiowalność (udział pozycji wyjścia)

`d1` = lookup proponuje i trafia następny token; `≥8` / `≥15` = trafia co najmniej 8 / 15 kolejnych tokenów.

| klasa | tokeny | lookup proponuje | d1 | ≥ 8 | ≥ 15 |
|---|---|---|---|---|---|
| spec_sweep EN / PL / kod | 4.1k / 6.1k / 6.1k | – | 0.13 / 0.07 / 0.07 | 0.03 / 0.00 / 0.01 | – |
| czat/proza (gen_p1, WildChat, oasst2, aya) | 0.45 M | 0.10 | 0.01–0.10 | 0.00–0.02 | – |
| kod selfoss | 27k | – | 0.17 | 0.05 | – |
| agent: tekst | 468k | 0.27 | 0.16 | 0.025 | 0.011 |
| agent: bash | 1.98 M | 0.61 | 0.51 | 0.20 | 0.11 |
| agent: inne wywołania | 1.41 M | 0.55 | 0.44 | 0.15 | 0.08 |
| agent: edit hashline | 1.05 M | 0.72 | 0.58 | 0.26 | 0.17 |
| agent: edit str_replace | 27k | 0.69 | 0.60 | 0.38 | 0.32 |
| agent: write | 2.26 M | 0.39 | 0.27 | 0.07 | 0.04 |

Kontekst przy wyjściach agenta: mediana ≥ 113k tokenów (p25 55–111k), czyli prawie zawsze „długi kontekst”.

### 6.3 Kluczowy pomiar: czy MTP już kopiuje? (prawdziwe łańcuchy, 69 207 pozycji)

| warunek | P(MTP draft 1 trafia) | n |
|---|---|---|
| lookup trafia na d1 | **0.968** | 4 744 |
| lookup proponuje, ale chybia | 0.776 | 2 560 |
| brak dopasowania | 0.765 | 61 903 |
| łańcuch d2 / d3 / d4, gdy lookup trafia do tej głębokości | 0.938 / 0.914 / 0.899 | 3 412 / 2 596 / 2 055 |
| pełne 4 drafty na długiej kopii (m ≥ 6, r ≥ 8) | 0.935 | 1% pozycji |

Wniosek: tam, gdzie lookup ma rację, MTP zwykle też ją ma. Lookup wnosi tylko (1) tokeny **za** pozycją 4, (2) pominięcie draftu w łańcuchach, (3) ~3% przypadków, w których MTP chybia na kopii. Nadpisanie głowy lookupem (HyperQwen) psuje głównie te ~22% przypadków, w których lookup chybia, a MTP trafia.

### 6.4 Wyniki polityk (t/s na XTX, zmiana względem MTP n=4)

Polityki:
- **HYB-16:** reguły HyperQwen (lookup nadpisuje głowę przy m ≥ 6, ogon do 16);
- **EXT-W:** głowa MTP, ogon z lookupu tylko przy zgodności 4 draftów MTP z lookupem; długi blok po 2 nasyconych krokach + 3 trzymane;
- **+CH:** łańcuchy bez draftera, czyli następny blok w całości z lookupu, bez MTP, aż do odrzucenia.

Prawdziwe drafty MTP (gen_p1, krótki kontekst):

| klasa | MTP4 tok/krok · t/s | HYB-16 | EXT-8 | EXT-16 | EXT+CH-16 |
|---|---|---|---|---|---|
| wszystkie 57 | 2.78 · 100.3 | −0.9% | 0.0% | −0.1% | −0.1% |
| en-code / pl-code | 3.55 · 127.9 / 3.28 · 118.1 | −1.8% / −0.8% | 0.0% / +0.2% | −0.1% / +0.2% | −0.1% / +0.2% |
| en-tech / pl-chat | 3.06 · 110.4 / 2.73 · 98.5 | −1.9% / −1.5% | −0.1% / 0.0% | −0.3% / −0.2% | −0.3% / −0.2% |

Model skalibrowany, agent (t/s; krótki kontekst | ~32k):

| klasa | MTP4 | HYB-16 | EXT-8 | EXT-16 | EXT+CH-8 | EXT+CH-16 |
|---|---|---|---|---|---|---|
| edit hashline | 139.1 | +1.3% \| −9.5% | +4.4% \| +0.9% | +7.4% \| −3.6% | +6.0% \| **+2.3%** | **+8.2%** \| −2.9% |
| edit str_replace | 139.5 | +16.4% \| +4.5% | +10.0% \| +6.0% | +19.9% \| +7.9% | +14.0% \| +9.5% | **+22.9%** \| +10.3% |
| bash | 134.8 | −1.3% \| −10.8% | +2.6% \| −0.3% | +3.6% \| −5.9% | +3.1% \| +0.1% | +3.9% \| −5.7% |
| inne wywołania | 131.2 | −3.1% \| −11.2% | +1.5% \| −0.8% | +1.5% \| −6.2% | +1.8% \| −0.6% | +1.7% \| −6.1% |
| write | 124.7 | −3.1% \| −6.2% | +0.7% \| −0.2% | +1.0% \| −2.1% | +0.9% \| 0.0% | +1.2% \| −1.8% |
| tekst asystenta | 119.8 | −3.8% \| −5.3% | +0.2% \| −0.1% | +0.1% \| −1.3% | +0.2% \| −0.1% | +0.1% \| −1.2% |
| **mieszanka agenta (ważona tokenami)** | 130.3 | −2.0% \| −8.8% | +1.9% \| −0.2% | +2.6% \| −4.1% | +2.4% \| **+0.2%** | **+2.9%** \| −3.8% |
| czat/proza/kod (Qwen, skalibrowane) | – | −0.1…−2.0% | −0.5…+0.3% | −0.4…+0.5% | −0.2…+0.7% | −0.4…+0.6% |

Długie łańcuchy (EXT-16 + łańcuch 32/64 tokenów, krótki kontekst, V(32) = 40–48 ms, V(64) = 50–65 ms jako scenariusze, bo niezmierzone): mieszanka agenta +2.9% (CH16) → +3.2–3.3% (CH32/64 optymistycznie), +2.7–2.8% pesymistycznie. Hashline +8.3 → +9.9%, str_replace +21.9 → +26.8%. Bloki > 16 nie są warte kosztu na naszych danych.

Sufit teoretyczny (kopia verbatim, r = 15 wszędzie): łańcuch W=16 bez draftu = 15 tok / V(16) ≈ 31.2 ms → ~480 t/s przy krótkim kontekście. Przy 25k z kaflami kvq to ~41 ms i ~365 t/s [INFERENCE], czyli rząd wielkości 381 z HyperQwen na 3090.

### 6.5 Ograniczenia symulacji

- MTP dla agenta jest modelem, nie pomiarem; AL 3.2 to założenie.
- Kontekst agenta jest ucięty do 131k, a kopiowania z poprzednich sesji (cache ngram-mod między żądaniami) nie liczę.
- Koszt W > 8 przy długim kontekście to ekstrapolacja z dwóch punktów.
- Wyjścia agenta pochodzą od Claude, nie od Qwena.
- Sampling: dokładność „trajektoria niezależna od draftów” zakłada sample-and-match z jednym losowaniem na token.

## 7. Transfer na nasz stos

### 7.1 Gdzie w budżecie kroku

Krok MTP 27.74 ms = weryfikacja W=5 ≈ 24.1 ms + łańcuch MTP 3.62 ms (PM4, krótki kontekst). Lookup nie skraca żadnej ms kroku. Zmienia **tok/krok** (więcej tokenów z jednego przejścia wag) i ewentualnie usuwa 3.62 ms draftu w łańcuchach. Koszt to +2.48 ms (W=8) lub +7.09 ms (W=16) weryfikacji, plus kafle kvq przy długim kontekście. Maksymalny możliwy zysk na naszych danych:
- edycje +8% (hashline) / +23% (str_replace);
- mieszanka agenta +3% (krótki kontekst), ≈0 przy ~32k;
- czat 0%.

### 7.2 Ranking: (zysk na wąskim gardle × pewność) / koszt

| # | Pomysł | Zysk (nasze dane) | Pewność | Koszt (osobodni) | Ryzyko / bit-exact | Platformy |
|---|---|---|---|---|---|---|
| 1 | **Shadow-log lookupu** w serwerze: per krok m, v, r lookupu obok akceptacji MTP, bez wpływu na wyjście | 0 bezpośrednio; rozstrzyga #2/#3 na realnym ruchu użytkownika (PL, agent omp) | wysoka | 0.5 | brak (tylko log) | wszystkie |
| 2 | **EXT-W8 + łańcuchy**: MTP zostaje głową, ogon ≤ 3 tokeny z lookupu przy zgodności 4/4 i 2 nasyconych krokach, łańcuchy bez MTP przy pełnych blokach | edycje +2…+6%, str_replace +10…+14%, czat 0; mieszanka agenta +2.4% (krótki) / +0.2% (~32k) | średnia | 2 | W ≤ 8 mieści się w trybie BITEXACT (n_max ≤ 7); poza nim tekst greedy zależy od szerokości (jak u HyperQwen). Łańcuch pomija MTP: catch-up h dla przyjętych wierszy trzeba odrobić w następnym grafie MTP (ryzyko średnie) | logika hosta: HIP/CUDA/Vulkan/Metal; koszt W=8: HIP MMVQ 2–8 kol., CUDA MMVQ ≤ 8 |
| 3 | **EXT-W16** (na bazie #2) | krótki kontekst: edycje +7…+8%, str_replace +20…+23%; przy ~32k ujemne | średnio-niska (koszt FA) | +0.5, plus pomiar V(W)@32k | bitexact wymaga kolumnowo-niezależnego K4 WMMA (test jak tqLLM `quant.cu:1392`) | HIP K4 WMMA 9–16; CUDA > 8 → MMQ (+11% w LukasParke) |
| 4 | **FA kvq: jedno czytanie KV dla ≤ 16 tokenów × 6 głów** (6 kafli WMMA na blok zamiast bloku na kafel) | warunek #3 przy długim kontekście; może też obniżyć koszt W=5 (2 kafle → 1) przy ≥ 32k [INFERENCE] | niska–średnia | 2–3 | numeryka per kafel się nie zmienia, jeśli kolejność sumowania zostaje [INFERENCE] | HIP RDNA3 |
| 5 | Łańcuchy 32/64 | +0.3 pp ponad #3 na naszej mieszance; duże dla przepisywania całych plików (0x7067: 108.8 → 260.8) | niska dla naszych danych | 3–5 | MMQ w weryfikacji, replay LAG do 64 wierszy, FA | – |
| ✗ | Nadpisanie głowy lookupem (HYB, HyperQwen) | −1…−4% czat/tekst; mieszanka agenta −2.0% (krótki) / −8.8% (~32k) | wysoka (prawdziwe drafty) | – | – | – |
| ✗ | DFlash2 + lookup (przepis HyperQwen) | DFlash2 u nas < MTP przy T=1 (97.9–107.5 vs 108.8 t/s) | wysoka | – | – | – |
| ✗ | upstream `ngram-mod` przed MTP (priorytet n-gramu) | jak HYB: wyprzedza dobry draft MTP; bez `n-match 32` zgaduje źle | średnia | config | – | – |

### 7.3 Co zmienić w kodzie (dla #1–#3)

- `common/speculative.cpp`: przyrostowy indeks sufiksów po stronie hosta (hash n-gramów prompt + wygenerowane, O(1) na token; HyperQwen robi brute force na GPU, u nas wystarczy CPU, bo historia i tak jest na hoście), reguła EXT i kontroler 2+3 kroków.
- Szerokość weryfikacji per krok: T2 ma już grafy per szerokość (zmiana szerokości bez cache kosztowała 1.6 ms). PM4 przechwytuje graf per szerokość, więc potrzebne są W ∈ {5, 8} lub {5, 16}.
- `n_rs_seq`: musi być ≥ 15 dla W=16. Projekt LAG (S4/T1) nie ma snapshotów, więc VRAM rośnie tylko o bufory wierszy oczekujących [INFERENCE ~15 MB]. U HyperQwen vLLM align mode kosztował 2× stron stanu.
- Metryki serwera: `n_lookup_tail_accepted`, udział kroków długich; shadow-log (#1) z flagą env.

## 8. Projekty eksperymentów

**E1. Shadow-log na realnym ruchu** ($0, GPU tylko w produkcji użytkownika; brak obciążenia testowego)
- Hipoteza: na ruchu agenta omp udział tokenów z lookupem trafiającym ≥ 8 do przodu wynosi ≥ 15%, a P(MTP d1 | lookup d1) ≥ 0.95, czyli zgodnie z symulacją.
- Prototyp: log per krok (m, v, r, akceptacja MTP, szerokość) do JSONL, bez zmiany ścieżki.
- Pomiar: tydzień normalnego użycia; skrypt `policies2.py` na logach.
- Kill: jeśli udział ≥ 8 na ruchu użytkownika < 5%, zamknąć temat lookupu.

**E2. Koszt szerokości przy długim kontekście** (< 3 min GPU, wymaga zgody na GPU)
- Komenda: `llama-bench -m Qwen3.8-27B-UD-Q4_K_XL.gguf -fa 1 -ctk q4_0 -ctv q4_0 -p 5,8,9,12,16 -n 0 -d 2048,32768,98304 -r 5`.
- Hipoteza: V(16) − V(5) przy 32k ≤ 12 ms.
- Kill: jeśli > 12 ms, EXT-16 tylko poniżej 8k kontekstu, a priorytet dostaje #4 (FA).

**E3. EXT-W8 + łańcuchy, A/B na XTX** (~30 min GPU, wymaga zgody)
- Zestawy:
  - `spec_sweep` 6 × 3 (regresja);
  - nowy zestaw „copy”: 6 promptów (edycja pliku 2k/8k/32k z poleceniem „zwróć cały plik”; cytuj sekcje dokumentu; refaktoryzacja z zachowaniem kodu; PL i EN), T=0 i T=1.
- Pomiar:
  - ABBA na świeżych serwerach, ms/krok i tok/krok;
  - greedy md5: EXT-W8 vs MTP-only w trybie `LLAMA_SPEC_BITEXACT=1`; przy domyślnym trybie oczekiwana różnica tylko przy remisie;
  - KLD niepotrzebne, bo weryfikacja jest dokładna.
- Kill: < +3% t/s na „copy” przy ≤ 8k albo > 0.5% regresji na `spec_sweep` → nie scalać.

**E4. EXT-W16** (po E2/E3)
- Kill: < +5% na „copy” albo regresja na promptach 32k.

**E5. Test end-to-end bit-exact w stylu tqLLM** (CPU do przygotowania, GPU < 5 min)
- Prompt code-review 3.7k, 512 tokenów, `ubatch` ∈ {64, 512, 4096} × kontekst ∈ {16k, 64k} × {plain, MTP n=2..7, EXT-8}.
- Kryterium: md5 równe w trybie BITEXACT.
- Kill: żaden; to test regresji do CI gałęzi `batch-invariant`.

**E6 (opcjonalnie, chmura, wymaga zgody): 3090 Vast, ~2 h × ~$0.30 ≈ $0.6**
- Nasz fork EXT-W16 vs HyperQwen `labd_bench.py --ctx 20000` na tym samym 3090.
- Cel: niezależna replikacja 381 i 133 oraz koszt W > 8 na CUDA (MMVQ → MMQ).

## 9. Dowody zewnętrzne

- **Za lookupem na kopiach:**
  - HyperQwen: +47% kopia, +6% skracanie z zachowaniem komend, +2–3% proza; GSM8K bez zmian;
  - Strata `bbe8944e`: edycje kodu +6–11%;
  - TensorFold: przepisanie pliku 3.7×, edycja 1.4×;
  - 0x7067 (llama.cpp, 3090, MTP + `ngram-mod`, `n-match 32`): sesja edycji 108.8 → 260.8 t/s; proza-7k +7%; najgorzej −1.7%;
  - hipfire 307.9 t/s na krótkim kodzie (DFlash B=16, gfx1100).
- **Przeciw / ostrożnie:**
  - HyperQwen: pozycje 7–14 to 0.65% na czacie, a @changtimwu zmierzył 0 (issue #22);
  - LukasParke (5090): kaskady ngram→DFlash2 −8…−64%, ogony z kontekstu −21%;
  - Strata lookup-chain: netto ujemny na Strix Halo, ±0.05% na 4090D;
  - TensorFold: dla 27B kopie < drzewo DFlash2 (138 vs 146).
- **Rankingi:**
  - LocalMaxxing: tqLLM 273.1 t/s na 3090 „submitted, approved” (reasoning-v1, `tqllm.com`). Strona modelu https://www.localmaxxing.com/en/models/Qwen/Qwen3.8-27B renderuje tabelę po stronie klienta, więc nie odczytałem wpisu [NIEZWERYFIKOWANE].
- **Brak:**
  - niezależnej reprodukcji 381 na innym 3090 (reprodukcje w `docs/reproductions/` dotyczą trybu C1/MTP);
  - upstreamu lookupu do vLLM („Upstream: none”);
  - surowych logów NVIDIA dla Muse-Spark (tylko tabele AL).
- **Co by obaliło nasze wnioski:** shadow-log (E1) pokazujący P(MTP | lookup) < 0.9 na realnych edycjach (wtedy HYB miałby sens) albo udział ≥ 15 tokenów > 30% (wtedy łańcuchy 32/64 tak).

## 10. Źródła

- HyperQwen (dawniej `syv-ai/qwen38-27b-rtx3090`, przekierowanie GitHub): https://github.com/syv-ai/HyperQwen @ `95ee3b6` (2026-10-11)
  - `patches/dflash2-lookup-drafting.patch:302-637` (lookup.py: `_suffix_lookup_kernel` 346-413, `_fuse_draft_kernel` 417-500, `_point_mass_draft_logits_kernel` 504-540), `:948-996` (`next_num_draft_tokens`), `:916-937` (STICKY);
  - `patches/speed-knobs-envs.patch:34-89` (domyślne wartości);
  - `patches/dflash2-ngram-chains.patch:44-84`;
  - `patches/spec-decode-attn.patch:1-28`;
  - `docs/optimizations.md:256-361, 363-412`; `docs/gotchas.md:253-268`; `docs/quality.md`;
  - `single-user/README.md:18-133, 170-263, 355-370, 487-523`;
  - `bench/labd_bench.py:1-80`;
  - commity `9850338`, `e964409`, `f05ab55`, `407771b`, `bd35b54`, `706a14b`; issue #22, #38.
- Post X: https://x.com/Oluwaphilemon1/status/2108729001762079052. Reddit `1vtup5s`: niedostępny (403).
- DFlash: https://arxiv.org/abs/2602.06036 (HTML: Tab. 1, 3, 4, 8; §4).
- NVIDIA: https://huggingface.co/nvidia/Muse-Spark-Open-816B-A42B-DFlash2 (`config.json`, README, wydane 2026-10-16).
- tqLLM: https://tqllm.com/, https://github.com/turbo-tan/tqllm @ `23af3c9`:
  - `docs/ARCHITECTURE.md:41-45`; `src/qwen35.cpp:2243-2246, 3101`;
  - `kernels/common.cuh:67-71`; `kernels/attention.cu:438-447`; `kernels/formats/matvec_rules.hpp:1-50`;
  - `tests/dflash_exact.cpp`; `tests/quant.cu:187-302, 1392-1402`;
  - commity `946b683`, `7fb94d7`, `b6c95ad`, `7d7382b`, `8bb1119`, `015a14a`; `CHANGELOG.md:60-63`.
- Zewnętrzne llama.cpp: https://github.com/0x7067/qwen38-27b-rtx3090-llamacpp (README: „Stacked n-gram drafting”), https://github.com/LukasParke/qwen38-27b-5090 (README: „What did NOT work”).
- Nasze:
  - `qwen-opt/NOTES.md:206-213, 297-331, 372-375`; `qwen-opt/k4/vcost_qwen-k4b.csv`;
  - `qwen-opt/spec_sweep.jsonl` (final-qwen, `DRAFT_N=6/10/15 LABEL=q5`);
  - `qwen-opt/mtp-train/data/gen_p1.jsonl`, `data/ext_p1/{chain.bin,meta.txt}`, `pod-results/data/gen_{val,train}.jsonl`, `mtp-train/RESULTS.md:1-60`;
  - `product/research/12-bit-exact-spekulacja.md`;
  - `qwen-opt/research/v2/rr-engines-drafters.md`, `strata/spec-host.md`, `tensorfold/spec-host.md`, `repos/22-lucebox.md`, `repos/30-hipfire.md`, `drafters.md`, `qwen-round5.md`.
- Symulacja: [15b-sim/](15b-sim/). Kolejność: `extract_agent.py` → `lookup_stats.py chat|agent` (`KMAX=63` dla łańcuchów) → `mtp_join.py`, `policies.py`, `policies2.py real|<pkl>`, `policies3.py`. Dane pośrednie w `/tmp/specsim`, nie są w repo (pochodzą z prywatnych sesji).

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie (1 linia) | kluczowe liczby (źródło) |
|---|---|---|---|
| `research/` | Raport 15b: frontier spekulacji (`raport-15b-spekulacja-frontier.md`) | Lookup z kontekstu + szeroki blok (HyperQwen) daje nam mało, bo MTP już kopiuje; sens ma tylko doklejanie ogona (EXT) na edycjach agenta. | P(MTP d1 \| lookup d1) 0.968 vs 0.765 (15b-sim/results.txt, mtp_join); mieszanka agenta EXT+CH-16 +2.9% krótki kontekst, −3.8% przy ~32k (EXT+CH-8: +2.4% / +0.2%); hashline +8.2%, str_replace +22.9%, czat 0% (policies2) |
| `repo/` | HyperQwen (`hyperqwen.md`) | vLLM + łatki dla Qwen3.8-27B na 3090: LABD lookup, blok 16, łańcuchy, prefix cache; werdykt: mechanizm przenośny tylko jako „ogon”, liczby 381 = kopia verbatim. | 381 t/s = 14.97 tok/krok, 39.3 ms/krok, dokument 25k z powtórzonych docs repo (labd_bench.py:42-47); czat 133 vs 131; pozycje 7–14 = 0.65% (single-user/README.md:510-516) |
| `repo/` | tqLLM (`tqllm.md`) | Silnik C++/CUDA z dokładną spekulacją greedy: dekodowanie N=1 przez te same kernele co weryfikacja, matvec testowany bitowo 1..16 kolumn, split atencji zależny tylko od pozycji. | naprawa 2026-10-13 `7d7382b`; test 3.7k prompt × 512 tok.; 273.1 t/s LocalMaxxing 3090 (tqllm.com) [do-sprawdzenia] |
| `eksperymenty/` | 2026-10-16 kopiowalność workloadów (`2026-10-16-lookup-kopiowalnosc.md`) | Symulacja CPU: lookup trafia 1–17% pozycji czatu i 27–60% wyjść agenta; HYB szkodzi, EXT pomaga tylko na edycjach. | tabele §6.2–6.4 tego raportu; vcost V(16) − V(5) = +7.09 ms, V(8) − V(5) = +2.48 ms (k4/vcost_qwen-k4b.csv) |
| `lekcje/` | MTP już kopiuje (`lekcja-mtp-juz-kopiuje.md`) | Zanim dołożysz drafter „z kontekstu”, zmierz P(MTP \| lookup); u nas 0.968, więc nadpisywanie draftów MTP to strata. | ext_p1 chain.bin, 69 207 pozycji (mtp_join.py) |
| `modele/` | aktualizacja `drafter-dflash.md` | DFlash2 n=15 przy T=1: akceptacja rośnie na kodzie (pl-kod 4.21 → 5.67), krok 32.9 → 39.1 ms, średnio 97.9 t/s < MTP 108.8; artykuł Tab. 8: b8 testowany na b16 ma niższe τ. | spec_sweep.jsonl `DRAFT_N=15 LABEL=q5`; arXiv 2602.06036 Tab. 8 |
| `research/` | aktualizacja `raport-12-bit-exact.md` | Dopisać metodykę tqLLM: test end-to-end z przemiataniem ubatch/kontekstu; kolumnowa niezależność K4 jako warunek bitexact dla W > 8. | tqllm `015a14a`/`8bb1119` (błąd tylko przy `-ub 4096`) |
| `kernele/` | aktualizacja `mmvq-multikolumnowe.md` lub nowa notatka o fattn-kvq | Koszt szerokości: kvq czyta KV raz na kafel 16 wierszy (`ceil(6W/16)`); kandydat na jedno czytanie KV dla ≤ 16 tokenów. | n1 28.1 vs n5 33.8 ms przy 32k (NOTES.md:193-195); HyperQwen 250/583/1132 µs przy 8/16/32 zapytaniach (spec-decode-attn.patch) [do-sprawdzenia] |
