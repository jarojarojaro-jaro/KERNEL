---
typ: produkt
tags: [produkt, app, landing]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/app/REPORT.md:11-13,16-17,22-46,70,77-78; ~/KERNEL/app/design/DESIGN.md:119
status: aktualne
---
# Strona (landing) PL/EN

**Statyczna strona w SvelteKit 2.70 + Svelte 5 (adapter-static), 47 stron PL i EN: hero z animacją „pojedynek prędkości” 38,8 → 109,0 t/s, metodologia z surowymi liczbami, dokumenty prawne i baner cookies.**

Dokumenty: [REPORT.md](../../app/REPORT.md), [DESIGN.md](../../app/design/DESIGN.md), [APP-ARCHITECTURE.md](../../app/design/APP-ARCHITECTURE.md).

- Strona główna: hero, liczby z labu, 3 kroki z warstwami L0–L3, tabela wyników ze źródłami, karty NVIDIA z chmury, „bit w bit”, sprzęt, prywatność, cennik (hipoteza) z listą oczekujących typu fake-door, FAQ.
- Hero odtwarza ten sam tekst w zmierzonym tempie (38,8 upstream bez spekulacji vs 109,0 nasz silnik z MTP, Qwen3.8-27B na RX 7900 XTX); podpis mówi, że liczby są z różnych skryptów i że spekulacja może zmienić tekst.
- `/methodology/`: surowe liczby z plikiem i linią, md5, wyjątki KLD, surowy scorecard 3090, wzory estymatora, lista niezmierzonych rzeczy.
- `/legal/{terms,privacy,cookies,ai,imprint}/`: projekty z banerem „do weryfikacji przez prawnika”, dane spółki puste. Baner cookies: „Odrzucam” i „Akceptuję” równej wagi, nic nie ładuje się przed zgodą.
- Weryfikacja: `svelte-check` 0 błędów (249 plików), 50 ścieżek → 200, axe-core 4.14 0 naruszeń (1280 i 390 px, oba motywy), Lighthouse mobile wydajność 96–98, pozostałe 100.
- Wybór SvelteKit zamiast Astro: ten sam stos co web UI llama.cpp i przyszła aplikacja Tauri.

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-system-projektowy]]
- [[app-onboarding-prototyp]]
- [[produkt-landing-i-onboarding]]
- [[2026-10-16-landing-i-konto]]
