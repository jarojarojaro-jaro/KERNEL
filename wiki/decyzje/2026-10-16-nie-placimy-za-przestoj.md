---
typ: decyzja
tags: [decyzje, chmura, koszty]
aktualizacja: 2026-10-16
zrodlo: rozmowa 2026-10-16 (użytkownik: „nie ma sensu płacić jak stoją — pilnuj i miej na uwadze zawsze, żeby nie marnować”); ~/qwen-opt/cloud/idle-watch.py
status: aktualne
---
# 2026-10-16: nie płacimy za stojące karty w chmurze (twarda zasada)

**Wynajęta karta ma liczyć albo zostać usunięta; główny agent pilnuje tego automatycznie strażnikiem `idle-watch.py`.**

Strażnik co 180 s czyta obciążenie GPU wszystkich naszych instancji Vast i podów RunPod (pomija pod użytkownika) i budzi głównego agenta, gdy któraś ma < 5% przez 15 min z rzędu; krótkie przerwy między rundami ABBA alarmu nie wywołują. Zasady dla agentów chmurowych: budowy i przygotowania robić lokalnie przed wynajmem (nvcc w `~/opt/cuda-12.8`), modele pobierać równolegle z kompilacją, kolejne pomiary ustawiać w kolejce bez przerw, po ostatnim pomiarze od razu `collect` i `destroy`.

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[decyzje/2026-10-16-budzety-chmury|budżety chmury]]
- [[lekcje/lekcja-5060ti-bezczynna|lekcja: bezczynna 5060 Ti]]
- [[narzedzia/skrypty-chmury|skrypty chmury]]
