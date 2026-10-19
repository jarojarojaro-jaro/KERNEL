# Benchmarki PRZED → PO — cała optymalizacja (stan 2026-10-19)

Wyłącznie liczby zmierzone, ze źródłem `plik:linia`. Ścieżki: `NOTES` = `~/KERNEL/qwen-opt/NOTES.md`, `STATUS` = `~/KERNEL/qwen-opt/STATUS-NEXT.md`, `SPEC` = `~/KERNEL/qwen-opt/SPEC-QWEN27B.md`, `NV` = `~/KERNEL/product/BENCHMARKI-NVIDIA-2026-10-16.md`, `R/xx` = `~/KERNEL/product/research/xx-*.md`.
Kolumna **„porównywalność”**:
- **P (porównywalne)**: ten sam skrypt i warunki;
- **O (orientacyjne)**: inne skrypty, prompty, T lub KV;
- **brak**: nie zmierzone.

## Skrypty (skróty)
- **spec_sweep**: serwer, 6 promptów (PL proza/tech/kod, EN czat/tech/kod) × 3 seedy, T=1, 400 tok., świeży serwer, mediana (`STATUS:8`, `NV:6`).
- **serve_bench**: serwer, 3 EN + 3 PL, T=0, 256 tok., 3 przebiegi, mediana (`NOTES:3-4`, `SPEC:52-54`).
- **long_ctx_bench**: serwer, MTP n=4, T=0, 256 tok., prompty 1.7k/6.6k/29.5k/94k (`NOTES:197`, `NOTES:331`).
- **llama-bench**: `-fa 1 -p 4096 -n 128 -r 2`, KV jak w `run-llm.sh` (`STATUS:8`).
- **xbench**: workload MagnitudeVs, czyli sweep + copy 64k + code-edit 4 pliki + TTFT (`R/16d:52-58`, `R/16j:39`).

## Uwaga bezpieczeństwa
Produkcja (`amd-opt` @ f61994f58) ma domyślnie włączony replay PM4. Raport 17 zaleca `GGML_HIP_PM4=0` w serwerach z powodu 8 resetów GPU w ścieżce PM4 (`R/17:8,24`). Bez PM4 obowiązują liczby sprzed rundy 4: Qwen MTP 103.7, Uncensored 109.9, LFM 259.3 t/s (`NOTES:375`).

---

## 1. RX 7900 XTX — Qwen3.8-27B UD-Q4_K_XL (ROCm, KV q4_0)

