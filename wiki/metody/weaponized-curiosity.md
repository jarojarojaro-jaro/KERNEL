---
typ: metoda
tags: [metody, agenci, autoresearch, pomiar, proces]
aktualizacja: 2026-11-24
zrodlo: https://github.com/ayushrajsinghparihar/weaponized-curiosity (`0b6d2d3`, 2026-11-24, MIT; README, SKILL.md, references/, docs/evaluation/); https://x.com/PariharCodes/status/2124987196709245394; nasze wyniki procesu 24.11 w [[ashhart-skills-infra]]
status: aktualne
---
# Weaponized Curiosity: skill badań i autoresearchu dla agentów, porównany z naszym wyścigiem

**To sam proces w Markdownie (Codex, Claude Code), bez kerneli; 23.11 oceniłem go jako „to, co już robimy”, ale pomiar 24.11 pokazał, że trzech jego elementów nie mamy: zamrożonego ewaluatora z rezerwą na walidację, budżetu prób zapisanego przed startem i dziennika prób, który blokuje powtórki.**

## Jak działa (README, SKILL.md)
- Tryby: Quick (sprawdź tezę), Deep (do 4 niezależnych pracowników, potem porównanie), Extreme (więcej źródeł i replikacji), Autoresearch (cel liczbowy, limit prób, stały ewaluator).
- Budżet podany z góry (`searches=12 experiments=2 minutes=10`); jedna partia pomiarów zostawiona na walidację; surowe czasy w raporcie.
- Stan w `.research/<run-id>/` (źródła, hipotezy, próby T01, T02…, punkt wznowienia); raport mówi, co zmieniłoby decyzję i najtańszy sposób, żeby to sprawdzić.
- Uczciwa ewaluacja własna: pilot na syntetycznych zadaniach, 1 recenzent, „brak dowodu, że 4 agenty poprawiają decyzję”; 41× (autoresearch) na zabawce odrzucone przez limit pamięci.

## Porównanie z naszym procesem (wyścig Kernel vs Gemini na Mayi)
| element | oni | my (24.11) |
|---|---|---|
| ewaluator | zamrożony przed próbami | rep2 mediana 5; szum między restartami serwera nieznany do 24.11 (Q6 0,1%, L2k 0,9%) |
| walidacja | osobna partia na zwycięzcę | jedna para A/B, zwycięzca nie mierzony drugi raz (Enigma `optimize.ts` to robi, wyścig nie) |
| budżet | prób i minut z góry | brak; fuzje L+D zbudowane w całości, wynik +0,6% |
| dziennik prób | T01, T02… z wynikiem | KOLEJKA „Odrzucone” ręcznie, bez prognozy |
| prognoza | „co zmieni decyzję” | agenci: „+3–7%”, zmierzone +0,6%; dało się przewidzieć +0,8% z czasu ściany ([[ashhart-skills-infra]]) |
| wielu agentów | do 4, sami piszą, że bez dowodu | 2 zawodników; nie liczymy, który lepiej przewiduje |

## Co bierzemy
1. Karta próby przed budową: prognoza liczbowa z zakresem, próg „zabij”, budżet; po pomiarze błąd prognozy w dzienniku wyścigu.
2. Rezerwa na walidację: zwycięzca każdej rundy mierzony drugi raz w nowym procesie.
3. Z ich negatywnego wyniku: więcej agentów nie jest dowodem lepszej decyzji — liczyć trafność prognoz każdego zawodnika, zanim dodamy trzeciego.

## Powiązane
- [[ashhart-skills-infra]]
- [[ga-racing-rohanarun]]
- [[wyniki-negatywne]]
- [[lekcja-uczymy-sie-nie-tylko-predkosc]]
