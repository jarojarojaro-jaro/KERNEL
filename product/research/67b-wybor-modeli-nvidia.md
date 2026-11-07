# 67b: Ostateczny wybór modeli na karty NVIDIA (8–32 GB), przepisy Enigmy (2026-11-07)

Autor: ModelSelect67 (Opus). Pobierane były wyłącznie API HF, karty modeli i nagłówki GGUF (range requests). Liczby VRAM pochodzą z żywych logów kampanii 67 (`NvVast67`, upstream b11856/b12110, `-lv 4`), pobranych 2026-11-07 o 16:30–17:00. Poprzednik: [33-modele-na-karty.md](33-modele-na-karty.md) (2026-10-20). Zgodnie z KONWENCJE §6 przegląd HF to tylko **delta** od raportu 33.

Oznaczenia: `[SZACUNEK]` to wynik z modelu (fitcalc / model pamięci poniżej), `[INFERENCE]` to wniosek bez pomiaru, „zmierz.” to pomiar kampanii 67. Kontekst podany jako „k” oznacza wielokrotność 1024 (256k = 262 144).

## 0. Werdykt: tabela na klasę VRAM

Silnik to upstream llama.cpp CUDA b12110 (Enigma v0.9.0) ze standardowymi flagami. Kwanty są wyłącznie opublikowane. Dla Qwena KV q4_0 to nasz przyjęty standard (wiki `kwanty-gguf`). Zapas liczony jest od **sumy CUDA** (cudaMemGetInfo), a nie od sumy z nvidia-smi: przy 4090 to 24 082, a nie 24 564 MiB.

„Linux” oznacza 128 MiB zapasu. „Pulpit” oznacza dodatkowe 768 MiB na kompozytor (Windows i Linux z monitorem; host 5060 Ti z włączonym wyświetlaczem zużywał w spoczynku 339 MiB).

**Kierunek użytkownika (2026-11-07, w trakcie raportu):** Gemma 4 12B odrzucona („zły model”). Domyślny wybór dla każdej klasy ≥ 8 GB to rodzina Qwen3.8-27B w małych kwantach oraz LFM2.5. Qwen3.6-35B-A3B zostaje jako opcja MoE. KLD to E1 (do Qwen BF16, wiki / PL); im mniejszy, tym lepiej.