| metryka | upstream domyślny (A0, `-m`) | upstream, najlepsze flagi | wcześniejszy stan / nasz fork | **produkcja amd-opt** | porównywalność |
|---|---|---|---|---|---|
| decode z MTP (spec_sweep T=1) | **nie zmierzone** (Ollama na XTX też nie, `wiki/ludzie-firmy/ollama.md:12`) | **nie zmierzone** tym skryptem | fork ROCm 2026-10-12: 74.5 t/s, 41.8 ms/krok (`NOTES:183`) | **109.0** t/s, 27.74 ms/krok (`STATUS:10`); bez PM4 103.7 (`NOTES:375`) | fork → prod: **P** (×1.46) |
| decode z MTP (serve_bench T=0, inne prompty) | nie zmierzone | Vulkan MTP n=4: 85.6 (EN+PL); ROCm MTP n=3: 68.6 (EN); DFlash2 n=7: 97.7 (EN) (`NOTES:43,45,48`) | stary build b356fa262, MTP n=3: 59.2 (`NOTES:10`) | spec_sweep 109.0 (`STATUS:10`) | upstream/stary → prod: **O** (różne skrypty i T) |
| decode bez spekulacji (llama-bench tg128) | nie zmierzone | upstream Vulkan 38.8 (`NOTES:48`) | nasz ROCm 2026-10-09: 36.6 (`NOTES:47`) | **43.2** (`STATUS:10`) | to samo narzędzie, inne buildy i backend: **O** |
| prefill pp512 | nie zmierzone | nie zmierzone | nasz ROCm 856 (`SPEC:86`) | brak wartości bezwzględnej (+1.9% z 0070, `NOTES:397`) | brak |
| prefill pp4096 | nie zmierzone | Vulkan 850 (`NOTES:16`; build oznaczony „nasz”, `SPEC:86`) | nasz ROCm 1044 (`NOTES:16`) | **1115** (`STATUS:10`); 1099.5 → 1123.2 z 0070 (`NOTES:397`) | 1044 → 1115: llama-bench, **P/O** (inny dzień) |
| prefill serwera 1.7k / 6.6k / 29.5k / 94k | nie zmierzone | nie zmierzone | 750 / 924 / 863 / 666 t/s (2026-10-12, `NOTES:175-178`) | 818 / 985 / 945 / 766 (`NOTES:331`) | **P** (long_ctx_bench) |
| czas prefillu 94k (TTFT) | nie zmierzone | nie zmierzone | 142 s (`NOTES:178`) | 123 s (`NOTES:322`) | **P** |
| prefill ~2k / ~16k (xbench) | nie zmierzone | nie zmierzone | — | 871–879 / 988 t/s (`R/16j:47-48`) | punkt pomiarowy |
| decode MTP przy 1.7k / 6.6k / 29.5k / 94k (T=0) | nie zmierzone | nie zmierzone | 78.6 / 75.5 / 62.4 / 43.0 (`NOTES:175-178`) | **130.2 / 118.5 / 105.2 / 100.6** (`NOTES:331`; przed PM4, potem nie powtarzane) | **P** (94k: ×2.34) |
| decode MTP, prompt 27 327 tok. | — | — | — | 111.77 / 111.85 (`R/12:326`) | punkt pomiarowy |
| decode bez spekulacji przy 16k / 32k / 98k | nie zmierzone | — | Vulkan 35.8 / 34.6 / 29.2 (`SPEC:87-89`) | **nie zmierzone** | brak |
| 64k / 128k (decode) | nie zmierzone | nie zmierzone | — | **nie zmierzone** (najbliżej 94k i 27k) | brak |
| VRAM, ctx 204800 | nie zmierzone | nie zmierzone | 22.8 GB (stary build), 23.2 GB (ROCm 2026-10-09) (`SPEC:66`) | **nie zmierzone** po S2/S4 (S4: stany 748 → 195 MiB; S2: +0.4 GB; graf draftu +180 MiB, `NOTES:283-317`) | brak |
| VRAM, ctx 67584 (szczyt) | — | — | — | 20182 MiB (`R/16j:50`) | punkt pomiarowy |
| maks. kontekst | nie zmierzone | — | — | ustawione 204800; z ub 2048 przy 204800 OOM 24.5 GB (`NOTES:218`); 262144 na XTX **nie zmierzone** | brak |

**Qwen3.8-27B Uncensored Q4_K_M:**

| metryka | upstream | wcześniej (fork) | produkcja | porównywalność |
|---|---|---|---|---|
| decode MTP (spec_sweep) | **nie zmierzone** | 78.5 t/s, 39.6 ms/krok (2026-10-12, 3 seedy, `NOTES:224`) | **115.5** t/s, 26.68 ms/krok (`STATUS:11`); bez PM4 109.9 (`NOTES:375`) | **P** (×1.47) |
| tg128 bez spekulacji | nie zmierzone | — | 44.0 (`STATUS:11`) | — |
| pp4096 | nie zmierzone | — | 1109 (`STATUS:11`) | — |
| prefill serwera 6.6k / 29.5k / 94k | nie zmierzone | 906 / 867 / 666 (`NOTES:322`) | 956 / 941 / 762 (`NOTES:322`; tylko K5) | **P** |
| decode przy długim kontekście, VRAM, maks. kontekst | **nie zmierzone** | | | brak |

## 2. RX 7900 XTX — LFM2.5-24B-A2B Q5_K_M (ROCm, produkcja KV q8_0, ctx 131072)

