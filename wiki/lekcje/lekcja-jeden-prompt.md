---
typ: lekcja
tags: [lekcje, pomiar, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:274; ~/KERNEL/qwen-opt/NOTES.md:158
status: aktualne
---
# Benchmark z jednym promptem

**„DFlash 120 t/s” zmierzono na 1 prompcie; na zestawie promptów wynik ≈ MTP. Zawsze 6 promptów × seedy.**

Tryb awarii #13. Akceptacja draftów silnie zależy od treści (kod vs proza, EN vs PL), więc pojedynczy prompt może zawyżyć wynik o dziesiątki procent. To samo widać w cudzych liczbach: hipfire 307.9 t/s DFlash na jednym krótkim prompcie.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-szum-t-s-przy-t1]]
- [[lekcja-mikrobench-klamie]]
- [[2026-10-10-sweep-mtp-dflash]]
- [[hipfire]]