| klasa (karty) | wybór | kwant, KV, flagi | ctx | wolne VRAM @ctx | t/s (decode) | jakość, licencja, koszt |
|---|---|---|---|---|---|---|
| **32 GB** (5090) | **Qwen3.8-27B** | UD-Q6_K 20.47 GiB, KV q4_0, MTP n=3, ub 1024 | **262 144 – mieści się** | 2.9 GiB (zmierz. load 29 158) | plain ~64 `[SZACUNEK]`; MTP ~90–100 `[INFERENCE]` (LP 5090 Q4_K_M+MTP n=3: 93.8 @4k / 68.8 @65k) | Q6 ≈ podłoga Q8; Apache-2.0. KV q8_0 + MTP n≥2 przy 262k się nie mieści |
| **24 GB** (3090, 4090) | **Qwen3.8-27B** | **UD-Q4_K_M** 15.33 GiB, KV q4_0, MTP n=2, ub 512, `--spec-draft-n-ubatch 64` | **262 144 – mieści się** | 3090 1278 / 4090 1105 MiB (także z pulpitem) | 3090 upstream+MTP ~52–55 `[INFERENCE z R56: 51.7 przy n=4]`; plain 43.1 zmierz. | jak produkcja XTX (Q4_K_M @262k). UD-Q4_K_M nie ma naszego KLD (UD-Q4_K_XL 0.0122 wg 15e) – do zmierzenia |
| 24 GB wariant „Linux bez monitora” | Qwen3.8-27B | UD-Q4_K_XL, MTP n=1, ub 256, ubd 64 | 262 144 | 4090 402 MiB (zmierz. load 23 680) | jw. | wymaga testu fill; z portem lean n=2 i ~1 GiB zapasu |
| **16 GB** (4060 Ti, 5060 Ti, 4070 Ti S, 4080, 5070 Ti, 5080) | **Qwen3.8-27B GSQ-RCO IQ3_XXS-mtp** (ISTA-DASLab, Apache-2.0) | 9.73 GiB, KV q4_0, MTP n=1, ub 256, ubd 64 | **MTP: 4060 Ti 217 088, 5080 208 896, 5060 Ti z monitorem 200 704**; z portem lean 225–245k; **bez MTP: 262 144 mieści się** (586 / 340 / 158 MiB) | ≥ 128 MiB | 5060 Ti ~50 z MTP `[INFERENCE: E1 5060 Ti MTP n=2 IQ3_S 50.0, U3 51.7]`; 4060 Ti ~32, 5080 ~85 `[INFERENCE]` | KLD 0.119 / 0.108 (Swift o tej samej alokacji; ISTA niezmierzony, vendor GPQA 88.9 vs 89.9 BF16). Koszt kontekstu: UD-Q3_K_XL (0.039) mieści tylko 164k bez MTP lub 136k z MTP i portem lean |
| 16 GB alt. „jakość” | Qwen3.8-27B | UD-Q3_K_XL (= bajty AP-Q3_K_XL), bez MTP, ub 256 | 4060 Ti 167 936 / 5080 159 744 | 147–303 MiB | plain: 5060 Ti 28.7 zmierz., 4060 Ti 18.4 (R31) | KLD 0.039 / 0.032. MTP ≥ 131k na stock się nie mieści (n=1: 1 MiB) |
| 16 GB alt. 262k + MTP | Saluki-MTP lub Swift/ISTA IQ2_S-mtp | Saluki n=2 (stock); IQ2_S n=1 (lean) | 262 144 | 762 / 565 MiB (4060 Ti) | – | KLD 0.257 / 0.164 – za drogo w jakości jak na 16 GB |
| 16 GB alt. LFM | LFM2.5-24B-A2B | Q4_K_M 13.53 GiB, **KV q8_0**, ub 512, wszystko w VRAM | 131 072 (limit modelu) | 4060 Ti 128 MiB; 5080 −118 (wtedy `--n-cpu-moe 3`) | 5060 Ti upstream 147.7 zmierz. (R09) | licencja LFM < US$10M przychodu; KLD Q4_K_M 0.201 do własnego Q8 |
| **12 GB** (3060, 4070; 3080 12 GB / 4070 Ti / 5070 przy 131 072) | **Saluki 27B + MTP** (Kujira graft, 8.35 GB) | IQ2-mix, KV q4_0, MTP n=1, ub 256, ubd 64 | **135 168** (4070 Ti / 5070 / 3080-12: 131 072); z portem lean 151 552 | 304 MiB | 3060 nasz fork 38.2 (MTP n=2, 170 W); karta Kujiry: 3080 12 GB 41.2 → 66.2; upstream 3060 `[INFERENCE]` ~33 | KLD 0.257 / 0.320. **Licencja Saluki od 2026-11-05 to CC BY-NC 4.0** (commit „Switch the license to CC BY-NC 4.0”); do produktu tylko z licencją od Conway |
| 12 GB alt. licencyjnie czysty | Bonsai 2 27B (PrismML) | oficjalny upstream **Q2_0** 7.63 GB (Apache-2.0), bez MTP, ub 256 | 221 184 | ≥ 128 MiB | 3060 upstream 33.15, nasz fork 35.5 zmierz. | KLD 0.352 / 0.508, błędy po polsku |
| 12 GB alt. LFM | LFM2.5-24B-A2B | Q4_K_M, KV q8_0, `--n-cpu-moe 14` (4.1 GB w RAM) albo UD-Q3_K_XL (KV q4_0, wszystko w VRAM) | 131 072 | ≥ 128 MiB | 3060 ~69 @0 / 39 @64k `[SZACUNEK]` | licencja < US$10M |
| 12 GB, czego nie da się | Swift / ISTA IQ3_XXS-mtp (jedyny 12 GB, który przeszedł E1) | – | MTP 64k, plain 98k | – | 3060 25.15 (E1, 120 W) | **≥ 131k się nie mieści**; E1 mierzył przy 16k |
| **11 GB** (2080 Ti) | **Bonsai 2 27B** | Q2_0, bez MTP, ub 256 | 163 840 | 210 MiB | `[INFERENCE]` ~35 | Saluki-MTP mieści tylko 88k |
| **10 GB** (3080) | **LFM2.5-24B-A2B** | Q4_K_M, KV q8_0, `--n-cpu-moe 20` (6.1 GB w RAM) | 131 072 | ≥ 128 MiB | ~69 @0 / 51 @64k `[SZACUNEK]` | żaden 27B nie osiąga 131k (Bonsai 124k, Saluki-MTP 52k) |
| **8 GB** (3060 Ti, 3070) | **LFM2.5-24B-A2B** | Q4_K_M, KV q8_0, `--n-cpu-moe 26` (8.1 GB w RAM) | 131 072 | ≥ 128 MiB | ~52 @0 / 33 @64k `[SZACUNEK]` | 27B nie mieści się wcale |
| MoE (8–16 GB, wszystkie klasy) | Qwen3.6-35B-A3B MTP GGUF | 8 GB UD-IQ4_XS ncm 35–36; 10–16 GB UD-Q4_K_XL ncm 19–33; KV q4_0, MTP n=2 | **262 144 – mieści się** | ≥ 128 MiB | 36–52 @64k `[SZACUNEK]` | AA v4 18; RAM ≥ 32 GB |

