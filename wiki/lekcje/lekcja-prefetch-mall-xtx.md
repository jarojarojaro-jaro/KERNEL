---
typ: lekcja
tags: [lekcje, pm4, cache, wyniki-negatywne]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16a-pm4-pdl.md:18-19,114-134; ~/qwen-opt/pm4pdl/x2/ab4.log; ~/KERNEL/product/research/18-nastepna-fala.md:200-211
status: aktualne
---
# Wynik negatywny: prefetch wag do L2/MALL dispatchem bez granicy

**X3 (2026-10-18): dispatch „touch” (1 dword na linię 128 B pierwszych N KiB wag następnego matvec) wstawiony bez granicy obok małych kerneli (54 na taśmę LFM) dał +0.2…+0.6% przy 1–4 MiB – w szumie (produkcja vs ta sama taśma 0.5%, rozrzut rund do 8 t/s) – a 16 MiB spowolnił o 2.4%.**

Przyczyna: touch konkuruje o pasmo z bieżącym kernelem; w X1 analogiczny touch przed czekaniem też przegrywał z prefetchem do VGPR. `hipLaunchAttributeExtDynDataPrefetch` nie działa na gfx1100 (ROCr: 0 regionów, 15a §7).

Reguła: na XTX prefetch do cache osobnym dispatchem nie jest dźwignią; jeśli prefetch, to do rejestrów wewnątrz kernela konsumenta.

Arytmetyka (raport 18): w kroku batch 1 żadna waga nie jest czytana dwa razy, a odległość ponownego użycia między krokami to ~16.8 GB (Qwen) / ~1.8 GB (LFM) ≫ 96 MB MALL; jedyny kandydat z reużyciem – stan GDN Qwena – ma 151 MB f32.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-handoff-rdna3]]
- [[wyniki-negatywne]]
- [[2026-10-18-pm4-ub-lfm]]
