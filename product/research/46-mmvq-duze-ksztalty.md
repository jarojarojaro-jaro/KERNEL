# 46. MMVQ n=5 na dużych kształtach: pasmo per typ kwantyzacji, warianty pamięciowe (MmvqBig)

Gałąź `mmvq-big` (worktree `~/wt/mmvqbig`, baza topka b659634fd), commit **69f14108b**. Narzędzia i logi: `~/qwen-opt/mmvqbig/` (`bench.hip`, `bench_n1.hip`, `mk.sh`, `kst.sh`, `mb4.jobs`, `g46.jobs`), wyniki w `~/qwen-opt/queue/logs/mb4-*.log`. GPU: 1 przebieg kolejki `mb4`, ~1 min GPU (PM4=0, mikrobench), bez błędów amdgpu.

Punkt wyjścia (raport 41, X1 ATT): MMVQ spędza 70–82% czasu w `s_waitcnt vmcnt`. Dźwignie są więc po stronie pamięci: loady w locie na falę, obsadzenie a VGPR, odczyty aktywacji, ogon siatki.

## Werdykt

- **Q4_K n=5: software pipelining (wagi następnej iteracji ładowane przed bieżącym dot) + cel 8 fal/SIMD — wygrana, bitowo zgodna.**
  - 17408×5120 −15%, 16384×5120 −6%, 10240×5120 −3% (mikrobench cache-cold).
  - Szacunek na krok `[SZACUNEK]`: −0.18 ms/krok (~0.6%), z czasów Q4_K w trasie klab (0.85 + 0.61 + 0.51 ms/krok).
  - W kodzie: `MMVQ_R3_PIPE_Q4K=1`, `MMVQ_R3_WAVES_Q4K_PIPE=8` (compile-time, jak istniejące `MMVQ_R3_PIPE_Q6K`).
  - Status: bramka md5 + ABBA E0 zakolejkowane (`g46.jobs`, uruchamia je `chain46.sh` po buildzie `rbuild --local`). Wyniki: `~/qwen-opt/queue/logs/g46-*.log`, `~/qwen-opt/mmvqbig/logs/x46-*`.
- **Q5_K: pipelining jest mieszany → bez zmian.** Przy 8 falach wygrywa na >5120 wierszach (−1.6…−2.8%), ale przegrywa +1.4% na 5120-wierszowych down/out, a te dominują (73.6 uruchomień/krok, 3.9 ms). Netto ok. −0.05 ms `[SZACUNEK]`. Pełny zysk (~−0.15 ms) wymagałby wyboru instancji po liczbie wierszy w launcherze.
- **IQ4_XS: pipelining przegrywa** (up 17408 +4.4%) → bez zmian.
- **Q6_K: obecna konfiguracja jest optimum.** Bez pipeliningu: +7…+31%. 8 fal: +5…+15%.
- **Aktywacje (q8_1) nie są wąskim gardłem.** Diagnostyka `DIAG_Y` (odczyty y zamknięte w 32 blokach, wyniki celowo błędne) daje −5…+5%, bez spójnego zysku.
- **IQ4_XS n=1 z 2/4 wierszami na blok: KILL.** Jest wolniejszy o 1–2% (2 wiersze) i o 3–7% (4 wiersze). 1 wiersz na blok osiąga już 832–843 GB/s.
  - „46% pasma” dla `IQ4_XS n1 fused r17408` w `klab profile` to błąd liczenia bajtów: fused gate|up czyta dwie macierze, klab liczy jedną. Faktycznie ~850 GB/s. Zgłoszone KernelLab2.

## Pasmo per typ kwantyzacji (bazowy kernel topki, n=5, cache-cold)

Mikrobench: kopie macierzy łącznie > 640 MB (poza Infinity Cache), round robin, ABAB, mediana z 7 rund. Wynik pokrywa się z trasą modelu (Q5_K down 761 vs 756 GB/s w klab). Sufit odczytu to 926 GB/s (24r). Kontrola A/A: ±0.3% (Q4_K up 0.8%).

| typ | kształt (wiersze×K) | µs | GB/s | % z 926 |
|---|---|---|---|---|
| Q5_K | para ffn 2×17408×5120 | 154.0 | 796 | 86 |
| Q5_K | down 5120×17408 (+bias) | 80.6 (79.8) | 760 (768) | 82 |
| Q5_K | up 17408×5120 | 83.1 | 737 | 80 |
| Q5_K | qkvz 16384×5120 | 79.4 | 726 | 78 |
| Q5_K | q 12288×5120 | 57.7 | 750 | 81 |
| Q5_K | out 5120×6144 (+bias) | 30.3 (29.9) | 714 (724) | 77 |
| Q5_K | kv 1024×5120 | 10.7 | 337 | 36 |
| IQ4_XS | para ffn 2×17408×5120 | 121.4 | 780 | 84 |
| IQ4_XS | down 5120×17408 (+bias) | 61.6 (61.1) | 768 (775) | 83 |
| IQ4_XS | up 17408×5120 | 61.6 | 769 | 83 |
| Q4_K | up 17408×5120 | 74.9 | **669** | **72** |
| Q4_K | qkvz 16384×5120 | 65.0 | 726 | 78 |
| Q4_K | qkv 10240×5120 | 42.4 | 695 | 75 |
| Q6_K | down 5120×17408 (+bias) | 101.4 (99.9) | 721 (732) | 78 |
| Q6_K | out 5120×6144 (+bias) | 37.6 (36.8) | 686 (702) | 74 |
| Q6_K | kv 1024×5120 | 10.8 | 397 | 43 |
| Q6_K | głowica 248320×5120 | 1250.9 | 834 | 90 |
| IQ4_XS n=1 | gate\|up fused 17408×5120 | 113.8 | 832 | 90 |
| IQ4_XS n=1 | down 5120×17408 | 56.5 | 838 | 90 |