**Najważniejsze odkrycia:**
1. **Upstream CUDA prawie nie rośnie z wypełnieniem kontekstu.** 3090 b11856 (24.10): +2 / +4 / +6 MiB po prompcie 32.6k. Kampania 67 (P0): +18–28 MiB. Kopia f16 K/V do FA jest już w buforze compute rezerwowanym przy starcie. Model pamięci aplikacji (`memory.ts`, `GROWTH.cuda.spec 3.77`) dolicza za to `prompt × 15.4 KB`, czyli 3.9 GiB przy 262k. **Stąd 3090/4090 dostały 160k.** Ten współczynnik pochodzi z naszego forka (cuda-topka2), a nie z upstream.
2. **24 GB mieści 262 144 z MTP** na upstream. 4090 UD-Q4_K_XL MTP n=1 ub256 ubd64: load 23 680 MiB, n=3: 23 980 (dane NvVast67).
3. **Upstream ma już odpowiednik naszej „chudej rezerwy”:** `--spec-draft-n-ubatch 64` zmniejsza bufor compute draftu z 648 do 40 MiB (5090, 262k). Zostaje KV draftu w f16: 1024 MiB @262k. `-ctkd q4_0` dziś dokłada kopię f16 (+0.9–1.5 GiB), więc pomaga dopiero port lean (LeanPort67, ~0.7 GiB).
4. **Stan rekurencyjny (RS) rośnie z `--spec-draft-n-max`:** 149.6 MiB × (n+1), czyli 299 / 598 / 748 MiB przy n = 1 / 3 / 4. Na 24 GB n=4 bywa różnicą między „mieści” a OOM.

## 1. Model pamięci (upstream CUDA, b12110)

```
VRAM = W (+ warstwa nextn 335 MiB przy MTP; token_embd na hoście, o ile głowa nie jest związana)
     + KV(ctx) + RS × (n_max + 1 przy MTP)
     + ctx × (K+V f16 jednej pełnej warstwy + 2·ub) + ub × 40 × n_embd          # compute główny (zmierz.: 880 @160k ub512)
     + [MTP] KV draftu f16 (ctx × 4 KiB) + ctx × 2·ubd + ubd × 32 × n_embd     # ubd = --spec-draft-n-ubatch
     + [drafter Gemmy] W 429 MiB + ctx × (2048 + 2·ubd)
     + ovh(karta): 3060 150, 4060 Ti 173, 3070 195, 4070 196, 3080 276, 5080 309, 3090 336, 4090 465, 5090 579,
                   5060 Ti 500 (host z monitorem: 339 MiB w spoczynku)
mieści się ⇔ VRAM + 128 MiB ≤ suma CUDA (3090 24 126, 4090 24 082, 5090 32 109, 4060 Ti 15 947, 5060 Ti 15 846,
                                          5080 15 837, 4070 11 955, 3060 11 909, 3080 9927, 3070 7842)
```

