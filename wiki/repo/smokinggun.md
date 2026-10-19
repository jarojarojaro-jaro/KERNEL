---
typ: repo
tags: [repo, narzedzia, wyniki-negatywne]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21k-smokinggun.md:1-44; https://github.com/morluto/smokinggun (HEAD `cf3a387`)
status: aktualne
---
# morluto/smokinggun: nie stosuje się do naszej pracy

**Mimo nazwy narzędzie nie szuka przyczyn regresji: to statyczny skaner wzorców złożoności w pętlach kodu CPU (tree-sitter, 13 języków, bez `.cu`/`.cuh`/`.hip`) plus porównanie zaimportowanych wyników benchmarków (hyperfine, pyperf, Google Benchmark, criterion, JMH, pprof, Perfetto) z gate'em eligible/blocked/inconclusive; MIT, TypeScript/Node, ostatni commit 2026-08-29 (raport 21k, 2026-10-19).**

Nie bisektuje, nie analizuje kerneli ani faultów GPU (raport 17), nie szuka rozbieżności numerycznych (raport 12, `llama-bx-diff`). Jedyna wspólna część – gate z dowodami – jest u nas silniejsza: [[fabryka-cli]] przypina sha256 binarek i modelu, liczy ABBA + A/A z 95% CI zamiast „mediana lepsza o X%” / rozłączne IQR, ma pełną taksonomię werdyktów i ledger z łańcuchem hashy; zasadę „brak dowodu ≠ pusty wynik” realizuje werdykt UNMEASURED. Werdykt: nie adoptować.

## Powiązane
- [[repo/_hub|repo]]
- [[fabryka-v1]]
- [[repos-30-przeglad]]