Q4_K był najsłabszym typem na dużych kształtach (669 GB/s na 17408 wierszach). Po zmianie: **780 GB/s (84%)**.

## Warianty (zmiana czasu var vs base; ujemna = szybciej; wszystkie bitowo zgodne poza DIAG_Y)

ISA (`kst.sh`, scratch 0 wszędzie). Bazowo: Q4_K 140 VGPR / occ 10, Q5_K 142 / 10, IQ4_XS 166 / 8, Q6_K 250 / 5.

| wariant | VGPR/occ | Q4_K up / qkvz / qkv | Q5_K para / down / out / up / q / kv | IQ4_XS para / down / up | Q6_K |
|---|---|---|---|---|---|
| pipe (fale bez zmian) | Q4_K 145/9, Q5_K 151/9, IQ4 185/8 | −0.5 / −1.0 / −2.0 | +2.0 / +1.4 / +1.8 / +1.8 / +2.5 / −11.4 | +0.1 / +1.5 / +4.7 | 0 |
| **pipe + 8 fal** | Q4_K 189/8, Q5_K 190/8 | **−14.9 / −6.3 / −3.3** | −1.6 / +1.4 / +1.4 / −2.0 / −2.8 / −18.1 | −0.1 / +1.9 / +4.4 | 0 |
| pipe + 6 fal | Q4_K 214/6, Q5_K 232/6, IQ4 185/6 | −14.3 / −5.1 / −2.0 | −2.3 / **+13.5** / **+14.2** / −0.6 / +0.7 / −16.6 | −0.6 / **+21.8** / +2.8 | 0 |
| Q6_K bez pipe, 8 fal | — | — | — | — | +0.7…+31.4 |
| Q6_K 8 fal | — | — | — | — | +1.1…+15.3 |
| DIAG_Y (diagnoza) | — | −5.2 / −1.1 / −1.8 | +0.2 / 0 / +5.2 / +1.6 / −0.8 / +14.5 | −0.4 / −2.3 / +0.9 | −12…+0 |

- 6 fal za mało obsadza 1280-blokowe uruchomienia 5120 wierszy (+13…+22%). To ta sama obserwacja co przy strojeniu `MMVQ_R3_WAVES_*`.
- Q4_K zyskuje, bo jego surowe wagi (`hdr` + `q[NI]`) są małe. Przy 8 falach kompilator trzyma dwie iteracje w rejestrach bez spadku obsadzenia poniżej progu 5120-wierszowych siatek. Q5_K ma dodatkowo `qh`, a IQ4_XS ma już 166 VGPR bez pipe.

## Adopcja

- Kandydat: `mmvq-big` @ 69f14108b. Zmiana tylko w `ggml/src/ggml-cuda/mmvq.cu` (+13/−2): `mmvq_r3_pipeline` i `mmvq_max_waves_per_eu` dla Q4_K przy n=5.
- Przełącznik compile-time: `-DMMVQ_R3_PIPE_Q4K=0` daje stary kernel.
- Bramki (`g46.jobs`):
  1. Mikrobench końcowego źródła vs topka.
  2. Smoke greedy z PM4=0.
  3. md5 PM4=1: Qwen c4708318 / MTP 6f14e814, LFM 894e56e4.
  4. ABBA E0 prose+mvs, seedy 1,2: A = `~/llama-topka`, B = `~/qwen-opt/mmvqbig/inst`.
- Po PASS bramki md5 i braku regresji w ABBA → IntegTopka2 cherry-pick 69f14108b na topkę.

## Do bazy wiedzy

- Mikrobench cache-cold (kopie > 640 MB, round robin) odtwarza pasmo MMVQ z trasy modelu z dokładnością ~1%. Wzorzec „czysty odczyt” (24r) zawyża sufit o 10–15 pp.
- Przy n=5 odczyty aktywacji q8_1 nie są wąskim gardłem. Liczą się loady wag w locie na falę i obsadzenie.
- Pipelining wag + cel fal działa tylko dla typów o małym surowym bloku na wątek (Q4_K, Q6_K). Dla Q5_K i IQ4_XS koszt VGPR zjada zysk na 5120-wierszowych siatkach.
- `klab profile`: fused n=1 z gate liczy połowę bajtów (jedną macierz zamiast dwóch).
