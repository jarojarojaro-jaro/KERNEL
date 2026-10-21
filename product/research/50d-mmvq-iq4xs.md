# 50d. MMVQ IQ4_XS n=5: pipelining z pierścieniem rejestrów + 2 wiersze na blok (MmvqIQ4XS)

Gałąź `mmvq-iq4xs` (worktree `~/wt/mmvq-iq4xs`, baza topka 098ce134d = b659634fd + safe-io), commity:
- **862cdfbcc**: przełącznik `MMVQ_R3_PIPE_IQ4XS`, domyślnie wyłączony;
- **5fb07a00b**: ten sam przełącznik, domyślnie włączony.

Zmiana dotyczy tylko `ggml/src/ggml-cuda/mmvq.cu`, wyłącznie IQ4_XS przy ncols=5. Narzędzia leżą w `~/qwen-opt/mmvqiq4/`:
- `bench_multi.hip` + `mkmulti.sh`: jeden plik binarny zawiera N wariantów w osobnych przestrzeniach nazw. Kompilacja trwa ~7 s.
- `r*.jobs`, `g50d.jobs`.

Logi: `~/qwen-opt/queue/logs/iq4r{1,2,3}.log`, `g50d-*.log`.

## Werdykt

- **Wygrana, bitowo zgodna** na wszystkich 4 kształtach produkcyjnych (hash całego tensora wyjściowego == topka): pętla multi z pipeliningiem w pierścieniu rejestrów + 2 wiersze na blok (`ryp2`).
- Mikrobench cache-cold, ten sam przebieg, delta względem topki: para ffn **−3.7%**, down+residual **−6.8%**, up **−2.9%**, down **−6.6%**.
- Szacunek na krok `[SZACUNEK]` z czasów IQ4_XS w trasie klab (para 1.851, down+bias 1.030, up 0.856 ms/krok): **−0.16 ms/krok (~0.6%)**.
- Status bramki md5 + ABBA E0: patrz sekcja „Bramka”.

| kształt | GB/s przed → po | % z 926 | bitowo |
|---|---|---|---|
| para ffn gate\|up 2×17408×5120 | 775 → 805 | 84 → 87 | TAK |
| down+residual 5120×17408 | 756 → 811 | 82 → 88 | TAK |
| up 17408×5120 | 766 → 789 | 83 → 85 | TAK |
| down 5120×17408 (bez bias) | 748 → 801 | 81 → 87 | TAK |

(przebieg `iq4r3`, mediana z 7 rund, A/A „same” ±1%)

## Co było nie tak z istniejącym pipeliningiem (raport 46: IQ4_XS +4%)

Pętla `use_pipeline` (`w = wn`) traci z trzech powodów, widocznych w ISA:
1. **vmcnt jest w kolejności.** Prefetch wag następnej iteracji wychodzi PRZED loadami aktywacji y. Czekanie na y czeka więc też na prefetch, czyli na pełne opóźnienie DRAM.
2. **Kopia `wn → w` wymusza `s_waitcnt` przed wydaniem kolejnych loadów.** Wagi w locie nigdy nie obejmują dwóch iteracji.
3. **Trip count zależy od lane'a** (`kbx_start = tid/8`), więc wyjście z pętli jest dywergentne. Każde częściowe ostatnie przejście zostawia w pętli loady w toku na krawędzi powrotnej, a kompilator wstawia wtedy `s_waitcnt vmcnt(0)` na nagłówku pętli.

Poprawka: `mmvq_ring_step`, czyli kolejno:
- loady y;
- `sched_barrier`;
- wagi o PD iteracji do przodu, do slotu pierścienia;
- `sched_barrier`;
- unpack + dot slotu bieżącego.

Pętla jest rozwinięta PD+1 razy, bez kopii. Trip count `blocks_per_row_x / blocks_per_iter` jest jednolity dla fali, a ogon jest wyjęty z pętli. Wiersze o liczbie bloków niepodzielnej przez 4 idą starą pętlą. W ISA: na nagłówku nie ma `vmcnt(0)`, jest `vmcnt(29)`, czyli y i wagi i+1 są w locie, gdy czekamy na wagi i.

## Warianty (delta czasu vs topka, ujemna = szybciej; wszystkie bitowo zgodne)

ISA: topka 166 VGPR / 8 fal.

