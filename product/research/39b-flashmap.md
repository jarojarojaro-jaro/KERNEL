# 39b. FlashMap (flow-map speculative decoding, arXiv 2610.24365): co to jest, czy jest bezstratne, czy da nam coś na Qwen3.8-27B / XTX

Data: 2026-10-20. Autor: podagent Res39bFlashMap. Tylko CPU: przeczytałem artykuł (PDF v1, 17.10.2026), stronę projektu, repo `al-jshen/flashmap` (`cd5b45b`, 2026-10-20, płytki klon w `/tmp/res-flashmap/repo`), konfigurację HF draftera, recepturę treningu w forku speculators (`al-jshen/speculators@835619f`) oraz kod weryfikacji SGLang (`dspark_verify.py`, `dspark_accept.py`, `reject_sampling.py` z `sgl-project/sglang@main`). W KB nie było wcześniej nic o FlashMap. Opis DFlash/DFlash2 pomijam, bo jest w R15b, 32f i [[drafter-dflash]]. Pokrewne prace mamy w R21a (DSpine) i R32b (DSpark).

Oznaczenia: `P:` = artykuł (strona/tabela), `K:` = repo flashmap (`plik:linia`), `S:` = SGLang main, `[INFERENCE]` = mój szacunek, niezmierzony.

## TL;DR

1. **Co to jest.** FlashMap to drafter blokowy klasy DFlash: czyta stany ukryte z 5 warstw celu i jednym przebiegiem sieci proponuje K=16 tokenów. Zamiast maskowanej dyfuzji dyskretnej ma ciągły flow po one-hotach słownika, zdestylowany do *flow mapy* (skok szum → blok w 1 NFE). Szum jest wspólny dla całego bloku, więc w teorii sloty mogą być ze sobą spójne. Sieć to DiT z 6 blokami, hidden 2048, adaLN od czasów (s, t) i cross-attention do cech celu. Embedding i lm_head celu są zamrożone, a draft idzie po słowniku 64k. Drafter ma 0.5B parametrów (DFlash w tym samym porównaniu ~1.05B). Weryfikacja to zwykły łańcuch K+1 wierszy w jednym przebiegu celu.
2. **Bezstratność: potwierdzona w kodzie.** Przy T>0 to standardowe rejection sampling `u·q < p` z resztą `max(p−q, 0)`, gdzie q to softmax slotu przy ustalonym szumie (`K: modeling_flashmap.py:520-535`). SGLang woła `chain_speculative_sampling_triton` z `threshold_single=1.0, threshold_acc=1.0` (`S: dspark_accept.py`), czyli **bez** ε-kary, którą R32b znalazł w DSpark z DeepInfer. Przy T=0 wynik to greedy celu (z zastrzeżeniem numeryki szerokiego wiersza, jak dla każdej spekulacji).
3. **„>6×” jest wąskie.** 6.14× to GSM8K przy T=0 na Qwen3-8B (gęsty), H200 NVL, SGLang, c=1, thinking off, K=16 (17 wierszy weryfikacji), jeden run na konfigurację, baza to zwykłe AR w SGLang. Na czacie przy T=1 jest **2.28–2.44×**. Sam DFlash w swojej pracy miał 6.08× (MATH-500), więc „>6×” nie jest nowością.
4. **Przewaga nad DFlash: +7.4% średnio, ale prawie połowa z mniejszego draftera.** Przeliczyłem ich liczby. γ rośnie średnio o +4.0%, a koszt kroku spada z 1.27–1.28 do 1.23 kroku AR (drafter 2× mniejszy). Baseline DFlash był **przetrenowany przez nich na 500K próbek** i jest słaby na czacie: MT-Bench T=0 ma γ 3.14, a oficjalny DFlash w swojej pracy 4.24 (inny wariant MT-Bench, więc to tylko sygnał). Główny mechanizm, czyli spójność bloku przy 1 kroku, ich własny test tasowania szumu wycenia na **0.08 tokenu na czacie** (0.32 na matematyce). Spójność pojawia się dopiero przy 2 krokach, a 2 kroki są tylko +1–2% szybsze od DFlash.
5. **Dla nas, licząc z budżetu R36:** bloki ≤ 8 wierszy (próg MMVQ), krok 29.2–29.9 ms.
   - **Proza PL T=1:** **−30…−36%**, jeśli drafter jest trenowany jak DFlash2, bez PL. Nawet przy τ równym MTP n=4 wychodzi −6…−8%. Próg opłacalności to τ ≥ 2.80–2.87 tok/krok, czyli +6.5…9% ponad MTP4, a w ich danych 1-krokowy FlashMap ma na czacie T=1 o ~12% niższe γ niż drafter AR (EAGLE-3).
   - **Czat T=1:** −4…+4% (≈0).
   - **T=0 EN kod/reasoning:** **+29…42%** względem MTP n=4 `[INFERENCE]`. To tylko +3…7% ponad ścieżkę L5 (DFlash2 na urządzeniu, +26…32%), której jeszcze nie ma, i wymaga checkpointu dla Qwen3.8-27B, którego **nie ma**: na HF są tylko Qwen3-8B i Qwen3-4B.
