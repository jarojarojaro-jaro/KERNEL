---
typ: metoda
tags: [metody, publikacja, bramki, enigma, wdrozenie, skill-io]
aktualizacja: 2026-11-17
zrodlo: ~/kernel/zrodla/inference-optimisation-skill @ fda968e — references/publishing.md:1-64, SKILL.md:152-159, PROMPT.md:50-94 (format raportu)
status: aktualne
---
# Kwalifikacja i publikacja wg skill-io (publishing.md) a nasze wdrożenia topki i Enigmy

**Przepis jest coś wart tylko wtedy, gdy ktoś inny go odbuduje i dostanie ten sam wynik (`publishing.md:3`). Nasze wdrożenia spełniają przypinanie, bramkę md5 i dowód „kopia = najlepsze”. Brakuje pełnego zestawu 6 bramek akceptacji (narzędzia w obie strony, igła przy 85% okna, rozdzielenie myślenia) i budowania produkcji z czystego checkoutu przypiętego commita.**

**Kroki** (`publishing.md:5-50`):
1. **Kod w publicznym repo na przypiętym commicie, bez lokalnych łatek** (`:5-9`).
   - Topka: łatki w `qwen-opt/patches/topka-q70`, ale build z worktree. Enigma: wydanie `enigma-engines-cuda-2026-11-07` + SHA256.
2. **Przypiąć wszystko** (obraz, commit silnika, pakiety, rewizja wag) **i budować z czystego checkoutu** z tymi samymi flagami. Nigdy dwóch buildów jednej biblioteki w procesie (`:11-18`).
   - Częściowo: rewizji wag modeli nie przypinamy w zapisie.
3. **Uruchomienie dokładnie jak w benchmarku:** mechaniczny diff argumentów (`:20-23`).
   - Tak: `run-topka.sh` jest jedynym launcherem; [[lekcja-restart-zlym-launcherem]].
4. **Sześć bramek na czystym buildzie** (`:25-36`):

   | bramka | u nas |
   |---|---|
   | ładowanie i `/v1/models` | tak (`/health`, n_ctx 262144) |
   | czat ze stop | tak (greedy md5) |
   | rozumowanie oddzielone od treści | **brak w bramce** (jest w EvalPlus/jakość-mini) |
   | narzędzia: pełny round trip | **brak** (BFCL jest offline, bez wykonania) |
   | igła ~85% okna | **brak** (K-109) |
   | prędkość: 30 s dekodu, liczona tokenizerem serwera | tak (spec_sweep) |

   Do tego wizja i soak współbieżny, jeśli dotyczy. Bramki z rozgrzewką powtarzać, nigdy nie publikować z jednej fali.
5. **Dowód, że czysty build = najlepszy:** harness back-to-back z przeplotem (`:40-43`).
   - Tak: topka-q70 staged copy i bramka md5 przed podmianą ([[2026-11-09-wdrozenie-topka-q70]]).
6. **Publikacja** (`:45-56`):
   - branch od aktualnego main;
   - nie kasować gałęzi z przypiętym commitem;
   - commitować dowody (JSON bramek, launch + hash, logi, próbki pamięci, PLAN/THEORY/ledger);
   - grep na sekrety, ścieżki domowe i maile;
   - README mówi, które liczby są z bramek, a które z harnessu.

   U nas: grep na IP i sekrety w lincie wiki. **Do przyjęcia:** rozdzielać w kartach strony liczby z bramki od liczb z harnessu.
7. **Karta wyników:** mediany, nie najlepsze runy; „było X → jest Y (+Z%)”; oznaczać zimne i ciepłe (`:58-64`). Tak (reguła właściciela baseline → teraz → %).

**Format raportu z PROMPT.md** (`:50-77`): tabela „metryka | baseline | teraz | **sufit** | jak mierzone”, potem co dało zysk, co ogranicza (z dowodem: profil, akceptacja per głębokość, % sufitu), znane ograniczenia, zmieniony stan systemu, czego nie zweryfikowano. **Przyjmujemy kolumnę „sufit”** do naszych raportów i notatek eksperymentów.

## Powiązane
- [[skill-io-przeglad]]
- [[2026-11-09-wdrozenie-topka-q70]]
- [[final-recipes-nvidia]]
- [[KOLEJKA-TESTOW]]
