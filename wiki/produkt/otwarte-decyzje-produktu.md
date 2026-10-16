---
typ: produkt
tags: [produkt, decyzje-otwarte, app]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:92-109; ~/KERNEL/product/PLAN.md:491-499
status: aktualne
---
# Otwarte decyzje produktu (po prototypie aplikacji)

**Pytania AppStudio do użytkownika z 2026-10-16, wciąż bez decyzji: nazwa, kolor akcentu, ceny w teście fake-door, konto przed pobraniem, sprawy prawne, port lokalnego API 11500 i domena.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

| temat | stan w prototypie | do decyzji |
|---|---|---|
| nazwa | `BRAND.name = "Podkręt"` | Podkręt, Nocna Zmiana / NightShift, Turbina, Rozpęd, Tuned; sprawdzić EUIPO i domeny, potem wordmark SVG |
| kolor | volt jedynym akcentem, motyw wg systemu | alternatywa: ion główny, volt tylko „po”; ciemny domyślnie czy wg systemu |
| ceny fake-door | PL 149 zł/rok, 299 zł dożywotnio, 19 zł/mies.; EN 39 €/rok, 79 € dożywotnio | pokazywać przy zapisie czy po |
| konto | przed pobraniem (PLAN §8.1.1) | czy pobieranie bez konta; kandydat do testu A/B |
| prawo | projekty dokumentów | kancelaria/KRiBSI ws. art. 50(2) AI Act, retencja danych, IOD, zakresy OAuth, platforma ODR, kiedy spółka |
| port API | 11500 (`BRAND.apiPort`) | zatwierdzić |
| domena | brak; `SITE_ORIGIN` → build wskazuje `127.0.0.1:18433` | wybrać (ustawia `hreflang` i `canonical`) |

Decyzje już podjęte są w folderze decyzji (np. open core, czat na web UI llama.cpp, konto na początku jako pomysł użytkownika).

## Powiązane
- [[produkt/_hub|produkt]]
- [[aplikacja-w-budowie]]
- [[produkt-biznes-edycje]]
- [[2026-10-16-landing-i-konto]]
- [[2026-10-15-open-core]]
