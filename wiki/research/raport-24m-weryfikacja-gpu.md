---
typ: research
tags: [research, weryfikacja, sampler, topka]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24m-weryfikacja-gpu.md:3-6,18-38,44-46
status: aktualne
---
# Raport 24m: weryfikacja draftu bez kopii logitów (`LLAMA_GPU_VERIFY`)

**Top-128 kandydatów liczone na GPU zamiast kopii 16 MB logitów: `mvs` 410.4 → 420.1 t/s (+2.4%), copy +2.2%, czat +0.5%, md5 identyczne przy T=0 i T=1 – wdrożone w topce (commit `f2217bac7`, 2026-10-19).**

- Przyczyna przerw: kopia D2H 0.045 ms/wiersz i skan pełnego wiersza 1 MB przez sampler CPU (~50–60 µs na przyjęty wiersz) (`24m:10-16`).
- Bezstratność: jeśli kandydaci tworzą zbiór top-m bez NaN/inf i m ≥ k+1, top-k jest identyczne z pełnym wierszem – przy każdej temperaturze; sprawdzone na 20 000 losowych wierszy (`24m:21-25`).
- Ślad: przerwy > 40 µs 2.84 → 1.54 ms/krok przy W16 (`24m:44-45`).
- test-backend-ops TOP_K 533/533, GET_ROWS 222/222 (`24m:36`). Na 3090 zysk +6…+9%: [[raport-27-3090-final]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24k-koszt-weryfikacji]]
- [[raport-27-3090-final]]
- [[koszt-szerokosci-weryfikacji]]
