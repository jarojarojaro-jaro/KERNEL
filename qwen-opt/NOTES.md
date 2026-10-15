# qwen-opt — szybki Qwen3.8-27B na RX 7900 XTX (gfx1100, ROCm 10.0)

Wszystkie liczby z tej maszyny. Dekodowanie = `serve_bench.py` (llama-server, chat, temp 0, 256 tokenów,
3 przebiegi na prompt, mediana, z rozgrzewką). KV q4_0, flash attention.

## Wynik na punkcie odniesienia użytkownika (ctx 204800, KV q4_0, mieszanka 3 EN + 3 PL promptów)

| Konfiguracja | t/s | PL proza | VRAM |
|---|---|---|---|
| stary build b356fa262, ROCm, MTP n=3 (punkt startowy) | **59.2** | 47.4 | 22.8 GB |
| nasz ROCm (kernele + cache q8 + draft head 64k), MTP n=4 | 85.5 | 60.2 | 23.2 GB |
| Vulkan RADV (user-space) + draft head 64k, MTP n=4 | 88.1 | 62.0 | 22.1 GB |
| Vulkan RADV + draft head 64k, MTP n=5 | **91.8** | 59.4 | 22.3 GB |

Vulkan dekoduje szybciej (mniejszy narzut uruchomień), ROCm szybciej przetwarza prompt:
pp4096 1044 vs 850 t/s, pp4096 przy 16k kontekstu 890 vs 622 t/s.

## Co jest gdzie

| Ścieżka | Co |
|---|---|
| `~/llama-master` (gałąź `amd-opt`) | llama.cpp master + nasze zmiany: kernele HIP (`mmvq.cu`), cache q8_1, `--spec-draft-vocab` |
| `~/llama-opt` | zainstalowany build ROCm z tej gałęzi |
| `~/llama-opt-vk` | build Vulkan z tej gałęzi (+ `radeon_icd.json` dla RADV w przestrzeni użytkownika) |
| `~/vk` | Mesa RADV 25.2.8 rozpakowana z .deb + LunarG Vulkan SDK 1.4.363 (bez sudo) |
| `~/llama-base` | czysty upstream e60eff95f do porównań A/B |
| `~/models/draft/` | drafter DFlash2 Q4_K_M + `draft_vocab_qwen38.txt` (ranking tokenów dla draftu MTP) |
| `run-llm.sh` | start serwera: `run-llm.sh [qwen\|uncensored\|lfm] [mtp\|dflash\|none] [rocm\|vulkan]` |
| `serve_bench.py` | pomiar end-to-end (`--lang en\|pl\|all`) |
| `quick_quality.py` | 10 krótkich pytań EN/PL do szybkiej kontroli jakości |
| `build_draft_vocab.py` | buduje ranking tokenów dla `--spec-draft-vocab` |
| `greedy_check.sh` | porównanie wyjść greedy dwóch buildów (bezstratność zmian) |
| `mmvq-bench/` | mikrobenchmark kerneli „na zimno" (wagi > 96 MB Infinity Cache), kształty Qwena; `mm_dump` = bitowe porównanie wyników |
| `prof_serve.sh`, `trace_breakdown.py`, `kernel_bw.py` | profilowanie rocprofv3 |
| `e2e_exp.sh` | wariant makr → przebudowa → pomiar DFlash i MTP |
| `results.jsonl` | wszystkie pomiary end-to-end |

## Wyniki (Qwen3.8-27B UD-Q4_K_XL, angielskie prompty)

| Konfiguracja | t/s |
|---|---|
| stary build (b356fa262, 1 wrz), MTP n=3 | 58.2 |
| upstream master (e60eff95f), MTP n=3 | 68.6 |
| + nasze kernele, MTP n=4 | 82.3 |
| upstream master, DFlash2 n=7 | 97.7 |
| + nasze kernele, DFlash2 n=6 | 111–112 |
| + cache q8_1: MTP n=4 / DFlash2 n=6 / bez spekulacji | 84.4 / 115.7 / 36.6 |
| upstream Vulkan RADV: bez spekulacji / MTP n=4 / DFlash2 n=6 (kod EN) | 38.8 / 85.6* / 127* |

\* mieszanka EN+PL. Prompty po polsku: MTP n=4 78 t/s, DFlash2 n=6 65 t/s (drafter DFlash słabo zna polski).

## Diagnoza

- Dekodowanie 1 tokenu: `mul_mat_vec_q` czyta wagi z ~81–88% z 960 GB/s. Tam nie ma już dużo do wzięcia.
- Spekulacja (MTP/DFlash) weryfikuje 4–8 tokenów naraz. Upstream liczył wtedy każdą kolumnę osobno
  (rozpakowanie wag × liczba kolumn) → przy 8 kolumnach 240–340 GB/s zamiast ~700.
- Narzut uruchomień: ~1900–2100 kerneli na forward, ~3.2 µs przerwy między nimi w HIP graph → ~16% czasu.

## Zmiany w kernelach (mmvq.cu, tylko HIP/RDNA3, kolumny 2–8)

1. Wagi rozpakowane raz na wątek, iloczyn z każdą kolumną y (`vec_dot_q_multi`).
2. Q4_K/Q5_K: człon min liczony z sum bloków q8_1 (ds.y) jak w MMQ → połowa dp4a.
3. Ciągłe, szerokie odczyty: wątek bierze 4 kolejne inty (Q4_K/Q5_K/Q2_K), 2 pozycje (Q6_K).
4. Wiersze na blok: 2 przy 2–4 kolumnach, 4 przy 5–8 (Q2_K: 2).
5. Typy: Q4_K, Q5_K, Q6_K, IQ4_XS, IQ4_NL, Q2_K, IQ2_XXS/XS/S, IQ3_XXS/S, IQ1_S/M.

Mikrobenchmark (GB/s, 5120×17408, 1 / 4 / 8 kolumn):

| typ | upstream | nasze |
|---|---|---|
| Q5_K | 663 / 512 / 296 | 742 / 713 / 621 |
| Q4_K | 768 / 436 / 246 | 764 / 694 / 573 |
| Q6_K | 750 / 549 / 342 | 729 / 695 / 641 |
| IQ4_XS | 761 / 705 / 456 | 779 / 704 / 545 |
| Q2_K | 571 / 243 / 132 | 563 / 504 / 272 |
| IQ2_XXS | 466 / 328 / 223 | 474 / 368 / 261 |

Testy: `test-backend-ops -o MUL_MAT` 2444/2444, fusion 3709/3709.

## Pozostałe zmiany w llama.cpp (gałąź `amd-opt`)

- **Cache q8_1 aktywacji** (`ggml-cuda.cu`, `common.cuh`, `mmvq.cu`): kolejne MUL_MAT z tym samym src1
  (Q/K/V, qkv/z/alpha/beta w DeltaNet) kwantyzują wejście raz na ewaluację grafu. Bufor 4 MB alokowany raz
  poza przechwytywaniem grafu; unieważnienie na starcie ewaluacji i przy każdym zapisie nachodzącym na cache.
  Wyjścia greedy bitowo identyczne z/bez cache. +2–4%.
