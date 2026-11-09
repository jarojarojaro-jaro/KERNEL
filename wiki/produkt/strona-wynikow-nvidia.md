---
typ: produkt
tags: [produkt, app, landing, nvidia, seo]
aktualizacja: 2026-11-09
zrodlo: app/landing/src/lib/nvidia/NvidiaPage.svelte; app/landing/src/lib/data/nvidia-cards.ts; product/SITE-NVIDIA.md:17-88; missions/M-261108-nvidia-strona/web-tresc/out/strony.md
status: aktualne
---
# Strona wyników NVIDIA `/pl/nvidia/` i `/en/nvidia/`

**Nowa trasa w istniejącym landingu SvelteKit: jedna tabela 11 kart NVIDIA po trzy prędkości, sekcja MoE, modele z licencjami, gotowe ustawienia, metoda, zastrzeżenia §6 i odnośnik do wydania silników CUDA. 8 833 znaków tekstu PL, 8 779 EN.**

Trasa `src/routes/[lang=lang]/(site)/nvidia/+page.svelte` to 6-liniowy wrapper wokół `$lib/nvidia/NvidiaPage.svelte` (803 linie), więc dziedziczy layout, `Seo.svelte`, i18n i tokeny designu. Liczby leżą w `src/lib/data/nvidia-cards.ts` z komentarzem `src: 'product/SITE-NVIDIA.md:<linia>'` przy każdym wierszu, a słowa w `src/lib/nvidia/copy.ts` — dzięki temu `num()` formatuje je per locale (148,6 vs 148.6), a skrypt `sprawdz-liczby.py` potwierdza każdą wartość w cytowanej linii materiału (11/11 kart, 0 rozbieżności).

Pomiar po oddaniu: 40 żądań / 506 kB (istniejące `/pl/karty/nvidia/` ma 50 / 627 kB), zero poziomego przewijania na 375/768/1440 px, axe 0 naruszeń PL i EN, 51/51 elementów osiągalnych Tabem, INP 72 ms na 4× wolniejszym procesorze. Test `slow3g` (50 kB/s, treść < 8 s) nie przechodzi — ale identycznie nie przechodzi na istniejącej stronie producenta (12,4 s vs 9,9 s), bo same fonty to 129 kB.

Dwie pułapki warte zapamiętania: `bun run build` w tym workspace uruchamia `sync-results` i wycina liczby z `cards.json` (budować przez `web-krok0b/build.py`), a `span.sr-only` w komórce tabeli bez pozycjonowanego przodka kotwiczy się do initial containing block i rozpycha dokument o 89 px na mobile.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[nvidia-wyniki-2026-10-16]]
- [[strona-zrodlo-rowna-zywej]]
- [[2026-10-20-uncensored-poza-strona]]
