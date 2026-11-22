---
typ: test
tags: [testy, xtx, budzet-kroku]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/36-xtx-qwen-roadmap.md:8-20
status: aktualne
model: qwen3-8-27b
karta: rx-7900-xtx
wynik: qwen3-8-27b | rx-7900-xtx | 27.38 ms | krok prozy T=1; 2.63 tok/krok, stara metryka | 2026-10-20
---
# Raport 36: budżet kroku prozy T=1 na XTX

**Krok prozy 27.38 ms przy 2.63 tok/krok (96.1 t/s, stara metryka z myśleniem); 89.5% to taśma weryfikacji, z tego MMVQ n=5 21.79 ms (2026-10-20).**

- Podłoga fizyczna 18.17 ms (144.7 t/s), inżynierska ~21.4 ms (~123 t/s); wykorzystanie 66% sufitu pasma.
- Wniosek: najpierw stała metryka prozy → raport 37.

## Powiązane
- [[raporty-2026-10-20-21]]
- [[sufit-pasma-i-mapa-czasu]]
- [[metryka-prozy-e0]]
