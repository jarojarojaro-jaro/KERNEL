---
typ: decyzja
tags: [decyzje, edycja-wag, eksperymenty]
aktualizacja: 2026-11-26
zrodlo: panel JARO 2026-11-26 02:07
status: aktualne
---
# 2026-11-26: robimy dużo eksperymentów z edycją wag

**JARO (2026-11-26 02:07), o skracaniu myślenia jednym kierunkiem i wpisaniu ablacji w plik Mai/Niba: „zrobmy duzo eksperymen tow z tym weight editing i wgl - to jest groundbreaking temat i musimy go analizowac jak sie da”.**

- Zgoda na eksperymenty zmieniające odpowiedzi modelu przez edycję wag (testy, nie produkcja). Każdy wynik z metryką zachowania, jakością na zestawie z odpowiedziami i KLD na neutralnym tekście ([[2026-11-26-bramka-kld]]).
- Zmiana modelu w produkcji (czat :8080, topka) dalej tylko decyzją JARO po wynikach.
- Start 2026-11-26: WE1 Astra-Stop na Qwen uncensored (runtime LoRA, skale 0–1,5), WE2 scalenie LoRA uncensored w wagi NVFP4 Niba, lista kolejnych eksperymentów ([[edycja-wag-a-z]]).

## Powiązane
- [[decyzje/_hub|decyzje]]
- [[edycja-wag-a-z]]