6. **Własny trening nie wchodzi w grę.** U nich 25 h + 9 h na 32×H200 (~1.1k GPU-h) dla 8B, bez generowania danych. Dla 27B szacuję ~2–3k H200-h, czyli ~$8–12k `[INFERENCE]`, a nasz pilot MTP-PL kosztował $2.14 (R11). Do tego dane bez PL i brak potwierdzonej obsługi hybrydy GDN w ich forkach speculators/SpecForge.
7. **Werdykt:** watch-lista dla trybu L5 (T=0 EN kod/reasoning). Do prozy, czyli naszego celu ≥ 100 t/s, nic. Nie ma eksperymentu na XTX, który testowałby sam FlashMap, bo brak draftera dla naszego celu. Dwa ≤10-min eksperymenty niżej mierzą DFlash2 jako górny proxy i rozstrzygają, czy ta klasa drafterów jest warta śledzenia.

## 1. Jak to działa (z kodu)

- **Wejście:** cechy celu z warstw `[1, 9, 17, 25, 33]` (8B) są konkatenowane, rzutowane i trzymane w cache K/V cross-attention draftera. Na pozycji kotwicy dochodzi embedding tokenu kotwicy (`K: modeling_flashmap.py:402-409`).
- **Stan:** blok to punkt w R^{K×|V|} na ścieżce `x_t = (1−t)·x0 + t·onehot(y)`. Przy 1 kroku szum wchodzi tylko jako `x0 @ E`. Kod losuje go od razu jako `z @ chol(EᵀE)ᵀ` (ten sam rozkład Gaussa, bez wektora o rozmiarze słownika; `K: :356-373, :413-417`). Wejście sieci to `RMSNorm(π_s(x)E) + (t−s)·g·RMSNorm(xE)`: posterior plus liniowy kanał szumu. Bez kanału liniowego 1-krokowa mapa zapada się do marginesów, czyli do DFlash (`P: App. A`).
- **Draft:** `logits = lm_head(DiT(inputs, s=0, t=1))`, potem per slot `y_k ~ softmax(logits_k/T)` albo argmax (`K: :422-429`). Przy 2 krokach jest siatka `[0, 0.817, 1]` (config HF), a drugi skok liczy się tanio z banku 8192 przeliczonych szumów i 16 wierszy E na slot (`K: sglang/jump_bank.py:1-37`, `P: App. B`: −70% kosztu drugiego skoku).
- **Weryfikacja:** łańcuch kotwica + K draftów w jednym przebiegu celu. Przy T=0 brany jest najdłuższy zgodny prefiks i token bonusowy, przy T>0 rejection sampling (`K: :514-535`). W SGLang FlashMap jest wtyczką do workera **DSPARK** z `IdentityMarkov`, czyli zerowym biasem Markowa (`K: sglang/sampler.py:1-21`). Pod spodem to ta sama maszyneria co DSpark (R32b), tylko bez głowicy Markowa.
- **Drafter HF (Qwen3-8B):** `block_size 16`, `hidden 2048`, `6 warstw`, `draft_vocab_size 65536`, bf16 **1.0 GB** (`model.safetensors` 1 000 238 762 B), domyślnie 1 krok, siatki dla 1–4 kroków.

