---
typ: ekosystem
tags: [ekosystem, narzedzia, wyniki-negatywne]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/21k-smokinggun.md:1-44; https://github.com/morluto/smokinggun (HEAD `cf3a387`); ~/KERNEL/product/research/21k-smokinggun.md:5-24,30-35
status: aktualne
---
# morluto/smokinggun: nie stosuje się do naszej pracy

**Mimo nazwy narzędzie nie szuka przyczyn regresji: to statyczny skaner wzorców złożoności w pętlach kodu CPU (tree-sitter, 13 języków, bez `.cu`/`.cuh`/`.hip`) plus porównanie zaimportowanych wyników benchmarków (hyperfine, pyperf, Google Benchmark, criterion, JMH, pprof, Perfetto) z gate'em eligible/blocked/inconclusive; MIT, TypeScript/Node, ostatni commit 2026-08-29 (raport 21k, 2026-10-19).**

Nie bisektuje, nie analizuje kerneli ani faultów GPU (raport 17), nie szuka rozbieżności numerycznych (raport 12, `llama-bx-diff`). Jedyna wspólna część – gate z dowodami – jest u nas silniejsza: [[fabryka-cli]] przypina sha256 binarek i modelu, liczy ABBA + A/A z 95% CI zamiast „mediana lepsza o X%” / rozłączne IQR, ma pełną taksonomię werdyktów i ledger z łańcuchem hashy; zasadę „brak dowodu ≠ pusty wynik” realizuje werdykt UNMEASURED. Werdykt: nie adoptować.

## Ze scalonej notatki: Raport 21k: morluto/smokinggun – nie dla nas

Smokinggun (MIT, TS, v5.0.0, HEAD `cf3a387`) to statyczny skaner pętli w kodzie CPU plus import-only porównanie benchmarków z gate’em; nie bisektuje, nie zna GPU – nie stosuje się (2026-10-19).

- Sześć reguł tree-sitter (13 języków, bez `.cu`/`.hip`) i gate eligible/blocked/inconclusive (`21k:9-10`).
- Nie diagnozuje faultów GPU ani rozbieżności numerycznych (`21k:12-16`).
- Część wspólna (gate z dowodami) jest u nas silniejsza: [[fabryka-v1]] przypina sha256, liczy ABBA + A/A z CI, ma werdykt UNMEASURED (`21k:18-24`).
- Repo: 52 commity, 32 gwiazdki (stan 2026-10-19, `21k:34`). Profil: [[smokinggun]].

## Powiązane
- [[fabryka-v1]]
- [[repos-30-przeglad]]
