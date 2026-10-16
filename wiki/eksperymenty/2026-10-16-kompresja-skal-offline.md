---
typ: eksperyment
tags: [eksperymenty, kwanty, nvfp4, wynik-negatywny]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:56-58,303-319,434-436
status: aktualne
---
# 2026-10-16: bezstratna kompresja skal kwantów (offline, odrzucona)

**Pomiar entropii skal na prawdziwych plikach: dla naszych K-quantów (UD-Q4_K_XL) bezstratna kompresja skal oszczędziłaby najwyżej 2.19% bajtów – za mało na nowy typ ggml; dla NVFP4 w GGUF −5.4% (kod CSF-like) do −8% (entropia), odłożone.**

- `scale_entropy.py` (UD-Q4_K_XL, próbka 200k bloków na tensor): sufit H1 Q4_K −2.88%, Q5_K −2.38%, Q6_K −1.33%, IQ4_XS −1.60%, razem **−2.19%** (0.234 GB). Skale 6-bitowe mają H0 ≈ 5.1–5.2 bit/skala, czyli są prawie nieściśliwe.
- `nvfp4_scale_entropy_remote.py` (esatapedico NVFP4 VERY-LOW): duże tensory H1 1.3–3.6 bit/skala, kod CSF-like 4.01–4.17 bit/skala → 4.5 → ~4.26 bpw (−5.4%); sufit ~4.14 bpw (−8%); małe `ssm_beta` 37% wyjątków.
Kill: nie budujemy kompresji skal K-quantów (próg sensowności ≥ 5%). CSF dla NVFP4 odłożony, bo NVFP4 w dekodowaniu nie jest naszą ścieżką.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-15e-kwantyzacja-nowa]]
- [[2026-10-16-nvfp4-skala-globalna-sim]]
- [[kwanty-gguf]]
- [[wyniki-negatywne]]
