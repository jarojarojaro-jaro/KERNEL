---
typ: eksperyment
tags: [eksperymenty, prefill, pflash, pl]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:137-183; ~/KERNEL/product/research/15d-pilot/results.jsonl
status: aktualne
---
# 2026-10-16: pilot CPU selekcji PFlash v2 po polsku i angielsku

**Kopia selekcji PFlash v2 na CPU ($0): głowica Q/K przenosi się na polski, ale sonda żądania trenowana po angielsku wskazała pytanie jako top-1 w 1/10 przypadków PL wobec 10/10 EN.**

Ustawienie: drafter `Qwen3.5-0.8B-BF16.gguf` obcięty do 15 bloków, tap przez `llama-embedding --pooling none` na CPU; sondy i selekcja odtworzone w numpy; budżet ~30% przy 20–23K; dokument PL 22.9K tokenów (37 notatek wiki), EN 19.8K tokenów; 10 pytań na język.

| metryka | PL | EN |
|---|---|---|
| sonda żądania: top-1 = pytanie | 1/10 | 10/10 |
| dowód zachowany, zapytanie tylko z sondy | 6/10 | 10/10 |
| dowód zachowany, blend release | 10/10 (ranga mediana ~10) | 10/10 (ranga 1–2) |
| dowód zachowany, wyrocznia (dokładne pytanie) | 10/10 | 10/10 |
| BM25 | 10/10 | 10/10 |
| losowe jednostki | 0.45 | 0.49 |
| tap na CPU | ~150 tok/s | ~160 tok/s |

W 9/10 PL sonda wzięła za „żądanie” tytuł wklejonej notatki. Test łatwy (BM25 też 10/10), mierzy tylko selekcję, nie odpowiedź. Lekarstwo: dotrenować sondę żądania (265k parametrów) na polskich promptach – etap B planu E2.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[lekcja-sondy-en-na-polskim]]
- [[lucebox]]
- [[tryb-stratny-pflash]]
