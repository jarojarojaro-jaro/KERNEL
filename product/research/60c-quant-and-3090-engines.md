# 60c. Kwanty i silniki 3090: Gyro-Coder, tqLLM 1.2, DCQ, posty @superalesha, Nemotron-3.5-Bolt-E4B

Data: 2026-10-24. Autor: podagent ResQuantEngines. Tylko CPU, bez GPU i bez pobierania wag.

Co przeczytałem:
- karty HF: Gyro-Coder, Gyro-GGUF, DCQ, YTan2000/Qwen3.8-Flash-Next-tqLLM, unsloth/nvidia Bolt-E4B (+ `config.json`), FastVideo FastH3 Omni, Qwen3.8-Flash-Next i Qwen3.8-27B (tabele benchmarków);
- tqllm.com (`/releases`, `/performance`);
- posty X przez `api.fxtwitter.com`: @superalesha 2113131231168831637 i cytowany 2111885825218838905, @fraserpricee 2112111199454454169;
- README `fraserprice/dspark-vllm`.

Co sklonowałem (`blob:none`) do `~/qwen-opt/research/`:
- `agention-gyro` (`587a526`, 2026-10-24);
- `tqllm` (`c2163c2`, tag v1.2.3);
- `agentionai-llama.cpp` (gałąź domyślna `release/gyro-l` = `9aa51ce`, 2026-10-12, bez checkoutu).

Kod i JSON-y wyników DCQ pobrałem do `~/qwen-opt/research/dcq/`: same pliki `.py` i `.json`, bez wag.

**Ten raport to delta.** Bazę już mamy:
- Gyro-S, Strata i Flash-Next: R21n, R32a §3, R57b;
- tqLLM 1.0 i rekord 273.1 t/s: R15c, R32f, [[tqllm]];
- HyperQwen: R15b, [[hyperqwen]];
- Nemotron 3.5 Bolt 74B: R14.

Tamtych wniosków tu nie powtarzam.

Oznaczenia: `[INFERENCE]` = mój szacunek; `[niezweryfikowane]` = nie dało się sprawdzić u źródła.

Nasze liczby odniesienia (XTX, Qwen3.8-27B UD-Q4_K_XL, topka, [[REKORDY]]):

| metryka | wynik |
|---|---|
| proza E0 | ~79 t/s |
| czat | 95–104 t/s |
| spec_sweep T=1 | 109.0 t/s |
| code-edit z lookupem | 400.9 t/s |
| tg128 bez spekulacji | 43.2 t/s |
| pp4096 | 1123 t/s |
| decode MTP przy 94k | 100.6 t/s |

Na 3090 (topka, chmura): czat T=1 **93.3 t/s**, code-edit 348.9 t/s.

## TL;DR

1. **Gyro-Coder to Qwen3.8-Flash-Next (125B MoE) przycięty do 256 z 512 ekspertów w każdej warstwie.** Eksperci są w trellisie TQ2_T (2.125 bpw), na GPU zajmuje 19.92 GiB. Do tego dochodzi **50.7 GiB tabeli n-gramów na NVMe**, więc plik ma 70.6 GiB.
   - Ekspertów wybrano przeszukiwaniem ewolucyjnym: ~2 200 kandydatów w 14 przebiegach.
   - Uruchamia go tylko fork agentionai/llama.cpp: obraz Docker z Vulkanem, na AMD przez `/dev/dri`. Stock llama.cpp, nasz fork i Strata 0.2.2 go nie załadują.
   - ROCm/HIP: kernele trellis są w `ggml-cuda` forka (`tq.cuh` z dp4a, instancje MMQ), ale ścieżka HIP nie jest nigdzie deklarowana ani mierzona `[niezweryfikowane]`.
   - **Nowość dnia:** 2026-10-24 opublikowano otwartą specyfikację formatu Gyro z referencyjnym enkoderem i dekoderem (Apache-2.0). Enkoder produkcyjny pozostaje zamknięty.
2. **Gyro-Coder vs nasz 27B w kodowaniu agentowym: bez rozstrzygnięcia, na XTX nie ma tu zysku.**
   - Pełny Flash-Next bije 27B na DeepSWE 1.1 (58.7 vs 42.2) i SWE-bench Multilingual (81.0 vs 73.8). SWE-bench Pro to remis (62.5 vs 61.7).
   - Przycięcie i 2 bity kosztują: KLD Python 0.165 / top-1 93.1% vs Q8_0 pełnego modelu, test zadań 13/16 (te same eksperty w 8 bitach 15/16).
   - Nasz U4 ma KLD 0.0117 vs BF16. Protokół inny, ale to rząd wielkości różnicy.
   - Bajty na token to ~5 GiB, czyli ~3× mniej niż 27B, więc teoretyczny sufit plain decode jest wysoki. Jedyny pomiar to Strix Halo (Vulkan, MTP): 11–22 t/s na strumień przy 2 strumieniach. Pomiaru na XTX nie ma.
3. **tqLLM 1.2.x to otwarty kod (Apache-2.0, tagi v1.2.0–v1.2.3), wyłącznie CUDA (+MLX), bez ROCm.** Flash-Next na jednej 3090: eksperci w RAM, cache „slotów” ekspertów w VRAM z prefetchem następnej warstwy, natywne MTP z adaptacyjną długością (≤ 5, stop przy p < 0.9), grafy CUDA współdzielone przez warstwy tego samego typu.
   - Wynik: 77.1 vs 47.2 t/s po 128K (vs Strata 0.2.2). W 1.2.3 czat 96–103 t/s, to **nasz poziom czatu 27B na XTX, ale modelem 125B**.
   - **„+32 GB RAM” z posta jest sprzeczne z kartą:** wymagane ≥ 64 GB, a pomiary zrobiono na 128 GB.
