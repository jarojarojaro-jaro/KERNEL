---
typ: produkt
tags: [produkt, landing, wdrozenie]
aktualizacja: 2026-11-09
zrodlo: app/landing/build; repo enigmalabz.com main d3054d2 (tag wgranie-20261109-035541); missions/M-261108-nvidia-strona/web-krok0b/out/rownosc.md
status: aktualne
---
# Strona: źródło = żywa (krok 0 przed zmianami treści)

**Build z `app/landing` (gałąź `nvidia-2026-11`, przebazowana na KERNEL `main` = `8307d36`) daje stronę równą żywej enigmalabz.com z 2026-11-09 (`d3054d2`): 86/86 stron z identycznym `<head>`, 86/86 z identycznym widocznym tekstem, 88/88 HTML bez realnej różnicy treści, zero wycieków ze `.strona.json`.**

Przebazowanie r2 (2026-11-09) po decyzji właściciela: żywa przeszła rano na `d3054d2` (tytuły/opisy 87 stron, OG na `/app/`, `_app/i4`), a KERNEL `main` na `8307d36` (te same tytuły i opisy w źródle). Konflikt przy `rebase` był wyłącznie w polach meta: main ma `metaTitle`/`metaDescription` (tytuł ≠ widoczny nagłówek), gałąź misji dodawała `<Seo>` (OG, Twitter, JSON-LD). Rozwiązanie: **meta z maina, `Seo` z misji**, z tymi samymi wyrażeniami tytułu/opisu — dlatego `og:title` = `<title>`. Twarde spacje z żywej (`i terminala`, `kartę graficzną ·`) wróciły do źródła jako `\u00a0`, bo head-diff porównuje bajty.

Ekrany prototypu `/[lang]/app/` (16 HTML) mają teraz `<Seo>` tak jak żywa — wcześniej OG/Twitter były tylko na żywej.

Ręczne dodatki z 23–24.10 są w źródle, nie tylko na serwerze: `poprawki.css` i `poprawki.js` (ładowane z `?v=`, bump po każdej zmianie pliku), skrypt zgody + `/ruch.js`, favicony, `og-pl.jpg`/`og-en.jpg`, `robots.txt`, `llms.txt`, trasa `/404` prerenderowana do `404.html`, `.htaccess` w `scripts/deploy-ftp.py`.

Kluczowe: `deploy-ftp.py` zmienia nazwę `_app/immutable` na `_app/i<N>` i przepisuje 88 HTML, bo `.htaccess` cache'uje `^/_app/i\d+/` na rok; `N` z `scripts/.generation` (start 4 — ta sama generacja co na żywej). `copy_404()` dodatkowo zamienia w `404.html` odwołania `../` na `/` (`absolutize()`), bo `ErrorDocument 404 /404.html` serwuje ten plik pod dowolnym brakującym adresem — ze ścieżką względną przeglądarka żądała `/<żądany-katalog>/_app/iN/...` i wszystkie zasoby wracały 404 (zmierzone: 26/27, pusty ekran). Po poprawce 0 wystąpień `../` w `404.html` i 53/53 zasobów < 400 pod `/pl/karty/rx-7900-xtx/nie-ma/`. Poprawki w źródle przy okazji tej roboty: `href()` w `i18n.ts` doklejał `/` po query stringu (`/en/cards/compare/?a=x&b=y/` zamiast `...b=y`), a `<link>` ikon trafił w to samo miejsce `<head>`, co na żywej.

**Nazwy chunków `_app/i4` różnią się od żywej** — źródło ma dodatkowe moduły tej misji (`Seo.svelte`, `jsonld.ts`, trasa `404`), a Vite liczy nazwy z grafu modułów. To jedyne odstępstwo poza `version.json`; treść stron jest równa (trzy niezależne kontrole).

Build: `PUBLIC_SITE_PUBLIC=1 PUBLIC_SITE_ORIGIN=https://enigmalabz.com bun x vite build` — nie `bun run build`, bo `sync-results` w klonie bez `scorecard.json` wyciera liczby z `cards.json`.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[aplikacja-w-budowie]]
- [[lekcja-build-landing-nie-czyta-home]]
- [[lekcja-zmiana-draftu-zmienia-md5]]
