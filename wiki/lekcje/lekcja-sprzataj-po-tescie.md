---
typ: lekcja
tags: [lekcje, dysk, jaroserverai, testy]
aktualizacja: 2026-11-27
zrodlo: panel JARO 2026-11-27 13:54 („czemu je przepisywałeś skoro to te same… czemu nie usunąłeś po testach… na chuj bym chciał mieć plik, który jest do niczego”)
status: aktualne
---
# Lekcja: pliki zrobione tylko na test kasuję zaraz po teście, a przegrane warianty po werdykcie

**Na teście K-193 podagent przepisał nasze AD-Q4_K i UD-Q4_K_XL do nowego formatu GGUF (`~/models/inkling/mainline`, 32 GB), żeby nowa llama.cpp mogła je czytać obok IQ3_S; po teście zostały na dysku. Przegrany wariant WE2 (`unc-nearest.patch.gguf`, 5,9 GB) leżał od 26.11. Zamiast usunąć, pytałem JARO o zgodę.**

- Przyczyna: w zadaniu dla podagenta nie było „po teście usuń, co stworzyłeś”, a ja w raporcie tylko proponowałem usunięcie, zamiast zrobić to jako część testu.
- Dlaczego przepisanie w ogóle: nowa llama.cpp (b12803) nie czyta starego układu (`blk.24.attn_q.weight not found`), a porównanie IQ3_S z naszym plikiem na tym samym silniku tego wymagało. Te same wagi, nowy nagłówek; tańsze byłoby jednorazowe przepisanie do `/tmp`/osobnego katalogu z kasowaniem w ostatnim jobie.
- Reguła: każdy jobs file, który tworzy pliki tylko na test (konwersje, kopie modeli, sidecary, przegrane warianty), kończy się jobem sprzątającym przed `restore8080`; po werdykcie „przegrany” plik usuwam w tej samej turze. Raport podaje, co usunięto (GB), a pyta tylko o rzeczy, które mogą się jeszcze przydać produkcji.
- Do zrobienia przy najbliższym włączeniu jaroserverai: `rm -rf ~/models/inkling/mainline ~/models/nib/we2/unc-nearest.patch.gguf` (zlecone przez JARO 2026-11-27).

## Powiązane
- [[2026-11-26-we2-nib-scalona-ablacja]]
