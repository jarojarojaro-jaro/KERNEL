---
typ: research
tags: [research, konkurencja, vulkan]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:1-110
status: aktualne
---
# Raport 16j: Magnitude przez Vulkan na 7900 XTX (E-X5)

**Agent MagnitudeVulkanXtx uruchomił Magnitude na naszej XTX przez Vulkan i zmierzył go tym samym harnessem co 16d: na AMD Magnitude jest konkurentem w łatwości instalacji (jedna binarka, bez ROCm), nie w wydajności (×1.42–×2.24 dla nas).**

- Przewaga Magnitude to wyłącznie tok/krok (blok 8 DFlash2 + kontroler); na Vulkanie ich krok 8 wierszy kosztuje ×3.0 kroku 1-wierszowego, a nasz krok prawie nie zależy od szerokości ([[lekcja-koszt-szerokosci-backendu]]).
- Kontroler sam wyłącza draft na pl-proza (1.00 tok/krok, akceptacja 0.04–0.09) – nie tracą względem plain, ale ich plain jest 2× za wolny.
- Do przejęcia: nic z kerneli Vulkan. Szerszy blok (ogon lookupu) ma na XTX lepsze warunki niż u nich: przy 7.88 tok/krok i ~35 ms code-edit dałby ~225 t/s `[INFERENCE]`.
- Ryzyko: strojenie kerneli pod RDNA i skrócenie kroku 8-wierszowego z 83 do < 48 ms zrównałoby ich z nami na code-edit.
- Komunikat produktu poparty pomiarem: „na kartach AMD ~2× szybsi od Magnitude na tym samym modelu i GPU”.

Wyniki: [[2026-10-18-magnitude-vulkan-xtx]].

## Powiązane
- [[research/_hub|research]]
- [[raport-16i-magnitude]]
- [[raport-16d-magnitude-vs-nasz]]
- [[2026-10-16-badamy-magnitude]]
