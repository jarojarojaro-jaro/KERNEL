# 24h – jeden przebieg KV w `fattn-kvq` dla weryfikacji MTP (W 2–17)

**Werdykt: nie wdrażać teraz. Sufit dla MTP n=4 (W=5) przy 94k to +3.0…6.6% e2e (górna granica = idealny odczyt jednokrotny), przy 32k ≤ 2.3%. Cel +8% jest nieosiągalny nawet w idealnym przypadku. Sensowny zysk widać tylko dla szerokich weryfikacji lookup (W ≥ 11), ale tam nie zmierzyliśmy jeszcze udziału kroku.** Kod kernela nie zmieniony. Ścieżka bitowa nietknięta.

## Pomiar (test-backend-ops perf, FA D256 GQA 6, KV q4_0, `kvpass` @ 2821e1303, gfx1100, topka działała równolegle)

| kv \ nb | 1 | 2 | 3 | 5 | 6 | 8 | 11 | 16 |
|---|---|---|---|---|---|---|---|---|
| 2048 | 12.3 | 14.7 | 18.2 | 17.8 | 18.7 | 19.3 | 25.2 | 39.3 µs |
| 32768 | 57.1 | 59.1 | 99.5 | 101.4 | 142.1 | 145.0 | 268.4 | 283.3 µs |
| 98304 | 161.1 | 164.8 | 292.6 | 296.5 | 424.8 | 428.2 | 773.1 | 831.4 µs |

- Czas zależy od liczby kafli 16 wierszy, `ceil(6·W/16)`: przy 98k ≈ 33 µs stałego kosztu + **~130 µs na kafel**. Każdy kafel to osobny pełny odczyt KV (113 MB q4_0 K+V na warstwę przy 98k). 130 µs to ~870 GB/s, czyli prawie szczyt pasma. Narzut zależy więc od pasma, nie od obliczeń.
- KV czytany jest 1× dla W 1–2, 2× dla W 3–5, 3× dla W 6–8, 5–6× dla W 11–16 (zgodnie z zadaniem: „2–6×”).

## Sufit e2e (16 warstw z pełną atencją, krok MTP przy 94k ≈ 35 ms wg raportu 21m; 16×296.5 µs = 4.7 ms = 13.6% kroku, zgodne z 14% z 21m)

| przypadek | dziś / warstwę | jeden przebieg: dolna granica (pasmo) … realnie | oszczędność / krok | e2e |
|---|---|---|---|---|
| MTP W=5 @94k | 297 µs | 165 … ~235 µs | 1.0–2.1 ms | **+3.0…6.6%** |
| MTP W=5 @32k | 101 µs | 59 … ~85 µs | 0.26–0.67 ms | ≤ +2.3% |
| lookup W=16/17 @94k | 831 µs (~950 przy 7 kaflach) | ≥ 165 µs + 6–7× WMMA (52–100 µs/kafel `[SZACUNEK]`) | 4–9 ms na krok z draftem lookup | zależy od udziału kroków lookup (nie zmierzone) |

„Realnie” to `[INFERENCE]`. Przy jednym przebiegu zostają WMMA + softmax dla każdego kafla. 6.4 GFLOP na kafel to 52 µs przy szczycie 123 TFLOPS f16, a ~100 µs przy ~60 TFLOPS. Kernel prefill osiąga 50 TFLOPS (nb512: 8.2 ms przy 32k). Rejestry/LDS dla 2–7 kafli naraz na blok obniżą obsadzenie. Przy W=5 realny zysk to więc bliżej dolnej połowy przedziału.

## Decyzja
- **Kill dla celu „+8% MTP @94–113k”**: idealny sufit to 6.6% przy 94k (przy 113k ~7%, bo krok rośnie razem z atencją). Prawdopodobny wynik to ~3–4%, czyli na granicy progu 3%. Przepisanie kernela (wiele kafli akumulowanych na jeden odczyt K/V, bitowa ścieżka osobno) nie jest uzasadnione samym MTP.
- **Ewentualny następca:** jeden przebieg tylko dla W ≥ 6 (lookup W=16). Najpierw trzeba zmierzyć udział kroków weryfikacji lookup w zegarze sesji copy/code-edit przy długim kontekście.

## Nie zrobione (pauza GPU, termin 18:18 UTC)
- rocprof udziału atencji na serwerze przy 32k/94k i long_ctx_bench. Zamiast tego użyto mikrobenchmarku i kroku 35 ms z raportu 21m.
- Implementacja, md5 greedy, ABBA, spec_sweep.

Commit `0bca59f74` (`~/wt/kvpass`): przypadki perf W 3/6/11/16 w test-backend-ops (sama zmiana testu).

## Do bazy wiedzy
- `fattn-kvq` przy 98k kosztuje ~130 µs na każdy kafel 16 wierszy (`ceil(6·W/16)`) plus ~33 µs stałego kosztu. Każdy kafel czyta cały KV prawie z pełnym pasmem. Pomiar: d98304 n1/2/3/5/6/8/11/16 = 161/165/293/297/425/428/773/831 µs.
- Sufit jednego przebiegu KV dla MTP W=5: +3.0…6.6% przy 94k, ≤ 2.3% przy 32k. Cel +8% jest nieosiągalny. Temat ma sens tylko dla szerokiej weryfikacji lookup.
