---
typ: produkt
tags: [produkt, app, desktop, tui]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:18-20,85-89; ~/KERNEL/app/design/APP-ARCHITECTURE.md:107-133,429-437,557-571
status: aktualne
---
# Prototyp aplikacji desktop, makieta TUI i architektura

**Osiem ekranów prototypu aplikacji (`/[lang]/app/…`, kod w `landing/src/lib/desktop`), makieta TUI w stylu REACTOR (`tui/tui_demo.py`, 5 scen) i dokument architektury: daemon, lokalne API, onboarding, łączenie konta, dane lokalne vs wysyłane.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

- Ekrany: przegląd, kreator, Mój komputer, Wynik (L0–L3, miejsce na przedział ufności, md5/KLD, raport JSON), Optymalizacja nocna, Modele, Dla programistów, Czat. Strony `/app/*` mają celowe `noindex`.
- TUI: czysty Python, tryby `--plain`, `--snapshot`, `--html`.
- Lokalne API (propozycja): `http://127.0.0.1:11500`, tylko loopback, token 256-bitowy w pliku `0600`, kontrola nagłówka `Host` (ochrona przed DNS rebinding), domyślnie bez CORS; nasze API kontrolne pod `/x/v1/…`, długie operacje jako joby.
- Trzy przełączniki zgody na wysyłkę danych, wszystkie domyślnie wyłączone; protokół uczciwego pomiaru w UI.
- Otwarte ryzyka z dokumentu (13 punktów), m.in. `llama-server` vs własny host na `libllama`, przenośność md5 kanarków, watermark AI Act, Tauri na Linuksie.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-system-projektowy]]
- [[otwarte-decyzje-produktu]]
- [[produkt-architektura]]
- [[reactor-monitor]]
