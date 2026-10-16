---
typ: kernel
tags: [kernele, pm4, rocr]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:6-14,18-57,81-99; ~/KERNEL/qwen-opt/NOTES.md:372-376; ~/KERNEL/product/research/08-analiza-platformy-latek.md:14-21; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:135-136,473
status: aktualne
---
# Replay grafu dekodowania jako bufor PM4 (0060, 0061, 0063)

**Przechwycony graf HIP jest przebudowany w jeden bufor poleceń PM4 wysyłany jednym pakietem AQL na własnej kolejce ROCr; granica między kernelami spada z ~2.75 µs do ~0.46–0.86 µs.**

Mechanizm (`ggml/src/ggml-cuda/hip-pm4.{cu,cuh}`, runda 4, 2026-10-14): węzły grafu stają się taśmą: deskryptory kerneli z loadera ROCr, kernargi z metadanych code object (własny czytnik msgpack), ukryte argumenty jak w ROCclr (reszta „fail closed”); kernargi w VRAM, IB w pamięci wykonywalnej. Kolejność ze strumieniem HIP po stronie hosta. Grafy z innymi węzłami idą starą drogą (`cudaGraphLaunch`). Te same kernele i argumenty, więc wynik bitowo identyczny.

Wynik (przeplatane):
- LFM llama-bench tg128: 3.887 → 3.424 ms/token (257.3 → 292.1 t/s); spec_sweep 259.3 → 293.6 t/s;
- Qwen MTP: 29.16 → 27.80 ms/krok, 103.7 → 108.8 t/s; Uncensored MTP 109.9 → 115.3;
- taśma LFM: 304 dispatche na token.

Bezpieczeństwo: 20 przebiegów testu, soak `pm4_soak.py` (~4 min na model) bez zawieszeń; pierwsza próba dała odwracalny page fault (IB musi być w pamięci wykonywalnej).

Wyłączniki: `GGML_HIP_PM4=0`; diagnostyka `GGML_HIP_PM4_DEBUG=1/2/3` (0061), bo rocprofv3 nie widzi dispatchy PM4. Ograniczenia: zależy od wnętrzności ROCr; **nie działa na Windows** (HIP na PAL), a bezwarunkowe `find_package(hsa-runtime64)` może łamać tam build.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mikrobench-granicy-kernela]]
- [[pm4]]
- [[pm4-niewidoczne-w-rocprof]]
- [[lfm-runda-4-pm4]]
