# 21a. DSpine (Tencent YouTu): równoległy drafter z „kręgosłupem” przyczynowym. Czy pobije nasze MTP n=4 + ogon lookup W16 na XTX?

Data: 2026-10-19. Autor: podagent ResDSpine. Tylko CPU: przeczytałem źródła, repo sklonowane do `/tmp/dspine/repo` (commit `07f326a`, jedyny), źródło TeX artykułu w `/tmp/dspine/src`. Niczego nie uruchamiałem na GPU.

Skróty źródeł:
- `P:` = źródło TeX arXiv 2609.36173v2 (`/tmp/dspine/src/sections/<plik>:<linia>`);
- `R:` = repo `github.com/tencent/dspine` (`/tmp/dspine/repo/<plik>:<linia>`);
- `HF:` = karta i `config.json` modelu `tencent/Qwen3-8B-DSpine-b16`;
- `16b`, `16i`, `16k`, `18`, `15b` = nasze raporty w `~/KERNEL/product/research/`.

---

## 0. Najważniejsze

1. **Co to jest.** DSpine to drafter z rodziny DFlash: 5 warstw, blok 16 (anchor + 15 propozycji), K/V z cech 5 warstw celu, współdzielone z celem embedding i LM head (`P:A_appendix.tex:5`, `HF: config.json`). Od DFlash różni się trzema rzeczami:
   - atencja w bloku jest **przyczynowa** zamiast dwukierunkowej (`P:4_method.tex:30`);
   - **po każdej warstwie** pozycja t dostaje bramkowaną wiadomość z przewidywanej cechy pozycji t−1. Cecha leży w stałej przestrzeni 1024-wymiarowej zbudowanej z wybielonych wierszy LM head celu (`P:4_method.tex:20-28`, `R:sglang_dspine/models/dspine.py:285-322`);
   - token wybierany jest **z warunkiem na już zdekodowanego poprzednika**: ostatni zapis jest przeliczany dla każdego z K=16 kandydatów poprzednika („transition cache”, K×K par na pozycję), a potem idzie łańcuch argmax lub próbkowanie (`P:4_method.tex:44-48`, `R:sglang_dspine/worker.py:173-190`).
2. **Liczby producenta są arytmetycznie poprawne, ale nagłówek jest pompowany.**
   - „+27.8% τ nad DFlash (3.77 → 4.82)” porównuje z DFlashem **przetrenowanym przez autorów na ShareGPT**, który jest dużo słabszy od oficjalnego checkpointu: na karcie HF oficjalny DFlash ma średnio 5.92 (`P:5_experiments.tex:32,36`, `HF`).
   - Uczciwe porównanie przy tych samych danych to tabela z karty HF (Open-PerfectBlend): **DSpine vs DFlash2 = +3.7% τ przy T=0 (7.83 vs 7.55) i +6.9% przy T=1 (6.98 vs 6.53)**. W artykule (ShareGPT) przewaga wynosi +10% / +12.8%. Z lepszymi danymi przewaga metody maleje.
   - Nie ma porównania z MTP ani z EAGLE-3. Nie ma długiego kontekstu (trening ≤ 3072 tokenów, serwer `--context-length 8192`), nie ma języków innych niż angielski, nie ma słupków błędu.
3. **Na XTX koszt szerokości zjada większość zysku.**
   - U nich weryfikacja 16 tokenów kosztuje ≈ 1.04× krok AR. Liczę to z 5.46 ms weryfikacji (`P:figures/latency_breakdown.pdf`) wobec 2/381 s = 5.25 ms kroku AR przy współbieżności 2 (`P:C_experiment_details.tex`, tab. SGLang).
   - U nas V16/V1 = 30.53/22.83 = **1.34× przy 2k** i 39.66/24.60 = **1.61× przy 64k** (`16b:59-64`).
   - Przy drafcie DFlash-podobnym 5.5–9.6 ms krok DSpine b16 to 36–40 ms przy 2k i 45–49 ms przy 64k, wobec 27.76 / 30.83 ms dla MTP4. **DSpine musi mieć 1.30–1.45× więcej tok/krok niż MTP przy 2k i 1.46–1.60× przy 64k, żeby tylko wyjść na zero.**
4. **Czat: nie pobije MTP n=4 (109 t/s). Polski czat i proza: duża strata.**
   - Model per klasa (τ DFlash2-27B × 1.05–1.20, krok 36–40 ms): pl-proza **−38…−51%**, pl-tech −23…−40%, en-chat −20…+2%, en-tech −17…+6%.
   - Wygrana jest tylko na **nowym kodzie** (bez kopii): pl-kod +9…+39%, en-code −6…+19% (§4.2).
5. **Code-edit: nie pobije ogona lookup W16 (401 t/s).**
   - Sufit DSpine to 16 tok/krok przy kroku ≥ 36 ms, czyli ≤ 444 t/s przy 100% akceptacji. Ogon ma 14.4 tok/krok przy 35.9 ms, a draft kosztuje go 0 ms GPU (`16b:15,109`).
   - Przy realistycznej akceptacji p = 0.97–0.99 na token DSpine daje 321–413 t/s, czyli od −20% do +3%. Przy długim kontekście (krok rośnie szybciej niż u ogona) przegrywa wyraźnie (§4.3).
