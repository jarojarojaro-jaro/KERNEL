---
typ: ekosystem
tags: [ekosystem, silnik, inkling, spekulacja, produkt, enigma]
aktualizacja: 2026-11-24
zrodlo: https://github.com/satellitedown/inkling-2-mini-abliterated-ingine (`556acc7`, 2026-11-22, README i lista plików); https://x.com/satellitedown/status/2124945507214856588; nasz wpis w [[maya-ik2-inkling]] i [[inkling-2-mini]]
status: aktualne
---
# ingine (satellitedown): własny silnik dla jednego modelu na jednej karcie, który działa

**Jedna osoba napisała silnik C++/CUDA tylko dla Inkling-2-Mini na RTX 5090 (sm_120a, FP4 Blackwella) i doszła do 490–560 t/s z DSpark i prefillu 6200–10 900 t/s, z instalatorem, aktualizacją i API — czyli zrobiła to, co nie udało się nam w Enigma Turbo, bo zawęziła zakres i od początku sprawdzała wynik względem oryginału.**

## Co jest w repo (README, lista plików)
- Silnik: `native/src/core/decode_graph.cpp` (krok jako graf), `kernels/draft/accept.cu` (akceptacja draftów na GPU), szerokość weryfikacji wybierana na GPU, jedna synchronizacja hosta na rundę, krok N+1 przed odczytem tokenu N, wagi czytane evict-first (+1–2%; u nas nietemporalne +9%).
- `apps/validate` i `apps/bench` obok `apps/serve`; `engine/fake_generator.cpp` — generator bez GPU do testów serwera (to samo co symulator w [[inference-stack]]).
- Serwowanie: 1 zapytanie naraz, do 4 w kolejce, potem HTTP 503; następna tura czyta tylko nowe tokeny; rozmowy na zmianę (podagenci, drugi klient) „zaparkowane” w wolnej pamięci karty (domyślnie do 3 GiB, nigdy ostatnie 4 GiB, `--park-mb`).
- Produkt: instalator jedną komendą, model przypięty do rewizji HF i sprawdzany plik po pliku, aktualizacja przenosi stare pliki do `models/…previous-<czas>/` zamiast kasować, jednostka `systemd --user`, `ingine status` z kodami wyjścia (0 gotowy, 1 startuje, 3 zatrzymany), profil sterownika P0 (+0,8% dekodu, opisany i wyłączalny).
- Ablacja: plik 1,7 MB, rzut z progiem i detektorem; odmowy 1/104, KL 0,014 na nieszkodliwych.

## Porównanie z naszymi odpowiednikami
| warstwa | ingine | my |
|---|---|---|
| silnik | 1 model, 1 karta, bramka względem oryginału | Enigma Turbo: ogólny silnik, testy tylko na syntetycznym modelu, bełkot 0,7 t/s ([[enigma-turbo-gemini-2026-11-20]]); Maya ik2 z naszymi łatkami HIP: 113 t/s na XTX |
| dekod (skala pasma) | 5090 1,79 TB/s → przy tej wydajności XTX miałby ~260 t/s [INFERENCE] | Maya na XTX ~104–113 t/s |
| serwer | kolejka 4 + 503, parkowanie rozmów w VRAM | topka: sloty + cache w RAM, E4 wyrzucanie cache agenta |
| instalacja i aktualizacja | jedna komenda, sprawdzane pliki, poprzednia wersja zachowana | Enigma: instalator bez powrotu do poprzedniej wersji; silnik AMD `distribution: local` |

## Co bierzemy
1. Lekcja „własny silnik”: zakres jeden model × jedna karta, bramka tekstu i logitów względem referencji od pierwszego dnia; dopiero potem prędkość. Maya to dla nas ta droga na AMD, nie nowy silnik od zera.
2. Parkowanie rozmów podagentów w wolnej VRAM z budżetem — dla topki i Mayi, gdzie omp prowadzi kilka rozmów na zmianę.
3. Kolejka z limitem i 503 zamiast wiszących połączeń; `status` z kodami wyjścia — do watchdoga Enigmy.
4. Mechanizmy kroku (wybór szerokości na GPU, potok kroków) — kolejka testów Mayi.

## Powiązane
- [[maya-ik2-inkling]]
- [[inkling-2-mini]]
- [[inference-stack]]
- [[enigma-turbo-gemini-2026-11-20]]
