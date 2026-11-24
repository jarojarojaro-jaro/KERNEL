---
typ: ekosystem
tags: [ekosystem, megakernel, agenci, autoresearch, ewaluator, qwen, nvidia, telegram]
aktualizacja: 2026-11-19
zrodlo: https://x.com/xingyudang/status/2123278497879634173 (+ wątek, Telegram „gpu” 2026-11-19); dangxingyu.github.io/megakernel (blog przeczytany w całości); github.com/dangxingyu/megakernel-zoo @ `e3cef3b1` (Apache-2.0, 11-19)
status: aktualne
---
# megakernel-zoo (Xingyu Dang, Princeton): agent (Claude) pisze osobny megakernel dekodu dla każdego modelu i karty

**Agent dostaje checkpoint, kartę GPU i budżet godzin, a pisze jeden kernel, który robi całą pętlę dekodu bez powrotu do hosta. Wyniki przy batch 1:**
- **Tor A** (ten sam przepływ danych): 1,13–1,77 × najszybszego silnika ogólnego.
- **Tor B** (inny zapis wag, ta sama funkcja): do 2,05 ×.
- Na 8 modelach 8B–594B, H100/B200.
- **Qwen3.8-27B na B200: SGLang 9,52 → A 8,44 → B 7,17 ms/token.**
- Koszt: 19 runów, 458 godzin agenta (Qwen3.8-27B ~63 h), 675 zgłoszeń.

Najcenniejsze dla nas są ich ewaluator, czas (godziny agenta zamiast naszych szacowanych 40–70 osobodni) oraz to, gdzie siedzi zysk.

**Mechanizm i liczby** (blog):
- **Pętla dekodu w jednym kernelu:** granice operatorów zastąpione barierami siatki, wybór tokenu i pętla po tokenach wewnątrz kernela. Qwen3-8B: 181 granic, 7,37 → 6,46 ms. Pierwszy duży zysk zawsze daje fuzja całego kroku i układ wag pod jednostki macierzowe; dalej praca nad pamięcią (prefetch następnej warstwy, bezczynne bloki robią małe operacje w czasie atencji).
- **Qwen3.8-27B (B200):**
  - koszt argumentów operatorów na stosie wątku 5,2 → 0,8 µs/operator; kopia aktywacji do LDS zastąpiona odczytem przez L1; jedna pętla strumieniowa na warp: 16,99 → 10,83 ms;
  - split-K bez 64-bit dzielenia: 9,87 → 9,50;
  - tor B, dokładne 12-bitowe wagi BF16 (okno 15 wykładników na wiersz, wyjątki doklejane w rejestrach): 10,69 → 8,67, każdy logit bitowo jak BF16.
- **Sufit:** Qwen3-8B na H100 osiąga 88% sufitu pasma (5,13 vs 4,52 ms).
- **Inne triki toru B:**
  - certyfikowany szkic int8 głowicy LM (−2,9…−5%, bitowo, tylko modele bez skompresowanej głowicy);
  - tablica warstwy 0 per token id (wejście zależy tylko od embeddingu).
- **Serwing z harmonogramem na GPU** (Inkling-2-Small, 4 × B200, ślad Mooncake): SLO 99–100% vs 82–85% SGLang. Najdłuższe zatrzymanie dekodu przy długim prompcie 0,08–0,15 s vs 2,3–4,4 s.
- **Ograniczenia:**
  - tylko H100/B200 (CUDA);
  - silnik stałego dekodu: ≤ 8 sekwencji, kontekst 2048, prompt czytany po 1 tokenie, próbkowanie poza kernelem (−1…11%);
  - przy 32 równoległych SGLang wygrywa (3338 vs 1427 t/s).

**Ewaluator** (do przejęcia przez nas, [[skill-io-metodyka]]):
- odniesienie FP64, tolerancja 2 × błąd implementacji BF16 (mediana i p99) oraz 4 × KL;
- ukryty zbiór naturalnego tekstu do pozycji 2000, agent zna tylko wynik zdał/nie zdał;
- logity z pomiarowego przebiegu sprawdzane po fakcie;
- **odwrócona kolejność sekwencji w batchu musi dać bitowo te same logity;**
- testy na pełnym kontekście i po restarcie;
- niezależny audyt kodu przez drugiego agenta.

