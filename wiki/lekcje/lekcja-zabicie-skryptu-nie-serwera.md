---
typ: lekcja
tags: [lekcje, proces, gpu]
aktualizacja: 2026-11-25
zrodlo: ~/KERNEL/product/research/16e-kwanty-kld.md:306
status: aktualne
---
# Zabicie skryptu nie zabija serwera

**Po zabiciu skryptu zadań osierocony `llama-server` (Saluki, `-np 20`) trzymał 18 GB na A40, przez co dwa kolejne serwery zadań (U3, B0) dostały OOM (E1, 2026-10-16).**

Reguła: skrypt uruchamiający serwer ma `trap` zabijający serwer, a ręczne przerwanie kończy się `pkill -9 -f "llama-server.*<port>"` i sprawdzeniem VRAM przed następnym startem.

## Nawrót 2026-11-25 (K-164 → K-165)
- `k164.sh wall` startował serwer jako `cd … && taskset … server.py … & srv=$!`: `$!` to PID podpowłoki, nie Pythona. Trap zabił podpowłokę i `maya-ik2`, a osierocony `server.py` dalej trzymał port 18796 i **sam wskrzesił silnik**.
- Skutek: cały K-165 (Nib z LoRA i bez) odpowiadał serwer Mai: Nib dostał OOM i `bind: Address already in use`, a skrypt i tak zmierzył 112/108 t/s i 0/5 odmów z cudzego serwera. Wynik wyglądał wiarygodnie; zdradziły go identyczne odpowiedzi obu ramion i brak linii `[lora]`.
- Poprawka: w `k164.sh`, `nib-ab.sh`, `nib-unc-ab.sh` przed startem i w trapie `pkill -9 -f "port $PORT"` (kolejka jest szeregowa, więc wszystko na porcie testowym jest nasze i nieaktualne), a gdy port nadal zajęty: wyjście 4 zamiast pomiaru.
- Reguła dodatkowa: tło z `cd … && …` daje PID podpowłoki; serwer startujemy przez `cd …; taskset … &` albo zabijamy po porcie. Skrypt pomiarowy sprawdza, że odpowiada **jego** serwer (port wolny przed startem, PID nasłuchującego = nasz).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-zombie-serwery]]
- [[lekcja-pkill-wlasna-powloka]]
- [[serializacja-gpu]]
