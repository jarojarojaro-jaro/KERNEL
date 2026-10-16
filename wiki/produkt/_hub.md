---
typ: hub
tags: [produkt, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Produkt

**Plan produktu konsumenckiego: lokalne AI plug and play, które samo się przyspiesza.**

Źródło: `product/PLAN.md`. Decyzje produktowe z datą także w [[decyzje/_hub|Decyzjach]].

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (16)

- [[produkt-analiza-platformy|Analiza platformy (PLAN §4.5)]] — Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; wynik idzie do manifestu jako predykat (np. `os: [linux]`, `runtime: rocr`).
- [[produkt-anatomia-l0-l3|Anatomia „przed → po”: warstwy L0–L3]] — Zysk dzieli się na cztery warstwy: L0 naprawy (do ×20, gdy coś zepsute), L1 konfiguracja (×1.5–2.2), L2 strojenie nocne (+0–15%), L3 przepis z labu (+30–70%).
- [[aplikacja-w-budowie|Aplikacja (~/KERNEL/app) – w budowie]] — Katalog `~/KERNEL/app/` jest w trakcie budowy przez agenta AppStudio; brak `REPORT.md`, więc opis dotyczy tylko struktury katalogów.
- [[produkt-architektura|Architektura systemu i silnik]] — Komputer użytkownika (GUI Tauri, TUI, daemon Rust `appd`, llama-server jako proces potomny, tuner, updater Ed25519) + mały backend (katalog, baza profili, kolejka) + fabryka przepisów.
- [[produkt-biznes-edycje|Biznes: edycje, model kodu, wejście na rynek]] — Hipotezy (nie decyzje): Free, Turbo (149 zł/rok lub 299 zł dożywotnio), Business (~8 €/stanowisko/mies.), OEM (1–3 € za urządzenie), Tuning Lab (od 5 k€); kod w modelu open core.
- [[produkt-budzet|Budżet (rząd wielkości)]] — GPU w chmurze: faza 0 ~$50–150 łącznie, faza 1 ~$500–600/mies., faza 2 ~$1.2–1.5k/mies., faza 3 ~$2.5–3.5k/mies.; tokeny agentów prawdopodobnie największy koszt fabryki.
- [[produkt-dla-kogo-i-ekrany|Dla kogo, przepływ laika i ekrany MVP]] — Trzy persony (gracz z dobrą kartą, entuzjasta, firma), cel „rozmowa w < 10 min” i siedem ekranów MVP z czatem opartym na web UI llama.cpp.
- [[produkt-fabryka|Fabryka przepisów (lab)]] — Fabryka zamienia nową parę (GPU, model) w zweryfikowane przyspieszenie: 10-krokowy playbook, istniejące narzędzia, bramki antyoszustwa i metryki (cel ≤ 7 dni od premiery modelu).
- [[produkt-landing-i-onboarding|Landing page i ścieżka użytkownika]] — Hero „Ten sam sprzęt. Ten sam model. Po prostu szybciej.” z animacją prędkości, potem konto na początku i trzy drogi: formularz sprzętu (z komendą „skan”), aplikacja desktop, terminal (pomysł z 2026-10-16).
- [[produkt-ryzyka|Największe ryzyka]] — Dziewięć ryzyk z odpowiedziami; najgroźniejsze: zysk nie przenosi się poza 7900 XTX/Linux oraz wbudowanie auto-tuningu przez LM Studio, Ollamę, Jana lub NVIDIA.
- [[produkt-optymalizacja-u-uzytkownika|Optymalizacja u użytkownika: kalibracja i noc]] — Zawsze szybka kalibracja 1–5 min; opcjonalnie noc za zgodą (zasilacz, bezczynność, limity), z bramką md5 i ABBA; nigdy agentów ani kompilacji na komputerze użytkownika.
- [[produkt-platformy-i-lab|Platformy, sprzęt i lab]] — Rozwój na Linuksie, projekt od początku na Win/Linux/macOS; wolumen to NVIDIA (76% Steam), wyróżnik AMD; popularne karty kupujemy, rzadkie (3090, 4090, 5090) wynajmujemy.
- [[produkt-prawo|Prawo, dystrybucja, prywatność]] — Potrzebna spółka z o.o. (podpis Azure w UE, Apple dla organizacji); AI Act art. 50(2) to główne otwarte pytanie; telemetria domyślnie wyłączona; koszt roku 1 ~5.8 tys. zł opłat twardych.
- [[produkt-roadmapa|Roadmapa: fazy 0–4 z kryteriami wyjścia]] — Faza 0 dowód (3–4 tyg., E1–E7), faza 1 silnik + CLI/TUI alfa (6–8 tyg.), faza 2 GUI + noc beta (8–12 tyg.), faza 3 launch + Turbo + macOS (od ~6.–9. miesiąca), faza 4 rozszerzenia.
- [[produkt-stack|Stack technologiczny]] — llama.cpp jako cienka nakładka, daemon i TUI w Rust (ratatui), GUI w Tauri 2 z web UI llama.cpp, API OpenAI/Anthropic/Ollama tylko na 127.0.0.1 z tokenem.
- [[werdykt|Werdykt planu produktu]] — Produkt da się zrobić, a luka jest realna, ale duży skok (np. Qwen 40 → 109 t/s) daje konfiguracja i przepisy z naszego labu, nie „noc u użytkownika” (PLAN, stan 2026-10-15).
<!-- AUTO:END -->
