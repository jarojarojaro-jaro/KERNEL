---
typ: research
tags: [research, moe, offload, konkurencja]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/28-moe-offload-silniki.md:11-15,27-36,42,47,66-70
status: aktualne
---
# Raport 28: silniki MoE-offload TideLM i Xolotl – stratne z założenia

**Prędkości TideLM i Xolotl biorą się z nieliczenia ekspertów wybranych przez router (podstawianie, bias routingu do VRAM) i kwantów 2–3 bit; przy dokładnym routingu Xolotl sam podaje ~3.5 tok/s – dla naszych modeli (w całości w VRAM) offload nic nie daje (2026-10-20).**

- Górna granica bezstratnego offloadu: tok/s ≤ pasmo (RAM ~70 / PCIe ~25 / NVMe ~6 GB/s) ÷ bajty chybionych ekspertów na token (`28:69`).
- Jedyna przenośna technika: dynamiczna głębokość draftu (TideLM: kod +21% przy głębokości 5, proza −10%) (`28:42,68`) – u nas sprawdzona w [[raport-24q-adaptacyjna-spekulacja]] (md5 się zmienia).
- Lekcja: bit-exactness przy zmianie chunku GEMM nie istnieje; bezstratność mierzyć KL/top-1 (`28:47,70`).
- Nie portujemy route-bias, podstawiania, LOOP_BREAK ani KV FP4.

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[raport-24q-adaptacyjna-spekulacja]]
- [[raport-21n-strata-gyro]]
- [[model-kosztu-weryfikacji-moe]]
