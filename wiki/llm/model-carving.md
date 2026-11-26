---
typ: llm
tags: [llm, trening, architektura, pruning, petla]
aktualizacja: 2026-11-26
zrodlo: arXiv 2611.27962 (Zheng, Sharma, 2026-11-20); kadenzheng.com/model-carving; github.com/KadenZheng/model-carving; panel JARO 2026-11-26 (x.com/kadenzheng/status/2125648943971213813)
status: aktualne
---
# Model Carving: trening sam wycina zbędne podwarstwy

**Każda podwarstwa (atencja, MLP) dostaje uczony bramkowy skalar; strata treningu może go wyzerować, więc z gęstego Transformera zostaje mniejsza, niejednorodna sieć. Pretrening od zera 140M–2,7B (i modele z pętlą warstw 140M–1,3B): przy tym samym koszcie treningu niższa strata walidacyjna niż gęste modele trenowane do 1,7× dłużej, lepsze od modeli tej samej wielkości z pruningu i destylacji; do 34% mniej FLOPów na token i do 1,6× szybszy dekod bez straty jakości (deklaracja autorów, abstrakt).**

## Co to znaczy dla nas
- **Trening od zera, nie gotowy model.** Metoda działa w trakcie pretreningu; nie wycina warstw z naszego Qwen3.8-27B ani Inklinga bez ponownego treningu. Autorzy wprost: „lepiej wycinać w treningu niż kompresować duży model potem”.
- **Dla silnika:** wycięty model ma różne warstwy (część bez atencji, część bez MLP), więc grafy, fuzje i harmonogram muszą obsługiwać niejednorodną budowę; 1,6× dekodu wynika z mniej bajtów i mniej kerneli na token. Lekcja ta sama co przy pętli Inklinga: kto przygotuje silnik na nieregularne modele, ten zyska.
- **Związek z edycją wag i pruningiem warstw** (np. pomijanie warstw w drafterze, „layer skip”): carving to wersja uczona w treningu; dla gotowych modeli najbliższe są eksperymenty z pomijaniem podwarstw z bramką KLD, ale to zmiana modelu, nie bezstratna optymalizacja.
- Nie mierzymy: brak gotowych dużych wyciętych modeli do pobrania na nasze karty (stan 2026-11-26, przypuszczam; repo autorów ma kod treningu).

## Powiązane
- [[trening-llm-mapa]]
- [[edycja-wag-a-z]]
- [[sleep-rekurencja-kontekstu]]
