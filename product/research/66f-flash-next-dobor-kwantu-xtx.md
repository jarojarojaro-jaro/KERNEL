# 66f: Qwen3.8-Flash-Next na naszym boxie: dobór kwantu i silnika (2026-11-06)

**TL;DR**
- Na XTX 24 GB + 62 GB DDR4 (Ryzen 7 5700X) i 119 GB wolnego dysku najlepszym wyborem jest **Strata + ISTA-DASLab GSQ-RCO IQ3_S**: 54.8 GB w RAM i VRAM plus 28.8 GB tabeli n-gramów na SSD.
- To najwyższy kwant, jaki Strata dopuszcza przy 64 GB RAM. Społeczność zmierzyła na XTX 62.3 t/s (z DDR5 i 96 GB RAM).
- Najwyższy kwant, który w ogóle się mieści, to **Unsloth Dynamic v3.1 UD-IQ4_XS** (93.7 GB). Działa tylko w llama.cpp z `qwen4exp`, ma na HIP błąd ładowania #29149, a jego MTP siedzi w osobnej gałęzi. Szacujemy go jako wolniejszy.
- UD-Q4_K_XL (111.3 GB) się nie mieści: bez tabeli n-gramów zostaje 82.5 GB, a RAM i VRAM to ~86 GB łącznie, przed KV i systemem.
- Dzisiejsze 27B daje 95–217 t/s. Flash-Next będzie wyraźnie wolniejszy, ale lepszy w benchmarkach agentowych.

## Model (karta HF unsloth/Qwen3.8-Flash-Next-GGUF, README)
- **Parametry:** 125B MoE, 6B aktywnych, do tego 51B embeddingu n-gramowego (warstwa 2) i 4B MTP.
- **Warstwy:** 48 = 12 × (3 × GDN → MoE, 1 × QSA → MoE).
- **QSA:** 24 głowice Q i 2 głowice KV, head 256.
- **Eksperci:** 512, aktywnych 10 routowanych + 1 współdzielony, wymiar pośredni 640.
- **Kontekst:** 262 144 natywnie, do 1M z rozszerzeniem.
- **Benchmarki z karty, Flash-Next vs Qwen3.8-27B:**
  - DeepSWE 1.1: 58.7 vs 42.2;
  - SWE-bench Pro: 62.5 vs 61.7;
  - JobBench: 55.7 vs 33.4;
  - Toolathlon: 73.5 vs 67.1;
  - GPQA-D: 91.7 vs 89.2;
  - HLE: 35.9 vs 30.8.
- **Licencja:** Qwen Community 1.0. Do produktu „AI Work Assistant” potrzebna osobna licencja (wiki `ludzie-firmy/qwen-alibaba`).

## Rozmiary (API HF tree, 2026-11-06; GB dziesiętne)
Tabela n-gramów to w każdym kwancie osobny shard: IQ4_NL, 28.8 GB. Przy losowym dostępie wystarczy ją zostawić na SSD (mmap), czyta się kilka wierszy na token.

| Kwant Unsloth v3.1 | Razem | Bez tabeli n-gramów | top-1 / mean KLD (Unsloth) | Mieści się u nas? |
|---|---:|---:|---|---|
| UD-Q2_K_XL | 79.5 | 50.7 | 82.7 / 0.225 | tak |
| UD-IQ3_XXS | 83.6 | 54.8 | 85.4 / 0.165 | tak |
| UD-Q3_K_XL | 89.4 | 60.6 | 88.3 / 0.107 | tak (llama.cpp); w Stracie na styk |
| **UD-IQ4_XS** | 93.7 | 64.9 | **89.6 / 0.084** | tak w llama.cpp (~13 GB na GPU + ~52 GB w RAM); w Stracie nie (eksperci + 10 GB > 62 GB) |
| UD-Q4_K_XL | 111.3 | 82.5 | 92.3 / 0.047 | **nie** |

Tabele n-gramów do podmiany (`engram/`):
- BF16 102.4 GB;
- Q8_0 54.4 GB;
- Q5_1 38.4 GB, RMSE 0.038;
- IQ4_NL 28.8 GB, RMSE 0.076.

IQ4_XS z tabelą Q5_1 zajmuje 103.3 GB i mieści się na dysku (119 GB wolne).

