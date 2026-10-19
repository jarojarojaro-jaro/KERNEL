---
typ: lekcja
tags: [lekcje, gpu, proces]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16f-xtx-szybkie.md:6,227; komunikat Main do WikiIngest 2026-10-18 (wentylator, Chrome); ~/KERNEL/product/research/17-gpu-page-fault.md:55-56
status: aktualne
---
# Nigdy nie usuwać ani nie odtwarzać `/tmp/*.lock`

**2026-10-18 ktoś odtworzył pliki `/tmp/gpu.lock` i `/tmp/quiet.lock`; nowy inode złamał wzajemne wykluczanie `flock`, dwa zadania GPU szły równolegle (23:18–23:30 UTC, wyniki 16f odrzucone).**

Korekta (raport 17): mode1 reset o 23:25 nie wynikał z kolizji – pliki blokad odtworzono ~23:26, blok `pin1-lfm` ruszył 23:25:26 przy `vram_used_before 26 MiB`, czyli po resecie; R9 to ta sama awaria PM4 co pozostałe ([[2026-10-19-page-faulty-gpu-analiza]]).

`flock` blokuje inode, nie nazwę: proces trzymający stary plik i proces na nowym pliku nie widzą się nawzajem. Restart czyści `/tmp`, więc pliki blokad tworzy się raz po starcie i tylko je otwiera.

Reguła: skrypty robią `flock /tmp/gpu.lock …` (tworzy, gdy brak), nigdy `rm`/`touch` po usunięciu; po kolizji odrzucić wszystkie pomiary z jej okna.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[serializacja-gpu]]
- [[lekcja-zombie-serwery]]
- [[lekcja-tmp-po-restarcie]]
