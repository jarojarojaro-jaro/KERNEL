# Benchmarki NVIDIA — przed i po naszej optymalizacji (2026-10-16)

Zestawienie z raportów `research/09-chmura-3090.md`, `09-chmura-5060ti.md`, `09-chmura-3060.md` (surowe dane: `~/qwen-opt/cloud/results/<karta>-20261016/`, `scorecard.json`). Wszystkie liczby zmierzone; nic nie jest szacunkiem.

## Wspólna metoda
- **Generowanie (decode t/s):** `spec_sweep` przez serwer, 6 promptów (PL proza, PL tech, PL kod, EN czat, EN tech, EN kod) × 3 seedy, T=1, odpowiedź 400 tokenów. Kolejność ABBA (np. A0 A1 A2 A2s A2s A2 A1 A0), świeży serwer na każdy tryb. Mediana z rund; w nawiasie min–max per prompt. Nie best-of.
- **Prefill (pp512 / pp4096):** `llama-bench`, `-r 5`, kolejność ABCDDCBA.
- **TTFT:** czas do pierwszego tokena dla promptu ~2k tokenów, bez cache promptu, 3 powtórzenia.
- **Długi kontekst:** `llama-bench` tg64 na głębokości `-d` (0 / 8k / 32k / 64k).
- **Poprawność:** greedy T=0, 2 prompty × 400 tokenów, każdy przebieg na świeżym serwerze; `test-backend-ops`.
- **Tryby:**
  - A0 = upstream llama.cpp v0.7.0, tylko `llama-server -m model` („typowa aplikacja”);
  - A1 = upstream z najlepszymi flagami;
  - A2 = nasz fork `cuda-v070` z flagami A1 + nasze dodatki;
  - profil = A2 + ustawienia dobrane pod daną architekturę.

## RTX 3090 24 GB (Ampere sm_86)
- **Sprzęt:** limit mocy 300 W (host), PCIe gen3 x16, pamięć 936 GB/s, CPU hosta i7-4790 (2014), sterownik 615.71.09, CUDA 12.8.
- **Flagi A1/A2:** `-fit on -fa on -c 65536 -np 1`.
  - Qwen: KV q4_0, MTP n=4, `--reasoning-effort low`.
  - LFM: KV q8_0.
  - A2 dla Qwena dodatkowo: słownik draftu 64k + głowica i MTP w IQ4_XS.
  - A0: kontekst dobrany przez `-fit` = 84k, KV f16.

### Qwen3.8-27B UD-Q4_K_XL (17.6 GB)
| | A0 typowa (= Ollama) | A1 najlepsze flagi | **A2 nasz** |
|---|---|---|---|
| decode t/s | 38.9 (Ollama 39.0) | 63.3 [49–70] | **78.0** [65–88] |
| ms na krok | 25.7 | 51.6 | 38.4 |
| tokeny na krok (MTP) | 1.00 | 3.32 | 3.31 |
| prefill pp512 / pp4096 | 1410 / 1396 | 1404 / 1384 | 1378 / 1363 |
| prefill przez serwer (2k) | 1207 t/s | 1075 | 1040 |
| TTFT ~2.1k tokenów | 2.14 s (Ollama 1.83 s*) | 2.29 s | 2.40 s |
| tg128 bez spekulacji | 39.5 | 39.0 | 39.4 (profil Ampere: 43.0) |
| odpowiedź 500 słów EN / PL | 15.0 s / 34.5 s | 9.2 s / 21.2 s | 7.5 s / 17.3 s |
| VRAM | 22.1 GB (Ollama 18.4) | 19.2 GB | 19.5 GB |

### LFM2.5-24B-A2B Q5_K_M (17.0 GB)
| | A0 typowa (= Ollama) | A1 najlepsze flagi | **profil Ampere** |
|---|---|---|---|
| decode t/s | 180.2 [179–184] (Ollama 180.5) | 176.0 | **263.9** [263–266] |
| ms na token | 5.55 | 5.68 | 3.79 |
| prefill pp512 / pp4096 | 5168 / 5168 | 5113 / 5135 | 5126 / 5164 |
| TTFT ~2.1k | 0.46 s (Ollama 0.31 s*) | 0.45 s | 0.45 s |
| tg128 | 241.2 | 236.9 | 284.5 |
| odpowiedź 500 słów EN / PL | 3.2 s / 7.5 s | 3.3 s / 7.6 s | 2.2 s / 5.1 s |
| VRAM | 19.3 GB | 17.5 GB | 17.5 GB |

\* Ollama mierzona na promptcie ~1.8k tokenów (inny tokenizer promptu), więc TTFT nie jest 1:1.

