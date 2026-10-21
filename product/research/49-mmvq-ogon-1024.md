# 49. MMVQ n=5: ogon 1024-wierszowych k/v (MmvqBig3)

Gałąź `mmvq-big3` (worktree `~/wt/mmvqbig3`, baza `mmvq-big` 69f14108b), commit **52784c744** (lokalny). Zmiana tylko w `ggml/src/ggml-cuda/mmvq.cu`. Narzędzia w `~/qwen-opt/mmvqbig3/`: `bench3.hip`, `mk3.sh`, `isa.sh`, `g49c.jobs`. Wariant Q8_0 z prefetchem napisał worker DeepSeek `DsQ8small` (`~/qwen-opt/ds/out/DsQ8small.md`); przejrzałem go, zmierzyłem i odrzuciłem.

**Status: mikrobench zrobiony; bramka md5 i ABBA E0 NIE uruchomione** (GPU zatrzymane decyzją użytkownika 21.10 ~03:30, kolejka wyczyszczona). Instalacja do bramki jest gotowa: `~/qwen-opt/mmvqbig3/inst` (build 03:05, źródło = 52784c744 bez kodu ringu; z `MMVQ_R3_SMALL_PD=0` kernele są te same).

## Inwentarz (trasa klab `traces/now1/off`, topka, 104 kroki)

Wszystkie 1024-wierszowe macierze modelu to **projekcje `attn_k` / `attn_v`** 17 warstw uwagi (blk 3, 7, …, 63 i MTP blk 64), K = 5120. Razem 34 tensory: Q6_K 15, Q8_0 13, Q5_K 5, Q4_K 1.

| typ | uruch./krok | µs/uruch. | MB | GB/s | ms/krok | idealnie @90% (833 GB/s) | strata ms/krok |
|---|---|---|---|---|---|---|---|
| Q6_K n5 | 14.7 | 11.2 | 4.30 | 384 | 0.165 | 5.2 µs | 0.089 |
| Q8_0 n5 | 10.8 | 13.1 | 5.57 | 424 | 0.142 | 6.7 µs | 0.070 |
| Q5_K n5 | 4.9 | 9.9 | 3.60 | 362 | 0.049 | 4.3 µs | 0.028 |
| Q4_K n5 | 1.0 | 10.0 | 2.95 | 294 | 0.010 | 3.5 µs | 0.006 |
| n4 (wszystkie typy) | 0.6 | 8–14 | | | 0.007 | | 0.004 |
| **razem k/v** | **32** | | | | **0.373** | | **0.197** |

Pula do odzyskania: **~0.20 ms/krok (~0.6% kroku 31.2 ms)**. Wpisy `IQ4_XS n1/n5 r1024` z `klab profile` nie są k/v: model nie ma 1024-wierszowych tensorów IQ4_XS (błędne dopasowanie wierszy z siatki), pominięte.

## Przyczyna

- **To nie jest koszt uruchomienia.** Przerwa między kernelami w trasie wynosi 3.2–3.3 µs dla *wszystkich* kerneli (mediana całej trasy 3.28 µs), tyle samo przed k/v. Sam kernel trwa 10–13 µs. k i v nie sąsiadują (fwht → k → rms_norm_mul_rope → v → fwht), a mają różne typy, więc łączenie uruchomień odpada.
- **Za mało fal i łańcuch round tripów.** Tabela RDNA3 daje przy n=5 4 wiersze/blok (Q8_0: 2), 1 falę/blok. 1024 wiersze to 256 fal na 192 SIMD32 (1.3 fali/SIMD; Q8_0: 512). Każda fala robi pętlę K sekwencyjnie: 5 iteracji (Q4_K/Q5_K/Q6_K/IQ4_XS), 20 iteracji Q8_0 (ścieżka generyczna, 2 inty x na iterację). ISA bazowego Q6_K: pętla z 60 loadami i 28 `s_waitcnt vmcnt` na iterację, 250 VGPR. Q8_0: 14 loadów i 7 czekań na iterację. Czas ≈ liczba iteracji × opóźnienie DRAM, a nie pasmo.

## Warianty (mikrobench cache-cold, PM4=0, mediana 9 rund, 2 przebiegi, `~/qwen-opt/queue/logs/mb49-*.log`)

