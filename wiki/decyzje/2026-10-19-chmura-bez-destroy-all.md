---
typ: decyzja
tags: [decyzje, chmura, vast, koszty]
aktualizacja: 2026-10-20
zrodlo: ~/AGENTS.md:15; ~/KERNEL/product/research/25-buildfarm.md:43-45; ~/KERNEL/product/research/27-3090-final.md:227; polecenie użytkownika przekazane przez Main 2026-10-20 (neuron-lab*)
status: aktualne
---
# 2026-10-19: w chmurze nigdy „destroy all” – usuwamy tylko własne instancje po id

**Decyzja (2026-10-19): instancje Vast/RunPod usuwamy wyłącznie po id (`~/qwen-opt/cloud/down.sh <id>`); instancji `buildfarm-*` i `neuron-lab*` nie dotykamy – teardown sesji 3090 skasował wcześniej serwer kompilacji innego agenta.**

- `idle-watch.py` pomija etykiety `buildfarm*`; `down.sh --all` i masowe `vastai destroy instances` w `lib.sh` nie ruszają `buildfarm*` (`25:43-45`).
- Wzorzec poprawny: raport 27 zniszczył wszystkie swoje `nv-final-*` po id, z lokalnym watchdogiem i self-destruct na instancji (`27:227`).
- Instancje `neuron-lab*` nie są nasze (zakaz z polecenia użytkownika 2026-10-20) [INFERENCE: inny projekt].
- Kontekst kosztów: [[2026-10-16-nie-placimy-za-przestoj]], [[2026-10-16-budzety-chmury]].

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[2026-10-16-nie-placimy-za-przestoj]]
- [[2026-10-16-budzety-chmury]]
- [[raport-25-buildfarm]]
- [[vast-ai]]
