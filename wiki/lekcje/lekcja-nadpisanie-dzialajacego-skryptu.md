---
typ: lekcja
tags: [lekcje, chmura, skrypty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-5060ti.md:212
status: aktualne
---
# Nadpisanie działającego skryptu przerwało pomiar

**Na wynajętej RTX 5060 Ti `scp` nadpisał `plan.sh` (ten sam i-węzeł) podczas jego działania i przerwał fazę pomiaru przełączników hosta Qwena po 2 przełącznikach.**

Powtórzenie poszło jako nowy plik `plan2.sh hostspec`. Powód: powłoka czyta skrypt w trakcie wykonania, więc zmiana zawartości tego samego pliku zmienia dalsze polecenia. Reguła: na zdalnych maszynach wysyłać nowe pliki (inna nazwa albo zapis do pliku tymczasowego i `mv`), nigdy nie nadpisywać działającego skryptu w miejscu.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-brak-column-w-obrazie]]
- [[lekcja-5060ti-bezczynna]]
- [[skrypty-chmury]]
- [[2026-10-16-kampania-nvidia]]