4. **DCQ to sensowny pomysł z dowodem bliskim zeru.** Uczone zaokrąglanie STE + **błąd końcowego stanu GDN w funkcji straty** + kotwica do oryginalnych wag + bity per rola tensora.
   - Ewaluacja: n=20 na zadanie, a JSON-y z repo przeczą tabeli z karty: GPTQ W4 w JSON ma 0.80/0.85, czyli tyle co DCQ W4, a nie 0.75/0.80.
   - Wynik „AWQ W4 0.00” to zepsuty przebieg: 40/40 odpowiedzi ucięte limitem tokenów, a plik jest bajtowo identyczny z wynikiem `learned_w2`.
   - BF16 AIME 0.20 nie ma pokrycia: plik pokazuje n=2 i 0/2.
   - **Przenośny wniosek:** `in_proj_qkv` w GDN (u nas `attn_qkv`) niszczy stan rekurencyjny 25× bardziej niż wyjście warstwy. To sygnał dla naszej alokacji z 57g.
5. **@superalesha:**
   - „4.6×” to 82 → 382 t/s na zadaniu cytowania dokumentu 25K. Liczby pochodzą z posta r/LocalLLaMA, z dużym prawdopodobieństwem HyperQwen (vLLM). Sam autor pisze: „in normal chat he gets about 133 tok/s… 1.6×”. Nasza 3090 robi code-edit 348.9 t/s i czat 93.3 (T=1).
   - „574 tok/s DeepSeek V4.1 Flash” to 4× RTX Pro 6000 Max-Q (384 GB VRAM). Własny post Frasera mówi „500TPS+, megakernel WIP”, a 574 nie znalazłem u źródła `[niezweryfikowane]`.
   - FastH3 Omni to model wideo (MiniMax H3, 8 kroków), **nie dotyczy**.
6. **Nemotron-3.5-Bolt-E4B to model na telefon/edge, nie drafter dla nas.** Gemma-4-E4B (8B, w tym ~2.8B PLE, „4B effective”) po RL od NVIDIA, 42 warstwy, słownik 262 144 (Qwen ma 248 320), więc nie da się go podpiąć jako drafter Qwena. Ma własny drafter DFlash, a Q4_K_M zajmuje 6.18 GB.

## 1. Co to jest

| pozycja | czym jest | forma |
|---|---|---|
| Gyro-Coder | Qwen3.8-Flash-Next z 256/512 ekspertami w warstwie, eksperci w TQ2_T | GGUF z niestandardowymi typami (144), plik `…-Gyro-Coder-TQ2_0.gguf` (nazwa „TQ2_0” to tylko klasa rozmiaru) |
| Gyro-Coder-L | te same eksperty w „about 3.2 bits per weight” (typ nieopisany na karcie; najbliżej TQP6 3.125 bpw `[INFERENCE]`), dla 32 GB | 27.54 GiB GPU |
| agention-gyro | specyfikacja formatu Gyro TQ (TQK4–7, TQ2_T, TQP5–7) + obrót block-Hadamard, referencyjny dekoder/enkoder C, dekoder Python | repo GitLab, Apache-2.0 |
| tqLLM 1.2.x | własny silnik C++/CUDA (turbo-tan) z obsługą Flash-Next (`qwen4exp`) i MoE z RAM | GitHub, Docker `ytan2000/tqllm:1.2.3` |
| DCQ | metoda PTQ dla hybryd GDN (Qwen3.5-arch), demonstrowana na MiMo-V2.6-Distill-Qwen-9B | HF: wagi W4 (GPTQ v1) i W3mix (własny format) + `tools/` |
| posty @superalesha | przegląd cudzych wyników („this is software”) | X |
| Nemotron-3.5-Bolt-E4B | SLM NVIDIA na bazie Gemma-4-E4B-it, RL (GRPO) pod narzędzia, rozmowę i instrukcje | GGUF NVIDIA/unsloth, DFlash drafter |

## 2. Kto / skąd

- **Gyro / AgentionAI:** jednoosobowy zespół, Laurent Zuijdwijk (`agention-gyro` README: „copyright AgentionAI (Laurent Zuijdwijk)”). Sprzęt dostarcza AMD: „Built and tested on AMD Ryzen AI Max (Strix Halo). Hardware supported by AMD”. Kod trellis w strix-llama.cpp PR #195 jest tego samego autora (R32a).
- **tqLLM:** turbo-tan / YTan2000. Wszystkie commity 1.2.x (2026-10-22) mają autora `turbo-tan`. Repo `turbo-tan/tqllm`, licencja Apache-2.0 (`LICENSE`).
- **DCQ:** HF `Akahsizrr`: 0 pobrań, 1 polubienie. Ścieżki w kodzie (`/home/riftuser/...`) i dopisek „no compile toolchain on this pod” wskazują na jednoosobowy eksperyment na wynajętym L40S. Artykułu nie ma.
- **@superalesha:** Alexey Fateev („how far can 4x RTX 3090s go?”, GitHub `alesha-pro`). Agreguje cudze wyniki.
- **@fraserpricee:** Fraser Price, autor `fraserprice/dspark-vllm` (overlay vLLM z DSpark dla DeepSeek-V4-Flash na RTX Pro 6000, Apache-2.0).
- **FastH3 Omni:** FastVideo (Hao AI Lab, UCSD) z Nuva Lab, destylat MiniMax H3.
- **Bolt-E4B:** NVIDIA. Wydanie na HF 2026-10-23, licencja OpenMDW-1.1 (baza Gemma 4 na Apache-2.0).

