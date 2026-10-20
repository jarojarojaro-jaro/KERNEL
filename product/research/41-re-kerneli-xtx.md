# 41. RE kerneli XTX: GDN i małe opy vs hipfire (XtxRE)

Wszystkie zadania GPU szły przez `~/qwen-opt/queue/run-jobs.sh` (`x1`, `x2`, `g1`, `g2`). Łącznie ok. 20 min GPU, w tym bramka md5 i ABBA ok. 17 min. Błędów amdgpu nie było.

## Wyniki

| Pozycja | Wynik | Decyzja |
|---|---|---|
| X1 ATT (MMVQ q8 w5) | 70–82% latencji to `wait vmcnt`. Kernel jest związany z pamięcią, nie z ALU (`x41-att.summary.txt`) | brak zmiany |
| RE GDN vs hipfire (DS, `ds/out/re-gdn-verify.md`) | Na wiersz jesteśmy tańsi (278 vs 417 instr.). Różnica 1.33× wynika z 5 wierszy replay w `set_input_lag`. Ich `dflash_gdn_pre` nic nie przenosi | kandydat na później: drugi bank stanu i `n_pend=0` przy pełnej akceptacji. Pułap +1.1% t/s, to praca po stronie hosta |
| RE norm/małe opy (DS, `ds/out/re-norm-fuse.md`) | `_wavegrid`/`_vecsum` hipfire'a nie odpalają się przy K=5120. Nasz norm jest ograniczony przez issue/obsadzenie (5 CU). Anomalia: grid 4 jest wolniejszy od grid 5 (zegar w burście MTP, ok. 0.36 ms/krok) | do sprawdzenia przez SPM |
| **G: `GGML_HIP_GDN_PREFETCH=1`** (loady tokenu t+1 w trakcie tokenu t, bitowo zgodne) | tbo GDN i GDN_LAG OK. kt 8.60 → 8.08 µs/launch (−6%). md5 Qwen c4708318 / MTP 6f14e814 OK. **ABBA E0 (seedy 1,2): A 78.95/79.01, B 78.87/78.89 t/s, czyli −0.13%** (w szumie), mvs 432.4 → 433.4 | **nie adoptuję**: zysk na prozie niemierzalny |
| `GGML_HIP_GDN_PREFETCH=2` (float4 przez LDS) | 13.2 µs (+53%) | odrzucone |

Gałąź `~/wt/xtx-re` @ 384a79577: przełącznik jest domyślnie wyłączony i nie trafia do topki.

## Wniosek

GDN nie jest wąskim gardłem w kernelu. Jedyny realny zysk w GDN to usunięcie wierszy replay (host, drugi bank stanu). Następny krok: `rocprofv3 --spm` dla `rms_norm_mul_f32_unrolled` przy grid 4 vs 5.