| metryka | upstream e60eff95f | fork bez prac nad LFM | **produkcja** | porównywalność |
|---|---|---|---|---|
| decode przez serwer (spec_sweep) | **nie zmierzone** | 173 t/s, 5.78 ms/token, KV q4_0 (`NOTES:335`) | **293.7** t/s, 3.41 ms/token, KV q8_0 (`STATUS:12`); bez PM4 259.3 (`NOTES:375`) | ten sam skrypt, inny KV (q8_0 kosztuje +2.6% przy głębokości 0, `NOTES:354`): **P/O** (×1.70) |
| tg128 (llama-bench) | 169.3, KV q4_0 (`NOTES:339`) | 198.3, KV q4_0 (`NOTES:339`) | 289.7, KV q8_0 (`STATUS:12`) | upstream → fork: **P**; → prod: **O** (inny KV) |
| pp4096 | 6107 (`NOTES:339`) | 6180 (`NOTES:339`) | 6175 (`STATUS:12`) | **P/O** |
| pp512 | ~5.6k, duży rozrzut (`NOTES:339`) | ~5.6k | nieinterpretowalne (±1100–1400, `R/16f:61`) | brak |
| prefill serwera 1.7k / 6.7k / 29.7k / 95k | nie zmierzone | 2768 / 5805 / 5172 / 3709 (`NOTES:336`) | **nie zmierzone** tym skryptem | brak |
| TTFT 2k / 8k / 32k (ub 512, produkcja) | nie zmierzone | — | 366 / 1473 / 6676 ms (`R/16f:67`) | punkt pomiarowy |
| decode przez serwer przy 1.7k / 6.7k / 29.7k / 95k | nie zmierzone | 174 / 172 / 168 / 153 (`NOTES:336`) | **nie zmierzone** | brak |
| llama-bench tg przy głębokości 0 / 32k / 98k (q8_0) | nie zmierzone | przed rundą 3: 241.1 / 205.4 / 152.4 (`NOTES:368`); 98k przed rundą 2 (q8_0): 144 (`NOTES:354`) | po rundzie 4: 294.8 przy 0, 213.0 przy 98k (`NOTES:375`) | **P** (98k: 144 → 213, ×1.48) |
| VRAM, 131k | nie zmierzone | 17.8 GB z KV q4_0 (`NOTES:334`) | 19.3 GB z KV q8_0 (`NOTES:354`); 18591 MiB po pomiarach (`R/16f:67`) | **O** |
| maks. kontekst | — | — | ustawione 131072; maksimum **nie zmierzone** | brak |

**LFM2.5 Uncensored AD-Q5_K_M:**

| metryka | upstream | wcześniej | produkcja | porównywalność |
|---|---|---|---|---|
| decode przez serwer | **nie zmierzone** | ~264 t/s (soak po PM4, `NOTES:375`) | **267.3** t/s, 3.74 ms/token (`STATUS:13`) | **O** |
| ms/token (llama-bench, łatka 0064) | — | 3.933 | 3.706 (`NOTES:374`) | **P** |
| tg128 / pp4096 | nie zmierzone | — | 264.3 / 6291 (`STATUS:13`) | — |
| długi kontekst, VRAM | **nie zmierzone** | | | brak |

## 3. Nowe w tej sesji, jeszcze nie w produkcji

| zmiana | przed → po | skrypt / warunki | porównywalność |
|---|---|---|---|
| Ogon z lookupu, Qwen XTX (`LLAMA_SPEC_LOOKUP=3 W=16`) | code-edit (`mvs`) T=0: MTP4 166.2 → W8 255.6 → **W16 400.9** t/s (×2.41); T=1: 166.1 → 375.8 (×2.26); copy T=0: 235.8 (W8) → 355.0; ~30k T=0: 156.7 → 373.5 (`R/16b:13-17,85-89,102-107`) | `copy_bench.py`, ABBA, md5 T=0 identyczne 11/11 (`R/16b:18`) | **P** |
| … na czacie | spec_sweep 106.4 → 105.3 (seedy 1–3), 106.1 → 106.8 (seedy 4–9); ms/krok 28.74 → 28.73 (`R/16b:123-124`) | spec_sweep 6×3 | **P** (w szumie) |
| Współdzielenie cache promptu (`LLAMA_SERVER_CACHE_SHARE_MIN=1024`) | nowa sesja omp po obcym zapytaniu: Qwen **8019 → 1612 ms**, LFM 1357 → 230 ms (166 ms z `LLAMA_LFM2_MSG_SPANS=1`) (`R/16f:15,168-170`) | replay omp, łatka 50c3a2f2a | **P** |
| Cache sesji na SSD (slot save/restore) | sesja 53k: Qwen 2.51 s zamiast ~61.5 s prefillu; LFM 0.53 s zamiast ~12.2 s (`R/16f:16,198-199`) | slot save/restore | **O** (prefill ~ wartość przybliżona) |
| LFM `-b/-ub 2048` (XTX) | pp4096 6108 → **7148** (+17%), pp16384 5654 → 6680 (+18%); TTFT 8k 1471 → 1254 ms, 32k 6668 → 5692 ms; VRAM +498 MiB (`R/16f:12,57-59,67-69`) | llama-bench `-r 3` A/B; TTFT przez serwer | **P**; KLD ≈ szum podziału batcha (`R/16f:80-86`) |
| `GGML_HIP_MOE_GU_BLOCK` (LFM) | tg128 291.26 → 292.22 (+0.33%, szum); Uncensored 264.60 → 268.27 (+1.39%) (`R/16g:86-88`) | llama-bench ABBA | **P** |
| Bit-exact (`LLAMA_SPEC_BITEXACT=1`) | tg128 43.17 → 41.79 (−2.8%); pp5 @32k 152–157 → 134 (−11%); spec_sweep 107.7 → 108.3 (0%); MTP 27k 111.8 → 102.66 (−9%) (`R/12:323-327`) | XTX, ABBA, prod vs bx | **P** |
| kvq na CUDA (3090) | tg64 @64k: Qwen 28.61 → 39.14 (+36.8%), LFM 159.65 → 208.12 (+30.4%); MTP przez serwer @59k 70.33 → 89.75 (+27.6%) (`R/16c:86,95,118-120`) | A/B w jednej binarce (`GGML_CUDA_KVQ=0/1`), ABBA | **P** |
| kvq na CUDA (5060 Ti) | tg64 @64k: Qwen Q3 20.61 → 25.69 (+24.6%), LFM 119.82 → 155.77 (+30.0%) (`R/16c:105,107`) | j.w. | **P** |
| kvq z wyjątkiem n=1 D256 q4_0 (po FAIL KLD) | Qwen tg64 @64k: 27.29 / 36.99 / **27.40** (off / kvq / wyjątek); pp5 @64k 103.18 → 141.83 (`R/16c:211-214`) | 3090 | **P** |
| Sprzężone próbkowanie (`LLAMA_SPEC_COUPLED`) | T=1: 107.7 (off) → 114.2 (sprzężone) vs 116.1 (kontrola); czysty efekt tok/krok +1.6%, netto ≈ 0; szacunek +0…+3.6% (`R/16k:20-26,108-113`) | spec_sweep, 12 bloków ABBA; A/B **niepełne** (resety GPU) | nierozstrzygnięte |
| PM4-PDL / PM4_UB (LFM) | górna granica 289.3 → 324.0 t/s (+12%), tylko pomiar czasu, **złe wyniki z definicji**; X1/X3 odrzucone (`R/16a:79-88,123-131`) | ab4 | nie dotyczy (nie do wdrożenia) |

