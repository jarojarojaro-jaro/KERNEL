# Drafter dla Bonsai 2.5 27B Uncensored na XTX: plan (2026-11-25)

Cel: więcej tokenów na rundę przy T=0,7 bez zmiany wag celu (bezstratnie). Tylko research i projekt: bez treningu i bez GPU.
`[szac.]` oznacza szacunek, `[wniosek]` wniosek z liczb, a nie pomiar.

## 0. Wnioski
1. **Dla Bonsai 2.5 jest tylko głowica MTP PrismML** (`blk.64`, Q4_0). PrismML douczyło ją od głowicy Bonsai 2, a ta zaczynała od MTP Qwena (NOTICE.txt). Nie ma DSpark ani DFlash dla 2.5. Istniejące drafty są pod Qwen3.8-27B BF16 albo pod Bonsai 2 (ProCreations).
2. **„DFlash2 0,27–0,40 przy T=0,7” to błędny opis.** Te liczby, podobnie jak wszystkie akceptacje MTP w notatce (n2 0,76–0,79, n3 0,63–0,70, n4 0,58–0,61), pochodzą z dwóch ostatnich żądań xbench (L2048 i L8192, po 64 tokeny, **T=0**), bo `b25.sh` robi `tail -2`. **Akceptacji przy T=0,7 nikt nie zmierzył.** Przy T=0 i długim kontekście nieuczony DFlash2 daje 3,32 / 2,70 tok./rundę, a MTP n4 3,26–3,32, więc na trytowym pniu działa normalnie.
3. Z t/s wynika `[wniosek]`, że przy T=0,7 DFlash2 traci ok. 65–70% przyjętych draftów (0,7–0,85 z 6 na rundę), a MTP ok. 40%. Główna przyczyna to **drafty punktowe (argmax) przy próbkowanym celu** razem z **drogim stałym oknem 7**. Pełny rozkład nie jest przyczyną: GGUF ma domyślne `top_k 20, top_p 0,95, min_p 0,05`.
4. **Ranking przy T=0,7** (`[szac.]`, model kosztu z §4): (b) DSpark douczony na Bonsai-unc + losowanie sprzężone + okno wg pewności + powrót do MTP: **ok. 136–150 t/s (+16…28%)**. (a) douczona głowica MTP: ok. 118–121 (+1…3%). (c) LoRA na DFlash2: ok. 113 (−3%). Gotowy DSpark/DFlash2 bez treningu: ok. 107 (−9%), ale przy T=0 i na kodzie wygrywa.
5. Przed treningiem trzeba zrobić dwie rzeczy: bramkę GPU ok. 30 min (`drafter-gate.jobs`: akceptacja T=0,7 per kategoria + koszt rundy przy syntetycznej akceptacji) i naprawę w topce (E1). Wszystkie sprawdzone drafty dla Qwen3.8-27B (DFlash2 z-lab GGUF, RedHat, Avifenesh, RadixArk, GGUF magnitudedev/Anbeeld) nie mają własnych `token_embd` ani `output` i pożyczają je z celu. W topce graf draftu nie dostawał transformacji Hadamarda celu: `token_embd` szedł bez odwrotnej transformacji (`dflash.cpp:693`, `eagle3.cpp:181`), a związany `output` bez transformacji wejścia, bo `hdmd` grafu pochodził z modelu draftu. Prism łączy transformacje celu w kontekście draftu (`llama-context.cpp:265-271`, `build_embd_rows`). Do E1 każdy pomiar DFlash/DSpark na Bonsai w topce był nieważny. **E1 zrobione** w `~/wt/topka-dsp` (`topka-e1-draft-hdmd.patch`).

