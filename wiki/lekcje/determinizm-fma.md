---
typ: lekcja
tags: [lekcje, numeryka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:262-265; ~/KERNEL/qwen-opt/NOTES.md:261,377; ~/KERNEL/qwen-opt/research/qwen-round5.md:10-16
status: aktualne
---
# Determinizm: kontrakcja FMA i świeży serwer

**Bity zmieniają się z trzech powodów: kompilator łączy mnożenie z dodawaniem w FMA, weryfikacja batcha liczy inaczej niż N=1, a llama.cpp nie jest deterministyczny w obrębie jednego serwera.**

- Kontrakcja FMA: rozwinięta suma x·x dała 1 ulp w ~4% wierszy (0025); GDN fast 94 vs 83 FMA → inny md5. Reguła: jawny łańcuch `fmaf`, `ggml_cuda_no_contract`, stary kernel nietknięty.
- Spekulacja: MTP rozjeżdża się z plain po 129 znakach, DFlash po 229 — porównujemy MTP z bazą MTP.
- Serwer: ten sam greedy request przy 2. wywołaniu rozjeżdża się po ~270 znakach (upstream też) — greedy md5 zawsze na świeżym serwerze.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[zgodnosc-bitowa-md5]]
- [[rmsnorm-dpp]]
- [[2026-10-16-bit-exact]]