## 3. Jak działa technicznie

### 3.1 Gyro-Coder i format Gyro

**Przycinanie ekspertów (karta):**
- najpierw „mapping which experts carry which domains”;
- potem przeszukiwanie ewolucyjne: ~2 200 zestawów w 14 przebiegach, przestrzeń 10⁷³²⁸ kombinacji;
- najlepsze zestawy zbudowano jako pełne modele i przepuszczono przez testy kodu, pętli i wiedzy.

Kryterium selekcji ani danych kalibracyjnych nie opublikowano. Router po przycięciu: nie podano, czy jest renormalizowany ani czy wybiera top-10 z 256 `[niezweryfikowane]`.

**Format** (`agention-gyro/README.md`, `SPEC.md`):
- bloki po 128 wag: skala fp16 + strumień bitów tail-biting bitshift trellis (K nowych bitów na krok, 15 bitów stanu);
- TQ2_T/TQK: 32 kroki po 4 wagi, stan → 2 punkty z ustalonego kodebooka 2048×2 przez hash multiplikatywny (`x = (s & 0x7FFF) * 0x9E3779B1`);
- TQP: 64 kroki po 2 wagi;
- każdy ciąg bajtów jest poprawnym blokiem;
- typy: TQK4 151 (1.125 bpw), TQK5 150 (1.375), TQK6 145 (1.625), TQK7 146 (1.875), **TQ2_T 144 (2.125)**, TQP5–7 147–149 (2.625/3.125/3.625);
- obrót: `T w = H_b (s ⊙ w)` na wybranych macierzach (`prism.hadamard.weight_names`). Runtime obraca wejście matmula albo odkręca wagi przy ładowaniu.

**Alokacja Gyro-Coder** (z tabeli tensorów Gyro-M, R21n-notatki `gguf-M-TQ2_0.txt`, ten sam typ ekspertów):
- eksperci gate/up/down w TQ2_T;
- cała reszta w Q8_0: `attn_qkv` 0.934 GiB, `output` 0.629, `attn_gate`/`ssm_out` po 0.560, hiper-połączenia 4×0.156, shared expert;
- router w F32;
- PLE/n-gram `per_layer_token_embd` [160 × 320 001 536] w Q8_0 = 50.66 GiB, czytany wierszami z dysku (`--ngram-on-disk`).

Arytmetyka: eksperci 256 × 48 × 3 × (2560×640) × 2.125/8 B = 14.9 GiB, a 19.92 − 14.9 ≈ 5.0 GiB to części gęste. Zgadza się z kartą („65B parameters on the GPU”).

**Bajty na token (dekod, 1 sekwencja)** `[INFERENCE]`:
- części gęste czytane w każdym kroku ~4.3 GiB;
- 10 aktywnych ekspertów × 48 warstw × 3 × 1.64M × 0.2656 B ≈ 0.58 GiB;
- razem **~4.9 GiB/token**, wobec ~16.5 GB dla naszego 27B U4.

Przy MTP weryfikacja k tokenów trafia w różne eksperty, więc bajty rosną z k szybciej niż u modelu gęstego.

**Silnik:**
- fork `gitlab.com/agentionai-group/llama.cpp` (`9aa51ce`, 2026-10-12);
- `ggml/src/ggml-cuda/tq.cuh` (296 linii, ścieżka int8-kodebook + `ggml_cuda_dp4a`), `mmq-instance-tq2_t/tqk6/tqk7/tqp5-7.cu`, shadery Vulkan `dequant_tq2_t.comp` i `tq2_t_lut.glsl`;
- karta podaje tylko Docker Vulkan (`agentionai/agention-llama:server`), na AMD przez `/dev/dri`;
- w drzewie nie ma żadnych `#if` HIP/RDNA w `tq.cuh`. Kompilacja pod HIP jest prawdopodobna (dp4a mapuje się na `sdot4`), ale nikt jej nie deklaruje `[niezweryfikowane]`.

Gałąź `feat/deepseek41-tqk45` wskazuje, że TQK4/5 powstały pod DeepSeek V4.1 `[INFERENCE z nazwy]`.

**Referencyjny enkoder:** tail-biting Viterbi po siatce skal, opcjonalnie ważony imatrixem, plus refit skali. Ograniczenia:
- jednowątkowy, ~25 ms (TQ2_T/TQK) do 50 ms (TQP) na blok 128 wag;
- README sam ostrzega: „noticeably worse than AgentionAI's published Gyro quants… not a production quantizer”.

Self-test na N(0,1): TQ2_T RMSE 0.2612 przy granicy D(R) 0.2293.

### 3.2 tqLLM 1.2.0–1.2.3 (`CHANGELOG.md`, tqllm.com)

