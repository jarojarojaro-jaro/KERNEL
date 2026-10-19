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
## Notatki (28)

- [[produkt-analiza-platformy|Analiza platformy (PLAN §4.5)]] — Każda łatka, profil i ustawienie dostaje rubrykę „gdzie działa i co się zmienia” na Linux / Windows / macOS; wynik idzie do manifestu jako predykat (np. `os: [linux]`, `runtime: rocr`).
- [[produkt-anatomia-l0-l3|Anatomia „przed → po”: warstwy L0–L3]] — Zysk dzieli się na cztery warstwy: L0 naprawy (do ×20, gdy coś zepsute), L1 konfiguracja (×1.5–2.2), L2 strojenie nocne (+0–15%), L3 przepis z labu (+30–70%).
- [[aplikacja-w-budowie|Aplikacja (~/KERNEL/app): stan prototypu]] — Pierwsze elementy produktu zbudowane lokalnie przez AppStudio (2026-10-16, commit `9f96ff4`): system projektowy „Tacho”, statyczna strona SvelteKit PL/EN (47 stron), prototyp onboardingu, skrypty skanu, prototyp aplikacji desktop (8 ekranów), makieta TUI i dokument architektury; nic nie jest wdrożone.
- [[produkt-architektura|Architektura systemu i silnik]] — Komputer użytkownika (GUI Tauri, TUI, daemon Rust `appd`, llama-server jako proces potomny, tuner, updater Ed25519) + mały backend (katalog, baza profili, kolejka) + fabryka przepisów.
- [[produkt-biznes-edycje|Biznes: edycje, model kodu, wejście na rynek]] — Hipotezy (nie decyzje): Free, Turbo (149 zł/rok lub 299 zł dożywotnio), Business (~8 €/stanowisko/mies.), OEM (1–3 € za urządzenie), Tuning Lab (od 5 k€); kod w modelu open core.
- [[produkt-budzet|Budżet (rząd wielkości)]] — GPU w chmurze: faza 0 ~$50–150 łącznie, faza 1 ~$500–600/mies., faza 2 ~$1.2–1.5k/mies., faza 3 ~$2.5–3.5k/mies.; tokeny agentów prawdopodobnie największy koszt fabryki.
- [[kv-na-dysku-polityka|Cache KV na dysku: polityka warstw i budżet zużycia SSD]] — Dysk zabija tylko naiwna polityka: pełny zapis slotu po każdej turze w formacie E5 to ~582 GB na sesję 150k i ~4.7 TB/dzień (dysk 300 TBW w ~64 dni), a polityka „najpierw RAM/tmpfs, na dysk tylko przy shutdown lub presji RAM, top-2 sesje” to ~7 GB/dzień pod twardym limitem 10 GB/dzień (raport 21d, 2026-10-19).
- [[cache-sesji-na-dysku|Cache sesji na dysku (projekt z 16f E5)]] — Istniejący mechanizm llama-server `--slot-save-path` + `/slots/0?action=save|restore` (z checkpointami) przywraca sesję 53k z SSD 23–24× szybciej niż prefill: Qwen MTP 2.28 GiB w 2.51 s zamiast ~61.5 s, LFM 553 MiB w 0.53 s zamiast ~12.2 s (2026-10-18).
- [[produkt-dla-kogo-i-ekrany|Dla kogo, przepływ laika i ekrany MVP]] — Trzy persony (gracz z dobrą kartą, entuzjasta, firma), cel „rozmowa w < 10 min” i siedem ekranów MVP z czatem opartym na web UI llama.cpp.
- [[zawezenie-tezy-produktu|Do decyzji: zawężenie tezy PLAN §0.1 po Magnitude]] — Propozycja raportu 15c (do decyzji użytkownika): teza „żaden produkt nie robi naraz…” zostaje, ale „optymalizacja poza flagami” nie jest już wyróżnikiem; wyróżnikiem jest kombinacja weryfikacji (md5/KLD) + przed → po wobec tuned upstream + AMD natywnie.
- [[produkt-fabryka|Fabryka przepisów (lab)]] — Fabryka zamienia nową parę (GPU, model) w zweryfikowane przyspieszenie: 10-krokowy playbook, istniejące narzędzia, bramki antyoszustwa i metryki (cel ≤ 7 dni od premiery modelu).
- [[produkt-landing-i-onboarding|Landing page i ścieżka użytkownika]] — Hero „Ten sam sprzęt. Ten sam model. Po prostu szybciej.” z animacją prędkości, potem konto na początku i trzy drogi: formularz sprzętu (z komendą „skan”), aplikacja desktop, terminal (pomysł z 2026-10-16).
- [[produkt-ryzyka|Największe ryzyka]] — Dziewięć ryzyk z odpowiedziami; najgroźniejsze: zysk nie przenosi się poza 7900 XTX/Linux oraz wbudowanie auto-tuningu przez LM Studio, Ollamę, Jana lub NVIDIA.
- [[produkt-optymalizacja-u-uzytkownika|Optymalizacja u użytkownika: kalibracja i noc]] — Zawsze szybka kalibracja 1–5 min; opcjonalnie noc za zgodą (zasilacz, bezczynność, limity), z bramką md5 i ABBA; nigdy agentów ani kompilacji na komputerze użytkownika.
- [[otwarte-decyzje-produktu|Otwarte decyzje produktu (po prototypie aplikacji)]] — Pytania AppStudio do użytkownika z 2026-10-16, wciąż bez decyzji: nazwa, kolor akcentu, ceny w teście fake-door, konto przed pobraniem, sprawy prawne, port lokalnego API 11500 i domena.
- [[otwarte-decyzje-techniczne|Otwarte decyzje techniczne (silnik, flagi, wydatki)]] — Rekomendacje agentów, które czekają na decyzję użytkownika: zmiany flag `run-llm.sh`, scalenie łatek do `amd-opt`, testy GPU z ryzykiem i wydatki na chmurę; po decyzji wiersz przechodzi do [[decyzje/_hub|decyzji]].
- [[produkt-platformy-i-lab|Platformy, sprzęt i lab]] — Rozwój na Linuksie, projekt od początku na Win/Linux/macOS; wolumen to NVIDIA (76% Steam), wyróżnik AMD; popularne karty kupujemy, rzadkie (3090, 4090, 5090) wynajmujemy.
- [[produkt-prawo|Prawo, dystrybucja, prywatność]] — Potrzebna spółka z o.o. (podpis Azure w UE, Apple dla organizacji); AI Act art. 50(2) to główne otwarte pytanie; telemetria domyślnie wyłączona; koszt roku 1 ~5.8 tys. zł opłat twardych.
- [[tryb-stratny-pflash|Propozycja: tryb stratny „szybki odczyt długich dokumentów” (PFlash)]] — Propozycja z raportu 15d: PFlash tylko jako jawny tryb opt-in „szybki odczyt długich dokumentów (przybliżony)”, nigdy w sesjach agenta; decyzja po etapie C pilota (~$2 chmury).
- [[app-prototyp-desktop|Prototyp aplikacji desktop, makieta TUI i architektura]] — Osiem ekranów prototypu aplikacji (`/[lang]/app/…`, kod w `landing/src/lib/desktop`), makieta TUI w stylu REACTOR (`tui/tui_demo.py`, 5 scen) i dokument architektury: daemon, lokalne API, onboarding, łączenie konta, dane lokalne vs wysyłane.
- [[app-onboarding-prototyp|Prototyp onboardingu (konto, 3 drogi, wynik)]] — Ścieżki `/start/`, `paths`, `hardware`, `result`, `download`, `terminal` i `/scan/`: konto na początku (Google, GitHub, e-mail – bez backendu), trzy drogi i wynik z przedziałami z estymatora.
- [[przelaczanie-main-uncensored|Przełączanie Main ↔ Uncensored (i „Uncensored jako tryb”)]] — Dziś przełączenie Main ↔ Uncensored to przeładowanie modelu i pełny prefill (~61.5 s przy 53k dla Qwena); llama.cpp przyjmuje jednak plik slotu z drugiego modelu o tych samych kształtach (sprawdza tylko magic, wersję i rozmiary), więc restore trwa 2.51 s – a tryb Uncensored w locie (`h ← h − r(r·h)`) zniósłby przełączenie i osobne pliki całkiem (raport 21e, 2026-10-19).
- [[produkt-roadmapa|Roadmapa: fazy 0–4 z kryteriami wyjścia]] — Faza 0 dowód (3–4 tyg., E1–E7), faza 1 silnik + CLI/TUI alfa (6–8 tyg.), faza 2 GUI + noc beta (8–12 tyg.), faza 3 launch + Turbo + macOS (od ~6.–9. miesiąca), faza 4 rozszerzenia.
- [[app-skrypty-skanu|Skrypty skanu sprzętu (scan.sh, scan-macos.sh, scan.ps1)]] — Trzy skrypty tylko do odczytu wypisują specyfikację i czytelny kod `HW1;os=…;gpu=…;sum=XXXX` do wklejenia w formularz; na Linuksie `strace` uruchomienia przez `sh` pokazał 0 otwarć `/dev/*`.
- [[produkt-stack|Stack technologiczny]] — llama.cpp jako cienka nakładka, daemon i TUI w Rust (ratatui), GUI w Tauri 2 z web UI llama.cpp, API OpenAI/Anthropic/Ollama tylko na 127.0.0.1 z tokenem.
- [[app-landing|Strona (landing) PL/EN]] — Statyczna strona w SvelteKit 2.70 + Svelte 5 (adapter-static), 47 stron PL i EN: hero z animacją „pojedynek prędkości” 38,8 → 109,0 t/s, metodologia z surowymi liczbami, dokumenty prawne i baner cookies.
- [[app-system-projektowy|System projektowy „telemetria w nocy” i znak Tacho]] — Tokeny (kolor, typografia, przestrzeń, ruch), motyw ciemny i jasny, komponenty i znak „Tacho”: grafitowe tło `#07080D` i jeden kolor sygnałowy volt `#C8FF3D`, który znaczy „po” i „nasze”.
- [[werdykt|Werdykt planu produktu]] — Produkt da się zrobić, a luka jest realna, ale duży skok (np. Qwen 40 → 109 t/s) daje konfiguracja i przepisy z naszego labu, nie „noc u użytkownika” (PLAN, stan 2026-10-15).
<!-- AUTO:END -->
