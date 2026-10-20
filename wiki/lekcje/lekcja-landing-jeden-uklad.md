---
typ: lekcja
tags: [lekcje, landing, ux, produkt]
aktualizacja: 2026-10-20
zrodlo: git `e873c35`, `53945b1`, `0c4a2c9` (~/KERNEL, app/landing); ~/KERNEL/app/landing/src/lib/data/measurements.ts:685; polecenie użytkownika przekazane przez Main 2026-10-20
status: aktualne
---
# Landing: jeden układ stron producentów, spójne liczby między scenami, treść widoczna od pierwszej klatki, spokojny ruch

**Cztery uwagi użytkownika z 2026-10-20 do landingu: osobny układ strony Apple odrzucony, scena 02 pokazywała liczbę z innej karty niż 01, wejście „laguje” przez fade z opacity 0, a pulsujące elementy są niemile widziane.**

- **Jeden układ dla wszystkich producentów**: strony NVIDIA/AMD/Intel/Apple mają tę samą strukturę i pozycje; różni się tylko rodzina kolorów i zdjęcie (Apple: srebro + Mac Studio, `e873c35`). Własny układ Apple użytkownik odrzucił.
- **Scena 01 (Skan) i 02 (Dobór) pokazują tę samą kartę**: 22.9 GB było liczbą z RTX 3090 obok skanu XTX; XTX zmierzony: 23359 MiB = 22.8 GB (amd-smi po załadowaniu, n_ctx 204800; `measurements.ts:685`, `53945b1`). Każda liczba na stronie musi pochodzić z tej samej karty co scena.
- **Above the fold widoczne przy pierwszym renderze**: fade-in z opacity 0 bramkowany JS dawał ~1.0–1.2 s „lagu”; wejścia tylko transformem, 0.6–0.7 s (`e873c35`).
- **Bez pulsowania**: ruch spokojny i jednorazowy (pas wyniku „no plate, no pulse”, `0c4a2c9`).

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[app-landing]]
- [[landing-qa]]
- [[lekcja-timeline-scen-3s]]
- [[2026-10-16-landing-i-konto]]
