---
typ: chmura
tags: [chmura, amd, darmowe]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:38-40,77,114,139,161-167,206,299,366,407,418
status: aktualne
---
# AMD Developer Cloud i inne programy AMD

**AMD daje $100 kredytu na MI300X (30 dni) i krótkie testy stacji Radeon PRO, ale z zakazami użycia komercyjnego; dla nas tylko do sanity-checku kodu HIP na CDNA3.**

| program | co | warunki |
|---|---|---|
| AMD AI Developer Program → Developer Cloud (DigitalOcean / Vultr) | MI300X 1× lub 8×, $100 kredytu na 30 dni | karta płatnicza; nie wolno „provide a service to a third-party” |
| AMD Cloud Evaluation, ścieżka „25 h” | ~25 h / ~$50, wygasa po 10 dniach | po akceptacji |
| AMD Instinct Evaluation Program | MI300X/MI325X u partnerów CSP | startupy, odpowiedź w 2 tyg. |
| AMD Radeon Test Drive | W7800, W7900 (gfx1100), R9700, ≤ 14 dni | „commercial use strictly prohibited” |

Ceny MI300X na rynku: Dev Cloud/DO $1.99/h, Vultr $1.75 (8×), RunPod $2.39, Hot Aisle $2.99.

Rekomendacja raportu 05: MI300X tylko z darmowego kredytu, do sprawdzenia wspólnego kodu HIP na CDNA3; użycie do tuningu produktu komercyjnego to szara strefa — zapytać AMD (otwarte pytanie: czy AMD da „partner access” do Radeonów, np. przez program ISV). Profilowanie w VM DO: „prawdopodobnie tak” [INFERENCE raportu].

## Powiązane
- [[chmura/_hub|Chmura]]
- [[mi300x]]
- [[radeon-ai-pro-r9700]]
- raport-05-chmura
- amd
