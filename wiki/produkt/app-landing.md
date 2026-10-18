---
typ: produkt
tags: [produkt, app, landing]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/app/REPORT.md:11-13,16-17,22-46,70,77-78; ~/KERNEL/app/design/DESIGN.md:119; ~/KERNEL/app/REPORT.md:238-260; ~/KERNEL/app/design/REDESIGN.md:154-169; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8/LandingWow.jsonl:1224
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

**Rundy 6–8 (2026-10-16/18, commit `511fcf2`):** naprawiony `hydration_mismatch` ([[lekcja-hydration-blok-w-p]]); hero tylko z `transform` (QA 40/40); wartości końcowe liczników w HTML z SSR, odczyty na żywo nie przekraczają zmierzonej mediany; onboarding zaczyna się nagłówkiem, ciemny motyw domyślnie. Juror (WOW/oryginalność/szlif): r6 7/7/6, r7 7/7/6, r8 7/6/7 – cel 8/8/8 nieosiągnięty. Kontrole r8: svelte-check 0/0, axe 0, Lighthouse mobile `/pl/` 87, `/pl/wyniki/` 90, CLS 0, LCP 3.0–3.6 s ([[landing-qa]]).

## Powiązane
- [[produkt/_hub|produkt]]
- [[app-system-projektowy]]
- [[app-onboarding-prototyp]]
- [[produkt-landing-i-onboarding]]
- [[2026-10-16-landing-i-konto]]
