---
typ: test
tags: [testy, prefill, gdn]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/qwen-opt/STATUS-NEXT.md:3,31-38; ~/KERNEL/qwen-opt/NOTES.md:394-398; ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:159-168; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:176-184; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:5; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:1-25; ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:1-25; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:1-25
status: aktualne
---
# 2026-10-15: runda 6 — epilog MMQ, GDN fast, narzędzia

**Trzy gałęzie przygotowane offline i zmierzone w oknie GPU: epilog MMQ scalony (+2.2% pp4096 Qwena), GDN fast bitowy, ale w szumie (nie scalony), narzędzia LOO / kanarki KLD / Kernel Tuner gotowe, ale jeszcze nieuruchomione na GPU.**

| gałąź | co | wynik | werdykt |
|---|---|---|---|
| `opt-mmq6` (ae1ef6a97 → 0070) | epilog MMQ Q4_K/Q5_K w parach VOPD | Qwen pp4096 1099.5 → 1123.2 (+2.2%, każda z 3 rund), pp512 +1.9%, LFM pp4096 +0.3%; logity bit w bit | scalone jako f61994f58 |
| `opt-gdn6` (b4e819237, 0d89ce56c) | GDN fast z DPP i stanem przez LDS | test-backend-ops 67/67, md5 = baza; tg128 +0.15%, pp512 +0.7% | nie scalone |
| `tools6` (4db68c6ab) | `loo.py`, `kld_canary.sh`, Kernel Tuner | dry-run / fake / ISA OK | GPU: zostało do zrobienia |

Szacunek offline epilogu był ~5%; zmierzone 2.2% (część VALU chowa się za WMMA). Po rundzie 6 stan instalacji to 70 łatek ([[stan-2026-10-15]]). Kolejka GPU po rundzie: `loo.py run`, `kld_canary.sh`, Kernel Tuner.

## Ze scalonej notatki: Runda 6: raporty GDN, MMQ i narzędzi

Trzy raporty rundy 6 (2026-10-15), wszystkie bez GPU: szybki kernel GDN bitowy z konstrukcji, epilog MMQ w VOPD oraz narzędzia LOO / kanarki KLD / Kernel Tuner.

- `gdn-bitwise.md` (gałąź `opt-gdn6`): `b4e819237` i `0d89ce56c`, kernel bazowy nietknięty (379 wstawień, 0 usunięć), dowód przez emulację ISA (katalog `gdn-isa-tools`).
- `mmq-epilogue.md` (gałąź `opt-mmq6`): `ae1ef6a97`, na lane 64 `v_fma_mix_f32` + 64 `v_cvt_f32_i32` + 64 fmac + 64 `v_fma_mix_f32`, które nie dual-issue; zmiana na f32 parowalne w VOPD, bitowo te same sumy; potem łatka 0070.
- `test-tooling.md` (gałąź `tools6`): `loo.py` (27 przełączników env, 2 CLI, 22 tylko build, 14 nie-wydajnościowych), kanarki KLD, rusztowanie `kt/`.
Wszystkie commity oznaczone NIEZMIERZONE w chwili pisania.

## Powiązane
- [[mmq-epilog]]
- [[gdn-fast]]
- [[kernel-tuner]]
- [[dowod-offline]]
