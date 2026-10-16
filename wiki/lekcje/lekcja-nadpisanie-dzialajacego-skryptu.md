---
typ: lekcja
tags: [lekcje, chmura, skrypty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-5060ti.md:212; rozmowa 2026-10-16 (BitExactSpec: edycja ~/wt/bx-isa/validate.sh w trakcie przebiegu, restart z kopii /tmp/bxv-validate-frozen.sh)
status: aktualne
---
# Nadpisanie działającego skryptu psuje pomiar (2 incydenty)

**Powłoka czyta skrypt w trakcie wykonania po przesunięciu bajtowym, więc zmiana pliku, który właśnie działa, zmienia dalsze polecenia; zdarzyło się to dwa razy 2026-10-16.**

1. RTX 5060 Ti: `scp` nadpisał `plan.sh` (ten sam i-węzeł) i przerwał fazę przełączników hosta Qwena po 2 przełącznikach; powtórzenie jako `plan2.sh`.
2. XTX: agent poprawił `validate.sh` (dłuższe wcześniejsze linie) podczas walidacji bit-exact; przebieg przerwany, uruchomiony ponownie z zamrożonej kopii.

Reguła: długie testy uruchamiać z kopii (`cp skrypt /tmp/…-frozen.sh`), a zmiany zapisywać jako nowy plik albo przez plik tymczasowy i `mv`; nigdy nie edytować działającego skryptu w miejscu. Skrypty GPU same biorą blokadę `/tmp/gpu.lock` (incydent 2 zaczął się od skryptu bez blokady, który zabrał VRAM innemu agentowi).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-brak-column-w-obrazie]]
- [[lekcja-5060ti-bezczynna]]
- [[skrypty-chmury]]
- [[2026-10-16-bit-exact]]