## 2. Tabela tez z werdyktami

| # | Teza | Źródło | Próba obalenia → potwierdzenie z innej strony | Werdykt |
|---|---|---|---|---|
| C1 | Drafter generuje cały blok K tokenów w jednym przebiegu (flow map, 1 NFE) | strona, `P: §3` | `K: draft()` z siatką `[0.0, 1.0]` to jedno wywołanie sieci i jeden lm_head; config `num_steps 1` | **prawda** |
| C2 | Bezstratne („exactly the same outputs”) | strona, README | Szukałem relaksacji akceptacji, jak ε=5e-5 w DSpark/DeepInfer (R32b). Referencja: `u·q < p` i reszta `(p−q)+` (`K: :525-535`). SGLang: `threshold_single=1.0, threshold_acc=1.0`, reszta `p−q` w `reject_sampling.py` (opcjonalna block verification też jest bezstratna). q to rzeczywisty rozkład losowania przy ustalonym szumie, a szum jest niezależny od losowości celu | **prawda** (w rozkładzie; przy T=0 greedy celu w numeryce weryfikacji szerokiej) |
| C3 | „up to 6.1× lossless” na Qwen3-8B | abstrakt | 6.14× to jedna komórka: GSM8K, T=0, H200 NVL, SGLang c=1, thinking off, max 2048 tok, K=16, jeden run. Czat T=1: 2.28–2.44×. Krok spekulacji kosztuje u nich tylko 1.23× kroku AR (γ/speedup, wszystkie komórki), bo 17 wierszy 8B na H200 jest prawie darmowe. Oficjalny DFlash: 6.08× MATH-500 | **prawda, wąsko**; nie przenosi się na nasz koszt kroku |
| C4 | +7% średniego speedupu względem „matched DFlash” | abstrakt, `P: §5` | Przeliczone z rys. 1c: +7.45% (T=0 +7.8%, T=1 +7.1%). γ +4.0% (T=0 +4.3%, T=1 +3.7%). Reszta to koszt kroku: 1.23 vs 1.27–1.28 kroku AR (drafter 0.5B vs 1.05B). Baseline przetrenowany na 500K Open-PerfectBlend, oryginał miał ~800K Nemotron v2 + CodeAlpaca. MT-Bench T=0 γ: ich DFlash 3.14, FlashMap 3.34, oficjalny DFlash 4.24 (cytują MT-Bench-101, więc porównanie jest przybliżone). Autorzy sami piszą „possibly undertrained” (39k/23k kroków vs 1M/100k w FMLM) | **prawda liczbowo, słaby baseline**; ~45% zysku to mniejszy drafter, nie lepszy model |
| C5 | Flow map w jednym przebiegu uchwyca zależności między tokenami | abstrakt, `P: §1` | Własny test tasowania (Tab. 2): Δ przy 1 kroku = 0.32 / 0.13 / **0.08** tok (matematyka/kod/czat), przy 2 krokach 0.78 / 0.47 / 0.25. W Tab. 2 FlashMap 1-krok (shared) jest **poniżej** DFlash na matematyce (7.05 vs 7.29) i kodzie (5.92 vs 6.07), choć w Tab. 1 jest powyżej (inny podzbiór, jeden run) | **częściowo**: przy 1 kroku mechanizm prawie nie działa; działa przy 2 krokach, które są tylko +1–2% szybsze od DFlash |
| C6 | Szybszy od DFlash na każdym benchmarku | `P: §5` | Speedup 18/18 komórek. γ: 15/18 (T=1 HumanEval i MBPP przegrywa, MATH remis) | **prawda** (speedup); γ nie wszędzie |
| C7 | Drafter AR (EAGLE-3) jest dokładny, ale wolny | `P: §5` | Na H200 krok EAGLE-3 (drzewo 16) = 2.1× kroku AR. Ale na czacie T=1 EAGLE-3 ma γ **+14%** nad FlashMap 1-krok (3.43 vs 3.00 MT-Bench). U nas draft AR (MTP n=4) kosztuje 2.28 ms z 27.38 (8%), więc ich argument kosztowy się odwraca | **prawda u nich, fałsz dla nas** |
| C8 | Wiele szumów, scalonych w trie przy budżecie 16 tok, daje +11% | `P: App. D, Tab. 4` | H100 SXM, 32 prompty, T=0; +4…24% (1 krok). Wymaga weryfikacji drzewa | **prawda**; u nas wymaga drzew GDN (L1, 10+ dni) |
| C9 | Działa w Transformers / vLLM / SGLang | README | Wtyczki `flashmap[vllm]`, `flashmap[sglang]` (worker DSPARK). Brak GGUF/llama.cpp, brak ROCm-specyficznego kodu | **prawda**; dla nas port od zera |
| C10 | Koszt treningu | `P: App. G` | Flow 25 h + destylacja 9 h na 32×H200 dla 8B (~1.1k GPU-h); całość z ablacjami 4600 GPU-h. Batch 256 sekw. × 4096 tok, 512/128 kotwic (`speculators .../flashmap_training.md`) | **prawda**; dla 27B ~2–3k H200-h `[INFERENCE]` |
| C11 | Istnieje drafter dla naszego modelu | HF | API HF: autor `j-shen` ma tylko `FlashMap-Qwen3-8B` i `FlashMap-Qwen3-4B` (2026-10-15); wyszukiwanie „flashmap” daje 2 modele. Cele gęste Qwen3, bez hybryd | **fałsz**: nie ma draftera dla Qwen3.5/3.6/3.8-27B |

