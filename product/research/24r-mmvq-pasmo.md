# 24r — pasmo MMVQ weryfikacji n=5: sufit 926 GB/s, koszt stały na uruchomienie, RPB (kill), PAIR2 (niezmierzony)

Gałęzie: `mmvq-bw` (76f0dfd33, `GGML_HIP_MMVQ_RPB`) i `mmvq-pair2` (7b446922a, `GGML_HIP_MMVQ_PAIR2` na wierzchu RPB), worktree `~/wt/mmvqbw`. Joby, narzędzia i logi: `~/qwen-opt/mmvqbw/` (`readceil.hip`, `readceil_sum.py`, `bw_*.sh`, `logs/`) oraz `~/qwen-opt/mmvqn5/launch_bw.py`.

## Werdykt

- **Sufit zmierzony: 926 GB/s** czystego odczytu strumieniowego (b128, 64 MB–1 GB, rocprofv3) = 96.5% z 960. To jest „100%” dla naszych kerneli (`logs/readceil.sum.txt`).
- Weryfikacja n=5 czyta 16.15 GB w 21.2 ms, czyli **762 GB/s = 82% sufitu**.
- Strata to **koszt stały na uruchomienie**: ~7–9 µs na każdy z 340 MMVQ w kroku, łącznie ~2.4 ms. Pasmo asymptotyczne z dopasowania do śladu to 837–873 GB/s (90–94% sufitu).
- **RPB=1 (1 wiersz na blok w uruchomieniach ≤ 6144 wierszy): KILL.**
  - Poprawność: bitowo identyczny (`mm_dump2` 160 hashy, md5 c4708318/6f14e814).
  - spec_sweep T=1, 3 seedy: **−3.0%**, 27.98 → 28.80 ms/step, na wszystkich 6 promptach.
  - Czysty odczyt przy R=1 jest szybszy (5120×6144: 775 → 835 GB/s), ale prawdziwy kernel traci, bo każdy wiersz osobno ładuje i rozpakowuje aktywacje (5 kolumn q8_1) `[INFERENCE]`.
- **PAIR2 (mieszane typy w parze): zakodowany (7b446922a), niezbudowany.** rbuild przerwało zerwane połączenie z farmą. Niezmierzony.

## Liczby

**Ślad rzeczywistego kroku** (`vcost/prof-gv1/off`, MTP n=4, GPU_VERIFY=1, mediana 107 kroków):
- Kroki: 840 kerneli, wall 27.4 ms, busy 24.6 ms. Mediana przerwy po MMVQ: 3.28 µs.
- MMVQ n=5: 340 uruchomień, 21.8 ms.

| uruchomienie (typ, wiersze×K) | n/krok | µs | GB/s | % sufitu 926 |
|---|---|---|---|---|
| Q5_K para ffn 34816×5120 | 17 | 148.8 | 823 | 89 |
| Q5_K down 5120×17408 | 33 | 75.7 | 810 | 87 |
| Q5_K ssm_out/attn_out 5120×6144 | 38 | 33.0 | **655** | **71** |
| Q6_K głowica 248320×5120 | 1 | 1234 | 845 | 91 |
| Q6_K 5120×6144 | 20 | 39.6 | 652 | 70 |
| Q4_K 10240×5120 (qkv bez pary) | 14 | 41.6 | 708 | 76 |
| Q6_K/Q5_K k,v 1024×5120 | 19 | 9.6–11.5 | **370** | **40** |

**Sufit wzorca** (`readceil.hip`: jedna fala na blok czyta R wierszy po kolei, b128, bez arytmetyki, cache-cold; pełna tabela w `logs/readceil.sum.txt`):

| kształt | R=4 (dziś) | R=2 | R=1 |
|---|---|---|---|
| Q5_K para 34816×5120 | 878 | 895 | 908 |
| Q5_K 5120×6144 | 768 | 814 | **829** |
| Q5_K down 5120×17408 | 868 | 864 | 876 |
| Q5_K 1024×5120 | 421 | 621 | **652** |
| Q5_K 12288×5120 | 789 | 803 | 832 |

- Nawet czysty odczyt przy 4 wierszach na blok traci w małych uruchomieniach (1280 bloków jednofalowych): to rampa i ogon siatki.
- R=1 podnosi sufit wzorca o 8% dla 5120×6144 i o 55% dla 1024 wierszy.

## Zmiany (domyślnie wyłączone, bitowe)

