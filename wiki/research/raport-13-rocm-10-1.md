---
typ: research
tags: [research, rocm, profilowanie]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/13-rocm-10.1.md:1-33
status: aktualne
---
# Raport 13: ROCm 10.1

**ROCm 10.1 nic istotnego nie daje na gfx1100: zostajemy na 10.0, a 10.1 trzymamy obok jako tarball user-local; ważniejsze odkrycia to ATT na gfx1100 i przyczyna PMC = 0.**

Data 2026-10-16. Tarball TheRock gfx110X 10.1.0 (2.67 GB), rozpakowany do `~/opt/rocm-10.1` (11 GB); system ma `10.0.0~pre4`.
- PC sampling i roofline HTML: tylko Instinct (APU) – 0 dla nas.
- LLVM 24: ≈0 wydajności, ISA różni się w 98% kerneli, ryzyko spill w kvq D=256.
- CK FMHA: 0, bo llama.cpp nie używa CK. hipFile/AIS: tylko Instinct.
- WSL2 tech preview: RX 7900 XTX na liście, ale pakiet PM4 (0060) jest tam cicho pomijany → blokada 0060 pod WSL2.
- ATT/thread trace działa na gfx1100 już w 10.0 (`rocprofv3 --att`); PMC = 0 prawdopodobnie przez brak stabilnego stanu zasilania z `amd-smi`.

## Powiązane
- [[research/_hub|research]]
- [[raport-08-platforma]]
- [[raport-12-bit-exact]]
- [[rocm-10-1]]
- [[rocprof]]
