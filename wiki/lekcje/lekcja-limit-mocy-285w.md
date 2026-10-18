---
typ: lekcja
tags: [lekcje, moc, pomiar]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16g-lfm-moe-pasmo.md:76-81,91-92; ~/KERNEL/qwen-opt/research/lfm-decode-round4.md:154-159
status: do-sprawdzenia
---
# Zysk kernela ≠ zysk tokena przy limicie mocy 285 W

**Szybszy gate+up LFM (−0.5 µs/wywołanie w trybie szybkim, −2.2 µs w wolnym) spowolnił inne kernele (out_proj 5.48 → 5.76–5.84 µs × 39 wywołań), więc LFM zyskał tylko +0.33%; ten sam objaw dały 3 wiersze w rundzie 4 (down 12.92 → 13.20, out_proj 5.44 → 5.84, FA 8.88 → 9.48 µs) (2026-10-18).**

Hipoteza (niepotwierdzona, `[INFERENCE]`): wydajniejszy kernel pobiera więcej mocy i przy limicie 285 W reszta taśmy zwalnia zegar.

Reguła: zysk kernela oceniać tylko end-to-end (ABBA t/s, taśma PM4 µs/token), nigdy z czasu samego kernela; przy przesunięciach rzędu 1% patrzeć na sąsiednie kernele.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-mikrobench-klamie]]
- [[amdgpu-moc-i-termika]]
- [[2026-10-09-limit-mocy-odlozony]]
- [[2026-10-18-lfm-moe-pasmo]]
