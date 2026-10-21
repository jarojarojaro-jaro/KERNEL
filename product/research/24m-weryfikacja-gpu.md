# 24m: weryfikacja draftu bez kopii logitów (LLAMA_GPU_VERIFY), 2026-10-19

**Werdykt: wygrana i bezstratna, do wdrożenia w topce.**
- Kod (W16) przyspiesza o **+2.2…2.4%**, czyli o 0.7–0.8 ms/krok. Czat zyskuje +0.5% (−0.14 ms/krok), bez regresji.
- Wyjście jest identyczne bitowo przy T=0 i przy T=1 (md5 dla każdego promptu i seeda).
- Gałąź `gpu-verify` (`~/wt/gpuverify`, commit `f2217bac7` na topce `caf2b8e14`), przełącznik `LLAMA_GPU_VERIFY=1`, domyślnie wyłączony.

## Przyczyna przerw (analiza CPU: kod + ślady 24k)
Kolejność w serwerze: `decode` → `llama_synchronize` → `common_speculative_process` (catch-up MTP, 13 kerneli) → `post_decode` (próbkowanie + akceptacja) → następny krok.
- **Przerwa 1** (głowa LM → catch-up, 0.96 ms przy W16 wobec 0.37 ms przy MTP):
  - synchronizacja czeka na kopię D2H 16 × 248320 × f32 = 16 MB, czyli ~0.045 ms na wiersz;
  - do tego przygotowanie catch-upu.
- **Przerwa 2** (catch-up → weryfikacja, 0.99 ms w krokach łańcucha):
  - próbkowanie na CPU: `set_logits_top_k` przegląda cały wiersz 1 MB (SSE, pamięć pinned prosto po DMA), ok. 50–60 µs na przyjęty wiersz;
  - przy ~14 przyjętych wierszach to ok. 0.8 ms;
  - przy MTP (5 wierszy) przerwa 2 wynosi 0.29 ms.

## Zmiana
- **Graf weryfikacji** (2..64 wyjść w jednym ubatchu, bez backend samplerów) dostaje `TOP_K(m=128)` + `GET_ROWS` (wartości) + `SUM_ROWS`. `SUM_ROWS` to flaga NaN/inf.
- **Na host** idzie 16 × 128 × 8 B zamiast 16 MB. Pełne wiersze zostają na GPU i są kopiowane na żądanie przez `llama_get_logits_ith` / `llama_get_logits`, ważne do następnego decode (`gv_fetch`, `gv_drop`).
- **Sampler** (ścieżka `LLAMA_SAMPLER_FAST_TOPK`) wybiera z kandydatów (`common_top_k_distinct_topm`).
  - Kandydaci tworzą zbiór top-m bez NaN/inf, a m ≥ k+1. Wtedy k+1 największych kandydatów ma te same wartości co k+1 największych w wierszu.
  - Dlatego wynik testu „różne” i lista top-k (id, logit, kolejność) są identyczne z wynikiem na pełnym wierszu, a dalszy łańcuch (temp, dist/RNG, odrzucanie) dostaje te same dane. Daje to bitową zgodność **przy każdej temperaturze**.
  - Remisy, NaN/inf, logit-bias, FORCING budżetu rozumowania, grammar-first i n_probs idą jak dotąd przez pełny wiersz (kopia na żądanie).
- **Sprawdzenie CPU:** 20 000 losowych wierszy (remisy, ±0, k 1..60, m do k+80), wersja gęsta i top-m zgodne w 100%, z czego 9816 wierszy to fallbacki.
- **Upstream backend sampling:** nie użyty, bo wyłącza się przy budżecie rozumowania (`common/sampling.cpp:585`) i nie obsługuje wielu wyjść na sekwencję w weryfikacji.

