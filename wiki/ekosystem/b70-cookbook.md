---
typ: ekosystem
tags: [ekosystem, intel, serwowanie, metodologia, spekulacja, dwie-karty]
aktualizacja: 2026-11-24
zrodlo: https://github.com/SergiioB/intel-arc-pro-b70-inference-cookbook (MIT, push 2026-11-23) — README.md, docs/WHAT-WORKED.md (stan 2026-11-22), docs/DO-NOT-REPEAT.md; Telegram „gpu” 2026-11-19
status: aktualne
---
# Intel Arc Pro B70 inference cookbook (SergiioB): przepisy z dowodem, rejestr zamkniętych prób i parytet spekulacji

**Najcenniejsza tu jest dyscyplina zapisu, nie 1,3–1,5 × z drugiej karty: każdy wiersz z drafterem mówi, czy drafter zmienia odpowiedź greedy, a każda zamknięta próba ma warunek ponownego otwarcia.**

## Co to jest
- Przepisy dla Intel Arc Pro B60/B70: vLLM XPU, llama.cpp SYCL, EXL3-XPU i TensorFold. Do tego launcher (`b70-launcher`, `recipes.json`), `scripts/doctor.py` (sprawdzenie karty i hosta przed startem) i skill dla agenta do strojenia na Intelu.
- Jedno źródło liczb: `data/benchmarks.v1.json`. Tabele w dokumentach (`BENCHMARK-CATALOG.md`) są z niego generowane (`README.md`, sekcja „Reproduce and operate”).

## Liczby, które coś zmieniają u nas
- **Spekulacja nie jest automatycznie bezstratna:** EXL3 + MTP3 zmienia odpowiedź greedy w 27% z 329 stałych zadań (README, opis repo). Dlatego każdy wiersz ze spekulacją ma kolumnę „parytet”. TensorFold + DFlash2 daje 128 t/s z wyjściem bajt w bajt jak bez draftu (`WHAT-WORKED.md`).
- **Bateria dokładnych odpowiedzi:** checkpoint GPTQ odpowiada 30 zamiast 14 na `sum(i*i for i in range(4))`, a GGUF Q4_K_M z tego samego źródła 59 zamiast 60 na 9×7−3 (`WHAT-WORKED.md`, „Next decisions” p. 1). Smoke „czy brzmi dobrze” tego nie łapie.
- **Dwie karty:** dwa niezależne serwery dają 2 × łącznej przepustowości. Jeden strumień na dwóch kartach daje 1,3–1,5 ×. Przy 4 strumieniach dwa serwery jednokartowe zrobiły 159–161 t/s, a jeden serwer dwukartowy 129–130. Domyślnie więc „serwer na kartę”.
- **Ciepłe tury:** 250K w kolejnej turze w 1,1–1,6 s zamiast 205 s (wznowione = świeże).

## Porównanie z naszym odpowiednikiem
- **Rejestr zamkniętych prób:** `DO-NOT-REPEAT.md` ma 40 pozycji. Każda ma wynik z kształtem pomiaru, przyczynę („nieznana”, gdy nie wiadomo), zakres i warunek ponownego otwarcia. Nasz odpowiednik to [[wyniki-negatywne]] i werdykty KILL w notatkach. Ma liczby i powód, ale nie ma zakresu ani warunku powrotu, więc „nie dla nas” zamyka temat na zawsze. Ten sam błąd przy ocenie źródeł opisuje [[lekcja-uczymy-sie-nie-tylko-predkosc]].
- **Jedno źródło liczb:** u nas liczby żyją ręcznie w REKORDY, ZRODLA i notatkach i rozjeżdżają się (przegląd ZRODLA 24.11). Oni generują tabele z jednego JSON.
- **Dwie karty (K-107):** ich wynik potwierdza wariant (a) „dwa serwery dla roju agentów” jako domyślny. Podział jednego strumienia to osobna dźwignia z małym zyskiem.
- **Parytet spekulacji:** Enigma pokazuje `sameOutput` (md5 greedy, `app/engine/CONTRACT.md`, „Optymalizacja”), ale tylko na kilku opowiadaniach z benchmarku (`DECODE_TASKS`, 4 pary PL/EN, `app/engine/src/server/bench.ts:70-87`). 27% rozjazdów u nich mówi, że przy każdej zmianie spekulacji potrzebny jest większy, stały zestaw zadań (u nich 329), także z kodem i liczbami.

## Co bierzemy
1. Pola „zakres” i „otwórz ponownie, gdy” w [[wyniki-negatywne]] i przy każdym KILL.
2. Kolumna „parytet z greedy” przy każdej liczbie ze spekulacją (topka, Enigma).
3. Bateria dokładnych odpowiedzi (arytmetyka, krótki kod) jako bramka kwantu w Enigmie, obok KLD.
4. `doctor.py` jako wzór wstępnej diagnostyki w aplikacji.

## Powiązane
- [[skill-io-sufity]]
- [[skill-io-przeglad]]
- [[tensorfold]]
- [[inference-stack]]
- [[KOLEJKA-TESTOW]]
