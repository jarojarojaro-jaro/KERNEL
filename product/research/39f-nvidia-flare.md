# 39f. NVIDIA Flare (flare-local-inference): czego się nauczyć dla forka llama.cpp

Repo: <https://github.com/NVIDIA/flare-local-inference>, Apache-2.0, płytki klon `47581cc` (2026-10-20), 1093 pliki, 202 × `.rs`, ~400 × `.py` poza testami. Kernele: fork `local-inference-lab/flashinfer` z `b12x`, przypięty na `622cec10` (HEAD forka `4092b28`, 2026-10-19). Czytałem tylko kod i dokumenty, bez GPU i bez kosztów. W KB nie było nic o Flare. FlashInfer jest w `ZRODLA.md:79` jako „średnia, tylko NVIDIA”, a ten raport opisuje tylko to, co nowe.

## TL;DR

- **Architektura się potwierdza.** Ignition (PyTorch + Transformers + b12x) ładuje checkpoint, stroi kernele, przepuszcza cały forward przez `torch.compile` i przechwytuje grafy CUDA. Wynik eksportuje do podpisanego pakietu `.safetensors` z zaszyfrowanymi cubinami i „rekordami grafów”. Helios w Rust nie deserializuje grafów: odbudowuje je węzeł po węźle (`cuModuleLoadData` → `cuGraphCreate` → `cuGraphAddKernelNode_v2`/memset/memcpy/event-wait → `cuGraphInstantiateWithFlags`, `helios/src/runtime_package/mod.rs:492-763`) i uruchamia przez `cuGraphLaunch`. W trakcie serwowania Python nie działa.
- **Graf obejmuje cały krok**, razem z metadanymi żądań, samplingiem i (w trybie spekulacji) weryfikacją, akceptacją i commitem (`core-design.md:588`, `performance-work.md` „Complete-forward compilation”). Graf sam zapisuje próbkowany token do stanu żądania na GPU, a następny krok czyta go bezpośrednio. Dlatego zwykły decode ma **dwa kroki w locie** (`core-design.md:1159-1174`). **Spekulacja ma tylko jedną rundę w locie**, bo host wybiera szerokość weryfikacji i propozycje kopiowania z gotowego wyniku. Nawet NVIDIA nie schowała luki hosta w spekulacji.
- **Qwen3.8-27B jest obsługiwany**, ale tylko jako `nvidia/Qwen3.8-27B-NVFP4` (20.15 GB na GPU) i **bez spekulacji**: `max_draft_tokens=0`, a przy `plan.speculation` przepis rzuca błąd (`ignition/recipes/qwen38_dense/recipe.py:12-13,38`). MTP, adaptacyjna weryfikacja i drafty kopiowane z historii (`--history-drafts`) działają tylko dla Qwen3.8-Flash-Next, GLM-5.3-Flash i DeepSeek-V4.1 (DSpark).
- **Na 16 GB nic się nie mieści.** Najmniejsze przepisy to Qwen3.8-27B (20.15 GB) i Nemotron-3.5-Bolt-74B-A9B (25.06 GB). 5060 Ti, 5070 i 5080 odpadają, a 5090 (32 GB) mieści tylko te dwa. Formalnie kod celuje w SM120/SM121 (`sm_120a`), więc GeForce Blackwell jest w zasięgu architektonicznie, ale nikt tego nie sprawdzał na GeForce (wszystkie przebiegi w dokumentach to RTX PRO 6000/4000, DGX Spark, RTX Spark N1X i GB300).
- **Nie ma opublikowanych liczb t/s dla jednego użytkownika.** Dokumenty podają tylko metodę: podłogę z minimalnego replay harnessu i wymóg, żeby natywny serwis był w granicy 5% od niej. Podają też sufit pasma dla Flash-Next (6.9 GB/token → ~3.9 ms przy 1.79 TB/s).
- **Dla nas:** nic, co dałoby ≥ +5% bezstratnie. Najlepsze rzeczy do przeniesienia to (1) wzorzec „token zwrotny na GPU + 2 kroki w locie”, czyli to samo, co L11/ZOS-lite z R36: sufit +1.8% na XTX i ≤ +3.9% na 5060 Ti, (2) metryka „serwis vs minimalna podłoga replay” jako stały pomiar, (3) kernel GDN decode z b12x jako wzorzec podziału V na 5060 Ti (sufit ≤ ~1.9% kroku, wynik nie musi być bitowo identyczny). FP8 KV i NVFP4 są dla nas na minusie, bo przy ograniczeniu pasma i 16 GB oznaczają więcej bajtów.
- **Konkurencja dla produktu: słaba na naszych kartach.** Flare obsługuje tylko NVIDIA, ma 9 przepisów, wymaga środowiska PyTorch i docelowego GPU do przygotowania pakietu, a większość modeli waży 70 GB–1.5 TB. Sygnał do obserwacji: natywny Windows ARM64 na **RTX Spark N1X** (SM121) z Qwen3.8-27B (`docs/windows.md:106`) i podpisane pakiety od wydawcy. Taki kanał dystrybucji pasuje do laptopów N1X. Śledzone w CompWatch (tier B).

