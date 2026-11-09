---
typ: lekcja
tags: [lekcje, kolejka, gpu, build]
aktualizacja: 2026-11-08
zrodlo: ~/qwen-opt/queue/run-jobs.sh:40-47; ~/.local/bin/cpuheavy:1-15; zgłoszenie agenta XtxKvOnce (job kvq-once2, 2026-11-08 ~00:50)
status: aktualne
---
# `cpuheavy` wywołany z wnętrza joba kolejki GPU = zakleszczenie

**Job `kvq-once2` budował silnik przez `cpuheavy` w etapie joba: oba sloty CPU trzymały procesy `cpuheavy --quiet` innego agenta, które czekały na `quiet.lock`, a ten trzymała kolejka dla właśnie tego joba — nikt nie mógł ruszyć, GPU stało (2026-11-08).**

Reguła: w jobie kolejki nigdy `cpuheavy` (ani `--quiet`). Budować przed zgłoszeniem joba; jeśli build musi być w jobie, to zwykłe `nice -n19 taskset -c 0-3 cmake --build … -j4` (kolejka i tak trzyma GPU, a CPU ma wolne).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-kolejka-fifo-bilety]]
