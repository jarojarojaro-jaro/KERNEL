# 33 — Najlepsze modele lokalne na klasę karty (ctx ≥ 131k), październik 2026

Data: 2026-10-20. Autor: ModelScout (Opus, tylko CPU, `nice -n 19`, nic nie wynajęte ani pobrane poza nagłówkami GGUF).
Poprzednik: [`PLAN-NV-V2.md`](../PLAN-NV-V2.md) (eeb29e9) sprawdzał tylko Qwen3.8-27B / Saluki / Bonsai / LFM / Qwen3.5-9B
i dla 10–16 GB napisał „brak modelu”. Ten raport rozszerza pole o MoE (z ekspertami w RAM), Gemma 4, Ornith, Nemotron,
GLM, gpt-oss, Mellum i inne modele z HF (październik 2026).

Narzędzie: `qwen-opt/cloud/fitcalc.py` (rozszerzony w tym commicie: iSWA, MLA, MoE i `--n-cpu-moe`, drafter jako osobny
plik `--draft`, szacunek decode t/s). Dane społeczności: LocalMaxxing (peer Res32dLocalmaxxing, `/tmp/ms/localmaxxing-per-karta.md`,
dane tylko do użytku wewnętrznego), llamaperf.com (agregat r/LocalLLaMA; Reddit z tej sieci zablokowany), karty modeli na HF.

Oznaczenia: `[SZACUNEK]` = z modelu fitcalc, `[INFERENCE]` = wniosek bez pomiaru, „LM” = LocalMaxxing, „LP” = llamaperf.
t/s to **plain decode** (bez spekulacji) przy głębokości 0 / 64k / 131k, chyba że napisano inaczej.

## 0. Werdykt: jeden wybór na kartę

| karta | wybór | kwant, flagi | `-c` | VRAM szczyt @131k / RAM na ekspertów | t/s 0 / 64k / 131k `[SZACUNEK]` | dlaczego |
|---|---|---|---|---|---|---|
| **RTX 3080 10 GB** | **Qwen3.6-35B-A3B** (MoE 35B/3B) | UD-IQ4_XS 18.2 GB, `--n-cpu-moe 28`, KV q4_0 | 131072 (max 143k) | 9530 MiB / 10.5 GB (RAM ≥ 32 GB) | 64 / 55 / 47 | jedyna klasa „jakość ≈ AA 18” z ≥131k na 10 GB; żaden 27B nie przechodzi J1 |
| **RTX 3060 12 GB** | **Qwen3.6-35B-A3B** | UD-IQ4_XS, `--n-cpu-moe 21`, KV q4_0 | 131072 | 11666 / 7.8 GB | 52 / 40 / 32 | LP: 3060 Q4_K_M ncmoe 25 → 50–58 t/s @32k; Ornith Q4_K_M 47.6 @32k, 30.6 @112k |
| **RTX 4070 Ti 12 GB** | **Qwen3.6-35B-A3B** | UD-IQ4_XS, `--n-cpu-moe 21`, KV q4_0 | 131072 | 11758 / 7.8 GB | 69 / 54 / 44 | 4070 S 12 GB (ik_llama): 64 @32k, 55 @128k |
| **RTX 4060 Ti 16 GB** | **Qwen3.6-35B-A3B** | UD-Q3_K_XL 17.2 GB, `--n-cpu-moe 8`, KV q4_0 | 131072 (max 151k) | 15560 / 2.8 GB | 68 / 46 / 34 | ~1.8× szybszy przy 64k niż najlepszy gęsty, który się mieści (Ornith-1.5-9B Q6_K: 26 t/s) |
| **RTX 5060 Ti 16 GB** | **Qwen3.6-35B-A3B** | UD-Q3_K_XL, `--n-cpu-moe 8` (+ MTP w pliku: `--n-cpu-moe 12`) | 131072 (max 145k) | 15570 / 2.8 GB | 95 / 66 / 50 | LM 5060 Ti Qwen3.6: mediana 115.9 t/s (IQ3_XXS/IQ4_NL) |
| **Mac 16 GB** | **Qwen3.6-35B-A3B** (warunkowo) | UD-IQ2_M 11.5 GB, `sudo sysctl iogpu.wired_limit_mb=12288`, KV q4_0 | 131072 | ~11.8 GB unified | 48 / 29 / 21 (M5) | LP: M4 mini 38 t/s; 2-bit = ryzyko jakości; żaden model nie spełnia wszystkich bramek z zapasem |
| **RTX 3090 / 4090 / XTX 24 GB** | **Qwen3.8-27B** (gęsty) | UD-Q4_K_XL + MTP, nasz fork (ramię T) | 131072 | 23630 (3090, walidowane) | **zmierzone**: 3090 czat T=1 93.3, po 60k 56.7; XTX 109–114.8 | AA 34 vs 18 najlepszego MoE; MoE (Ornith/Qwen3.6) jako „szybki” wariant 2.5–3.5× plain |
| **RTX 5090 32 GB** | **Qwen3.8-27B** | UD-Q6_K + MTP | 204800 | 31321 (plan) | plain 64 / 52 / 43; z MTP ~110 po 64k `[SZACUNEK]` | najwyższa jakość; Ornith-1.5-35B Q5_K_M 175 t/s @64k jako szybka alternatywa |

**Główny wniosek:** na 10–16 GB **MoE z częścią ekspertów w RAM (`--n-cpu-moe`) bije każdy gęsty model**. Daje 35B-klasę
(AA 18, GPQA-D 86, SWE-bench V 73.4) przy 131k i 40–95 t/s. Gęste alternatywy to 9–12B (AA 11–14) przy 20–40 t/s albo
27B w 2 bitach, które oblewają J1. Na 24–32 GB MoE jest 2.5–3.5× szybszy, ale gęsty Qwen3.8-27B ma wyraźnie wyższą
jakość (AA 34 vs 18; GPQA-D 89.2 vs 86.0). Z naszym MTP 27B też ma ≥ 56 t/s po 60k.

**Warunek dla 10–16 GB:** RAM systemowy ≥ 32 GB (DDR5 2ch) na eksperci + system. Przy DDR4-3200 (`--ram-bw 45`) t/s
spada o ~10–20% `[SZACUNEK]`. Prefill z ekspertami w RAM idzie przez PCIe (`GGML_OP_OFFLOAD_MIN_BATCH`; raport 04
§2.2.5): TTFT przy 131k to minuty, nie sekundy. Na 3080 z Vast (PCIe x1, `31-3060-3080.md:80`) to dyskwalifikuje.

## 1. Metoda

### 1.1 Pamięć: fitcalc v2 (z nagłówków GGUF, range requests)

