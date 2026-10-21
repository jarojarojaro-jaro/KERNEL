---
typ: lekcja
tags: [lekcje, pm4, awarie, kolejka]
aktualizacja: 2026-10-21
zrodlo: journalctl -k 2026-10-21 04:07:21 (pid 1293181) i 12:46:18 (pid 22639); ~/qwen-opt/draft-shortlist/logs/s53-A1.launch.log, s53m-A1.launch.log; ~/KERNEL/product/research/55-teardown-pm4.md; ~/qwen-opt/queue/cancel.sh
status: aktualne (przyczyna znaleziona, poprawka w gałęzi pm4-teardown, test GPU w ~/qwen-opt/teardown/td.jobs jeszcze nieuruchomiony)
---
# Nie zabijaj serwera PM4 w trakcie taśmy (drugi SIGTERM → exit() → page fault)

**2026-10-21 o 04:07 i 12:46 zatrzymanie ramienia benchmarku (`cancel.sh` + `stop()` w `p100_arm.sh`) dało page fault SQC (inst), PERMISSION_FAULTS 0x3. Resetu nie było. Przyczyna (raport 55): serwer dostał ≥3 SIGTERM w kilka ms w trakcie generacji. Drugi wywołał w handlerze sygnału `exit(1)` (`tools/server/server.cpp:33`, „Received second interrupt”). `exit()` uruchomił destruktory modułów HIP, które wyładowały code objecty, a wątek główny wciąż czekał na taśmę PM4 wykonującą się na GPU. Fale pobierały instrukcje ze zwolnionej pamięci. O 12:46 w tej samej sekundzie wystąpił też GP fault w libc, a proces zawiesił się w `exit()`, więc po 45 s dostał SIGKILL.**

Pierwsza wersja tej lekcji (04:07) przypisywała fault SIGKILL-owi. Log serwera pokazuje, że wcześniej zadziałała ścieżka `exit(1)`.

Poprawka (gałąź `pm4-teardown`, domyślnie on, md5 bez zmian z konstrukcji):
- handler tylko zapisuje do pipe'a, a sygnał obsługuje osobny wątek;
- pierwszy sygnał zatrzymuje pętlę na granicy kroku, potem `ggml_backend_quiesce` (replay PM4 off, czekanie na ostatnią taśmę, `cudaDeviceSynchronize`, z limitem i logiem), dopiero potem zwalnianie;
- kolejny sygnał czeka na drenaż (do 30 s) i robi `_Exit`, nigdy `exit`;
- `atexit` w hip-pm4 drenuje taśmę przed destruktorami HIP.

Reguły:
- buildy bez `pm4-teardown` (produkcja f9b84bcfa) zatrzymujemy JEDNYM SIGTERM, gdy serwer jest bezczynny (obecny `cancel.sh`: najpierw klienci, czekanie na idle, potem SIGTERM, 45 s, SIGKILL w ostateczności);
- nie wysyłać kilku sygnałów naraz: `pkill` w trapie skryptu plus SIGTERM z `cancel.sh` to dokładnie wzór z 04:07 i 12:46;
- `exit()` nigdy z handlera sygnału w procesie z pracą na GPU;
- po faulcie: `journalctl -k` (reset?), stan karty, dopiero potem dalsza praca.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[pm4-replay]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[lekcja-pm4-zawsze-jawnie]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
