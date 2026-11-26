---
typ: lekcja
tags: [lekcje, research, infra, produkt]
aktualizacja: 2026-11-26
zrodlo: panel JARO 2026-11-24 03:37 (o Inference Stack: „czemu wszystko wziąłeś teraz pod optymalizację… mieliśmy się uczyć… próbowaliśmy zrobić własny i nam poszło gorzej… musisz łączyć takie kropki”)
status: aktualne
---
# Lekcja: link o infrastrukturze oceniam także jako naukę i wzór dla naszych projektów, nie tylko „czy przyspieszy model”

**2026-11-24 ocenę Inference Stack (BerriAI/LiteLLM: vLLM + llm-d + LiteLLM + Grafana + Lens) zamknąłem zdaniem „dla prędkości na XTX zero”, choć to ten sam rodzaj produktu, który budujemy w Enigmie (instalator, wybór modelu, silnik, pomiar, lokalne API) i który nam wyszedł gorzej.**

- Przyczyna: przy triage patrzyłem tylko przez jeden filtr (dekod Inklinga na XTX), a cel to też nauka i trening, a każdy link ma odpowiedzieć „czego to uczy o naszej pracy” ([[decyzje/_hub]], cel 14.11).
- Reguła: przy każdym linku o infrastrukturze, serwowaniu lub produkcie najpierw szukam naszego odpowiednika (Enigma app, serwer topki, kolejka, harness agentów), studiuję źródło (kod, architektura, `plik:linia`) i zapisuję porównanie warstwa po warstwie z wnioskami; „zero dla prędkości” to najwyżej jedno zdanie, nie werdykt.
- Głębokość: tak jak dla kerneli — klon repo, mechanizm, co lepsze od nas, co bierzemy, gdzie nam nie wyszło i dlaczego.

## Powtórka 2026-11-26 (JARO: „powinieneś już dawno wiedzieć i nie robić takich błędów”)
- Ten sam błąd po dwóch dniach: przy 8 linkach napisałem „nic z tego nie przyspiesza naszych modeli” i dałem werdykty „nie dla nas”, choć lekcja już istniała.
- Przyczyna: lekcja była tylko tekstem, nic jej nie wymuszało; szablon zadań dla zwiadowców pytał „relevant / lesson only / hype”, co ustawia ocenę na „przyda się dziś czy nie”.
- Poprawka mechaniczna: `wiki/tools/wiki.py lint` zgłasza błąd dla każdej notatki `research/` od 2026-11-26 bez sekcji `## Na później` (przy jakim modelu, karcie, skali się przyda i co wtedy sprawdzić); bez 0 błędów nie ma commita. W zadaniach dla zwiadowców kategorie: „dla nas teraz / na później (kiedy) / bzdura”.
- Decyzja: [[2026-11-26-wiedza-na-pozniej]].

## Powiązane
- [[lekcja-tylko-wynik-ze-zgadywaniem]]
- [[ZRODLA]]
