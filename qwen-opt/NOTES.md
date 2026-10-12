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

Underdog-Saluki 27B IQ2-mix przy tym samym ustawieniu (brak głowicy MTP):

| Konfiguracja | t/s | kod EN | proza PL | VRAM |
|---|---|---|---|---|
| Vulkan, bez spekulacji | 55.6 | 55.7 | 55.7 | 11.4 GB |
| ROCm, bez spekulacji | 47.8 | 47.9 | 47.5 | 12.5 GB |
| Vulkan, DFlash2 n=6 | 70.5 | 115.3 | 36.4 | 14.0 GB |
| ROCm, DFlash2 n=6 | 71.2 | 120.6 | 42.1 | 15.1 GB |

Szybki test jakości (`quick_quality.py`, 10 krótkich pytań EN/PL, greedy, bez thinking): Qwen 8/10,
Saluki 9/10. Za mało pytań, żeby rozróżnić modele; obie wpadki Qwena to „poszłem" uznane za poprawne
i ucięta odpowiedź (limit 200 tokenów).

## Co jest gdzie

| Ścieżka | Co |
|---|---|
| `~/llama-master` (gałąź `amd-opt`) | llama.cpp master + nasze zmiany: kernele HIP (`mmvq.cu`), cache q8_1, `--spec-draft-vocab` |
| `~/llama-opt` | zainstalowany build ROCm z tej gałęzi |
| `~/llama-opt-vk` | build Vulkan z tej gałęzi (+ `radeon_icd.json` dla RADV w przestrzeni użytkownika) |
| `~/vk` | Mesa RADV 25.2.8 rozpakowana z .deb + LunarG Vulkan SDK 1.4.363 (bez sudo) |
| `~/llama-base` | czysty upstream e60eff95f do porównań A/B |
| `~/models/draft/` | drafter DFlash2 Q4_K_M + `draft_vocab_qwen38.txt` (ranking tokenów dla draftu MTP) |
| `run-llm.sh` | start serwera: `run-llm.sh [qwen\|saluki] [mtp\|dflash\|none] [vulkan\|rocm]` |
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

Underdog-Saluki 27B IQ2-mix: bez spekulacji 46.5 t/s, DFlash2 n=7 80.6 → 91.2 z naszymi kernelami.

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
- Saluki (IQ1/IQ2): przy 1 tokenie kernele stoją na ~450–600 GB/s przez lookupy siatek (grid tables).

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