## 3. Transfer na nasz stos (XTX, Qwen3.8-27B, MTP n=4 + lookup W16, GPU verify, sprzężone próbkowanie, PM4)

### 3.1 Model kosztu kroku

Budżet R36 (proza T=1): krok 27.38 ms = weryfikacja 24.50 (5 wierszy) + draft MTP 2.28 + top-k 0.11 + host 0.49, przy 2.63 tok/krok (96.1 t/s).

- Weryfikacja przy 8 wierszach: 24.50 + 3×0.85 = **27.05 ms**. Przy 16 wierszach: 24.50 + 9.4 (R24k) = **33.9 ms**. Przejście 8 → 9 wierszy to skok MMVQ → WMMA (+1.37 ms), a CUDA MMVQ ma ≤ 8 kolumn.
- Draft FlashMap dla 27B `[INFERENCE]`: DiT ~0.45–0.5B (6 × ~63M + projekcje 5×5120→2048), Q8 ~0.5 GB → ~0.55 ms odczytu przy 926 GB/s. Do tego lm_head 64k × 5120 iq4_xs ~0.17 GB dla 16 wierszy, cross-attn po cache kontekstu (~0.2 ms przy 4k) i ~90 uruchomień kerneli (~0.7 ms bez PM4). Razem **d ≈ 1.5–2.2 ms**, czyli tyle co MTP n=4 albo o 0.1–0.8 ms mniej. Cechy z 5 warstw celu muszą zostać na GPU, bo przez hosta DF2 zyskuje dziś ~+2% (32f).
- **Krok FlashMap K=7 (8 wierszy): 29.15–29.85 ms. K=15 (16 wierszy): 36.0–36.7 ms.**
- **Próg opłacalności (τ_FM ≥ τ_MTP4 · krok_FM / 27.38):**

| klasa | MTP4 τ | próg τ przy 8 wierszach | próg τ przy 16 wierszach |
|---|---|---|---|
| proza PL T=1 | 2.63 | **2.80–2.87** | 3.46–3.53 |
| tech (3.3 tok/krok) | 3.30 | 3.51–3.60 | 4.34–4.42 |

Dla porównania: MTP n=7 kosztuje 27.38 + 3 × 1.45–1.6 = 31.7–32.2 ms (35 E1). Przy tej samej głębokości 7 drafter równoległy oszczędza więc **2.2–2.6 ms/krok (7–8%)**. To jedyna strukturalna przewaga tej klasy u nas. Liczy się tylko tam, gdzie τ rośnie z głębokością, czyli przy T=0 na kodzie i reasoningu.

### 3.2 Oczekiwany zysk per klasa

Punkt odniesienia: DFlash2 (z-lab, pełne dane) na naszych klasach (R16d, 32f). Mnożniki FlashMap/DFlash wziąłem z ich Tab. 1 (γ) i z różnicy kosztu draftera.