| wariant | VGPR/fale | para | down+bias | up | down |
|---|---|---|---|---|---|
| fale 6 / 7 / 9 / 10 / 12 (bez pipe) | 166/6 … 118/12 | −0.9 / −0.8 / +0.8 / +1.2 / +3.8 | +19.8 / −2.0 / −0.4 / −1.1 / −3.1 | −0.8 / 0 / +1.4 / +2.4 / +4.1 | +18.8 / −2.8 / −1.0 / −1.1 / −3.4 |
| rpb 2 (bez pipe) | 111/8 | −2.4 | −3.2 | −2.3 | −4.4 |
| rpb 8 / rpb 8 + 6 fal | 193/7, 230/6 | +14.6 / +6.4 | +44 / −1.1 | +21 / +17 | −0.4 / −3.3 |
| cpol 0 / 1 / 3 / 4 / 7 (obecnie 5 = GLC\|DLC) | 166/8 | ≈0 … −1.4, cp7 +28 | +16 / +7 / +15 / +2.4 / +31 | ≈0, cp7 +36 | +15 / +5 / +15 / +1.7 / +30 |
| stary pipe (kopia, x przed y) | 185/8 | +0.5 | −2.2 | **+4.9** | −3.5 |
| pipe y-first z kopią | 188/8 | 0 | −2.8 | +0.4 | −3.0 |
| pierścień PD=1, 4 wiersze (`ry`) | 191/8 | −1.4 | −1.9 / −0.4 | −0.9 | −1.7 / −2.0 |
| pierścień PD=1, 4 wiersze, 7 fal | 191/7 | −1.9 | −4.4 | −1.6 | −3.4 |
| pierścień PD=2, 4 wiersze | 244/5 | −1.6 | +0.2 | +1.7 | +0.6 |
| **pierścień PD=1, 2 wiersze (`ryp2`)** | **150/8** | **−3.7** | **−6.8** | **−2.9** | **−6.6** |
| pierścień PD=1, 2 wiersze, 10 / 12 fal | 150/9, 150/9 | −3.1 / −2.4 | −4.6 / −2.3 | −2.4 / −2.6 | −6.4 / −6.3 |
| pierścień PD=1, 4 wiersze, cpol 4 | 191/8 | −1.7 | −2.6 | −1.0 | −4.0 |

Wnioski z tabeli:
- 2 wiersze na blok wygrywają na każdym kształcie. To dwa razy więcej fal w siatce (lepszy ogon i balans przy 1280 → 2560 blokach dla down), a mniej VGPR robi miejsce na pierścień przy 8 falach.
- cpol: obecne GLC|DLC (5) zostaje. Każda inna polityka szkodzi down o 2–16%.
- Pętla z kopią buforów (pipe w topce dla Q6_K) nie daje MLP. Pierścień daje.

## Bramka

`g50d.jobs` (zakolejkowane 03:08, FIFO):
1. mikrobench rundy 4: warianty wokół zwycięzcy (fale 6/7/9/10, cpol 1/4, PD 2, rpb 1/4);
2. smoke PM4=0;
3. md5 PM4=1: Qwen c4708318 / MTP 6f14e814, LFM 894e56e4;
4. ABBA E0 prose+mvs, seedy 1,2: A = `~/llama-topka`, B = `~/wt/mmvq-iq4xs/build-hip` (5fb07a00b).

Wynik: o 03:43 (limit czasu agenta) `g50d` czekało jeszcze w kolejce FIFO. Dalej biegnie samo, a wyniki trafią do `~/qwen-opt/queue/logs/g50d-*.log`, `/tmp/p100-gate/mmvq50d.PASS` i `~/qwen-opt/mmvqiq4/logs/x50d-*`. Sprawdzone przed bramką:
- build B ma nowy kernel: `mmvq.cu.o`, IQ4_XS n5, 150 VGPR, tak jak w mikrobenchu;
- bitowa zgodność wyjść na wszystkich 4 kształtach produkcyjnych: `ryp2` w `iq4r3`, wszystkie warianty pierścienia w `iq4r2` i `iq4r3`.

Bez PASS md5 i ABBA nie adoptować.

## Do bazy wiedzy

- **vmcnt na gfx11 jest w kolejności wydania.** Prefetch wydany przed loadami, na które czekamy wcześniej, zamienia pipelining w szeregowanie. Kolejność musi być: najpierw to, czego użyjemy teraz, potem prefetch. Kompilator tego sam nie przestawi; trzeba wymusić `__builtin_amdgcn_sched_barrier(0)`.
- **Bufor `w = wn` w pętli to ukryty `s_waitcnt`.** Rotacja musi być w rozwiniętym pierścieniu rejestrów.
- **Pętla z dywergentnym trip count lub `break` w rozwiniętym ciele daje `s_waitcnt vmcnt(0)` na nagłówku.** Trip count musi być jednolity dla fali, a ogon wyjęty z pętli.
- Przy n=5 mniej wierszy na blok (2 zamiast 4) wygrywa mimo 2× więcej loadów y na bajt wag. Y siedzi w L2/L0, a liczy się MLP wag i liczba fal.
- Szybka pętla: jeden binarny mikrobench z N wariantami (namespace per wariant, `#undef` przełączników między include'ami) kompiluje się w ~7 s i mierzy wszystko w jednym slocie kolejki.
- Uwaga dla Q4_K/Q5_K/Q6_K: ta sama poprawka pipeliningu (pierścień, y-first, jednolity trip count) jest gotowa do przeniesienia (`mmvq_ring_step` jest generyczny po typie z `mmvq_xraw`). Nie mierzono.