**Flash-Next na 24 GB:**
- routowani eksperci w RAM (`--moe-host-mb auto`);
- „expert slot tiers”: banki slotów w VRAM współdzielone między warstwami i dopasowane do wolnej pamięci (144 → 157 slotów na warstwę na 3090). Długi prompt pożycza banki na swój stan, minimum to 64 sloty;
- chybienia lecą przez PCIe silnikiem kopiującym, eksperci następnej warstwy są pobierani w trakcie bieżącej;
- efekt slotów: czat 94.2 → 100.4 t/s, po 32K 67.3 → 71.2, po 64K 63.3 → 69.3.

**MTP Flash-Next:**
- adaptacyjna długość draftu do 5, stop gdy top-p draftu < 0.9 (`TQFN_DRAFT_TAU`);
- greedy daje to samo wyjście co stały draft 3;
- zysk: 3090 czat +1.5%, po 32K +3%; GB10 +4.4%.

**Pozostałe zmiany 1.2.0:**
- **grafy CUDA:** część uwagi każdej warstwy odtwarzana z grafu współdzielonego przez warstwy tego samego rodzaju; czat 92.1 → 94.1 t/s;
- **prefill:** top-k QSA na bitach 32-bitowych, reguła areny scratch (16K chunków przy 245K), MTP catch-up liczący tylko K/V warstwy MTP;
- **MTP na MoE z blokiem MTP** (Qwen3.6-35B-A3B UD-Q4_K_XL): 3090 177.5–182.8 → **246.2–329.6 t/s**, wyjście identyczne;
- **cache ekspertów hosta w VRAM** w grafie (`--moe-cache-mb`): MiniCPM-V 4.7 Q5_K_M przy 16 GB 71.9/112.5/54.9 → 96.2/146.3/85.9 t/s vs llama.cpp `-ncmoe 19` 62.6/62.8/62.8;
- **`tools/rc_gate.py`:** bramka RC z identycznym tekstem greedy, limitem utraty dekodu i `--np N` = `--np 1`.

**1.2.1–1.2.3:**
- 1.2.1: eksperci układani w RAM z publicznego GGUF ISTA IQ3_S przy starcie (~50 s), bez pliku „pack” 51 GB;
- 1.2.3: **przyczyną spadku 15% było niecache'owane osadzenie per warstwa (28.8 GB czytane wiersz po wierszu w każdym tokenie)**. Po wczytaniu raz przy starcie (~6 s) czat wrócił do 96–103 t/s, a TTFT 32K spadło z 17.3 do 14.6 s.

### 3.3 DCQ (`tools/quant_learned.py`, `sens_probe.py`, karta)

- **Algorytm:** PTQ warstwa po warstwie, STE na wagach przed zaokrągleniem i log-skalach grup (Adam: weight lr 1e-4, scale lr 0.025, 60 kroków), g=128 symetrycznie.
- **Strata:** `rel_mse(wyjście_warstwy) + 0.25 · rel_mse(końcowy stan GDN)` plus kotwica „trust region” (waga 1.0) do oryginalnych wag. Stan przechwytuje wrapper na `torch_chunk_gated_delta_rule(output_final_state=True)`.
- **Bity per rola** z `sens_probe.py`: `in_proj_qkv` → 4 bity, `in_proj_a/b` → bf16, reszta 3 bity (W3mix).
- **Kalibracja:** WikiText-2, 8 okien × 512 tokenów = **4 096 tokenów**. To bardzo mało: ISTA używa 1000 × 4096.
- **Niespójność:** docstring opisuje closed-loop, ale karta mówi „`closed_loop: false`” dla wydanych plików.
- **Mapa wrażliwości** (`results/sens_table.json`, średnia po 24 warstwach GDN, rel. MSE wyjścia / stanu):

| rola | 4 bit | 3 bit | 2 bit |
|---|---|---|---|
| `in_proj_qkv` | 0.0008 / **0.0198** | 0.0034 / **0.0855** | 0.0170 / **0.5466** |
| `in_proj_b` | 0.0000 / 0.0015 | 0.0002 / 0.0075 | 0.0013 / 0.0690 |
| `in_proj_a` | 0.0000 / 0.0022 | 0.0001 / 0.0104 | 0.0003 / 0.0382 |
| `in_proj_z`, `out_proj` | ≤ 0.0007 / 0 | ≤ 0.0035 / 0 | ≤ 0.0222 / 0 |

### 3.4 Claimy @superalesha (posty pierwotne)

- **2111885825218838905 (10-18):** „A guy on r/LocalLLaMA started at 82 tok/s. He tuned MTP, added a DFlash2 drafter and a lookup drafter, and pushed verify to 16 tokens per step. 382 tok/s on a task that quotes a 25K token document. To be fair, the 4.6x is on that quoting task. In normal chat he gets about 133 tok/s… context went up to 138K.”
  - Mechanizm (blok 16, lookup sufiksu wypełnia pozycje 8–15 za DFlash2) i liczby (381 t/s, 25k dokument) pasują do HyperQwen (R15b: 14.97 tok/krok przy 39.3 ms/krok). Repo nie jest nazwane w poście `[INFERENCE]`.
- **2113131231168831637 (10-22):**
  - „1 Linux kernel module unlocked full-speed BF16 tensor math, 82 to 155 TFLOPS… Real prefill in Strata got +10 to 12%”. To osobny temat, pokrywa go raport peera ResGpuUnlock.
  - „DeepSeek V4.1 Flash 1017 at home: @fraserpricee runs it at 574 tok/s, 2x faster than DeepSeek's own API”.
  - „FastH3 Omni does it in 8 steps instead of 25. On an RTX 5090 a 5 second clip went from 555 seconds to 115.”
