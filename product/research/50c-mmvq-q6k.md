# 50c. MMVQ Q6_K n=5: potok z dwoma zestawami rejestrów, kolejność loadów, wspólne skale q8_1 (MmvqQ6K)

Gałąź `mmvq-q6k` (worktree `~/wt/mmvq-q6kf`, baza topka ce4df1917 = mmvq.cu z cf927413b), commit **5bd79bc23**. Gałąź eksperymentów: `mmvq-q6k-exp` 522a195e7 (`~/wt/mmvq-q6k`). Narzędzia i logi: `~/qwen-opt/mmvq-q6k/` (`bench_multi.hip`/`mkm.sh`: wiele wariantów w jednej binarce, `bench_final.hip`/`mkf.sh`: drzewo końcowe). Wyniki: `~/qwen-opt/queue/logs/q6r{1,2,3}.log`. GPU: 3 przebiegi mikrobenchu po ~7 s (PM4=0), bez błędów amdgpu.

**Status: kandydat zbudowany (`~/qwen-opt/mmvq-q6k/inst`), bramki nieuruchomione** — GPU zatrzymane decyzją użytkownika przed bramką. Jutro: `~/qwen-opt/mmvq-q6k/g50c.jobs` (niżej).

## Werdykt

- **Przyczyna słabego Q6_K: istniejąca pętla z potokiem prawie nie nakłada opóźnień.**
  - Kopia `w = wn` na końcu iteracji wymusza `s_waitcnt vmcnt(4)` przed `v_mov`, czyli czekanie na prefetch w tej samej iteracji.
  - `vmcnt` liczy w kolejności. Kompilator wydaje loady aktywacji po prefetchu wag, więc czekanie na y czeka też na wagi.
- **Poprawka (bitowo zgodna, ta sama kolejność sum per wątek):**
  - dwa zestawy rejestrów na zmianę (pętla rozwinięta ×2, bez kopii);
  - `__builtin_amdgcn_sched_barrier` trzyma kolejność: y tego kroku → prefetch wag następnego kroku → unpack + dot;
  - **wspólne skale q8_1 (DPP quad_perm):** 4 wątki quada liczą tę samą połówkę bloku. Każdy ładuje `d` jednego z 4 bloków q8_1, a DPP rozdaje je pozostałym. Daje 1 load na kolumnę zamiast 4 (−15 z 60 instrukcji VMEM na iterację).
- **Sam ping-pong bez barier jest gorszy** (+3…+4%): kompilator dalej przestawia loady.
- **Polityka cache wag `MMVQ_R3_X_CPOL=0` (bez GLC|DLC) jest dla Q6_K lepsza na wszystkich kształtach mikrobenchu.** Głowica −6.2%, down −4.9%, up −3.6%. Zgadza się to z uwagą w kodzie („Q6_K output head loses ~0.14 ms”). W kandydacie jest to osobna gałka `MMVQ_R3_X_CPOL_Q6K=0`, ale kombinacji z potokiem nie zmierzono (pomiar r6/f1 przepadł przez stop GPU).
- **Odrzucone:**
  - cel 7–8 fal bez potoku: +4…+14%;
  - 2 wiersze na blok: głowica +11…+15%;
  - GLC (c1): ±1%;
  - pierścień z wave-uniform pętlą (wzorzec IQ4_XS 862cdfbcc) przy 4 wierszach: **spill** 128–860 B scratch, nie mierzony. Przy 2 wierszach mieści się (212 VGPR, 7 fal), ale nie zmierzono.
- **`amdgpu_waves_per_eu` jest tylko wskazówką.** Przy celu 7 kompilator bierze 219–237 VGPR (6 fal), zamiast rozlewać rejestry.

## Pasmo (mikrobench cache-cold, kopie > 640 MB, mediana 7 rund, wszystkie bitowo zgodne = YES)

Najlepsza w pełni zmierzona kombinacja: `pp1qxsbw7` (ping-pong + bariery + wspólne skale q8_1 i wag + cel 7 fal, cpol 5). Kandydat w gałęzi różni się od niej w dwóch punktach:

