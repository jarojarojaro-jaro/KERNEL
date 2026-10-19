---
typ: repo
tags: [repo, spekulacja, serwer]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:286-323; https://mtplx.com/releases/2.6.0
status: do-sprawdzenia
---
# MTPLX: współbieżny MTP dla wielu agentów

**Silnik z MTP w kohortach (3/8 strumieni) deklaruje 1.6–2.25× na strumień dla 2 agentów względem zwykłego batchingu AR; wspiera LFM2 (wydanie 2.6.0, stan 2026-10-19).**

Dla nas: dowód zewnętrzny dla pomysłu #4 raportu 18 (serwer wielostrumieniowy z batched MTP) – przez 37% czasu agentów w locie są ≥ 2 żądania ([[2026-10-19-workload-omp]]), a `-np 1` je szereguje. Liczby zgłoszone przez autorów, niezweryfikowane.

## Powiązane
- [[repo/_hub|repo]]
- [[raport-18-nastepna-fala]]
- [[suffixdecoding]]
