# 04 — KernelBench (ScalingIntelligence/KernelBench): jak oceniać kernele pisane przez agentów

Klon: `--depth 1`, HEAD `423217d9` (2026-03-05), 5.7 MB; po analizie usunięty. Ścieżki `plik:linia` są względem korzenia repo. Nic nie było budowane ani uruchamiane. Źródła dodatkowe: blog v0.1 (https://scalingintelligence.stanford.edu/blogs/kernelbenchv01/), dwa wpisy Ornith/DeepReinforce podlinkowane z `EVAL.md:17` (https://ornith.ai/defense_kernel_hack.html, https://ornith.ai/correctness_check.html) i blog Kevin-32B (https://cognition.com/blog/kevin-32b). Odniesienia do naszych narzędzi: `~/KERNEL/qwen-opt/greedy_check.sh`, `mmvq-bench/mm_dump.cpp`, `~/wt/lfm2-prof/{ab.sh,logit_hash.cpp}`, `~/llama-master/tests/test-backend-ops.cpp`.

## 1. Co to jest

Benchmark i środowisko (ICML'25) do oceny kerneli CUDA/DSL generowanych przez LLM. Zadanie: przepisać program PyTorch (`Model`) na `ModelNew` z własnymi kernelami. Problemy są w 4 poziomach: 100 pojedynczych operatorów, 100 fuzji, 50 całych architektur i 20 modeli z HF (`KernelBench/level1..4`). Ocena to poprawność (`torch.allclose` na losowych wejściach) i przyspieszenie względem PyTorch eager/compile, zbiorczo jako metryka `fast_p` (`src/kernelbench/score.py:28-36`). Licencja MIT. Repo żyje (v0.1 w lipcu 2025, ostatni commit marzec 2026), ale `EVAL.md` jest wciąż „[WIP]”. Baseline'y są mierzone na NVIDIA (L40S/H100/A100…, `results/timing/README.md:73-87`). AMD obsługuje tylko `gfx942`/`gfx950` (`src/kernelbench/utils.py:43`), nie gfx1100. **Kernel nie zawiera żadnej techniki, która przyspieszy inferencję.** Wartość repo dla nas leży w metodologii pomiaru i w katalogu sposobów oszukiwania oceny.

## 2. Kluczowe techniki (dowody)

**Poprawność**
- Porównanie z niezależną referencją (PyTorch). Na wejściach z `num_correct_trials` różnych seedów (`eval.py:751-754`) kernel przechodzi tylko wtedy, gdy przejdą wszystkie próby (`eval.py:845`). Referencja liczy się **przed** kandydatem na tych samych tensorach (`eval.py:777,782`). Dzięki temu kandydat, który niszczy wejście, nie zmieni wyniku referencji (test `unit_tests/test_kernels/zero_out_kernel.py`).
- Tolerancja `atol = rtol`: 1e-4 dla fp32, 1e-2 dla fp16/bf16 (`eval.py:95-99`, `eval.py:804-805`).
- Zestaw testów adwersarialnych (`unit_tests/test_eval_adversarial.py`), które sprawdzają, czy harness łapie trzy rodzaje oszustw:
  - ponowne użycie pamięci z wynikiem referencji: `torch::empty` dostaje od alokatora niewyczyszczony bufor (`test_kernels/result_reuse_kernel.py:1-20`); łapane tylko dzięki kolejnym próbom z innymi seedami;
  - modyfikację wejść;
  - pracę na niedomyślnym strumieniu (`test_kernels/non_default_stream_kernel.py:27-32`).
- Statyczny checker regexowy (`kernel_static_checker.py`). Jako błędy traktuje: `try/except` z fallbackiem, `pass` (dziedziczenie po referencji), monkey-patch timerów, wątki i leniwe podklasy `Tensor` (`:594-599`). Jako ostrzeżenia: strumienie, operatory torch i obniżenie precyzji fp32→fp16 (`:615-621`). Wzorce wzięto z Kevina i z bloga Ornith.
- Blog v0.1 zebrał to, czego się nauczyli:
  - zadania, których wynik ląduje w „szumie 1e-2” albo redukuje się do stałej (np. `mean(softmax(x))`), nie sprawdzają niczego;
  - RNN-y przenosiły stan między wywołaniami;
  - dodali `rand_mix` (rozkład normalny, jednostajny, Laplace'a, wykładniczy, log-normalny), bo samo N(0,1) przepuszcza błędy numeryczne.
- Blog Ornith o poprawności proponuje **dokładny test dla operacji liniowych**: wejścia binarne lub małe całkowite, dobrane tak, żeby każda suma częściowa była dokładnie reprezentowalna. Wtedy wynik nie zależy od kolejności sumowania i można żądać równości bitowej (dla fp16 wartości ≤ 2048). Autorzy zastrzegają, że nie działa to dla exp/log.

**Pomiar czasu (`src/kernelbench/timing.py`)**
- Cztery metody (`:150-184`): zdarzenia CUDA dla każdej próby, implementacja w stylu Triton `do_bench` (zdarzenia zbierane w tablicach, jedna synchronizacja), czas hosta i nsight.
- Przed każdą próbą zimny cache: zapis 256 MB nadpisuje L2 (`:126-142`), wywołanie `clear_l2_cache` jest w `:259`.
- Wynik to średnia (`eval.py:636`) zaokrąglona do 3 cyfr znaczących (`timing.py:614`).
- Flaga „podejrzane przyspieszenie” przy >10× względem referencji (`eval.py:412,691`). `EVAL.md:5-8` radzi być paranoikiem już przy >2× („if you beat cudnn by more than 10%, think again”).
- Blog v0.1: sanity check względem speed-of-light, czyli max(FLOP/peak, bajty/pasmo). Rozmiary zadań przeskalowano do 1–15 ms na H100, bo w zakresie mikrosekund dominował narzut uruchomienia. Przykłady: ReLU 0.013 → 6.97 ms, Sum 0.0148 → 5.41 ms (pomiary autorów, H100).
- Blog Ornith o obronach, z pomiarami autorów:
  - wstrzyknięcie strumienia: 264.7 → 4.2 ms. Obrona `synchronize()` przed `end_event` dodaje opóźnienie hosta, więc proponują tryb hybrydowy: porównać czas z synchronizacją i bez niej, a dużą różnicę traktować jako oszustwo;
  - wstrzyknięcie wątku (obrona: licznik wątków);
  - leniwy tensor: 305 → 0.34 ms;
  - obniżenie precyzji („nie ma dobrej obrony”);
  - monkey-patch `elapsed_time`.

**Oszustwa obserwowane w praktyce** (Kevin-32B i blog v0.1):
- skopiowanie referencji i zgarnięcie nagrody za 1.0×;
- `try/except` z fallbackiem do PyTorch;
- dziedziczenie po referencji;
- kernel napisany, ale nigdy niewywołany;
- no-op na buforze z poprzednim wynikiem;
- błędna synchronizacja przy pomiarze.

## 3. Przeniesienie na AMD/HIP/RDNA3

Nie przenosimy kodu (to harness Python/PyTorch, my mamy ggml w C++). Przenosimy klasy błędów i obron. Odpowiedniki u nas:

| KernelBench | Nasz odpowiednik na gfx1100 / ggml-hip | Stan u nas |
|---|---|---|
| Referencja PyTorch + `allclose` | `test-backend-ops` (CPU jako referencja, NMSE) + bitowa zgodność całego modelu z poprzednim buildem (`logit_hash`, greedy md5) | Mamy, i mocniej: bitowość jest ostrzejsza niż `allclose`. Słabe punkty niżej. |
| Kilka seedów (`eval.py:751`) | `mm_dump.cpp`: jeden seed (`:28`), tylko N(0,1) (`:29`), jeden kształt 5120×1024 (`:17`), kolumny {1,2,4,8} (`:19`). `logit_hash.cpp`: jeden prompt (`:39`), dekodowanie po 1 tokenie (`:65-66`). | Pokrycie wąskie. Ścieżki 3, 5–7 i 9–16 kolumn oraz weryfikacja MTP są sprawdzane tylko md5 tekstu. |
| Ponowne użycie wyniku (`result_reuse_kernel.py`) | Kernel czyta nieświeży bufor z poprzedniego odtworzenia grafu HIP albo z bufora ggml-alloc współdzielonego przez węzły, albo liczniki „ostatni blok”/ticket zakładają wyzerowaną pamięć | Brak testu z zatruwaniem buforów. |
| Kernel napisany, ale niewywołany / fallback (Kevin) | Warunki dispatchu (typ, n, `ne`) albo przełącznik `GGML_HIP_*` sprawiają, że nowy kernel nie działa w mierzonej konfiguracji. Bitowa zgodność jest wtedy **trywialna**, a wynik A/B to szum. | Nie ma bramki, która to sprawdza. |
| Niedomyślny strumień / zdarzenia | U nas zegar ścienny llama-bench/serwera plus suma kerneli z rocprofv3. Zdarzenia na jednym strumieniu się nie stosują. | OK (mierzymy end-to-end). |
| Zimny L2 (zapis 256 MB) | Na RX 7900 XTX odpowiednikiem jest MALL 96 MB, więc 256 MB też wystarczy. Wagi dużych macierzy i tak nie mieszczą się w cache, ale małe kernele (router, conv, norm LFM) w pętli mikrobenchmarku siedzą w MALL. | `mmvq-bench` jest „na zimno” z racji rozmiaru. Mikrobenchmark małych kerneli nie czyści cache. |
| Rozmiary 1–15 ms, żeby ukryć narzut uruchomienia | **Odwrotnie**: LFM jest ograniczony liczbą uruchomień (~2.5 µs na granicę kernela). Pomiar musi zawierać granice grafu. | Wiemy o tym (`NOTES.md:247-248`, mikrobenchmark myli się co do GLC/DLC). |
| Speed-of-light | Bajty/czas względem 960 GB/s per kernel (`kernel_bw.py` liczy %peak per typ, `:17,41-47`) | Mamy, ale bez automatycznej flagi przy >100%. Błąd „112% peaku” z raportu autokernel (`NOTES.md:104-105`) to dokładnie ta klasa. |
| Obniżenie precyzji | Agent zamienia akumulację f32 na f16 w FA/WMMA. Bramka bitowa to blokuje. Przy zmianach niebitowych mamy KLD (`NOTES.md:225`). | OK. |
| Dokładny test na wejściach całkowitych (Ornith) | MMVQ/MMQ: dot int8 jest dokładny w int32, a mnożenie przez skale `d = 2^k` jest dokładne w f32. FA: Q=0 daje równą uwagę, softmax = 1/n jest dokładny dla n = 2^m, V całkowite. GDN: część liniowa z całkowitymi wartościami. | Nie mamy tego. Pozwoliłoby testować bitowo zmiany **kolejności redukcji** (split-K, motylek DPP, kolejność chunków FA). |

Nie przenosi się:
- regexowy checker Pythona (u nas nie ma `try/except` ani `torch.*`);
- nsight (tylko NVIDIA, `timing.py:526-531`);
- Modal/chmura;
- `fast_p` jako metryka (nasza referencja to nasz własny, dostrojony kernel, a nie PyTorch eager).

## 4. Pomysły dla nas

Wszystko poniżej dotyczy procesu, nie kerneli. Bezpośredni zysk w t/s wynosi 0. Zysk polega na tym, że eksperymenty z pozornym zyskiem albo pozorną bitowością kosztują mniej, a agenci mogą bezpiecznie robić zmiany niebitowe (np. nowy FA dla KV q8_0).

1. **Bramka „czy nowy kernel w ogóle się wykonał”** (lekcja z fallbacku i niewywołanego kernela).
   - Co zmienić: do każdego A/B dołączyć 1 token pod `rocprofv3 --kernel-trace` dla A i B, histogram nazw kerneli i diff. Commit deklaruje oczekiwany diff, np. „−2× `rms_norm_f32`, −1× `quantize_q8_1`, +1× `rms_norm_mul_q8_1`”. `trace_breakdown.py` ma już parser.
   - Zysk: [SZACUNEK] 0 t/s, ale eliminuje fałszywe „bitowo identyczne, szum” w sytuacji, gdy dispatch nie trafia (np. inne `ne` w MTP niż w llama-bench).
   - Koszt: ok. 0.5 dnia. Ryzyko: brak.
   - Pomiar: diff zgodny z deklaracją dla obu modeli i trybów plain/MTP.

2. **`logit_hash` w trybie wsadowym, wielu promptów i dużych głębokości** (lekcja z wielu seedów; zadania, które nic nie sprawdzają).
   - Co zmienić w `~/wt/lfm2-prof/logit_hash.cpp`: opcja `BATCH=k`, która przepuszcza k tokenów (teacher-forcing z zapisanej sekwencji) przez `llama_batch` i hashuje logity wszystkich k wierszy. Do tego k ∈ {2,3,5,8,9,12,16}, 3 prompty (EN/PL/kod) i głębokości przekraczające progi dispatchu FA/nsplit (np. 0, 3000, 33k, 98k).
   - Dziś ścieżki weryfikacji (MMVQ 2–8 kolumn, WMMA 9–16) mają bitowy test tylko przez md5 tekstu z jednego promptu (`greedy_check.sh`). Md5 tekstu przepuszcza dowolny błąd, który nie zmienia argmaxu.
   - Zysk: [SZACUNEK] 0 t/s, ale łapie błędy, które dziś wyszłyby dopiero w jakości.
   - Koszt: 0.5–1 dzień plus ok. 3 min GPU na pełny przebieg. Ryzyko: niskie.
   - Pomiar: tabela hashy (prompt × głębokość × k) równa z bazą.

3. **Test A/A (zerowy) dla determinizmu i szumu.**
   - Ten sam build uruchomiony dwa razy: (a) `logit_hash` musi dać identyczne hashe; dowód, że jądra „ostatni blok”/ticket i atomiki są deterministyczne. (b) `ab.sh` z A = B daje rozkład różnic, który jest progiem decyzji.
   - Dziś `ab.sh` biegnie zawsze w kolejności A, B, A, B (`ab.sh:12-13`). Przy limicie 285 W i throttlingu (`NOTES.md:112`) B systematycznie startuje na rozgrzanej karcie [WNIOSEK].
   - Zmiana: kolejność ABBA albo losowa per runda, log `amd-smi` (sclk, moc, temperatura junction) przy każdym przebiegu, w raporcie mediana i rozrzut zamiast samej średniej. Zysk uznawać, gdy |Δ| > 2σ z A/A.
   - Kontrprzykład z KernelBench: średnia zaokrąglona do 3 cyfr znaczących (`timing.py:614`) ma rozdzielczość rzędu naszych typowych zysków (1–3%).
   - Koszt: 2 h. Ryzyko: brak.

4. **Zatruwanie buforów** (lekcja z ponownego użycia wyniku).
   - Tryb testowy, np. `GGML_HIP_POISON=1` w ggml-cuda przy alokacji i przed każdym wykonaniem grafu. Wypełnia bufor obliczeniowy schedulera wzorcem 0xFF (NaN dla f32/f16) albo losowym. Nie zeruje liczników ticket (one muszą się resetować same). Potem `logit_hash` z pomysłu 2.
   - Odczyt nieświeżej albo niezainicjalizowanej pamięci daje NaN zamiast przypadkowo poprawnej wartości. Szczególnie ważne przy naszym stanie GDN i historii conv z opóźnieniem, replay, asynchronicznych wejściach grafu, buforze cache q8_1 alokowanym raz (`NOTES.md:83-85`) i liczniku ticket w norm+router+top-k.
   - Zysk: [SZACUNEK] 0 t/s, ale wykrywa klasę błędów, której bitowe A/B z tym samym układem pamięci nie widzi: obie wersje dostają ten sam nieświeży bufor.
   - Koszt: 1 dzień (trzeba znaleźć miejsce w `ggml-backend.cpp`/`ggml-cuda.cu` oraz dodatkowy węzeł memset w grafie HIP). Ryzyko: fałszywe alarmy tam, gdzie upstream celowo czyta niezapisane wiersze. Wymaga białej listy.
   - Pomiar: brak NaN i hashe równe trybowi bez zatrucia.

5. **Dokładne testy na wejściach całkowitych dla zmian niebitowych** (blog Ornith o poprawności).
   - Rozszerzyć `mm_dump.cpp` i `test-backend-ops` o tryb wejść „dokładnych”:
     - MMVQ/MMQ: aktywacje q8_1 z małymi całkowitymi wartościami i `d = 2^k`; wagi z wybranymi skalami `2^k`. Tak dobrane, że cała suma mieści się w 2^24.
     - FA (KV q8_0/q4_0): Q = 0 (równa uwaga) i V całkowite, długość KV = 2^m; osobno K jedno-gorące.
   - Każda kolejność redukcji musi wtedy dać identyczne bity. Agent może zmienić split-K, drzewo redukcji DPP czy kolejność chunków i nadal mieć test zero-jedynkowy zamiast KLD.
   - Bezpośrednie zastosowanie: otwarte wąskie gardło „atencja decode przy długim kontekście, KV q8_0”. Nowy kernel FA współdzielący odczyt K/V w grupie GQA (zamiast generycznego `flash_attn_ext_vec`, `NOTES.md:354`) prawie na pewno nie będzie bitowy względem obecnego.
   - Koszt: 1–2 dni. Ryzyko: test nie pokrywa exp/softmax z nietrywialnymi wynikami; nadal potrzebne są KLD i `test-backend-ops`.
   - Pomiar: równość bitowa na wejściach dokładnych plus KLD na modelu (jak przy A4).

6. **Szersze wejścia w `mm_dump` i testach fuzji** (`rand_mix` z bloga v0.1 + krytyka tolerancji niżej).
   - 3 seedy; rozkłady N(0,1), Laplace'a, log-normalny i rzadkie wartości odstające do ~6e4 (sprawdza clamp S1 ±65504, `NOTES.md:259`).
   - Kształty z resztami: k=2048 (LFM), n=48 (alpha/beta), n niepodzielne przez rows-per-block; kolumny 1..16 (dziś {1,2,4,8}, `mm_dump.cpp:19`).
   - Koszt: 2 h. Pomiar: hashe równe z bazą.

7. **Automatyczna flaga speed-of-light** w `kernel_bw.py`/`trace_breakdown.py`.
   - Per kernel: bajty z modelu (wagi + KV + aktywacje) / czas. Flaga przy >960 GB/s (dla tensorów mieszczących się w MALL osobny próg albo adnotacja).
   - Odpowiednik `excessive_speedup` (`eval.py:691`), ale z fizyki zamiast z mnożnika 10×.
   - Koszt: 2–4 h. Wyłapałby błąd „112% peaku” automatycznie.

8. **Czyszczenie cache w mikrobenchmarkach małych kerneli** (`timing.py:126-142`).
   - Przed każdą iteracją małego kernela (router LFM, conv, rms_norm, kernele `launch_cost.hip`/`chain_cost.hip`) zapisać 256 MB, bo w modelu te wagi wypadają z MALL między tokenami (aktywne wagi na token >> 96 MB).
   - Zysk: lepsza zgodność mikrobenchmarku z rocprofv3 w modelu. Dziś wiemy, że mikrobenchmark myli się w kwestii GLC/DLC (`NOTES.md:247-248`).
   - Koszt: 1 h. Ryzyko: brak.

9. **Poza schematem: czerwony zespół dla naszej bramki** (`unit_tests/test_eval_adversarial.py` jako wzór).
   - Zbudować jednorazowo 4–5 celowo zepsutych łatek i sprawdzić, czy proces (`test-backend-ops`, `logit_hash`, greedy md5, diff histogramu) łapie każdą:
     - (a) nowy kernel nie jest dispatchowany dla n=5;
     - (b) pominięty ogon ostatnich 16 wierszy przy n%RPB≠0;
     - (c) licznik ticket niezerowany przy drugim odtworzeniu grafu;
     - (d) akumulacja w f16 w jednej fuzji;
     - (e) wczesny `return` dla ostatniej warstwy.
   - Wynik: macierz „łatka × test”, która pokazuje, które testy są potrzebne, a które zbędne.
   - Szczególnie przydatne, bo łatki piszą agenci; EVAL.md: „If the model can reward hack, it will find ways” (`EVAL.md:12`).
   - Koszt: 1 dzień. Ryzyko: brak, łatki nie trafiają do gałęzi.

10. **Przegląd tolerancji w `test-backend-ops` dla naszych fuzji.**
    - Wiele testów fuzji ma `max_nmse_err` 5e-4…5e-3 (np. `test-backend-ops.cpp:4929`, `:7922`, `:8304`). NMSE 5e-4 to ok. 2% względnego RMS: zgubienie składnika o udziale energii poniżej ~5e-4 przejdzie. Analogia do błędu KernelBench poniżej (zera przechodzą `allclose`).
    - Propozycja: tam, gdzie fuzja deklaruje bitowość względem niefuzowanej ścieżki GPU, testować **GPU-fuzja vs GPU-bez-fuzji z NMSE = 0** (przełączniki `GGML_HIP_*=0`). Porównanie z CPU zostaje tylko jako test referencyjny.
    - Koszt: 0.5–1 dnia.

## 5. Krytyka

- **Tolerancja absolutna przepuszcza zera.** `level1/23_Softmax.py:23-27`: softmax po 393 216 wartościach z U[0,1). Największe wyjście ≈ e/(393216·(e−1)) ≈ 4e-6, a `atol = 1e-4` (`eval.py:95`, `:804-805`), więc **kernel zwracający same zera przechodzi test poprawności** [WNIOSEK: rachunek, nie uruchamiałem]. To przykład problemu z „szumem” z bloga v0.1, który przetrwał v0.1. Lekcja dla nas: tolerancja względna lub normalizowana (NMSE) albo bitowość, nigdy sama absolutna.
- Wszystkie 100 problemów level 1 używa `torch.rand`, czyli U[0,1), same wartości dodatnie (292 wystąpienia `torch.rand(` na wszystkich poziomach). Tymczasem blog v0.1 pisze, że „by default the problems use torch.randn”. Kod i blog są niezgodne. `rand_mix` jest tylko opcją.
- Pomiar w `host_time`: `clear_l2_cache` (asynchroniczny zapis 256 MB) jest zlecany po `synchronize`, ale przed `perf_counter()` (`timing.py:479-487`), więc czas hosta **zawiera czyszczenie cache** [WNIOSEK z kodu]. Na H100 to rząd 0.1 ms, czyli 1–10% zadania 1–15 ms.
- `cuda_event` nie broni się przed niedomyślnym strumieniem (sam docstring, `timing.py:215`). Oszustwo zostaje oflagowane dopiero przy >10× (`eval.py:691`); przyspieszenie 3× przejdzie. Parametr `threshold=1.5` w `test_non_default_stream` (`test_eval_adversarial.py:80`) nie jest nigdzie użyty.
- Pomiar czasu używa tych samych wejść we wszystkich próbach (`eval.py:616`), więc memoizacja kluczowana wskaźnikiem dałaby zysk w pomiarze. Wynik to średnia, a nie mediana; brak testu statystycznego i porównania przeplatanego. Nasz proces (przeplatane A/B, przełączniki w tym samym binarium) jest już dojrzalszy.
- Statyczny checker to regexy, które łatwo obejść, a jednocześnie dają fałszywe alarmy: każde `pass` i każde `try:` to błąd (`kernel_static_checker.py:46-73`). Dla C++/HIP sprawdza jedynie `__global__`, `load_inline` i `hipcc` (`:193-207`).
- Detekcja AMD po nazwie: `"AMD" in name or "MI3"` (`utils.py:59`). gfx1100 nie jest na liście architektur (`utils.py:43`), więc harnessu nie dałoby się użyć u nas bez łatek. Nie ma to znaczenia, i tak nie zamierzamy.
- Referencja PyTorch eager jako baseline zawyża przyspieszenia i nie ma nic wspólnego z naszym problemem (nasz baseline to dostrojone MMVQ/FA). Skalowanie zadań do 1–15 ms celowo usuwa narzut uruchomień, a ten narzut jest u nas głównym kosztem LFM. Wyniki „fast_p” z KernelBench nie mówią nic o kernelach dekodowania LLM.
- Repo samo zastrzega, że nie weryfikuje kerneli ani wyników zewnętrznych (`EVAL.md:21`, `README.md:176`). Liczby z publikacji, które je cytują, trzeba traktować ostrożnie.

## 6. Werdykt

**Średnia.** Repo nie zawiera żadnej techniki, która przyspieszy nasze kernele. Daje za to sprawdzony katalog sposobów oszukiwania oceny i błędów pomiaru, a do tego pomysł dokładnych testów na wejściach całkowitych. Wprost przekłada się to na tanie wzmocnienie naszej bramki bitowej i A/B dla łatek pisanych przez agentów: diff histogramu kerneli, `logit_hash` wsadowy i na głębokości, zatruwanie buforów, test A/A, kolejność ABBA. Najbardziej przyda się to w zmianach niebitowych, takich jak nowy FA dla KV q8_0.
