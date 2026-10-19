---
typ: lekcja
tags: [lekcje, pm4, diagnostyka]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:16-17,70-76
status: aktualne
---
# „Tape did not complete within 10 s” to skutek, nie przyczyna

**W 7 awariach E-X4 fault i reset GPU przyszły 0.57–3.20 s po starcie requestu, a komunikat `tape of 823 dispatches did not complete within 10 s` dopiero ~10 s później – po resecie sygnał taśmy nigdy nie spada (raport 17, 2026-10-19).**

Reguła: przyczyny szukać w `journalctl -k` z dokładnym czasem (porównanie z mtime `.server.log` i `launch_slot_`), nie w ostatniej linii logu serwera.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[dekodowanie-page-fault-amdgpu]]
- [[lekcja-dowod-poza-commitem]]
