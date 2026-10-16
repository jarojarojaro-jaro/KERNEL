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
## Notatki (19)

- [[2026-10-12-rocm-domyslny|2026-10-12: ROCm stałym backendem]] — ROCm jest stałym backendem domyślnym; dalsze optymalizacje robimy pod HIP/ROCm, a Vulkan zostaje tylko jako opcja (`run-llm.sh … vulkan`).
- [[2026-10-14-lfm-kv-q8|2026-10-14: LFM używa KV q8_0 (decyzja użytkownika)]] — Użytkownik zdecydował, że LFM2.5 działa z KV cache q8_0 (`run-llm.sh lfm`), mimo kosztu prędkości względem q4_0.
- [[2026-10-15-zakaz-gpu-w-nocy|2026-10-15: czasowy zakaz pracy na GPU]] — Ok. 00:45 użytkownik zakazał pracy na GPU, ok. 02:00 pozwolił znowu; w tym czasie agenci pracowali offline (ISA, emulacja, dry-run).
- [[2026-10-15-czat-na-web-ui-llama|2026-10-15: czat na web UI z llama.cpp, model open core]] — Ekran czatu produktu powstaje na web UI z llama.cpp (MIT); kod w modelu open core (łatki silnika otwarte, baza profili i orkiestrator zamknięte).
- [[2026-10-15-open-core|2026-10-15: model kodu open core]] — Zdecydowane: open core – łatki silnika otwarte (MIT, do upstreamu), a baza profili, orkiestrator strojenia i harness bramek zamknięte.
- [[2026-10-15-karty-kupujemy|2026-10-15: popularne karty kupujemy, rzadkie wynajmujemy]] — Budżet na karty jest: najpopularniejsze karty kupujemy, a rzadkie i drogie (3090, 4090, 5090) wynajmujemy na Vast.
- [[2026-10-15-reasoning-control-off|2026-10-15: reasoning_control wyłączony domyślnie]] — Użytkownik kazał samemu ustawić `reasoning_control` (2026-10-15 00:14 UTC: „NO DOBRA TO USTAW TO REASING CONTROL SAM”); serwer startuje z `{"reasoning_control": false}`, a łatka 0065 ignoruje tę flagę z web UI.
- [[2026-10-15-linux-i-analiza-platformy|2026-10-15: rozwój na Linuksie, obowiązkowa analiza platformy]] — Rozwijamy i testujemy na Linuksie (bez testów na Windowsie teraz), ale każda optymalizacja ma obowiązkowy krok „analiza platformy” dla Windows i macOS.
- [[2026-10-16-budzety-chmury|2026-10-16: budżety $5 na Vast i $6 na RunPod]] — Kampania NVIDIA na Vast może wydać łącznie do $5 (z przedłużeniami), a trening głowicy MTP na RunPod do $6 kosztu naszego poda.
- [[2026-10-16-runpod-drugi-pod|2026-10-16: drugi pod na RunPod należy do użytkownika]] — Drugi działający pod na koncie RunPod (od innego projektu użytkownika) jest jego; nasi agenci go nie dotykają, a nasz limit liczy tylko koszt naszego poda.
- [[2026-10-16-landing-i-konto|2026-10-16: hero landingu i konto na początku]] — Użytkownik chce pełnoprawnego landingu z hero „same hardware, same model, just faster / ten sam sprzęt, ten sam model, po prostu szybciej” i animacją prędkości, a potem konta zakładanego na początku i trzech dróg: wpisz sprzęt (z komendą skanu), aplikacja desktop, terminal.
- [[2026-10-16-saluki-bonsai-na-3060|2026-10-16: na RTX 3060 tylko Saluki i Bonsai]] — Na RTX 3060 testujemy Underdog Saluki 27B i Ternary Bonsai 2 27B, bez Qwen3.5-9B i Qwen 0.8B („tutaj robimy tylko saluki i bonsaia bez 9b i 08b”, 2026-10-16 01:26 UTC).
- [[2026-10-16-nie-placimy-za-przestoj|2026-10-16: nie płacimy za stojące karty w chmurze (twarda zasada)]] — Wynajęta karta ma liczyć albo zostać usunięta; główny agent pilnuje tego automatycznie strażnikiem `idle-watch.py`.
- [[2026-10-16-bez-lokalnego-gpu|2026-10-16: nie testujemy na naszym 7900 XTX]] — Użytkownik: najpierw „narazie nie rób testów na naszym gpu” (2026-10-16 00:56 UTC), a po krótkim teście bit-exact (02:46 UTC): optymalizacje tylko na kartach z Vast, 7900 XTX zostawić i nie robić na nim testów.
- [[2026-10-16-najpierw-wynajem-na-vast|2026-10-16: pierwsza runda NVIDIA na wynajętych kartach]] — Choć plan z 2026-10-15 zakładał kupno popularnych kart (5060 Ti, 3060), pierwsza runda testów NVIDIA poszła w całości na wynajętych kartach Vast (5060 Ti, 3060, 3090) za zgodą użytkownika.
- [[2026-10-16-prosta-baza-wiedzy|2026-10-16: prosta baza wiedzy w KERNEL/wiki]] — Użytkownik: „po prostu baza wiedzy; wszystko ma być dokładnie, ale bez przesady”, każda kategoria w osobnym folderze, widoczna w Obsidianie.
- [[2026-10-16-wiki-jeden-agent|2026-10-16: second brain robi jeden agent, po kolei]] — Użytkownik (2026-10-16 02:23 UTC): „zrób tego second braina jako jeden agent po kolei wszystko dokładnie – mamy dużo czasu, nie spiesz się”.
- [[2026-10-16-wszystko-do-bazy-wiedzy|2026-10-16: wszystko nowe trafia do bazy wiedzy (twarda zasada)]] — Każdy research, pomiar, eksperyment, decyzja i lekcja z projektu trafia do `KERNEL/wiki` zaraz po zakończeniu zadania, zanim zadanie uznamy za skończone.
- [[2026-10-09-limit-mocy-odlozony|Limit mocy GPU odłożony (na prośbę użytkownika)]] — Optymalizacja limitu mocy (np. −20% mocy kosztem ≤5% t/s) została odłożona na prośbę użytkownika; karta pracuje z limitem 285 W.
<!-- AUTO:END -->