## 1. Istniejące drafty (HF, 2026-11-25)
| drafter | dla czego / trening | akceptacja (warunki) | dla nas |
|---|---|---|---|
| [PrismML 2.5 MTP](https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF) `blk.64` Q4_0 | pień 2.5 bazowy (nie uncensored), PrismML, start: głowica Bonsai 2 ← MTP Qwena (Unsloth UD-Q4_K_M) | 1,5–1,8× na NVIDIA, ustawienie n3 p-min 0,1 (4090: n3 p-min 0, 204 t/s); KL wł./wył. 5,2e-5 (H200) | to jest nasz baseline |
| [PrismML Ternary-Bonsai-27B DSpark](https://huggingface.co/prism-ml/Ternary-Bonsai-27B-gguf) | Bonsai 1 (Qwen3.6-27B), trenowany na trytowym celu | τ≈3,7 przy k=4, 1,34× na H100 | inna baza, nie pasuje; Bonsai 2 „no official DSpark drafter” ([SPECULATIVE.md](https://github.com/PrismML-Eng/Bonsai-demo/blob/main/SPECULATIVE.md)) |
| [RadixArk DSpark](https://huggingface.co/RadixArk/Qwen3.8-27B-DSpark) 1,86B (v2), licencja „other” | Qwen3.8 NVFP4/FP8, SpecForge; tapy 5/19/33/47/61, Markov r256, głowica pewności (`conf_proj` w GGUF Anbeeld) | v2: MT-Bench 3,29, Alpaca 3,23, HumanEval 3,85 (T=1, top-p 0,95, top-k 20, thinking, 7 draftów) | GGUF < 2 GB: [Anbeeld](https://huggingface.co/Anbeeld/Qwen3.8-27B-DSpark-GGUF) Q8_0 1,98 GB (v2); [magnitudedev](https://huggingface.co/magnitudedev/Qwen3.8-27B-DSpark-GGUF) Q8_0 1,46 GB (linia v1: 1,36B, tapy 4/16/28/40/52, z głowicą pewności, format upstream llama.cpp) |
| [RedHatAI DSpark](https://huggingface.co/RedHatAI/Qwen3.8-27B-speculator.dspark) Apache-2.0 | BF16, 1,74 mln × 8192 tok. Open PerfectBlend regenerowane, 0,9 TV + 0,1 CE; 8 tapów 4…60; **głowica pewności** | writing 3,77 (skumul.: 0,78 / 0,58 / 0,43 / 0,32 / 0,24 / 0,18 / 0,14), question 3,80, translation 4,55, HumanEval 4,42 (8 draftów, vLLM); długi kontekst 4,49 do 1M | najlepszy start (b) |
| [Avifenesh DSpark-Agentic](https://huggingface.co/Avifenesh/Qwen3.8-27B-DSpark-Agentic) Apache-2.0, 1,36B | od zera, odpowiedzi celu przy T=0; 5 tapów 4/16/28/40/52; głowica pewności | T=0,6 top-k 20 FP8: 2,88 / 2,92 (agent), GSM8K 4,61; greedy na NVFP4 GGUF: 2,23–2,41 (okno adaptacyjne), 96,3 vs 65,0 t/s | drugi kandydat (tańsze cechy) |
| [incoai/z-lab DFlash2](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2) (mamy Q4_K_M) | BF16 | H200, T=1, 7 draftów: MT-Bench 4,10 vs MTP 3,74 vs DSpark 3,01; HumanEval 4,39 / 3,91 / 3,30 | test b25d |
| [RedHatAI DFlash2](https://huggingface.co/RedHatAI/Qwen3.8-27B-speculator.dflash2) | speculators | writing 3,87, roleplay 3,85, multilingual 4,30 (T=1, top-p 0,95, top-k 20) | – |
| [EAGLE-4](https://huggingface.co/EAGLE-Corp/Qwen3.8-27B-EAGLE4) | własny kod, licencja eagle-4 | B300 TP4 T=1: 2,59× (DFlash2 2,39×, MTP 1,57×) | brak llama.cpp |
| [nvidia Qwen3.5-0.8B Draft](https://huggingface.co/nvidia/Qwen3.5-0.8B-Qwen3.8-27B-Draft) | zewnętrzny LM, prawdziwe q, T=1 top-k 20 | 3,92 vs MTP 3,81 (blok 16) | 16 kroków AR na rundę, za drogie na XTX przy batch 1 |
| [ProCreations Bonsai 2 MTP](https://huggingface.co/ProCreations/Ternary-Bonsai-2-27B-MTP) / [DFlash2](https://huggingface.co/ProCreations/Ternary-Bonsai-2-27B-DFlash2) | dopasowane do trytowego Bonsai 2 (cechy z natywnego prism), 304 sekw. | MTP: akceptacja z MTP Qwena 0,559 → 0,605, 157,6/165,0 → 171,7 t/s; DFlash2: 172,6 → 179,2 t/s (+3,8%), offline AL 2,30 → 2,64; n3 50,7%, n5 35% (T=1, top-k 20, RTX PRO 6000) | **dopasowanie do trytów daje +4…8% akceptacji, nie +30%** |

Nie znaleziono: EAGLE-3, Medusa, PARD dla Qwen3.8-27B; niczego pod Bonsai 2.5 Uncensored. Tencent DSpine b16: [[drafter-dspine]].

## 2. Dlaczego DFlash2 przegrał przy T=0,7 i co da się naprawić bez strat
### 2.1 Liczby z logów (`~/qwen-opt/queue/logs/b25d-*.log`, prism 910442b)
- Koszt rundy z L2k: DFlash2 n6 3,32 / 74,4 = 44,6 ms; MTP n2 2,52 / 96,8 = 26,0 ms (zwykły token prism 18,4 ms).
- Q6 T=0,7: DFlash2 41,7 t/s, czyli ok. 1,7–1,85 tok./rundę, ok. 0,12–0,14 akceptacji na draft; MTP n2 77,6, czyli ok. 1,9–2,0 tok./rundę `[wniosek]`. Topka-k157 MTP n2 coupled 116,9 t/s przy rundzie ok. 18 ms to ok. 2,1 tok./rundę `[wniosek]`.
- Przyczyny według wagi:
  1. **Drafty punktowe przy próbkowanym celu.** Draft = argmax, więc P(przyjęcie na pozycji i) = p_T(x̂_i | prefiks). Na prozie przy T=0,7 to ok. 0,5–0,6 i spada geometrycznie. DFlash2 stawia na 6–7 pozycji, MTP na 2. Prism nie ma sprzężonego losowania; topka ma je tylko dla MTP (`LLAMA_SPEC_COUPLED`), a ścieżka DFlash2 bierze argmax z kraty (`common/speculative.cpp:1298-1325`).
  2. **Stałe okno 7:** weryfikacja + draft ≈ 2,4 zwykłego tokenu (prism), w topce 26,9 + ok. 2–3 ms ≈ 2,2. Przy 1,8 tok./rundę to strata.
  3. **Niedopasowanie pnia:** DFlash2 uczony na cechach BF16 z thinking; Bonsai to tryty plus edycja warstw 27–44 (tapy 33 i 47 leżą za nią). Według ProCreations to +15% AL offline i +3,8% t/s, czyli czynnik umiarkowany.
  4. Pełny rozkład **nie** jest przyczyną: xbench wysyła tylko `temperature`, więc działają domyślne z GGUF (`general.sampling.top_k 20, top_p 0,95, min_p 0,05`, odczytane z naszego pliku). Nib miał 39 t/s przy top_k 0, my nie.
  5. Baza Hadamarda **nie** jest przyczyną w prism (łączy transformacje celu w kontekście draftu), ale **jest w topce** (pkt 0.5, naprawione w E1).
### 2.2 Poprawki bezstratne (cel nietknięty, każda za env, domyślnie wyłączona)
- **Sprzężony wybór w bloku** (rozszerzenie `LLAMA_SPEC_COUPLED` na DFlash2/DSpark): x̂_i = argmax_k[log q_i(k)/T + g(seed, klucz+i, k)] z tym samym szumem Gumbela co sampler celu. Cel losuje jak dotąd, więc rozkład wyjścia się nie zmienia, a przyjęcie ≈ P(trafienie) ≈ 1 − TV(p, q) zamiast p(argmax). Dowody: MTP coupled +3,5% przy T=1 ([[sprzezone-probkowanie-draftu]]); Inkling K-164 losowanie z q 1,93 → 2,05 tok./okno (+6%). Oczekujemy +5…15% przyjętych na rundę `[szac.]`. Dla DFlash2: wybór spośród top-16 kandydatów selektora; dla DSpark: łańcuch Markova z szumem (top-K na GPU, spacer na CPU).
- **q-losowanie + min(1, p/q) + resampling reszty**: upstream `--spec-draft-sampling probabilistic` dla DFlash2/DSpark (llama.cpp #30663, [docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md)). Równoważna alternatywa; zostajemy przy coupled, bo jest w topce, zgadza się z GPU verify i daje deterministyczny seed.
- **Kalibracja temperatury draftu**: drafty społeczności są niedopewne, skalowanie temperatury daje do ok. +10% AL ([arXiv 2611.33111](https://arxiv.org/abs/2611.33111)). U nas MTP najlepsze przy DT=1, więc stroić per drafter (`LLAMA_SPEC_COUPLED_DT`).
- **Okno wg pewności** (Nib `server.cpp:2721`: wiodące drafty z p > 0,8). Topka już obcina DSpark przy `conf < p_min` (`speculative.cpp:1336`). Dodać szerokość z kosztu: m = argmax E[tok]/(draft + v(m)), rozszerzając `common_spec_depth_policy`. Wymaga głowicy pewności (RedHat, Avifenesh); dla DFlash2 zastępczo softmax selektora.
- **Bramka per zapytanie z powrotem do MTP n2** (lekcja Mai K-158e: polski −39% bez bramki).
- **Top-k**: wynik jest bezstratny względem samplera z zapytania. Zmiana domyślnych to decyzja JARO; benchmarki zawsze z jawnymi top_k/top_p.
- **Drzewo z głowicy Markova** (PCTree, [arXiv 2608.02123](https://arxiv.org/abs/2608.02123)): +3…30% nad DSpark bez treningu. Na później.

## 3. Warianty samodestylacji
Wspólne:
- **Dane on-policy**: odpowiedzi Bonsai-unc przy polityce serwowania (T=0,7, top-k 20, top-p 0,95; ok. 20% T=0; thinking wył. i ok. 20% wł.). Mieszanka: 35% PL (proza, czat, tech), 25% kod/edycja, 20% EN czat/tech, 10% JSON/narzędzia/agent, 10% długi kontekst 4–32k. Prompty z publicznych zbiorów (WildChat-PL, oasst2, aya PL, self-oss-instruct), bez danych użytkowników. Off-policy szkodzi (pilot MTP: 3,281 → 3,235, [[2026-10-16-mtp-pl-pilot]]).
- **Zrzut stanów ukrytych**:
  - topka ma `llama_set_embeddings_layer_inp` / `llama_get_embeddings_layer_inp` (wejścia warstw, z tego korzysta przechwytywanie DFlash) oraz `llama_get_embeddings_nextn`; dopisać `llama-feat-dump` (ok. 200 linii: tapy fp16/fp8 + tokeny + top-32 logitów celu w shardach);
  - nasz `llama-mtp-extract` (gałąź `mtp-train`) jako wzór;
  - wzorzec ProCreations: `collect.cpp` na runtime prism z odwróceniem Hadamarda dla embeddingów;
  - ścieżka vLLM: `prism_ternary` ([fraserprice/bonsai-vllm](https://github.com/fraserprice/bonsai-vllm)) + bitowo wierny konwerter GGUF → vLLM ([nakakennnn](https://huggingface.co/nakakennnn/Ternary-Bonsai-2.5-27B-vllm), `conv_gguf_pq2.py`) + serwer stanów ukrytych speculators (`--target-layer-ids`), co daje gotowy przepis RedHat; ryzyko: zgodność wersji vLLM.
  - PrismML nie publikuje narzędzi do treningu drafterów.
- **Bezstratność**: sha256 pliku celu bez zmian, plain md5 greedy bez zmian, spec md5 deterministyczne ×2, pierwszy różny token to near-tie ([[lekcja-zmiana-draftu-zmienia-md5]]), KLD spec vs plain na poziomie 1e-5.
- Ceny (2026-11-25): Colab L4 1,94 j./h, A100 40GB 6,73 j./h; Vast minima on-demand ([GPU Radar](https://munkhbayarbr.github.io/gpu-radar/)): RTX 4090 $0,36, A100 SXM4 80GB $0,47, A100 PCIe 80GB $0,37, L40S $0,53, RTX PRO 6000 $1,07, H100 SXM $1,73 /h.

### (a) Douczenie głowicy MTP (`blk.64`) na wyjściach Bonsai-unc, wielokrokowo
- Co: głowica ok. 0,42B, start z Q4_0 PrismML (zdekwantyzowany), FastMTP rekurencyjnie K=3 (0,9·TV + 0,1·CE przy T=0,7), lm head zamrożony (shortlista 64k). Eksport Q4_0 albo Q8_0 (+0,2 GB, ok. +0,15 ms na krok `[szac.]`).
- Dane: 3–5 mln tokenów; h_final 10 KB/tok. + top-32 logitów, razem 30–50 GB.
- GPU: generacja na XTX ok. 3 h (noc, `-np 16`, 400–600 t/s `[szac.]`); trening L4 2–3 h (lustro mierzone 2,3 tys. tok./s, K=4) = 4–6 j., albo Vast 4090 ok. $1.
- Zysk: **+0…3% t/s**. Źródła: nasz pilot na Qwen Q4 ±0,2% offline; ProCreations: MTP Qwena → douczone +8% akceptacji (+4% t/s), dalszy trening +1,26%. PrismML zrobiło już ten krok na pniu 2.5, więc zostaje tylko przesunięcie po edycji uncensored.
- Ryzyka: lustro musi odtworzyć transformację Hadamarda głowicy (K-151, „przeniesienie transformacji na głowicę draftu”); niski sufit.
- Topka: podmiana `blk.64.*` w GGUF (graft jak w `build_b25.py`), loader bez zmian.

### (b) Drafter blokowy DSpark na stanach ukrytych Bonsai-unc (główny wariant)
- Co: start z RedHat DSpark (Apache-2.0, głowica pewności, 8 tapów 4,12,…,60; tapy 28/36/44 leżą w edytowanym zakresie 27–44, więc dopasowanie jest konieczne). Zapas: Avifenesh (5 tapów, cechy 51 zamiast 82 KB/tok.). Blok 8, Markov r256, pewność (BCE przeżycia). Strata 0,9·TV + 0,1·CE przy T=0,7 albo WTV ([arXiv 2609.24150](https://arxiv.org/abs/2609.24150)) pod dekodowanie z próbkowaniem. Własny lm head ze shortlistą 64k (`draft_vocab_qwen38`).
- Bramka przed treningiem: offline AL trzech gotowych DSparków na cechach Bonsai-unc (held-out) plus `dg-syn-df*` (§5).
- Dane: 20–40 mln tokenów on-policy; ok. 1 kotwica na 4 tokeny, czyli 5–10 mln kotwic.
- GPU `[szac.]`:
  - generacja 20 mln tok.: XTX 2 noce (darmowe) albo Vast H100 prism CUDA `-np 32` (1,5–2,5 tys. t/s), 2,5–4 h = $4–7;
  - cechy: prefill Bonsai na A100 ok. 1342 t/s (README PrismML), czyli ok. 4 h na 20 mln; shardy po 1 mln tok. (51–82 GB): zrzut → trening → kasowanie;
  - trening: ok. 1,2B trenowalnych, ok. 80 GFLOP na kotwicę, ok. 4e17 FLOP na epokę, ok. 1 h/epokę na A100, 2–3 epoki;
  - razem ok. 7–10 h A100 80GB na przebieg: Vast $4–10 albo Colab A100 40GB 47–67 j. (mieści się: GGUF 8 GB + trener ok. 25 GB, etapy po kolei). L4 się nie nadaje (AdamW dla 1,2B ≈ 19 GB).
  - 2–3 przebiegi: **ok. $15–30 albo 150–200 j. Colab**.
- Zysk: **+16…28% przy T=0,7** (tabela §4). Krzywa RedHat „writing” na BF16 i nasza kalibracja to `[szac.]`. Kod/JSON: ok. +50%. T=0: przynajmniej tyle co nieuczony DFlash2 (Q4 158,5 vs MTP 117,2 na prism).
- Ryzyka:
  - akceptacja zależy od języka (PL; Maya K-158c −39% bez bramki), ale bramka i powrót do MTP chronią przed stratą;
  - VRAM: drafter Q8 ok. 0,75 GB + lm head 64k ok. 0,35 GB obok MTP; przy ctx 262k sprawdzić zapas;
  - koszt draftu na XTX ok. 2 ms `[szac.]` (Maya K-158e: 1,96–2,04 ms, Nib 1,4);
  - weryfikacja m=4–5 w serwerze może kosztować więcej niż w llama-bench (patrz anomalia n3);
  - zgodność wersji vLLM/speculators.
- Topka:
  - HF `DSparkDraftModel` → `convert_hf_to_gguf.py` (klasa `DSparkModel`: `Qwen3DSparkModel`/`DSparkDraftModel`/`DSparkSpeculator`) z `--target-model-dir` (tokenizer i config Qwen3.8) → `llama-quantize Q8_0` → `-md X.gguf --spec-type draft-dspark --spec-draft-n-max 7 --spec-draft-p-min P`;
  - prace w silniku: E1 odwrotny Hadamard dla pożyczanego `token_embd` (i transformacja wejścia, jeśli drafter pożycza związany `output`); E2 spacer sprzężony; E3 okno z kosztu + podwójny drafter (MTP i DSpark, wybór per runda); test parytetu logitów draftera vs referencja PyTorch (cos > 0,9997 jak u ProCreations).

### (c) LoRA na DFlash2
- Co: LoRA r32 na 5 warstwach + pełne `fc`, ok. 50 mln parametrów; cechy z 5 tapów (5/19/33/47/61).
- Dane: 2–5 mln tok. (cechy 100–250 GB w shardach). L4 3–6 h = 6–12 j.
- Zysk: ≤ pełny fine-tune ProCreations (+3,8% t/s, +15% AL offline). Nie daje głowicy pewności i zostaje drafterem punktowym, więc przy T=0,7 ok. 113 t/s (< 116,9) `[szac.]`. Sens tylko dla T=0 i kodu.
- Topka: scalić LoRA → `convert_hf_to_gguf.py` (DFlash2) → `--spec-type draft-dflash`.

## 4. Ranking przy T=0,7 (czat EN; PL niżej)
Model: tok./rundę E = 1 + Σ c_i (c_i = P(i pierwszych draftów przyjętych), z sprzężonym losowaniem); t/s = E / (draft + v(m)).
- v(m) = 13 + 1,5·(m−1) ms dla m ≤ 5, v(8) = 27 ms, v(6–7) interpolowane. Zmierzone: 15,5 / 16,5 / 17,9 / 21,2 / 26,9 ms dla m = 2 / 3 / 4 / 5 / 8.
- Krok MTP 1 ms, przebieg bloku 2 ms `[szac.]`.
- Kalibracja: MTP n2 116,9 t/s daje E = 2,10, czyli c = 0,665 / 0,439.

| # | wariant | c1…c5 (szac.) | najlepsze m | E | t/s (model) | vs 116,9 | koszt |
|---|---|---|---|---|---|---|---|
| 1 | (b) DSpark Bonsai-unc + coupled + okno z kosztu + powrót do MTP | 0,75 / 0,55 / 0,40 / 0,30 / 0,22 | 5 (4 przy zmierzonym v) | 3,0 | 143 (136); adaptacyjnie ok. 140–150 | +16…28% | $15–30, E1–E3 ok. 3–5 dni |
| 2 | (a) MTP douczone (n2; n3 tyle samo) | 0,685 / 0,475 / 0,30 | n2 | 2,16 | 120 | +3% | ok. $1 / 4–6 j. |
| 3 | baseline MTP n2 coupled | 0,665 / 0,439 | n2 | 2,10 | 116,9 | 0 | – |
| 4 | (c) LoRA DFlash2 + coupled + okno | 0,60 / 0,37 / 0,23 / 0,14 | 4 | 2,20 | 113 | −3% | 6–12 j. |
| 5 | gotowy DSpark/DFlash2 + coupled + okno | 0,55 / 0,33 / 0,20 / 0,12 | 4 | 2,08 | 107 | −9% | tylko E1–E3 |
| – | (b) na prozie PL przy słabym PL w danych | 0,65 / 0,42 / 0,27 / 0,18 | 4–5 | 2,3–2,5 | 120 | +3% | bramka → MTP |
| – | (b) kod/JSON | 0,85 / 0,72 / 0,61 / 0,52 / 0,45 | 5–6 | 3,7 | 176 | +50% | – |

Uwaga: według modelu MTP n3 ≈ n2 (115,5), a zmierzone n3 było o 13% gorsze (topka-bonsai 92,6 vs 106,0). Dodatkowa głębokość MTP kosztuje w serwerze ok. 5–6 ms, a nie 2,5 ms `[wniosek]`. Bramka `dg-syn-mtp*` to rozstrzygnie. Drafter blokowy płaci za głębokość tylko weryfikacją.

## 5. Kolejność i bramki
1. **G0 (GPU ok. 30 min, bez builda):** `qwen-opt/bonsai25/drafter-gate.jobs` + `drafter-gate.sh` (topka-k157):
   - akceptacja przy T=0,7 per kategoria (code/tech/pl/json) dla MTP n2/n3 i rozkładu bez obcięcia;
   - koszt rundy MTP n2/n3/n4 przy tej samej krzywej syntetycznej;
   - koszt rundy bloku (przebieg DFlash2) przy krzywej docelowej (b) dla m = 3/4/5/7.
   - Decyzja: jeśli `dg-syn-df4/5` przy T=0,7 da < 125 t/s, (b) się nie opłaca na tym silniku i najpierw trzeba potanić weryfikację.
2. **E1 (zrobione 2026-11-25, bez przełącznika: czysta poprawka błędu, dotyczy tylko celów z prism.hadamard):** `llama_context::graph_hdmd()` daje grafowi draftu transformacje celu z ctx_other (wzór prism), `build_embd_rows` w DFlash/DSpark/EAGLE-3, a weryfikator pokrycia Hadamarda sprawdza też grafy draftu. Gałąź `topka-dsp` w `~/wt/topka-dsp` (z topka-rt 6c2c507e6), łatka `topka-e1-draft-hdmd.patch`. Testy: plain md5 topka-dsp == topka-k157 (`dsp-plain*`), realna akceptacja w `dsp.jobs`.
3. **G1:** realna akceptacja gotowych drafterów na Bonsai-unc przy T=0 i T=0,7 po E1: `dsp.jobs` (DFlash2 Q4_K_M i DSpark magnitudedev Q8_0, okna pewności p-min 0,5/0,8). RedHat (3,98 GB BF16, po konwersji Q8_0 ok. 2,1 GB) i Avifenesh (2,72 GB BF16, Q8_0 ok. 1,44 GB) wymagają zgody na pobranie > 2 GB. Wybór startu do (b).
4. **E2** coupled w bloku, **E3** okno z kosztu + podwójny drafter + bramka PL (env, domyślnie wyłączone; parytet md5 greedy, wall.py per kategoria, strata na pl > 2% blokuje).
5. **T1–T3:** dane (XTX nocą albo Vast) → trening (b) na Vast A100 80GB → GGUF Q8_0 → ABBA wall.py + xbench, md5/KLD.
6. (a) równolegle jako tani zakład (L4), jeśli G0 pokaże, że MTP n3 opłaca się po naprawie kosztu.

## 6. Ryzyka
- Krzywe c_i dla (b) to ekstrapolacja z BF16 i H100/B300; nasz cel jest trytowy i uncensored, więc trzeba to zmierzyć w G1 i offline.
- Koszt weryfikacji m=4–5 w serwerze wobec llama-bench (anomalia n3).
- Polski: zgodnie z lekcją dane muszą mieć dużo PL, do tego bramka i powrót do MTP.
- Synteza w topce (`--spec-synth-rates`) z `LLAMA_GPU_VERIFY=1`: sprawdzić w logu, czy akceptacja zgadza się z zadaną krzywą (to samokontrola joba).
- Licencje: RedHat i Avifenesh Apache-2.0; RadixArk „other”; EAGLE-4 własna.
