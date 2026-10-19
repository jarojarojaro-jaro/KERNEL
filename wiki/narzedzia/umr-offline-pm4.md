---
typ: narzedzie
tags: [narzedzia, pm4, rocm]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21l-reverse-engineering-gpu.md:24,43,79-80; ~/KERNEL/product/research/21l-skrypty/umr-tape-wa0.txt; ~/KERNEL/product/research/21l-skrypty/umr-tape-wa2.txt; ~/KERNEL/product/research/21l-skrypty/pm4_synth_tape.py
status: aktualne
---
# umr offline: dekodowanie taśmy PM4 bez roota

**umr zbudowany bez roota (`apt download` + `dpkg -x`) dekoduje offline pakiety PM4, AQL i pola rejestrów gfx1100: `umr -f gfx11_vm_test -df plik.bin`; nie dekoduje słowa inicjatora `DISPATCH_DIRECT` (Mesa `ac_parse_ib.c` też nie) (raport 21l, 2026-10-19).**

Syntetyczna taśma z deskryptora: `pm4_synth_tape.py HSACO SYM out.bin --wa N`. Potwierdziło: deskryptor MMVQ `rsrc1=0xe0af0011` → PRIV=0, TRAP_PRESENT=0; taśma `WA=2` ustawia PRIV=1, RESTART_X/Y/Z=0, polityka IB 3 → 0 ([[gfx11-pm4-dispatch-priv]]). Plan A2: `GGML_HIP_PM4_DUMP` + umr w CI jako bramka. Binarka `~/qwen-opt/research-src/umr/build/src/app/umr` z `LD_LIBRARY_PATH` na `libpciaccess` w `/tmp` (ulotne – pobrać ponownie po restarcie).

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[pm4-replay]]
- [[raport-21l-re-gpu]]
