---
typ: rocm
tags: [rocm, pm4, command-processor]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:18-57; ~/KERNEL/qwen-opt/NOTES.md:373; ~/KERNEL/product/research/13-rocm-10.1.md:230-240
status: aktualne
---
# PM4: bufory poleceń procesora poleceń GPU

**PM4 to format pakietów, które wykonuje command processor (CP) karty AMD; jeden bufor PM4 z wieloma `DISPATCH_DIRECT` omija koszt ~2 µs na każdy pakiet AQL.**

Pomiar granicy między zależnymi kernelami (gfx1100, ROCm 10.0, 2026-10-14, `~/wt/lfm4-prof/pm4.cpp`; kodowanie wzorowane na hipfire `redline-rocr/src/pm4_gfx10.rs`):

| wariant | µs na granicę (kernel kopiujący) | poprawny łańcuch |
|---|---|---|
| graf HIP | 2.754 | tak |
| PM4 IB, CS_PARTIAL_FLUSH + ACQUIRE_MEM (GCR 0x380), kernargi w VRAM | 0.858 | tak |
| PM4 IB, kernargi w pamięci hosta | 1.874 | tak |
| PM4 IB, tylko CS_PARTIAL_FLUSH | 0.731 | **nie** |
| PM4 bez pakietów granicy | 0.262 | **nie** |

Wnioski: między dispatchami potrzebny jest wait + inwalidacja cache (L0/K$/GL1), inaczej kolejny kernel czyta nieaktualne dane; kernargi muszą leżeć w VRAM (z hosta zależny `s_load` kosztuje +1 µs); bufor IB w pamięci wykonywalnej.

Pakiety PM4 są per generacja GPU (raport 07: RDNA4/RDNA2 = port i test). Pod WSL2 pakiet vendor PM4 jest domyślnie pomijany, a sygnał zakończenia i tak zwraca sukces (raport 13). Nasze wdrożenie: [[pm4-replay]].

## Powiązane
- [[rocm/_hub|ROCm]]
- [[rocr]]
- [[pm4-replay]]
- [[mikrobench-granicy-kernela]]
- hipfire
