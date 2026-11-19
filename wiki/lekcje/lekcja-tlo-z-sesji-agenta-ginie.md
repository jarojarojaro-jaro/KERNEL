---
typ: lekcja
tags: [lekcje, vast, koszty, agenci]
aktualizacja: 2026-11-19
zrodlo: qwen-opt/cloud/vast-reaper.sh, qwen-opt/cloud/onstart-guard.sh, qwen-opt/cloud/systemd/, qwen-opt/cloud/k114/launch.sh; [[2026-11-19-k118-nvidia-pelna-moc]]
status: aktualne
---
# Karty w chmurze nigdy nie stoją: zbieranie i usuwanie robi timer systemowy, nie sesja agenta

**2026-11-19: `launch.sh` odpalił `fetch.sh` (zbieranie wyników i usuwanie instancji) oraz lokalne watchdogi przez `setsid nohup … &`. Wszystkie zginęły po zakończeniu tury agenta. Cztery instancje Vast stały bezczynnie ~70 min po skończeniu testów (~$0,8 z $1,11), aż usunąłem je ręcznie. Właściciel: „KARTY NIGDY NIE MOGĄ STAĆ BEZCZYNNIE, to karygodny błąd”.**

Poprawka (wdrożona i sprawdzona na 2 instancjach 3060 tego samego wieczoru, koszt ~$0,02):

1. **`qwen-opt/cloud/vast-reaper.sh`, timer `systemd --user` co 2 min** (`vast-reaper.timer`, linger włączony, działa bez żadnej sesji). Obejmuje każdą naszą instancję (`qwenbench-*`, `kernel-*`, nigdy `buildfarm-*`). Kopiuje `/root/res`, usuwa instancję i zostawia wiadomość w skrzynce Kernela, gdy:
   - runner zostawił `FINISHED`;
   - runner padł;
   - GPU < 5% przez 10 min po „ready”.

   Wiadomość w skrzynce uruchamia turę Kernela, więc każdy koniec testów kończy się pełnym raportem do właściciela bez czekania na jego pytanie. Usuwa też instancje, które nie wystartowały w 15 min, którym runner nie ruszył w 20 min, z SSH martwym od 10 min albo starsze niż 100 min.
   - Test: instancja z udawanym runnerem (60 s, potem `FINISHED`). Reaper skopiował wyniki, usunął ją i zapisał wiadomość z wątkiem KERNEL.
2. **Na instancji `onstart-guard.sh`** to zapas, gdy serwer Jarva nie działa. Instancja usuwa się sama, gdy:
   - runner zniknął bez `FINISHED` na 5 min;
   - GPU < 5% przez 15 min po „ready”;
   - minęło 10 min po `FINISHED`;
   - minęło 25 min bez startu runnera;
   - przekroczyła LIFE_S.
   - Test: instancja ze startem runnera bez procesu usunęła się sama po ~5 min.
3. **`launch.sh` odmawia wynajmu, gdy `vast-reaper.timer` nie jest aktywny.** Na końcu sprawdza, że strażnik na instancji żyje („guard alive”).

Reguły:
- Nic, co ma przeżyć turę (strażnik kosztów, zbieranie, runner lokalny), nie startuje przez `setsid nohup` z narzędzia agenta. Tylko unit `systemd --user`: timer albo `systemd-run --user`.
- „Ruszyło” piszesz tylko wtedy, gdy timer i strażnik na instancji są aktywne.

## Powiązane
- [[lekcja-vastai-destroy-pyta]]
- [[lekcja-vast-tylko-pelna-moc]]