- nie ma wspólnych skal wag (XBCAST). Efekt był mieszany: głowica −1.7 pp (pp1xsb vs pp1sb), down +0.5 pp. Porównanie `p1q` vs `p1qx` jest w r6;
- ma cpol 0.

Tej dokładnej kombinacji jeszcze nie zmierzono (f1 w `g50c.jobs`).

| kształt | GB/s przed → po | % z 926 | Δ czasu | bitowo |
|---|---|---|---|---|
| down+bias 5120×17408 | 734 → 785 | 85 | −6.5% | tak |
| out+bias 5120×6144 | 705 → 734 | 79 | −4.0% | tak |
| down 5120×17408 | 720 → 778 | 84 | −7.5% | tak |
| out 5120×6144 | 686 → 725 | 78 | −5.4% | tak |
| para ffn 2×17408×5120 | 801 → 819 | 88 | −2.2% | tak |
| up 17408×5120 | 753 → 772 | 83 | −2.5% | tak |
| kv 1024×5120 | 391 → 435 | 47 | −10.2% | tak |
| głowica 248320×5120 | 812 → 852 (pp1qxsb: 856) | 92 | −4.7% (−5.1%) | tak |
| diag 3840×17408 (całe fale) | 723 → 827 | 89 | −12.5% | tak |

- Sam `cpol 0` (bez potoku): głowica 812 → 865, down 711 → 748, para 789 → 807, up 738 → 765.
- Same wspólne skale q8_1 (bez potoku): −2…−5%, kv −11%.
- Resztka straty na 5120 wierszach to ogon siatki. 1280 bloków przypada na 960–1152 slotów (5–6 fal × 192 SIMD), a 3840 wierszy (całe fale) dają 827 GB/s.
- Szacunek na krok `[SZACUNEK]` (trasa klab `now1`, Q6_K = 3.19 ms/krok):
  - fused r5120 1.29 ms × −5% ≈ −0.065;
  - głowica 1.21 ms × −5% ≈ −0.06;
  - r1024 −0.017 (kształt MmvqBig3);
  - para i up −0.014.
  - **Razem ≈ −0.15 ms/krok.** Z `cpol 0` możliwe do ~−0.25 ms, do potwierdzenia trasą.

## Kod (gałąź mmvq-q6k 5bd79bc23, tylko `ggml/src/ggml-cuda/mmvq.cu`)

- Q6_K n=5 dostaje instancję `big_rows`: wspólny, typowo-agnostyczny parametr z MmvqQ5K, `mmvq_r3_has_big_rows` / `mmvq_r3_big_rows_min`. Domyślna instancja jest bez zmian.
- Przełącznik: env `GGML_HIP_MMVQ_Q6K_BIG_ROWS=N` (launch > N wierszy bierze nową instancję). Domyślnie `MMVQ_R3_Q6K_BIG_ROWS=0`, czyli wyłączony. `1` = wszystkie launchy Q6_K n=5.
- Gałki compile-time:
  - `MMVQ_R3_Q6K_SHARE=1` (wspólne `d` q8_1, DPP quad);
  - `MMVQ_R3_X_CPOL_Q6K=0`;
  - `MMVQ_R3_WAVES_Q6K_PP=7` (miękkie).
- `mmvq_load_y` jest rozdzielone na `mmvq_load_y_raw` + `mmvq_finish_y`, żeby część DPP szła po wydaniu prefetchu. `mmvq_load_xraw` dostało parametr szablonu `cp`.

## Rano (GPU): `~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/mmvq-q6k/g50c.jobs`