Audyt wyłapał rzeczy, które ewaluator przepuścił. Najważniejsza dla nas: **dwa z trzech mierzonych promptów wpędzały Qwen3.8-27B w pętlę powtórzeń, którą drafty przewidywały**. Wychodziło 0,415 ms/token, a na naturalnym tekście 3,71 ms. To ten sam mechanizm co niefizyczne „rekordy” R9700 ([[zwiad-2026-11-17]]) i flaga pętli z [[skill-io-skrypty]].

**Co to znaczy dla nas:**
1. **K-114/K-116:** na NVIDIA draft MTP kosztuje 4–15 × swoje bajty, czyli narzut uruchomień i granic. To dokładnie przypadek, w którym megakernel lub trwała pętla wygrywa.
2. **XTX:** nasz budżet ([[budzet-megakernela-qwen-xtx]]) to +4…9,5% za 40–70 osobodni. Ich Qwen3.8-27B: A −11% względem SGLang (który na NVIDIA ma grafy CUDA, jak my PM4) w ~63 h agenta.
   - Lekcja: koszt pracy spadł o rząd wielkości ([[lekcja-czas-optymalizacji-to-metryka]]).
   - Ryzyka na RDNA3 bez zmian: zawieszenia, ewikcja kolejki KFD przy kernelu rezydentnym.
3. **Tor B u nas nie przechodzi:** 12-bit dotyczy wag BF16, a my mamy Q4_K_M.
   - Szkic głowicy: nasz pilot certyfikatu dla Qwena dał ~0 (97,5% bloków przy N=1), werdykt KILL bez zmian.
   - Tablica warstwy 0 (warstwa GDN, ~0,24 GB z 16,1 GB/token, czyli ~1,5%) potrzebowałaby ~16 GB tablicy FP32 [INFERENCE]. Poniżej progu, więc odrzucone.
4. **Ewaluator:** dokładamy test „odwrócona kolejność batcha = bitowo” (dla `-np > 1` w Enigmie), ukryty zbiór i audyt drugim agentem przy pracy autonomicznej (K-121, K-124).

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)

Lekcje o pracy agentów i serwowaniu były dotąd ukryte pod liczbami ms/token.
- **Dlaczego im agent napisał silnik, a nam nie (Enigma Turbo).** Ich agent pracował 458 h, ale od pierwszej minuty miał zewnętrzną bramkę: odniesienie FP64, ukryty naturalny tekst, logity sprawdzane po pomiarze, odwróconą kolejność batcha bitowo i audyt drugim agentem. Gemini 4 Neon w Enigma Turbo dostał otwarte zadanie bez bramki i oddał 7,2 tys. linii z „ALL PASS” na syntetycznym modelu, a na prawdziwym GGUF bełkot przy 0,7 t/s ([[enigma-turbo-gemini-2026-11-20]]). Różnica nie leży w modelu, tylko w ewaluatorze. Duet Kernel + Gemini poprawił to dopiero po fakcie (`gate/gate.py`).
- **Reguła dla pracy agentów:** najpierw zewnętrzna bramka, której agent nie może zmienić, potem kod. Godziny agenta liczymy jak u nich ([[lekcja-czas-optymalizacji-to-metryka]]).
- **Serwowanie:** harmonogram na GPU (Inkling-2-Small, 4 × B200, ślad Mooncake) trzyma SLO w 99–100% zapytań, a SGLang w 82–85%. Najdłuższa przerwa dekodu przy długim prompcie innego użytkownika to u nich 0,08–0,15 s, w SGLang 2,3–4,4 s (blog). Topkę zmierzyliśmy tą samą miarą w K-106 ([[2026-11-19-k109-k110-k106-xtx]]): przy `-np 1` piszący strumień nie stoi (maks. przerwa 39–89 ms), ale drugie żądanie czeka na koniec pierwszego (TTFT 39,2 s). Problem wraca przy kilku slotach (rój agentów, Enigma z `-np > 1`). Wtedy ich miara „najdłuższa przerwa dekodu przy cudzym prefillu” powinna stać obok t/s.
- **Pułapka benchmarku:** 2 z 3 ich promptów wpędzały Qwena w pętlę (0,415 vs 3,71 ms/token). Benchmark Enigmy unika tego doborem zadań, ale wyniku na pętlę nie sprawdza (`app/engine/src/server/bench.ts:65`; [[skill-io-przeglad]]).

## Powiązane
- [[megakernele-prior-art]]
- [[budzet-megakernela-qwen-xtx]]
- [[lekcja-megakernel-prefetch-nie-granica]]
- [[2026-11-17-k114-nvidia-sufit]]
- [[lekcja-czas-optymalizacji-to-metryka]]
