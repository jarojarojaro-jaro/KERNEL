---
typ: lekcja
tags: [lekcje, chmura, dane]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:309-312; ~/qwen-opt/cloud/results/3060-20261016/NOTE-quantkld-overwrite.txt:1-5; ~/qwen-opt/cloud/collect.sh:18-20; komunikat Main do WikiIngest 2026-10-18
status: aktualne
---
# Katalog wyników `<klasa>-<data>` nie jest unikalny: collect nadpisał dane raportu 09

**Po awarii omp (2026-10-16) rodzic uruchomił `collect.sh` dla instancji 3060 agenta QuantKLD; rsync `/root/results/` zapisał jej `3060-20261016/` na lokalny katalog o tej samej nazwie z raportu 09 i nadpisał `hw/*` (5 plików) oraz część `build/*` (m.in. `times.jsonl`, `downloads.tsv`, `fork-head.txt`) – oryginały raportu 09 są stracone.**

Naprawa: dane QuantKLD przeniesione do `quantkld-20261016/3060-hostA/`, opis szkody w `NOTE-quantkld-overwrite.txt`; `collect.sh` używa teraz `rsync --backup --suffix=.prev-<timestamp>`, więc kolejne nadpisanie zostawia kopię.

Reguła: katalog wyników każdego przebiegu ma unikalną nazwę (etykieta instancji albo agent + znacznik czasu); para klasa-data nie wystarcza, bo tego samego dnia może być kilka instancji tej samej klasy.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[raport-09-chmura-3060]]
- [[skrypty-chmury]]
- [[lekcja-uslugi-poza-omp]]
