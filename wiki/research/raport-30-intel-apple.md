---
typ: research
tags: [research, chmura, intel, apple]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/30-intel-apple-dostep.md:7-11,26-38,142-149
status: aktualne
---
# Raport 30: dostęp do Intel Arc i Apple Silicon + plan testów na M1 Pro

**Godzinowego wynajmu Intel Arc nie ma nigdzie (Vast 2026-10-20: 0 Intel na 5039 ofert); Apple: Scaleway M4-M 32 GB €0.29/h z minimum 24 h (€6.96), Enverge Mac Studio M5 Ultra $2.50/h rozliczane co minutę; Darkbloom to API inferencji, nie wynajem (2026-10-20).**

- Intel z rootem tylko jako dedyk miesięczny: GigaGPU Arc Pro B60 £129/mies. (ten sam BMG-G21 co B580) (`30:20,143`).
- AWS EC2 Mac: m4 $1.23/h … m3ultra $12.50/h, minimum 24 h (licencja macOS SLA §3A) (`30:30,38,145`).
- M1 Pro 16 GB: limit GPU 2/3 RAM = 10922.67 MiB; mieści Saluki 27B IQ2-mix + MTP (8.35 GB), Qwen UD-IQ3_XXS dopiero po `iogpu.wired_limit_mb=12288` (`30:11,148`).
- GUMBEL_MAX (sprzężone) ma tylko CPU i CUDA; opy GPU verify są w Metal/Vulkan/SYCL (`30:149`).
- Lekcja: [[lekcja-dostep-intel-apple]]. Karta: [[arc-b580-i-mac]]. Poprzednio: [[raport-05-chmura]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[lekcja-dostep-intel-apple]]
- [[arc-b580-i-mac]]
- [[raport-05-chmura]]
