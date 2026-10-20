---
typ: research
tags: [research, fuzje, pm4, awarie]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24l-fuzja-norm.md:7,26-37,62-65
status: aktualne
---
# Raport 24l: fuzja RMS norm do MMVQ – stop po faulcie GPU

**Pierwszy job testowy fuzji norm (ogon producenta ze spin-waitem między blokami) zawiesił taśmę PM4 i skończył się page faultem + mode1 reset GPU (21:10:09); test nie ustawił `GGML_HIP_PM4`, więc szedł przez PM4 `WA=0` bez poprawki PRIV (2026-10-19).**

- Norma F32 bitowo zgodna 216/216, ale następny matvec różny w 13/216 (tylko typy z sumą bloku q8_1 `ds.y`) (`24l:26-27`).
- Zawieszenie: IQ4_XS 5120, 12 tokenów, „tape of 3 dispatches did not complete within 10 s” (`24l:28`).
- Sygnatura faultu SQC(data) @0, STATUS 0x00801431 = raport 17 (`24l:35`).
- Wniosek sprzętowy: [[lekcja-pm4-zawsze-jawnie]]; spin-wait między workgroupami nie może iść przez taśmę bez `WA=2` (`24l:62`).
- Branch `norm-fuse` zostaje jako negatyw; zgodnie z [[2026-10-19-bezpieczenstwo-sprzetu]] bez ponawiania.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[lekcja-pm4-zawsze-jawnie]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[raport-17-gpu-page-fault]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
