---
typ: hub
tags: [decyzje, hub]
aktualizacja: 2026-10-16
zrodlo: wiki/tools/wiki.py index
status: aktualne
---
# Decyzje użytkownika

**Decyzje i korekty użytkownika z datą; mają pierwszeństwo przed każdą inną notatką.**

Gdy notatka w innym folderze przeczy decyzji, wygrywa decyzja (a notatkę trzeba poprawić). Jedna notatka = jedna decyzja, nazwa `RRRR-MM-DD-krotko`.

Wróć: [[index|Strona główna]]. Lista niżej jest generowana przez `python3 tools/wiki.py index`; nie edytuj jej ręcznie.

<!-- AUTO:START -->
## Notatki (36)

- [[2026-10-12-rocm-domyslny|2026-10-12: ROCm stałym backendem]] — ROCm jest stałym backendem domyślnym; dalsze optymalizacje robimy pod HIP/ROCm, a Vulkan zostaje tylko jako opcja (`run-llm.sh … vulkan`).
- [[2026-10-14-lfm-kv-q8|2026-10-14: LFM używa KV q8_0 (decyzja użytkownika)]] — Użytkownik zdecydował, że LFM2.5 działa z KV cache q8_0 (`run-llm.sh lfm`), mimo kosztu prędkości względem q4_0.
- [[2026-10-15-zakaz-gpu-w-nocy|2026-10-15: czasowy zakaz pracy na GPU]] — Ok. 00:45 użytkownik zakazał pracy na GPU, ok. 02:00 pozwolił znowu; w tym czasie agenci pracowali offline (ISA, emulacja, dry-run).
- [[2026-10-15-czat-na-web-ui-llama|2026-10-15: czat na web UI z llama.cpp, model open core]] — Ekran czatu produktu powstaje na web UI z llama.cpp (MIT); kod w modelu open core (łatki silnika otwarte, baza profili i orkiestrator zamknięte).
- [[2026-10-15-open-core|2026-10-15: model kodu open core]] — Zdecydowane: open core – łatki silnika otwarte (MIT, do upstreamu), a baza profili, orkiestrator strojenia i harness bramek zamknięte.
- [[2026-10-15-karty-kupujemy|2026-10-15: popularne karty kupujemy, rzadkie wynajmujemy]] — Budżet na karty jest: najpopularniejsze karty kupujemy, a rzadkie i drogie (3090, 4090, 5090) wynajmujemy na Vast.
- [[2026-10-15-reasoning-control-off|2026-10-15: reasoning_control wyłączony domyślnie]] — Użytkownik kazał samemu ustawić `reasoning_control` (2026-10-15 00:14 UTC: „NO DOBRA TO USTAW TO REASING CONTROL SAM”); serwer startuje z `{"reasoning_control": false}`, a łatka 0065 ignoruje tę flagę z web UI.
- [[2026-10-15-linux-i-analiza-platformy|2026-10-15: rozwój na Linuksie, obowiązkowa analiza platformy]] — Rozwijamy i testujemy na Linuksie (bez testów na Windowsie teraz), ale każda optymalizacja ma obowiązkowy krok „analiza platformy” dla Windows i macOS.
- [[2026-10-16-badamy-magnitude|2026-10-16: badamy podejście Magnitude i przejmujemy, co działa]] — Użytkownik (2026-10-16, 17:22 UTC): „oni coś zrobili dobrze, trzeba to zbadać i zobaczyć, czy możemy wykorzystać” – po wynikach 16d, gdzie Magnitude wygrał code-edit 156.1 vs 105.2 t/s.
- [[2026-10-16-budzety-chmury|2026-10-16: budżety $5 na Vast i $6 na RunPod]] — Kampania NVIDIA na Vast może wydać łącznie do $5 (z przedłużeniami), a trening głowicy MTP na RunPod do $6 kosztu naszego poda.
- [[2026-10-16-runpod-drugi-pod|2026-10-16: drugi pod na RunPod należy do użytkownika]] — Drugi działający pod na koncie RunPod (od innego projektu użytkownika) jest jego; nasi agenci go nie dotykają, a nasz limit liczy tylko koszt naszego poda.
- [[2026-10-16-landing-i-konto|2026-10-16: hero landingu i konto na początku]] — Użytkownik chce pełnoprawnego landingu z hero „same hardware, same model, just faster / ten sam sprzęt, ten sam model, po prostu szybciej” i animacją prędkości, a potem konta zakładanego na początku i trzech dróg: wpisz sprzęt (z komendą skanu), aplikacja desktop, terminal.
- [[2026-10-16-kvq-cuda-zostaje|2026-10-16: kvq na CUDA zostaje włączone, KLD Qwena do powtórki]] — Rodzic (Main) zdecydował (2026-10-16; 2026-10-18 zawężone wyjątkiem n=1, niżej): `kvq` na CUDA zostaje domyślnie włączone także dla Qwena przy ub 1, mimo FAIL bramki KLD +2.53σ; przy następnym wynajmie 3090 powtarzamy KLD Qwena z `--chunks 4`.
- [[2026-10-16-saluki-bonsai-na-3060|2026-10-16: na RTX 3060 tylko Saluki i Bonsai]] — Na RTX 3060 testujemy Underdog Saluki 27B i Ternary Bonsai 2 27B, bez Qwen3.5-9B i Qwen 0.8B („tutaj robimy tylko saluki i bonsaia bez 9b i 08b”, 2026-10-16 01:26 UTC).
- [[2026-10-16-nie-placimy-za-przestoj|2026-10-16: nie płacimy za stojące karty w chmurze (twarda zasada)]] — Wynajęta karta ma liczyć albo zostać usunięta; główny agent pilnuje tego automatycznie strażnikiem `idle-watch.py`.
- [[2026-10-16-bez-lokalnego-gpu|2026-10-16: nie testujemy na naszym 7900 XTX]] — Użytkownik: najpierw „narazie nie rób testów na naszym gpu” (2026-10-16 00:56 UTC), a po krótkim teście bit-exact (02:46 UTC): optymalizacje tylko na kartach z Vast, 7900 XTX zostawić i nie robić na nim testów.
- [[2026-10-16-najpierw-wynajem-na-vast|2026-10-16: pierwsza runda NVIDIA na wynajętych kartach]] — Choć plan z 2026-10-15 zakładał kupno popularnych kart (5060 Ti, 3060), pierwsza runda testów NVIDIA poszła w całości na wynajętych kartach Vast (5060 Ti, 3060, 3090) za zgodą użytkownika.
- [[2026-10-16-prosta-baza-wiedzy|2026-10-16: prosta baza wiedzy w KERNEL/wiki]] — Użytkownik: „po prostu baza wiedzy; wszystko ma być dokładnie, ale bez przesady”, każda kategoria w osobnym folderze, widoczna w Obsidianie.
- [[2026-10-16-wiki-jeden-agent|2026-10-16: second brain robi jeden agent, po kolei]] — Użytkownik (2026-10-16 02:23 UTC): „zrób tego second braina jako jeden agent po kolei wszystko dokładnie – mamy dużo czasu, nie spiesz się”.
- [[2026-10-16-wszystko-do-bazy-wiedzy|2026-10-16: wszystko nowe trafia do bazy wiedzy (twarda zasada)]] — Każdy research, pomiar, eksperyment, decyzja i lekcja z projektu trafia do `KERNEL/wiki` zaraz po zakończeniu zadania, zanim zadanie uznamy za skończone.
- [[2026-10-19-kv-tylko-w-ram|2026-10-19: cache sesji/KV tylko w RAM, bez warstwy SSD]] — Użytkownik zdecydował (2026-10-19): „zostawiamy głównie RAM offload, jak już SSD nie ruszamy” – stan sesji i KV trzymamy tylko w RAM (`--cache-ram`, ewentualnie tmpfs), niczego z KV/sesji nie zapisujemy na dysk; warstwa L3 SSD z raportu 21d odpada.
- [[2026-10-19-buildy-przez-rbuild|2026-10-19: kompilacje tylko przez `rbuild` (zdalny serwer), bez cichego lokalnego fallbacku]] — Decyzja (2026-10-19): każdy build forka idzie przez `~/qwen-opt/tools/rbuild <worktree> [cele]` na zdalnym serwerze 24 vCPU; lokalne buildy `-j2` trzymały quiet.lock ~50 min i GPU stało przy 11 zadaniach w kolejce.
- [[2026-10-19-bezpieczenstwo-sprzetu|2026-10-19: maksymalna optymalizacja, ale nigdy kosztem bezpieczeństwa sprzętu]] — Twarda zasada użytkownika (2026-10-19, `AGENTS.md` wiersz 5): optymalizujemy maksymalnie, ale nigdy kosztem bezpieczeństwa sprzętu.
- [[2026-10-19-szanujemy-sprzet-serwera|2026-10-19: szanujemy sprzęt serwera (CPU i narzędzia w tle)]] — Twarda zasada z `AGENTS.md` (2026-10-19): ciężkie skrypty CPU `nice -n 19` i ≤ 4 wątki, kompilacje `nice -n 10 -j6`, bez pętli z drogimi komendami (pełny `journalctl`, `find ~`), headless Chrome zamykany od razu po testach, narzędzia działające w tle mają kosztować ~0 CPU; dla GPU obowiązuje [[2026-10-19-bezpieczenstwo-sprzetu]].
- [[2026-10-19-topka-tylko-keeper|2026-10-19: topkę (serwer użytkownika na :8080) restartuje tylko `topka-keeper.sh`]] — Decyzja (2026-10-19): topkę uruchamia wyłącznie `~/qwen-opt/tools/topka-keeper.sh` (start, gdy blokada GPU wolna, i trzymanie blokady podczas ładowania); agenci mogą ją tylko zatrzymać wewnątrz własnej blokady GPU, nigdy uruchomić, a serwery testowe nigdy nie słuchają na 8080.
- [[2026-10-19-chmura-bez-destroy-all|2026-10-19: w chmurze nigdy „destroy all” – usuwamy tylko własne instancje po id]] — Decyzja (2026-10-19): instancje Vast/RunPod usuwamy wyłącznie po id (`~/qwen-opt/cloud/down.sh <id>`); instancji `buildfarm-*` i `neuron-lab*` nie dotykamy – teardown sesji 3090 skasował wcześniej serwer kompilacji innego agenta.
- [[2026-10-19-wentylator-100-przy-pracy|2026-10-19: wentylator XTX 100%, gdy GPU pracuje]] — Użytkownik zdecydował (2026-10-19, 00:00 UTC): gdy GPU pracuje, wentylator RX 7900 XTX chodzi na 100% (`FAN=100` w `fan.sh`, wcześniej 90%).
- [[2026-10-19-najlepiej-bez-pytania|2026-10-19: wszystko jak najlepiej i jak najszybciej, bez pytania]] — Użytkownik (2026-10-19): „Wszystko jak najlepiej i jak najszybciej. Jeśli coś poprawia, dodajemy; jeśli dodanie psuje coś innego, nie dodajemy. Nie pytaj mnie – po prostu zrób najlepiej, jak się da.”
- [[2026-10-20-karta-fabrycznie|2026-10-20: karta zostaje na ustawieniach fabrycznych]] — Decyzja użytkownika (2026-10-20): żadnego podkręcania pamięci ani rdzenia, żadnych zmian taktowań, napięć ani limitu mocy dla zysku prędkości – przyspieszamy wyłącznie programowo.
- [[2026-10-20-bez-publikacji-localmaxxing|2026-10-20: localmaxxing tylko do czytania, ciągły wywiad konkurencji]] — Użytkownik (2026-10-20): „na localmaxxing nie chcę na razie publikować — takie rzeczy mamy wyciągać” (np. NInfer 510,7 t/s na 5090, tqLLM 156,2 t/s na 5060 Ti). Nie zgłaszamy naszych wyników; bazę i repozytoria konkurencji czytamy stale i każdą nowość przekuwamy w eksperyment.
- [[2026-10-20-auth-bez-backendu|2026-10-20: logowanie bez backendu – `PUBLIC_AUTH_PROVIDER=none`, wymienne Supabase / Auth.js]] — Nie ma jeszcze backendu ani domeny, więc landing buduje się z `PUBLIC_AUTH_PROVIDER=none`: przyciski Google/GitHub widoczne, ale wyłączone, a pole e-mail zapisuje na listę oczekujących; backend wybieramy później przez zmianę jednej zmiennej (`supabase` albo `authjs`).
- [[2026-10-20-uncensored-poza-strona|2026-10-20: Qwen3.8-27B Uncensored nie pojawia się na stronie produktu (licencja otwarta)]] — Qwen3.8-27B Uncensored zostaje poza stroną produktu, dopóki kwestia licencji jest otwarta; mierzymy go wewnętrznie (rekordy, raporty), ale landing i katalog pokazują tylko modele bez usuniętych zabezpieczeń.
- [[2026-10-20-szybkie-iteracje|2026-10-20: szybkie iteracje – ≤ 10 min GPU na pomysł, ≤ 20 min pracy na próbę]] — Decyzja użytkownika (2026-10-20): test GPU jednego pomysłu maksymalnie 10 minut łącznie (krótka bramka + krótkie A/B, 2–3 seedy), jedna próba optymalizacji maksymalnie 20 minut pracy do pierwszego testu; nie wygrywa wyraźnie → odrzucamy i dalej.
- [[2026-10-20-kontekst-min-131k|2026-10-20: testy na kontekście minimum 131k]] — Użytkownik (2026-10-20): „ma być kontekst minimum 131k do testów, 32k to nie benchmark”. Każdy pomiar karty (U0/U1/T) idzie przy `-c ≥ 131072`, KV q4_0; reguła „≥32k” z kampanii opt-* 2026-10-20 jest nieaktualna.
- [[2026-10-20-chmura-wstrzymana|2026-10-20: testy w chmurze wstrzymane, priorytet XTX i research]] — Użytkownik (2026-10-20): „na razie testy cloud GPU odpuszczamy — robimy research z nowych tematów i patrzymy, jak zoptymalizować Qwena na XTX”. Plan v2 kampanii NVIDIA (PLAN-NV-V2.md, doładowanie $8 / wariant $3) czeka; nic nie wynajmujemy.
- [[2026-10-09-limit-mocy-odlozony|Limit mocy GPU odłożony (na prośbę użytkownika)]] — Optymalizacja limitu mocy (np. −20% mocy kosztem ≤5% t/s) została odłożona na prośbę użytkownika; karta pracuje z limitem 285 W.
<!-- AUTO:END -->