- **Fraser Price 2112111199454454169 (10-19):** „Local DeepSeek-4.1-Flash-1017 @ 500TPS+. 4 x RTX Pro 6000 Max-Q, full precision, standard coding prompt, 5 DSpark tokens, full SSD ngram offload. Still WIP, recipe incoming… THE MACHINE YEARNS FOR 600”. Liczby 574 w poście źródłowym, który przeczytałem, nie ma. Megakernela ani przepisu nie opublikowano.
- **FastH3 Omni:** karta FastVideo podaje „eight transformer evaluations, guidance 1.0”, NVFP4 QAD wyłącznie na Blackwell. Inne źródła piszą, że baza H3 ma 50 kroków, post mówi 25. Czasy 555 → 115 s znam tylko z posta `[niezweryfikowane]`.

### 3.5 Nemotron-3.5-Bolt-E4B (`config.json` BF16, karta)

- `Gemma4ForConditionalGeneration`: 42 warstwy, hidden 2560, 8 głów Q / 2 KV, head_dim 256, FFN 10240, okno przesuwne 512 (co szósta warstwa pełna), 18 warstw dzieli KV, PLE 256 na warstwę.
- Słownik: 262 144 (osadzenia PLE 262 144 × 42 × 256 ≈ 2.8B parametrów, stąd „8B (4B effective)”); kontekst 64K; softcap logitów 30.
- Trening: RL (GRPO, NeMo RL/Gym) na Gemma-4-E4B-it. Karta podaje wejście tekstowe; post Unsloth wspomina wizję.
- Spekulacja: osobny `NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-DFlash` (`Nemotron-3.5-Bolt-E4B-DFlash-BF16.gguf`), uruchamiany w stock llama.cpp b11459 (`--spec-type draft-dflash --spec-draft-n-max 7`).

## 4. Liczby (z warunkami pomiaru)

| co | wynik | sprzęt / warunki | źródło |
|---|---|---|---|
| Gyro-Coder KLD / top-1 vs pełny model Q8_0 | C++ 0.118 / 94.5%; web 0.142 / 92.5%; SQL 0.145 / 92.7%; **Python 0.165 / 93.1%**; Rust 0.223 / 88.7%; shell 0.417 / 80.9%; wiedza 0.301 / 80.8%; held-out 0.579 / 70.8% | `-c 2048`, ref Q8_0 512 ekspertów | karta Gyro-Coder |
| Gyro-Coder-L (27.54 GiB) | C++ 0.077 / 95.5%; Python 0.132 / 94.0%; held-out 0.521 | jw. | jw. |
| dla skali: Gyro-M (512 eksp., 34.98 GiB) | held-out 0.291; code 0.066; IQ4_NL ggml-org 0.200 przy 68.2 GiB | held-out 2026 | karta Gyro-GGUF |
| zadania kodowe | Gyro-Coder 13/16; te same eksperty w 8 bitach 15/16; Gyro-Coder-L 15/16 | 8 zadań × 2 seedy, thinking, 64k | karta |
| pamięć | 19.92 GiB wag GPU; 21.1 GiB z 64k ctx (KV q8_0); na dysku 70.6 GiB | — | karta |
| prędkość Gyro-Coder | 11–22 t/s na strumień, 2 strumienie | Strix Halo, Vulkan, MTP | karta |
| pełny Flash-Next vs 27B (BF16) | DeepSWE 1.1 58.7 vs 42.2; SWE-bench Pro 62.5 vs 61.7; SWE-Multilingual 81.0 vs 73.8; LCB v6 91.9 vs 90.3 | Qwen, Claude Code / mini-SWE-agent, T=1 | karta Qwen3.8-Flash-Next |
| nasz 27B U4 KLD | 0.0117 (held-out, protokół agentionai, ref BF16); wiki 0.0153; PL 0.0073 | E1 | R32a, R16e |
| tqLLM Flash-Next vs Strata 0.2.2 | po 32K 76.4 vs 72.2; po 64K 85.1 vs 63.6; **po 128K 77.1 vs 47.2 t/s**; TTFT 32K 14.98 vs 15.14 s | 3090, ISTA IQ3_S, greedy, reasoning off, MTP `mtp-blk48-iq4` vs `--spec 4`, host 128 GB RAM | tqllm.com/performance, karta YTan2000 |
| tqLLM czat krótki | 91.6 vs 89.6 t/s; TTFT 0.32–0.41 vs 1.07–1.29 s; ciepły serwer 95.6; 1.2.3: 96–103 t/s | 5 × 512 tok., świeży serwer | jw., releases |
| tqLLM MTP na MoE | Qwen3.6-35B-A3B 177.5–182.8 → 246.2–329.6 t/s | 3090, UD-Q4_K_XL, 5 czatów | CHANGELOG 1.2.0 |
| tqLLM wymagania | ≥ 64 GB RAM (51 GB ekspertów), RTX 30+ / GB10 | — | karta YTan2000 |
| DCQ (n=20, thinking) | BF16 MMLU 0.90 / GSM8K 0.85; DCQ W4 0.80 / 0.85; DCQ W3mix 0.55 / 0.70; Paro W4 0.75 / 0.85; **GPTQ W4 wg JSON 0.80 / 0.85** (karta: 0.75 / 0.80); GPTQ W3 0.45 / 0.35; AWQ W4 0 / 0 (zepsuty przebieg) | L40S, gptqmodel / sglang | `results/*.json` |
| DCQ serwowanie | W3mix 7.50 GiB po załadowaniu, 8.35 GiB szczyt; ~16 t/s (referencyjne kernele GDN bez FLA) | L40S | karta |
| HyperQwen (cytowany) | 82 → 382 t/s (cytowanie 25K), czat ~133 t/s, ctx 138K | 3090 | post 2111885825218838905; R15b |
| nasza 3090 | czat T=1 93.3 t/s; code-edit mvs T=0 348.9 t/s | topka `cuda-topka2`, 335 W | R27 |
| DeepSeek V4.1 Flash, Fraser | 200 TPS (64 GB RAM, Engram na NVMe), 300+ TPS, **500+ TPS** (megakernel WIP) | 4× RTX Pro 6000 Max-Q, pełna precyzja, DSpark 5 | posty X (500+ przeczytany bezpośrednio; 200/300 z wyszukiwarki `[niezweryfikowane]`) |
| Bolt-E4B | Q4_K_M 6.18 GB; „~4 GB VRAM”; Tau2 55.10 (Qwen3.5-4B 75.06); BFCL-v3 68.51 (Qwen3.5-4B 70.95) | NVIDIA NeMo Gym, BF16 | karta |