Model pamięci z PLAN-NV-V2 §1.2, rozszerzony. Dla qwen35 (ramię T) wyniki są **identyczne bit w bit ze starą wersją**
(3090 Q4_K_XL c131072: loaded 21380 / peak 23630 MiB, max 140288). Zmiany:
- **KV per warstwa z kształtów tensorów** `attn_k` / `attn_v`. Brak `attn_v` oznacza V = K, ale V nadal jest w cache
  (globalne warstwy Gemma 4, `src/models/gemma4.cpp:244-246`). MLA (`attn_kv_a_mqa`) to tylko latent 576 (GLM-4.7-Flash).
- **iSWA**: warstwy SWA zajmują `min(c, pad256(n_swa + ub))` komórek (`llama-kv-cache-iswa.cpp:73`). Gemma 4: 25/30
  (26B), 50/60 (31B), 40/48 (12B) warstw SWA z oknem 1024. gpt-oss: 12/24 z oknem 128. Mellum: 21/28 z oknem 1024.
- **MoE**: `W_exp` z tensorów `*_exps`. `--n-cpu-moe N` zdejmuje z GPU ekspertów warstw 0..N−1, tak jak llama.cpp.
- **Drafter jako osobny plik** (`--draft`): wagi + jego kontekst (pliki `mtp-*.gguf` dla Gemma 4 i Nemotrona).
- **Stan rekurencyjny**: GDN (qwen35/qwen35moe) i Mamba-2 (nemotron_h), zawsze ×1.686 (walidowane snapshoty).
- **Wzrost szczytu po długim prompcie**: g(karta) × (największe f16 K+V na token jednej pełnej warstwy) / 4096.
  `[SZACUNEK]` dla architektur innych niż qwen35.
- Preset **mac16** (10922 MiB = domyślny working set 16 GB, 120 GB/s) i **mac16w** (wired_limit 12288 MiB, 153 GB/s).
  Oba `[SZACUNEK]`. Na Macu RAM jest wspólny, więc `--n-cpu-moe` nie dodaje pamięci, tylko przenosi obliczenia na CPU.

Walidacja nowych części na naszych logach (`04-wykrywanie-sprzetu-i-dobor-modeli.md:236-245`): LFM2.5-24B Q5_K_M
W_gpu 16233 MiB (log 16232), KV q8_0 @131072 = 1360 MiB (log 1360), bajty/token 1.78 GB (NOTES 1.78).

### 1.2 Prędkość: model dwuczłonowy z kalibracją

`t_tok = B_w/(η·BW) + B_kv/(0.18·BW) + B_ram/(0.7·BW_ram) + n_MoE·τ (+30 µs na warstwę MoE na CPU)`

- η (dense, plain U0) z naszych pomiarów Qwen3.8-27B: 3090 0.77, 4060 Ti 0.87, 5060 Ti 0.81, 4070 Ti 0.76, XTX (Vulkan) 0.67.
  3060 (0.54) i 3080 (0.42) zmierzono tylko na plikach IQ2/Q2. Dla K-quantów ≥Q3 przyjmuję η = 0.65 `[SZACUNEK]`.
  4090 0.78, 5090 0.75 i Mac 0.70 `[SZACUNEK]`.
- η_kv = 0.18: decode w FA czyta skwantowane KV dużo poniżej pasma. Dopasowane na 3090 (43.1 → 30.4 t/s przy 64k,
  `27-3090-final.md:100,103`) i potwierdzone na sweepach 5060 Ti / 3060 ze społeczności. Nasz `GGML_CUDA_KVQ=1` (+28% po
  29.5k, PLAN-NV-V2 O1) poprawia dokładnie ten człon.
- τ (dodatkowy czas na warstwę MoE: router, top-k, gather) dopasowany na medianach LM/LP llama.cpp: Ampere 85 µs,
  Ada 65, 5060 Ti 40, 5090 70, XTX 60, Mac 80 `[SZACUNEK]`.