| klasa | DF2 vs MTP4 (32f/R16d) | FlashMap γ vs DFlash | **FlashMap vs MTP4 u nas** | warunek |
|---|---|---|---|---|
| proza PL T=1 (96.1 t/s) | τ ×0.67 → 1.76 | ×1.05–1.12 (czat T=1, 1–2 kroki) | τ 1.85–1.97 → **62–68 t/s (−30…−36%)** | drafter trenowany bez PL, jak DF2 i jak FlashMap |
| proza PL, hipotetyczny drafter PL (własny trening) | – | – | przy τ = 2.63: 88–90 t/s (**−6…−8%**); próg +6.5…9% τ ponad MTP4 | u nich 1 krok ma γ −12% wobec AR na czacie T=1 → spodziewam się ≤ 0 |
| czat T=1 (114.6 t/s, PL/EN) | −6…−10% | ×1.05–1.08, draft −0.3…−0.8 ms | **−4…+4% (≈ 0)** | DF2 na urządzeniu (L5) |
| T=0 EN kod / reasoning | +26…+32% (na urządzeniu) | ×1.01–1.05 (T=0 kod/matematyka), draft −0.3…−0.8 ms | **+29…+42%** `[INFERENCE]` | checkpoint 27B (nie ma) + infrastruktura L5 (nie ma) |
| T=0 EN, wariant 2 kroki | – | γ +5–6% nad 1 krokiem, drugi skok +0.6–1.0 ms `[INFERENCE]` | +2…3% ponad 1 krok | jw. |
| multi-sample trie (App. D) | – | +11% (16 tok, H100) | przy 8 wierszach +5…8% `[INFERENCE]` | weryfikacja drzewa dla GDN (L1) |

Sufit: przy 8 wierszach i fizycznej podłodze kroku (18.17 ms, R36) nawet τ = 1.97 daje tylko 108 t/s na prozie. Dla prozy przy T=1 ta klasa drafterów nie ma więc sensu ani dziś, ani przy idealnym silniku. W prozie wygrywa tani drafter AR (MTP), bo jego koszt to 8% kroku.

### 3.3 Mapowanie na elementy stosu

- **Hybryda GDN:** drafter nie dotyka architektury celu, czyta tylko stany ukryte, embedding i lm_head. Weryfikację łańcucha do 8 (i 16) wierszy z cofaniem stanu GDN już mamy (MTP + lookup W16). Multi-sample trie wymaga kerneli drzewa (L1).
- **MTP / lookup:** FlashMap zastępuje MTP, nie dokłada się do niego. W limicie 8 wierszy konkuruje o miejsce z ogonem lookupu, jak DF2 (32f). Na edycji kodu i tak wygrywa lookup (R24j).
- **GPU verify / sprzężone próbkowanie:** przy ustalonym szumie sloty są niezależne. Można je więc losować kluczowanym Gumbelem (seed, pozycja, token), wspólnym z celem, jak MTP (R24p: +3.7–4.2% τ). To ten sam plan co dla DF2 w 32f, nic nowego. Rejection z resztą `(p−q)+` wymaga q z pełnego wiersza draftu (64k), a sprzężenie Gumbela tego unika.
- **PM4 replay:** DiT ma stały kształt per K, więc nadaje się do jednej taśmy. Jeden graf per szerokość, jak dziś.
- **NVIDIA:** werdykt ten sam (MMVQ ≤ 8 kolumn). Tensor cores tanio dokładają wiersze, ale nie zmienia to τ na prozie. **Mac:** brak portu MLX, brak checkpointu; bez działań.
- **Produkt:** liczby „6×” dotyczą H200, gęstego 8B, T=0 i matematyki. Nie wolno ich zestawiać z naszymi t/s na czacie.

### 3.4 Własny drafter dla Qwen3.8-27B?

