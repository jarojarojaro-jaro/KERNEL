---
typ: eksperyment
tags: [eksperymenty, spekulacja, mtp, slownik]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21c-copy-paste-lm.md:157-174,198-202; ~/KERNEL/product/research/21c-cplm/oov.txt:12-15; ~/KERNEL/product/research/21c-cplm/oov_steps.txt:2-8
status: aktualne
---
# 2026-10-19: tokeny spoza słownika draftu 64k (CPU)

**Poza 65 536 najczęstszymi tokenami słownika draftu leży 2.83% tokenów czatu (pl-proza 4.96%) i 0.93% wyjść agenta, z czego w kontekście jest odpowiednio 33.8% (pl-proza 21.6%) i 75.6%; słownik „64k ∪ tokeny kontekstu” ma sufit +0.8…+1.7% tok/krok.**

Sufit tok/krok (łańcuch MTP ucinany na tokenie spoza słownika): czat EN +0.97%, czat PL +1.68%, agent +0.77…+1.32%. Górna granica, bo MTP na rzadkich tokenach trafia rzadziej. Koszt ~4k dodatkowych wierszy × 2.7 KB w IQ4_XS ≈ 11 MB na przebieg draftu; wymaga dynamicznego zbioru wierszy i stałych slotów (np. 64k + 4096) dla cache'a grafu, ~1–2 dni.

Priorytet niski: wcześniejsze wyniki `--spec-draft-vocab` (16k −5%, 32k +7%, 64k +7.5%, 96k +6%) pokazują, że większe pokrycie samo mało daje. Kill: < +1% t/s na `spec_sweep` PL przy ABBA.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[latki-spekulacji]]
- [[glowica-mtp]]
- [[raport-21c-cplm]]
