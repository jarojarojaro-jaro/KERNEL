---
typ: lekcja
tags: [lekcje, research, infra, produkt]
aktualizacja: 2026-11-24
zrodlo: panel JARO 2026-11-24 03:37 (o Inference Stack: „czemu wszystko wziąłeś teraz pod optymalizację… mieliśmy się uczyć… próbowaliśmy zrobić własny i nam poszło gorzej… musisz łączyć takie kropki”)
status: aktualne
---
# Lekcja: link o infrastrukturze oceniam także jako naukę i wzór dla naszych projektów, nie tylko „czy przyspieszy model”

**2026-11-24 ocenę Inference Stack (BerriAI/LiteLLM: vLLM + llm-d + LiteLLM + Grafana + Lens) zamknąłem zdaniem „dla prędkości na XTX zero”, choć to ten sam rodzaj produktu, który budujemy w Enigmie (instalator, wybór modelu, silnik, pomiar, lokalne API) i który nam wyszedł gorzej.**

- Przyczyna: przy triage patrzyłem tylko przez jeden filtr (dekod Inklinga na XTX), a cel to też nauka i trening, a każdy link ma odpowiedzieć „czego to uczy o naszej pracy” ([[decyzje/_hub]], cel 14.11).
- Reguła: przy każdym linku o infrastrukturze, serwowaniu lub produkcie najpierw szukam naszego odpowiednika (Enigma app, serwer topki, kolejka, harness agentów), studiuję źródło (kod, architektura, `plik:linia`) i zapisuję porównanie warstwa po warstwie z wnioskami; „zero dla prędkości” to najwyżej jedno zdanie, nie werdykt.
- Głębokość: tak jak dla kerneli — klon repo, mechanizm, co lepsze od nas, co bierzemy, gdzie nam nie wyszło i dlaczego.

## Powiązane
- [[lekcja-tylko-wynik-ze-zgadywaniem]]
- [[ZRODLA]]
