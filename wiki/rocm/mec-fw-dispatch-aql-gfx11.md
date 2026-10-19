---
typ: rocm
tags: [rocm, firmware, pm4, rdna3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23d-re-runtime-amd.md:5-34,50-58; deasemblacja `gc_11_0_0_mec.bin` (lokalnie, poza repo; wiersze 41164-41212, 52843-52849, 58370-58684, 6163-6233)
status: aktualne
---
# Firmware MEC gfx11: co robi z pakietem AQL, a czego nie robi z `DISPATCH_DIRECT`

**Przy pakiecie AQL firmware MEC ustawia RSRC1 = deskryptor & `0xe4aff3ff` z PRIV wziętym z flagi kolejki (obejście CWSR), RSRC2 = deskryptor & `0x1fbf` | TRAP_PRESENT | LDS z pakietu (granula 512 B, limit 64 KiB), `PGM_HI |= 0x100` i inicjator `0x1065 | W32<<15`; handler `DISPATCH_DIRECT` zapisuje tylko wymiary, START i inicjator, a RSRC1 bierze bez zmian – fale naszej taśmy dostają PRIV wyłącznie od nas (raport 23d, 2026-10-19).**

- Potwierdza H1′ z raportu 17 i poprawkę `GGML_HIP_PM4_WA≥1` ([[gfx11-pm4-dispatch-priv]]). Wewnętrzny dispatch firmware ustawia PRIV=1, `RESTART=0`, inicjator `0x8045` – jak nasze `WA=2` plus ORDER_MODE.
- Nowe różnice wobec AQL: ORDER_MODE (bit 6) i `PGM_HI` bit 8 – kandydaci na `WA=3`, tylko jeśli S4 da fault.
- Wznowienie po wywłaszczeniu ponownie zapisuje zapamiętany inicjator dispatchu – przerwana taśma wraca z naszym inicjatorem i bez obejścia CWSR przy `WA<1` `[INFERENCE]`.
- Podłoga 2.08 µs na pakiet AQL to praca firmware (4 odczyty deskryptora kernela, składanie user SGPR, EOP/sygnał); taśma podaje gotowe wartości, stąd 0.46–0.86 µs.
- Deasemblacja firmware wykonana dla interoperacyjności (dyr. 2009/24/WE art. 6); zrzuty tylko lokalnie w `~/qwen-opt/re/runtime/fw/`, nie w repo ([[re-vendorow-zasady]]).

## Powiązane
- [[rocm/_hub|ROCm]]
- [[kfd-ewikcja-kolejek-gfx11]]
- [[pm4-replay]]
- [[rs64-firmware-re]]
