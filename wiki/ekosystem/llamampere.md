---
typ: ekosystem
tags: [ekosystem, nvidia, ampere, 3090, mtp, sparse-attention, telegram]
aktualizacja: 2026-11-25
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

## Inkling 2 Mini v0.7.5 / v0.7.5.1 (2026-11-25, HEAD `8369abe`)
- Liczby autora, RTX 3090 Ti 350 W, T=1, odpowiedź 5120 tok., KV 4-bit, `--preset 24ink` z drafterem `Inkling-2-Mini-ATX-Drafter-Q8_0` (0,45 GB): plik 5,4 bpw (NVFP4Q8, 17,56 GB) 3K **189,0**, 32K 182,6, 100K 144,7 t/s; plik 4,4 bpw (AI4) 3K 192,6, 100K 147,9. Prefill 100K 2512–2747 t/s. v0.7.4.1 → v0.7.5 to +4–12% dekodu i +23–45% prefillu (maski atencji na GPU, padding KV, top-K głowicy draftera, rdzenie tensorowe w weryfikacji Q8).
- **Uwaga 1, próbkowanie:** profile kart w `common/preset.cpp:117` ustawiają T=1 z **top-k 20**, top-p 0,95. Profilu `24ink` nie ma w opublikowanym źródle (rg: tylko README), więc jego sampler jest nieznany. Przypuszczam, że jest ten sam. Nasza lekcja K-167: Nib robi 150 t/s z top-k 40, a przy pełnym rozkładzie 39,3, więc obcięcie rozkładu mocno podnosi akceptację.
- **Uwaga 2, jakość:** to ich własne kwanty, a KL liczą do pełnej precyzji (0,00315, top-1 98,1%), czyli inaczej niż nasz dowód „ten sam plik”. Weryfikacja w partiach 512 zamiast 5 zmienia KL (0,00337), więc ścieżka weryfikacji nie jest bitowo równa autoregresji.
- **Porównanie z nami:** 3090 Ti ma 1008 GB/s, XTX 960. Nasza produkcja Maya T=0,7 ok. 113 t/s, Nib + LoRA 147,3 (top-k 40), K-158f do 165,6 na kodzie. Test na równych warunkach (T=1, top-k 20, top-p 0,95, prompt 3K i 32K, odpowiedź długa): K-171.


## K-171: pomiar w ich warunkach (2026-11-25)
- XTX, T=1 / top-k 20 / top-p 0,95, odpowiedź 2048 tok.: Maya prod 101,8 (3K) / 90,7 (32K), Maya K-158 110,3 / 105,9; llamAmpere na 3090 Ti 189,0 / 182,6. Różnica ok. 1,7×.
- Opublikowane źródło (HEAD `8369abe`) nie zawiera ścieżki Inklinga: brak profilu `24ink`, przełączników `FUSE_*`, `NK_*`, `Q8TC`, formatu NVFP4Q8 (przegląd scout 2026-11-25). Akceptacja spekulacji przy T=1 w ich domyślnej ścieżce jest dokładna (`common/sampling.cpp:1237-1270`), mb-MTP nie dotyczy draftera blokowego. Przyczyny przewagi nie da się więc odczytać z kodu; pierwszy pomiar u nas: udział grafów i ścieżki blokowej w Mai (`IK2_GRAPH=0`, `IK2_BLOCK=0`) i akceptacja na krok.

## Powiązane
- [[2026-11-17-k114-nvidia-sufit]]
- [[latent-sparse-attention]]
- [[qwen-qsa-llama-cpp]]
- [[project-maya]]
- [[final-recipes-nvidia]]
