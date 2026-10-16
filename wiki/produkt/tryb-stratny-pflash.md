---
typ: produkt
tags: [produkt, propozycja, prefill, pflash]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:10-11,118-135,222-237
status: do-sprawdzenia
---
# Propozycja: tryb stratny „szybki odczyt długich dokumentów” (PFlash)

**Propozycja z raportu 15d: PFlash tylko jako jawny tryb opt-in „szybki odczyt długich dokumentów (przybliżony)”, nigdy w sesjach agenta; decyzja po etapie C pilota (~$2 chmury).**

- Zysk: TTFT przy ≥ 32K nowych tokenów ×2.5–3.5 wobec naszego baseline'u na XTX `[INFERENCE]`; przy 120K pełny prefill ≈ 165 s vs ~50–55 s.
- Koszt jakości: −2/124 (publiczne zbiory), −4/102 (prywatne), −8/255 (MTRAG), LongBench-v2 −3/12; sondy trenowane po angielsku (pilot: 1/10 PL).
- Nie dla agenta: kompresja dopiero przy ≥ 16K nowych tokenów, historia agenta nigdy nie jest kompresowana.
- XTX: drafter BF16 1.5 GB + KV draftera; trzeba zejść z ctx 204800 do 131072 albo parkować cel.
- Wysiłek 15–25 osobodni natywnie w llama-server. Kill etapu C: spadek PL lub EN > 5 pp albo TTFT < ×2 przy 64K.
Odpowiedź w produkcie musi mówić wprost „odpowiedź z części dokumentu”.

## Powiązane
- [[produkt/_hub|produkt]]
- [[otwarte-decyzje-produktu]]
- [[produkt-optymalizacja-u-uzytkownika]]
- [[raport-15d-prefill-dlugi-kontekst]]
- [[2026-10-16-pflash-pilot-cpu]]
