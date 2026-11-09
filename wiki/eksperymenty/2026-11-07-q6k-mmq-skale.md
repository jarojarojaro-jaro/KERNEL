---
typ: eksperyment
tags: [eksperymenty, rx-7900-xtx, prefill, mmq, q6k, wynik-negatywny]
aktualizacja: 2026-11-07
zrodlo: ~/qwen-opt/q6kwide/run-1107-2305/summary.txt, pp4096.txt, prefill.txt; ~/qwen-opt/q6kwide/NOTE.txt; branch q6k-wide 4dc11c952
status: aktualne
---
# Q6_K MMQ na gfx11: skale jednym `int` zamiast 16 odczytów bajtowych — 0,0% (KILL, 2026-11-07)

**Łatka `GGML_HIP_Q6K_WIDE` (skale wiersza czytane jednym `int` na pół-k01, 16× `ds_load_i8` → 0, 222 VGPR, 0 spilli) nie zmieniła prefillu: pp4096 1000,7 → 1000,6 t/s (−0,01%), prompt 12k 933,1 → 933,0 t/s; md5 identyczne (0221afd9) — odczyty skal nie były wąskim gardłem kernela, więc łatka odrzucona i usunięta.**

Warunki: final mode (eco 2200), Qwen3.8-27B-Uncensored Q4_K_M, topka-q63 base vs ta sama baza + łatka, ABBA 4 × pp4096 (llama-bench) i 6 × prompt 11 962 tok. na serwerze; `test-backend-ops -o MUL_MAT` 2496/2496 OK.

| Pomiar | base | wide | Δ |
|---|---|---|---|
| pp4096 (mediana ABBA) | 1000,7 t/s | 1000,6 t/s | −0,01% |
| prefill 12k (serwer) | 933,1 t/s | 933,0 t/s | −0,01% |
| md5 greedy | 0221afd9 | 0221afd9 | = |

Wniosek: w MMQ Q6_K na gfx11 dominuje WMMA i ładowanie kafli, nie skale (hipoteza z 66a A1 obalona). Pełne odczyty 128-bit są niemożliwe (8 B skal na wiersz, wiersze co `sram_stride`), rozwinięcie pętli `k01` spilluje (256 VGPR). Uwaga z przebiegu: przy wyjściu `test-backend-ops` PM4 zgłosił „last tape did not signal completion within 12000 ms” (tylko narzędzie testowe, serwer odtworzony poprawnie: `/health` OK, n_ctx 262 144).

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[mmq-q6k-skale-lds]]
- [[raport-66-synteza]]
