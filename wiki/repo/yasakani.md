---
typ: repo
tags: [repo, konkurencja, rtx-5090, qwen3-8-27b]
aktualizacja: 2026-11-05
zrodlo: ~/KERNEL/product/research/63a-silniki-lokalne.md:18-23,40-47,247-284; https://x.com/yasakani_dev/status/2117521489885090271 ; https://x.com/yasakani_dev/status/2117529802844610956
status: do-sprawdzenia
---
# YASAKANI: „1220 t/s” Qwen3.8-27B na RTX 5090

**Własny silnik i format (fast 11.7 GB) na 5090 stock; 1220 t/s na JSONL i 1241 na edycji pliku to ~11–12 tokenów na krok weryfikacji na tekście powtarzającym strukturę, nie nowy algorytm (2026-11-03, bez kodu).**

- Normalizacja na XTX (pasmo ×0.536, bajty 11.7/16.83): edycja ~462 vs nasze `mvs` 433.8 (parytet); thinking T=1 mediana 381 → ~142 vs nasze 114.8.
- Autor sam poprawił prozę 424 → 303 (pętla greedy zawyżała).
- Format 12.4 GB przy KLD 0.021 to klasa trellis; zmiana kwantu wag jest dla nas wykluczona ([[2026-11-05-tylko-bezstratne]]).
- Do zrobienia: watch konta i repo po publikacji; ich zestaw zadań (fixture NInfer) uruchomić na XTX jako wspólny punkt.

## Powiązane
- [[repo/_hub|repo]]
- [[ninfer]]
- [[zestaw-copy-mvs]]
- [[lekcja-benchmark-kopia]]
- [[raport-63-synteza]]
