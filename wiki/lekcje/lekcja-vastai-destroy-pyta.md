---
typ: lekcja
tags: [lekcje, vast, chmura, koszty, watchdog]
aktualizacja: 2026-11-17
zrodlo: sesja K-114 2026-11-17 (serwer Jarva, vastai 1.11.0); `vastai destroy instance --help`
status: aktualne
---
# Lekcja: `vastai destroy instance` w CLI 1.11 pyta o potwierdzenie, więc watchdog bez `-y` nic nie usuwa

**`vastai destroy instance <id>` bez terminala wypisuje „Aborted.” i instancja dalej działa i kosztuje. Każdy watchdog, sprzątanie i skrypt `down` musi wołać `vastai destroy instance <id> -y`, a po usunięciu trzeba sprawdzić `vastai show instances`.**

**Co się stało (2026-11-17):**
- Wolna 3060 (pobieranie modelu z HF ~3 MB/s) miała zostać usunięta. Pierwsze `destroy` z basha agenta wypisało „Aborted.” i nic nie zrobiło.
- Te same polecenia bez `-y` czekały w lokalnych watchdogach 3090 i 5060 Ti. Po czasie życia też by nie zadziałały, a instancje stałyby do samozniszczenia na hoście.

**Poprawka:**
- `qwen-opt/cloud/k114/launch.sh` woła już `destroy ... -y`;
- `down.sh` miał `-y` wcześniej;
- obecne watchdogi uruchomione ponownie z `-y`.

**Reguła:**
- Dwa niezależne timery: lokalny watchdog z `-y` oraz samozniszczenie na instancji przez `CONTAINER_API_KEY`.
- Po każdym usunięciu kontrola listą instancji.
- Za wolny host (pobieranie < 20 MB/s przy 10 GB) usuwamy od razu i bierzemy inną ofertę. Deklarowane `inet_down` nie gwarantuje prędkości z HF (2026-11-17: 1–3 MB/s na 3 z 5 hostów).
- Pobieranie modelu z HF przez `qwen-opt/cloud/k114/pdl.sh` (16 równoległych zakresów): 2 → 16 MB/s na tym samym hoście.
- Przy wyborze hosta patrz też na CPU: słaby CPU = minuty ponownej kwantyzacji draftu przy każdym starcie serwera (K-117).

## Powiązane
- [[lekcja-vast-transfer-kosztuje]]
- [[skrypty-chmury]]
- [[vast-ai]]