## Tabela twierdzeń

| # | Twierdzenie | Werdykt | Dowód / uwaga |
|---|---|---|---|
| 1 | Zbudowany dla SM120/SM121 (RTX PRO 6000, DGX Spark) | **Potwierdzone** | `README.md:7`, `core-design.md:3`; `scripts/b12x_gemm_stage_race.py:245` odrzuca inne SM; GLM na SM103 (GB300) ma osobne kernele (`glm-batched-speculation-defect.md:230`) |
| 2 | PyTorch + FlashInfer przy budowie, Rust bez Pythona przy serwowaniu | **Potwierdzone** | `model-preparation.md:39-40`; Helios ładuje cubiny i buduje grafy z rekordów przez Driver API; `core-design.md:1600-1612` (zero callbacków Pythona, alokacji i rekompilacji po starcie) |
| 3 | Grafy CUDA przechwycone przed serwowaniem | **Potwierdzone, z doprecyzowaniem** | Katalog wariantów: decode 1/2/4, prefill 128…4096, resume, vision, snapshot/restore. Qwen Flash: 25 grafów, z MTP-5 40 grafów (`core-design.md:407-432`). Pakiet jest związany z SM i pojemnościami: zmiana pojemności w górę = ponowny eksport |
| 4 | Cały krok w jednym grafie | **Potwierdzone** | Sampling, metadane i maintenance są „captured server operations” (`core-design.md:588`). Spekulacja: MTP + weryfikacja + commit w jednym forwardzie (`performance-work.md` „Complete-forward compilation”); „acceptance and token feedback remain on the device” (`mtp-design.md:7-8`) |
| 5 | Dekodowanie spekulatywne | **Potwierdzone tylko dla MoE/Flash** | MTP do 5 draftów, adaptacyjna szerokość, drafty z historii żądania. **Qwen3.8-27B dense: brak** (`qwen38_dense/recipe.py:12,38`) |
| 6 | FP8 KV domyślnie | **Częściowo** | „Every recipe defaults to FP8 E4M3 KV” (`model-preparation.md:41`), dense 27B też (`qwen38_dense/pool.py:47`). Ale `core-design.md:1476-1480` mówi, że **główne KV Qwen Flash jest BF16**, bo checkpoint nie deklaruje kwantyzacji KV, a FP8 to „separately qualified option”. Dokumenty są ze sobą sprzeczne |
| 7 | Jakość FP8 KV | **Niezweryfikowane** | Step-5 używa „unit descales”, czyli bez kalibracji (`model-preparation.md:374`). Brak PPL/KL/zadań. Testy są komponentowe (np. sparse MLA cos ≥ 0.99998 na rekordach FP8, `glm-batched-speculation-defect.md:277`), bez końcowej jakości modelu |
| 8 | Przepisy Qwen Flash, GLM, DeepSeek | **Potwierdzone, a jest ich więcej** | 9 przepisów: qwen38 (Flash-Next, 73.5 GB), qwen38_dense (27B, 20.2 GB), glm53 (177.8 GB), deepseek4 (160 GB), deepseek41 (306.6 GB), kimi3 (1.5 TB), mimo_v2 (568.5 GB), step5 (367.5 GB), nemotron_h (74B-A9B, 25.1 GB) |
| 9 | Liczby decode dla jednego użytkownika | **Brak** | Jest tylko metodologia (`core-design.md:1640-1693`) i sufit pasma Flash-Next ~3.9 ms/token. Jedyne zmierzone czasy to replay TP ~0.67 ms (`same-process-tp.md:161`), nieprzydatne |
| 10 | Działa na konsumenckim sm_120 (5060 Ti/5070/5080/5090) | **Niezweryfikowane** | Architektura ta sama (`sm_120a`), więc prawdopodobnie tak `[INFERENCE]`. Pamięć: ≤16 GB żaden przepis, 5090 dwa przepisy. Pakiet przygotowuje się na docelowym GPU (strojenie), więc na 16 GB nie zrobi się go nawet dla 27B (wagi 20 GB) |
| 11 | „Rust = szybciej” | **Obalone przez samych autorów** | README: „Rust gives the serving runtime explicit resource ownership; performance still depends on the GPU work…”. `core-design.md:60`: tłumaczenie hosta nie zmniejsza bajtów GEMM |

