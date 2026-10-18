---
typ: produkt
tags: [produkt, decyzje-otwarte, app]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:92-109; ~/KERNEL/product/PLAN.md:491-499; ~/KERNEL/product/research/15c-nowe-silniki.md:395; ~/KERNEL/product/research/15d-prefill-dlugi-kontekst.md:122; ~/KERNEL/product/research/15e-kwantyzacja-nowa.md:146-149,547; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:334-343,340-342
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
| teza produktu (PLAN §0.1) | „żaden nie robi naraz…” | zawęzić wyróżnik po Magnitude ([[zawezenie-tezy-produktu]], raport 15c) |
| tryb stratny PFlash | brak | czy oferować opt-in „szybki odczyt długich dokumentów” ([[tryb-stratny-pflash]], raport 15d) |
| licencje z progiem przychodu | brak | czy dopuszczamy modele jak Swift 1.5 (komercyjnie tylko < US$1M przychodu, [[swift-1-5]], raport 15e) |
| tryb „identyczne odpowiedzi” | gałąź `batch-invariant` @ `365af3e5e`, przełącznik wyłączony = produkcja | wdrożyć z `LLAMA_SPEC_BITEXACT=1` jako opt-in? koszt 0% krótki kontekst, −9% przy ~27k ([[2026-10-16-bit-exact]], raport 12) |

Decyzje już podjęte są w folderze decyzji (np. open core, czat na web UI llama.cpp, konto na początku jako pomysł użytkownika).

## Powiązane
- [[produkt/_hub|produkt]]
- [[aplikacja-w-budowie]]
- [[produkt-biznes-edycje]]
- [[2026-10-16-landing-i-konto]]
- [[2026-10-15-open-core]]
