---
typ: decyzja
tags: [decyzje, chmura, priorytety]
aktualizacja: 2026-10-20
zrodlo: polecenie użytkownika 2026-10-20 (czat z Main); ~/KERNEL/product/PLAN-NV-V2.md
status: aktualne
---
# 2026-10-20: testy w chmurze wstrzymane, priorytet XTX i research

**Użytkownik (2026-10-20): „na razie testy cloud GPU odpuszczamy — robimy research z nowych tematów i patrzymy, jak zoptymalizować Qwena na XTX”. Plan v2 kampanii NVIDIA (PLAN-NV-V2.md, doładowanie $8 / wariant $3) czeka; nic nie wynajmujemy.**

Konsekwencje:
- Praca GPU tylko na lokalnej RX 7900 XTX przez kolejkę (`run-jobs.sh`), według zasad 10/20 min i bramek md5.
- Research nowych tematów + codzienny wywiad konkurencji ([[2026-10-20-bez-publikacji-localmaxxing]]) zasila listę eksperymentów na XTX.
- Decyzje kampanii NVIDIA (3060 na Qwen3.6-35B-A3B zamiast Saluki/Bonsai, 3080 z płatnym transferem) wracają przy wznowieniu.

## Powiązane
- [[decyzje/_hub|Decyzje]]
- [[2026-10-20-kontekst-min-131k]]
- [[lekcja-vast-transfer-kosztuje]]
- [[qwen3-8-27b]]
