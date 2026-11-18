---
typ: repo
tags: [repo, nvidia, ampere, 3090, mtp, sparse-attention, telegram]
aktualizacja: 2026-11-18
zrodlo: https://x.com/JakeKAllDay/status/2122782053288829400 (Telegram „gpu”, 2026-11-18); github.com/JakeATX/llamAmpere (MIT) — release v0.7 (2026-11-17, źródło `037e42d8`, build `fe6462fc`), README main (push 11-18)
status: aktualne
---
# llamAmpere (JakeATX): fork llama.cpp pod RTX 30xx — szybki, ale domyślnie niebezstratny

**Fork llama.cpp v1.0 pod Ampere (3090, 3080 Ti, 3060): presety per karta, własne kwanty „AI+”, MTP. Nagłówkowe liczby (3090 „110+ t/s przy 100K generacji, T=1”) pochodzą jednak z trybów, które zmieniają wyjście. Bezstratnych dźwigni do przeniesienia jest mało; najważniejszy dla nas jest kolejny dowód, że w drafcie siedzi zbędna praca (drafter DFlash2 ×3,4 po usunięciu podwójnego kroku).**

**Co jest niebezstratne:**
- **mb-MTP domyślnie włączone:** „więcej zgadniętych słów jest zachowywanych”, a `--no-spec-mb-mtp` daje dokładne próbkowanie.
- **Współdzielony wybór rzadkiej atencji (LSA, Prefrontal AI)** w presetach 12 i 8 GB: ogon 8K + 20% wcześniejszego kontekstu. Autor sam pisze „accepts some output drift”, a KL dopiero „pending”. Liczby: 12 GB przy 102K 73,74 → 103,38 t/s (+40,2%), przy 199K 39,59 → 59,65 (+50,7%); dwa seedy, symulowana pamięć na 3090 Ti.
- Własne kwanty AI4/AI3/AI2 (Swift 1.5 27B: AI4 14,4 GB, KL −10,4% vs IQ4_XS-M). To zmiana kwantu, u nas zakazana jako dźwignia prędkości.

**Co jest bezstratne lub warte uwagi:**

| zmiana | liczba (autor) | u nas |
|---|---|---|
| drafter DFlash2: krok mieszania liczony dwa razy na warstwę → raz | 27 → 93 t/s (×3,4), 3090 Ti, 100K, T=1 | ten sam wzorzec co w K-114 i K-116 (draft 4–15 × droższy niż bajty) oraz w Maya v1.1.66 (podwójny odczyt wag w weryfikacji) |
| 4 użytkowników po ~64K: weryfikacja równoległa zamiast szeregowej | 96,66 → 201,25 t/s łącznie | produkcja 1 slot; ważne dla Enigmy wieloosobowej |
| dynamiczny rozmiar mikrobatcha (duży ub na początku, mniejszy, gdy kontekst potrzebuje pamięci) | 94,21 → 94,60 t/s (×1,004, szum), prefill bez zmian | pomysł dla Enigmy 12–16 GB (dziś stałe ub 256); zmiana ub zmienia numerykę prefillu, więc potrzebna bramka KLD |
| słownik głowicy draftu: uporządkowane 2048 „gorących” tokenów (RM24H) + cache draftu SJ-KVaRN | brak liczb akceptacji | my 64k IQ4_XS; mniejszy słownik zmniejsza bajty, ale K-114 pokazuje, że koszt draftu to narzut, nie bajty |
| prefill Swift 1.5 27B przy 100K „z tym samym wyjściem” | +5,3% | – |
| tryb dokładny rc1 vs v0.6.4 | KL 0 / 0 / 0,0000118 (top-1024 + ogon, 1280 pozycji) | ta sama kultura bramki co nasza (md5/KLD) |

**Jabłka do jabłek:** nasz fork na 3090 robi 80,0 t/s (UD-Q4_K_XL, T=1, krótki kontekst, host 340 W), qwen-warp 121–124 (R69b). llamAmpere w trybie dokładnym (`--no-spec-mb-mtp`, bez rzadkiej atencji) na tym samym pliku nie był mierzony. Test: K-122.

## Powiązane
- [[2026-11-17-k114-nvidia-sufit]]
- [[latent-sparse-attention]]
- [[qwen-qsa-llama-cpp]]
- [[project-maya]]
- [[final-recipes-nvidia]]
