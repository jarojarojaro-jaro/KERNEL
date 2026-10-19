---
typ: research
tags: [research, kwantyzacja, kld]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:1-374
status: aktualne
---
# Raport 16e: nowe kwanty 27B na 12–16 GB (E1 + E3 z 15e)

**Agent QuantKLD zmierzył 12 ramion kwantów Qwen3.8-27B/Swift/Saluki/Bonsai (KLD do BF16 na 5 korpusach, 20 zadań, prędkość na 3060 i 5060 Ti) w dwóch rundach (2026-10-16, dokończenie po awarii omp 2026-10-18).**

Hipotezy 15e: H1 (GSQ/Swift-mtp ≥ 1.3 × Saluki przy niższym KLD) potwierdzona (W2 ×1.46, KLD 0.164 < 0.257); H2 (Swift −20% tokenów) na granicy; H3 (GSQ na 16 GB gorszy w KLD-PL) potwierdzona. Kill: GSQ 16 GB zadziałał, MTP 12 GB / Swift / AP nie.

Rekomendacje (czekają na decyzję, [[otwarte-decyzje-techniczne]]): 16 GB U3 → A3 po bramce na forku; 12 GB IQ3_XXS-mtp (W3 zmierzony, ISTA IQ3_XXS-mtp do jednego przebiegu KLD); Swift jako tryb „mniej zapętleń” (licencja).

Zastrzeżenia: host 3060 A przycięty do 120 W (tylko porównania wewnątrz hosta), LanguageTool na ~550 słowach to szum, seedy zadań na różnych kartach. Wyniki: [[2026-10-18-e1-kwanty-27b-kld]], metoda: [[kld-po-polsku]].

Lekcje operacyjne (§7): [[lekcja-build-przed-wynajmem]], [[lekcja-bootstrap-numpy]], [[lekcja-limit-cpu-kontenera]], [[lekcja-zabicie-skryptu-nie-serwera]], [[lekcja-pkill-wlasna-powloka]], [[lekcja-unikalny-katalog-wynikow]], [[lekcja-limit-mocy-hosta]]; host 5060 Ti z HF 1 MB/s wymieniony po ~55 min.

## Powiązane
- [[research/_hub|research]]
- [[raport-15e-kwantyzacja-nowa]]
- [[lekcja-kld-protokoly]]
- [[lekcja-unikalny-katalog-wynikow]]
