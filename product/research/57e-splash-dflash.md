# 57e. Splash + DFlash 2 (Inco AI, @inco_ai): silnik na Maca i co z niego bierzemy

Data: 2026-10-21. Praca tylko na CPU, bez GPU. Rozszerza R03/R15b/R16i/R21a (DFlash, DFlash2, DSpine) i [[drafter-dflash]]; nie powtarzam opisu architektury DFlash 1.

Źródła pierwotne: README `incoai/splash` (`main` `1482f6b`, 2026-10-20), blog „Splash” (2026-09-17), blog „DFlash 2” (2026-08-18), karta HF `incoai/Qwen3.8-27B-DFlash2`, nasz kod `~/wt/topka-int` (`cf927413b`), metadane GGUF draftera OrcaCyber.

## TL;DR

1. **Splash to silnik inference tylko na Apple silicon (M3+, macOS 26.4+, Metal), Apache-2.0, od Inco AI.** Inco AI to ten sam zespół, który wydał DFlash (arXiv 2602.06036, z-lab). Zasada: „silnik zbudowany wokół modelu”, czyli kernele Metal pod konkretne kształty, drafter DFlash 2 wytrenowany dla danego modelu i plan pamięci. Bez generycznej ścieżki i bez fallbacku. Obsługiwane: Qwen3.8-27B, Qwen3.6-35B-A3B oraz Qwen3.8-Flash-Next w `ISTA-DASLab/...-GSQ-RCO-GGUF:Q2_0`. **To łączy Splash z GSQ-RCO** (patrz R57 o GSQ-RCO).
2. **Liczby Splash (M5 Pro 48 GB, pomiar producenta):** Qwen3.8-27B UD-Q4_K_M dekoduje 74 t/s, a llama.cpp 16 t/s i llama.cpp+MTP 27 t/s na tym samym Macu. Przy kontekście 32K jest to 54 t/s. Zgodność następnego tokenu z llama.cpp: 99.30–99.45%. Na M3 Max 40c: 92 t/s. Nasze XTX ma około 79–104 t/s przy ~960 GB/s. Mac M5 Pro ma ~307 GB/s `[niezweryfikowane: przepustowość wg specyfikacji Apple]`, więc 74 t/s oznacza AL ×~3+ przy bardzo krótkim kroku.
3. **DFlash 2 = DFlash + dwie tanie poprawki.**
   - (a) **Selektor ścieżki:** top-16 kandydatów na pozycję. Każda para sąsiadów dostaje wynik `U_t(b) + ⟨A(a)⊙H(h_t), B(b)⟩`: niskorzędowa (rank 256) dwuliniowa uwaga po kandydatach, +2.0M parametrów, +0.6% latencji.
   - (b) **Dwukranowa dynamiczna konwolucja** depthwise przed i po każdej podwarstwie: +16.5M (+3%), +0.7% latencji. Rozwiązuje „suffix decay”.
   - Na Qwen3.8-27B (H200, T=1, blok 8) średnie AL wynosi MTP 4.28, DSpark 3.62, DFlash2 4.80.
4. **Nasz fork topka już ma DFlash i DFlash2** (`--spec-type draft-dflash`, arch `dflash`, odczyt `selector_top_k`/`conv_kernel_size`, `src/models/dflash.cpp`), a ścieżka działa na ROCm. Pomiary z 2026-10-09/10 na XTX: 111–116 t/s EN przy T=0. **Brakuje jednego: nasz selektor jest wyłącznie zachłanny (argmax po `scores`, `common/speculative.cpp:1298-1324`).** Blog opisuje próbkowanie ścieżki z tych samych wyników i rejection sampling dla T>0. U nas przy T=1 DFlash przegrywa z MTP (71.9 vs 81.1 t/s, 10-10). To jest najtańszy realny zysk.
5. **Drafter OrcaCyber `...-DFlash2-Q8_0.gguf` (2.06 GB) to drafter DFlash2 w tym samym formacie co incoai** (`general.architecture=dflash`, klucze `dflash.selector_top_k`, `dflash.conv_kernel_size`, `dflash.selector_rank`, `dflash.block_size`). Rozmiar zgadza się co do bajta z Q8_0 Qwen3.8-DFlash2 u Magnitude (2.06 GB). To, czy został dotrenowany na danych Orca, a nie jest przemianowanym draftem incoai lub z-lab dla Qwen3.5, jest `[niezweryfikowane]`: karta HF tego nie mówi.

