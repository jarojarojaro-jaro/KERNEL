# 24n — MMVQ ncols=5: obłożenie (VGPR → fale) per typ i ncols, przełącznik `GGML_HIP_MMVQ_OCC`

Gałąź `mmvq-n5` (`~/wt/mmvqn5`, z `topka` f2217bac7), commit e6f9882ec. Narzędzia ISA i joby: `~/qwen-opt/mmvqn5/` (`isa_s.sh`, `kstat.py`, `loopstat.py`, `mb_summary.py`, `occ_*.sh`). Logi: `~/qwen-opt/queue/logs/occ-*.log`, `~/qwen-opt/mmvqn5/logs/`.

## Werdykt

**KILL. Wyższe obłożenie nie przyspiesza MMVQ n=5. Topki nie zmieniamy.**

- Poprawność jest pełna. Wyjście jest bitowo identyczne na obu poziomach, a md5 się zgadzają.
- Poziom 1 (czyste warianty, ładowania nadal w locie): mikrobench +0.3% (szum ±2%), e2e **−0.5%**. Wolniej na każdym z 6 promptów; rozrzut A/A to 0.02 ms.
- Poziom 2 (warianty z serializacją ładowań): **−6.4%** e2e.
- Hipoteza z 24f („klif 140 → 119 VGPR da 12 fal i zysk”) jest obalona: 10 → 12 fal przy Q4_K n=5 nie zmienia przepustowości. MMVQ n=5 nie jest ograniczone liczbą fal ani ładowań w locie.

## Co zmieniono

- `mul_mat_vec_q` dostał parametr szablonu `int occ`. Dla `occ > 0` kernel ma `amdgpu_waves_per_eu(min = cel, max)`, a cel pochodzi z tabeli `mmvq_occ_table(type, ncols, level)`. Minimum fal wyznacza budżet rejestrów.
- `amdgpu_num_vgpr` wymaga literału: w szablonie daje błąd „attribute requires an integer constant”. Przy stałej wartości generuje ten sam kod co `waves_per_eu(min)`. Sprawdzone dla 120/12, 120/10, 144/10 i 168/9.
- Instancje tworzone są tylko dla wpisów tabeli. Domyślne kernele mają te same atrybuty, VGPR i pętle co w topce (diff `loopstat.py`).
- `GGML_HIP_MMVQ_OCC=1|2` (domyślnie 0) wybiera instancję w runtime, tylko na RDNA3_0. Zmienia się wyłącznie alokacja rejestrów i harmonogram. Matematyka i kolejność sum zostają te same.

## ISA gfx1100 (VGPR / fale sprzętowe; granulacja 24 z 1536)

Typy z gguf (bajty wag na krok): Q5_K 7.93 GB (47%), IQ4_XS 3.13 (19%), Q6_K 2.86 (17%, w tym głowica 1.04), Q4_K 2.34 (14%), IQ4_NL 0.28, Q8_0 0.13, Q3_K 0.11, IQ3_S 0.04.

| typ | n | topka | poziom 1 | poziom 2 | uwagi |
|---|---|---|---|---|---|
| Q4_K | 5 | 140/10 | **119/12** | = | pętla: vmcnt 17→0, +5% instrukcji |
| Q4_K | 6 | 142/10 | **120/12** (min 10, max 16) | = | (12,12) daje 20 B scratch |
| Q4_K | 7 / 8 | 179/8, 190/8 | **166/9** | = | |
| Q5_K | 5 | 142/10 | – | 95/16 | 12 fal tylko przez serializację (vmcnt(0) ×9 w pętli, +31% instrukcji) |
| Q5_K | 6 | 147/9 | – | 123/10 | serializacja (vmcnt(0) ×24) |
| Q5_K | 7 / 8 | 184/8, 190/8 | – | – | 9 fal = scratch 12–16 B |
| Q6_K | 5 | 250/5 (pipeline) | – | 138/10 | serializacja (vmcnt(0) ×25) |
| Q6_K | 4 / 6 | 98/12, 202/7 | – | – | wyższe fale = scratch |
| IQ4_XS | 5 | 166/9 | **138/10** | 119/12 | poziom 1: ta sama pętla (504 instr.) |
| IQ4_XS | 6 / 7 / 8 | 179/8, 186/8, 186/8 | **141/10, 141/10, 165/9** | = | |
| IQ4_NL | 5 / 7 | 106/12, 130/10 | **94/16, 118/12** | = | |
| IQ3_S | 5 / 6 | 190/8, 192/8 | **167/9** | = | |
| Q3_K | 8 | 134/10 | – | 113/12 | +13% instrukcji |
| Q8_0, n=2–4 wszystkie | | ≤ 96 albo 12–16 fal | – | – | nic do zyskania |

## Pomiary (RX 7900 XTX, joby `occ1.jobs`, 2026-10-20)

