---
typ: metoda
tags: [metody, loo, latki]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/tools/README.md:8-33; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:14-35; ~/KERNEL/product/PLAN.md:166
status: aktualne
---
# Leave-one-out łatek (LOO)

**Wyłączamy po jednej łatce i mierzymy, czy bez niej jest wolniej; łatka bez mierzalnego zysku jest kandydatem do usunięcia.**

Klasyfikacja łatek pod LOO (stan na 65 łatek, `amd-opt` @ c36fd2c87; `loo/loo-plan.md`):

| klasa | liczba |
|---|---|
| wyłącznik env w runtime (`GGML_HIP_*`, `LLAMA_*`) | 27 |
| wyłącznik CLI (0004 `--spec-draft-vocab`, 0032 `--spec-*-type`) | 2 |
| tylko build (revert + przebudowa) | 22: 8 revertuje się czysto (0022/35/36/37/40/41/42/45), 14 ma konflikty |
| nie dotyczy prędkości (Vulkan 5, poprawki 3, opt-in 2, narzędzia/testy/higiena 4) | 14 |

Konflikty revertu: 0001/02/16/21 na `mmvq.cu`. 0033 wyłącza `LLAMA_GDN_REPLAY=0`, które gasi też 0034–0036 i 0038.

Przebieg: ABBA pod lockami GPU, bloki ≤ 5 min z 45 s przerwy, port 18440, wyniki dopisywane do jsonl (wznawialne); raport z sparowanym 95% CI i flagami NEUTRAL / REMOVAL FASTER. Statystyki sprawdzone na danych syntetycznych.

Stan: na GPU **nieuruchomione** (szacunek ~3.8 h + buildy). PLAN §4.1 robi z tego regułę: łatka, która przez N wydań nie weszła do upstreamu i nigdzie nie daje ≥3%, jest usuwana.

## Powiązane
- [[metody/_hub|Metody]]
- loo-py: narzędzie
- [[wylacznik-w-kazdej-latce]]
- [[pomiar-abba]]
- [[wylaczniki-env]]