Walidacja na 19 punktach kampanii 67 (Qwen 27B Q3/Q4/Q6, Gemma 12B, Qwen3.5-9B; plain i MTP n = 1/3; ub 256/512/1024; ubd 64): błąd **−3…+23 MiB**. Drafter Gemmy był zaniżony o 263 MiB w pierwszej wersji; po poprawce bufora draftu (ctx × 2048, zmierz. 550 MiB @262k) błąd wynosi −7 MiB.

Liczby wejściowe (pole `buffers` w `arms.jsonl`):
- W 15 718.5 / 16 053.2 MiB (UD-Q4_K_XL plain / MTP);
- KV 4608 @262k;
- compute 1380.02 @262k ub512 i 1202.01 @ub256;
- KV draftu 1024;
- compute draftu z ubd64 40.5.

Skrypt i tabele: komórki `eval` w tej sesji, wynik zapisany w `~/qwen-opt/cloud/runs/nv67/mkcards_final.py`.

Maks. kontekst Qwen3.8-27B (Linux / pulpit, KV q4_0, k = 1024 tokeny):

| kwant | konfiguracja | 3090 | 4090 | 4060 Ti | 5080 | 5090 |
|---|---|---|---|---|---|---|
| UD-Q3_K_XL | plain ub256 | – | – | 164k / 132k | 156k / 120k | – |
| UD-Q3_K_XL | MTP1 ub256 ubd64 | – | – | 120k / 92k | 112k / 84k | – |
| UD-Q3_K_XL | MTP2 + port lean | – | – | 128k / 96k | 120k / 88k | – |
| UD-IQ4_XS | plain ub256 | – | – | 120k / 84k | 108k / 72k | – |
| UD-Q4_K_M | MTP3 ub256 ubd64 | 256k / 256k | 256k / 256k | – | – | – |
| UD-Q4_K_XL | MTP1 / MTP2 / MTP3 ub256 ubd64 | 256k / 240k, 256k / 236k, 256k / 232k | 256k / 236k, 256k / 228k, 252k / 224k | – | – | – |
| UD-Q5_K_XL | plain ub256 / MTP2 | 216k / 180k, 156k / 128k | 208k / 172k, 152k / 124k | – | – | – |
| UD-Q6_K | MTP3, KV q4_0 / q8_0 | – | – | – | – | 256k / 256k; 252k / 232k |
| UD-Q6_K_XL | MTP3 ubd64 | – | – | – | – | 256k (755 MiB wolne) / – |
| UD-Q8_K_L | plain / MTP2 | – | – | – | – | 256k / 228k; 204k / 172k |

Małe kwanty 27B i LFM2.5. Maks. ctx przy zapasie 128 MiB (Linux); KV 27B q4_0 = 18 KiB/token, a z KV draftu f16 przy MTP ~22 KiB/token. „Lean” to port LeanPort67 z KV draftu q4_0.

