---
typ: lekcja
tags: [lekcje, pm4, rdna3]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/17-gpu-page-fault.md:218-247,276-292
status: aktualne
---
# Własny PM4 musi robić to, co firmware robi dla AQL

**Nasza taśma PM4 omijała wszystko, co CP robi przy pakiecie AQL – pola „CP is responsible” (PRIV, TRAP_PRESENT, user SGPR), obejścia sprzętowe (PRIV=1 na GFX11) i stan przy wywłaszczeniu – i najpewniej przez to 8 razy zresetowała GPU (raport 17 §9, 2026-10-19).**

Reguła: przed wdrożeniem własnej ścieżki dispatchu porównać pakiety pole po polu z referencjami (kfdtest, tinygrad, radv/PAL) i przetestować wywłaszczenie wstrzykniętą ewikcją ([[lekcja-test-wywlaszczenia]]), nie tylko soak.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[gfx11-pm4-dispatch-priv]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[pm4-replay]]
