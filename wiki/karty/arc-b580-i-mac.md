---
typ: karta
tags: [karty, intel, apple]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:291,294-296; ~/KERNEL/product/research/05-chmura-gpu-do-testow.md:26-28,121,241-242,259-260,324-325
status: aktualne
---
# Intel Arc B580 i Mac mini M4 (platformy spoza AMD/NVIDIA)

**Dwie platformy z listy MVP, których nie da się wynająć z root na godziny (Arc) albo wynajmuje się je tylko z 24-godzinnym minimum (Mac); w planie zakup.**

**Intel Arc B580** (Xe2, 12 GB):
- brak podaży godzinowej; alternatywa GigaGPU Arc Pro B60 £129/mies. lub B70 £179/mies.;
- używana mediana €270 (nowa $370); zakup zwraca się po ~2 mies. vs dedyk B60;
- PLAN §5.2: pozycja 5 na liście zakupów, „jedyny realny Intel”.

**Mac mini M4** (Apple M4, 16 GB; okazjonalnie M4 Pro 64 GB):
- Scaleway €0.22/h (M4 16 GB, €149/mies.) i €0.49/h (M4 Pro 64 GB), minimum 24 h z licencji Apple; AWS mac-m4pro ~$1.97/h;
- zakup ~$650–800 używany, od $799 nowy; zwrot po ~5 mies.;
- PLAN: Scaleway na start, zakup od bety; macOS w fazie 3 (Metal, potem MLX).

Nasze łatki na tych platformach: z 70 przenoszą się tylko host i sampler (F1) oraz spekulacja na poziomie grafu (F2); reszta to nowa kampania na innym backendzie (raport 07).

## Powiązane
- [[karty/_hub|Karty]]
- raport-05-chmura
- plan-produktu
- [[klasyfikacja-latek]]
- [[inne-karty-nvidia]]
