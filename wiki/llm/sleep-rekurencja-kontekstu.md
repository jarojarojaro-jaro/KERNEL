---
typ: llm
tags: [llm, trening, architektura, rekurencja, pretrening]
aktualizacja: 2026-11-26
zrodlo: arXiv 2611.32802 (Lee i in., Microsoft Research + CMU, 2026-11-24); arXiv 2605.26099 (poprzednia praca o „sleep”); panel JARO 2026-11-26 (x.com/scaling01/status/2125343228375531743)
status: aktualne
---
# „Sleep”: model przelicza fragment kontekstu N razy, zanim czyta dalej

**Transformer co pewien fragment kontekstu robi N rekurencyjnych przejść po tym samym fragmencie („śpi”), zanim przyjmie nowe tokeny. Modele do 1,2B parametrów, trenowane od zera na do 100B tokenów: na nieznanym kodzie N=2 i N=4 osiągają stratę modelu bez snu przy 2,10× i 2,39× mniejszej liczbie tokenów w kontekście, a do tego szybciej uczą się z kilku przykładów i mają niższą stratę na danych spoza rozkładu.**

## Co to znaczy dla nas
- **Trening:** to cecha pretreningu (mechanizm wbudowany od początku), nie dostrojenie gotowego modelu. Dla naszych LoRA i ablacji nie do użycia; ciekawe jako kierunek architektur po „looperach” (Inkling 2 Mini zapętla 12 warstw 3× na każdy token).
- **Inferencja:** koszt idzie w przetwarzanie kontekstu: N przejść po fragmencie to ok. N× pracy prefillu na ten fragment, przy dekodowaniu zależnie od tego, jak często model „śpi”. Autorzy sami nazywają to kompromisem między adaptacją a opóźnieniem dekodu. Dla silnika to ta sama lekcja co pętla Inklinga: więcej obliczeń na bajt wag, więc przewagę dają fuzje i grafy, nie pasmo.
- **Tweet „SLEEP-LOOPERS 2027/2028”** to prognoza autora tweeta, bez liczb.

## Na później
- **Własny trening modeli z pętlą warstw** (Inkling już ma pętlę warstw 6–17): „sen” na fragmentach kontekstu to sposób, by mniejszy model lepiej uczył się z kontekstu.
- **Inferencja:** N przejść po fragmencie kosztuje N× prefill tego fragmentu; ważne przy liczeniu kosztów, gdyby taki model trafił do topki.

## Test u nas
- Nie da się zmierzyć na naszych modelach: wymaga modelu trenowanego od zera z tym mechanizmem (do 1,2B w pracy), a żadnego takiego nie mamy; wraca, gdy autorzy wydadzą wagi albo gdy zaczniemy trenować własne.

## Powiązane
- [[trening-llm-mapa]]
- [[inkling-2-mini]]