### Długi kontekst (tg64, upstream / nasz)
| | 0 | 8k | 32k | 64k |
|---|---|---|---|---|
| Qwen (KV q4_0) | 38.8 / 39.3 | 37.0 / 37.7 | 31.8 / 32.3 | 26.7 / 27.2 |
| LFM (KV q8_0) | 234.3 / 251.9 | 218.8 / 237.0 | 178.8 / 190.2 | 140.8 / 147.7 |

### Profil kroku (nsys)
| | kerneli/token | czas GPU | przerwy |
|---|---|---|---|
| Qwen upstream → nasz | 1956 → 795 | 24.9 → 24.5 ms | 3.83 → 2.55 ms |
| LFM upstream → nasz | 908 → 357 | 3.95 → 3.66 ms | 2.22 → 1.85 ms |

## RTX 5060 Ti 16 GB (Blackwell sm_120)
- **Sprzęt:** 180 W, PCIe gen4 x8, GDDR7 448 GB/s, kontener z limitem 7.68 CPU (EPYC 7502), sterownik 580.173.02.
- **Flagi:**
  - A0: tylko `-m`, czyli domyślny `-fit`, KV f16, domyślne wątki.
  - A1/A2: `-fit off -ngl 99 -t 8 -fa on -ctk q8_0 -ctv q8_0 -c 32768 -np 1`; Qwen dodatkowo MTP n=4.
  - A2 dla Qwena: + słownik draftu 64k + IQ4_XS.
  - Profil NVIDIA: `GGML_HIP_GATE_UP_Q8=0`, dla LFM też `Q8_IDS=0`.
- **Uwaga:** upstream MTP z domyślnym `-fit on` na 16 GB spada do 7.7 t/s (pułapka).

### Qwen3.8-27B UD-Q3_K_XL (13.15 GB; Q4 się nie mieści)
| | A0 typowa | A1 najlepsze flagi | A2 nasz | **profil NVIDIA** |
|---|---|---|---|---|
| decode t/s | 28.07 [27.9–28.1] | 37.32 [34.0–42.8] | 50.8 [48.2–59.9] | **51.66** [49.6–59.9] |
| ms na krok | 35.66 | 68.36 | 48.58 | 47.92 |
| tokeny na krok | 1.0 | 2.55 | 2.48 | 2.48 |
| prefill pp512 / pp4096 | 1048 / 1044 | 1041 / 1038 | 1041 / 1036 | 1032 / — |
| TTFT ~2k | 2.42 s | 2.69 s | 2.71 s | 2.71 s |
| odpowiedź 500 słów EN / PL | 20.2 s / 42.9 s | 15.2 s / 32.3 s | 11.2 s / 23.7 s | 11.0 s / 23.3 s |
| VRAM | 13.9 GiB | 14.3 GiB | 14.5 GiB | 14.5 GiB |

### LFM2.5-24B-A2B Q4_K_M (14.5 GB; Q5 się nie mieści)
| | A0 typowa | A1 najlepsze flagi | A2 nasz | **profil NVIDIA** |
|---|---|---|---|---|
| decode t/s | 147.69 [146.5–150.2] | 144.47 | 190.99 | **207.86** [206.7–209.1] |
| ms na token | 6.77 | 6.92 | 5.30 | 4.81 |
| prefill pp512 / pp4096 | 4148 / 4221 | 4162 / 4210 | 4146 / 4235 | 4160 / — |
| prefill z `-ub 2048` (pp4096) | | | | **6587** (+56%) |
| TTFT ~2k | 0.55 s | 0.54 s | 0.53 s | 0.53 s |
| odpowiedź 500 słów EN / PL | 3.9 s / 8.5 s | 4.0 s / 8.7 s | 3.0 s / 6.5 s | 2.8 s / 6.0 s |
| VRAM | 14.5 GiB | 14.2 GiB | 14.2 GiB | 14.2 GiB |

### Długi kontekst (tg64, KV q8_0, upstream / nasz)
| | 0 | 8k | 32k | 64k |
|---|---|---|---|---|
| Qwen Q3_K_XL | 28.2 / 28.9 | 27.2 / 27.6 | 23.6 / 23.9 | 20.1 / 20.2 |
| LFM Q4_K_M | 192.2 / 198.8 | 178.6 / 181.1 | 143.1 / 145.8 | 112.5 / 114.7 |