## Tabela (XTX, flagi run-topka, PM4 WA=2, świeże serwery, `~/qwen-opt/gpuverify/logs`)
| test | A: off | B: `LLAMA_GPU_VERIFY=1` | Δ | md5 |
|---|---|---|---|---|
| mvs T=0 W16, 1024 tok., 2× ABBA (8 ramion) | 410.4 t/s, 34.67 ms/krok | 420.1 t/s, 33.86 ms/krok | **+2.4%**, −0.81 ms | 4/4 identyczne (= e3 topka) |
| copy short T=0, ABBA | 359.7 t/s, 34.11 ms/krok | 367.6 t/s, 33.40 ms/krok | **+2.2%**, −0.71 ms | 6/6 identyczne (= e1/e3) |
| copy short T=1, seedy 1,2, ABBA | 329.1 t/s, 34.62 ms/krok | 335.5 t/s, 33.97 ms/krok | +2.0%, −0.64 ms | 12/12 identyczne |
| spec_sweep T=1, 5 seedów, ABBA (czat) | 111.0 t/s, 27.75 ms/krok | 111.5 t/s, 27.61 ms/krok | +0.5%, −0.14 ms | tok/krok identyczne |
| greedy md5 (Qwen plain / MTP, LFM) | c4708318 / 6f14e814, 894e56e4 | to samo | – | on == off |
| test-backend-ops | – | TOP_K 533/533, GET_ROWS 222/222, SUM_ROWS 10/10, MUL_MAT q6_K 62/62 | – | – |

Rozrzut między ramionami ≤ 0.3%. Każde ramię B jest szybsze od każdego ramienia A.

**Ślad rocprofv3** (mvs-pad.cu, PM4 off, ten sam binarny plik; `vcost/prof-gv0/w16` vs `prof-gv1/{off,w16}`):

| krok | wall | busy | bezczynność | przerwy > 40 µs |
|---|---|---|---|---|
| W16 off | 37.38 | 31.52 | 5.86 | 2.84 ms (0.96 + 0.99 + 0.05) |
| W16 on | 36.46 | 31.85 | **4.61** | **1.54 ms** (0.38 + 0.16 + 0.05) |
| MTP off (topka, 24k) | 30.99 | 26.85 | 4.14 | 0.94 |
| MTP on | 30.83 | 26.97 | 3.86 | 0.56 |

Kernele top-k kosztują 0.16 ms/krok przy W16 (0.08 przy 5 wierszach). To 11 uruchomień radix, ok. 4 przebiegi po 16 MB.

## Akcje
1. Wdrożyć w topce: `LLAMA_GPU_VERIFY=1` w `run-topka.sh` (instrukcja poniżej / w wyniku dla Main).
2. Opcjonalnie: własny kernel top-m w jednym przebiegu zamiast radix (≤ 0.12 ms/krok do odzyskania).
3. Pozostała bezczynność (~4.6 ms/krok W16) leży poza tą zmianą: start grafów i catch-up, `process_token`, przygotowanie batcha.
4. CUDA (3090): ta sama zmiana dotyczy ścieżki `ggml-cuda` (TOP_K jest tam przez CUB/radix). Do zmierzenia w sesji 3090.

Wpadka: `gv_arm.sh` kończył się rc=1, bo w pułapce EXIT pod `set -e` było `kill -9` już martwego serwera. Pomiary to nie dotknęło, poprawione (`|| true`).

## Do bazy wiedzy
- `lekcje/` „Szeroka weryfikacja czeka na CPU z dwóch powodów”:
  - kopia D2H wszystkich logitów (0.045 ms/wiersz);
  - skan pełnego wiersza 1 MB przez sampler na CPU (~50–60 µs na przyjęty wiersz).
  - Razem ok. 1.3 ms bezczynności na krok W16. Top-m na GPU usuwa oba.
- `metody/` „Bezstratny top-m z GPU”:
  - jeśli kandydaci tworzą zbiór top-m bez NaN/inf, a m ≥ k+1, to top-k z testem różności daje ten sam wynik co na pełnym wierszu;
  - wiersze z remisami lub nie-skończonymi wartościami → pełny wiersz na żądanie.
  - Bitowo przy T>0, bo ten sam łańcuch dostaje te same dane.
- `eksperymenty/` 2026-10-19 „24m weryfikacja GPU”:
  - mvs +2.4%, copy +2.2%, czat +0.5%, md5 identyczne;
  - commit `f2217bac7`, skrypty `~/qwen-opt/gpuverify/` (`gv_arm.sh`, `gv_ab.sh`, `gv_md5.sh`, `gv_prof.sh`, `gv_tbo.sh`).
