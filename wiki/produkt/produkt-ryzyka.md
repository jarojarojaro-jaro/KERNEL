---
typ: produkt
tags: [produkt, plan, ryzyka]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/PLAN.md:475-487; ~/KERNEL/product/research/15c-nowe-silniki.md:389-393; ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:308-321; ~/KERNEL/product/research/16d-magnitude-vs-nasz.md:131-138; ~/KERNEL/product/research/16j-magnitude-vulkan-xtx.md:85-91; ~/KERNEL/product/research/21g-nowe-silniki.md:359-362
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

Magnitude (2026-10-16): wygrywa code-edit 1.35–1.56×; nasze przewagi: polski (9B sweep 121.0 vs 68.2 t/s), 27B Q3_K_XL na 16 GB (u nich się nie ładuje), LFM 64k na 16 GB (u nich OOM), prefill 27B na 3090 (64k 72.4 vs 86.4 s). Magnitude Vulkan na XTX zmierzony 2026-10-18: my ×1.94–×2.22 (Qwen 27B), ×1.42–×2.24 (LFM); ich przewaga na AMD to tylko instalacja bez ROCm ([[2026-10-18-magnitude-vulkan-xtx]], [[firma-magnitude]]).

21g (2026-10-19): TensorFold 27B + DFlash2 na NVIDIA (5090 263/367 t/s) wymaga A/B z naszym forkiem na 3090; Strata uruchamia 125B MoE na XTX + 96 GB RAM z ~80 t/s – alternatywa dla użytkowników z dużym RAM-em ([[raport-21g-nowe-silniki]]).

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-roadmapa]]
- [[werdykt]]
- [[raport-06-produkt]]
- [[wyniki-negatywne]]
- [[magnitude]]
- [[zawezenie-tezy-produktu]]