## 4. Karty NVIDIA (kampania 2026-10-16; metoda `NV:5-15`, wszystkie **P** w obrębie karty)

| karta / model | A0 typowa aplikacja | A1 najlepsze flagi upstream | **nasz silnik** | pozostałe (A0 → nasz) | źródło |
|---|---|---|---|---|---|
| 3090, Qwen 27B Q4_K_XL | 38.9 t/s (Ollama 39.0) | 63.3 | **78.0** (×2.00) | pp512/4096: 1410/1396 → 1378/1363; TTFT 2.14 → 2.40 s; VRAM 22.1 → 19.5 GB; tg64 @64k 26.7 → 27.2 | `NV:28-36,54,151` |
| 3090, LFM Q5_K_M | 180.2 (Ollama 180.5) | 176.0 | **263.9** (×1.46) | pp 5168 → 5126/5164; TTFT 0.46 → 0.45 s; VRAM 19.3 → 17.5 GB; tg64 @64k 140.8 → 147.7 | `NV:41-47,55,152` |
| 5060 Ti, Qwen Q3_K_XL | 28.07 | 37.32 | **51.66** (×1.84) | pp 1048/1044 → 1032; TTFT 2.42 → 2.71 s; VRAM 13.9 → 14.5 GiB; tg64 @64k 20.1 → 20.2 | `NV:75-81,97,153` |
| 5060 Ti, LFM Q4_K_M | 147.69 | 144.47 | **207.86** (×1.41) | pp4096 4221 → 4160; z `-ub 2048` **6587** (+56%); TTFT 0.55 → 0.53 s; tg64 @64k 112.5 → 114.7 | `NV:86-92,98,154` |
| 5060 Ti, LFM QAD-Q4_0 | 164.5 (serwer upstream) | — | **226.8** | md5 identyczne z upstreamem | `NV:103` |
| 3060, Saluki 27B IQ2 | 22.1 | 22.3 | **23.4** (×1.05) | TTFT 3.61 → 3.67 s; VRAM 10.1 → 9.7 GB | `NV:118-123,155` |
| 3060, Bonsai 27B | Prism PQ2_0 36.8 (PTQ1_0 44.8) | upstream + Q2_0: 33.1 | 35.5 | ×0.97 względem domyślnego Prism | `NV:130-134,156` |
| **3090, Nemotron 3.5 Bolt 74B-A9B IQ2_XXS** | **87.2** | 131.4 (DFlash n5) | **141.1** (×1.62) | pp512/4096 1602/1566 → 1605/1563; TTFT 1.87 → 2.33 s; VRAM 22.0 → 23.1 GB; tg128 87.3 → 96.7 | `R/14:77-83,216-224` |
| Nemotron, długi kontekst (bez spekulacji) | upstream q8_0: 84.6 / 74.6 / 65.8 (0/32k/64k) | upstream f16: 85.2 / 84.5 / 82.5 | tuned q8_0: 91.4 / 79.9 / 69.4 | maks. kontekst: 262144 bez draftera; z DFlash 131072 (KV q4_0) | `R/14:44-47,95-97` |

