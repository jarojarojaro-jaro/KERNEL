---
typ: produkt
tags: [produkt, plan, ux]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:89-126
status: aktualne
---
# Dla kogo, przepływ laika i ekrany MVP

**Trzy persony (gracz z dobrą kartą, entuzjasta, firma), cel „rozmowa w < 10 min” i siedem ekranów MVP z czatem opartym na web UI llama.cpp.**

- Persony: „Gracz” (RTX 3060–5090 / RX 7800–9070, Windows), „Entuzjasta” (r/LocalLLaMA, ma Ollamę/LM Studio), „Firma/integrator” (później).
- Hasło robocze: „Twoje AI na Twoim komputerze. Dobrane, zmierzone i przyspieszone. Te same odpowiedzi.”
- Przepływ: instalator < 60 MB → kreator i zgoda → skan < 1 s + test silnika w podprocesie → rekomendacja (1 + 2 alternatywy) → pobieranie z HF z sha256 → paczka silnika z bazy → kalibracja 1–5 min + self-test → pierwsza rozmowa → propozycja nocy → raport rano z „Cofnij”.
- Ekrany: Czat (web UI llama.cpp, SvelteKit 2 + Svelte 5, MIT; decyzja 2026-10-15), Mój komputer, Wynik, Optymalizacja nocna, Modele, Dla programistów (lokalne API), TUI/CLI w stylu REACTOR.

## Powiązane
- [[produkt/_hub|produkt]]
- [[werdykt]]
- [[produkt-landing-i-onboarding]]
- [[2026-10-15-czat-na-web-ui-llama]]
- [[reactor-monitor]]
