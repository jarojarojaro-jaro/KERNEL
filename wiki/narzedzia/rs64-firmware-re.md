---
typ: narzedzie
tags: [narzedzia, firmware, reverse-engineering]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/23d-re-runtime-amd.md:3,71-78
status: aktualne
---
# Deasemblacja firmware CP/MES gfx11 (RS64 = RV64)

**Jak czytać firmware MEC/MES gfx11: parsowanie nagłówka v2 (`fwparse.py`), deasemblacja capstone RV64C, propagacja znanych bitów do nazw rejestrów (`rs64kb.py`); apertura SH – indeks rejestru × 4 od `0x1_0002_0000_0000` (raport 23d, 2026-10-19).**

Narzędzia i zrzuty leżą lokalnie w `~/qwen-opt/re/runtime/` (zrzuty firmware nigdy w publicznym repo – licencja linux-firmware zakazuje RE; wolno tylko dla interoperacyjności, cytujemy numery linii i zachowanie, [[re-vendorow-zasady]]). Zastosowanie: [[mec-fw-dispatch-aql-gfx11]].

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[umr-offline-pm4]]
- [[hip-fatbin-extract]]
