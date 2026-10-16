---
typ: produkt
tags: [produkt, plan, ryzyka]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:475-487; ~/KERNEL/product/research/15c-nowe-silniki.md:389-393
status: aktualne
---
# Największe ryzyka

**Dziewięć ryzyk z odpowiedziami; najgroźniejsze: zysk nie przenosi się poza 7900 XTX/Linux oraz wbudowanie auto-tuningu przez LM Studio, Ollamę, Jana lub NVIDIA.**

| ryzyko | p / wpływ | odpowiedź |
|---|---|---|
| zysk tylko na XTX/Linux | średnie / wysoki | faza 0 (E3, E4) przed aplikacją |
| konkurencja wbuduje auto-tuning | wysokie / wysoki | fosa L3 + baza profili + AMD-first |
| upstream ucieka | wysokie / średni | semver, budżet łatek, bot rebase |
| fałszywe „po” (szum) | średnie / wysoki | ABBA, A/A, „brak istotnej zmiany” |
| crash nocą (TDR, laptop) | średnie / wysoki | limity, checkpointy, tylko zasilacz |
| AI Act 50(2) vs „bit w bit” | średnie / wysoki | opinia prawna, ten sam watermark w A/B |
| brak popytu na płatną edycję | średnie / średni | fake-door, B2B/OEM |
| AV/SmartScreen | wysokie / średni | podpis, MS Store |
| zależność od HF | niskie–średnie / wysoki | pin rewizji, mirror |
| Magnitude jako „LM Studio z własnymi kernelami” dla agentów (raport 15c) | już jest / wysoki na Mac i NVIDIA, niski na AMD | AMD natywnie, baseline vs tuned upstream i jakość na ekranie wyniku, dowolny GGUF i MoE offload, LocalMaxxing |

Nowe ryzyko z 2026-10-16: Magnitude ma 6.9k★ w 4 miesiące, ale brak HIP, brak bitowej bramki i brak MoE offload (#194).

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-roadmapa]]
- [[werdykt]]
- [[raport-06-produkt]]
- [[wyniki-negatywne]]
- [[magnitude]]
- [[zawezenie-tezy-produktu]]
