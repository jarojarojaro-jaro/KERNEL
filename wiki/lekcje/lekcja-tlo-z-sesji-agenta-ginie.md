---
typ: lekcja
tags: [lekcje, vast, koszty, agenci]
aktualizacja: 2026-11-19
zrodlo: qwen-opt/cloud/k114/launch.sh, fetch.sh; [[2026-11-19-k118-nvidia-pelna-moc]]
status: aktualne
---
# Procesy w tle odpalone z sesji agenta giną razem z nią: strażników kosztów uruchamiaj przez `systemd-run --user`

**2026-11-19: `launch.sh` odpalił `fetch.sh` (zbieranie wyników i usuwanie instancji) oraz lokalne watchdogi przez `setsid nohup … &`. Wszystkie zginęły po zakończeniu tury agenta. Cztery instancje Vast stały bezczynnie ~70 min po skończeniu testów (~$0,8 z $1,11), aż usunąłem je ręcznie.**

- `setsid nohup` nie wystarcza. Narzędzie sprząta całą grupę procesów albo cgroup sesji.
- Reguła: wszystko, co ma żyć dłużej niż tura (watchdog kosztów, zbieranie wyników, runner), startuje przez `systemd-run --user --collect --unit=<nazwa> …`. Na serwerze Jarva linger jest włączony.
- Reguła: przed odpowiedzią „ruszyło” sprawdź, że strażnik naprawdę żyje (`systemctl --user status <unit>`), a nie tylko sam test.
- Ostatnia linia obrony to samozniszczenie na instancji (`onstart`, `CONTAINER_API_KEY`, LIFE_S + 600 s). Ono zadziałało by po 90 min, więc trzymaj LIFE_S blisko realnego czasu testu.

## Powiązane
- [[lekcja-vastai-destroy-pyta]]
- [[lekcja-vast-tylko-pelna-moc]]