- **Obliczenia `[INFERENCE]`:** na sekwencję 4096 tok forward celu 27B kosztuje ~2.2e14 FLOP, a drafter z 8192 slotami i lm_head 248k×5120 w backwardzie ~6.6e13. Wobec ~1.1e14 dla 8B to ×~2.6, czyli **~2.8k H200-h** (+30–50 h na regenerację 500K odpowiedzi). Przy $4/h (R10) to ~$11k, przy A100 $0.73/h (~3× wolniej) ~$6k. Cache cech zamiast forwardu online to ~25 TB (5e8 tok × 5 warstw × 5120 × 2 B).
- **Dane:** ich mieszanka jest „mostly English”. Zysk na prozie wymaga regeneracji PL przez cel. R11 pokazał, że na PL głowica MTP jest już w optimum (wyrocznia +27%, trening +0.2%).
- **Kod:** forki `al-jshen/speculators@flashmap` i `al-jshen/SpecForge@flashmap` istnieją. Obsługi hybrydy Qwen3.5/3.8 (GDN) jako weryfikatora nie sprawdziłem w kodzie, więc to `[INFERENCE]` ryzyko. Dochodzi doświadczenie TensorFold: trening drafterów od zera na H200 dał 3.8–5.1% akceptacji (R10).
- **Inicjalizacja z DFlash2 odpada:** inna architektura (DiT z adaLN vs warstwy Qwen z wstrzykiwaniem KV), a licencja DFlash2 to CC BY-NC-ND.
- **Werdykt:** 2–3 rzędy wielkości ponad nasze budżety pilotów, za zysk ograniczony do klasy T=0 EN, której L5 jeszcze nie obsługuje. **Nie.**

## 4. Co z tego dla nas (ranking)

| # | Pomysł | Zysk | Nakład | Bezstratność | Decyzja |
|---|---|---|---|---|---|
| 1 | Watch: `FlashMap-Qwen3.x-27B` jako zamiennik DF2 w trybie L5 (T=0 EN kod/reasoning) | +3…7% ponad DF2 na urządzeniu; razem +29…42% vs MTP4 na tej klasie `[INFERENCE]` | L5 (3–5 dni) + DiT w ggml (adaLN, cross-attn do cache cech, wejście `z·chol(EᵀE)`; 2–3 dni) + konwerter GGUF; VRAM +0.5–1.0 GB | tak (rejection / Gumbel) | tylko gdy pojawi się checkpoint; najpierw E1 |
| 2 | Lekcja metodyczna: oceniać „N× speedup” drafterów przez krok spekulacji / krok AR (u nich 1.23, u nas +38% za 17 wierszy) i przez γ przy ≤ 8 wierszach | – | 0 | – | do [[koszt-szerokosci-weryfikacji]] |
| 3 | Multi-sample trie z jednego przebiegu draftera | +5…8% przy 8 wierszach `[INFERENCE]` | wymaga L1 (drzewa GDN, 10+ dni) | tak | po L1, nie wcześniej |
| 4 | FlashMap na prozie / czacie T=1 | −36…+4% | – | tak | **odrzucone** |
| 5 | Własny trening draftera 27B | jw. | ~$6–12k, dane PL | tak | **odrzucone** |

## 5. Eksperymenty na XTX (≤ 10 min każdy)

Samego FlashMap nie da się uruchomić, bo nie ma draftera dla Qwen3.8-27B. Oba eksperymenty mierzą DFlash2 jako proxy: FlashMap ≈ DF2 × (1.01–1.05 γ przy T=0) i krok −0.3…−0.8 ms. Wszystko przy **T=0**, bo ścieżka DFlash w forku przy T=1 nie miała rejection sampling ([[drafter-dflash]], 2026-10-10), więc T=1 byłoby stratne. Ten sam build dla obu ramion: `run-llm.sh` (`~/llama-opt`).

