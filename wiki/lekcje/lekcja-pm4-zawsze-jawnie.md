---
typ: lekcja
tags: [lekcje, pm4, awarie, bezpieczenstwo]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24l-fuzja-norm.md:7,35-37,62-63; ~/AGENTS.md:17; XtxLab 2026-10-20 (raport 35, reasoning n=4 136.2 vs 144.4 t/s)
status: aktualne
---
# Nieustawione `GGML_HIP_PM4` = PM4 z `WA=0` – zawsze ustawiaj jawnie

**Każdy build naszego forka przy nieustawionym `GGML_HIP_PM4` włącza taśmę PM4 w trybie `WA=0` bez poprawki PRIV; test fuzji norm (24l) bez tej zmiennej zawiesił taśmę i skończył się page faultem + mode1 resetem GPU (2026-10-19 21:10).**

Reguła (od 2026-10-19, `~/AGENTS.md:17`): w każdym jobie, teście, benchu i skrypcie ustaw PM4 jawnie:
- `GGML_HIP_PM4=0` (eksperymenty, test-backend-ops, nowe kernele), albo
- `GGML_HIP_PM4=1 GGML_HIP_PM4_WA=2 GGML_HIP_PM4_GUARD=1 HSA_USE_SVM=0` (profil topki).

`run-jobs.sh` domyślnie eksportuje `GGML_HIP_PM4=0`; `run-topka.sh` ustawia profil WA=2. Skrypty spoza tych dwóch (np. `tests.sh` z 24l) nie dziedziczą niczego – trzeba dopisać ręcznie.

**Druga pułapka (2026-10-20):** `run-topka.sh` brał `${GGML_HIP_PM4:-1}`, więc w kolejce dziedziczył bezpieczne `0` i topka (także okno testowe użytkownika) chodziła bez PM4: 136.2 zamiast 144.4 t/s, bez żadnego ostrzeżenia. Naprawa: `run-jobs.sh` oznacza swój domyślny `0` przez `QUEUE_PM4_SAFETY=1`, a `run-topka.sh` wtedy wraca do profilu produkcyjnego; `user-window.sh` ustawia PM4 jawnie. Wniosek ogólny: domyślna wartość bezpieczeństwa nie może po cichu zmieniać konfiguracji produkcyjnej – przy każdym starcie sprawdzaj w `/proc/<pid>/environ` faktyczne PM4 serwera.

Dlaczego to groźne: wywłaszczenie (CWSR) taśmy z `PRIV=0` zostawia wskaźnik kernargów 0 → fault SQC(data) @0 (sygnatura raportu 17), a fault w taśmie PM4 kończy się resetem całej karty, nie procesu ([[lekcja-pm4-zamienia-fault-w-reset]]).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-pm4-zamienia-fault-w-reset]]
- [[raport-24l-fuzja-norm]]
- [[pm4-replay]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
