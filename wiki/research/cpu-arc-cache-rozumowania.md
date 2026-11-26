---
typ: research
tags: [research, serwowanie, agenci, cache, produkt]
aktualizacja: 2026-11-26
zrodlo: arXiv 2611.09891 (Belcak, Heinrich, Muralidharan, Diao, Molchanov; NVIDIA; 2026-11-06), abstrakt + HTML; panel JARO 2026-11-26 (x.com/oliviscusAI/status/2125423669337829577)
status: aktualne
---
# CPU-ARC: rozwiązanie raz, potem tylko uruchamianie kodu na CPU

**Mocny model (Claude Opus 4.5) zamienia ślad rozumowania z rozwiązanego zadania w funkcje Pythona z parametrami; podobne zadania z innymi liczbami albo innym sformułowaniem obsługuje CPU (dopasowanie przez osadzenia + mały model 1B do drobnych kroków tekstowych), a gdy cache nie pasuje, pytanie wraca do dużego modelu. Na 7 z 8 testów matematyczno-naukowych wynik równy albo lepszy od modelu źródłowego (AIME'25 93,3 vs 83,3%), ≥ 90% przeformułowanych wariantów obsłużonych; wywołanie 16–291× tańsze, ale zbudowanie cache kosztuje 12–84× jednego rozumowania.**

## Czy to coś dla kerneli i prędkości?
- **Nie dla silnika.** To warstwa aplikacji/agenta (cache semantyczny przed modelem), nie kernel ani dekod: nic nie przyspiesza t/s na karcie.
- **Dla produktu (Enigma) tak, jako funkcja serwera agenta:** agent, który powtarza to samo zadanie z nowymi danymi (raporty, konwersje, obliczenia), płaci raz za rozumowanie, potem uruchamia funkcję. Opłaca się dopiero przy wielu powtórzeniach (koszt budowy 12–84×).
- **Dla naszej pracy już to robimy w prostszej formie:** zasada sesji „serię poleceń składaną trzeci raz zapisuję jako narzędzie w `~/dev/KERNEL/tools`” (np. `kol`, `wall.py`, skrypty kolejki) to ręczne ARC: rozumowanie raz, potem kod.
- Ryzyko: poprawność przy trafieniu zależy od tego, czy funkcja obejmuje wariant; autorzy proponują asynchroniczny przegląd przez człowieka albo AI.

## Na później
- **Warstwa agentów i produktu:** cache rozwiązań jako kod (CPU-ARC) dla powtarzalnych zadań agentów omp/Jarvo: zamiast drugi raz rozumować, uruchomić funkcję; ma sens, gdy będziemy mieli ruch z wieloma podobnymi zapytaniami (serwer API Enigmy).
- **Pomiar:** wtedy liczyć trafienia cache i oszczędzony czas karty, nie prędkość dekodu.

## Test u nas
- Nie da się zmierzyć jako prędkość karty: to warstwa agenta (cache rozwiązań na CPU), a nie silnika. Test w harnessie agentów: ten sam zestaw 20 zadań z `~/qwen-opt/k120/agent.py` w dwóch wariantach liczbowych, z cache i bez; liczyć trafienia i czas — do zrobienia, gdy JARO zechce rozwijać warstwę agentów.

## Powiązane
- [[narzedzia/_hub|narzędzia]]
- [[adapter-pod-omp-2026-11-26]]
