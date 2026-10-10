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