## 5. Licencja / dostępność

| artefakt | licencja | uwagi |
|---|---|---|
| Gyro-Coder GGUF | „qwen-community-1.0” (`license: other`) | ładuje tylko fork agentionai; Strata „support is coming” |
| `agention-gyro` | Apache-2.0 + NOTICE (do 10-24 MIT) | spec + referencyjny enkoder; produkcyjny enkoder zamknięty |
| fork agentionai/llama.cpp | MIT (dziedziczy po llama.cpp) `[INFERENCE]` | ostatni commit gałęzi domyślnej 10-12 |
| tqLLM | Apache-2.0 | kod 1.2.3 publiczny; tylko CUDA i MLX (`src/backends/mlx`), brak ROCm |
| DCQ | Apache-2.0 | kod w repo HF; jedna architektura (Qwen3.5 w transformers), brak GGUF |
| dspark-vllm | Apache-2.0 | Blackwell sm_120 |
| FastH3 Omni | MiniMax-H3 Community License | NVFP4 tylko Blackwell |
| Bolt-E4B | OpenMDW-1.1 | „ready for commercial or non-commercial use” |

## 6. Co z tego dla nas

| # | pomysł | dotyczy | zysk `[INFERENCE]` | koszt | uwagi |
|---|---|---|---|---|---|
| 1 | **Alokacja 57g bez obniżania `attn_qkv` w warstwach GDN** (sygnał z DCQ: `in_proj_qkv` niszczy stan 25× bardziej niż wyjście). Plan 57g obniża 15–18 tensorów `attn_qkv` Q5_K → Q4_K/IQ4_XS. Dodać ramię „`attn_qkv` bez zmian”: ten sam cel −1.0 GB, oszczędność z FFN | XTX, 3090 | zachowanie +4…+5% t/s z 57g przy niższym KLD-PL; ramię kosztuje ~0.1 GB mniej oszczędności | +1 ramię w jobie 57g (~30 min GPU) | zablokowane jak 57g: potrzebny BF16 (zakaz pobierania) |
| 2 | **Bramka `--np N` = `--np 1`** (tqLLM `rc_gate.py`) dla topki: greedy md5 dla 1 i N slotów | XTX, 3090 | 0 t/s; łapie błędy batch-zależne w multi-slot (agent + czat) | ~15 min GPU, skrypt na CPU | nasze kernele wybierają ścieżkę po rozmiarze batcha, więc różnica jest możliwa, ale niekoniecznie jest błędem ([[batch-invariant]]) |
| 3 | **Próg na pozycję draftu MTP (τ=0.9)** jako ramię obok `LLAMA_DRAFT_CUMP` (58, `ds.jobs`) | XTX, 3090 | 0…+2% (tqLLM +1.5% czat, +3% po 32K na MoE). U nas `p_min` 0.3 było neutralne, 0.5 dało −7% (sweep 10-10) | 10 min GPU (ramię w kolejce) | niski priorytet; MoE zyskuje więcej, bo każdy draft dokłada ekspertów |
| 4 | **Lekcja PLE/n-gram z tqLLM 1.2.3:** tablice osadzeń czytane wierszami z mmap/dysku mają być w RAM (tqLLM: −15% dekodu, TTFT +18%) | Flash-Next / Gyro na XTX (jeśli kiedyś) | do +15% dla tej linii | 0 teraz | nasz box ma 62 GB DDR4, a tabela Gyro to 50.7 GiB, więc zmieści się na styk |
| 5 | Gyro-Coder na XTX do kodowania agentowego | XTX | **nieznany**: ~4.9 GiB/token to ~3× mniej bajtów niż 27B, ale brak silnika ROCm (tylko Vulkan Docker), kernele trellis są obliczeniowo cięższe, KLD ~10× gorsze od U4 | pobranie 70.6 GiB + 0.5 dnia | zablokowane pobraniem; kill: czat < 95 t/s albo mniej zadań zaliczonych niż 27B |
| 6 | MTP na MoE (Qwen3.6-35B-A3B): tqLLM ×1.4–1.8 | katalog 10–16 GB | duży dla katalogu, 0 dla 27B | — | nasze lokalne GGUF-y q36 nie mają bloku MTP (`qwen35moe.block_count` 40, 0 tensorów `nextn`; nagłówki sprawdzone na CPU) |
| 7 | Port Gyro / TQ2_T do topki | — | **nie dotyczy** przy 24 GB (U4 mieści się z KLD 0.0117). Referencyjny enkoder: ~25 ms/blok → 27B ≈ 210 M bloków ≈ 1 460 rdzeniogodzin i „noticeably worse” niż produkcyjny | — | wraca tylko dla tieru 12–16 GB, i to z produkcyjnym enkoderem |
| 8 | tqLLM jako silnik | 3090 | **nie dotyczy** XTX (brak ROCm). Na 3090 to konkurencja: Flash-Next 96–103 t/s ≈ nasz 27B 93.3 (T=1) przy innym modelu, T=0 i 128 GB RAM | — | dopisane do CompWatch (tqLLM już był, tier A) |
| 9 | DeepSeek V4.1 Flash 574/500+ t/s, megakernel | — | **nie dotyczy** (384 GB VRAM). Megakernele mamy w R15a i [[megakernele-prior-art]] | — | śledzić publikację megakernela (CompWatch: `fraserprice/dspark-vllm`) |
| 10 | FastH3 Omni | — | **nie dotyczy** (wideo, NVFP4 Blackwell) | — | — |
| 11 | Bolt-E4B jako drafter Qwen3.8-27B | — | **nie dotyczy**: inny słownik (262 144 vs 248 320). Do tego ~2.5–3 GB/token przy Q4 to ~15–20% kosztu kroku 27B, a nasze MTP jest prawie darmowe | — | kandydat do katalogu „6–8 GB / telefon” i konkurent LFM w małym tierze; nie dla XTX |

