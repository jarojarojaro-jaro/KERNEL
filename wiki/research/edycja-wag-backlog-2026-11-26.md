---
typ: research
tags: [research, edycja-wag, eksperymenty, plan]
aktualizacja: 2026-11-26
zrodlo: zwiad WEBacklog 2026-11-26 (na podstawie [[edycja-wag-a-z]], product/research/69c-astra-stop.md, narzedzia/kld-canary.md, ekosystem/nib-chromadera.md, llm/vocab-surgery.md); decyzja [[2026-11-26-eksperymenty-edycji-wag]]
status: aktualne
---
# Lista eksperymentów z edycją wag (2026-11-26)

**11 eksperymentów na nasze modele, uszeregowanych według wartości i gotowości; wspólna bramka dla każdego: podział zadań raz (bramka do wyboru edycji, zamknięty test), KLD na neutralnym tekście ≤ 0,005 (2σ, [[kld-canary]]), metryka zachowania i jakości oceniana sędzią, nie słowami kluczowymi, oraz kontrola z losową edycją tej samej normy (bez niej zysku nie da się przypisać kierunkowi).**

| # | eksperyment | model | stan | praca | karta | decyzja JARO |
|---|---|---|---|---|---|---|
| 1 | WE1 Astra-Stop jako LoRA w locie, skala 0 / 0,5 / 1 / 1,5 | Qwen uncensored Q4_K_M | **zrobione 2026-11-26: negatywne przy effort low** ([[2026-11-26-we1-astra-stop-qwen]]) | 3 h | ok. 100 min | wdrożenie tylko opt-in |
| 2 | „vocab surgery” (Pliny) na Inklingu vs nasza LoRA, sędzia LLM | Inkling AD-Q4_K | gotowe do przygotowania | 4 h | ok. 30 min | nie (test) |
| 3 | WE2 scalenie LoRA uncensored w wagi NVFP4 Niba | Nib | w przygotowaniu | 3 h | ok. 30 min | tak (produkcja) |
| 4 | kierunek długości myślenia per poziom effort | Qwen uncensored | gotowe | 6 h | ok. 180 min | który effort domyślny |
| 5 | kierunek zwięzłości odpowiedzi | Qwen uncensored | gotowe | 5 h | ok. 120 min | czy chcemy krótszych odpowiedzi |
| 6 | kierunek tłumiący `</think>` poza blokiem myślenia (naprawa przecieku Astra) | Qwen uncensored | wymaga strażnika (build) | 6 h | ok. 150 min | tak, jeśli agenci |
| 7 | kierunek „odpowiadaj po polsku” | Qwen, Inkling | gotowe | 5 h | ok. 90 min | czy chcemy |
| 8 | scalenie adaptera pi jako task vector w model uncensored | Qwen uncensored | czeka (adapter nie pobrany, temat odłożony) | 5 h | ok. 120 min | tak |
| 9 | kierunek odmowy dla bazowego Bonsai 2 (najpierw pomiar, czy odmawia) | Bonsai 2 Q2_0 | warunkowe | 8 h | ok. 120 min | czy bazowy Bonsai jest używany |
| 10 | myślenie + zwięzłość razem (gdy 1 i 5 przejdą) | Qwen uncensored | po 1 i 5 | 3 h | ok. 60 min | tak |
| 11 | mini-SELFWRITE: bramka 200 zadań + kontrola losowa, 2 rundy × 3 kandydatów | Qwen uncensored | gotowe, drogie | 12 h | 10–40 h | budżet godzin GPU |

- Statystyka: przy 200 zadaniach 95% CI to ±6,6 pkt, więc małe efekty (rzędu SELFWRITE +1,45) wymagają 500 zadań.
- Kolejność: 1 i 3 już przygotowywane (agenci WE1, WE2), potem 2, 7, 5, 4; 11 tylko z budżetem.

## Na później
- **Większe modele i inne architektury:** techniki ablacji kierunku i scalania LoRA w wagi (WE2: +5–6% vs LoRA w locie) przenoszą się na każdy model z liniowymi projekcjami; sprawdzić przy następnym modelu w topce.
- **Astra-Stop (WE1):** nie działa przy effort low, ale przy effort xhigh (myślenie 26k tokenów) dawał −35% czasu — wrócić, gdy użytkownicy zaczną używać wysokiego effortu.
- **Nib + WE2 na 0.1.2:** łata psuje drafter (K-159); naprawić, jeśli Nib wróci jako silnik.

## Powiązane
- [[edycja-wag-a-z]]
- [[astra-stop]]
- [[vocab-surgery]]
