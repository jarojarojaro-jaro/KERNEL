---
typ: eksperyment
tags: [eksperymenty, prefill, gdn]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/STATUS-NEXT.md:3,31-38; ~/KERNEL/qwen-opt/NOTES.md:394-398; ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:159-168; ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:176-184; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:5
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

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[mmq-epilog]]
- [[gdn-fast]]
- [[kernel-tuner]]
- [[dowod-offline]]
