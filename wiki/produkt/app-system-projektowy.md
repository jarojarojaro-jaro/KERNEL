---
typ: produkt
tags: [produkt, app, design]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/design/DESIGN.md:5-60,104-120,143-156; ~/KERNEL/app/REPORT.md:9-10,71-76
status: aktualne
---
# System projektowy „telemetria w nocy” i znak Tacho

**Tokeny (kolor, typografia, przestrzeń, ruch), motyw ciemny i jasny, komponenty i znak „Tacho”: grafitowe tło `#07080D` i jeden kolor sygnałowy volt `#C8FF3D`, który znaczy „po” i „nasze”.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

- Kolory znaczeniowe: ion `#3DD6FF` (informacja, fokus, prototyp), amber `#FFB23E` (szacunek), heat `#FF4D8D` (błąd), ok `#5BE49B`; na jasnym tle akcent `#3B6E00`. Kontrast policzony dla obu motywów (tekst ≥ 4,5:1, kontrolki ≥ 3:1); kolor nigdy nie jest jedynym nośnikiem informacji.
- Fonty Geist i Geist Mono hostowane lokalnie (bez zapytań do Google Fonts, RODO); liczby w mono z cyframi tabelarycznymi.
- Znak „Tacho”: łuk tarczy 270° ze wskazówką w czerwonym polu, siatka 32×32, nie zależy od nazwy produktu (`design/logo/*.svg`).
- Ruch niesie dane: `--dur-1`…`--dur-4` = 110/180/320/640 ms; `prefers-reduced-motion` zatrzymuje animacje, każdy ruch dłuższy niż 5 s ma pauzę.
- Wzorce uczciwości: plakietki ZMIERZONE / SZACUNEK / WKRÓTCE / POMIAR W TOKU / PROTOTYP i przypis źródła przy każdej liczbie.
- Motyw czatu llama.cpp: `design/llama-ui-theme.css` mapuje tokeny na zmienne shadcn w `tools/ui`.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-landing]]
- [[aplikacja-w-budowie]]
- [[reactor-monitor]]
- [[2026-10-15-czat-na-web-ui-llama]]
