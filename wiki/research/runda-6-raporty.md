---
typ: research
tags: [research, runda-6, gdn, mmq]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:1-25; ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:1-25; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:1-25
status: aktualne
---
# Runda 6: raporty GDN, MMQ i narzędzi

**Trzy raporty rundy 6 (2026-10-15), wszystkie bez GPU: szybki kernel GDN bitowy z konstrukcji, epilog MMQ w VOPD oraz narzędzia LOO / kanarki KLD / Kernel Tuner.**

- `gdn-bitwise.md` (gałąź `opt-gdn6`): `b4e819237` i `0d89ce56c`, kernel bazowy nietknięty (379 wstawień, 0 usunięć), dowód przez emulację ISA (katalog `gdn-isa-tools`).
- `mmq-epilogue.md` (gałąź `opt-mmq6`): `ae1ef6a97`, na lane 64 `v_fma_mix_f32` + 64 `v_cvt_f32_i32` + 64 fmac + 64 `v_fma_mix_f32`, które nie dual-issue; zmiana na f32 parowalne w VOPD, bitowo te same sumy; potem łatka 0070.
- `test-tooling.md` (gałąź `tools6`): `loo.py` (27 przełączników env, 2 CLI, 22 tylko build, 14 nie-wydajnościowych), kanarki KLD, rusztowanie `kt/`.
Wszystkie commity oznaczone NIEZMIERZONE w chwili pisania.

## Powiązane
- [[research/_hub|research]]
- [[raport-07-metody]]
- [[opt-gdn6]]
- [[opt-mmq6]]
- [[tools6]]
- [[runda-6]]