Shared MTP Q8_0: 2.8 GB. Unsloth podaje dla MTP przy 4 bitach 97–115 GB łącznej pamięci.

ISTA-DASLab GSQ-RCO (domyślny dostawca Straty; `docs/MODELS.md`):
- IQ3_S: 54.8 GB w RAM i VRAM, eksperci 50 GB, „best; matches the full model”;
- IQ3_XXS: 47.0 GB;
- Strata wymaga RAM ≥ eksperci + 10 GB, więc IQ3_S przy 64 GB „with little else open”.

## Silniki na gfx1100
- **Strata (rekomendacja):**
  - wszyscy eksperci są w RAM i liczeni na CPU, gorący cache ekspertów i KV siedzą w VRAM, tabela n-gramów na SSD;
  - MTP jest wbudowane, jest paczka Linux rx7900;
  - pomiary społeczności na XTX: IQ3_S 62.3 t/s, MTP spec 3, greedy, 7900X + 96 GB DDR5; prefill przy 128K 926 → 1687 t/s z tabelą hipBLASLt (R57b §4);
  - nasz DDR4 dual-channel ma ~połowę pasma DDR5, więc `[INFERENCE]` spodziewamy się ~40–55 t/s;
  - zastrzeżenie: opiekunowie nie uruchamiali paczek RX 7000 na karcie (`docs/AMD_HIP.md:114-118`).
- **llama.cpp upstream:**
  - ma arch `qwen4exp` (QSA: `GGML_OP_LIGHTNING_INDEXER`, `TOP_K_MASK`) i `--moe-cache-mib` (PR #29887);
  - MTP jest tylko w `danielhanchen/llama.cpp` na gałęzi `qwen4exp/mtp`;
  - otwarte problemy:
    - #29149: livelock ładowania na HIP, jest łatka z buforem pośrednim 64 MiB; ta sama ścieżka mmap → upload na urządzenie co nasze `init_user_pages` w dmesg `[INFERENCE]`;
    - #30032: OOM indeksera QSA przy wizji;
    - #30768: śmieci na Vulkan RADV z transfer queue;
  - społeczność (#29149): RX 9060 XT 16 GB + 64 GB DDR4: 8 t/s, przy długim kontekście 3 t/s (ROCm); 5700X + 16 GB VRAM + DDR4: 14.8 t/s;
  - na V100 Strata vs llama.cpp z `--moe-cache-mib`: ~2.4× (#3082).
- **Topka (nasz fork):** brak `qwen4exp` (baza d5839abfb), więc odpada bez rebase.

## KV przy pełnym kontekście
- Pełna uwaga to tylko 12 warstw QSA × 2 głowice KV × 256, co daje 24.6 KB/token f16, a indekser dokłada ~3 KB/token.
- 262 144 tokenów to ok. **7.2 GB f16**, do tego mały stan GDN. Pełny kontekst bez kwantyzacji KV jest więc wykonalny `[INFERENCE: z karty modelu]`.

## Plan testu (po decyzji użytkownika)
1. Pobranie robi użytkownik, ~84 GB, nie my przez łącze domowe:
   - **Strata `--include` IQ3_S** z repo ISTA-DASLab;
   - alternatywa: UD-IQ4_XS + shared MTP Q8_0 (~97 GB).
2. Czat 27B zatrzymać przez `run-llm.sh` (jeden SIGTERM).
3. Uruchomić Stratę z paczki rx7900.
4. Test w tych samych warunkach co nasz czat: spec_sweep T=1 seedy 1,2,3, prompt prefill 12K, fill 255K, VRAM i RAM w szczycie, waty i temperatury przy eco 2200.
5. Wynik zapisać jako baseline (27B uncensored) → Flash-Next → %, plus jakościowo DeepSWE wg karty.
6. Powrót: `run-llm.sh uncensored`.

## Źródła
- https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF (README, API tree 2026-11-06)
- https://unsloth.ai/docs/models/qwen3.8-next (Dynamic v3.1, tabela KLD, engram, MTP)
- https://github.com/Niko1221/Strata `docs/MODELS.md` (main, 2026-11-06)
- https://github.com/ggml-org/llama.cpp/issues/29149, /issues/30768, /issues/30032, /pull/28699
- R57b (`57b-strata-qwen38-flash.md` §4), R21n, wiki `repo/strata`, `repo/llama-moe-cache-mib`, `repo/tqllm`