1. **`GGML_HIP_MMVQ_RPB=1|2|4` + `GGML_HIP_MMVQ_RPB_ROWS=N`**: liczba wierszy na blok w 2..8-kolumnowym MMVQ dla typów Qwena, w uruchomieniach do N wierszy.
   - Kolejność sum się nie zmienia: transponowany butterfly redukuje każdy element parami warp_reduce_sum.
   - ISA n=5: Q4_K R1/R2/R4 = 79/102/140 VGPR, Q5_K 88/111/142, Q6_K 109/148/250.
   - Bramka: `mm_dump2` przy RPB=1 jest **identyczny z topką** (160 hashy).
   - RPB=2 nie skończył się w budżecie bramki (zawieszenie albo wolny przebieg, przyczyna nieznana, bez faultu GPU). Wyłączony do diagnozy (`bw_diag2.sh`).
2. **`GGML_HIP_MMVQ_PAIR2=1`**: para MMVQ (to samo src1) także dla różnych typów Q4_K/Q5_K/IQ4_XS, przez `mul_mat_vec_q_pair2<t0,t1,n>`.
   - Bloki pierwszej macierzy liczą ciałem t0, reszta ciałem t1, każde bitowo jak osobne uruchomienie.
   - Qwen ma 23 warstwy GDN (qkv/z) i 17 FFN (gate/up) o mieszanych typach, więc krok traci **40 uruchomień**.
   - Szacunek: ~0.3–0.5 ms/krok `[SZACUNEK]`.
   - ISA: 0 scratch, VGPR = max z dwóch ciał (np. Q5_K+IQ4_XS n5: 168).
   - Ciało kernela przeniesiono do `mul_mat_vec_q_body`. Domyślne kernele mają te same VGPR, a instrukcje pętli różnią się o ±1%.

## Akcje / następne kroki

- Nic do instalacji. RPB zostaje w gałęzi `mmvq-bw` jako zapis negatywnego wyniku (domyślnie wyłączony).
- Następny krok to PAIR2 (`mmvq-pair2`, 7b446922a). Wymaga kodu RPB tylko przez parametr `rows`, więc da się go przenieść na topkę bez instancji RPB.
  1. Po postawieniu farmy: `rbuild --prefix ~/qwen-opt/mmvqbw/p2 ~/wt/mmvqbw`.
  2. Bramka: greedy md5 z `GGML_HIP_MMVQ_PAIR2=1` (`bw_md5.sh`; `mm_dump2` nie testuje par).
  3. A/B: `bw_arm.sh` z `BIN=~/qwen-opt/mmvqbw/p2`.
  - Oczekiwanie: −40 uruchomień na krok, `[SZACUNEK]` 0.3–0.5 ms/step.
- RPB=2 nie skończył `mm_dump2` w 200–300 s. Przyczyna nieznana (diagnoza: `bw_diag2.sh`), ale idea jest zabita.
- Split-K dla down (K=17408) pominięty: zmienia kolejność sum, a down ma już 87% sufitu.

## Do bazy wiedzy

- Zmierzony sufit odczytu XTX: **926 GB/s** (96.5% z 960, stream b128, 64 MB–1 GB, rocprofv3). Procenty pasma kerneli liczyć od 926, nie od 960.
- MMVQ n=5 w Qwenie: koszt stały ~7–9 µs na uruchomienie plus 3.3 µs przerwy, przy pasmie asymptotycznym 840–870 GB/s. Strata (~2.4 ms/krok) jest w liczbie i rozmiarze uruchomień, nie w pętli kernela.
- Sufit wzorca „jedna fala, R wierszy na blok”: przy małych siatkach (1280 bloków) R=4 traci 8% (5120×6144), a przy 256 blokach (1024 wiersze) 35%.
- Mniej wierszy na blok w MMVQ n=5 (więcej fal, krótsze ogony siatki) **przegrywa w modelu: −3%** (24r), choć czysty odczyt tym wzorcem zyskuje do +55%. Reużycie aktywacji między 4 wierszami bloku jest warte więcej niż rampa i ogon. Nie ruszać rows-per-block przy n=5.
- Sufit wzorca (czysty odczyt, R=4) dla małych siatek: 5120×6144 = 84%, 1024 wiersze = 27–45% sufitu. Te uruchomienia da się przyspieszyć tylko przez zmniejszenie ich liczby (fuzja, para), nie przez kształt bloku.