| model (plik, GiB) | konfiguracja | 3070 8 GB | 3080 10 GB | 2080 Ti 11 GB | 3060 / 4070 12 GB | 4060 Ti 16 GB | 5080 16 GB |
|---|---|---|---|---|---|---|---|
| Bonsai 2 Q2_0 (7.10) | plain ub256 | 32k | 124k | 160k | 216k | 256k | 256k |
| Saluki-MTP Kujira (7.78) | plain / MTP1 ubd64 / MTP1 lean | – | 88k / 52k / 60k | 128k / 88k / 96k | 184k / 132k / 148k | 256k / 256k / 256k | 256k / 256k / 256k |
| Swift/ISTA IQ2_S-mtp (8.95) | plain / MTP1 ubd64 / MTP1 lean | – | 36k / 12k / 16k | 76k / 48k / 52k | 132k / 92k / 104k | 256k / 244k / 256k | 256k / 232k / 256k |
| ISTA IQ3_XXS-mtp (9.73) | plain / MTP1 ubd64 / MTP1 lean | – | – | 40k / 16k / 20k | 96k / 64k / 72k | 256k / 212k / 240k | 256k / 204k / 228k |
| UD-IQ3_XXS (10.18) | plain / MTP1 ubd64 | – | – | 20k / – | 76k / 44k | 256k / 196k | 244k / 188k |
| ISTA IQ3_S-mtp (11.29) | plain / MTP1 ubd64 / MTP1 lean | – | – | – | 24k / 4k / 4k | 204k / 152k / 172k | 192k / 144k / 160k |
| UD-Q3_K_XL (12.24) | plain / MTP1 ubd64 / MTP1 lean | – | – | – | – | 164k / 120k / 136k | 156k / 112k / 124k |
| LFM2.5 UD-IQ3_XXS, KV q8_0 | wszystko w VRAM | ncm 16 | ncm 6 | 128k (204 MiB) | 128k (1.4 GB) | 128k | 128k |
| LFM2.5 Q4_K_M, KV q8_0 | `--n-cpu-moe` przy 131 072 | 26 (8.1 GB RAM) | 20 (6.1) | 18 (5.4) | 14 (4.1) | 0 (128 MiB) | 3 (0.4) |

## 2. Przegląd HF: delta od raportu 33 (API, 2026-11-07)

| model | data | licencja | pobrania / ♥ | ranking | arch./KV | dla nas |
|---|---|---|---|---|---|---|
| **Nanbeige4.3-33B** (Nanbeige / BOSS Zhipin) | 2026-10-24 | Apache-2.0 | 20 062 / 1055 (GGUF bartowski 130k) | **AA v5 20.4** (= Qwen3.8-27B 20.1); TB 4.0 30% vs 6%; 44% więcej tokenów na zadanie; karta: SWE-Pro 60.3 vs 61.7 | gęsty Llama, 52 warstwy × 8 KV × 128: **58.5 KB/token q4_0** (3.2× Qwen) | 24 GB: Q4_K_M tylko 64k, IQ4_XS 100k. **5090: Q4_K_M 184k / IQ4_XS 212k** (plain). Ciekawa alternatywa agentowa na 32 GB, bez MTP. Do zmierzenia |
| **Arete-27B** (NousResearch) | 2026-11-06 | Apache-2.0 | 989 / 166 | SFT Qwen3.8-27B (wartości, 52.8M tokenów); fakty 2.32 → 2.98/5, propaganda 22% → 0.9% | jak Qwen3.8-27B | ten sam profil VRAM. **Głowica MTP wyłączona przy treningu**, więc akceptacja niepewna `[INFERENCE]`. Kandydat „bez cenzury politycznej” zamiast abliteracji |
| **Apex-35B-V1.0** | 2026-10-28 | Apache-2.0 | 1597 / 67 | vendor (własny harness): GPQA 83.3 vs 75.8 Qwen3.6, BFCL v4 84.0 vs 75.2, TB 2.1 65.2 vs 46.1 | fine-tune Qwen3.6-35B-A3B | ten sam profil co nasz wybór MoE; liczby niezweryfikowane. Do KLD/zadań przed katalogiem |
| Axion-1.0-35B | 10-16 / 11-04 | Apache-2.0 | 919 / 61 | agent naukowy (HLE 52.2 w pracy); checkpoint reprodukcyjny | `Qwen3_5Moe` | niszowy |
| Clover-35B-A3B-Preview | 10-24 | Apache-2.0 | 4061 / 255 | dyfuzyjny LM na Qwen3.6 | własna arch., 128k, własny llama.cpp | poza upstream: odpada |
| tencent/Qwen3.8-27B-DSpine-b16 | **2026-11-07** | Apache-2.0 | 0 / 5 | akceptacja 4.5–7.2 vs DFlash2 4.1–5.7 | drafter SGLang | brak GGUF i llama.cpp; obserwować |
| DeepSeek-V4.1-Flash-1017 (+ GSQ ISTA, 2.99M pobrań) | 10-17 | MIT | – | AA v5 32.6 | 552B MoE | za duży na ≤ 32 GB |
| Inkling 2 Small (Thinking Machines) | 11-05 | wagi „wkrótce” | – | AA v5 30.6 | – | obserwować wydanie wag |
| MiniMax-M3.1-Flash / GLM-5.3-Flash | 10-17 / 08-25 | – | – | AA v5 29.1 / 27.8 | 100B+ | poza ≤ 32 GB |
| Mistral Small 4 | – | Apache-2.0 | – | AA v5 4.3 | **119B MoE** (`Mistral-Small-4-119B-2603`) | poza klasą ≤ 35B |
| Bielik 11B v3.0 | – | Apache-2.0 | 13 375 / 158 | – | Llama, **ctx 32 768** | nie spełnia 131k minimum. PL zostaje przy Qwen/Gemmie |
| Spark-X2.6-4B, LFM3-1.7B, Dory 4B | 10-19…10-26 | Apache / LFM / NVIDIA | – | małe on-device | – | telefon, nie karty |
| Qwen3.5-9B MTP GGUF (unsloth) | – | Apache-2.0 | – | – | 9B z głowicą nextn | 8 GB: z MTP tylko 124k |
| Ornith-1.5-9B / 35B-A3B | 08-18 | **MIT** | 5.7M / 4.2M (GGUF) | vendor GPQA 86.4 (9B), SWE-V 79 (35B) | jak Qwen3.5/3.6 | 8 GB alt.: Ornith-9B Q4_K_M 180k (368 MiB); jakość niezweryfikowana (R33) |