Baza: kernel topki z tabelą (4 wiersze/blok, Q8_0 2). R = wiersze/blok przez nowy `rows_override`. Zmiana czasu względem bazy, ujemna = szybciej. Wszystkie warianty bitowo zgodne (YES w każdym przypadku i przebiegu).

| 1024×5120 | baza µs (GB/s) | R=4 | R=2 | R=1 | R=1 + prefetch 5 iter. (Q8_0: 10, DeepSeek) |
|---|---|---|---|---|---|
| Q6_K | 10.8–11.0 (390–397) | +0.2% | **−9.4%** | −0.4% | +7.5% (R=2: +9.5%) |
| Q8_0 | 13.0 (430) | +11.3% | −0.3% | **−6.6%** | +0.8% |
| Q5_K | 10.65 (338) | −0.2% | −14.4% | **−16.0%** | −4.0% |
| Q4_K | 9.67 (305) | −16.3% | −17.4% | **−17.6%** | −1.1% |
| IQ4_XS | 7.98 (349) | −0.3% | −2.3% | **−9.5%** | +16.6% |
| Q5_K 2048×5120 | 15.0 (480) | −0.8% | −12.4% | +2.2% | +14% |
| Q5_K 6144×5120 | 31.0 (697) | 0 | +0.1% | +2.9% | +13% |

- **Wygrywa sama liczba wierszy na blok.** Q6_K przy 2 wierszach (przy 1 jest neutralny: ciężki blok Q6_K, 147 VGPR/6 fal, więcej fal nie pomaga), pozostałe typy przy 1.
- **Głęboki prefetch (wszystkie iteracje K najpierw, potem dot w kolejności) przegrywa wszędzie** (+1…+17% względem samego R). ISA: pełne rozwinięcie z warunkowymi loadami, 98–227 loadów i 55–98 `vmcnt` na falę. Loady y (L2) trafiają między dot-y, a VGPR rośnie (Q6_K R=4: spill 164 B). Wariant Q8_0 od DeepSeek jest bitowo zgodny i ma 30 loadów w locie przed pierwszym czekaniem (baza 14), a mimo to jest wolniejszy od zwykłego R=1 (+0.8% vs −6.6%). Oba usunięte z kodu.
- Próg: 2048 wierszy przy R=1 już przegrywa (Q5_K +2%), 6144 też. `MMVQ_R3_SMALL_ROWS` = 1024, tylko zmierzony kształt.

## Poprawka (gałąź `mmvq-big3`)

- Parametr szablonu `n1_rows` uogólniony do `rows_override` (dowolne ncols): `calc_rows_per_block`, `calc_launch_params`, `mul_mat_vec_q`, `mul_mat_vec_q_switch_fusion`.
- Launcher `case 5`, RDNA3, typy Q4_K/Q5_K/Q6_K/IQ4_XS/Q8_0, `nrows_x <= MMVQ_R3_SMALL_ROWS` (1024), bez fuzji: `rows_override = mmvq_r3_small_rpb(type)` (Q6_K 2, reszta 1). Uruchomienia z fuzją (bias/pair) zostają przy tabeli (assert w switch_fusion). `-DMMVQ_R3_SMALL_ROWS=0` przywraca stare zachowanie.
- Dlaczego bitowo: każdy wiersz liczy te same pasy, `kqs` i składniki w tej samej kolejności `tmp += …` po kbx. Redukcja (transponowany butterfly `mmvq_tsum`, offsety 16→1; Q8_0 `warp_reduce_sum`) ma to samo drzewo dla każdego P = ncols·rpb. Zmienia się tylko pas, który trzyma wynik, a dodawanie fp jest przemienne. Potwierdzone bitowo w mikrobenchu na wszystkich typach i R.

## Ile odzyskano z puli `[SZACUNEK]`

Oszczędność na uruchomienie × uruchomienia/krok (czasy z trasy): Q6_K 1.06 µs × 14.7, Q8_0 0.86 × 10.8, Q5_K 1.6 × 4.9, Q4_K 1.75 × 1.0. Razem **≈ 0.034 ms/krok, czyli ~17% puli 0.197 ms** (~0.1% kroku). Po zmianie najlepsze warianty osiągają 370–460 GB/s (40–50% sufitu). Reszta puli to stała część krótkiego kernela: rozbieg siatki i opóźnienie pierwszych bajtów przy 3–5.6 MB na uruchomienie. Dźwignią na nią nie jest kernel, tylko mniej uruchomień (taśma PM4 / scalanie grafu); k i v mają w tym modelu różne typy w 13 z 17 warstw.

