---
typ: metoda
tags: [metody, isa, poprawnosc]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/round6/gdn-bitwise.md:19-93,176-184
status: aktualne
---
# Symboliczny emulator ISA (dowód bitowości offline)

**Gdy GPU było niedostępne, bitowość nowego kernela GDN udowodniliśmy, emulując symbolicznie skompilowane ISA gfx11 i porównując grafy operacji float z bazą.**

Narzędzia (`~/wt/gdn6-isa`, kopia w `qwen-opt/research/round6/gdn-isa-tools`): `gdnemu.py` (emulator jednej fali wave32), `gdncmp.py`, `cmpall.sh`, `isadiff.py`, `dyncount.py`.
- Liczby całkowite (adresy, pętle, exec, LDS, DPP) są konkretne; każdy float z pamięci to symbol, każda instrukcja float tworzy węzeł DAG. Ten sam węzeł = te same operacje IEEE na tych samych argumentach.
- Kanonizacja tylko przez tożsamości dokładne w IEEE (przemienność a·b, a+b, multiplikandów fma, znaki).
- Walidacja: `--numeric` vs rekurencja float64 (błąd 1e-7…1e-4) i 3 celowo zepsute buildy, które emulator oznaczył DIFF.

Wynik dla `opt-gdn6` (b4e819237, 0d89ce56c): wszystkie 4 warianty ALL IDENTICAL; `isadiff`: 44/44 kernele bazy identyczne; liczba wykonanych fma/mul/add równa (np. decode T=1: 83/89/14). Na GPU 2026-10-15 potwierdzone: test-backend-ops 67/67, logity i greedy md5 = baza. Zysk end-to-end w szumie, więc kernel nie trafił do `amd-opt`.

## Powiązane
- [[metody/_hub|Metody]]
- [[zgodnosc-bitowa-md5]]
- [[dowod-offline]]
- [[gdn-fast]]
- [[determinizm-fma]]