## Przenośne pomysły (ranking)

Budżety: XTX z R36 §1 (27.38 ms/krok prozy, weryfikacja 24.50, w tym koszt stały ~2.4, host 0.49) i 5060 Ti z R31-5060ti (62.6 t/s, krok ~49 ms, luki hosta ~1.9 ms/krok łącznie, 2.9 `cudaGraphLaunch`/krok, zwykły token na 85% pasma).

| # | Pomysł (z Flare) | Zysk: sufit | Wysiłek | Bezstratny | Uwagi |
|---|---|---|---|---|---|
| 1 | **Token zwrotny na GPU + przygotowanie wejść następnego kroku przed odczytem wyniku** (Flare: 2 kroki w locie dla decode, 1 runda dla spekulacji, rekordy token/status kopiowane osobnym strumieniem po evencie) | XTX ≤ 0.49/27.38 = **+1.8%**; 5060 Ti ≤ 1.9/49 ≈ **+3.9%** | 1–3 dni (to jest L11/ZOS-lite z R36) | tak (md5) | Flare przy spekulacji nadal czeka na wynik rundy, więc realnie zostaje część luki: akceptacja na GPU, ale plan następnej rundy na hoście. Realny zysk to raczej połowa sufitu `[INFERENCE]` |
| 2 | **Metryka „serwis vs minimalna podłoga replay ≤ 5%”** jako stały gate (harness odtwarza ten sam ciąg grafów bez serwera) | 0 bezpośrednio; mierzy pkt 1 | ~0.5 dnia (CUDA: odtworzyć przechwycony `cudaGraphExec` w pętli; XTX: mamy PM4 replay) | n/d | Rozdziela GPU, submisję i HTTP. U nas ślady host-gap robią to częściowo. Podłoga replay daje górną granicę bez zgadywania |
| 3 | **b12x `gdn_decode` jako wzorzec dla GDN przy 5 kolumnach na sm_120** (tuning `recurrent_block_v ∈ {16,32}`, CuTe DSL) | GDN na 5060 Ti: 1.20 ms przy T vs 0.26 przy U1 (+0.94 ms/krok), więc ≤ **~1.9%** kroku | 2–4 dni (port z CuTe DSL do CUDA C++) | **nie gwarantowany** (inna kolejność redukcji FP32, potrzebna bramka tolerancji) | Kod jest Apache-2.0 (`local-inference-lab/flashinfer`, `flashinfer/experimental/b12x/sequence/gdn_decode/`). Najpierw przeczytać `_kernels.py`; wydajności na GeForce nie sprawdzałem |
| 4 | Sampling w tym samym grafie co weryfikacja (2.9 → ~1 `cudaGraphLaunch`/krok) | ~2 launche × 10–20 µs ≈ **≤ 0.1%** `[INFERENCE]` | 1 dzień | tak | Nie warto osobno. Wychodzi przy okazji pkt 1 |
| 5 | Pojemności grafów jako katalog (batch × szerokość weryfikacji) wybierany przez scheduler na podstawie zmierzonego czasu grafu (`scheduling-theory.md`) | ~0 dla 1 użytkownika | — | tak | Mamy już routing profili spekulacji (R44). Dla `-np 1` brak delty |
| 6 | FP8 E4M3 KV zamiast q4_0 | **ujemny**: 27B ma 16 warstw × 2 × 4 × 256; FP8 = 32 KiB/token vs q4_0 = 18 KiB/token; przy 32k +0.47 GB, a 5060 Ti ma 15839/16311 MiB, więc **nie mieści się**; więcej bajtów czytanych w FA | — | nie (inny format) | XTX nie ma sprzętowego FP8. Na 24 GB+ jakościowo FP8 > q4_0 `[INFERENCE]`, ale Flare nie publikuje jakości |
| 7 | NVFP4/MXFP8 b12x GEMM zamiast MMVQ | **ujemny** dla 16 GB: NVFP4 27B to 20.15 GB vs IQ4_XS 14.25 GB (+41% bajtów przy decode ograniczonym pasmem) | — | nie (inne wagi) | Ma sens tylko przy batch > 1 albo na 5090 z FP4 tensor cores. Poza zakresem |
| 8 | „Rust zamiast llama-server” | ≤ luki hosta (pkt 1), samo przepisanie nic nie da | tygodnie | — | Odrzucone. Autorzy sami tak piszą |