Wyniki AA v5.0.1 (strona modelu, JSON `intelligenceIndex`): Qwen3.8-27B 20.1, Nanbeige4.3-33B 20.4, Nemotron 3.5 Lightning 5.5, Gemma 4 31B 4.4, Mistral Small 4 4.3. Qwen3.6-35B-A3B, Gemma 4 12B/26B, Qwen3.5-9B i gpt-oss-20b nie mają jeszcze wyniku v5. Dla nich została skala v4.3.2 z katalogu: 18 / 14 / 17 / 11 / 9.

Inne fakty:
- **Unsloth v3.1 dla 27B nie istnieje.** Ostatni upload `unsloth/Qwen3.8-27B-GGUF` to 2026-08-20; v3.1 jest tylko dla Flash-Next (R66f).
- W repo są nowe rozmiary: UD-IQ4_XS 13.27, UD-Q4_K_S 14.30, UD-Q4_K_M 15.33, UD-Q6_K_XL 23.56 i UD-Q8_K_L 26.12 GiB.
- Commit Qwen 2026-11-07 dodaje do szablonu czatu tylko „response template”, wag nie zmienia.
- `google/gemma-4-12b-it`: 2026-10-30 poprawiono 210 „glitch tokens” w tokenizerze. GGUF Unsloth pochodzą z 07-17, a ggml-org zaktualizował swoje 11-01, więc trzeba sprawdzić, czy GGUF Unsloth ma już poprawiony słownik.
- `ConwayResearch/Underdog-Saluki-27B-1.0`: 2026-11-05 commit „Switch the license to CC BY-NC 4.0” (766 261 pobrań, 701 ♥); licencję komercyjną trzeba uzyskać od Conway (kontakt w README). `Kujira/…-MTP-GGUF` (8.35 GB, 164 748 pobrań) deklaruje Apache-2.0.
- `prism-ml/Ternary-Bonsai-2-27B-gguf` publikuje oficjalny upstreamowy **Q2_0** (7 626 008 928 B, obok PQ2_0 / PTQ1_0), więc nasz repack nie jest już potrzebny.