6. **Polski to ryzyko nr 1.** Checkpoint 8B jest trenowany na Open-PerfectBlend: 1.42 M próbek, praktycznie tylko EN, ~42% matematyki (MetaMathQA 395k + orca-math 200k). Artykuł używa ShareGPT. DFlash2 z podobnym brakiem PL daje u nas pl-proza 1.32 tok/krok wobec 1.97 dla MTP (`16i:182`). Mechanizm DSpine poprawia spójność **głębokich** pozycji bloku. Na polskiej prozie wąskim gardłem jest pozycja 1, więc nie widzę powodu, żeby DSpine tę lukę zamknął `[INFERENCE]`.
7. **Wsparcie w llama.cpp: brak.** Kod istnieje tylko jako wtyczka SGLang 0.5.20 (CUDA/Triton, BF16, kwantyzacja zablokowana: `R:models/dspine.py:413-414`). Nasz fork ma już prawie cały fundament: graf DFlash/DFlash2/DSpark (`~/llama.cpp/src/models/dflash.cpp`, 1001 linii), przyczynową atencję draftu z metadanych `dflash.attention.causal` (`~/llama.cpp/common/speculative.cpp:975-977,1052`), wstrzykiwanie cech celu i sprzężone próbkowanie (`16k:7-9`). Brakuje konwertera, zapisów „bridge” po warstwach i transition cache. Szacunek: **5–7 osobodni**.
8. **Werdykt.** DSpine to solidna, uczciwie małymi krokami ulepszona wersja DFlash2 (+4–7% τ przy tych samych danych). **Nie jest zamiennikiem MTP ani ogona.** Ma sens tylko jako drafter klasy „nowy kod” w kontrolerze per klasa ruchu (plan 16i #4), przy kontekście ≤ 32k. Wersji 27B jeszcze nie ma (roadmapa: „DSpine for Qwen3.8-27B” niezaznaczone, HF: brak repo 27B na 2026-10-19). **Rekomendacja:** nie portować na ślepo. Gdy 27B wyjdzie, zrobić bramkę G0 (config, 1 h) i pomiar τ offline na CPU (§8, kill K1), a dopiero potem port.

---

## 1. Jak DSpine drafuje (architektura z kodu, nie z marketingu)

### 1.1 Szkielet (to samo co DFlash)
- **Checkpoint 8B** (`HF: config.json`):
  - `architectures: DFlashDraftModel`, 5 warstw `full_attention`, hidden 4096, FFN 12288, 32/8 głów (GQA 4), `block_size: 16`, `mask_token_id: 151669`;
  - `target_layer_ids: [1, 9, 17, 25, 33]` z 36 warstw Qwen3-8B;
  - plik `model.safetensors` ma 2 475 535 344 B BF16, czyli ≈ 1.24 B parametrów. Liczę: szkielet ≈ 0.97 B + `fc` 5·4096→4096 ≈ 84 M + bridge ≈ 33 M + codebook 151 936 × 1024 ≈ 156 M. Embedding i LM head są pożyczane od celu.
- **Wejście:** blok `[anchor, mask × 15]` w jednym przejściu. Kontekst to cechy celu z 5 warstw, połączone, zrzutowane przez `fc` i podane jako K/V każdej warstwy draftu, tak jak w DFlash (`P:2_preliminaries.tex:24-28`).
- **Różnica 1, atencja w bloku jest przyczynowa.** Pozycja t widzi kontekst i pozycje 0..t (`P:4_method.tex:30`). Kod odrzuca checkpoint bez `draft_block_causal` i warstwy z oknem (`R:models/dspine.py:105-108,430-437`).
  - **Konsekwencja dla nas:** wynik pozycji t zależy tylko od pozycji ≤ t. Krótszy blok daje więc identyczne propozycje dla pierwszych k pozycji. DFlash2 z atencją dwukierunkową tego nie ma (artykuł DFlash, tab. 8: b8 testowany na b16 traci τ; wiki `modele/drafter-dflash.md:21`).
  - Serwer SGLang mimo to blokuje inny blok niż 16 (`R:models/dspine.py:447-454`). To ograniczenie implementacji, nie metody.
  - **Konsekwencja dla VRAM:** pełna atencja bez okna, więc KV draftu rośnie z kontekstem (§7.2). DFlash2-27B ma SWA 2048 (`z-lab/Qwen3.8-27B-DFlash2/config.json`).

### 1.2 Wstrzykiwanie poprzednika przez głębokość („spine”)
Po warstwach `selected_prefix_feature_layers = [1..5]`, czyli po **każdej** (`HF: config.json`, `R:models/dspine.py:482-503`):
1. `raw = h + residual`; `rms`; `z = √C · normalize(R_ℓ · RMSNorm(raw))` (C = 1024, `R_ℓ` ∈ 1024×4096 na warstwę). Wiersz anchora dostaje zamiast tego `√C · codebook[anchor]` (`R:models/dspine.py:249-283,338-345`).
2. `[q; s; v] = [G_q; G_p; A] · z` (3 × 512). Bramka `g_t = σ(q_t + s_{t−1} + b)`, wiadomość `m_t = g_t ⊙ v_{t−1}`, dla anchora zero (`R:models/dspine.py:349-353`).
3. `h_t = raw_t + rms_t · W_ℓ · m_t`, z `W_ℓ` ∈ 4096×512 na warstwę. Matryce `A, G_q, G_p, b` są wspólne dla warstw (`P:4_method.tex:28`).
- **Przestrzeń „unified transfer space”** (`P:A_appendix.tex:7-8`): wiersze LM head celu normalizowane L2, centrowane, PCA-wybielone do r = 1024 i znów normalizowane, czyli stała tablica `codebook` [V × 1024].
  - Przewidywana cecha poprzednika i embedding zdekodowanego tokenu leżą w tej samej przestrzeni. Ta sama ścieżka obsługuje więc i „przewidywanie”, i „decyzję”.
- **Koszt:** +33 M parametrów (~3% szkieletu, `P:A_appendix.tex:5`). Na H100 [INFERENCE: FA3 + 381 t/s AR przy współbieżności 2 pasuje do Hoppera] +0.15 ms na rundę (`P:5_latency_breakdown.tex:11`).

### 1.3 Dekodowanie z warunkiem na poprzednika (transition cache)
- Z ostatniej warstwy biorą top-16 kandydatów na pozycję z pełnego LM head (`R:worker.py:173-175`).
- Potem dla każdej pary (kandydat poprzednika j, kandydat pozycji i) liczą wynik ostatniego zapisu przeliczonego z `√C·C_{token_j}` w miejsce przewidywanej cechy. Odbywa się to bez GEMM-ów w czasie dekodowania, przez tablice słownikowe (`R:kernels.py:349-373`):
  - `TG[v] = (LMhead[v] ⊙ norm_w) · W_last` [V × 512];
  - `TSV[v] = [G_p; A] · √C·codebook[v]` [V × 1024].
- Wybór to spacer po tablicy K×K, z lewej do prawej (`R:kernels.py:473-495`). Przy T > 0 próbkują z softmaxu wyników po top-16 i dają rozkład q do zwykłego rejection samplingu łańcuchowego (`R:worker.py:200-242,320-395`). **Weryfikacja jest standardowa i bezstratna rozkładowo.**
- Ablacja (`P:5_ablations.tex:47`): bez last-write refinement τ spada o 6.6–7.1%, bez refinement i bez wstrzykiwania o 8.8–10.7%.
  - Uwaga: wariant „bez obu” (MATH 4.93) jest już **wyżej** niż przetrenowany DFlash (4.23) i bliski DFlash2 (5.10). Większość różnicy wobec DFlash bierze się więc z receptury treningu (strata CE + L1 z DSpark, zanik pozycyjny γ = 7) i z przyczynowej atencji, a nie z samego „kręgosłupa”.

### 1.4 Trening (dla planu własnego treningu PL)
- Cel, embedding i LM head zamrożone. Strata `0.1·CE + 0.9·‖q − p‖₁` z wagą pozycji `exp(−(t−1)/7)`, plus cosinus warstwowy do `C_y` z wagą λ rosnącą do 0.5 (`P:4_method.tex:66-78`, `P:A_appendix.tex:13-17`).
- Curriculum: z prawdopodobieństwem 0.5 → 0 cecha poprzednika w warstwach 1–3 jest podmieniana na prawdziwy token (`P:A_appendix.tex:18`).
- ShareGPT z odpowiedziami wygenerowanymi przez cel, thinking wyłączony, ≤ 3072 tokenów, 6 epok, 3655 kroków przy batchu 112 (`P:A_appendix.tex:20`).
- **Kodu treningu nie ma** (roadmapa repo: „☐ Training code for DSpine”).

---

## 2. Co zmierzyli i czy to prawda

| # | Twierdzenie | Co faktycznie zmierzono | Bazy | Nasza arytmetyka | Ocena |
|---|---|---|---|---|---|
| C1 | „τ 3.77 → 4.82 (+27.8%) nad DFlash” (abstrakt) | Qwen3-8B, 7 benchmarków, T=0, 15 propozycji/rundę, SGLang, 8 instancji × 16 współbieżnych, ≤ 2048 tok., bez system promptu (`P:C_experiment_details.tex:56`) | DFlash **przetrenowany przez autorów** na ShareGPT (`P:5_experiments.tex:14`) | 4.82 / 3.77 = 1.279 ✓. Oficjalny DFlash-b16 ma średnio 5.92 (karta HF), czyli więcej niż DSpine z artykułu | **poprawne liczbowo, pompowane**: baza osłabiona treningiem na słabszych danych |
| C2 | „+10.0% nad najlepszą bazą (DFlash2) przy T=0, +12.8% przy T=1 (DSpark)” | j.w. (`P:5_experiments.tex:48`) | DFlash2, DSpark, Domino na tych samych danych | 4.82/4.39 = 1.098 ✓; 4.42/3.92 = 1.128 ✓ | **plausible**, porównanie fair (ta sama receptura), ale dane ShareGPT |
| C3 | Karta HF: DSpine 7.83 / 6.98 (T=0/1) | Open-PerfectBlend, „same configuration” | DFlash2 7.55/6.53, DSpark 7.44/6.65 (ten sam trening); DFlash 5.92/4.94 i Domino oficjalne | per benchmark DSpine/DFlash2 T=0: +1.4…+4.9%, średnio **+3.7%**; T=1: +3.9…+8.4%, średnio **+6.9%** | **plausible**: najuczciwsza liczba. Z lepszymi danymi przewaga maleje ~2.7× (10% → 3.7%) |
| C4 | „+23.3% przepustowości nad DFlash, +11.1% nad DFlash2, do 4.0× nad AR” | GSM8K/MATH/HumanEval/MBPP, współbieżność 2–32, T=0, jeden GPU BF16 FA3 (`P:C_experiment_details.tex:73`) | AR SGLang; DFlash/DFlash2 z tym samym budżetem 15 | z tabeli: średnia DS/DFlash = 1.233 ✓, DS/DFlash2 = 1.111 ✓ (zakres 1.085–1.141), MATH-500 przy c=2: 1522/380 = 4.01× ✓ | **poprawne**, ale tylko math/code. **Czatu brak** w pomiarze przepustowości |
| C5 | „Runda DSpine 7.14 ms vs DFlash2 7.19 ms, −10.9% czasu na token” | fig. latency_breakdown: backbone 1.17 + injection 0.15 + post-head 0.36 + verify 5.46 ms (`P:figures/latency_breakdown.pdf`, `P:5_latency_breakdown.tex:11`) | DFlash2 1.35 + 0.39 + 5.45 | 1.17 + 0.15 + 0.36 + 5.46 = 7.14 ✓. Weryfikacja 16 wierszy ≈ 1.04× krok AR (5.25 ms) | **poprawne dla H100**. U nas V16 = 1.34–1.61× V1 (§4.1), więc ten bilans się nie przenosi |
| C6 | „DSpine najlepszy na wszystkich benchmarkach” | 7 benchmarków; MT-Bench to 80 promptów × 2 tury | – | różnice na Arena-Hard T=0 (+1.4% na karcie) bez słupków błędu ani seedów | **plausible kierunkowo**, przy pojedynczych benchmarkach mogą być w szumie |
| C7 | GSM8K τ 10.55 (karta) | – | – | PerfectBlend zawiera MetaMathQA (przeformułowania GSM8K/MATH train) i orca-math: ewaluacja w rozkładzie treningu | **zawyżone względem ogólnego ruchu**. Dla nas liczą się MT-Bench/Arena (5.63/5.13 T=0) |

Czego brakuje (dla nas kluczowe):
- **Brak MTP i EAGLE-3 jako bazy.** Qwen3-8B nie ma MTP, a EAGLE-3 dla Qwen3-8B istnieje publicznie, ale nie został porównany.
- **Brak długiego kontekstu.** Trening ≤ 3072 tok., serwer 8192.
- **Brak języków innych niż EN.**
- **Brak batch 1.** Akceptację mierzono przy 16 współbieżnych, ale τ od batcha nie zależy. Przepustowość zaczyna się od c=2.
- **Nieujawniony GPU.** Tylko „one GPU … FlashAttention-3”, więc Hopper [INFERENCE]. Weryfikacja 16.4 GB BF16 w 5.46 ms ≈ 3.0 TB/s, co pasuje do H100 SXM.

---

## 3. Czym DSpine różni się od reszty

| metoda | jak drafuje | warunek na poprzednika | koszt draftu (k propozycji) | trening | u nas |
|---|---|---|---|---|---|
| **MTP Qwen3.8 (n=4)** | 1 warstwa MTP celu, autoregresywnie k razy | pełny: każdy krok widzi wydraftowany token | k sekwencyjnych przejść; u nas 3.62 ms dla k=4 (`16i:202`) | przez Qwen, w pretreningu, wielojęzyczny | **domyślne**; czat 3.02 tok/krok (`18:165`), pl-proza 1.97 (`16i:182`) |
| **EAGLE-3** | 1 warstwa na fuzji cech low/mid/high celu, autoregresywnie, drzewo | pełny | k przejść małej warstwy + drzewo | zewnętrzny (SpecForge) | dla Qwen3.8-27B nie istnieje (`~/KERNEL/qwen-opt/research/drafters.md:40`) |
| **Medusa** | k niezależnych głowic na ostatnim stanie | brak (tylko drzewo kandydatów) | 1 przejście | lekki | słabsza od MTP dla Qwena (`18:503`) |
| **DFlash** | 5 warstw, blok z maskami, atencja dwukierunkowa, argmax per pozycja | brak (faktoryzacja po pozycjach, `P:2_preliminaries.tex:30-34`) | 1 przejście | ~800K Nemotron + CodeAlpaca, bez PL | 9B: pl-proza 1.00 (`16i:189`) |
| **DFlash2** | DFlash + dwutapowe przyczynowe konwolucje w szkielecie + selektor ścieżki top-16 (rank 256) po szkielecie | słaby w szkielecie (mieszanie stanów), pełny w selektorze | 1 przejście + lattice | j.w.; 27B: blok 8, SWA 2048 | mamy GGUF 1.06 GiB; n=6–7 ≈ MTP na czacie, n=15 gorzej (`15b:21`) |
| **DSpark / Domino** | szkielet DFlash + sekwencyjna głowica Markowa / gałąź korekcji po szkielecie | po szkielecie | 1 przejście + sekwencyjna głowica 0.88–0.97 ms na H100 | – | DSpark obsługiwany (`dflash.cpp:307-321`); ≤ MTP na czacie (`drafters.md:31`) |
| **DSpine** | szkielet DFlash, **przyczynowa** atencja bloku, **bramkowane wstrzykiwanie przewidywanej cechy poprzednika po każdej warstwie**, transition cache K×K | przez głębokość (od warstwy 1) + dokładny w ostatnim zapisie | 1 przejście + 0.15 + 0.36 ms na H100 | ShareGPT / PerfectBlend, ≤ 3072 tok., bez PL | **brak wsparcia**; 8B tylko, 27B „coming soon” |
| **ogon lookup W16** | MTP4 + dokładna kopia sufiksu z kontekstu do 16 wierszy | dokładny (to kopia) | **0 ms GPU** (hash na CPU, `16i:205`) | brak | code-edit 400.9 t/s, ×2.41 (`16b:15`); czat ≈ 0 (`16b:19`) |

Istota: DSpine poprawia wyłącznie **spójność wewnątrz bloku** równoległego draftu, czyli akceptację pozycji 3..15 pod warunkiem trafienia pozycji 1–2. Nie poprawia trafienia pozycji 1 tam, gdzie drafter nie zna rozkładu (polski). Nie skraca też naszej weryfikacji.

---

## 4. Rachunek na XTX (Qwen3.8-27B, nasz fork)

### 4.1 Model kosztu kroku
- **Weryfikacja** V(w) z `llama-bench -fa 1 -ctk q4_0 -ctv q4_0` (`16b:57-64`):

| kontekst | V1 | V5 | V8 | V16 | V16 − V5 | V16 / V1 |
|---|---|---|---|---|---|---|
| 2k | 22.83 | 24.14 | 26.60 | 30.53 | 6.40 | 1.34 |
| 8k | 23.02 | 24.47 | 27.06 | 31.60 | 7.13 | 1.37 |
| 32k | 23.62 | 25.65 | 28.94 | 35.15 | 9.50 | 1.49 |
| 64k | 24.60 | 27.21 | 31.00 | 39.66 | 12.45 | 1.61 |

- **MTP4:** krok = V5 + 3.62 ms = 27.76 ms przy 2k. Zgadza się z serwerem: 27.74 ms, 3.02 tok/krok, 109 t/s (`18:165`, `16i:202`).
- **Draft DSpine-27B** `[INFERENCE]` (`D`):
  - dolna granica 5.5 ms: odczyt ~1.1 GB szkieletu Q4_K_M + LM head Q6_K 1.04 GB przy 15 wierszach + bridge; szacunek teoretyczny DFlash-rodziny 4–5 ms (`drafters.md:22`) + ~0.5–1 ms na bridge i transition cache;
  - górna granica 9.6 ms: zmierzony DFlash2 n=15 w naszym serwerze, krok 39.1 ms − V16 30.53 = 8.6 ms (`15b:21`), + ~1 ms na bridge i transition cache.
  - Przy 32–64k dochodzi pełna atencja draftu po KV kontekstu: 5 warstw × 8 głów KV × 128 × 2 = 10 240 elementów/token, q4_0 ≈ 5.8 KB/token, czyli 0.38 GB przy 64k. Przy 4 kaflach GQA [INFERENCE wg modelu kafli `15b:20`] to +1–2 ms.
- **Próg opłacalności** (DSpine b16 vs MTP4, ten sam stosunek dla t/s):

| kontekst | krok MTP4 | krok DSpine b16 (D 5.5 / 9.6) | wymagany τ_DSpine / τ_MTP |
|---|---|---|---|
| 2k | 27.76 | 36.0 / 40.1 | **1.30 / 1.45** |
| 8k | 28.09 | 37.1 / 41.2 | 1.32 / 1.47 |
| 32k | 29.27 | 40.6 / 44.8 | 1.39 / 1.53 |
| 64k | 30.83 | 45.2 / 49.3 | **1.46 / 1.60** |

Dla porównania u autorów: (5.46 + 1.68) / 5.25 = 1.36 kroku AR na rundę b16. U nas DSpine b16 to 36–40 / 22.83 = 1.58–1.76 kroku plain, a MTP4 tylko 1.22.

### 4.2 Czat i nowe pisanie (T=1, bez kopii)
Założenia `[INFERENCE]`:
- τ_DSpine-27B = τ_DFlash2-27B × (1.05–1.20). Dolna granica to przewaga z karty HF (+3.7…+6.9%), górna dodaje zysk z głębszego bloku 16 na przewidywalnych fragmentach.
- τ obu drafterów z per-klasowego pomiaru 27B na 3090 (`16i:182-187`; Magnitude DFlash2 b8 z kontrolerem vs nasze MTP4). τ to głównie własność modelu i draftera, więc przenoszę go na XTX.
- Krok DSpine 36–40 ms, MTP 27.74 ms (2k).

| klasa | τ MTP4 | τ DFlash2 | τ DSpine (est.) | MTP t/s | DSpine t/s | zmiana |
|---|---|---|---|---|---|---|
| pl-proza | 1.97 | 1.32 | 1.39–1.58 | 71.0 | 35–44 | **−38…−51%** |
| pl-tech | 2.99 | 2.48 | 2.60–2.98 | 107.8 | 65–83 | −23…−40% |
| pl-kod (nowy) | 3.52 | 5.29 | 5.55–6.35 | 126.9 | 139–176 | **+9…+39%** |
| en-chat | 2.61 | 2.87 | 3.01–3.44 | 94.1 | 75–96 | −20…+2% |
| en-tech | 2.97 | 3.39 | 3.56–4.07 | 107.1 | 89–113 | −17…+6% |
| en-code (nowy) | 3.24 | 4.18 | 4.39–5.02 | 116.8 | 110–139 | −6…+19% |

- **Odpowiedź: na czacie (spec_sweep PL/EN) DSpine nie pobije MTP n=4.** Na mieszance 6 klas średnio przegrywa. Wygrywa tylko na nowym kodzie.
- Kontroler z krótszym blokiem (7 propozycji: V8 + D = 32–36 ms) nie ratuje prozy PL, bo problemem jest τ, a nie szerokość: 1.45 / 34 ms = 43 t/s vs 71.
- Przy 32–64k nawet pl-kod zjeżdża do 0.96–1.27× MTP (model z §4.1), a dla agentów mediana kontekstu przekracza 100k (`18:327`).

### 4.3 Code-edit / kopia (tu dziś rządzi ogon)
- **Dziś:** MTP4 + ogon W16 na `mvs` daje 14.4 tok/krok przy ~35.9 ms, czyli **400.9 t/s** (`16b:15,109`, `18:166`). Przy ~30k: 373.5 t/s (`16b:106`), krok 39.2 ms (`16b:110`).
- **DSpine b16** przy akceptacji geometrycznej p na token, 15 propozycji, τ = 1 + Σ_{i=1..15} pⁱ:

| p | τ | t/s @36 ms | @38 ms | @40 ms | vs 401 |
|---|---|---|---|---|---|
| 0.95 | 11.20 | 311 | 295 | 280 | −22…−30% |
| 0.97 | 12.86 | 357 | 338 | 321 | −11…−20% |
| 0.99 | 14.85 | 413 | 391 | 371 | +3…−7% |
| 1.00 | 16.00 | 444 | 421 | 400 | +11…0% |

- Ogon przyjmuje dziś 96.0% swoich tokenów (`16b:112`), a DFlash2 b8 na pad.cu 99.7% (`16i:169`). Nawet przy p = 0.99 DSpine najwyżej remisuje. Przy 30k dodatkowo krok DSpine ≥ 40.6 ms wobec 39.2 ms ogona.
- Ryzyko długości: trening ≤ 3072 tokenów i pełna atencja bez okna. Kopiowanie z pliku 30k pozycji dalej oznacza pozycje RoPE spoza treningu [INFERENCE; DFlash2 z oknem 2048 spadał na `lazy.py` do 5.63 tok/krok, `16i:171-172`].
- **Odpowiedź: na code-edit DSpine nie pobije MTP4 + ogona W16.** Dołożenie go do ogona też nic nie daje: budżet szerokości (16 wierszy) jest już wypełniony darmowymi draftami.

### 4.4 Gdzie DSpine może coś dać w mieszance agenta
- Tylko klasa „nowy kod bez kopii” (`write`, część bash), przy kontekście ≤ 32k i przy kontrolerze, który na prozie i PL zostawia MTP, a na kopii ogon.
- `write` ma najniższą kopiowalność (27% d1, 7% ≥ 8; `15b:14`).
- Zysk czasu na mieszance ≈ f × (1 − 1/(1.10–1.30)), gdzie f to udział tokenów nowego kodu. Przy f = 0.2–0.3 `[INFERENCE]` daje to **+2…+7%**, a przy medianie kontekstu > 100k raczej ~0.
- To ten sam slot, który 16i #4 przypisało DFlash2: kod +20…38%, krok +5 ms, wysiłek 5–8 dni (`16i:246`). DSpine poprawi go o +4–7% τ, ale nie zmienia wniosku strukturalnego.

---

## 5. Ryzyko akceptacji po polsku

- **Dowody z naszej historii:**
  - DFlash2-27B: pl-proza 1.32 vs MTP 1.97 tok/krok, pl-tech 2.48 vs 2.99 (`16i:182-183`);
  - DFlash-9B: pl-proza 1.00 vs 1.71 (`16i:189`);
  - przyczyna: trening bez PL (wiki `lekcje/lekcja-drafter-gleboki-vs-mtp.md`);
  - na XTX DFlash po polsku 65 t/s vs MTP 78 (wiki `modele/drafter-dflash.md`).
- **Dane DSpine:**
  - artykuł: ShareGPT, z PL marginalnym [INFERENCE: ShareGPT to głównie EN/ZH];
  - karta: Open-PerfectBlend = MetaMathQA 395k, UltraInteract 289k, UltraChat 208k, orca-math 200k, UltraFeedback 187k, evol-codealpaca 111k, AutoIF 61k, lmsys-arena 57k (`huggingface.co/datasets/mlabonne/open-perfectblend`). Wszystko EN poza ułamkiem lmsys.
  - Odpowiedzi generuje cel, więc styl jest Qwena, ale prompty dalej są angielskie.
- **Mechanizm:** wstrzykiwanie wzmacnia pozycję t warunkiem na przewidywaną t−1. Na polskiej prozie typowy krok to odrzucenie pozycji 1 albo 2 (τ 1.3), więc łańcuch nie ma czego wzmacniać. Do tego polskie słowa rozpadają się na więcej tokenów i tokeny są krótsze, co dla drafterów bez PL oznacza niską pewność od początku [INFERENCE].
- **Słownik:** transition cache działa na top-16 z pełnego LM head, więc sam z siebie nie gubi tokenów PL. Optymalizacja „64k head” (`drafters.md:110`) zgubiłaby 3.5% tokenów polskiej prozy (wiki `eksperymenty/2026-10-10-sweep-mtp-dflash.md`), więc w ścieżce PL jej nie stosować.
- **Jedyne lekarstwo to trening z polskim.** Kodu treningu nie ma, ale receptura jest opisana dość dokładnie (§1.4), żeby ją odtworzyć na bazie SpecForge (DFlash training).
  - Trening drafttera 27B wymaga stanów 27B dla setek tysięcy próbek. Lokalnie na XTX to tygodnie, w chmurze wymaga zgody. **Poza planem.**

**Ocena ryzyka: wysokie (≥ 80%), że DSpine-27B od Tencenta będzie na pl-proza < 1.6 tok/krok, czyli 35–45% wolniej niż MTP** `[INFERENCE]`. Dlatego tylko per klasa, nigdy jako domyślny drafter Podkręta dla PL.

---

## 6. Integracja w llama.cpp

### 6.1 Stan
- **Upstream ggml-org/llama.cpp:** brak DSpine. Szukałem w sieci 2026-10-19; `docs/speculative.md` go nie wymienia, nie ma PR.
- **Repo Tencenta:** wtyczka SGLang `sglang==0.5.20` przypięta na sztywno, bo dziedziczy po wnętrznościach (`R:pyproject.toml`). Wymaga CUDA i Tritona, BF16, wyłączonego TF32 (`R:worker.py:49-55`), odrzuca kwantyzację (`R:models/dspine.py:413-414`).
  - `config.json` na HF wskazuje `auto_map: dflash.DFlashDraftModel`, ale pliku `dflash.py` w repo HF nie ma (lista plików: README, config, safetensors, LICENSE). Ścieżka transformers jest zepsuta. Jedyny wątek w dyskusjach HF to „dspine.git not found”.
- **Nasz fork (`~/llama.cpp`, master `b356fa262`)** ma:
  - wczytywanie DFlash/DFlash2/DSpark, w tym selektor DFlash2 top-16 z lattice (`src/models/dflash.cpp:128-148,520-560`) i głowicę Markowa DSpark (`:307-321`);
  - przyczynową atencję draftu przez `dflash.attention.causal` (`common/speculative.cpp:975-977,1052`);
  - ekstrakcję wejść warstw celu (`speculative.cpp:1045-1048`) i wstrzykiwanie cech (`batch_inject`, `:1011`);
  - sprzężone próbkowanie Gumbel-max (`GGML_OP_GUMBEL_MAX`, gałąź `opt-coupled`, `16k:7-9`). Dzięki niemu przy T>0 **nie trzeba** implementować rozkładu q ani rejection samplingu: akceptacja to dopasowanie do próbki celu z tym samym szumem, bezstratnie (`16k:8`).

### 6.2 Co trzeba dopisać

| krok | co | z czego | osobodni |
|---|---|---|---|
| I1 | konwerter HF → GGUF: tensory `selected_prefix_bridge.{prev,gate(+bias),predecessor_gate,out(=0),codebook,read_weight,early_read_weights,feature_write_weights}`, klucze `dspine.code_size/rank/active_layers/head_topk`, `dflash.attention.causal=true` | `R:models/dspine.py:142-170` | 0.5 |
| I2 | graf: zapis bridge po każdej warstwie (RMS, rzut 5120→1024, normalizacja, anchor z `get_rows(codebook)`, GEMM 1024→1536, przesunięcie o 1 w bloku, sigmoid, mnożenie, GEMM 512→5120, add ze skalą rms) | wyłącznie istniejące op-y ggml: `rms_norm`, `mul_mat`, `view`/`concat`, `sigmoid`, `mul`, `add`, `get_rows`. **Zero nowych kerneli HIP** | 1–1.5 |
| I3 | transition cache: top-16 z logitów 15 wierszy, potem wynik(n, i \| j) = E_{c_i}·(nw ⊙ raw_n) + rms_n · TG[c_i]·(σ(q_n + TSV_g[c_j] + b) ⊙ TSV_v[c_j]). TG i TSV liczone **w locie** z `get_rows` dla 16×15 kandydatów (63 M MAC), zamiast tablic [V × 1536] BF16 (~0.76 GB dla V = 248 320) | wzór z `R:kernels.py:349-373`; spacer 15 × 16 × 16 na CPU (3840 floatów) albo w grafie jak lattice DFlash2 | 1.5–2 |
| I4 | T>0: szum Gumbela (seed, pozycja, token) dodany do wyników łańcucha | `GGML_OP_GUMBEL_MAX` z `opt-coupled` | 0.5 |
| I5 | szerokość per krok (drabinka 4/7/15): blok przyczynowy, więc ucięcie jest dokładne; kontroler per klasa wspólny z 16i #2 | `common/speculative.cpp` | 0.5–1 |
| I6 | test: referencja eager z repo (`R:models/dspine.py:324-367`) przepisana do numpy vs nasz graf na CPU, na 8B (porównanie wyborów tokenów przy tych samych cechach) | `R:tests/ref_utils.py` | 1 |
| **razem** | | | **5–7** |

---

## 7. Zgodność z forkiem, VRAM i bezpieczeństwo sprzętu

### 7.1 Zgodność
- **MTP:** albo jedno, albo drugie w danym kroku. Oba w slocie oznaczają dwa konteksty draftu. Wspólny plan z 16i #4.
- **Ogon lookup:** na kopii ogon wygrywa (§4.3), więc kontroler daje pierwszeństwo ogonowi, gdy lookup ma ciąg ≥ 8.
- **Bit-exact:** W16 wychodzi poza `LLAMA_SPEC_BITEXACT` (≤ 8 kolumn, `16b:142`). Gwarancja „spec == plain przy każdym T” ze sprzężonego próbkowania wymaga bitowych logitów celu (`16k:8`), czyli w trybie BITEXACT tylko do 7 propozycji, dopóki 16i #5 (weryfikacja 1..16 kolumn niezależna od M) nie wejdzie. Rozkładowo bezstratne zawsze.
- **PM4:** drafter to osobny `llama_context`, jak DFlash2; nic specyficznego. Uwaga na historię page faultów (`17-gpu-page-fault.md`): nowy kod tylko za przełącznikiem.
- **kvq:** KV draftu można trzymać w q4_0 i liczyć istniejącym kvq (GQA 4 w drafcie vs 6 w celu). Weryfikacja bez zmian.

### 7.2 VRAM (XTX 24 GB)
- Cel 16.48 GB wag + KV 18 432 B/token (`18:584`). Przy 200k to 3.69 GB, razem ~20.3 GB + stan GDN 151 MB.
- DSpine-27B `[INFERENCE: jak DFlash2-27B + bridge]`: ~1.1 GB wag Q4_K_M + codebook 248 320 × 1024 (Q8_0 ≈ 0.27 GB) + **KV draftu z pełną atencją**. To 10 240 elementów/token: f16 20 480 B, q8_0 10 880 B, q4_0 5 760 B/token.

| ctx | f16 | q8_0 | q4_0 |
|---|---|---|---|
| 64k | 1.34 GB | 0.71 GB | 0.38 GB |
| 100k | 2.10 GB | 1.11 GB | 0.59 GB |
| 200k | 4.19 GB | 2.23 GB | 1.18 GB |

- Przy 200k i q4_0 wychodzi ~22.8 GB plus bufory, czyli na granicy. **Trzeba ograniczyć ctx do ~100k albo dodać okno.** DFlash2 z SWA 2048 to ~40 MB KV.
- Nie budować TG i TSV z referencji (~0.76 GB BF16), tylko liczyć w locie (I3).

### 7.3 Sprzęt
- **SSD:** jednorazowo ~2.5 GB (8B) lub ~4 GB BF16 (27B) + GGUF. Brak zapisów w pracy, zużycie pomijalne.
- **Termika i moc:** +6–10 ms obliczeń draftu na krok przy tej samej zajętości GPU. Pobór mieści się w obecnym limicie 285 W [INFERENCE]. Wentylatory były już problemem przy W16 (`16b:104`), więc monitorować jak przy każdym A/B.
- **Stabilność:** I2–I3 wyłącznie na istniejących op-ach, bez nowych kerneli HIP, za przełącznikiem domyślnie wyłączonym.

---

## 8. Plan

### 8.1 Teraz (wersji 27B nie ma): nic nie portować na GPU
- Nie zaczynać I1–I6 przed 27B. Jeśli 16i #4 (DFlash2 + kontroler per klasa + sprzężone próbkowanie) wejdzie wcześniej, DSpine będzie w tym samym slocie, a infrastruktura kontrolera się przyda.
- **Opcjonalny eksperyment E0 (CPU, ~1.5 dnia, dopiero gdy serwer nie jest obciążony; `nice -n 19`, 4 wątki):** teacher-forced τ na Qwen3-8B. Daje odpowiedź na ryzyko PL przed premierą 27B.
  1. Ciągłe greedy celu dla promptów `spec_sweep` (pl-proza, pl-tech, pl-kod, en-chat, en-tech, en-code) z llama.cpp CPU (Qwen3-8B Q8_0 ≈ 8.7 GB).
  2. Jedno przejście prefill z `llama_set_embeddings_layer_inp` na warstwach {1, 9, 17, 25, 33}, zrzut cech.
  3. Drafter DSpine-8B i, dla porównania, `z-lab/Qwen3-8B-DFlash-b16` w numpy/torch na CPU z referencji eager. Dla każdej pozycji anchora liczyć długość zgodnego prefiksu z greedy celu. Przy T=0 to dokładnie τ serwera, bo akceptacja greedy to dopasowanie do ciągu celu.
  - **Kill E0:** τ(pl-proza) / τ(en-chat) dla DSpine-8B < 0.6 → potwierdzone, że receptura nie zna PL; DSpine-27B tylko dla klasy kod. Dla porównania: MTP-27B 1.97/2.61 = 0.75, DFlash2-27B 1.32/2.87 = 0.46 (`16i:182-185`).
  - Jeśli zysk DSpine nad DFlash-b16 na pl-kod/en-code < +10% τ, niski priorytet także dla klasy kod.

### 8.2 Dzień premiery DSpine-27B

| krok | co | koszt | kill / bramka |
|---|---|---|---|
| G0 | przeczytać `config.json` i kartę: blok, SWA czy pełna atencja, `target_layer_ids`, dane (czy jest PL?), długość treningu, rozmiar, licencja; czy jest kod treningu | 1 h, CPU | jeśli pełna atencja bez okna **i** trening ≤ 4k → dopisać do planu limit ctx ≤ 100k; jeśli dane mają PL → priorytet ↑ |
| G1 | E0 na 27B: teacher-forced τ offline. Cel Qwen3.8-27B UD-Q4_K_XL na CPU (16.5 GB w 62 GB RAM), 6 klas + `mvs` + edycja 30k, porównanie z MTP4 (log `spec_sweep`) i DFlash2-27B | 1–1.5 d, CPU | **K1:** przewidywane t/s z §4.1 (krok = V16(ctx) + 7.5 ms) < MTP na wszystkich klasach poza nowym kodem **i** zysk na nowym kodzie < +15% przy 8k → kill portu |
| G2 | port I1–I6 za `LLAMA_SPEC_DSPINE=1` | 5–7 d | test I6: wybory tokenów graf vs referencja = 100% przy tych samych cechach |
| G3 | pomiar D(ctx): `llama-bench`-owy czas draftu przy 2k/32k/64k | 0.5 d, GPU | **K2:** D(2k) > 10 ms albo D(64k) > 14 ms → kill (próg z §4.1 nieosiągalny) |
| G4 | A/B ABBA: `spec_sweep` 6 × 3 T=1 (osobno klasy), `copy_bench` `mvs`/copy/long, replay agenta omp | 1 d, GPU | **K3:** brak +10% t/s na pl-kod/en-code przy 8k albo jakakolwiek regresja > 1% na prozie/czacie po włączeniu kontrolera → zostaje MTP + ogon; greedy md5 T=0 dla ≤ 7 propozycji w BITEXACT identyczne z plain |

**Oczekiwany zysk, jeśli wszystko przejdzie** `[INFERENCE]`: nowy kod +10…+39% przy ≤ 8k, mieszanka agenta +2…+7%, czat i code-edit 0 (kontroler zostawia MTP i ogon).

---

## 9. Źródła

- Artykuł: https://arxiv.org/abs/2609.36173 (v2, 2026-10-10; TeX: `/tmp/dspine/src/sections/*.tex`, figury `latency_breakdown.pdf`).
- Karta i config: https://huggingface.co/tencent/Qwen3-8B-DSpine-b16, https://huggingface.co/tencent/Qwen3-8B-DSpine-b16/raw/main/config.json.
- Kod: https://github.com/tencent/dspine (commit `07f326a`): `sglang_dspine/models/dspine.py`, `worker.py`, `kernels.py`, `tests/ref_utils.py`.
- Strona projektu: https://dspine-project.github.io.
- Dane: https://huggingface.co/datasets/mlabonne/open-perfectblend.
- DFlash2-27B config: https://huggingface.co/z-lab/Qwen3.8-27B-DFlash2/raw/main/config.json.
- Wtórne: https://www.explainx.ai/blog/tencent-dspine-speculative-decoding-drafter-qwen3-8b-27-percent-longer-acceptance-vs-dflash-2026 (powtarza nagłówek producenta, bez nowych pomiarów).
- Nasze:
  - `16b-lookup-tail.md:15,57-64,104-112,142`;
  - `16i-magnitude-co-robia-dobrze.md:169-172,182-191,202-205,246,278`;
  - `16k-sprzezone-probkowanie.md:7-21`;
  - `18-nastepna-fala.md:165-166,327,503,584`;
  - `15b-spekulacja-frontier.md:14,20-21`;
  - `~/KERNEL/qwen-opt/research/drafters.md:22,28-40,110`;
  - wiki `modele/drafter-dflash.md`, `lekcje/lekcja-drafter-gleboki-vs-mtp.md`, `eksperymenty/2026-10-10-sweep-mtp-dflash.md`;
  - fork `~/llama.cpp/common/speculative.cpp:975-977,1045-1052`, `src/models/dflash.cpp:128-148,307-321`.

---

## Do bazy wiedzy

- **Folder `modele/`, tytuł: „Drafter DSpine (Tencent) — DFlash z przyczynowym kręgosłupem”.**
  - 5 warstw, blok 16, atencja w bloku przyczynowa, bramkowane wstrzykiwanie cechy poprzednika po każdej warstwie w przestrzeni 1024-d z wybielonego LM head, transition cache K=16 (`P:4_method.tex:20-48`, `HF: config.json`).
  - 8B: 1.24 B parametrów BF16, plik 2.48 GB.
  - τ Qwen3-8B (karta, PerfectBlend): T=0 7.83 vs DFlash2 7.55 (+3.7%); T=1 6.98 vs 6.53 (+6.9%). Artykuł (ShareGPT): 4.82 vs 4.39 (+10%).
  - Przepustowość H100 [INFERENCE]: +11.1% nad DFlash2 (`P:tab. SGLang`).
  - Brak PL, brak długiego kontekstu (trening ≤ 3072).
  - Wsparcie: tylko SGLang 0.5.20. W llama.cpp brak; port do naszego forka 5–7 osobodni (§6.2).
  - 27B: zapowiedziany, niedostępny (2026-10-19).
- **Folder `lekcje/`, tytuł: „Akceptacja z H100 nie przenosi się na XTX: koszt szerokości”.**
  - U nich weryfikacja 16 wierszy ≈ 1.04× krok AR (5.46 vs 5.25 ms, `P:latency_breakdown`); u nas V16/V1 = 1.34 (2k) – 1.61 (64k) (`16b:59-64`).
  - Drafter b16 musi u nas mieć 1.30–1.45× tok/krok MTP4 przy 2k i 1.46–1.60× przy 64k, żeby wyjść na zero (§4.1).
- **Folder `research/`, tytuł: „Raport 21a: DSpine vs MTP4 + ogon W16”.**
  - Czat: pl-proza −38…−51%, en-chat −20…+2%.
  - Nowy kod: pl-kod +9…+39%, en-code −6…+19% (§4.2).
  - Code-edit: najwyżej remis z 401 t/s (p = 0.99: 371–413 t/s, §4.3).
  - Werdykt: tylko jako drafter klasy „nowy kod” w kontrolerze per klasa (16i #4), kill K1–K3 (§8.2).
- **Folder `research/` (aktualizacja przeglądu „spekulacja-frontier” albo `modele/drafter-dflash.md`), tytuł: „Nagłówki drafterów a bazy przetrenowane”.**
  - „+27.8% nad DFlash” DSpine liczy się od DFlasha przetrenowanego na ShareGPT (3.77), który jest słabszy od oficjalnego checkpointu (5.92 na tej samej karcie).
  - Uczciwa przewaga to +3.7…+6.9% nad DFlash2.
  - Zawsze szukać porównania „te same dane”.
