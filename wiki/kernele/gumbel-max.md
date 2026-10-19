---
typ: kernel
tags: [kernele, sampler, spekulacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16k-sprzezone-probkowanie.md:50-62,85-88,113-121,129-140
status: aktualne
---
# Op `GGML_OP_GUMBEL_MAX` (draft MTP ze sprzężonym szumem)

**Nowy op ggml (CPU `ggml-cpu/ops.cpp`, HIP/CUDA `ggml-cuda/gumbel-max.cu`) zastępuje `ggml_argmax` w grafie łańcucha MTP: top-k → top-p → min-p → /T + szum Philox4x32-10 kluczowany (seed, pozycja, token) na wierszu 65536 tokenów słownika draftu; wybiera bitowo to samo co CPU i łańcuch samplera celu.**

- Parametry (seed, klucz, T, k, p, min_p) są wejściami grafu, więc graf i nagranie PM4 są reużywane.
- Wersja 1 (`760ee6990`): +0.41 ms/krok (28.16 → 28.57) na 4 przejścia łańcucha MTP.
- Wersja 2 (`3f25fc204`): kandydaci z najciaśniejszego progu mieszczącego top_k, klucze sortowania w LDS, jedno przejście zliczanie+zbieranie, 1024 wątki: +0.11 ms (27.74 → 27.85).
- `test-backend-ops -o GUMBEL_MAX -b ROCm0` 152/152 dla obu wersji; CPU vs łańcuch samplera 0/2000 różnic.
- Warunek przyszłego certyfikowanego readoutu lm_head (16i #8).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[sampler-fast-path]]
- [[mtp-draft-graf]]
- [[2026-10-18-sprzezone-probkowanie-mtp]]
