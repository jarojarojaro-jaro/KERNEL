---
typ: test
tags: [testy, nvidia, rtx-5060-ti]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/31-5060ti.md:1-16
status: aktualne
model: qwen3-8-27b
karta: rtx-5060-ti
wyniki:
  - qwen3-8-27b | rtx-5060-ti | 62.6 t/s | czat T=1 T; UD-IQ4_XS 32k, 150 W | 2026-10-20
  - qwen3-8-27b | rtx-5060-ti | 244.2 t/s | mvs; UD-IQ4_XS | 2026-10-20
---
# Raport 31: RTX 5060 Ti 16 GB, UD-IQ4_XS 32k

**Na 5060 Ti czat T=1 26.7 (U0) → 40.6 (U1) → 62.6 t/s (T), mvs 244.2 t/s; bramka GPU verify 22/22 md5 (2026-10-20).**

- Zysk tylko ×2.34, bo zwykły token czyta już 381 z 448 GB/s (85% pasma, limit 150 W) (`31-5060ti:10-14`).
- 36 864 kontekstu → OOM; 32 768 przechodzi z 472 MiB zapasu.

## Powiązane
- [[raporty-2026-10-20-21]]
- [[rtx-5060-ti]]
- [[sufit-pasma-i-mapa-czasu]]
