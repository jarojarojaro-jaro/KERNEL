---
typ: llm
tags: [llm, uncensored, edycja-wag, inkling]
aktualizacja: 2026-11-23
zrodlo: https://x.com/elder_plinius/status/2124584972866498884 (2026-11-22; Telegram właściciela 2026-11-23)
status: do-sprawdzenia
---
# „Vocab Surgery”: zdjęcie cenzury przez edycję kilkunastu wierszy embeddingu i lm_head

**Pliny (2026-11-22) zdejmuje odmowy z Inkling-2-Mini bez ruszania warstw: przesuwa 7 wierszy embeddingu (z 201 024) w stronę „zgodnych” tokenów i zmniejsza do 10% 10 wierszy macierzy wyjściowej; deklaruje odmowy bliskie zeru na 800+ promptach i pomijalną stratę jakości, ale bez metody pomiaru (deklaracja, niezmierzone u nas).**

## Mechanizm
- **Wejście (embedding):** 7 tokenów odmowy przesunięte o 90% w stronę par: „cannot” → „can”, „ refuse” → „ provide”, „ unable” → „ able”, „ harmful” → „ helpful”, „ illegal” → „ legal”. Model „słyszy” te słowa w prompcie jak ich zgodne pary.
- **Wyjście (unembedding):** te 7 tokenów + „safety”, „ safety”, „Safety” przeskalowane do 10%, więc ich logit spada i prawdopodobieństwo maleje (autor: ~10×).
- Zero zmian w atencji, MLP, routerze i normach; edycja trwa < 2 min na MacBooku.

## Ocena (Kernel)
- **Najważniejsze zastrzeżenie:** jeśli „odmowę” liczono detektorem słów kluczowych („cannot”, „unable”, „refuse”), to metoda wyłącza dokładnie te słowa i wynik sam się potwierdza. Model może dalej odmawiać innymi słowami („I won't”, zmiana tematu). Potrzebny sędzia treści (LLM-judge albo ręczna ocena), nie słownik.
- Część wyjściowa to w praktyce stały `logit_bias` na 10 tokenów: to samo da się zrobić bez zmiany pliku, w samplerze.
- Różnica wobec naszych modeli Uncensored: OrcaRouter i AtomicChat robią edycję rank-1 kierunku odmowy w „pisarzach” strumienia ([[uncensored-ablacja-kierunku]]), czyli zmieniają *decyzję* modelu. Vocab Surgery zmienia tylko *słowa*, którymi decyzja wychodzi.
- Ryzyko jakości: tokeny „harmful/illegal/safety” występują też w zwykłych tekstach (prawo, medycyna, kod), a ich przytłumienie może psuć takie odpowiedzi; autor nie podaje benchmarku.
- Dla prędkości nic: ten sam rozmiar i kształt wag.

## Test (propozycja, bez karty)
CPU albo Colab T4: Inkling-2-Mini Q4 bazowy vs Vocab Surgery vs AtomicChat AD-Q4_K; ten sam zestaw promptów odmowy oceniany sędzią treści, plus PPL i krótki MMLU. Zmiana produkcyjnego modelu tylko decyzją JARO.

## Powiązane
- [[uncensored-ablacja-kierunku]]
- [[inkling-2-mini]]
- [[trening-llm-mapa]]
