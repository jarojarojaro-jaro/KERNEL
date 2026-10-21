# 50b. MMVQ Q5_K n=5: instancja „big_rows” (pipelining + wspólne loady nagłówka/qh/ds), MmvqQ5K

Gałąź `mmvq-q5k` (worktree `~/wt/mmvq-q5k`, baza `mmvq-big` 69f14108b). Kandydat **fd7dff630**. Zmiana tylko w `ggml/src/ggml-cuda/mmvq.cu`. Narzędzia: `~/qwen-opt/mmvqq5k/` (`bench_m.hip` = wiele wariantów w jednym binarnym pliku, `mk_m.sh`, `variants.txt`, `kst_m.sh`). Logi: `~/qwen-opt/queue/logs/q5m1-*.log` (m1) i `g50b2-*.log` (bramka). GPU: 1 przebieg mikrobencha (PM4=0), bez błędów amdgpu.

## Werdykt

- **Wygrana, bitowo zgodna: instancja `big_rows` dla Q5_K przy n=5, wybierana w launcherze po liczbie wierszy.**
  - Co robi:
    - pipelining z celem 8 fal;
    - nagłówek (dm+scales) i połówka qh ładowane jednym loadem 16 B na linię (linie 0/2/3 z ósemki bloku), rozdawane przez DPP8;
    - q8_1 `ds` też jednym loadem na linię + DPP8;
    - surowe wagi zajmują 8 VGPR na wiersz zamiast 12.
  - Wynik: **−1.3…−3.5% na 8192–34816 wierszach**.
- **Przełącznik:** env `GGML_HIP_MMVQ_Q5K_BIG_ROWS=6144`. Domyślnie off: domyślna wartość to compile-time `MMVQ_R3_PIPE_Q5K_ROWS=0`.
  - Instancja domyślna (≤ próg) jest niezmieniona.
  - Mechanizm jest typowo-agnostyczny: `mmvq_r3_has_big_rows` / `mmvq_r3_big_rows_min`, parametr szablonu `big_rows`. MmvqQ6K może go użyć dla głowicy.
- **Szacunek na krok `[SZACUNEK]`: ≈ −0.12 ms/krok (~0.4%).**
  - Liczony z trasy klab now1 (MmvqBig3), Δ% × ms/krok dla każdego kształtu:
    - fused r34816: 2.63 ms;
    - r17408: 1.14 ms;
    - fused r16384: 1.01 ms;
    - r12288: 0.45 ms;
    - r10240: 0.34 ms.
- **5120 wierszy (down/out + bias) — nic nie wygrało.** To największa pozycja (0.72 ms straty wg raportu 47).
  - Każdy wariant z pipe jest +0.1…+4% wolniejszy.
  - Same wspólne loady bez pipe: +2…+16%. Kompilator przy 96–143 VGPR gorzej rozkłada loady.
- Odrzucone:
  - pipe głębokość 2: +4…+11%, 205 VGPR → 7 fal;
  - cel 10 fal przy pipe: +1.8…+6%, 161 VGPR → 9 fal;
  - goły pipe z 46 (MmvqBig3, n0 big): mieszany −1.6…+2.3%; para 2×17408 +0.6…+0.9%, czyli w m1 nie powtórzył −1.6% z raportu 46.
- **Nie zmierzone (zakolejkowane, m3 w `g50b2-mb`):** pętla z pierścieniem rejestrów (`mmvq_ring_step`, wzorzec MmvqIQ4XS 862cdfbcc).
  - Switch `MMVQ_R3_Q5K_RING`, domyślnie 0, commit 556eae3f6.
  - Obecnie ma 244 VGPR → 5 fal. Wymaga jeszcze rpb 2 (jak IQ4_XS), żeby wrócić do 8 fal. To główny kierunek dla 5120 wierszy.

## Pasmo (cache-cold, n=5, mediana 9 rund ABAB, sufit 926 GB/s; po = `big_rows` dla > 6144)

| kształt (wiersze×K) | GB/s przed → po | % sufitu po | bitowo |
|---|---|---|---|
| para ffn 2×17408×5120 | 796 → 807 (−1.3%) | 87 | TAK |
| up 17408×5120 | 732 → 754 (−3.0%) | 81 | TAK |
| para qkvz 2×8192×5120 | 722 → 743 (−2.7%) | 80 | TAK |
| qkvz 16384×5120 | 720 → 747 (−3.5%) | 81 | TAK |
| q 12288×5120 | 744 → 769 (−3.3%) | 83 | TAK |
| 10240×5120 | 726 → 739 (−1.7%) | 80 | TAK |
| 6144×5120 | 703 → 703 (bez zmian; big +1.5%) | 76 | TAK |
| down 5120×17408 +bias | 762 → 762 (bez zmian; big +0.1%) | 82 | TAK |
| out 5120×6144 +bias | 722 → 722 (bez zmian; big +0.6%) | 78 | TAK |

- Bitowa zgodność to hash FNV całego wyjścia (oba tensory pary) vs kernel topki, na każdym kształcie i wariancie.
- Kontrola A/A (instancja domyślna gałęzi vs topka): −0.2…+0.9%.
- Pasmo bazowe zgadza się z raportem 46 w ±1%.
- ISA (big, plain/bias):
  - share+pipe: 183/184 VGPR, 8 fal, 33/34 VMEM;
  - goły pipe: 190/191 VGPR, 8 fal, 46/47 VMEM.

## Status bramek

- `g50b2.jobs` (bilet 1126493), build `~/wt/mmvqbig` @ fd7dff630:
  1. mikrobench m3 (pierścień);
  2. smoke PM4=0 z env;
  3. md5 PM4=1, ramiona `""` i `GGML_HIP_MMVQ_Q5K_BIG_ROWS=6144`: Qwen c4708318 / 6f14e814, LFM 894e56e4 → `/tmp/p100-gate/mmvq50b.PASS`;
  4. ABBA E0 prose+mvs, seedy 1,2, ten sam binarny: A = bez env, B = env (`~/qwen-opt/mmvqq5k/logs`).
- Wyniki w `~/qwen-opt/queue/logs/g50b2-*.log`. W chwili pisania: w kolejce.

## Do bazy wiedzy

- Loady współdzielone przez linie (jeden load 16 B na unikalny fragment bloku + `__builtin_amdgcn_mov_dpp8` w grupie 8 linii) są bitowo zgodne i tanie: DPP8 to modyfikator VALU.
  - Obniżają VGPR surowych wag. To one pozwalają pipeliningowi utrzymać 8 fal.
  - Selektor DPP8 musi być stałą compile-time (parametr szablonu, nie argument funkcji).
- Pipelining Q5_K: zysk na ≥ 8192 wierszach, strata na 5120–6144. Właściwy podział to wybór instancji po liczbie wierszy w launcherze. Próg 6144.
- Głębsza prefetch (2 iteracje) i wyższy cel fal przy pipe przegrywają. Liczy się obsadzenie ≥ 8 fal.
- Wiele wariantów kernela w jednym binarnym benchu (namespace na wariant, `bench_m.hip`) oznacza jedną kompilację (~40 s) i jeden job kolejki.
  - `-fsyntax-only --offload-device-only` (~2 s) łapie błędy przed 12-minutowym czekaniem na slot `cpuheavy`.
