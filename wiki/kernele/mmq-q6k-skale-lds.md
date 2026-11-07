---
typ: kernel
tags: [kernele, mmq, prefill, wmma]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66a-strata-maya.md:300-343,388; https://github.com/mw00/project-maya/pull/864
status: do-sprawdzenia
---
# MMQ Q6_K na gfx1100 czyta skale bajt po bajcie

**W produkcyjnym `libggml-hip.so` (topka, 2026-11-05) kernel MMQ Q6_K ma 16× `ds_load_i8` i zero `ds_load_b128`, podczas gdy Q4_K/Q5_K/IQ4 ładują operandy 128-bitowo; poprawka ładowania bez zmiany kolejności iloczynów daje szacunkowo pp4096 +1.5…3% (UD-Q4_K_XL) i +2.5…5% (Q4_K_M), bitowo (raport 66a, `[SZACUNEK]`).**

| typ, J | VGPR | `ds_load_b128` | `ds_load_i8` | WMMA iu8 |
|---|---|---|---|---|
| Q4_K, 128 | 239 | 36 | 0 | 32 |
| IQ4_XS, 128 | 242 | 36 | 0 | 32 |
| **Q6_K, 128** | 222 | **0** | **16** | 16 |

- Przyczyna: `mmq-vec-dot.cuh:1154-1182` czyta `sc[k01/4]` jako int8 w najgłębszej pętli, bez `#pragma unroll`. Ścieżka Turing ładuje skale raz jako `int`.
- Udział Q6_K: 13.4% elementów macierzy w UD-Q4_K_XL, 21.2% w Q4_K_M.
- Inspiracja: Maya #864 (XTX, −39% kerneli WMMA przez lepsze podawanie operandów, 108/108 wyjść bitowo).
- To niewykonany cel „T1: epilog Q6_K” z [[2026-10-19-plan-retro-rsr-0070]].
- Bramka: rocprofv3 `llama-bench -p 4096`, kill jeśli Q6_K < 5% prefillu; ABBA kill < +1%; md5.

**Test 2026-11-07 (final mode): 0,0% — KILL** (pp4096 1000,7 → 1000,6, prefill 12k 933,1 → 933,0, md5 identyczne); szczegóły [[2026-11-07-q6k-mmq-skale]]. Łatka usunięta.

## Powiązane
- [[kernele/_hub|kernele]]
- [[mmq-epilog]]
- [[prefill-mmq-fa]]
- [[project-maya]]
- [[rdna3-gfx1100]]
- [[raport-66-synteza]]
