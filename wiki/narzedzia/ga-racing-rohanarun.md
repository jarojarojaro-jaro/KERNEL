---
typ: narzedzie
tags: [narzedzia, kernele, sweep, statystyka, autoresearch, telegram]
aktualizacja: 2026-11-18
zrodlo: https://x.com/RohanArun/status/2122872101866746135 (Telegram „gpu”, 2026-11-18); github.com/rohanarun/Auto-research-agent @ `9367733` (PR #22 `7ecb410`, #23), benchmarks/ga/{README.md,engine.py,torch_gpu.py,daytona.py}; demo uruchomione tutaj 2026-11-18; poprzednio R63e §2.2–2.4 (`0230468`)
status: aktualne
---
# GA z wyścigami (Rohan Arun, Open Kernel Challenge): statystyczny wybór wariantu kernela, bez zależności

**Silnik genetyczny bez zależności (Python, 847 linii, MIT) do wyboru wariantu kernela. Działa tak:**
- warianty („geny”) per kształt („komórka”) ścigają się w sparowanych blokach pomiarowych;
- odpada wariant, który przegrywa statystycznie;
- zwycięzca zostaje mistrzem dopiero po potwierdzeniu na świeżych danych.

**Delta od R63e:** wtedy był to tylko opis w tweetach, teraz jest kod. Demo działa u nas na CPU w 1,4 s, ale jego czasy są syntetyczne. Bierzemy statystykę i odporność na awarie do naszych sweepów wariantów; wyników Open Kernel Challenge nie da się zweryfikować.

**Algorytm** (`benchmarks/ga/README.md`, `engine.py`):
1. **Generacja 0:** wszystkie warianty startowe per komórka, eliminacja sukcesywna. Miara: średni log(czas / czas najlepszego) w sparowanych blokach. Odniesieniem w bloku jest mediana żywych wariantów, więc wspólny szum maszyny się znosi. Wariant przeżywa, gdy różnica < max(3 × SE, 0,2%).
2. **Potwierdzenie na świeżych wejściach** względem bazy: mistrzem zostaje wariant z rel < 0,997 i górną granicą 95% CI < 1,0. Inaczej zostaje baza.
3. **Wspinaczka:** mutanty (≤ 3 na komórkę i generację) przeciw obecnemu mistrzowi; przechodzą przy różnicy < −max(2,5 × SE, 0,3%), potem ta sama bramka potwierdzenia.
4. **Stan monotoniczny:** mistrza zastępuje tylko potwierdzona poprawa.
5. **Odporność na awarie:** wariant ryzykowny trafia do `pending` przed budową. Gdy proces padnie, sterownik czarnolistuje dokładnie ten wariant i startuje od nowa. Zapis stanu atomowy.
6. **Adapter** dostarcza komórki, geny, build z kontrolą poprawności, sparowane pomiary (losowa kolejność, czyszczenie cache poza pomiarem) i potwierdzenie. Gotowe: `torch_gpu.py` (CUDA i Apple MPS) oraz zdalny H200.

**U nas a oni:**

| element | my | GA |
|---|---|---|
| sweep wariantów (FA D256 wariant 83, MMQ, kafle) | [[sweep-wariantow-kernela]]: siatka + ręczny wybór | eliminacja + wspinaczka, automatycznie |
| szum | ABBA, A/A, mediany ([[xtxbench-szybki-ab]]) | log-ratio do mediany żywych w bloku + SE |
| bramka | ≥ 3–5% end-to-end, md5 | ≥ 0,3% per kernel, CI < 1 na świeżych danych |
| awaria w trakcie | ręcznie (PM4 → reset karty) | `pending` → czarna lista wariantu |

**Lekcje:**
- Mediana żywych wariantów jako odniesienie w każdym bloku to tańsza kontrola dryfu niż przeplot ctl-NEW-ctl, gdy wariantów jest wiele.
- Mała bramka per kernel (0,3%) może się sumować, ale do wdrożenia nadal obowiązuje nasz próg end-to-end i md5.
- **Ryzyko:** samodzielny automat z `pending → restart` zakłada, że awaria = śmierć procesu. Na XTX awaria może oznaczać reset GPU ([[lekcja-pm4-zamienia-fault-w-reset]]). Taki sweep tylko z `GGML_HIP_PM4=0`, przez `run-jobs.sh`, nigdy bez nadzoru na produkcyjnej karcie.

**Działa na:** każdym GPU, bo adapter mierzy czas. Gotowe adaptery: NVIDIA CUDA i Apple MPS; na AMD (HIP) i Intelu trzeba napisać własny adapter, np. wokół `test-backend-ops -o perf`. Test: K-121.

## Przegląd 2026-11-24 (nauka, nie tylko prędkość)
Dotyczy wcześniejszego wiersza o tym repo (`0230468`, PR #6/#9, R63e §2.2–2.4). Werdykt „wiersze Gemini to nie pomiary agenta; PR #9 dobre reguły” mówił tylko o liczbach. Repo i tweety autora to jednak opis całego procesu pracy z agentami, a my prowadzimy podobny proces (omp, podagenci, Kernel + Gemini, kolejka GPU):
- **Kolejka GPU:** u nich hooki pilnują, żeby robotnicy nie stali i GPU było zajęte w 100%. Nasza `run-jobs.sh` (FIFO z biletami, stop przy page fault) stawia na bezpieczeństwo karty, a nie na zajętość; miary zajętości kolejki nie znalazłem `[INFERENCE]`.
- **Koordynator:** autor pisze, że człowiek jako koordynator dał 2× szybszy postęp niż koordynator-AI, a najwolniejszym ogniwem jest przegląd człowieka pod kątem oczywistych błędów (63e:186-192). U nas to ten sam wzorzec: JARO + bramki review, a Gemini bez bramki zbudował Enigmę Turbo z zielonymi testami i bełkotem ([[enigma-turbo-gemini-2026-11-20]]).
- **Przed pomiarem:** mały model statystyczny („surogat”) do shortlisty i automatyczne odrzucanie kombinacji niemożliwych fizycznie. U nas jest tylko to drugie: [[physics-floor-check]].
- **Benchmark „historical recovery”** (`benchmarks/PROTOCOL.md`): agent dostaje snapshot kodu sprzed znanej poprawy, 30 min i GPU przez zaufany dispatcher. Tanio dałoby się tak sprawdzać naszych agentów: odtworzyć znaną łatkę z historii topki i zmierzyć, czy ją znajdą.
- **Antywzorzec:** kryterium sukcesu zmienili po publikacji wyników (z „95% dolna granica ≥ 98%” na „> 1.01×”). To przesuwanie bramki po zobaczeniu danych; bramkę trzeba zapisać przed pomiarem.
- **PR #9:** zasadę „nie powtarzaj niezmienionego kodu, licząc na szum” i hash źródła przy każdym wyniku dalej mamy tylko w fabryce. W `spec_sweep.jsonl` hasha buildu brak (`qwen-opt/spec_sweep.py`).

## Powiązane
- [[sweep-wariantow-kernela]]
- [[xtxbench-szybki-ab]]
- [[skill-io-metodyka]]
- [[KOLEJKA-TESTOW]]