### Inne formaty LFM na tej karcie
| plik | GB | serwer upstream → nasz | KLD vs Q8_0 | md5 vs upstream |
|---|---|---|---|---|
| QAD-Q4_0 (oficjalny Liquid) | 13.58 | 164.5 → **226.8** | 0.203 | identyczne |
| NVFP4 (społeczność) | 13.58 | 156.0 → 198.0 | 1.183 (zła jakość) | identyczne |
| Q5_K_M z ekspertami w RAM | 17.03 | — / 120.9 (tg128) | 0.124 | — |

## RTX 3060 12 GB (Ampere sm_86)
- **Sprzęt:** 170 W (stale na limicie), PCIe gen3 x16, 360 GB/s, Xeon E5-2698 v4, sterownik 595.71.05.
- **Flagi:**
  - A0: tylko `-m`.
  - A1 (najlepsze, runda 2): `-fa on`, KV f16, `-ub 1024`, `-c 32768`.
  - Nasz: fork + te same flagi + `GGML_HIP_GATE_UP_Q8=0`.
- **Bez spekulacji:** te modele nie mają głowic MTP.

### Underdog Saluki 27B IQ2-mix (7.9 GB)
| | A0 typowa | A1 najlepsze flagi | **nasz** |
|---|---|---|---|
| decode t/s | 22.1 [22.1–22.2] | 22.3 | **23.4** [23.3–23.4] |
| ms na token | 45.18 | 44.87 | 42.82 |
| prefill pp512 / pp4096 | 573 / 570 | — / 581 | — / 568 |
| TTFT (1935 tokenów) | 3.61 s | 3.61 s | 3.67 s |
| odpowiedź 500 słów EN / PL | 26.4 s / 60.7 s | 26.2 s / 60.3 s | 25.1 s / 57.6 s |
| VRAM | 10.1 GB | 9.7 GB | 9.7 GB |
| tg przy 8k / 32k (upstream → nasz) | | 21.90 / 19.98 | 22.66 / 20.69 |
| perplexity (wikitext) | 7.67 | | |

### Ternary Bonsai 2 27B
| | A0 (Prism, PQ2_0) | Prism PTQ1_0 (najszybszy) | upstream + repack Q2_0 | **nasz + repack Q2_0** |
|---|---|---|---|---|
| decode t/s | 36.8 | **44.8** | 33.1 | 35.5 |
| prefill pp4096 | 601 | 592 | 638 | 622 |
| TTFT (1935 tok) | 3.40 s | 3.40 s | 3.26 s | 3.35 s |
| odpowiedź 500 słów EN / PL | 15.9 / 36.6 s | 13.1 / 30.0 s | 17.6 / 40.6 s | 16.5 / 37.9 s |
| VRAM | 10.1 GB | 6.8 GB | 9.4 GB | 9.4 GB |
| tg przy 8k / 32k | | 42.83 / 35.57 | 32.01 / 27.90 | 33.86 / 29.37 |
| perplexity (wikitext) | 8.62 | 8.62 | 8.62 | 8.62 |

## Poprawność (wszystkie karty)
- `test-backend-ops`:
  - 3090: 19253/19253;
  - 5060 Ti: 19251/19253 (2 przypadki naszej fuzji prologu GDN tuż ponad tolerancją: 5.05e-4 i 9.44e-4 przy progu 5e-4).
- **Greedy md5 nasz ≠ upstream w zwykłym trybie** (wszystkie karty, oba modele). Przyczyny:
  - wielokolumnowe MMVQ (łatki 0001/0002);
  - u Qwena dodatkowo fuzja prologu GDN (0013).
- Wyniki są deterministyczne (2/2). Jakość: KLD nasz vs upstream na 3060 (Saluki 0.00065, Bonsai 0.00032) mieści się w szumie samego upstreamu (0.00061 / 0.00021).
- Wyjątek: LFM QAD-Q4_0 i NVFP4 dają md5 **identyczne** z upstreamem.

## Skąd zysk
| karta / model | z flag upstream (A0→A1) | z naszego silnika (A1→nasz) | razem (A0→nasz) |
|---|---|---|---|
| 3090 Qwen | ×1.62 (MTP) | ×1.23 (słownik draftu + IQ4_XS ×1.12, kod forka ×1.10) | **×2.00** |
| 3090 LFM | ×0.98 | ×1.50 (sampler/host ×1.42, profil Ampere ×1.06) | **×1.46** |
| 5060 Ti Qwen | ×1.33 (MTP + `-fit off`) | ×1.38 | **×1.84** |
| 5060 Ti LFM | ×0.98 | ×1.44 (sampler ~+25%, fuzje +5%, profil +5–6%) | **×1.41** |
| 3060 Saluki | ×1.01 | ×1.05 | **×1.05** |
| 3060 Bonsai | — | 33.1 → 35.5 na Q2_0 (+7%) | ×0.97 vs domyślny Prism |
