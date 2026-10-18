---
typ: narzedzie
tags: [narzedzia, landing, qa]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/app/landing/scripts/qa/README.md:1-12; ~/KERNEL/app/REPORT.md:238-260; ~/KERNEL/app/design/REDESIGN.md:154-169
status: aktualne
---
# QA landingu: `app/landing/scripts/qa/`

**Cztery skrypty puppeteer-core po CDP (Chrome bez GPU, `.tools/chrome-swgl`, port 18499): hydracja, hero pod obciążeniem, axe i zrzuty ekranu.**

| skrypt | co sprawdza |
|---|---|
| `hyd.ts <urls>` | ostrzeżenia hydracji i konsoli per strona (`BASE`, `ONE=1`; na dev serwerze też złe zagnieżdżenie HTML) |
| `heroqa.ts` | 10 świeżych ładowań × 4 viewporty: normalnie, CPU 4×/6×, wolna sieć, bez JS; hero kompletne 1.5 s po nawigacji; arkusz w `screens/v2/hero-qa/` |
| `axe.ts <urls>` | axe-core WCAG 2.x A/AA + best practice, błędy konsoli, poziomy scroll, 1280 i 390 |
| `shots.ts` | każda sekcja i podstrona PL, 1440 + 390, do `OUT` |

Instalacja: w katalogu roboczym `bun add puppeteer-core@24` i skopiować skrypty. Wynik dla buildu rundy 8 (2026-10-18): 0 ostrzeżeń hydracji na 14 stronach, hero 40/40, axe 0 naruszeń na 20 stronach × 2 szerokości.

## Powiązane
- [[narzedzia/_hub|Narzędzia]]
- [[ss-zrzut-ekranu]]
- [[app-landing]]
- [[lekcja-hydration-blok-w-p]]
