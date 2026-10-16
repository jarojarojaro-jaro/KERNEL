---
typ: produkt
tags: [produkt, plan, lab, agenci]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/PLAN.md:223-250
status: aktualne
---
# Fabryka przepisów (lab)

**Fabryka zamienia nową parę (GPU, model) w zweryfikowane przyspieszenie: 10-krokowy playbook, istniejące narzędzia, bramki antyoszustwa i metryki (cel ≤ 7 dni od premiery modelu).**

- Playbook: sufit pasma → profil per token → koszt granicy kernela → ablacja → hipoteza z budżetem µs → łatka z wyłącznikiem → testy op → bramka bit/KLD → przeplatane A/B → wpis w NOTES (także negatywny).
- Narzędzia, które są: `greedy.sh`, `spec_sweep`, `samp_ab.py`, `kld_gate` + kanarki, `loo.py`, Kernel Tuner, emulator ISA GDN, `isadiff.py`, REACTOR, `pm4_soak.py`, `det_probe.py`.
- Brakuje: scheduler farmy, API serwisu bramek, jedna baza benchmarków, adaptery profilera NVIDIA/Apple, pakowanie przepisów i bot rebase, ledger hipotez.
- Antyoszustwo: referencja i pomiar poza zasięgiem agenta, fingerprint wyjść, sprawdzenie, czy zmiana się wykonała (lekcje Sakana, Kevin, METR, GPU MODE).
- Metryki: czas do przepisu na top-3 arch, koszt przepisu, odsetek łatek przechodzących rebase bez pracy ręcznej.

## Powiązane
- [[produkt/_hub|produkt]]
- [[produkt-architektura]]
- [[produkt-analiza-platformy]]
- [[playbook-optymalizacji]]
- [[metr-sakana]]
