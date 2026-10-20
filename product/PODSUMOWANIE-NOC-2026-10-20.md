# Podsumowanie nocy 2026-10-20

**Testy na 7900 XTX wstrzymane na noc (decyzja użytkownika ~03:15). Dokończone tylko CPU, RTX 4060 Ti w chmurze i baza wiedzy. Serwer wyłączony przez `systemctl poweroff`.**

## Silnik

| Co | Stan | Liczby / źródło |
|---|---|---|
| Nowa topka (coupled + host-gap, `~/wt/topka` 9056cea22) | zbudowana w `~/qwen-opt/topka-next`, **nie zainstalowana** | md5 OK: Qwen plain c4708318, MTP 6f14e814, LFM 894e56e4, przełączniki on == off (`queue/logs/next-md5-*.log`) |
| A/B host-gap na nowym buildzie (coupled=1 w obu ramionach, T=1, seeds 1–3, ABBA) | zrobione przed wstrzymaniem | średnio 113.0 → **114.6 t/s (+1.4%)**, każdy prompt szybszy; proza PL 93.4 → 96.1, EN chat 93.3 → 94.7; ms/step 27.7–28.2 → 27.3–27.7 (`~/qwen-opt/hostgap/logs-next/SUMMARY-sweep.txt`) |
| A/B mvs (edycja kodu) | przerwane (wstrzymanie) | do zrobienia rano |
| PAIR2 (−40 launchy/krok) | port + build gotowe, **bez pomiaru** | raport `research/24w-pair2.md`; rano `run-jobs.sh ~/qwen-opt/queue/p2.jobs` |
| Prefill FA (24v) | odrzucone: +0.4–0.8%, bit-exact, poniżej progu | `research/24v-prefill-fa.md` |
| Adaptacyjna głębokość (24q) | odrzucone dla topki | tail gate ≤ +0.5% nawet z wyrocznią; adaptacyjna głębokość zmienia greedy md5 (d217c1a0/888170e6), bo verify zależy od szerokości; sens tylko na gałęzi batch-invariant (sama kosztuje 2.8–9%) (`research/24q-adaptacyjna-spekulacja.md`) |

## RTX 4060 Ti 16 GB (raport 29, `research/29-4060ti.md`)

| | U0 | U1 | T (nasz) | T vs U0 |
|---|---|---|---|---|
| Qwen Q3_K_XL czat T=1 | 18.6 | 30.6 | **35.4** | ×1.90 |
| Qwen edycja kodu (mvs) | 18.5 | 50.0 | **170.9** | ×9.2 |
| LFM czat T=1 | 114.4 | 113.3 | **149.4** | ×1.31 |

Host Vast z limitem mocy 100 W i PCIe gen3 x8. Instancja zamknięta, Vast: 0 instancji. Karta jeszcze nie ma wpisu na stronie (`cards.json` + `measurements.ts`).

## Strona (wszystko wypchnięte)
Hero v3.3 (pas wyniku ×3,2 bez pulsowania), skan v4 (części karty ↔ log), Dobór zielony/czerwony na XTX 22.8 GB, spłaszczony wykres, zdjęcia kart 5060 Ti / 3060 / Mac Studio z logo, wspólny układ stron producentów + poprawka laga (1.4 → 0.8 s), metodologia (akcenty, 7 rozdziałów), konto `/start` (auth `none`, `AUTH.md`), nagłówek w jednej linii od 1021 px. `qa:clip` 0.

## Research
Raport 30: Intel Arc bez wynajmu godzinowego (GigaGPU Arc Pro B60 £129/mies.), Apple: Scaleway M4 32 GB €0.29/h (min. 24 h), Enverge Mac Studio M5 Ultra $2.50/h co minutę, Darkbloom nie nadaje się. M1 Pro użytkownika: plan w raporcie 30, czeka na dostęp SSH.

## Rano (kolejność)
1. Start topki i podglądu strony (po włączeniu serwera nie startują same z tej sesji).
2. A/B mvs nowej topki (`next.jobs`, tylko linia `next-mvs`), potem instalacja `topka-next` → `~/llama-topka` (backup), 3 przełączniki host-gap w `run-topka.sh`, md5.
3. PAIR2: `p2.jobs` (≤10 min).
4. Karta 4060 Ti na stronę.
5. Baza wiedzy: `wiki` zaktualizowana (commit dbea20c, lint 0/0).
