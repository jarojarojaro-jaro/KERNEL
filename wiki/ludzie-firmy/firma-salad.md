---
typ: firma
tags: [ludzie-firmy, chmura]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:21,23,55
status: aktualne
---
# Salad (SaladCloud)

**Rozproszona chmura na komputerach graczy; jedyne godzinowe konsumenckie Radeony, ale tylko w kontenerze WSL2 bez `/dev/kfd` i bez SSH.**

RX 7800 XT, 7900 XT, 7900 XTX, 9060 XT, 9070 XT za 0.04–0.17 $/h; RTX 3090 od 0.09 $/h na najniższym priorytecie. Bez ROCr/KFD nie da się testować naszych łatek ROCm (np. PM4). Rola w planie: walidacja „Windows/WSL2 u gracza”.

## Powiązane
- [[ludzie-firmy/_hub|ludzie-firmy]]
- [[firma-vast-ai]]
- [[hostkey]]
- [[salad]]
- [[wsl2-rocm]]