Kolejność: #1, gdy tylko 57g dostanie BF16. #2 tanio przy najbliższym oknie GPU. #3 dorzucić do `ds.jobs`. Reszta to wiedza albo tematy zablokowane pobraniem.

**Porównanie z naszym 27B na XTX (podsumowanie):**
- Prędkościowo nic z tej partii nie bije naszego czatu 95–104 t/s na XTX. Najbliżej jest tqLLM z Flash-Next na 3090 (96–103 t/s, T=0, 128 GB RAM), ale innym, większym modelem.
- „4.6×” na 3090 to zadanie cytowania. W tej klasie mamy na 3090 348.9 t/s (code-edit), a na XTX 400.9 t/s.
- Jakościowo Flash-Next ma przewagę w kodowaniu agentowym (DeepSWE +16.5 pkt), ale tylko jako pełny model. Gyro-Coder na 24 GB płaci za to KLD rzędu 0.12–0.17 na kodzie.

## 7. Do przetestowania

| test | cel | oczekiwany zysk | koszt | warunek |
|---|---|---|---|---|
| T1: ramię 57g „`attn_qkv` nietknięty” (KLD-PL, KLD-kod, t/s E0 i czat) | XTX, potem 3090 | KLD-PL ≥ 10% niższe niż plan 57g przy tym samym −1.0 GB; t/s +4…+5% vs U4 | ~30 min GPU + kwantyzacja na CPU | BF16 Qwen3.8-27B na dysku (dziś brak) |
| T2: `--np 1` vs `--np 4` greedy md5 na 6 promptach spec_sweep + 2 code-edit | XTX, 3090 | 0 t/s; bramka poprawności multi-slot | 15 min GPU | — |
| T3: MTP z progiem pozycji 0.9 (i 0.8) vs stałe n=4, ABBA, spec_sweep + long 32k | XTX | 0…+2% | 10–20 min GPU | ramię w `ds.jobs` |
| T4: tqLLM 1.2.3 Flash-Next vs nasz 27B na tej samej wynajętej 3090 (czat T=0/T=1, po 32K, TTFT) | 3090 | wiedza konkurencyjna; dla nas 0 t/s | ~2 h wynajmu z ≥ 128 GB RAM (~$1–2) + pobranie ~55 GB na maszynie wynajmu | zgoda na pobranie na Vast |
| T5: Gyro-Coder (fork agentionai, Vulkan, potem próba HIP) vs nasz 27B: czat t/s + 8 zadań kodowych × 2 seedy | XTX | nieznany; kill < 95 t/s albo mniej zadań niż 27B | 0.5 dnia + 70.6 GiB na dysku | zgoda na pobranie |
| T6: MTP na qwen35moe w topce (Qwen3.6-35B-A3B z blokiem `nextn`) | 3090 / XTX (katalog) | ×1.4–1.8 dla tieru 10–16 GB (wg tqLLM) | 1 h GPU | GGUF z MTP (pobranie) |

## 8. Do bazy wiedzy

