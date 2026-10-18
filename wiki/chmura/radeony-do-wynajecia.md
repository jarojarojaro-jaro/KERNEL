---
typ: chmura
tags: [chmura, amd, bare-metal]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:22-28,71-76,130-141,258-260,289-292,403; komunikat Main do WikiIngest 2026-10-18 (portal SaladCloud, 2026-10-18)
status: aktualne
---
# Gdzie wynająć Radeona, Arca i Maca (Hostkey, GigaGPU, Scaleway, hyperscalerzy)

**Konsumenckich Radeonów z root prawie nie ma w chmurze godzinowej; jedynym RDNA4 na godziny jest Hostkey R9700, reszta to dedyki miesięczne albo WSL2 bez `/dev/kfd`.**

| dostawca | co | forma | cena (2026-10) |
|---|---|---|---|
| Hostkey (NL) | Radeon AI PRO R9700; 4× RX 7900 XTX (pre-order) | bare metal, root, IPMI | R9700 €0.471/h |
| GigaGPU (UK) | RX 9070 XT, R9700, Ryzen AI Max+ 395, Arc Pro B60/B70 | dedyk miesięczny, root | 395 £299/mies., B60 £129, B70 £179 |
| Scaleway | Mac mini M4 / M4 Pro | bare metal macOS, min. 24 h | €0.22/h / €0.49/h |
| Azure NGads V620 | Radeon PRO V620 (RDNA2, gfx1030), 1/4–1 GPU | VM | $0.635–2.54/h; ROCm niezweryfikowany |
| AWS G4ad | Radeon Pro V520 (RDNA1) | VM | wycofywane od 2026-09-01 |
| SaladCloud | 5 klas Radeonów | kontener WSL2 | 0.04–0.17 $/h |

Wnioski raportu 05: AMD i Intela kupujemy (RX 9070 XT €694, Arc B580 €270), bo podaż w chmurze jest punktowa (jeden host w NL, jeden w UK, Salad) i może zniknąć; Hostkey R9700 jako „przelew” na równoległe kampanie RDNA4 (zakup 9070 XT zwraca się po ~1,470 h wynajmu).

Stan 2026-10-18: RX 7900 XTX nie da się wynająć ani na Vast, ani na RunPod, a klasy AMD w Salad są niedostępne dla naszej organizacji ([[salad]]).

## Powiązane
- [[chmura/_hub|Chmura]]
- [[salad]]
- [[radeon-ai-pro-r9700]]
- [[arc-b580-i-mac]]
- raport-05-chmura