- **`--spec-draft-vocab FILE` / `--spec-draft-vocab-n N`** (MTP): głowica draftu liczy logity tylko dla N
  najczęstszych tokenów (reszta −inf, `ggml_set_rows`). Weryfikacja bez zmian → wynik bezstratny (sprawdzone
  greedy). 16k: −5% (za dużo pudeł), 32k: +7%, 48–64k: +7.5% (wybrane 64k), 96k: +6%. Działa na ROCm i Vulkanie.
- Commity: `95a0c83d6`, `72cfa5656` (kernele), `3a05006a0` (cache q8_1), `3b15c2b6d` (draft vocab).

## Kolejne kroki (niezrobione)

- ROCm: ~2000 kerneli na forward × ~3.2 µs przerwy w HIP graph ≈ 16% czasu. To główna różnica do Vulkana
  w dekodowaniu; wymaga fuzji małych operacji (rms_norm, add, sigmoid, softplus, cpy) albo mniejszej liczby węzłów.
- Vulkan, forward weryfikacji 6 tokenów (GGML_VK_PERF_LOGGER): `MUL_MAT_VEC q8_0 m=48` (ssm_alpha/beta)
  96 × 13 µs ≈ 1.3 ms z 33.6 ms — za mało grup roboczych przy 48 wierszach; split-K dałby ~3%.

## Wyniki negatywne (nie wracać bez nowego pomysłu)