| model, karta | głębokość, `--n-cpu-moe` | zmierzone t/s | fitcalc | stosunek | źródło |
|---|---|---|---|---|---|
| Qwen3.8-27B Q4_K_XL, 3090 | 0 / 64k | 43.1 / 30.4 | 42.9 / 32.8 | 1.00 / 1.08 | `27-3090-final.md:100,103` |
| Qwen3.8-27B IQ4_XS, 4060 Ti / 5060 Ti | 0 | 18.4 / 26.7 | 18.3 / 26.6 | 1.00 / 1.00 | `31-4060ti.md:19`, `31-5060ti.md:10` |
| Qwen3.8-27B IQ3_XXS (proxy Q3_K_XL), 5060 Ti | 4k / 64k | 29.2 / 19.8 | 28.1 / 20.2 | 0.96 / 1.02 | LP 9b3857be |
| Gemma 4 26B-A4B Q4_K_XL, 3090 | 0 | 138.3 (mediana) | 135.5 | 0.98 | LM |
| Gemma 4 26B-A4B Q3_K_XL / MXFP4, 5060 Ti | 0 | 105.7 / 95.2 | 99.2 / 93.4 | 0.94 / 0.98 | LM; LP 2fa4707c |
| Gemma 4 26B-A4B, XTX / 5090 (4-bit) | 0 | 142.8 / 243.9 | 138.7 / 258.3 | 0.97 / 1.06 | LP |
| gpt-oss-20b Q4_K_M, 3090 | 0 | 170.9 | 189.6 | 1.11 | LM |
| Qwen3.6-35B-A3B Q4_K_M, 3090 / 4090 | 0 | 121.6 / 164.1 | 138.4 / 163.7 | 1.14 / 1.00 | LM |
| Ornith-1.5-35B Q4_K_M, 3060 | 8k n22 / 32k n24 / 112k n24 | 56.4 / 47.6 / 30.6 | 50.5 / 40.8 / 26.5 | 0.89 / 0.86 / 0.86 | [Ajay9o9 RESULTS](https://raw.githubusercontent.com/Ajay9o9/runs-on-a-3060/main/RESULTS.md) |
| Qwen3.6-35B (APEX 17 GB, ik_llama), 4070 S | 32k n16 / 128k n20 | 64.0 / 55.3 | 53.9 / 31.7 | 0.84 / **0.57** | [shiqikuangsan31](https://github.com/shiqikuangsan31/Qwen3.6-35B-12GB-VRAM-Guide) |
| Ornith-1.5-35B Q4_K_M, 4070 Ti S 16 GB / 3090 | 0, n15 / 0 | 88 / 131 | 65.7 / 158.1 | 0.75 / 1.21 | LP ornith1-5 |

Błąd modelu: **0.75–1.21× na llama.cpp** (mediana ~0.98). Głęboki kontekst w ik_llama.cpp jest szybszy, niż model
przewiduje (0.57), więc liczby @131k są raczej dolnym oszacowaniem.

### 1.3 Jakość

Ranking z oficjalnych tabel i Artificial Analysis Intelligence Index v4.3.2 (z 2026-10-20; skala zmieniła się w 2026,
nie mieszać ze starszymi artykułami). KLD kwantów tylko tam, gdzie je opublikowano albo zmierzyliśmy. **Bramka J1
(KLD ≤ 0.05/0.07) z PLAN-NV-V2 dotyczy kwantów tego samego modelu.** Dla innych modeli porównuję jakość bazową
(benchmarki) i stratę kwantu osobno.

## 2. Kandydaci: architektura i KV (z nagłówków GGUF)

| model | typ, total / aktywne | atencja (pełne / SWA / liniowe) | KV pełnych warstw B/tok q8_0 (q4_0) | KV @131k q8_0 | ctx natywny | llama.cpp / nasz fork | licencja |
|---|---|---|---|---|---|---|---|
| Qwen3.8-27B | gęsty 27.8B | 16 pełnych + 48 GDN + 1 MTP | 34816 (18432) | 4.25 GiB | 262k | `qwen35`, T | Apache-2.0 |
| Qwen3.6-35B-A3B | MoE 35B / 3B, 8/256 + shared | 10 pełnych (2×256) + 30 GDN + MTP | 10880 (5760) | 1.33 GiB | 262k | `qwen35moe` ✓ | Apache-2.0 |
| Ornith-1.5-35B-A3B | MoE jak wyżej (fine-tune RL) | jak wyżej, MTP w GGUF | 10880 | 1.33 GiB | 262k | `qwen35moe` ✓ | MIT |
| Gemma 4 26B-A4B | MoE 25.2B / 3.8B, 8/128 + shared | 5 pełnych (2×512, K=V) + 25 SWA (8×256, okno 1024) | 10880 + 159 MiB SWA | 1.48 GiB | 262k | `gemma4` ✓ + `gemma4-assistant` (MTP) | Apache-2.0 |
| Gemma 4 31B | gęsty 30.7B | 10 pełnych (4×512) + 50 SWA (16×256) | 43520 + 638 MiB | 5.94 GiB | 262k | `gemma4` ✓ | Apache-2.0 |
| Gemma 4 12B | gęsty 12B | 8 pełnych (1×512) + 40 SWA | 8704 + 255 MiB | 1.31 GiB | 262k | `gemma4` ✓ | Apache-2.0 |
| LFM2.5-24B-A2B | MoE 24B / 2.45B, 4/64 | 10 GQA (8×64) + 30 shortconv | 10880 | 1.33 GiB | **131072** | `lfm2moe` ✓ (nasze łatki AMD) | LFM Open v1.0 (< $10M przychodu) |
| Nemotron 3.5 Lightning 30B-A3B | MoE hybryda, 6/128 + shared | 6 GQA (2×128) + 23 Mamba-2 | **3264** | 0.40 GiB | 1M | `nemotron_h_moe` ✓, MTP jako osobny plik | OpenMDW-1.1 |
| GLM-4.7-Flash | MoE 31B / ~3B, 4/64 | 47× MLA (latent 576) | 28764 | 3.51 GiB | 202k | `deepseek2` ✓ | MIT |
| gpt-oss-20b | MoE 20.9B / 3.6B, 4/32 | 12 pełnych + 12 SWA (okno 128), 8×64 | 13056 | 1.60 GiB | 131072 | `gpt-oss` ✓, EAGLE3 GGUF | Apache-2.0 + policy |
| Mellum2.1-12B-A2.5B (kod) | MoE 12B / 2.5B, 8/64 | 7 pełnych + 21 SWA (4×128) | 7616 | 0.96 GiB | 131072 | `mellum` ✓ | Apache-2.0 |
| Qwen3.5-9B / Ornith-1.5-9B | gęsty 9.65B | 8 pełnych (4×256) + 24 GDN | 17408 (9216) | 2.12 GiB | 262k | `qwen35` ✓ | Apache / MIT |
| Ministral 3 14B / Devstral Small 2 24B | gęste | 40 pełnych (8×128) | **87040** | **10.6 GiB** | 262k / 393k | `mistral3` ✓ | Apache-2.0 |
| Qwen3.8-Flash-Next | MoE 125B / 6B + 51B n-gram + 4B MTP | 12 QSA (rzadka) + 36 GDN | ~24 KB f16 + indekser | ~3.4 GiB f16 | 262k | `qwen4exp` ✓, `--moe-cache-mib` | Qwen Community 1.0 |

Odrzucone z zasady: **MiniMax-H3** (to generator wideo+audio, a GGUF `minimax_h3_*_pruned` to DiT, nie LLM;
licencja wyklucza UE). **Phi-4-reasoning-vision-15B** (kontekst 16k). **Ministral 3 14B / Devstral Small 2 /
Granite 4.2-30B / K2-Horizon-7B / Jais-3-MoVA** (pełna atencja na wszystkich warstwach: 131k KV q8_0 to 10.6 GiB
(Mistral), 34 GB f16 (Granite), więc ≥131k nie mieści się z sensownymi wagami nawet na 24 GB; fitcalc: Devstral
na 3090 max 104k). **GLM-5.3-Flash** (320B/A18B; nawet REAP144 ma 45 GB w IQ2_XXS i pętli się poza Pythonem).
**Nemotron 3.5 Bolt 74B-A9B-24GB** (plik 22.0 GB; NVIDIA nie ma recepty na 24 GB, a nasze KLD to FAIL `[[nemotron-3-5-bolt-74b-a9b]]`).
**Hy-Memory-30B-A3B** (specjalista od pamięci, 96 KB/token). **empero „Qwen3.8-35B-A3B-Distill”** (nieoficjalny SFT Qwen3.6,
wątek „spam”, brak ewaluacji). **MiniCPM-V-4.7-35B-A3B** (ten sam szkielet co Qwen3.6, brak liczbowych benchmarków;
VLM). Brak „DeepSeek-V4-Flash distill” ≤ 35B poza SFT Qwen3.5-9B na 8k próbek (Jackrong) bez ewaluacji.

## 3. Jakość bazowa i jakość kwantów

| model | AA v4.3.2 | GPQA-D | SWE-bench V | LCB v6 | Terminal-Bench | źródło |
|---|---|---|---|---|---|---|
| Qwen3.8-Flash-Next | **40** | 91.7 | — (Pro 62.5) | 91.9 | — | [karta](https://huggingface.co/Qwen/Qwen3.8-Flash-Next), [AA](https://artificialanalysis.ai/models/qwen3-8-flash-next) |
| **Qwen3.8-27B** | **34** (xhigh) | 89.2 | — (Pro 61.7) | 90.3 | 2.1: 73.0 | [karta](https://huggingface.co/Qwen/Qwen3.8-27B), [AA](https://artificialanalysis.ai/models/qwen3-8-27b) |
| **Ornith-1.5-35B-A3B** | — (brak strony) | 89.2 (vendor) | **79** (vendor) | — | 2.1: 67.8 | [ornith.ai](https://ornith.ai/ornith_1_5.html) |
| Qwen3.6-27B | 21 | 87.8 | 77.2 | 83.9 | 2.0: 59.3 | [karta](https://huggingface.co/Qwen/Qwen3.6-27B) |
| **Qwen3.6-35B-A3B** | **18** | 86.0 | 73.4 | 80.4 | 2.0: 51.5 | [karta](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) |
| Gemma 4 26B-A4B | 17 | 82.3 | 17.4 (tabela Qwen) / 57.4 (tabela NVIDIA) | 77.1 | 2.0: 34.2 / 2.1: 37.2 | [karta 31B (tabela rodziny)](https://huggingface.co/google/gemma-4-31B-it), [AA](https://artificialanalysis.ai/models/comparisons/gemma-4-26b-a4b-vs-gpt-oss-20b) |
| Gemma 4 31B | 15 | 84.3 | 52.0 | 80.0 | 2.0: 42.9 | jw., [AA](https://artificialanalysis.ai/models/gemma-4-31b) |
| GLM-4.7-Flash | 15 (szac., strona „deprecated”) | 75.2 | 59.2 | 64.0 | — | [karta](https://huggingface.co/zai-org/GLM-4.7-Flash) |
| Gemma 4 12B | 14 | 78.8 | — | 72.0 | — | [AA](https://artificialanalysis.ai/models/gemma-4-12b) |
| Nemotron 3.5 Lightning | 13 | 75.4 | 51.6 | — | 2.1: 24.6 | [karta NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4), [AA](https://artificialanalysis.ai/models/nemotron-3-5-lightning) |
| Ornith-1.5-9B | — | 86.4 (vendor) | 70.6 (vendor) | — | 2.1: 46.2 | [karta](https://huggingface.co/ornith-ai/Ornith-1.5-9B) |
| Qwen3.5-9B | 11 | 81.7 | 53–60 (zależnie od harnessu) | 65.6 | 2.1: 21–27 | [karta](https://huggingface.co/Qwen/Qwen3.5-9B) |
| LFM2.5-24B-A2B | — (brak strony) | 74.4 | 51.0 | — | — (IFEval 96.75, BFCLv4 65.0) | [karta](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B) |
| gpt-oss-20b | 9 | 71.5 | 60.7 | — | 2.1: 15.2 | [OpenAI](https://deploymentsafety.openai.com/gpt-oss/full-evaluations) |
| Mellum2.1-12B-A2.5B (kod) | — | 64.6 | 47.0 | 82.0 | 2.1: 17.4 | [karta](https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking) |

Uwagi do jakości:
- **Ornith-1.5-35B** to fine-tune RL szkieletu Qwen3.5/3.6-35B-A3B (ta sama architektura). Liczby podaje tylko vendor,
  AA go nie ma. Społeczność używa go jako zamiennika Qwen3.6 (GGUF 3.8 mln pobrań, LP 32 GB: mediana 142 t/s). Są też
  uwagi „overthinks” i „Qwen3.6 bardziej niezawodny na moim repo” (LP ornith1-5). Stawiam go **#2, nie #1**, dopóki nie
  zmierzymy J2 sami.
- **Gemma 4 26B-A4B** ma AA ≈ Qwen3.6-35B (17 vs 18), ale jest słaba agentowo (SWE-V 17.4 w tabeli Qwen; LP: „insufficient
  for agentic”, nie zdała testu EPAM). Wybór „szybki/czat/wizja”, nie „agent”.
- **LFM2.5-24B** jest najlepszy w IFEval/BFCL, ale słabszy w wiedzy i kodzie, a jego kwanty są kruche. Nasze KLD (do własnego
  Q8_0, wikitext 512): QAD-Q4_0 0.203, Q4_K_M 0.201, Q5_K_M 0.124, przy Qwen U3 0.0265 w tym samym protokole
  (`09-chmura-5060ti.md:174-179`). Do tego licencja z progiem $10M.

| kwant (opublikowane) | KLD / zadania | źródło |
|---|---|---|
| Qwen3.8-27B UD-Q4_K_XL / UD-Q3_K_XL / AP-Q3_K_XL | 0.0153/0.0226; 0.039/0.0635; 0.040/0.056 (wiki/czat, nasze) | `16e-kwanty-kld.md:133-144` |
| Qwen3.8-27B GSQ IQ3_XXS / IQ2_S (10.1 / 9.3 GB) | GPQA-D 88.9 / 86.4 (BF16 89.9), LCB 84.6 / 82.3 | [ISTA-DASLab](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF) |
| Qwen3.8-27B EXL3-SC 3.0 / 4.0 bpw | mean KLD 0.0257 @~9.1 GiB vs UD-Q3_K_XL 0.0209 @12.1; 0.0062 @12.2 vs Q4_K_XL 0.0051 @16.0 (ich protokół) | `32c-sage-exl3-spark-afd.md:61` |
| Qwen3.6-35B-A3B | tylko wykres Unsloth („najlepsze w 21 z 22 rozmiarów”); NVFP4 = BF16 w MMLU-Pro/GPQA | [unsloth qwen3.6](https://unsloth.ai/docs/models/qwen3.6) |
| Gemma 4 26B / 31B / 12B UD-Q4_K_XL (z QAT) | KLD 0.098 / 0.014 / 0.133; naiwne Q4_0 z QAT: 0.361 / 0.094 / 0.507 | [unsloth gemma-4/qat](https://unsloth.ai/docs/models/gemma-4/qat) |
| Mellum2.1 Q8_0 / Q6_K / Q4_K_M / MXFP4 | KLD 0.008 / 0.020 / 0.075 / 0.115 | [JetBrains GGUF](https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking-GGUF) |
| Qwen3.8-Flash-Next UD-Q2_K_XL / Q3_K_XL / Q4_K_XL | KLD 0.225 / 0.107 / 0.047 | [unsloth qwen3.8-next](https://unsloth.ai/docs/models/qwen3.8-next.md) |
| Bonsai 2 27B (PQ2_0) / Saluki | nasze KLD-wiki 0.352 / 0.257 (oblewa J1); vendor: 98.2% FP16 na 14 benchmarkach; LP 3080: LCB 32/50 vs IQ2_XXS 16/50 | `16e:143-144`, [prism-ml](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) |

## 4. Karty: top 3 + alternatywy

Wszystkie wiersze: `fitcalc` (ub 512, zapas 512 MiB, g = preset karty, RAM DDR5 2ch). KV: q4_0 dla rodziny Qwen,
q8_0 dla Gemma/LFM/Nemotron/gpt-oss/Mellum (Gemma źle znosi q4_0 KV wg LP; LFM to nasza decyzja). „n” = `--n-cpu-moe`.
„max” = największy `-c`, przy którym szczyt po prompcie długości `-c` + 512 MiB mieści się w VRAM, przy tym n.
Spekulacja: zysk z publikacji, nie z modelu.

### RTX 3080 10 GB (10240 MiB, 760 GB/s, Ampere) — MoE wygrywa (żaden gęsty ≥ 27B nie przechodzi J1)

| # | model | kwant (plik) | n / RAM | max `-c` | szczyt @131k | t/s 0/64k/131k | jakość | spekulacja | uwagi |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.6-35B-A3B** | UD-IQ4_XS 18.2 GB | 28 / 10.5 GB | 143k | 9530 | 64 / 55 / 47 | AA 18, SWE-V 73.4 | MTP w pliku (`unsloth/…-MTP-GGUF`): n=2, 1.15–1.2×; z ekspertami w RAM zysk mały lub ujemny (LP numsu) → lookup | LM 3080: Qwen3.6 mediana 35.4 t/s przy ctx 188k (IQ4_K_M) |
| 2 | Ornith-1.5-35B-A3B | Q4_K_M 21.7 GB | 29 / 14.0 GB | 131k | 9696 | 60 / 52 / 45 | vendor SWE-V 79 / GPQA 89.2 | MTP w GGUF ma akceptację ~0.13 → wyłączyć; lookup | RAM ≥ 32 GB; jakość niezweryfikowana |
| 3 | Gemma 4 26B-A4B | UD-IQ4_XS 13.6 GB (lub UD-Q4_K_XL z QAT, +0.65 GB) | 22 / 7.9 GB | 143k | 9409 | 53 / 39 / 33 | AA 17, słabsza agentowo | MTP sidecar zjada VRAM (n 29) → raczej bez | KV q8_0, bez `--swa-full` |

Alternatywy: **LFM2.5-24B UD-Q3_K_XL** (n 15, 3.6 GB RAM, 94/63/47 t/s, 128k = limit modelu; GPQA 74, kruche kwanty,
licencja). **Nemotron Lightning Q4_0** (n 35, 57/52/48, do 163k, AA 13). **Mellum2.1 Q4_K_M** (prawie cały na GPU,
135/88/67; tylko kod). **Bonsai 2 27B PTQ1_0** (5.95 GB, mieści 131k; potrzebuje forka PrismML; nasze KLD 0.352).
**Qwen3.8-27B**: na 10 GB nic ≥ IQ3 nie mieści 131k.

### RTX 3060 12 GB (12288 MiB, 360 GB/s) — MoE wygrywa

| # | model | kwant | n / RAM | max `-c` | szczyt @131k | t/s 0/64k/131k | spekulacja | dowód społeczności |
|---|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.6-35B-A3B** | UD-IQ4_XS | 21 / 7.8 GB | 137k | 11666 | 52 / 40 / 32 | MTP n=3: 62.4 → 75.1 t/s na 3060 przy 64k ([tanhaien](https://github.com/tanhaien/qwen-moe-benchmark)) | LP 94edf301: Q4_K_M ncmoe 25 50–58 t/s, prefill 800–1190 |
| 2 | Ornith-1.5-35B-A3B | Q4_K_M | 24 / 11.6 GB | 139k | 11633 | 53 / 40 / 33 | graft MTP (BigBang) zamiast stockowego | Ajay9o9: 131k, 47.6 @32k, 30.6 @112k |
| 3 | Gemma 4 26B-A4B | UD-IQ4_XS | 14 / 5.1 GB | 133k | 11694 | 45 / 28 / 21 | — | Ajay9o9: Q6 ncmoe 20 ~39 t/s |

Bez RAM-u na ekspertów (wszystko w VRAM): **Gemma 4 12B UD-Q4_K_XL** (236k, 32/23/19 t/s; z MTP sidecar 139k, 12B
MTP ~1.97× na 3090 wg [PR #24282](https://github.com/ggml-org/llama.cpp/pull/24282)) albo **Ornith-1.5-9B Q6_K**
(225k, 35/27/21; vendor GPQA 86.4). Oba gęste i wyraźnie słabsze od 35B-A3B. Nemotron Lightning: n 28, 47/41/36, do 194k.

### RTX 4070 Ti 12 GB (12282 MiB, 504 GB/s) — MoE wygrywa

| # | model | kwant | n / RAM | max `-c` | szczyt @131k | t/s 0/64k/131k | dowód |
|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.6-35B-A3B** | UD-IQ4_XS | 21 / 7.8 GB | 131k | 11758 | 69 / 54 / 44 | 4070 S 12 GB (ik_llama, 17 GB APEX): 64.0 / 60.7 / 55.3 / 50.9 t/s przy 32/64/128/258k |
| 2 | Ornith-1.5-35B-A3B | Q4_K_M | 24 / 11.6 GB | 133k | 11725 | 65 / 51 / 42 | — |
| 3 | Gemma 4 26B-A4B | UD-IQ4_XS | 15 / 5.4 GB | 143k | 11441 | 59 / 38 / 29 | — |

Gęste w całości w VRAM: Ornith-1.5-9B Q6_K 219k, 58/42/33; Gemma 4 12B 236k, 52/35/29.
LM: na 4070 Ti nie ma runów docelowych modeli (0 w próbce).

### RTX 4060 Ti 16 GB (288 GB/s) i RTX 5060 Ti 16 GB (448 GB/s) — MoE wygrywa

| # | model | kwant | n / RAM | max `-c` 4060 Ti / 5060 Ti | szczyt @131k | t/s 4060 Ti | t/s 5060 Ti | spekulacja | dowód |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.6-35B-A3B** | UD-Q3_K_XL 17.2 GB | 8 / 2.8 GB | 151k / 145k | 15560 | 68 / 46 / 34 | 95 / 66 / 50 | MTP w pliku: n 12, +15–20% | LM 5060 Ti: mediana 115.9 (IQ3_XXS/IQ4_NL, 150k) |
| 1′ | jw. całość w VRAM | UD-IQ3_XXS 14.1 GB | 0 | 168k / 162k | 15322 | 89 / 54 / 39 | 132 / 81 / 59 | jw. (n 3–4) | LM 4060 Ti: IQ3_XXS 60.2 t/s, 262k |
| 2 | Ornith-1.5-35B-A3B | Q4_K_M | 15 / 7.3 GB | 139k / 133k | 15739 | 66 / 44 / 34 | 84 / 60 / 47 | — | LP: 4070 Ti S 16 GB ncmoe 15 → 86–91 t/s @65k |
| 3 | Gemma 4 26B-A4B | UD-IQ3_XXS 11.4 GB, całość w VRAM | 0 | 190k / 186k | 14451 | 80 / 34 / 23 | 118 / 52 / 35 | MTP sidecar (n 3–4): 1.35× na 3090 | LP 5060 Ti: 99 t/s ciągle, 49 przy 108k; MXFP4 95.2 @65k |

Alternatywy: **Nemotron Lightning Q4_0** (n 14, 4.3 GB RAM): 61/49/41 (4060 Ti), 80/66/56 (5060 Ti), do 192k. Ma
najmniejszy spadek z głębokością (6 warstw atencji × 2 głowy), ale niższą jakość (AA 13). **LFM2.5-24B QAD-Q4_0**
w całości w VRAM: 180/69/43 (5060 Ti), 128k, z zastrzeżeniami jakości i licencji. **gpt-oss-20b**: 128k, 135/55/35.

**Qwen3.8-27B na 16 GB (opcja „własny kwant”, niezweryfikowana):**
- Bez MTP 131k mieści się, jeśli wagi na GPU ≤ 11.7 GB (pewny, ub 512, g 18K) albo ≤ 12.4 GB (ub 256, g 14K).
  Z MTP (T) próg to ≤ 8.9 GB. UD-Q3_K_XL bez tensorów MTP ma 12.24 GB, AP-Q3_K_XL podobnie.
- (a) **GGUF z alokacją bitów EXL3-SC** przez `llama-quantize --tensor-type`: −5–10% bajtów przy tym samym KLD
  `[INFERENCE]` (`32c:115`). Wychodzi ~11.2–11.7 GB. fitcalc dla 11.2 GB: 5060 Ti max 145k (172k przy ub 256),
  32 / 22 / 16 t/s plain. 4060 Ti 22 / 15 / 11, czyli **oblewa J4**.
- (b) **exllamav3 SC_3.00bpw_H4** (~9.1 GiB wag, embedding na CPU): KLD ≈ UD-Q3_K_XL w protokole turboderpa. Mieściłby
  ≥131k `[INFERENCE]`, ale potrzebuje drugiego silnika, a jego model pamięci i prędkość są niezmierzone.
- **AMD (16 GB Radeon):** exllamav3 na gfx1100 dawał historycznie ~15 t/s (`32c:126`). Jedyny raport ROCm-portu
  (XTX, EXL3 3.5 bpw + DFlash2: 157 / 107 t/s przy 2k / 99k, [LP rx-7900-xtx](https://llamaperf.com/gpu/rx-7900-xtx))
  jest pojedynczy i niezweryfikowany.
- Oba warianty wymagają naszego KLD (protokół 16e) przed polecaniem. Nawet wtedy na 16 GB 27B (≤ 22 t/s @64k) przegrywa
  prędkością z Qwen3.6-35B (66 t/s) przy wyższej jakości bazowej (AA 34 vs 18). To wybór „jakość ponad szybkość”, nie domyślny.
- **12 GB:** 27B przy 131k wymaga ≤ 7.5 GB wag, czyli ~2.2 bpw. Brak danych SC poniżej 3.0 bpw; Saluki/Bonsai oblewają
  J1. Na 12 GB 27B nadal odpada.

### Mac 16 GB (M4 120 GB/s / M5 153 GB/s; GPU ~10.7 GiB domyślnie, ~12 GiB po `iogpu.wired_limit_mb`) — wszystko `[SZACUNEK]`

Pamięć jest wspólna: eksperci „w RAM” nie zwalniają miejsca. Model + KV + system muszą zmieścić się w 16 GB.

| # | model | kwant | ustawienie | max `-c` | t/s 0/64k/131k (M5, wired 12 GiB) | M4 domyślnie | uwagi |
|---|---|---|---|---|---|---|---|
| 1 | Qwen3.6-35B-A3B | UD-IQ2_M 11.5 GB | wired 12 GiB, n 5 (1.2 GB na CPU) | 131k | 48 / 29 / 21 | n 11, 38 / 23 / 16 | LP M4 mini: 38 t/s; 2-bit bez opublikowanego KLD, Unsloth odradza < Q2_K_XL do agentów |
| 2 | LFM2.5-24B-A2B | UD-IQ3_XXS 9.0 GB | wired 12 GiB | 128k | 72 / 25 / 15 | n 5, 58 / 20 / 12 | kruche kwanty (nasze KLD Q4 ~0.2), licencja |
| 3 | Ornith-1.5-9B / Qwen3.5-9B | Q4_K_M 5.8 GB | domyślnie | 256k | 21 / 14 / 11 | 16 / 11 / 9 | najlepsza jakość/GB, ale **oblewa J4** (≥ 20 t/s @64k) |

Kod: Mellum2.1 Q4_K_M (8.1 GB): 63 / 28 / 19 (LP M4 16 GB: ~60 t/s @130k na Q8). Werdykt: **na 16 GB Maca nie ma
modelu, który spełnia jakość + 131k + 20 t/s z zapasem.** Qwen3.6 IQ2_M jest najbliżej. Zmierzyć przed polecaniem.

### RTX 3090 / 4090 / RX 7900 XTX 24 GB — gęsty wygrywa jakością, MoE prędkością

| # | model | kwant | n | max `-c` (3090) | szczyt @131k | t/s 3090 | t/s 4090 | t/s XTX | spekulacja | jakość |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.8-27B** | UD-Q4_K_XL 17.56 GB, ramię T | 0 | 139k (T) / 235k (plain) | 23630 (walid.) | **zmierzone T**: czat 93.3, po 60k 56.7; plain 43 / 33 / 27 `[SZAC.]` | ~1.1× 3090 | **zmierzone**: 109–114.8 czat | MTP + lookup + GPU verify (nasz fork) | AA 34, KLD 0.0153 |
| 2 | Ornith-1.5-35B-A3B | Q4_K_M 21.7 GB | 0 | 211k (plain) | 22891 | 158 / 117 / 93 | 189 / 136 / 106 | 176 / 127 / 100 | stock MTP bezużyteczny; graft BigBang 131 → 169 (LP) | vendor |
| 3 | Qwen3.6-35B-A3B | UD-Q4_K_M 22.7 GB (MTP-GGUF) | 0 plain / 2 z MTP | 164k / 133k | 23554 | 138 / 106 / 85 | 164 / 122 / 97 | 150 / 113 / 90 | MTP n=2 1.15–1.2× | AA 18 |

Dalej: **Gemma 4 26B-A4B UD-Q4_K_XL** (262k plain, 180k z MTP sidecar; 136 / 79 / 59 na 3090; LM mediana 138, LP
143) to najlepszy MoE do wizji i czatu. **Nemotron Lightning Q4_0 + MTP sidecar**: 231k, 169 / 139 / 118 i najmniejszy
spadek z głębokością. **Gemma 4 31B** nie mieści 131k z MTP nawet w UD-Q3_K_XL (90k). Plain mieści dokładnie 131k
z zapasem 518 MiB i daje 47 / 24 / 17 t/s: na granicy bramek, a słabszy (AA 15) i wolniejszy od MoE, więc odrzucam.
**Qwen3.8-27B UD-Q4_K_M** daje 162k z MTP (o 23k więcej) kosztem ~+25% KLD (PLAN-NV-V2 §3).

**MoE vs gęsty na 24 GB:** plain MoE jest 3.2–3.5× szybszy (106–117 vs 33 t/s @64k na 3090). Przeciw naszemu T
(56.7 po 60k) przewaga MoE spada do ~2×, a jakość bazowa jest wyraźnie niższa (AA 18 vs 34, GPQA 86 vs 89.2,
LCB 80.4 vs 90.3). Rekomendacja domyślna zostaje: 27B. MoE pokazujemy jako „tryb szybki”.

### RTX 5090 32 GB (32607 MiB, 1792 GB/s)

| # | model | kwant | max `-c` | szczyt @131k | t/s 0/64k/131k plain `[SZAC.]` | spekulacja | uwagi |
|---|---|---|---|---|---|---|---|
| 1 | **Qwen3.8-27B** | UD-Q6_K 21.98 GB, T | 221k (T) | 27959 (fitcalc; plan dla 204800: 31321) | 64 / 52 / 43 | MTP: ~×1.8–2 `[SZACUNEK]`; LP 5090 Q4_K_M + MTP n=3: 93.8 / 68.8 / 55.3 @4k/65k/128k | PLAN-NV-V2 faza 2 |
| 2 | Ornith-1.5-35B-A3B | Q5_K_M 25.35 GB | 262k | 26558 | 220 / 175 / 145 | — | Q6_K 29.2 GB: 254k, 211 / 169 / 141 |
| 3 | Gemma 4 31B (gęsty) | UD-Q4_K_XL 18.8 GB | 201k plain / 141k z MTP | 27604 / 31050 | 71 / 40 / 30 | MTP sidecar 2.26× (3090, PR #24282) | AA 15 < Qwen3.6-35B; KV 43.5 KB/tok q8_0 |

Zamiast #3 dla agentów: **Qwen3.6-35B-A3B UD-Q5_K_XL + MTP** (238k, 198 / 161 / 135).

### Qwen3.8-Flash-Next (125B-A6B, AA 40) — tylko z dużym RAM-em

Jedyny lokalny model wyraźnie lepszy od Qwen3.8-27B. Potrzebuje 75 GB+ RAM/unified (UD-IQ1_S 72.5 GB, KLD 0.396;
UD-Q3_K_XL 90 GB, KLD 0.107). Prędkości:
- Strata: XTX + 96 GB DDR5 ~80 t/s przy 98k (`21g-nowe-silniki.md:269`); 5070 12 GB + 64 GB RAM 53–94 t/s
  ([compute-market](https://www.compute-market.com/blog/strata-qwen-3-8-flash-next-12gb-gpu-hardware-guide-2026)).
- llama.cpp z `--moe-cache-mib` (jest w bazie forka): 5090 Q4_0 67.8 t/s, 4090 40.7 (`[[llama-moe-cache-mib]]`).
- Goły `--n-cpu-moe` jest 3–5× wolniejszy: XTX IQ4_XS 17.5 t/s; 3060 + 16 GB RAM 1.4–2.1 t/s (LP).

Licencja Qwen Community 1.0 wymaga osobnej licencji dla „AI Work Assistant”/MaaS. Dla użytkownika z ≥ 96 GB RAM to
lepszy wybór niż wszystko powyżej. Do produktu tylko po decyzji prawnej.

## 5. Gdzie MoE bije gęsty

| klasa | zwycięzca | dlaczego (liczby z §4) |
|---|---|---|
| 10–12 GB | **MoE** (Qwen3.6/Ornith 35B-A3B z `--n-cpu-moe`) | gęste ≥ 27B nie mieszczą 131k z J1. Gęste 9–12B mają AA 11–14 i 23–42 t/s @64k. MoE 35B-A3B ma AA 18 i 40–55 t/s @64k |
| 16 GB | **MoE** | Qwen3.6-35B UD-Q3_K_XL 46–66 t/s @64k. Gęsty 27B w niestandardowym kwancie: 15–22 t/s (4060 Ti oblewa J4) |
| Mac 16 GB | MoE (warunkowo) | 9B gęsty ≤ 14 t/s @64k; Qwen3.6 IQ2_M ~29 |
| 24 GB | **gęsty jakością, MoE prędkością** | 27B Q4_K_XL + nasze MTP: 56.7 t/s po 60k, AA 34. Ornith/Qwen3.6: 106–117 t/s @64k, AA 18 |
| 32 GB | gęsty jakością | 27B Q6_K 200k+; MoE Q5 ~3× szybszy |

## 6. Spekulacja naszym stosem: co działa dla których modeli

| model | MTP | osobny drafter | lookup (`LLAMA_SPEC_LOOKUP`) |
|---|---|---|---|
| Qwen3.8-27B | ✓ w pliku, nasze T (zmierzone) | DFlash2 (z-lab) — nie bije MTP (`[[drafter-dflash]]`) | ✓ |
| Qwen3.6-35B-A3B | ✓ `unsloth/…-MTP-GGUF` / `ggml-org/…-MTP-GGUF`, n=2: 1.15–1.2×, akceptacja 83% (n=2) → 50% (n=4) | DFlash z-lab (GGUF społeczności) | ✓ |
| Ornith-1.5-35B / 9B | w GGUF (`nextn 1`), ale akceptacja ~0.13 → off | DFlash Ornith (tylko vLLM/SGLang) | ✓ |
| Gemma 4 (12B / 26B / 31B) | sidecar `mtp-gemma-4-*-Q8_0.gguf` (`gemma4-assistant`, jest w forku): 1.97× / 1.35× / 2.26× (3090, PR #24282) | DSpark gemma4-12b (deepseek-ai) | ✓ |
| Nemotron Lightning | sidecar `mtp-…-Q8_0.gguf` (2.18 GB) — zysk niezmierzony w llama.cpp | DSpark/DFlash NVFP4 (vLLM) | ✓ |
| gpt-oss-20b | — | EAGLE3 GGUF w `ggml-org/gpt-oss-20b-GGUF` | ✓ |
| LFM2.5-24B | — (DSpark „coming soon”) | — | ✓ (`24d-lfm-lookup.md`) |

Przy ekspertach w RAM zysk ze spekulacji maleje: weryfikacja k tokenów dotyka więcej ekspertów, a ich odczyt idzie z RAM-u.
LP numsu na 8 GB: MTP 29–40 t/s (niestabilne) vs 35–38 plain. Domyślnie off przy `--n-cpu-moe`, z wyjątkiem pomiaru
3060 (+20%).

## 7. Co zmierzyć zanim to trafi do produktu (CPU najpierw)

1. KLD (protokół 16e, CPU) dla Qwen3.6-35B-A3B UD-Q3_K_XL / UD-IQ4_XS / UD-IQ3_XXS i Ornith-1.5-35B Q4_K_M do BF16.
   Dziś dla MoE nie mamy żadnej liczby jakości kwantu.
2. J2 (PL/EN czat + edycja kodu) Ornith vs Qwen3.6, bo ranking #1/#2 opiera się na deklaracjach vendora.
3. Jedna karta 12 GB (3060) z `--n-cpu-moe` przy 131k, RAM DDR4 vs DDR5, TTFT 131k. Prefill przez PCIe to największa
   niewiadoma.
4. Gemma 4 26B: spadek t/s z głębokością przy KV q8_0 vs f16 (model przewiduje 2× spadek do 64k; LP 5060 Ti: 99 → 49 przy 108k).
5. Port alokacji EXL3-SC do GGUF (≤ 11.7 GB) i KLD. Tylko to może dać Qwen3.8-27B z J1 na 16 GB.

## 8. Reprodukcja

```
fitcalc.py unsloth/Qwen3.6-35B-A3B-MTP-GGUF:Qwen3.6-35B-A3B-UD-IQ4_XS.gguf --card 3080 --arm plain --n-cpu-moe 28 --ctx 131072
fitcalc.py unsloth/gemma-4-26B-A4B-it-GGUF:gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf --card 3090 --arm plain --kv q8_0 \
           --draft unsloth/gemma-4-26B-A4B-it-GGUF:MTP/mtp-gemma-4-26B-A4B-it-Q8_0.gguf
fitcalc.py <gguf> --card mac16w --arm plain --ram-bw 45 --depth 0,65536,131072
```
Nagłówki pobrane do `/tmp/ms/hdr/*.json` (68 plików GGUF, tylko range requests). Siatka: 11 kart × 59 kwantów ×
{z / bez spekulacji}, n = najmniejsze `--n-cpu-moe` dające ≥ 131k (albo limit modelu).

## 9. Źródła

Lokalne: `PLAN-NV-V2.md` §1–3; `27-3090-final.md:100-103,200-232`; `31-4060ti.md:19,59-64`; `31-5060ti.md:10,40`;
`31-4070ti.md:11`; `31-3060-3080.md:9-10,80`; `16e-kwanty-kld.md:133-144`; `09-chmura-5060ti.md:174-179`;
`04-wykrywanie-sprzetu-i-dobor-modeli.md:196-347`; `21g-nowe-silniki.md:205,269`; `32c-sage-exl3-spark-afd.md:61,114-148`;
`wiki/modele/*`; kod forka `~/wt/cuda-topka2/src/models/{gemma4,gemma4-assistant,qwen35moe,lfm2moe,nemotron-h-moe,mellum}.cpp`,
`src/llama-kv-cache-iswa.cpp:73`, `common/common.h:175-186`.

HF (API `?blobs=true`, nagłówki GGUF): `unsloth/{gemma-4-26B-A4B-it,gemma-4-31B-it,gemma-4-12b-it,LFM2.5-24B-A2B,Qwen3.6-35B-A3B(-MTP),Qwen3.8-27B,Qwen3.5-9B,gpt-oss-20b,GLM-4.7-Flash,Ministral-3-14B-Instruct-2512,Devstral-Small-2-24B-Instruct-2512,MiniMax-H3,Qwen3.8-Flash-Next}-GGUF`,
`LiquidAI/LFM2.5-24B-A2B-GGUF`, `ggml-org/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-GGUF`, `ornith-ai/Ornith-1.5-{9B,35B-A3B}-GGUF`,
`JetBrains/Mellum2.1-12B-A2.5B-Thinking-GGUF`, `openbmb/MiniCPM-V-4.7-35B-A3B-gguf`, `prism-ml/Ternary-Bonsai-2-{9B,27B}-gguf`,
`google/gemma-4-12B-it-qat-q4_0-gguf`, `lmstudio-community/gemma-4-26B-A4B-it-QAT-GGUF`.

Karty i benchmarki: [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) · [Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next) ·
[Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) · [Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) ·
[unsloth Qwen3.6-35B-A3B-MTP](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF) · [Ornith-1.5](https://ornith.ai/ornith_1_5.html) ·
[Gemma 4 31B (tabela rodziny)](https://huggingface.co/google/gemma-4-31B-it/resolve/main/README.md) · [unsloth Gemma 4 QAT KLD](https://unsloth.ai/docs/models/gemma-4/qat) ·
[Gemma 4 MTP blog](https://blog.google/innovation-and-ai/technology/developers-tools/multi-token-prediction-gemma-4/) ·
[llama.cpp PR #24282 (MTP Gemma 4)](https://github.com/ggml-org/llama.cpp/pull/24282) · [LFM2.5-24B-A2B](https://huggingface.co/LiquidAI/LFM2.5-24B-A2B) ·
[Nemotron 3.5 Lightning NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4) · [GLM-4.7-Flash](https://huggingface.co/zai-org/GLM-4.7-Flash) ·
[gpt-oss eval](https://deploymentsafety.openai.com/gpt-oss/full-evaluations) · [Mellum2.1 GGUF (KLD)](https://huggingface.co/JetBrains/Mellum2.1-12B-A2.5B-Thinking-GGUF) ·
[MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3) · [Bonsai 2 27B](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf) ·
[ISTA GSQ-RCO Qwen3.8-27B](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF) · [AA small open](https://artificialanalysis.ai/models/open-source/small).

Społeczność: LocalMaxxing API `/api/leaderboard` (2026-10-20, peer Res32dLocalmaxxing; bez licencji na republikację wierszy) ·
[llamaperf 12 GB](https://llamaperf.com/best/local-llm-for-12gb-vram) · [16 GB](https://llamaperf.com/best/local-llm-for-16gb-vram) ·
[24 GB](https://llamaperf.com/best/local-llm-for-24gb-vram) · [32 GB](https://llamaperf.com/best/local-llm-for-32gb-vram) ·
[ornith1-5](https://llamaperf.com/model/ornith1-5) · [m4-16gb](https://llamaperf.com/gpu/m4-16gb) · [rx-7900-xtx](https://llamaperf.com/gpu/rx-7900-xtx) ·
[Ajay9o9 runs-on-a-3060](https://raw.githubusercontent.com/Ajay9o9/runs-on-a-3060/main/RESULTS.md) ·
[shiqikuangsan31 Qwen3.6 12 GB](https://github.com/shiqikuangsan31/Qwen3.6-35B-12GB-VRAM-Guide) ·
[tanhaien qwen-moe-benchmark](https://github.com/tanhaien/qwen-moe-benchmark) · [numsu Qwen3.6 8 GB](https://github.com/numsu/Qwen3.6-A3B-8GB-llama.cpp) ·
[tsarihan 5090 playbook](https://github.com/tsarihan/qwen3.8-27b-rtx5090-playbook) · [mberatsanli Qwen3.8 16 GB](https://raw.githubusercontent.com/mberatsanli/qwen38-27b-local/main/README.md).
