---
typ: lekcja
tags: [lekcje, benchmark, enigma, pomiar]
aktualizacja: 2026-11-05
zrodlo: ~/qwen-opt/queue/logs/enigma-xtx2.log:50,67,100; ~/qwen-opt/queue/logs/enigma-xtx3.log:32,126-127; git 1af7fd2
status: aktualne
---
# Benchmark musi dać obu ramionom identyczne tokeny

**W Enigmie kandydat renderował prompt własnym szablonem czatu (inne myślenie), więc baseline i kandydat liczyły różne obciążenia; wynik +191.5% (2026-11-05 14:30) był zawyżony względem uczciwego +179.8% (15:08).**

- Objaw: md5 i liczby promptów różne między ramionami, a raport i tak mówił „kept”. Różnica długości/rodzaju odpowiedzi zmienia akceptację spekulacji i t/s bardziej niż wiele łatek.
- Reguła: workload renderowany **raz** (na baseline), te same tokeny bajt w bajt do każdego ramienia; ten sam reasoning effort i temperatura; próg szumu z powtórzonego baseline'u; zwycięzca potwierdzany drugim przebiegiem ([[enigma-uczciwy-benchmark]]).
- To wzorzec z katalogu reward hackingu: optymalizator „wygrywa”, zmieniając zadanie zamiast szybkości ([[reward-hacking-inferencji]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-higiena-pomiaru]]
- [[lekcja-agent-zmienia-protokol]]
- [[enigma-uczciwy-benchmark]]
