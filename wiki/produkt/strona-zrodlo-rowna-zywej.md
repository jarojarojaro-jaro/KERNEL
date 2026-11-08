---
typ: produkt
tags: [produkt, landing, wdrozenie]
aktualizacja: 2026-11-08
zrodlo: app/landing/build; repo enigmalabz.com (tag zywo-2026-11-07); missions/M-261108-nvidia-strona/web-krok0b/out/rownosc.md
status: aktualne
---
# Strona: źródło = żywa (krok 0 przed zmianami treści)

**Build z `app/landing` daje stronę równą żywej enigmalabz.com: 86/86 stron z identycznym `<head>`, 86/86 z identycznym widocznym tekstem, 88/88 HTML bez realnej różnicy treści, zero wycieków ze `.strona.json` (2026-11-08).**

Ręczne dodatki z 23–24.10 są teraz w źródle, nie tylko na serwerze: `poprawki.css` i `poprawki.js` (ładowane z `?v=`, bump po każdej zmianie pliku), skrypt zgody + `/ruch.js`, favicony, `og-pl.jpg`/`og-en.jpg`, `robots.txt`, `llms.txt`, trasa `/404` prerenderowana do `404.html`, `.htaccess` w `scripts/deploy-ftp.py`.

Kluczowe: `deploy-ftp.py` zmienia nazwę `_app/immutable` na `_app/i<N>` i przepisuje 88 HTML, bo `.htaccess` cache'uje `^/_app/i\d+/` na rok; `N` z `scripts/.generation` (start 4, żywa ma i2/i3). `copy_404()` dodatkowo zamienia w `404.html` odwołania `../` na `/` (`absolutize()`), bo `ErrorDocument 404 /404.html` serwuje ten plik pod dowolnym brakującym adresem — ze ścieżką względną przeglądarka żądała `/<żądany-katalog>/_app/iN/...` i wszystkie zasoby wracały 404 (zmierzone: 26/27, pusty ekran). Po poprawce 53/53 zasobów < 400 pod `/pl/karty/rx-7900-xtx/nie-ma/`. Poprawki w źródle przy okazji tej roboty: `href()` w `i18n.ts` doklejał `/` po query stringu (`/en/cards/compare/?a=x&b=y/` zamiast `...b=y`), a `<link>` ikon trafił w to samo miejsce `<head>`, co na żywej.

Build: `PUBLIC_SITE_PUBLIC=1 PUBLIC_SITE_ORIGIN=https://enigmalabz.com bun x vite build` — nie `bun run build`, bo `sync-results` w klonie bez `scorecard.json` wyciera liczby z `cards.json`.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[aplikacja-w-budowie]]
- [[lekcja-zmiana-draftu-zmienia-md5]]