**Bramka (`occ-gate`, `occ-md5-*`):**
- `mm_dump2` (Q4_K…IQ2_XXS, k=5120, m=1024/1021, n=1..8; 160 hashy) przy OCC=0/1/2 jest **identyczny** z `~/llama-topka`.
- test-backend-ops MUL_MAT (8 typów modelu, n=1..9 plus Q4_K/Q5_K n=1..16) przy OCC=1 i OCC=2: 624/624 OK.
- Greedy md5 (off/1/2): Qwen plain c4708318, MTP 6f14e814, LFM 894e56e4 we wszystkich ramionach.

**Mikrobench ncols=5** (`mmvq_bench`, cache-cold, kształty Qwena; po 1 przebiegu na ramię, `occ-mb5-1`). Typy bez wpisu w tabeli mają w obu ramionach ten sam kernel, a różnią się o ±2%: to jest szum.

| kształt (typ k×n) | OCC=0 µs | OCC=1 µs | Δ |
|---|---|---|---|
| Q4_K 5120×17408 (119/12 vs 140/10) | 78.30 | 76.01 | −2.9% |
| Q4_K 17408×5120 | 72.36 | 74.27 | +2.6% |
| Q4_K 5120×10240 | 46.63 | 47.54 | +2.0% |
| IQ4_XS 5120×17408 (138/10 vs 166/9) | 67.54 | 69.92 | +3.5% |
| IQ4_XS 5120×12288 | 49.13 | 50.60 | +3.0% |
| IQ4_NL 5120×17408 (94/16 vs 106/12) | 76.28 | 76.94 | +0.9% |
| szum: Q5_K 5120×12288 / Q8_0 6144×5120 (ten sam kernel) | 63.64 / 50.05 | 62.48 / 48.81 | −1.8% / −2.5% |
| **cały krok weryfikacji n=5 (szacunek z liczby tensorów)** | **26.22 ms** | **26.29 ms** | +0.3% |

**E2E spec_sweep** (T=1, 5 seedów, topka-config: MTP n=4 + lookup W16, PM4 WA=2, GPU_VERIFY=1; kolejność A B C C B A, `occ-sweep-1/2`):

| ramię | t/s (średnia) | ms/step (średnia 6 promptów) | tok/step |
|---|---|---|---|
| A: off (= topka) | 111.4 | 27.64 | bez zmian |
| B: `GGML_HIP_MMVQ_OCC=1` | 110.8 (**−0.5%**) | 27.78 | bez zmian |
| C: `GGML_HIP_MMVQ_OCC=2` | 104.3 (**−6.4%**) | 29.53 | bez zmian |

mvs i mikrobench n=6..8 pominięto (Main: tylko przy zysku w sweepie).

## Akcje

- Nic do instalacji. Gałąź `mmvq-n5` zostaje jako zapis negatywnego wyniku. Przełącznik jest domyślnie wyłączony, a domyślne kernele są identyczne z topką.
- Kolejny krok to nie obłożenie, tylko struktura pracy: rampa i ogon siatki, jedno uruchomienie dla macierzy o wspólnym wejściu, split-K dla K=17408. Zob. 24r.

## Do bazy wiedzy

- gfx1100: `amdgpu_waves_per_eu(W, W)` z minimum W działa jak `amdgpu_num_vgpr(1536/W w dół do 24)` i przyjmuje argument zależny od szablonu. `amdgpu_num_vgpr` go nie przyjmuje (tylko literał). Sam limit max (1, 12) zostawia Q4_K n=5 na 121 VGPR, czyli 10 fal.
- Kompilator dochodzi do wyższego obłożenia na dwa sposoby. (a) Pętla zachowuje ładowania w locie: Q4_K n5/n6, IQ4_XS, IQ4_NL, IQ3_S. (b) Zapada się do „czekaj na każde ładowanie” (seria vmcnt(0), +30% instrukcji): Q5_K n5/n6, Q6_K n5, IQ4_NL n6/n8. Q5_K, który niesie 47% bajtów, nie ma czystego wariantu 12 fal.
- `~/qwen-opt/mmvq-bench/mmvq_bench` ma DT_RPATH = `~/llama-opt/lib`, więc `LD_LIBRARY_PATH` (np. w `kbench.sh`) jest ignorowany i bench zawsze mierzy llama-opt. **Wcześniejsze porównania z `kbench.sh`/`exp.sh` między buildami trzeba sprawdzić.** Kopia z unieszkodliwionym RPATH: `~/qwen-opt/mmvqn5/mmvq_bench`.
- MMVQ n=5 na gfx1100 nie zależy od liczby fal. Q4_K 10 → 12 fal, IQ4_XS 9 → 10 i IQ4_NL 12 → 16 (przy zachowanych ładowaniach w locie) dają ±3% w obie strony. Na krok wychodzi −0.5% e2e. Warianty, które dochodzą do obłożenia serializacją ładowań, tracą 6.4%. Pomysł „więcej fal dla MMVQ” jest zamknięty (24n).
- test-backend-ops wypisuje `Backend X: \033[1;32mOK`. Wzorzec `grep "Backend .*: OK"` (np. w `gv_tbo.sh`) nigdy go nie łapie. Właściwy wzorzec to `Backend .*OK`.
