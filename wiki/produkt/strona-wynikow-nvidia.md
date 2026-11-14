---
typ: produkt
tags: [produkt, app, landing, nvidia, seo]
aktualizacja: 2026-11-14
zrodlo: app/landing/src/lib/nvidia/NvidiaPage.svelte; app/landing/src/lib/data/nvidia-cards.ts; app/landing/vite.config.ts; product/SITE-NVIDIA.md:17-88; missions/M-261108-nvidia-strona/web-tresc/out/strony.md
status: aktualne
---
# Strona wyników NVIDIA `/pl/nvidia/` i `/en/nvidia/`

**Nowa trasa w istniejącym landingu SvelteKit: jedna tabela 11 kart NVIDIA po trzy prędkości, sekcja MoE, modele z licencjami, gotowe ustawienia, metoda, zastrzeżenia §6 i odnośnik do wydania silników CUDA. 8 833 znaków tekstu PL, 8 779 EN.**

Trasa `src/routes/[lang=lang]/(site)/nvidia/+page.svelte` to 6-liniowy wrapper wokół `$lib/nvidia/NvidiaPage.svelte` (803 linie), więc dziedziczy layout, `Seo.svelte`, i18n i tokeny designu. Liczby leżą w `src/lib/data/nvidia-cards.ts` z komentarzem `src: 'product/SITE-NVIDIA.md:<linia>'` przy każdym wierszu, a słowa w `src/lib/nvidia/copy.ts` — dzięki temu `num()` formatuje je per locale (148,6 vs 148.6), a skrypt `sprawdz-liczby.py` potwierdza każdą wartość w cytowanej linii materiału (11/11 kart, 0 rozbieżności).

Pomiar po oddaniu: 40 żądań / 506 kB (istniejące `/pl/karty/nvidia/` ma 50 / 627 kB), zero poziomego przewijania dokumentu i **wszystkich trzech tabel** na 14 szerokościach 320–1440 px, axe 0 naruszeń PL i EN, 51/51 elementów osiągalnych Tabem, INP 72 ms na 4× wolniejszym procesorze. Test `slow3g` (50 kB/s, treść < 8 s) nie przechodzi — ale identycznie nie przechodzi na istniejącej stronie producenta (12,4 s vs 9,9 s), bo same fonty to 129 kB.

Trzy pułapki warte zapamiętania: `bun run build` w tym workspace uruchamia `sync-results` i wycina liczby z `cards.json` (budować przez `web-krok0b/build.py`); `span.sr-only` w komórce tabeli bez pozycjonowanego przodka kotwiczy się do initial containing block i rozpycha dokument o 89 px na mobile; a tabela sześciokolumnowa potrzebuje 1026 px treści, więc między 768 a ~1100 px trzeba jej zwijać `Model` i `Kontekst` do drugiej linii (`.mini`) — inaczej ostatnia kolumna „z silnikiem” wychodzi poza `.table-wrap`. Przy `table-layout: fixed` resztkowy nadmiar dają `min-content` komórek: `thead th { white-space: normal }` plus `overflow-wrap: anywhere` na badge’ach licencji, ścieżkach HF i zmiennych środowiska.

Czwarta pułapka, kosztowna: plugin `stripSources` w `app/landing/vite.config.ts` w buildzie publicznym kasuje **każdy** literał pasujący do `/KERNEL\//`, a adres wydania na GitHubie zawiera `KERNEL/releases/tag` — więc `ENGINE_RELEASE.url` trafiał do HTML jako `""` (pusty `href` przeładowuje bieżącą stronę). Dane w `nvidia-cards.ts` były poprawne, winny był filtr. Wyjątek `PUBLIC_GH_URL = /^https:\/\/github\.com\/\S+$/` (cały adres do publicznego repo, nie ścieżka) naprawia to bez osłabiania `leaks.py`. Wniosek na przyszłość: każdy nowy adres do publicznego repo trzeba sprawdzić w prerenderowanym HTML, nie tylko w źródle — `grep -c 'href=""'` na `build/`.

**2026-11-14, przed publikacją (operator, decyzja właściciela: stronę kończy Claude Code):** gałąź scalona z `main` (poprawka Skanu z 11.11), build tylko `bun x vite build` (bez `sync-results`, który tu przepisuje `cloud-results.json`). Zmiany: nagłówek z oboma porównaniami (do 2,4× wobec zwykłego llama.cpp, +47% wobec llama.cpp z MTP; reguła właściciela 7.11), pasek liczb bez ucinania przy 1440 px (`min-width: 0` i `minmax(0, 1fr)` w elementach siatki), ×2,6 na RTX 3060 z nazwami obu modeli (Saluki → Bonsai 2 + MTP), odstęp przy etykietach w tabeli, baner `NvidiaBanner.svelte` także na stronie Wyniki, licencje sprawdzone na HF 14.11 (bez zmian), opisy ≤ 160 znaków. Kontrola: 88 żywych stron bez zmian w treści i w `<head>` poza dwoma banerami, Lighthouse mobile 76 (istniejąca `/pl/karty/nvidia/` 71), desktop 98, dostępność 100, axe 0, blokady wycieków czyste. Generacja zasobów `_app/i5` (i2–i4 zostają).

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[nvidia-wyniki-2026-10-16]]
- [[strona-zrodlo-rowna-zywej]]
- [[2026-10-20-uncensored-poza-strona]]
