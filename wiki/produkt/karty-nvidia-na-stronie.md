---
typ: produkt
tags: [produkt, app, landing, nvidia]
aktualizacja: 2026-11-14
zrodlo: app/landing/src/lib/data/measurements.ts (RTX_5090 … RTX_3070, R67); product/research/67-nvidia-vast-kampania.md:13-23,46,68,114
status: aktualne
---
# Karty NVIDIA z kampanii 67 na stronie

**Każda karta z kampanii 67 ma własną stronę w katalogu kart, zbudowaną tak samo jak RTX 3090: 5090, 4090, 5080, 4070, 2080 Ti, 3080 i 3070 doszły jako zmierzone, a 3060 dostała nowe dane (Bonsai 2 + MTP, LFM2.5). Osobna strona z tabelą 11 kart została wycofana (decyzja właściciela 14.11).**

Dane leżą w `measurements.ts` jako `CardView` (jak RTX 4060 Ti): trzy ustawienia na tym samym skrypcie (`spec_sweep`, 6 promptów, 1 seed), typowa aplikacja → najlepsze flagi albo fork Prism → nasz silnik, każda liczba z `67-nvidia-vast-kampania.md:<linia>`. Karta z jednym zmierzonym ustawieniem (3080, 3070, LFM na 4070 i 3060) nie ma przelicznika: `duel()` zwraca `null`, gdy `before === ours`, a strona pisze „naszego silnika z tym modelem jeszcze nie mierzyliśmy”. Etykiety kolumn innych niż w arkuszu dają `Run.labels`.

**Underdog Saluki usunięty ze strony całkowicie** (CC BY-NC 4.0, tylko niekomercyjnie; decyzja właściciela 14.11): 3060 pokazuje Bonsai 2, panele jakości KLD tylko Bonsai, a z `cards.json`, `cards.ts`, typów, stylów i tokenów zniknął klucz `saluki` (0 wystąpień w publicznym buildzie, także w JS). Licencje Bonsai 2 i Qwen3.5-9B sprawdzone na Hugging Face 14.11 (Apache-2.0).

Dwie pułapki: zduplikowany klucz w `{#each}` (np. dwa takie same chipy warunków albo `[before, ours]` z tym samym kluczem) wywala hydrację i strona po załadowaniu ucina się do stopki; zrzut ekranu pokazuje to od razu, `svelte-check` nie. Kciuk w `Segmented` przy więcej niż 2 rzędach musi znać liczbę rzędów (`--rows`), inaczej na telefonie zasłania kartę pod spodem.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[raport-67-kampania-nvidia]]
- [[strona-zrodlo-rowna-zywej]]