**Pełny graf kroku vs nasz PM4 replay (XTX):** Helios robi to samo co nasz replay, czyli z góry zapisane węzły i zero pracy hosta na kernel. Różnica jest tylko w zakresie (u nich sampling i akceptacja też są w grafie). Koszt stały ~2.4 ms w weryfikacji XTX to czas GPU (ogony i rozruch kerneli), nie submisja, więc capture go nie usuwa. Tę część zmniejszają tylko fuzje i lepsze kernele.

## Eksperymenty ≤ 10 min

1. **(GPU, 5060 Ti, 10 min)** Podłoga replay: przechwycić graf weryfikacji n=5 z `cuda-topka2` i odpalić go 200× w pętli (`cudaGraphLaunch` + `cudaStreamSynchronize` tylko na końcu), potem porównać z ms/krok z serwera. Różnica to twardy sufit pkt 1 na sm_120 (oczekiwane ≤ 1.9 ms).
2. **(XTX, 10 min)** To samo na PM4 replay. R36 L11 już zakłada A/B `GPU_FORCE_BLIT_COPY_SIZE=1024` i nowy ślad host-gap. Dodać podłogę replay jako trzecie ramię.
3. **(CPU, 10 min)** Przeczytać `b12x/sequence/gdn_decode/_kernels.py` i `_tuning.py` na `622cec10`: jak dzielą V przy wielu kolumnach i czy stan jest w rejestrach czy w smem. Wynik zapisać jako notatkę do pkt 3, bez kodu.
4. **(CPU, 5 min)** Sprawdzić `nvidia/Qwen3.8-27B-NVFP4` na HF: które warstwy są NVFP4 a które BF16, i rozmiar head. To ważne dla katalogu, jeśli kiedyś dodamy ścieżkę NVFP4 na 5090.

## Konkurencja i produkt

- Inny segment: stacje robocze i Spark, modele 70 GB+, operator, który sam przygotowuje pakiet. Na naszych kartach (XTX/R9700, Ampere/Ada, 5060 Ti) nie działa albo się nie mieści. Picker/katalog nie musi go uwzględniać.
- Do obserwacji: (a) Windows ARM64 + RTX Spark N1X z 27B (konsumencki laptop NVIDIA); (b) podpisane pakiety z profilem wydawcy (`signing.md`), co wygląda na przyszły kanał gotowych pakietów od NVIDIA; (c) jeśli dojdzie przepis ≤16 GB i spekulacja dla 27B dense, Flare stanie się bezpośrednim punktem odniesienia na 5090/5080. Dlatego repo jest w CompWatch.

## Do bazy wiedzy

| Źródło | Data/wersja | Q/ref | Wartość | Status |
|---|---|---|---|---|
| NVIDIA Flare (NVIDIA/flare-local-inference) | `47581cc`, 2026-10-20 | 39f | Średnia: wzorzec „cały krok w grafie + token zwrotny na GPU + 2 kroki w locie” (= L11 R36), metryka podłogi replay; 27B tylko NVFP4 bez spekulacji; nic na ≤16 GB | CompWatch B |
| local-inference-lab/flashinfer (b12x) | `622cec10` (przypięty w Flare); HEAD `4092b28`, 2026-10-19 | 39f | Średnia: `sequence/gdn_decode` (CuTe DSL, `recurrent_block_v` 16/32) jako wzorzec GDN przy 5 kolumnach na sm_120 | – |