Uwaga: TTFT Ollamy mierzony na ~1.8k tokenów, więc nie jest 1:1 (`NV:49`). Prefill i TTFT forka są o 1.5–12% gorsze od upstreamu (`R/15d:16`).

## 5. Konkurencja: Magnitude 0.2.9 (xbench, ABBA, te same pliki GGUF; **P** w obrębie karty)

| karta / model | workload | Magnitude | nasz | upstream | źródło |
|---|---|---|---|---|---|
| XTX (Vulkan RADV), Qwen 27B (Mag: DFlash2; my: MTP4, ctx 67584) | sweep T=1 / copy 64k / code-edit | 49.1–51.0 / 63.5–63.8 / 87.5–87.8 | **99.9–100.1 / 141.1–141.3 / 169.6–170.4** (×2.00 / ×2.22 / ×1.94) | — | `R/16j:43-46` |
| XTX, Qwen 27B | prefill ~2k / ~16k / 64k; VRAM szczyt | 688–692 / 678–680 t/s / 117.5 s; 22886 MiB | **871–879 / 988 / 78.4 s; 20182 MiB** | — | `R/16j:47-50` |
| XTX, LFM Q4_K_M plain | sweep / copy 64k / code-edit | 219.2–219.9 / 116.5–116.8 / 219.8–220.1 | **322.7–323.0 / 245.5–247.3 / 311.7–312.0** | — | `R/16j:59-61` |
| XTX, LFM | prefill ~2k / ~16k / 64k | 2682–2691 / 2681–2688 / 32.7 s | **5745–5789 / 6002–6026 / 14.6 s** | — | `R/16j:62-64` |
| 3090, Qwen 27B Q4_K_XL | sweep / copy 64k / code-edit | 65.7 / **80.2** / **156.1** (1 runda) | 65.7 / 69.3 / 105.2 (fork + DFlash2: copy **94.0**, code 121.1) | 49.2 / 58.6 / 78.7 | `R/16d:65-67` |
| 3090, Qwen | prefill 64k / TTFT 2k; VRAM | 744 t/s / 2.04 s; 22.2 GB | **888 / 1.68 s**; 19.6 GB | 887 / 1.64 s; 19.3 GB | `R/16d:68-69` |
| 3090, LFM Q4_K_M | sweep / copy 64k / code-edit; pp 2k/16k | 209.0 / **163.5** / 216.9; 5890/5840 | **291.6** / 132.5 / **280.4**; **7907/7995** | 216.6 / 127.8 / 212.7; 7789/7894 | `R/16d:70-73` |
| 5060 Ti, Qwen 27B Q3_K_XL | wszystkie | **nie ładuje się** | sweep 58.0, copy 52.0, code 98.2 | 43.5 / 44.7 / 70.8 | `R/16d:74` |
| 5060 Ti, LFM Q4_K_M, ctx 32k | sweep / copy 32k / code-edit; pp 2k | 157.8 / 125.4 / 161.6; 4728 | **205.1 / 149.9 / 199.9; 6055** | 153.4 / 123.0 / 150.4; 6081 | `R/16d:75-78` |
| 5060 Ti, Qwen3.5-9B | sweep / copy 64k / code-edit; prefill 64k | 68.2 / **175.8** / **376.7**; 2053 t/s | **121.0** / 128.1 / 239.0; **2343** | — | `R/16d:110-115` |

Kontekst dla lookup tail: nasz code-edit z W16 na XTX daje 401 t/s (`R/16b:102`). Magnitude-Vulkan na XTX daje na code-edit 87.7 t/s, ale na innych promptach i długości, więc porównanie jest **O** (`R/16b:116`).

## Braki (nie zmierzone)
- XTX: upstream A0, Ollama i upstream z najlepszymi flagami przez `spec_sweep` (wszystkie modele).
- XTX: Qwen decode 64k/128k; maksymalny kontekst; VRAM przy 204800 po S2/S4; pp512 jako wartość bezwzględna.
- XTX: LFM decode i prefill przez serwer przy długim kontekście po optymalizacjach.
- XTX: Uncensored (oba modele) względem upstreamu i przy długim kontekście.
- KLD dla Nemotrona z łatkami forka (`R/14:163`).
- Kompletne A/B sprzężonego próbkowania; całe PM4 z guardem (`R/17` §6, test nie wykonany).