## Pierścień rejestrów (wzorzec MmvqIQ4XS, 862cdfbcc) — zbudowany, niezmierzony

`MMVQ_R3_SMALL_PD` (domyślnie 0 = wyłączony): dla małych uruchomień Q4_K/Q5_K/Q6_K/IQ4_XS pętla `mmvq_ring_step` (najpierw y, potem prefetch wag do slotu pierścienia, bez kopii, liczba iteracji jednakowa w fali, ogon odcięty). Wyjaśnia to przegraną mojego prefetchu: vmcnt kończy się w kolejności, więc czekanie na y czekało też na wagi. Binarki `build/ring1`, `build/ring2` są gotowe. ISA ring1 R=1/2: 137–226 VGPR bez spilli, 30–54 `vmcnt`. ring2 Q6_K R=2 ma spill 136 B, więc pewnie przegra.

## Bramka i E0 — kroki na rano

Jeden plik: **`~/qwen-opt/mmvqbig3/g49c.jobs`**, uruchamiany `~/qwen-opt/queue/run-jobs.sh ~/qwen-opt/mmvqbig3/g49c.jobs` (przedtem `rm -f /tmp/p100-gate/mmvq49.PASS`). Zawiera:

1. `g49-mb`: mikrobench końcowego źródła (PM4=0). Oczekiwane jak w `mb49-d0u1`: R=2 dla Q6_K −9%, R=1 −6…−18% dla reszty, wszystko YES.
2. `g49-ring2`, `g49-ring1`: pierścień na małych uruchomieniach (informacyjnie, PM4=0).
3. `g49-smoke` (PM4=0, greedy) i `g49-gate`: md5 z PM4=1 (`p100_md5.sh mmvq49`, Qwen c4708318 / 6f14e814, LFM 894e56e4).
4. ABBA E0 prose+mvs, seedy 1,2: A = `~/qwen-opt/mmvqbig/inst` (69f14108b), B = `~/qwen-opt/mmvqbig3/inst`. Logi w `~/qwen-opt/mmvqbig3/logs/x49-*`.

Oczekiwany efekt: −0.03 ms/krok `[SZACUNEK]`, poniżej szumu ABBA. Kryterium przyjęcia: md5 PASS i brak regresji w ABBA (B nie gorszy niż A poza szumem; czas hosta ~7 ms, dryf A1/A2 < 1%). Wtedy IntegTopka3 bierze 52784c744 (konflikty z gałęziami mmvq-q5k/q6k/q4k/iq4xs tylko w `case 5` launchera i w sygnaturze szablonu `rows_override`). Jeśli `g49-ring1` jest wyraźnie szybszy od `g49-mb` na k/v (bit-exact YES): ustawić `MMVQ_R3_SMALL_PD=1` (domyślnie), przebudować `rbuild --local --prefix ~/qwen-opt/mmvqbig3/inst ~/wt/mmvqbig3 llama-server` i powtórzyć kroki 3–4.

## Do bazy wiedzy

- 1024-wierszowe k/v Qwen3.8-27B (34 tensory, 4 typy) tracą ~0.2 ms/krok. Przyczyną jest kształt siatki (256 fal na 192 SIMD) plus sekwencyjna pętla K, a nie koszt uruchomienia: przerwa przed nimi jest taka jak przed każdym kernelem (3.3 µs).
- Wiersze na blok to bitowo neutralna dźwignia, dopóki każdy wiersz zachowuje pasy i kolejność `tmp +=`; drzewo `mmvq_tsum` nie zależy od P. Optimum zależy od typu (Q6_K 2, lżejsze typy 1).
- Prefetch „wszystkie iteracje K naraz” na krótkich pętlach przegrywa z samym zwiększeniem liczby fal. Więcej loadów w locie na falę nie zastępuje fal.
- `#pragma unroll` nie rozwija makr w argumencie (clang). Trzeba użyć zmiennej `constexpr`.
- Tablica o rozmiarze 0 z makra w gałęzi `if constexpr` i tak jest błędem w kodzie HIP. Rozmiar trzeba zabezpieczyć `max(1, …)`.
- Procesy uruchomione z `( … &)` w narzędziu bash giną z końcem wywołania. Długie buildy odpalać przez `setsid nohup`.