Jeden plik:
1. `g50c-mb`: mikrobench r4 (pierścień), r6 (PP+SB z cpol 0/4/2/5, z/bez wspólnych skal, 5–7 fal) i f1 (drzewo końcowe: topka vs instancja `big_rows`, warianty w6/w8/c5/bez share). Oczekiwane: f1 `big` −5…−10% na 5120 wierszach, głowica −5…−9%, wszystko YES.
2. `g50c-troff` / `g50c-tron`: trasa rocprofv3 tej samej binarki z przełącznikiem 0/1 → `klab profile ~/qwen-opt/klab/traces/q6k-{off,on}/off --by kernel`. Oczekiwane: Q6_K ≈ −0.15…−0.25 ms/krok.
3. `g50c-smoke`: greedy PM4=0 z przełącznikiem 1. Oczekiwane md5: c4708318 / 6f14e814.
4. `g50c-gate`: md5 PM4=1 WA=2 GUARD=1 SVM=0, ramiona `=0` i `=1`, Qwen + LFM (c4708318 / 6f14e814 / 894e56e4) → `/tmp/p100-gate/mmvq50c.PASS`.
5. `g50c-A1 B1 B2 A2`: ABBA E0 prose+mvs, seedy 1,2, ta sama binarka, A = `=0`, B = `=1`. Logi: `~/qwen-opt/mmvq-q6k/logs/x50c-*`.

**Reguła adopcji:**
- Warunki:
  - PASS bramki md5;
  - ABBA: B ≥ A (t/s prose i mvs, dryf A1/A2 < 1%, czas hosta ~7 ms);
  - trasa `on` < `off` dla Q6_K.
- Wtedy IntegTopka3 cherry-pickuje 5bd79bc23 i włącza go przez `MMVQ_R3_Q6K_BIG_ROWS=1` (lub env w configu topki).
- Jeśli f1 pokaże `big_c5` szybsze niż `big`: zmienić domyślne `MMVQ_R3_X_CPOL_Q6K` na 5 przed adopcją.
- Jeśli trasa `on` przegra na głowicy: próg `GGML_HIP_MMVQ_Q6K_BIG_ROWS` poniżej 248320 nie pomoże, bo głowica jest największa. Wtedy zostaje cpol 5 tylko dla głowicy (osobny próg).

## Do bazy wiedzy

- **Pętla z potokiem z kopią `w = wn` nie działa jak potok.** Kompilator czeka na prefetch (`vmcnt`) przed `v_mov` kopii w tej samej iteracji. Potrzebne są dwa zestawy rejestrów na zmianę (rozwinięcie ×2) albo pierścień.
- **`vmcnt` liczy w kolejności.** Loady aktywacji muszą wyjść przed prefetchem wag, a kolejności pilnuje `__builtin_amdgcn_sched_barrier(0)`. Bez barier ping-pong jest wolniejszy niż kopia.
- **Q6_K: 4 wątki quada (tid % 4) dzielą połówkę bloku.** Stałe per połówka (`d` q8_1, skale wag) można ładować raz na quad i rozdawać przez DPP quad_perm. Te same wartości, więc bitowo zgodnie. Strona y daje −2…−5%.
- **Q6_K i GLC|DLC (cpol 5) przegrywa w mikrobenchu na wszystkich kształtach** (głowica −6% przy cpol 0). Inne typy zyskiwały na cpol 5, więc polityka cache musi być per typ.
- **`amdgpu_waves_per_eu` to wskazówka.** Przy zbyt niskim celu kompilator przekracza budżet VGPR (237 przy celu 7), zamiast rozlewać rejestry.
- **Pierścień z wave-uniform pętlą (IQ4_XS) dla Q6_K przy 4 wierszach rozlewa rejestry** (scratch 128–860 B). Wersja ping-pong z pętlą zależną od wątku mieści się w 204–220 VGPR.
- **Ogon siatki na 5120 wierszach:** 1280 bloków na 960–1152 slotach. Kształt 3840 wierszy (całe fale) osiąga 827 GB/s wobec 778.
- **Kolejka:** współdzielony `quiet.lock` (`flock -s`) głodził runnera czekającego na wyłączność (2 × 15–25 min przestoju GPU). Poprawione flagą `/tmp/gpu-wanted` (23df077).
