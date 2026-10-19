---
typ: decyzja
tags: [decyzje, cache, ssd]
aktualizacja: 2026-10-19
zrodlo: komunikat Main do WikiIngest 2026-10-19 (decyzja użytkownika); ~/KERNEL/product/research/21d-kv-na-dysku.md:168-193; ~/KERNEL/product/research/17-gpu-page-fault.md:333-375
status: aktualne
---
# 2026-10-19: cache sesji/KV tylko w RAM, bez warstwy SSD

**Użytkownik zdecydował (2026-10-19): „zostawiamy głównie RAM offload, jak już SSD nie ruszamy” – stan sesji i KV trzymamy tylko w RAM (`--cache-ram`, ewentualnie tmpfs), niczego z KV/sesji nie zapisujemy na dysk; warstwa L3 SSD z raportu 21d odpada.**

Konsekwencje:
- Budżet RAM na tym serwerze: 62 GB, dziś `--cache-ram 16384` (wpis Qwena 53k ≈ 2.3 GB, LFM ≈ 0.55 GB); limit musi zostawić page cache na wagi (Qwen 17.6 GB + LFM).
- Kopie stanu `--cache-ram` z pamięci stronicowanej zostawiają zakresy SVM, których unieważnianie ewikuje kolejki KFD (wyzwalacz resetów PM4, [[hip-kopie-stronicowane-zostawiaja-svm]]) – cache RAM musi omijać ten mechanizm (`HSA_USE_SVM=0` albo transfery przez pinned; test S3, [[2026-10-19-pm4-priv-analiza]]).
- Sprawdzanie odcisku modelu przy restore nadal potrzebne także dla przywracania z RAM (para Main ↔ Uncensored o tych samych kształtach, [[przelaczanie-main-uncensored]], [[lekcja-restore-stanu-exactness]]).
- Projekt i budżet zużycia SSD z 21d zostają jako analiza, bez wdrożenia ([[kv-na-dysku-polityka]]).

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[cache-sesji-na-dysku]]
- [[raport-21d-kv-na-dysku]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