- Fuzja gate+up (+SwiGLU) w mmvq dla 2–8 kolumn: DFlash 111 → 96, MTP 82 → 76 (podwójne rejestry = niższe obłożenie).
- Zmienne środowiskowe HIP (graph batch/segment, classic path, kernarg, wait timeout, direct dispatch): szum.
- `GGML_CUDA_GRAPH_OPT=1`: −1%. Wyłączenie grafów: −3%. Wyłączenie fuzji ggml: −8%.
- NI=8 / NI=2 dla Q4_K/Q5_K, RPB=8: gorzej niż NI=4 / RPB=4.
- Raport `autokernel-amd/reports/15-road-to-65.md` §16 („1075 GB/s, 112% peaku") jest błędny: przy MTP
  jeden przebieg modelu daje ~2.7 tokenu, więc odczyt wag to ~400 GB/s, nie 1075.

## Na później: limit mocy GPU (odłożone na prośbę użytkownika)

Cel: np. −20% mocy kosztem ≤5% t/s. Stan karty (2026-10-09):
- `power1_cap` = 303 W (domyślny), zakres sterownika 272–350 W (`/sys/class/drm/card0/device/hwmon/hwmon2/power1_cap*`).
  Najniżej bez OverDrive: 272 W, czyli tylko −10%.
- Podczas dekodowania karta siedzi na limicie (~305 W, `THROTTLE_STATUS: THROTTLED`).
- Zapis do `power1_cap` i `power_dpm_force_performance_level` wymaga roota (brak sudo w tej sesji).
- `pp_od_clk_voltage` nie istnieje → OverDrive wyłączony. Niższy limit sclk / undervolt wymaga parametru jądra
  `amdgpu.ppfeaturemask=0xffffffff` + restart, potem `echo "s 1 <MHz>"`, `echo "vo -<mV>"`, `echo c` do `pp_od_clk_voltage`.
- Plan pomiaru: `serve_bench.py --lang all` przy 350/303/290/272 W i obniżonym sclk, odczyt mocy z `amd-smi metric -p`
  co 0.5 s, wynik w t/s na wat. Dekodowanie jest ograniczone pamięcią, więc spodziewany mały spadek t/s.
- Temperatura 2026-10-09, przy prefillu 196k tokenów: edge 66°C, junction 106°C, VRAM 76°C, wentylatory ~2970 RPM, 281 W.
  Różnica edge–junction ~40°C jest duża (typowo 15–25°C) → podejrzenie pasty / docisku / komory parowej.
  Junction blisko progu 110°C; power cap powinien obniżyć hotspot.

## Runtime suspend wyrzuca model z VRAM (2026-10-10)
Bez monitora amdgpu usypia kartę po 5 s bezczynności (runtime PM/BACO) i przenosi całą VRAM do RAM (GTT).
Załadowany model działa wtedy przez PCIe: 4.4 t/s zamiast 92 (vram_used 35 MB, gtt_used 23.8 GB).
Naprawa: power/control=on (gpu-powercap.service, root). Bez roota run-llm.sh trzyma kontekst KFD (gpu-keepawake), co blokuje usypianie.
Po naprawie przy limicie 285 W: 94.1 / 90.6 / 94.7 t/s, także po 20 s bezczynności.

## Draft MTP: długość draftu, p_min, temperatura (2026-10-10, Vulkan, 285 W)
spec_sweep.sh/spec_sweep.py, 5 promptów (PL proza/tech/kod, EN chat/tech), 2 seedy x 400 tokenów. Mediana t/s (akceptacja):

| konfiguracja | T | mediana | pl-proza | en-chat | pl-kod |
|---|---|---|---|---|---|
| n=5 (domyślne) | 1.0 | 80.5 | 64.2 (0.36) | 59.3 (0.32) | 96.0 (0.66) |
| n=3 | 1.0 | 75.0 | 67.1 (0.49) | 68.6 (0.51) | 84.6 (0.72) |
| n=5 p_min 0.3 | 1.0 | 80.7 | 62.8 (0.39) | 57.2 (0.33) | 86.5 (0.59) |
| n=5 p_min 0.5 | 1.0 | 75.0 | 66.0 (0.57) | 61.0 (0.48) | 89.4 (0.68) |
| n=6 p_min 0.5 | 1.0 | 77.0 | 63.3 (0.47) | 61.2 (0.47) | 94.1 (0.68) |
| n=8 p_min 0.5 | 1.0 | 47.0 | | | |
| n=5 | 0.7 | 79.5 | 60.6 (0.34) | 62.2 (0.34) | 85.3 (0.55) |
| n=5 | 0.0 | 81.9 | 67.8 (0.40) | 64.3 (0.36) | 92.0 (0.62) |

- Procent akceptacji = przyjęte / wszystkie zgadnięte; krótszy draft podnosi procent, nie prędkość. n=5 bez p_min zostaje.
- n=8: weryfikacja 9 tokenów wypada poza kernele mmvq 2-8 kolumn → 47 t/s.
- Temperatura prawie bez wpływu (rejection sampling przy T>0 działa). Sufitem jest jakość głowicy MTP.
- Skrócony słownik 64k: poza nim 3.5% tokenów polskiej prozy — nie on ogranicza akceptację.
- GPU przy 285 W w trakcie: 284 W, junction 85-88°C, edge 64-67°C, wentylatory ~1850 RPM.

## DFlash vs MTP na tym samym zestawie (2026-10-10, ctx 204800, 285 W)
| konfiguracja | T | mediana | pl-proza | pl-tech | en-chat | en-tech | en-code |
|---|---|---|---|---|---|---|---|
| MTP n=5 | 0.0 | 86.3 | 71.5 | 82.3 | 64.5 | 90.8 | 90.4 |
| DFlash n=6 | 0.0 | 90.6 | 64.7 | 95.9 | 60.2 | 99.7 | 90.8 |
| DFlash n=8 | 0.0 | 86.2 | 65.7 | 88.4 | 59.4 | 99.1 | 96.1 |
| MTP n=5 | 1.0 | 81.1 | 63.9 | 81.6 | 60.4 | 85.4 | 80.5 |
| MTP n=5 probabilistic | 1.0 | 81.1 | 65.5 | 85.2 | 61.7 | 84.9 | 77.3 |
| DFlash n=6 | 1.0 | 71.9 | 54.9 | 82.7 | 58.0 | 71.9 | — |

- DFlash nie daje ogólnie 120 t/s: tamto było na jednym prompcie (EN kod LRU, 256 tok., T=0). Na szerszym zestawie EN: ~równo z MTP przy T=0, gorzej przy T=1 (DFlash nie ma rejection sampling, tylko dopasowanie).
- --spec-draft-sampling probabilistic dla MTP: bez zysku.
- Pierwszy przebieg n=8 MTP (47-56 t/s) i MTP po DFlash (5.6 t/s) były zepsute: llama-server z DFlash wisi na SIGTERM, nowy serwer dzielił VRAM ze starym. spec_sweep.sh dobija teraz SIGKILL po 15 s.

## 2026-10-12: krok po kroku (Vulkan, ctx 204800, 285 W, 6 promptów x 3 seedy, T=1, A/B naprzemiennie 2x)
- Adaptacyjna długość draftu (iloczyn pewności, --spec-draft-p-cum, n_max 7/6): bez zysku (najlepsze 80.5 vs 80.3). Usunięte.
- Small-M matvec (ssm_alpha/beta q8_0 m=48): 13.6 -> 8.6 us na wywołanie (~0.5 ms/krok). 68e163cf4.
- MMVQ Vulkan (afbb23886, 81e5fb913, f6e5de112, 6c7801bf6): matvec 6-kol. q5_K 665->699, iq4_xs 579->663, q4_K 614->690 GB/s; Q6_K przez MMVQ (lm_head n=6 1.9->1.3 ms).
  - ms/krok (serwer): Qwen UD 43.73 -> 41.46 (-5.2%), Uncensored Q4_K_M 41.93 -> 39.92 (-4.8%). Powtarzalne co do 0.3 ms.
  - Q6_K numerics: KLD 0.0042 vs poprzednia wersja, w granicach szumu batch 6 vs 512 (0.0036). PPL 6.2226 -> 6.2099.
  - t/s przy 3 seedach zależy bardziej od wylosowanego tekstu (tok/krok) niż od kernela; ms/krok jest miarą wiarygodną.
- -bs (losowanie celu na GPU): pomiar zepsuty obciążeniem CPU, do powtórki.
- GPU w trakcie: 284 W, junction 87 (max 90), mem 84, edge 67.

## ROCm vs Vulkan: cały czas odpowiedzi (2026-10-12, serwer, ctx 204800, KV q4_0, MTP + vocab 64k, T=0, 256 tok.)
| prompt | ROCm prefill | ROCm decode | Vulkan prefill | Vulkan decode | prompt + 1000 tok. ROCm / Vulkan |
|---|---|---|---|---|---|
| 1.7k | 750 t/s (2.3 s) | 78.6 | 683 (2.5 s) | 92.4 | 15.0 / **13.3 s** |
| 6.6k | 924 (7.1 s) | 75.5 | 746 (8.8 s) | 80.9 | **20.3** / 21.2 s |
| 29.5k | 863 (34 s) | 62.4 | 624 (47 s) | 66.1 | **50.2** / 62.4 s |
| 94k | 666 (142 s) | 43.0 | 397 (237 s) | 43.9 | **165** / 260 s |
- ROCm domyślny (run-llm.sh). Vulkan szybszy tylko przy krótkich promptach (~11%).
- Decode przy głębokim kontekście spada ~2x (92 -> 44 przy 94k) na obu backendach: kolejny cel (FA weryfikacji przy długim KV).

## ROCm: krok i uwaga przy długim kontekście (2026-10-12)
- Serwer, 6 promptów x 3 seedy, T=1: MTP n=4 41.8 ms/krok 74.5 t/s; n=5 44.5 ms 73.8 t/s; n=3 38.4 ms 74.4 t/s. (Vulkan n=5: 41.5 ms, ~80 t/s.)
- rocprof: GPU bezczynne 15.5% czasu w przerwach <5 us między ~1200 kernelami na krok (rms_norm, quantize_q8_1, cpy, bin_bcast, unary...).
- FA przy kwantyzowanym KV i 5 tokenach: wybierany kernel tile, który co krok konwertuje cały K/V do F16.
  llama-bench (ROCm): d2048 n1 39.8 / n5 44.2 ms; d32768 n1 43.4 / n5 56.4 ms.
  Kernel vec dla 5 kolumn (GGML_CUDA_FA_VEC_MAX_COLS=8): d32768 n5 120.6 ms — dużo gorzej (vec czyta KV osobno dla każdej z 6 głów Q w grupie GQA).
  => potrzebny kernel FA czytający skwantyzowane KV raz na głowę KV dla wszystkich głów Q i tokenów (GQA 6 x 5 tokenów). Cel: n=1 i n=5 przy długim kontekście.

## Decyzja (2026-10-12)
ROCm jest stałym backendem domyślnym. Dalsze optymalizacje robimy pod HIP/ROCm; Vulkan zostaje tylko jako opcja (run-llm.sh ... vulkan).

## ROCm: nowy kernel FA dla KV q4_0 (40c9bacdc, 2026-10-12)
Kernel fattn-kvq (RDNA3.0, WMMA): czyta q4_0 KV bez konwersji do F16, wszystkie głowy Q grupy GQA i do 8 tokenów w jednym przejściu.
llama-bench ms/forward: d32768 n1 31.1->28.1, n5 43.3->33.8; d98304 n1 39.4->29.9, n5 68.2->36.7. test-backend-ops FLASH_ATTN_EXT 4017 OK.
Serwer (long_ctx_bench, MTP n=4, T=0, 256 tok.), decode t/s przed -> po:
| prompt | przed | po |
|---|---|---|
| 1.7k | 78.6 | 92.9 (inna akceptacja: inny tekst greedy) |
| 6.6k | 75.5 | 81.4 |
| 29.5k | 62.4 | 74.4 |
| 94k | 43.0 | **70.9** (+65%) |
Krótki kontekst (spec_sweep, 3 seedy): Qwen 41.74 ms/krok (było 41.8), Uncensored 39.56 ms/krok, 78.6 t/s — bez regresji.
-ctkd/-ctvd q4_0 dla draftu: bez zysku (71.6 vs 70.9 przy 94k, w szumie) — nie włączam.

## Cache promptu (2026-10-12, dokument 27k tokenów, ustawienia domyślne serwera)
| scenariusz | przetworzone tokeny | czas |
|---|---|---|
| pierwsze pytanie (zimno) | 27332 | 31.9 s |
| pytanie uzupełniające w tej samej rozmowie | 24 | 0.7 s |
| nowa rozmowa, ten sam dokument, inne pytanie | 517 | 1.2 s |
| inna rozmowa (inny dokument 28k), potem powrót do pierwszej | 536 | 1.4 s |
Domyślne --cache-ram 8192 i checkpointy już działają; strojenie zbędne. run-llm.sh: --cache-ram 16384 (więcej długich rozmów w RAM; 62 GB RAM).

## A7: testy bez zmian w kodzie (ROCm, 2026-10-12)
- -bs (losowanie celu na GPU): 41.69 vs 41.65 ms/krok — bez efektu.
- ROCBLAS_USE_HIPBLASLT=1: pp4096 1050 vs 1040 (d0), 772 vs 768 (d32k) — szum.
- -ub 1024: +1%, -ub 2048: pp +3% (1073 / 782), ale serwer z ctx 204800 kończy się OOM (24.5 GB VRAM) przy pierwszym długim prompcie. Zostaje ub 512.
- Governor CPU performance: wymaga sudo, nie testowane.

## ROCm: łączenie kerneli A3-A5 (6da87d000, a180bea04, 92b14b8b2; 2026-10-12)
- A3 epilog bias/residual w MMVQ wielokolumnowym (bitowo identyczne), A4 prolog GDN (alpha/beta + softplus/sigmoid w jednym MMVQ, l2-norm q/k w kernelu GDN, stan czytany z cache), A5 conv: concat + 5 kopii snapshotów + gather w jednym SSM_CONV.
- Kernele weryfikacji: 2156 -> 1308; przerwy 6.99 -> 4.30 ms.
- Serwer (spec_sweep, 3 seedy, T=1, potwierdzone niezależnie): Qwen UD 41.7 -> **37.71 ms/krok, 74.8 -> 83.3 t/s**; Uncensored 39.6 -> **35.83 ms/krok, 78.5 -> 85.3 t/s**.
- Jakość (A4 nie jest bitowy): llama-perplexity KLD, batch 6: fusion vs baza KLD 0.0067, same-top 96.5%, PPL 6.182 vs 6.191; szum samej bazy batch 512 vs 6: KLD 0.0098. Bez pogorszenia.
- A6 (kwantyzacja q8_1 w producentach) — szkic w ~/qwen-opt/fusion/a6-wip.patch, do dokończenia.

## ROCm: fuzje A6 + strojenie (b9db88004..b1f8c19ac, 2026-10-12), wszystkie bitowo identyczne
- A6 q8_1 pisane przez rms_norm*mul/swiglu/unary*mul; alpha/beta MMVQ szablon po liczbie tokenów (9.05 -> 6.1 us); IMROPE w fuzji RMS_NORM+MUL+ROPE i sigmoid bramki bez cont; FWHT (rotacja KV) w tej samej fuzji; cherry-pick #30103.
- Kernele weryfikacji 1308 -> 972, przerwy 4.30 -> 3.23 ms.
- Potwierdzone (spec_sweep, 3 seedy, T=1): Qwen UD **36.38 ms/krok, 86.4 t/s**; Uncensored **34.52 ms/krok, 88.5 t/s**.
- DEBUG_HIP_GRAPH_BATCH_SIZE=16: bez zysku (36.44). #29768 pominięte (wymaga VMM).
- Długość draftu po zmianach: n=3 85.2 t/s (czat 75), n=4 86.4, n=5 87.6 (kod lepiej, czat 68). Zostaje n=4.
- Długi kontekst (long_ctx_bench, T=0, decode t/s): 1.7k **106.9**, 6.6k **93.4**, 29.5k **85.5**, 94k **77.7** (rano: 78.6 / 75.5 / 62.4 / 43.0).

## ROCm: draft MTP jako jeden graf (c90db29c6, 2026-10-12), bitowo identyczne drafty
- 4 przebiegi draftu (42 kernele, ~1.19 ms każdy) -> jeden graf 104 kerneli z argmax i get_rows na GPU; +180 MiB VRAM (kopia 64k wierszy token_embd).
- Catch-up nie złączony: jego praca GPU już chowa się za próbkowaniem na CPU, zysk 0.2 ms za cenę zmiany draftów.
- Potwierdzone: Qwen UD **35.67 ms/krok, 88.1 t/s**; Uncensored **33.79 ms/krok, 90.4 t/s** (tok/krok bez zmian).

## ROCm: MMVQ wielokolumnowe K1 (gałąź opt-k1, 60ce2a71f + 9f83f1f81, 2026-10-13), bitowo identyczne
- Ładowanie wag/aktywacji przez buffer resource (SGPR) + 32-bitowe offsety, nagłówki bloków jednym load-em,
  amdgpu_waves_per_eu per (typ, n) dla 5-8 kolumn (HIP-owe __launch_bounds__(n,1) blokowało to), pipelining Q6_K (n=5),
  transponowany butterfly DPP w epilogu, wagi z GLC|DLC. n=1 bez zmian (ISA identyczne).
- rocprofv3 w modelu (Qwen UD): mmvq 24.3 -> 22.1 ms na weryfikację. Serwer (spec_sweep, 2 rundy A/B):
  Qwen 35.7 -> 33.2 ms/krok (88.0 -> 94.7 t/s), Uncensored 33.8 -> 32.1 (90.3 -> 95.4 t/s).
- Mikrobench (mmvq-bench/kbench.sh, czasy kerneli z rocprofv3): runs/final_vs_base.txt. Mikrobench myli się co do
  Q6_K i GLC|DLC (w modelu zysk) -> decyzje z rocprofv3 w modelu (mmvq-bench/verify_mmvq.py).
- Nie działało: same 32-bitowe offsety bez waves_per_eu (kompilator czeka na każdy load, -5..-40%), pipelining dla
  Q4_K/Q5_K/IQ4_XS, W=6 (za mało fal dla 1280 bloków), W=16 dla 5+ kolumn, SLC/GLC osobno.

## K1: HIP MMVQ wielokolumnowe (60ce2a71f, 9f83f1f81; 2026-10-13), bitowo identyczne
- Ładowanie nagłówków bloków jednym odczytem, offsety 32-bit w SGPR, amdgpu_waves_per_eu per (typ, n) (HIP __launch_bounds__ blokował to na domyślnym), pipelining Q6_K n=5, redukcja epilogu jednym transponowanym butterfly, odczyty wag GLC|DLC.
- MMVQ w weryfikacji: 24.3 -> 22.1 ms; weryfikacja 31.0 -> 28.4 ms.
- Potwierdzone: Qwen **33.17 ms/krok, 94.7 t/s** (było 35.67/88.1); Uncensored **32.02 ms/krok, 95.4 t/s** (33.79/90.4). n=1 i prefill bez zmian.
- Nie zadziałało: same offsety 32-bit bez waves_per_eu (-5..-40%), pipelining Q4_K/Q5_K/IQ4_XS, W=6/16, SLC/GLC osobno. Liczniki PMC w rocprofv3 zwracają 0 na tym setupie.

## K2: małe kernele weryfikacji/draftu (gałąź opt-k2, ba90baf3a..849b69978, 2026-10-13), bitowo identyczne
- S1 (poprawność): (d, sum) każdego bloku q8_1 przycinane do ±65504 (quantize, MMQ DS4, FA Q, producenci A6). Bitowo bez zmian na normalnych danych.
- Para MMVQ (GGML_HIP_MMVQ_PAIR): dwa MUL_MAT tego samego typu na tym samym src1 jednym gridem (ffn up/gate, GDN qkv/z; qwen35 rozwija qkv i z obok siebie).
- rms_norm*mul(+q8_1) 5120 kol.: ładowania naraz, redukcje DPP (GGML_HIP_NORM_FAST) 5.87 -> 4.51 us. Uwaga: rozwinięta suma x*x musi być jawnym łańcuchem fmaf, inaczej backend kontraktuje inny iloczyn (1 ulp w ~4% wierszy).
- argmax: 16 ładowań w locie + DPP (GGML_HIP_ARGMAX_FAST) 16.8 -> 4.3 us (draft).
- Bramkowana norma GDN silu(z)*(rms_norm(x)*w)+q8_1 jednym kernelem (GGML_HIP_NORM_GATE): 2.68+1.84 us -> 1.87 us.
- SSM_CONV + alpha/beta GDN jednym gridem (GGML_HIP_GDN_CONV_AB): 4.68+4.90 us -> 5.54 us.
- Weryfikacja: 972 -> ~815-830 kerneli. Serwer (spec_sweep, 2 rundy A/B naprzemiennie): Qwen 33.17 -> **32.17 ms/krok, 97.7 t/s**
  (bez CONV_AB 32.50); Uncensored 32.03 -> **30.67 ms/krok, 99.6 t/s**. Greedy md5 (plain + MTP) równe 9f83f1f81 po każdym kroku.
- Zostało (z rankingu rocprofv3): set_rows K/V q4_0 2x4.6 us/warstwę attn (jedno uruchomienie), fwht V/wyjścia (do set_rows / FA combine),
  rms_norm_mul_rope 4.4/7.0 us, GDN 17.7 us (snapshoty stanu), unary_gated (swiglu) 2.7 us, małe k/v MMVQ (1024 wiersze, różne typy w UD).

## K2 + S1: opóźnienia małych kerneli (ba90baf3a..849b69978; 2026-10-13), bitowo identyczne, przełączniki GGML_HIP_*=0
- S1: clamp q8_1 (d, sum) do ±65504 we wszystkich zapisach q8_1 (poprawność).
- Para MMVQ w jednej siatce (qkv + z), szybki rms_norm*mul(+q8_1) z DPP (5.87 -> 4.51 us), argmax z DPP (16.8 -> 4.3 us), fuzja wyjściowej normy GDN z bramką SiLU, SSM_CONV + alpha/beta w jednej siatce.
- Kernele weryfikacji 972 -> ~831; przerwy 3.18 -> ~2.8 ms.
- Potwierdzone: Qwen **32.14 ms/krok, 97.8 t/s**; Uncensored **30.68 ms/krok, 99.6 t/s**.

## K3: narzut CPU (2eb088419, 56be15abf, 35d04b446; 2026-10-13), bitowo identyczne, przełączniki LLAMA_*=0
- Asynchroniczne wysyłanie wejść grafu (było 2 synchronizacje x 16 wejść/krok), osobny scheduler dla łańcucha draftu MTP (bez przebudowy grafów co krok), top-k bez pełnej tablicy 248k kandydatów i bez kopii samplera co krok.
- Host na krok: sample+accept 645 -> 140 us, post_decode 963 -> 375 us, łącznie ~-1.1 ms.
- Potwierdzone: Qwen **30.97 ms/krok, 101.5 t/s**; Uncensored **29.46 ms/krok, 103.7 t/s**.
- Długi kontekst (T=0, decode t/s): 1.7k **126.0**, 6.6k **109.4**, 29.5k **98.8**, 94k **88.3**.
- Nie zrobione: przyrostowa maska KQ (przy 94k ~0.65 ms/krok, szacunek).

## S2: draft MTP w IQ4_XS (343c2fbbb; 2026-10-13), domyślnie w run-llm.sh (MTP_TYPE=iq4_xs)
- Przekwantyzowanie przy ładowaniu: --spec-draft-head-type / --spec-mtp-type. Wagi głównego modelu nietknięte; +0.4 GB VRAM.
- Draft: 4.82 -> 3.62 ms/krok. ms/krok: Qwen 30.97 -> 29.76, Uncensored 29.46 -> 28.74.
- Akceptacja spada ~2-3% (pooled 5 seedów: 3.063 -> 3.008 tok/krok), więc zysk netto t/s ~+1-3% (średnia z 6 promptów: Qwen 99.8 -> 100.7, Uncensored 100.6 -> 103.2); czat/proza zyskuje najwięcej (pl-proza 86 -> 92, en-chat 78 -> 85), kod/technika lekko traci.
- Greedy T=0 różni się od bazy przy remisie (char 308), jak przy każdej zmianie draftów; weryfikacja bez zmian.
- Draft n=5 vs n=4 po S2: średnio Qwen 103.9 vs 100.7 (kod/technika lepiej, czat gorzej), Uncensored 101.5 vs 103.2. Zostaje n=4 do czasu T2 (długość wyceniana kosztem).

## S4: stan GDN z opóźnieniem + cofanie przez przeliczenie (3f8c8ddff..b1a203959; 2026-10-13), bitowo identyczne, LLAMA_GDN_REPLAY=0 wyłącza
- Nowy op GATED_DELTA_NET_LAG: cache trzyma zatwierdzony stan + bufory wierszy oczekujących; następna weryfikacja przelicza przyjęte wiersze. Bez 720 MiB zapisów snapshotów na weryfikację.
- GDN 793 -> 638 us/weryfikację; VRAM stanów rekurencyjnych 748 -> 195 MiB.
- Potwierdzone: Qwen **29.36 ms/krok, 102.9 t/s**; Uncensored **28.27 ms/krok, 106.1 t/s**. Cache promptu działa bez zmian (follow-up 0.64 s, powrót 1.35 s).
- Koszt: zapis stanu przy każdym żądaniu +10-15 ms prefillu (48 kopii buforów oczekujących); poprawka w stash na opt-s4.
- Conv bez zmian (snapshoty conv to 4% bajtów, zysk max ~0.03 ms).

## K4: weryfikacja 9-16 tokenów (d3a0973ae; 2026-10-13)
- Nowy kernel WMMA iu8 small-N (RDNA3) dla 9-16 kolumn (Q6_K od 7). llama-bench: n=9 49.2 -> 32.1 ms, n=16 51.0 -> 35.0 ms (Qwen); ~0.43 ms na kolumnę. n<=8 bez zmian.
- Serwer: n=5 105.4 t/s średnio (czat/proza słabiej), n=4 101.7; n>=8 dalej przegrywa: osobny klif poza mnożeniem (SSM_CONV_FUSED_MAX_SNAPSHOTS 8 -> ~470 dodatkowych kerneli cpy/concat na krok). Do naprawy razem z T2.
- Uncensored po K4: zob. spec_sweep.jsonl (przerwany pomiar; serwer agenta K4 zostawiony na porcie 8097 trzymał VRAM — zabity).

## GPU_MAX_HW_QUEUES (Strata #2305): bez efektu
- 3 restarty na ramię (domyślnie, 1, 2, 4): 29.30-29.39 ms/krok we wszystkich; brak bimodalności czasu draftu u nas.

## T1 + T2: historia conv z opóźnieniem, adaptacyjna długość draftu (gałąź opt-t2, b9b476c87, 7e9c73d8b; 2026-10-14)
- T1 (LLAMA_CONV_LAG=0 wyłącza): wiersz conv w cache trzyma okno wokół wierszy oczekujących (jak stan GDN w S4); historia = GET_ROWS kroków n_keep..n_keep+2, zapis jednym transponowanym CPY, oba złożone w SSM_CONV. Bez snapshotów, bez limitu 8.
  - rocprof weryfikacji (kernele / wall / krok): draft 8: 1391 / 34.2 / 40.8 ms -> 832 / 30.9 / 37.2; draft 12: 1585 / 36.4 / 45.7 -> 834 / 32.2 / 41.1; draft 7 bez zmian. Greedy md5 = d3a0973ae (plain, n=4/8/12, oba modele, powrót z cache promptu).
- Po T1 (spec_sweep, T=1, średnia / czat / proza): Qwen n=4 102.7/84.6/93.5, n=5 103.0, n=6 103.5, n=8 96.7, n=12 82.6; Uncensored n=4 104.7/88.4/96.5, n=5 108.4/88.5/89.3, n=6 105.0, n=8 95.9.
  Głębokość kosztuje ~1.6 ms/poziom (draft ~0.65 + kolumna weryfikacji ~1).
- T2 (--spec-draft-adaptive, opt-in): segmenty łańcucha z pewnościami głowicy, kalibracja warunkowej akceptacji na żywo (koszyki pewności x głębokość), ceny: tabela weryfikacji mierzona przy starcie + korekta na żywo, rate tok/ms na żywo; graf weryfikacji per szerokość (zmiana szerokości bez cache kosztuje ~1.6 ms/krok: przebudowa 1.24 ms + aktualizacja grafu HIP).
  - Qwen: 103.6 (czat 79.8, proza 88.8) — równo z najlepszym stałym n, czat/proza gorzej niż n=4. Uncensored: 103.5 < n=4 104.7 < n=5 108.4. Nie włączone; run-llm.sh bez zmian (n=4).
  - Nie działało: kalibracja mnożnikiem per głębokość (iloczyn pewności, nadmierne draftowanie: 87 t/s), segment 2 (102.4).

## T2 + klif conv (b9b476c87, 7e9c73d8b; 2026-10-14)
- Historia conv z opóźnieniem jak stan GDN (LLAMA_CONV_LAG=0 wyłącza): bez snapshotów conv; weryfikacja 9-16 tokenów bez dodatkowych kerneli (draft 8: 1391 -> 832 kerneli, 34.2 -> 30.9 ms weryfikacji). Bitowo identyczne.
- Adaptacyjna długość draftu wyceniana kosztem (--spec-draft-adaptive, opcjonalna): Qwen średnio 103.6 vs n=4 102.7 (kod/technika lepiej, czat/proza -5 t/s); Uncensored gorzej. Domyślnie wyłączona. Graf per szerokość weryfikacji (zmiana szerokości kosztowała 1.6 ms).
- Stałe n po naprawie (6 promptów x 2 seedy): Qwen n4 102.7, n5 103.0, n6 103.5, n8 96.7, n12 82.6; Uncensored n4 104.7, n5 108.4 (proza 96.5 -> 89.3). Domyślnie n=4 (czat/proza).
- Potwierdzone po scaleniu: Qwen 29.36 ms/krok 102.6 t/s; Uncensored 28.28 ms/krok 105.0 t/s.

## K5 + T3: prefill (6aacfea49..575e3d893; 2026-10-14), logity bitowo identyczne
- Wybór kafla MMQ na RDNA3 (alpha/beta 5120x48 na 4 CU: 932 -> 249 ms przy 32k), warstwa MTP dla wierszy promptu liczy tylko K/V (T3), kafel FA prefillu bez spilli (Q w SRAM, 40 -> 49-52 TFLOPS) + kolejność chunków dla bitowej zgodności, normalizacja q/k GDN raz na (głowa, token).
- Prefill serwera (przed -> po): UD 6.6k 913 -> 962, 29.5k 870 -> 943, 94k 668 -> 767 (141 -> 123 s); Uncensored 906 -> 956, 867 -> 941, 666 -> 762.
- Decode bez zmian (Qwen 29.40 ms/krok, Uncensored 28.30). KLD vs baza = 0 (te same logity).
- Nie zadziałało: prefetch w GDN/FA, inne kafle FA, Q5_K MMQ sweep, dequant+hipBLAS dla wszystkich typów (-15%), -ub 1024. Q6_K przez MMQ i poprawka zapisu stanu S4 nie zrobione.

## S3 + T1 (0b5b15d17, e84abb808; 2026-10-14)
- S3 okno uwagi MTP (--spec-mtp-window, domyślnie 0 = wyłączone): negatywne. W=8192: krok krótszy (-0.5 ms przy 27k, -1.6 ms przy 62k), ale akceptacja spada 3.31 -> 2.78 / 2.98 -> 2.46; t/s 105 -> 90 / 83 -> 72. W=32k też gorzej.
- T1 koszty hosta w pętli spekulacji: seq_rm po indeksie sekwencji zamiast skanu 204800 komórek, szybka maska KQ dla jednej sekwencji, kopia promptu tylko dla n-gram. Rollback+process_token 236 -> 6 us; przy 89k start weryfikacji 305 -> 139 us. Greedy md5 = baza.
- Potwierdzone: Qwen **28.94 ms/krok, 104.2 t/s**; Uncensored **27.90 ms/krok, 106.5 t/s**.
- KV draftu q4_0 (-ctkd/-ctvd q4_0): krótki kontekst bez efektu (+0.15 ms, szum akceptacji), długi: 29.5k 104.1 -> 105.2, 94k 97.5 -> 100.6 t/s, akceptacja bez zmian. Włączone domyślnie w run-llm.sh.
- Długi kontekst, stan końcowy (T=0, decode / prefill): 1.7k 130.2 / 818, 6.6k 118.5 / 985, 29.5k 105.2 / 945, 94k 100.6 / 766 t/s.

## LFM2.5-24B-A2B Q5_K_M (LiquidAI, lfm2moe, ~2B aktywnych; 2026-10-14) — baza
- Działa na forku bez zmian. ctx 131072, KV q4_0, bez MTP: 17.8 GB VRAM.
- Czat (6 promptów x 3 seedy, T=1): **173 t/s** równo na wszystkich typach tekstu (5.78 ms/token).
- llama-bench: tg128 198 t/s, pp4096 6124 t/s. Serwer: prefill 2768 (1.7k), 5805 (6.7k), 5172 (29.7k), 3709 (95k) t/s; decode 174 / 172 / 168 / 153 t/s.
- Architektura: 40 warstw (30 shortconv + 10 GQA 32/8), 2 pierwsze gęste, potem MoE 64 ekspertów / 4 aktywne (ffn 1536), emb 2048, słownik 128k, głowica związana z `token_embd` (Q6_K 205 MiB). Eksperci Q5_K (gate/up) + Q5_K/Q6_K (down) = 15.1 GiB z ~16 GiB.
- Bajty na token ≈ 0.97 GiB ekspertów (4/64) + 0.33 shortconv + 0.21 głowica + 0.10 gęste FFN + 0.07 atencja ≈ 1.8 GB -> próg pasma ~1.9 ms (~500 t/s).
- Upstream e60eff95f vs fork (llama-bench, 2 przeplatane rundy, -fa 1, KV q4_0): tg128 169.3 -> **198.3 t/s (+17%)**, pp4096 6107 -> 6180 (+1%), pp512 ~5.6k (stddev duży u obu).
- Profil rocprofv3 tg (fork): ~721 kerneli/token, zajętość GPU 3.77 ms/token (pod profilerem). mul_mat_vec_q 71% (2.69 ms, ~680 GB/s), rms_norm 5%, quantize_q8_1 3.7%, bin_bcast 3.5%, topk_moe 3.5% (3.5 us x 38), mul_mat_vec_f (router F32) 2.5%, set_rows q4_0 1.9%, ssm_conv 1.8%, FA 1.5%. Przerwy między kernelami ~3.1 us mediana; bez profilera 5.05 ms/token = ~3.8 ms pracy + ~1.3 ms przerw/host.
- Do optymalizacji: mmvq_id ekspertów (~680 -> 850 GB/s), fuzje małych opów MoE (router F32 + topk + weighted reduction, norm + quantize), mniej przerw (721 kerneli). Spekulacja: brak MTP; weryfikacja k tokenów w MoE czyta do 4k różnych ekspertów na warstwę, więc zysk ograniczony (n-gram dla kodu do sprawdzenia).

## LFM2.5: optymalizacja dekodowania (52 łatki, 0048-0052; 2026-10-14), bitowo identyczne
- Szczegóły, profil i wyniki negatywne: `research/lfm-decode.md`.
- 0048 `LLAMA_SAMPLER_FAST_PENALTIES`: szybkie top-k także za samplerem kar (GGUF LFM ma domyślnie repeat_penalty 1.05, który wyłączał szybką ścieżkę na 128k kandydatów): serwer 5.79 -> 5.11 ms/token.
- 0049 `GGML_HIP_Q8_IDS`: norma FFN zapisuje wejście q8_1 dla gate/up ekspertów (720 -> 682 kerneli/token, 5.067 -> 4.979 ms).
- 0050 `GGML_HIP_CONV_MUL`: mnożenia b*x i c*conv shortconv w kernelu SSM_CONV, który zapisuje q8_1 dla out_proj (-> 595 kerneli, 4.800 ms).
- 0051 `GGML_HIP_MOE_DOWN_REDUCE`: down ekspertów + ważenie + residual w jednym kernelu (-> 521 kerneli, 4.817 -> 4.642 ms); nowy test MOE_DOWN_REDUCE.
- 0052 `GGML_HIP_MMVQ_N1_ROWS`: 1-kolumnowy MMVQ dla K-quantów liczy 2 wiersze na blok (4.610 -> 4.509 ms).
- Wynik (przeplatane A/B z amd-opt e84abb808): llama-bench tg128 197.4 -> **220.4 t/s** (5.067 -> 4.536 ms); serwer spec_sweep `lfm none` 172.9 -> **218.6 t/s** (+26%, 217-219 na każdym typie promptu); Qwen mtp 29.12 -> 29.17 ms/krok (szum). Greedy md5 bez zmian: LFM plain, Qwen plain + MTP (sprawdzone też na zainstalowanym buildzie).
- Nie dało nic: Hadamard + quantize wyjścia atencji (4.474 -> 4.490 ms), 4 wiersze na wave, rozwijanie pętli K, `--backend-sampling` (tak szybki jak 0048, ale inny sampler, nie bitowo). Niezrobione (~0.1 ms każde): router + top-k w jednym kernelu, gate+up zapisujące q8_1 dla down.

## LFM2.5: runda 2 + KV q8_0 (54 łatki, 0053-0054; 2026-10-14), bitowo identyczne
- Decyzja użytkownika: LFM używa KV q8_0 (`run-llm.sh lfm`). Koszt vs q4_0 (llama-bench tg128, `research/lfm-kv-q4-vs-q8.md`): głębokość 0 +2.6%, 8k +5.0%, 32k +12.7%, 98k +30.1% (187 -> 144 t/s); VRAM przy 131k 18.6 -> 19.3 GB. Przyczyna przy długim kontekście: q8_0 nie ma kernela `flash_attn_ext_kvq` (tylko q4_0), więc idzie generyczny `flash_attn_ext_vec`, który czyta K/V raz na każdą głowę Q z grupy GQA (4x).
- 0053 `GGML_HIP_NORM_ROUTER`: norma FFN (z q8_1 dla gate/up) + router F32 + top-k w jednym kernelu (top-k liczy ostatni blok z licznikiem atomowym): 521 -> 445 kerneli, 4.451 -> 4.246 ms.
- 0054 `GGML_HIP_INPROJ_CONV`: shortconv wewnątrz kernela in_proj (blok, który kończy grupę 32 kanałów, liczy jej konwolucję; drugi slot cache q8_1): 445 -> 416 kerneli, 4.231 -> 4.100 ms.
- Wynik (KV q8_0, przeplatane A/B z bcdf324d3): llama-bench tg128 221.3 -> **244.1 t/s** (4.519 -> 4.097 ms); serwer spec_sweep `lfm none` 217-223 -> **238-243 t/s**; Qwen mtp bez zmian (29.15 -> 29.14 ms/krok). Greedy md5 bez zmian (LFM q8_0 2c7ee8a2, Qwen plain c4708318, MTP 6f14e814) także na zainstalowanym buildzie; hash pełnych logitów 64 kroków równy przy głębokości 0 i 3000.
- Koszty uruchomień (pomiar): granica kernela w grafie HIP ~2.53 us (także pustego), bariera siatki w kernelu trwałym 0.5-0.8 us, ogon „ostatni blok” ~1 us, łańcuch dużych faz w jednym kernelu z czekającymi blokami 8-11 us/faza (odpada).
- Losowe spowolnienie gate+up ekspertów 24.3 -> 27.2 us/wywołanie w części procesów (także na buildzie bez zmian, 4/8 profili): ~0.11 ms/token, przyczyna nieznana.
- Szczegóły i wszystkie próby: `research/lfm-decode-round2.md`.

## LFM2.5: runda 3 (59 łatek, 0055-0059; 2026-10-14)
- 0055 `GGML_HIP_KVQ_Q8`: kernel `kvq` (RDNA3, cała grupa GQA w jednym przejściu) czyta też KV q8_0 (head dim 64/128), jeden blok na WGP. ms/token: 0: 4.121 -> 4.099, 8k: 4.290 -> 4.206, 32k: 4.875 -> 4.526, 98k: 6.561 -> 5.462; atencja przy 98k 223.5 -> 128.7 us/warstwę. **Jedyna zmiana numeryki**: KLD vs f16 KV (wikitext-2, 3 x 16k, ub 1): stary kernel q8_0 0.044171 (same top 92.25%, deterministyczny), nowy 0.044196 (92.35%, RMS dp 4.85 vs 5.00%, PPL ratio 1.0026 vs 1.0138) - przyjęty. Dla porównania q4_0: 0.128 (85.2%).
- 0056 `GGML_HIP_GATE_UP_Q8`: gate+up ekspertów zapisuje wejście q8_1 dla down (4.070 -> 3.973 ms). Bitowo.
- 0057 `GGML_HIP_ATTN_PREP`: q/k norm+rope+FWHT, FWHT v i oba zapisy KV w jednym kernelu zamiast pięciu (4.043 -> 3.907 ms). Bitowo.
- 0058 `GGML_HIP_KVQ_FWHT`: combine atencji robi FWHT wyjścia i q8_1 dla o-proj (3.928 -> 3.879 ms). Bitowo.
- 0059 `GGML_HIP_INPUT_BATCH`: 12 uploadów wejść grafu na token -> jedna kopia H2D + jeden kernel rozrzucający (3.840 -> 3.806 ms). Bitowo; dotyczy też Qwena.
- Wynik (KV q8_0, przeplatane A/B z 5909da1f1): llama-bench 0: 241.1 -> **262.1 t/s**, 32k: 205.4 -> 231.0, 98k: 152.4 -> **191.4 t/s** (+25.6%); serwer `lfm none` 237-243 -> **251-252 t/s**; Qwen mtp bez zmian. 416 -> 305 kerneli/token. Greedy: LFM ze starym kernelem atencji = baza, z nowym 894e56e4 (oczekiwane); Qwen plain/MTP bez zmian (sprawdzone na zainstalowanym buildzie).
- Nie wyszło: norma następnej warstwy jako ogon kernela MoE down (13 -> 56 us/wywołanie: duży kod jednej fali z zimnego cache instrukcji); ładowania nontemporal (slc/dlc) dla wag gate+up 12.9 -> 14.4 us (wolniej, także dla pomysłu DLC z research/repos/28); losowe spowolnienie gate+up (25.1 -> 28.1 us w ~1/3 procesów) nie znika po wyrównaniu bufora modelu do 2 MiB (4/12 vs 3/12) - hipoteza: konflikt fizyczny dwóch strumieni wag gate i up.
- Referencja f16 do KLD (6.3 GB) i narzędzia: `~/wt/lfm3-prof`. Szczegóły: `research/lfm-decode-round3.md`.

## Runda 4: replay PM4 (64 łatki, 0060-0064; 2026-10-14), bitowo identyczne
- Pomiar granicy kernela (`~/wt/lfm4-prof`): graf HIP 2.75 us; każdy wariant AQL (własna kolejka ROCr, dowolny fence, kernargi w VRAM, bez bitu bariery) >= 2.08 us (koszt CP na pakiet AQL); `hipExtAnyOrderLaunch` ignorowany przez przechwytywanie strumienia; **bufor poleceń PM4** (jeden pakiet vendor, w środku osobne dispatche z wait + inwalidacją L0/K$/GL1, kernargi w VRAM) **0.46-0.86 us** (+1 us z kernargami w pamięci hosta). Sufit pasma: gorące matvec 10-20% od idealnego odczytu tych samych bajtów i siatki (suma ~0.27 ms/token).
- 0060 `GGML_HIP_PM4`: każdy przechwycony graf przebudowany jako jeden bufor PM4 na własnej kolejce ROCr, porządek ze strumieniem HIP po stronie hosta; grafy nieobsługiwane idą starą drogą. LFM 3.887 -> 3.424 ms/token. 0061 `GGML_HIP_PM4_DEBUG=1/2/3` (liczba dispatchy taśmy, czasy; rocprofv3 nie widzi dispatchy PM4). 0062 `GGML_HIP_CONV_ROWS4` (in_proj+conv 4 wiersze/blok: 3.458 -> 3.402 ms, znika rozrzut per proces). 0063 przełączniki przez `ggml_cuda_env_switch`. 0064 `GGML_HIP_MMVQ_N1_Q8_0` (Q8_0 w ścieżce 2 wierszy: LFM Uncensored 3.933 -> 3.706 ms).
- Wynik (przeplatane, spec_sweep 6x3): LFM 259.3 -> **293.6 t/s** (3.40 ms/krok); llama-bench 0: 258.5 -> 294.8, 98k: 193.4 -> 213.0. **Qwen MTP 103.7 -> 108.8 t/s** (29.16 -> 27.80 ms/krok, 2 rundy, tok/krok bez zmian); **Uncensored MTP 109.9 -> 115.3**. LFM Uncensored ~264 t/s (soak).
- Bezpieczeństwo PM4: 20 przebiegów samodzielnego testu, potem soak serwera (`pm4_soak.py`, ~4 min na model: LFM, LFM Uncensored, Qwen MTP, mieszane długości 256-2048 tok., cache promptu, follow-upy) bez zawieszeń i błędów. Greedy md5 (świeży serwer) i hashe logitów bez zmian.
- **Determinizm w obrębie jednego serwera** (`det_probe.py`): ten sam greedy request bez cache promptu daje inny tekst przy 1. i 2. wywołaniu po starcie serwera (rozjazd po ~270 znakach), identycznie przy PM4=1 i PM4=0, a **upstream e60eff95f zachowuje się tak samo** (nawet częściej). To zachowanie llama.cpp, nie łatek; porównania greedy robimy zawsze na świeżym serwerze.
- Spowolnienie gate+up per proces: to nie konflikt strumieni gate/up ani rozmieszczenie w VRAM; wyzwalacz to siatki dokładnie 3072 bloków jednej fali (pełna pojemność GPU): 2560 bloków 12.2 us zawsze, 3072 bloki 13.6 lub 14.6 us. Conv naprawiony przez 0062; gate+up nadal 25.5 vs 26.2 us (3 wiersze/blok stabilizuje, ale reszta kerneli traci ~50 us/token).
- Niezrobione: trwały kernel warstwy MoE (przy granicy 0.5-0.9 us szacunek tylko ~1.4%), leave-one-out łatek; zostaje ~16 us synchronizacji strumienia + 23 us startu/końca taśmy na token. Szczegóły: `research/lfm-decode-round4.md`.

## Sampler: szybkie top-k także z budżetem myślenia, n_probs, logit_bias, gramatyką (69 łatek, 0065-0069; 2026-10-15), te same tokeny
- 0065 `LLAMA_SERVER_REASONING_CONTROL=0` (serwer ignoruje flagę `reasoning_control` z web UI; `REASONING_CONTROL=1` w run-llm.sh ją przywraca).
- 0066 `LLAMA_SAMPLER_FAST_RBUDGET`, 0067 `LLAMA_SAMPLER_FAST_NPROBS`, 0068 `LLAMA_SAMPLER_FAST_LOGIT_BIAS` (do 64 tokenów), 0069 `LLAMA_SAMPLER_FAST_GRAMMAR` (także leniwa gramatyka narzędzi omp; nie przy `grammar_first`). Każdy `=0` przywraca pełną ścieżkę 128k/248k kandydatów.
- Weryfikacja: harness CPU 312k wektorów 0 różnic; serwer (świeży, `samp_ab.py`, seed 11, T=0.8, 800 tok.) md5 tekstu i wywołań narzędzi fast == slow we wszystkich 5 przypadkach, LFM i Qwen MTP (narzędzia LFM 2 x 2 przebiegi).

| przypadek | LFM slow -> fast | Qwen MTP slow -> fast |
|---|---|---|
| zwykły | 293.2 -> 293.3 | 104.6 -> 104.6 |
| `reasoning_control` (web UI) | 256.9 -> 292.9 | 101.6 -> 109.5 |
| budżet myślenia 2048 (UI Low/Medium/High) | 256.9 -> 292.9 | 99.3 -> 107.0 |
| narzędzia (omp, leniwa gramatyka) | 254.2 -> 294.3 | 104.8 -> 113.2 |
| `logit_bias` | 257.1 -> 292.6 | 98.9 -> 105.4 |