Licencje wybranych modeli:
- Apache-2.0: Qwen3.8-27B (unsloth), GSQ-RCO ISTA, Bonsai 2 Q2_0, Qwen3.6, Nanbeige. MIT: Ornith.
- **Saluki: CC BY-NC 4.0 od 2026-11-05**; graft Kujiry deklaruje Apache-2.0, ale pochodzi z wag Saluki `[INFERENCE: też NC]`.
- **LFM2.5:** LFM Open v1.0, za darmo poniżej US$10M przychodu (dotyczy też klientów B2B).
- Swift 1.5: próg US$1M; zamiast niego plik ISTA o tej samej alokacji.
- Poza wyborem: Flash-Next (Qwen Community, „AI Work Assistant”) i Llama 4 (UE), zob. `modele-katalogowe`.

## 3. Uzasadnienie per klasa

- **32 / 24 GB:** 27B mieści 262 144 z MTP na stock upstream.
  - 32 GB: UD-Q6_K z MTP3 zostawia 2.9 GiB.
  - 24 GB: UD-Q4_K_M z MTP2 zostawia 1.1–1.3 GiB, więc działa też z pulpitem.
  - UD-Q4_K_XL (+1.04 GiB wag) mieści 262k z MTP1 tylko bez monitora (402 MiB); po teście fill.
- **16 GB:** 27B przy 262 144 mieści się tylko bez MTP, w IQ3_XXS (GSQ ISTA albo UD).
  - Z MTP stock: GSQ IQ3_XXS-mtp daje 200–217k, a z portem lean 225–245k. To najlepsza para „27B + długi kontekst + MTP”. Plik ISTA ma licencję Apache-2.0 i tę samą alokację co Swift W3.
  - Koszt: KLD 3× wyższe niż UD-Q3_K_XL (0.119 vs 0.039, E1).
  - E1 odrzucił GSQ na 16 GB, ale wtedy celem było 131k. Przy celu 262k/200k+ ten bilans się odwraca. Decyzja jakościowa wymaga zadań (E1 W-set) przy długim kontekście.
- **12 GB:** jedyne 27B ≥ 131k to 2-bity: Saluki-MTP (135k) i Bonsai Q2_0 (221k, bez MTP).
  - Swift/ISTA IQ3_XXS-mtp, „zwycięzca” E1 dla 12 GB, z MTP mieści tylko 64k.
  - Saluki ma lepsze KLD (0.257 vs 0.352), MTP i zmierzone 38.2 t/s (3060, fork), ale od 2026-11-05 licencję CC BY-NC 4.0.
  - Bonsai jest czysty licencyjnie (Apache-2.0, oficjalny Q2_0 w upstream) i ma dłuższy kontekst, ale robi błędy po polsku.
  - Decyzja licencyjna jest po stronie użytkownika.
- **11 GB:** Bonsai Q2_0 przy 163 840. **10 GB:** żadne 27B nie osiąga 131k (Bonsai 124k), więc LFM2.5 Q4_K_M z 6 GB ekspertów w RAM. **8 GB:** 27B nie mieści się wcale; LFM2.5 Q4_K_M z `--n-cpu-moe 26`.
- **LFM2.5:** kontekst do 131 072 (limit modelu), bez MTP/draftera. KV q8_0 to decyzja użytkownika; na 12 GB UD-Q3_K_XL mieści się w całości dopiero przy q4_0. Licencja < US$10M przychodu. Kwanty są kruche (KLD Q4 ~0.2 do własnego Q8).
- **Qwen3.6-35B-A3B** zostaje jako opcja MoE z pełnym 262 144 na każdej klasie, przy RAM ≥ 32 GB.


## 4. Plan weryfikacji (kampania 67, faza końcowa)

Karty: `~/qwen-opt/cloud/runs/nv67/cards-final/*.json` i `cards-final/alt/*.json` (generator `mkcards_final.py`, ten sam schemat; `cards/` bez zmian). Nowe pole `main_extra` (LFM na ≤ 10 GB: `--n-cpu-moe N` w każdym ramieniu głównym) wymaga dopisania w `nv67.py` albo ręcznego uruchomienia.

