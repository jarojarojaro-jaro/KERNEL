---
typ: lekcja
tags: [lekcje, spekulacja, konkurencja]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:12,70-75; ~/qwen-opt/magnitude-xtx/x/xbench.jsonl
status: aktualne
---
# tok/krok nie wygra z drogim krokiem

**Magnitude na Vulkanie (XTX, 2026-10-18) ma na code-edit 7.05 tok/krok, ale krok 83 ms → 87.7 t/s; my 4.92 tok/krok przy 29 ms → 170 t/s. Ich krok 1-wierszowy (27.7 ms) kosztuje tyle co nasz 5-wierszowy (28.1 ms), a 8 wierszy to ×3.0 kroku 1-wierszowego.**

Krzywa ich kroku: 1.00 tok/krok → 27.7 ms, 1.69 → 38.9, 2.77 → 51.7, 3.87 → 58.0, 7.05–7.88 → 83 ms. Nasz krok: 28.0–28.4 ms dla 1.9–3.6 tok/krok.

Reguła: wynik spekulacji to tok/krok ÷ ms/krok, a koszt szerokości weryfikacji zależy od backendu (ich CUDA: blok 8 = 50 ms). Przed przeniesieniem „szerszego bloku” na nową platformę zmierzyć krzywę V(w) (E-X0/E-C1).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-sufit-bloku]]
- [[kontroler-szerokosci-draftu]]
- [[2026-10-18-magnitude-vulkan-xtx]]
