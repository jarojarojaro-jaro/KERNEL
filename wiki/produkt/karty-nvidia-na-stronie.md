---
typ: produkt
tags: [produkt, app, landing, nvidia]
aktualizacja: 2026-11-14
zrodlo: app/landing/src/lib/data/measurements.ts (RTX_5090 … RTX_3070, RTX_3090, RTX_5060TI, RTX_4060TI, R67); product/research/67-nvidia-vast-kampania.md:13-23,46,50,68-71,85,97,114
status: aktualne
---
# Karty NVIDIA z kampanii 67 na stronie

**Każda karta z kampanii 67 ma własną stronę w katalogu kart, zbudowaną tak samo jak RTX 3090: 5090, 4090, 5080, 4070, 2080 Ti, 3080 i 3070 doszły jako zmierzone, a 3060 dostała nowe dane (Bonsai 2 + MTP, LFM2.5). Osobna strona z tabelą 11 kart została wycofana (decyzja właściciela 14.11).**

Dane leżą w `measurements.ts` jako `CardView` (jak RTX 4060 Ti): trzy ustawienia na tym samym skrypcie (`spec_sweep`, 6 promptów, 1 seed), typowa aplikacja → najlepsze flagi albo fork Prism → nasz silnik, każda liczba z `67-nvidia-vast-kampania.md:<linia>`. Karta z jednym zmierzonym ustawieniem (3080, 3070, LFM na 4070 i 3060) nie ma przelicznika: `duel()` zwraca `null`, gdy `before === ours`, a strona pisze „naszego silnika z tym modelem jeszcze nie mierzyliśmy”. Etykiety kolumn innych niż w arkuszu dają `Run.labels`.

**Underdog Saluki usunięty ze strony całkowicie** (CC BY-NC 4.0, tylko niekomercyjnie; decyzja właściciela 14.11): 3060 pokazuje Bonsai 2, panele jakości KLD tylko Bonsai, a z `cards.json`, `cards.ts`, typów, stylów i tokenów zniknął klucz `saluki` (0 wystąpień w publicznym buildzie, także w JS). Licencje Bonsai 2 i Qwen3.5-9B sprawdzone na Hugging Face 14.11 (Apache-2.0).

**Od 14.11 wieczorem najnowsze dane wygrywają (decyzja właściciela):** RTX 3090, 5060 Ti 16 GB i 4060 Ti 16 GB też pokazują listopad (raport 67), w tym samym układzie (`card67`, `r67`, `x`):

| Karta | typowa aplikacja → najlepsze flagi / lepszy plik → nasz silnik | warunki |
|---|---|---|
| 3090 (340 W) | 40,93 → 61,49 (MTP n=3, 245 760) → 79,97 t/s (fork + kvq + lean, 262 144) | ×1,95; UD-Q4_K_M 78,97 w notatce |
| 5060 Ti (160 W) | 27,48 → 31,42 (ISTA bez MTP) → 43,40 t/s (lean + MTP n=2, 229 376) | ×1,58; fork 196 608: 49,44 w notatce |
| 4060 Ti (165 W) | 19,78 → 24,02 (ISTA bez MTP) → 36,30 t/s (lean + MTP n=2, 229 376) | ×1,84 |

LFM2.5 na 5060 Ti to listopadowe pojedyncze ustawienie (Q4_K_M w VRAM, 139,48 t/s; październikowy pomiar naszego silnika 207,86 w notatce), więc para 5060 Ti × LFM2.5 wypadła z wyścigu na stronie głównej (`PAIR_IDS`). LFM2.5 i Nemotron na 3090 oraz LFM2.5 na 4060 Ti zostały z października (raport 67 ich nie mierzył), z warunkiem „inny host (październik, …)” i notatką; czyta je `sheetRuns()` z `cards.json`. Bohater strony głównej (3090 × Qwen) liczy kolumny z `before/flags/ours` biegu; opis JSON-LD ma liczby 3090 z karty.

**Lżejsze strony kart na telefonach (14.11):** Lighthouse mobile dławiło ciągłe przerysowywanie hero (zmienna CSS na korzeniu sekcji przeliczała style ~220 elementów co klatkę, rasteryzacja zabierała CPU głównemu wątkowi). Teraz: wartości zmieniane co klatkę siedzą na liściach, warstwy (`will-change`) tylko podczas animacji (`moving`), pętle kończą się po odegraniu, przy `prefers-reduced-motion` i na dotyku liczniki od razu pokazują wynik, rysunki innych kart renderują się dopiero blisko ekranu (akcja `near`, HTML 3090: 404 → 250 KB), na telefonach `content-visibility: auto` na blokach modeli, rozmiar elementu przy `tilt`/`magnetic` czytany raz na najechanie. Reguły w `app/landing/PERF.md`.

| strona | mobile przed → po (http.server bez kompresji) | mobile przed → po (gzip, jak produkcja) | TBT po | desktop po | CLS / a11y |
|---|---|---|---|---|---|
| `/pl/karty/rtx-3090/` | 34 → 52–64 | 80 → 82 | 100–500 ms | 94–99 | 0 / 100 |
| `/pl/karty/rtx-5090/` | 34 → 65–66 | 55 → 85 | 84–129 ms | 95–98 | 0 / 100 |

Na serwerze bez kompresji wynik trzyma FCP ~5 s (≈ 250 KB HTML z wklejonym CSS, ~370 KB JS w modulepreload, 136 KB fontów); produkcja podaje brotli. Pomiary na 3-rdzeniowym serwerze z `nice 15` mają duży rozrzut (TBT 100–500 ms dla tego samego buildu), więc audyty puszczać w ciszy.

Dwie pułapki: zduplikowany klucz w `{#each}` (np. dwa takie same chipy warunków albo `[before, ours]` z tym samym kluczem) wywala hydrację i strona po załadowaniu ucina się do stopki; zrzut ekranu pokazuje to od razu, `svelte-check` nie. Kciuk w `Segmented` przy więcej niż 2 rzędach musi znać liczbę rzędów (`--rows`), inaczej na telefonie zasłania kartę pod spodem.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[raport-67-kampania-nvidia]]
- [[strona-zrodlo-rowna-zywej]]
