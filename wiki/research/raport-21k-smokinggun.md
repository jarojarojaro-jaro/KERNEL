---
typ: research
tags: [research, narzedzia, benchmarki]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/21k-smokinggun.md:5-24,30-35
status: aktualne
---
# Raport 21k: morluto/smokinggun – nie dla nas

**Smokinggun (MIT, TS, v5.0.0, HEAD `cf3a387`) to statyczny skaner pętli w kodzie CPU plus import-only porównanie benchmarków z gate’em; nie bisektuje, nie zna GPU – nie stosuje się (2026-10-19).**

- Sześć reguł tree-sitter (13 języków, bez `.cu`/`.hip`) i gate eligible/blocked/inconclusive (`21k:9-10`).
- Nie diagnozuje faultów GPU ani rozbieżności numerycznych (`21k:12-16`).
- Część wspólna (gate z dowodami) jest u nas silniejsza: [[fabryka-v1]] przypina sha256, liczy ABBA + A/A z CI, ma werdykt UNMEASURED (`21k:18-24`).
- Repo: 52 commity, 32 gwiazdki (stan 2026-10-19, `21k:34`). Profil: [[smokinggun]].

## Powiązane
- [[research/_hub|research]]
- [[raporty-2026-10-19-20]]
- [[smokinggun]]
- [[fabryka-v1]]
- [[raport-21j-flameox]]