- **Fakt:** Gyro-Coder to 256/512 ekspertów na warstwę (selekcja ewolucyjna, ~2 200 kandydatów), eksperci TQ2_T 2.125 bpw, 19.92 GiB GPU + 50.7 GiB tabeli n-gramów na NVMe. Uruchamia go tylko fork agentionai (Docker Vulkan). Python KLD 0.165 / top-1 93.1% vs Q8_0, zadania 13/16 (8-bit: 15/16).
- **Fakt:** 2026-10-24 opublikowano format Gyro (`agention-gyro` `587a526`, Apache-2.0): 8 typów 1.125–3.625 bpw (TQK4 151, TQK5 150, TQK6 145, TQK7 146, TQ2_T 144, TQP5–7 147–149), bloki 128, 15-bitowy stan, kodebook 2048, obrót block-Hadamard w metadanych. Referencyjny enkoder jest jawny, ale słabszy od produkcyjnego. **Korekta** R57b („enkoder zamknięty”): zamknięty pozostaje tylko enkoder produkcyjny.
- **Fakt:** tqLLM 1.2.x ma otwarty kod (Apache-2.0), tylko CUDA/MLX. Flash-Next na 3090: 77.1 vs 47.2 t/s (Strata) po 128K, czat 96–103 t/s (1.2.3). Wymaga ≥ 64 GB RAM (pomiary na 128 GB), więc „32 GB RAM” z obiegu jest nieprawdą.
- **Lekcja:** osadzenia per warstwa / n-gram czytane wierszami z dysku kosztowały tqLLM 15% dekodu. Takie tablice trzymaj w RAM.
- **Fakt:** MTP na MoE (Qwen3.6-35B-A3B, tqLLM, 3090): 178–183 → 246–330 t/s. Nasze lokalne GGUF-y q36 nie mają bloku MTP.
- **Metoda (DCQ):** dodanie błędu końcowego stanu GDN do straty PTQ. `in_proj_qkv` (u nas `attn_qkv`) ma rel. MSE stanu 0.0198 przy 4 bitach vs 0.0008 wyjścia. Dowody DCQ są słabe: n=20, JSON GPTQ W4 = DCQ W4, AWQ to zepsuty przebieg, AIME bez pokrycia, kalibracja 4 096 tokenów.
- **Fakt:** „4.6×” @superalesha = 82 → 382 t/s na cytowaniu 25K (HyperQwen `[INFERENCE]`); czat ~133 t/s (1.6×).
- **Fakt:** „574 tok/s DeepSeek V4.1 Flash” to 4× RTX Pro 6000 Max-Q; źródło pierwotne mówi 500+ (megakernel WIP), a 574 jest `[niezweryfikowane]`.
- **Fakt:** Bolt-E4B to Gemma-4-E4B + RL NVIDIA, 42 warstwy, słownik 262 144, 64K, Q4_K_M 6.18 GB, własny drafter DFlash. Nie nadaje się na drafter Qwena; to model telefon/edge.
- Wersje bazowe: `agention-gyro@587a526`, `turbo-tan/tqllm@c2163c2` (v1.2.3), `agentionai-group/llama.cpp@9aa51ce`.

## 9. Źródła

- Gyro-Coder: https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF · Gyro: https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-GGUF · format: https://gitlab.com/agentionai-group/agention-gyro (README, SPEC.md) · fork: https://gitlab.com/agentionai-group/llama.cpp (`ggml/src/ggml-cuda/tq.cuh`, `template-instances/mmq-instance-tq*.cu`, `ggml-vulkan/vulkan-shaders/*tq*`)
- Qwen: https://huggingface.co/Qwen/Qwen3.8-Flash-Next · https://huggingface.co/Qwen/Qwen3.8-27B (tabele benchmarków)
- tqLLM: https://tqllm.com/releases · https://tqllm.com/performance · https://github.com/turbo-tan/tqllm (`CHANGELOG.md` 1.2.0–1.2.3, `LICENSE`, `src/models/qwen/qwen4exp/`) · https://huggingface.co/YTan2000/Qwen3.8-Flash-Next-tqLLM
- DCQ: https://huggingface.co/Akahsizrr/mimo-v2.6-distill-qwen-9b-dcq (README, `tools/quant_learned.py`, `tools/sens_probe.py`, `results/*.json`; drzewo przez API: `awq_w4_sglang_20.json` i `learned_w2*_mmlu_gsm_20.json` mają ten sam oid `58d8c78f`)
- @superalesha: https://x.com/superalesha/status/2113131231168831637 · https://x.com/superalesha/status/2111885825218838905 (treść przez https://api.fxtwitter.com/) · HyperQwen: https://github.com/syv-ai/qwen38-27b-rtx3090 (R15b)
- Fraser Price: https://x.com/fraserpricee/status/2112111199454454169 · https://github.com/fraserprice/dspark-vllm · https://huggingface.co/fraserprice/DeepSeek-V4-Flash-DSpark
- FastH3 Omni: https://huggingface.co/FastVideo/FastVideo-FastH3-Omni-8-Step-V1 · https://huggingface.co/FastVideo/FastH3-Omni-NVFP4-QAD-Comfy
- Bolt-E4B: https://huggingface.co/unsloth/NVIDIA-Nemotron-3.5-Bolt-E4B-GGUF · https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-BF16 (`config.json`) · https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-DFlash · https://unsloth.ai/docs/models/nemotron-3.5-bolt
- Nasze: R14, R15b, R15c, R16e, R21n (+ `21n-notatki/gguf-M-TQ2_0.txt`), R27, R32a §3, R32f, R57a, R57b, R57g (`57g-skrypty/alloc.json`), R58, [[REKORDY]], `wiki/eksperymenty/2026-10-10-sweep-mtp-dflash.md`
