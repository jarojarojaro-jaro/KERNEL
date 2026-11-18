---
typ: lekcja
tags: [lekcje, metodyka, automatyzacja, agenci, czas, telegram]
aktualizacja: 2026-11-18
zrodlo: właściciel 2026-11-18 („nie tylko optymalizacja kerneli, ale też to, w jakim czasie się optymalizują — bardzo ważna rzecz”); x.com/Akashi203/status/2123011900439142779 i x.com/rightnow_co/status/2123011648365666500 (2026-11-18); ~/KERNEL/product/research/70-fa-d256-jak-to-zrobilismy.md:28-40; [[2026-11-17-k114-nvidia-sufit]]
status: aktualne
---
# Lekcja: czas od nowego modelu lub pomysłu do zmierzonego wyniku to osobna metryka, którą mierzymy i skracamy

**Ważny jest nie tylko wynik optymalizacji, ale też ile czasu zajmuje jego zdobycie (właściciel 2026-11-18). Dlatego każda kampania zapisuje znaczniki czasu etapów i szukamy w niej najwolniejszego etapu, tak jak najwolniejszego kernela.**

**Bodziec:** RightNow (YC):
- Agent zoptymalizował kernele nowego modelu Tencent Hy4 flash „w niecałe 2 godziny, bez człowieka”, a miesiąc wcześniej jeden kernel zajmował całą noc.
- Podają 218 t/s i 98% trafień cache.
- **Nie podają karty, punktu wyjścia ani metody, więc liczby nie da się sprawdzić.** Prawdziwa jest sama lekcja.

**Nasze czasy (z zapisów):**

| kampania | od pomysłu do wyniku | czas GPU | najwolniejszy etap |
|---|---|---|---|
| FA D256 wariant 83 (XTX) | 2026-11-07 wieczór → 11-09 02:58, ~27 h | 62 min (jeden job) + 8 min straconego joba (brak biblioteki w RUNPATH) | czekanie na okno GPU i budowa, nie pomiar (`70-fa-d256-jak-to-zrobilismy.md:35-39`) |
| K-114 NVIDIA × 3 karty (Vast) | 13:30 → 14:24, ~55 min pomiaru, ~2 h ściany z analizą | ~25 min właściwych pomiarów | pobieranie modelu z HF (2 MB/s), złe hosty (3 z 5), ponowna kwantyzacja draftu na słabym CPU (12 min) |

**Co już skraca czas:**
- bramka bitowa zamiast kampanii KLD (FA83: 62 min zamiast dni);
- jedna binarka z maską wariantów ([[sweep-wariantow-kernela]]);
- `pdl.sh` (pobieranie 2 → 16 MB/s);
- `hostguard.sh` (zły host odpada w minutę);
- sufit z `karty.py` przed pomiarem ([[skill-io-sufity]]).

**Co jeszcze zabiera godziny i co z tym zrobić:**
- start serwera na słabym CPU → cache skwantowanego draftu na NVIDIA (K-117);
- ręczny wybór wariantu → wyścig statystyczny (K-121, [[ga-racing-rohanarun]]);
- czekanie na okno GPU i turę → runner odłączony + jeden plik wyników (już w `k114/`);
- pobieranie modeli → wybierać hosty z szybkim HF i `pdl.sh` od pierwszej minuty.

**Reguła:**
- Każda kampania (nowy model, nowa karta, nowy kernel) zapisuje w `phases.txt` znaczniki: start, host gotowy, model pobrany, silnik gotowy, pierwszy pomiar, wynik.
- W notatce eksperymentu wiersz „czas: ściana / GPU / najwolniejszy etap”.
- Pierwsze zastosowanie: nowy model z K-119 lub K-120, czyli zegar od pobrania do tabeli „zmierzone vs sufit”.

## Powiązane
- [[skill-io-metodyka]]
- [[2026-11-17-k114-nvidia-sufit]]
- [[ga-racing-rohanarun]]
- [[KOLEJKA-TESTOW]]