**E1. Czy klasa „drafter blokowy” w ogóle przekracza próg na naszych klasach (8 wierszy)?** ~8 min (2 starty serwera + 6 promptów × 1 seed).
```bash
cd ~/KERNEL/qwen-opt
TEMPS=0 SEEDS=1 RUN_ARGS="qwen dflash rocm" ./spec_sweep.sh "DRAFT_N=7"
TEMPS=0 SEEDS=1 RUN_ARGS="qwen mtp rocm"    ./spec_sweep.sh "DRAFT_N=4"
```
Odczyt z `spec_sweep.jsonl`: per prompt tok/krok i `median_ms_step`. Szacunek FlashMap: τ_FM = 1.03 × τ_DF2, krok_FM = krok_DF2 − 0.5 ms. **Reguła decyzji:** jeśli na jakiejkolwiek klasie τ_FM/krok_FM ≥ 1.10 × (τ/krok MTP4), wpisujemy FlashMap na watch-listę L5 z tą klasą. W przeciwnym razie zamykamy temat do czasu checkpointu i lepszego draftera. Spodziewam się wygranej tylko na promptach kod/reasoning EN, a na prozie PL τ_DF2 ≈ 0.67 × MTP. Uwaga: dzisiejszy DF2 w forku przechodzi przez hosta, więc ms/krok DF2 przeszacuje koszt. Liczy się τ, a krok liczymy z modelu §3.1.

**E2. Kształt γ(K) dla drafterów blokowych na naszym modelu (przeniesienie rys. 2).** ~8 min.
```bash
cd ~/KERNEL/qwen-opt
TEMPS=0 SEEDS=1 RUN_ARGS="qwen dflash rocm" ./spec_sweep.sh "DRAFT_N=3" "DRAFT_N=7"
```
Jeśli τ(K=7)/τ(K=3) < 1.10 na prozie, każdy drafter blokowy (FlashMap, DSpine, DF2) jest na prozie bez szans, bo dodatkowe wiersze nic nie dają. Na kodzie oczekuję ≥ 1.25 (u nich γ rośnie z K aż do 16 na kodzie i matematyce, a na czacie wolno).

Bramki: przy T=0 tekst DF2 i MTP musi mieć md5 równe zwykłemu greedy (`greedy_check.sh`). Inaczej wynik jest nieważny.

## 6. Do bazy wiedzy

Wiersze do `wiki/ZRODLA.md`:

Sekcja „Prace naukowe”:

| źródło | data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| FlashMap (arXiv 2610.24365, github al-jshen/flashmap, jshen.net/flashmap) | `cd5b45b` 2026-10-20 | R39b | Bezstratny drafter blokowy klasy DFlash (flow map, 1 NFE); +7% vs przetrenowany DFlash na 8B, z tego ~45% z mniejszego draftera; spójność bloku przy 1 kroku ≈ 0. U nas: proza −30…−36%, czat ≈ 0, T=0 EN kod +29…42% tylko z checkpointem 27B i L5 | 6.14× GSM8K T=0 H200 c=1; czat T=1 2.28–2.44×; Δ tasowania 1 krok 0.08 tok (czat); 1.1k H200-h / 8B | wydany checkpoint dla Qwen3.5/3.6/3.8-27B; wersja z K ≤ 8 |

Sekcja „Modele, kwanty i drafery”:

| źródło | data | raport, notatka | werdykt | liczby | następnym razem |
|---|---|---|---|---|---|
| FlashMap-Qwen3-8B / -4B (huggingface.co/j-shen) | 2026-10-15 | R39b | Tylko gęste Qwen3; brak drafterów dla hybryd | 0.5B, bf16 1.0 GB, draft vocab 64k, K=16, siatki 1–4 kroków | drafter dla 27B (`api/models?search=flashmap`) |

Fakty / lekcje:
- **Lekcja:** speedup drafterów z prac (H200, gęste 8B) przeliczać przez stosunek krok spekulacji / krok AR. U nich FlashMap/DFlash to 1.23/1.28 przy 17 wierszach. U nas 17 wierszy to +9.4 ms ponad 5 (R24k), czyli +38% samej weryfikacji. Liczy się γ przy ≤ 8 wierszach, a nie przy 16.
- **Lekcja:** przy T=1 na prozie drafter AR (MTP) wygrywa z równoległym, bo jego koszt to 8% kroku (2.28 / 27.38 ms). Przewaga równoległego to oszczędność 2.2–2.6 ms przy głębokości 7, a ta ma sens tylko przy T=0 kod/reasoning.
- **Fakt:** SGLang `chain_speculative_sampling_triton` (DSPARK, `threshold_single=threshold_acc=1.0`) jest dokładny. ε-kara 5e-5 to cecha DeepInfer (R32b), nie SGLang.