## 1. Co to jest

- **Splash**: lokalny serwer LLM na Maca (`brew install incoai/tap/splash`, `splash serve --model unsloth/Qwen3.8-27B-GGUF:UD-Q4_K_M`). Udostępnia API OpenAI (Chat, Responses, Completions) i Anthropic Messages, ma narzędzia, JSON Schema, wizję i PDF. Do tego wbudowany czat i launchery agentów (`splash opencode|claude|codex|hermes|pi`). Integracja z LM Studio Bionic jako runtime.
- **DFlash 2**: równoległy drafter blokowy (block diffusion), następca DFlash. Wydany 2026-08-18 z drafterami dla Qwen3.8-27B i Muse Glimmer 30B. Później doszedł `incoai/Qwen3.6-35B-A3B-DFlash2` (aktywność na HF ~10-10).
- W Splash spekulacja **nie jest opcją, tylko ścieżką dekodowania**: każdy model ma swój drafter.

## 2. Kto / skąd

- **Inco AI** (inco.ai): ten sam zespół co DFlash (z-lab; checkpointy lustrzane `z-lab/*`). Na HF wydania publikuje `zhijianliu`, czyli najpewniej Zhijian Liu `[niezweryfikowane: tożsamość z nicka]`. Firma twierdzi, że jest „najszybszym dostawcą na Artificial Analysis dla 5 otwartych modeli”.
- Repo: [github.com/incoai/splash](https://github.com/incoai/splash): C++ 4.7 MB, Python 3.0 MB, ObjC++ 2.3 MB, Metal 0.44 MB; ~1.66k gwiazdek; HEAD `1482f6b` (2026-10-20).
- Kernele GGUF zawierają kod llama.cpp na licencji MIT (THIRD_PARTY_NOTICES).

## 3. Jak działa technicznie

### 3.1 Splash (wg bloga i README; kodu nie budowałem, to Metal)
- **Kernele pod kształt i pod obciążenie:** osobne kernele matmul 4-bit i atencji dla prefillu (duże batche) oraz dla weryfikacji draftu (małe bloki). Pisane i strojone przez „wewnętrzne agenty kernelowe” i dostarczane prekompilowane z presetami per rodzina GPU, liczba rdzeni i obciążenie.
- **Konwersja wag do layoutu kerneli przy ładowaniu**, bez kopii na dysku. Wejście to zwykły GGUF (Unsloth UD 1–8 bit, NVFP4) albo MLX.
- **Dekodowanie KV 8-bit (INT8 domyślnie) czytane bezpośrednio, z reużyciem między głowicami zapytań i tokenami weryfikacji.** Stan GDN domyślnie FP32 (`--state-format bf16` daje połowę rozmiaru).
- **Prefill GDN trzyma stan rekurencyjny w pamięci on-chip.**
- **Prefill 27B częściowo na ANE (Neural Engine)**, wyłączany `--disable-ane`.
- **Cały krok dekodowania jako jedna jednostka:** draft, weryfikacja, akceptacja i aktualizacja stanu są wysyłane razem (gdy brak schematu JSON). To odpowiednik naszego PM4 graph replay plus spekulacji w grafie.
- **Spekulacja wewnątrz batcha:** każde żądanie ma własny stan draftera. Agregat przy 4 równoległych: 170 t/s na 27B (3.9× vs następny silnik).
- **Prefix cache paged + snapshot stanu GDN na granicach prefiksu**, więc cache obejmuje też warstwy rekurencyjne. Wynik: TTFT 282 ms przy 32K na 27B (7.3× vs oMLX). Do tego cache SSD (`--max-cache-disk`, `--persistent-cache`).
- **Drafter ma SWA**, a przy długim prefillu liczony jest tylko potrzebny stan draftera, więc pamięć draftera jest ograniczona.
- Budżet pamięci 27B: 15 GiB wag + 1.2 GiB draftera przed KV.

### 3.2 DFlash 2 (blog 2026-08-18)
- **Obserwacja:** w DFlash (Qwen3-4B, GSM8K) Recall@1 na pozycji 0 to 85.4%, a Recall@16 to 99.5%. Wyrocznia wybierająca z top-16 dałaby AL 6.79 zamiast 4.27, więc cały zapas siedzi w selekcji.
- **Selektor:** top-16 na pozycję i wynik każdej sąsiedniej pary. Wszystko liczone równolegle w jednym przebiegu, bez dodatkowego przebiegu backbone'u ani LM-head. Sekwencyjne jest tylko przejście po gotowych wynikach:
  - greedy wybiera najlepszego następnika;
  - **próbkowanie losuje z tych samych wyników, a rejection sampling przywraca dokładny rozkład celu.**
- **Ablacja selektora** (Qwen3-4B, GSM8K): DFlash 4.27/3.78 (T=0/T=1) → +selektor 4.61/4.25. DSpark daje 4.49/4.08 przy +77.8M parametrów i +9.6% latencji.
- **Suffix decay:** udział atencji wewnątrz bloku spada z 30% (L1) do 8% (L5). Konwolucja `Conv_k(x)_t = k_{t,0}⊙x_t + k_{t,1}⊙x_{t-1}`: współczynnik to bazowy kernel plus korekta z ukrytego stanu, jedna korekta na 16 kanałów. Pozycja 0 czyta reprezentację ostatniego zweryfikowanego tokenu. 5L+conv zbliża się do 15L DFlash.
- **Łącznie +1.3% latencji cyklu.** Qwen3.5-4B (T=1, thinking): średnie AL MTP 4.54, DFlash 4.92, DSpark 5.49, DFlash2 5.97. Akceptacja warunkowa na MATH-500 utrzymuje ~86% do pozycji 14.
- **Trening draftera:** blog nie podaje przepisu (danych, kroków). Z naszej bazy (Magnitude, R16i): DFlash był trenowany na ~800K próbek Nemotron v2 + CodeAlpaca, ≤3072 tokenów, bez języka polskiego. Inco oferuje trening drafterów „dla Twoich fine-tune'ów” komercyjnie (kontakt e-mailowy z bloga).

### 3.3 Wersje
| | DFlash | DFlash 2 |
|---|---|---|
| Wydanie | 2026-01, arXiv 2602.06036 | 2026-08-18, blog (bez arXiv) |
| Wybór tokenu | argmax niezależnie na pozycję | top-16 + selektor par (rank 256) |
| Backbone | 5 warstw | 5 warstw + conv 2-tap przed/po podwarstwie |
| GGUF | `dflash` | ten sam arch + `dflash.selector_*`, `dflash.conv_*` |
| Silniki | SGLang, vLLM, TRT-LLM, llama.cpp | SGLang, vLLM (PR 52816), llama.cpp `--spec-type draft-dflash`, Ollama PR 17865, fork oMLX, Splash |

## 4. Liczby

| Co | Wartość | Sprzęt / źródło |
|---|---|---|
| Splash 27B decode, krótki prompt / 8K / 16K / 32K | 74 / 55 / 55 / 54 t/s | M5 Pro 16c GPU 48 GB, SPEED-Bench kod, reasoning medium; blog |
| oMLX / Ollama / uzu, 27B, krótki prompt | 38 / 24 / 19 t/s | jw. |
| llama.cpp / +MTP / Splash, 27B UD-Q4_K_M | 16 / 27 / 74 t/s (M5 Pro 20c); 17 / 20 / 92 (M3 Max 40c) | README |
| Splash 35B-A3B decode | 210 t/s (krótki), 143 (32K) | M5 Pro 48 GB |
| Splash 27B prefill 32K | 363 t/s; TTFT z cache 32K: 282 ms | M5 Pro |
| Agregat 4 równoległe 27B | 170 t/s | M5 Pro |
| Qwen3.8-Flash-Next GSQ-RCO Q2_0 | 95 t/s decode (1.3× vs Strata), prefill 32K 1312 t/s | M5 Pro 20c 64 GB |
| Zgodność next-token Splash vs llama.cpp | 99.30–99.45% (27B), 97.83–98.14% (35B) | BF16 KV, bez ANE |
| DFlash2 AL Qwen3.8-27B | GSM8K 5.46, MATH 5.28, HumanEval 4.39, MBPP 4.79, MT-Bench 4.10 (MTP: 5.02 / 4.72 / 3.91 / 3.99 / 3.74) | H200 SGLang, T=1, blok 8, xhigh |
| DFlash2 throughput c=1 GSM8K | 236.1 t/s (3.43× AR; MTP 178.5) | H200 |
| **U nas (XTX, topka)** | DFlash2 n=6 111–116 t/s EN T=0; po polsku 65 (MTP 78); T=1 mediana 71.9 vs MTP 81.1 | wiki [[drafter-dflash]], 10-09/10-10 |

Uwaga: wszystkie liczby Splash pochodzą od producenta. Porównanie z llama.cpp na Metalu (16 t/s dla 27B Q4 na M5 Pro) wygląda podejrzanie nisko, bo przy ~300 GB/s i ~16 GB wag sufit wynosi około 19 t/s, więc 16 jest wiarygodne. 74 t/s wymaga więc AL ≈ 4–5 przy kroku ≈ 1.1× tokenu AR `[INFERENCE]`.

## 5. Licencja / dostępność

- Splash: Apache-2.0, kod otwarty. Binarka przez Homebrew, kernele prekompilowane. **Tylko Apple silicon.** Na Linuksie/ROCm nie uruchomimy.
- Drafter `incoai/Qwen3.8-27B-DFlash2`: Apache-2.0 (safetensors). GGUF: `incoai/Qwen3.8-27B-DFlash2-GGUF` (Q4_K_M i inne; mamy Q4_K_M 1.06 GiB).
- DFlash 2 nie ma artykułu na arXiv, jest tylko blog. Kod treningowy: repo `z-lab/dflash`, śledzone w CompWatch od dawna. Dostępność kodu treningowego DFlash 2 jest `[niezweryfikowane]`.

## 6. Co z tego dla nas

Ranking (zysk, koszt):

1. **Próbkowana ścieżka selektora + rejection sampling dla DFlash2 przy T>0 w topka** (`common/speculative.cpp:1298-1324`, dziś `max_element`).
   - Blog (Qwen3-4B) pokazuje, że selektor daje przy T=1 więcej (+0.47) niż przy T=0 (+0.34), ale tylko przy próbkowaniu z wyników i rejection.
   - U nas T=1 DFlash ma 71.9 t/s, a MTP 81.1. Wcześniejszy szacunek z drafters.md to +20–24% na EN czacie przy T=1, ~40 linii.
   - **Zysk:** +10–20% t/s przy T=1 na EN/kodzie `[INFERENCE]`. Na PL prozie drafter i tak przegrywa (brak polskiego w treningu).
   - **Koszt:** ~1 dzień (CPU + jeden pomiar XTX); ROCm nic nie zmienia, bo to kod hosta.
2. **Router MTP↔DFlash per prompt lub język** (PL proza → MTP, EN kod → DFlash2). Przy T=0 na EN kodzie DFlash2 wygrywa (90.6 vs 86.3 mediana), na PL przegrywa. **Zysk:** +5–10% na mieszanym ruchu `[INFERENCE]`. **Koszt:** średni (dwa drafty w pamięci: +1.06 GiB przy Q4_K_M; na 24 GB jest ciasno przy dużym kontekście).
3. **Snapshot stanu GDN na granicach prefiksu dla prefix cache** (Splash: TTFT 32K 282 ms).
   - Sprawdzić, czy nasz `--cache-reuse` i checkpointy kontekstu w llama-server obejmują GDN przy wielokrotnych turach agenta. llama.cpp ma checkpointy stanu rekurencyjnego (`--ctx-checkpoints`) `[niezweryfikowane dla naszej gałęzi]`.
   - **Zysk:** TTFT kolejnej tury agentowej, nie t/s. **Koszt:** niski (pomiar).
4. **Drafter OrcaCyber DFlash2-Q8_0 na XTX:** od razu wspierany (`--spec-type draft-dflash -md ... --spec-draft-n-max 7`; u nas lepiej n=6). Q8_0 (2.06 GB) to +1 GB względem Q4_K_M. Na 24 GB z modelem Mix-15.7G i KV q4_0 mieści się przy ~32K `[INFERENCE]`. Warto zmierzyć AL Orca+DFlash2-Q8 vs Orca+MTP na zestawie kod/cyber. Koszt 30 min XTX.
5. **3090 (CUDA):** ta sama ścieżka `draft-dflash` jest w upstream llama.cpp. Magnitude zmierzył, że DFlash2 na 3090 bije MTP na pl-kodzie (109.2 vs 79.3), a przegrywa na pl-prozie. Brak nowej pracy, tylko dodać DFlash2 do macierzy testu 3090.
6. **Kernele weryfikacji pod mały blok (osobne od prefillu i od n=1):** w Splash to osobna rodzina. U nas MMVQ działa dla n=1, a weryfikacja bloku 7–8 idzie przez MMVQ batched lub MMQ. Do sprawdzenia w R50/R51, czy ścieżka ne=8 jest optymalna. Zysk nieznany, koszt wysoki.
- **Nie dotyczy:** Metal, ANE, Homebrew, konwersja layoutu przy ładowaniu (u nas repack w ggml już istnieje).

### Czy topka obsługuje DFlash na ROCm?
Tak. `git -C ~/wt/topka-int grep -i dflash` zwraca `common/arg.cpp` (`COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH`, autopobieranie sidecara DFlash z HF, priorytet DSpark > DFlash), `common/speculative.cpp` (selektor DFlash2 `selector_top_k`, `is_dflash2`), `src/models/dflash.cpp` (hparams `block_size`, `conv_kernel_size`, `conv_group_size`, `selector_rank`, `selector_top_k`, `target_layers`), `convert_hf_to_gguf.py` i `gguf-py`. Brak kodu specyficznego dla backendu (zero trafień w `ggml/src/ggml-cuda`), więc działa wszędzie tam, gdzie działają standardowe opy. Na XTX było mierzone 10-09/10-10.

## 7. Do bazy wiedzy

- Splash (incoai/splash `1482f6b`, Apache-2.0) to silnik tylko na Apple silicon od zespołu DFlash. Zasada: kernele, drafter i plan pamięci per model. Qwen3.8-27B Q4 na M5 Pro: 74 t/s (llama.cpp 16, +MTP 27).
- DFlash 2 = top-16 kandydatów + selektor par rank-256 (+2M parametrów, +0.6%) + 2-tap dynamic conv (+16.5M, +0.7%). Qwen3.8-27B AL średnio 4.80 vs MTP 4.28 (H200, T=1, blok 8).
- Selektor DFlash2 w topka jest tylko zachłanny (`speculative.cpp:1298-1324`). Brakuje próbkowania ścieżki i rejection, a to tłumaczy przegraną z MTP przy T=1.
- Drafter OrcaCyber DFlash2-Q8_0 ma pełne metadane DFlash2 (selector, conv). To, czy był trenowany na danych Orca, jest niezweryfikowane.
- Splash robi snapshot stanu GDN na granicach prefiksu: TTFT z cache przy 32K wynosi 282 ms na 27B.
- Splash serwuje `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF:Q2_0`: 95 t/s, 1.3× vs Strata na M5 Pro.
- CompWatch: dodano `incoai/splash` (tier B).

## 8. Źródła

- https://github.com/incoai/splash (README, `main` `1482f6b`)
- https://inco.ai/blog/splash/ (2026-09-17)
- https://inco.ai/blog/dflash2/ (2026-08-18)
- https://huggingface.co/incoai/Qwen3.8-27B-DFlash2
- https://huggingface.co/incoai/Qwen3.8-27B-Splash, https://huggingface.co/incoai/Qwen3.6-35B-A3B-Splash
- https://arxiv.org/abs/2602.06036 (DFlash)
- `~/models/orca-cyber-nano/README.md` + metadane GGUF `OrcaCyber-Nano-1.0-AI-Defense-DFlash2-Q8_0.gguf`
- `~/wt/topka-int` `cf927413b`: `common/speculative.cpp:1006-1057,1298-1324`, `src/models/dflash.cpp`
- wiki: [[drafter-dflash]], [[drafter-dspine]], R15b, R16i