| karta | ramię główne (model / ctx / KV / ub / MTP) | do zmierzenia | blok `moe` (Qwen3.6 MTP GGUF, 262 144) |
|---|---|---|---|
| 3090, 4090 | 27B UD-Q4_K_M / 262 144 / q4_0 / 512 / self | mem, perf N1–N4 (ubd64), **fill 262k**, stab, ABBA | UD-IQ4_XS, KV q8_0, ncm 0–2 |
| 3090, 4090 (karty bieżące) | 27B UD-Q4_K_XL / 262 144 / ub256 / MTP1 ubd64 | **fill 262k** (402 MiB) | – |
| 5090 | 27B UD-Q6_K / 262 144 / q4_0 / 1024 / self | fill 262k z MTP3 | UD-Q5_K_XL, KV q8_0, ncm 0–2 |
| 4060 Ti / 5080 (+4080, 4070 Ti S, 5070 Ti) / 5060 Ti | GSQ IQ3_XXS-mtp / 217 088 / 208 896 / 200 704 / q4_0 / 256 / self | perf N1 ubd64, fill; ctx_probe lean 225–245k i 262k | UD-Q4_K_XL, ncm 18–25 |
| 4060 Ti, alt/ | IQ3_XXS plain 262 144; UD-Q3_K_XL plain 167 936; Saluki-MTP 262 144; LFM Q4_K_M q8_0 131 072 | fill, sweep (jakość vs kontekst vs t/s) | – |
| 3060, 4070 (3080-12, 4070 Ti, 5070: 131 072) | Saluki-MTP / 135 168 / q4_0 / 256 / self | perf N1/N2 ubd64, fill, ctx_probe 151 552 (lean) | UD-Q4_K_XL, ncm 27–33 |
| 3060, alt/ | Bonsai Q2_0 plain 217 088; LFM Q4_K_M ncm 14 / 131 072 | fill, sweep | – |
| 2080 Ti | Bonsai Q2_0 / 163 840 / q4_0 / 256 / plain | **najpierw nowy host** (obecny: 8558 z 10 817 MiB wolne, obcy proces ~2.2 GB) | UD-Q4_K_XL, ncm 29–35 |
| 3080 | LFM2.5 Q4_K_M / 131 072 / q8_0 / 512 / `--n-cpu-moe 20` | perf, fill | UD-Q4_K_XL, ncm 31–37 |
| 3070, 3060 Ti | LFM2.5 Q4_K_M / 131 072 / q8_0 / 512 / `--n-cpu-moe 26` | perf, fill | UD-IQ4_XS, ncm 34–40 |

Hosty dla bloków `moe` i LFM muszą mieć ≥ 32 GB RAM. Poza kampanią potrzebne są jeszcze:
- KLD UD-Q4_K_M vs UD-Q4_K_XL (protokół E1; bramka 24 GB);
- KLD ISTA IQ3_XXS-mtp, bo E1 mierzył tylko Swifta o tej samej alokacji;
- zadania W-set przy ≥ 128k dla IQ3_XXS vs UD-Q3_K_XL;
- decyzja licencyjna Saluki (CC BY-NC) vs Bonsai;
- zadania Apex-35B i Nanbeige4.3-33B przed katalogiem.

## 5. Co zmienić w aplikacji (poza kampanią)

`app/engine/src/server/catalog/memory.ts`:
- `GROWTH.cuda.spec 3.77` dotyczy forka, a nie upstream (upstream: +2…+28 MiB) – rozdzielić `enigmaSpec`;
- dodać `RS × (n_max+1)`;
- dodać KV draftu f16;
- dodać `--spec-draft-n-ubatch 64`;
- liczyć zapas od sumy CUDA, a nie nvidia-smi.

Bez tych poprawek `recommend()` zostanie przy 160k na 24 GB. Wymagane też: katalog modeli z UD-Q4_K_M / UD-Q6_K 27B i Qwen3.6 **MTP GGUF** (obecnie bez MTP) oraz `--n-cpu-moe` per klasa.
