---
typ: archiwum
tags: [archiwum, moc]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:107-121
status: nieaktualne
wycofano: 2026-11-22
powod: uchylona: od 20.10 karta fabrycznie (bez zmian limitu mocy), od 06.11 profil eco 2200 MHz; 285 W z 09.10 nie obowiązuje
zastapiona_przez: decyzje/2026-10-20-karta-fabrycznie
---
# Limit mocy GPU odłożony (na prośbę użytkownika)

**Optymalizacja limitu mocy (np. −20% mocy kosztem ≤5% t/s) została odłożona na prośbę użytkownika; karta pracuje z limitem 285 W.**

Sekcja NOTES „Na później: limit mocy GPU (odłożone na prośbę użytkownika)”, stan karty z 2026-10-09: domyślnie 303 W, zakres 272–350 W, zapis wymaga roota, OverDrive wyłączony. Plan pomiaru (350/303/290/272 W, `amd-smi metric -p`) czeka.

## Powiązane
- [[amdgpu-moc-i-termika]]
- [[rx-7900-xtx]]
- [[amd-smi]]
