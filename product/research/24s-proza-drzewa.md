# 24s. Drzewa draftu MTP i temperatura draftu na prozie przy T=1: sufit offline (Qwen3.8-27B, XTX, topka)

Data: 2026-10-20. Autor: podagent OptProseTree. **Wszystko na CPU**: lustro MTP `mtp_torch.py` (fp32, 2 rdzenie, nice 19), bez GPU i bez buildu. Nic nie zostało zaimplementowane w llama.cpp.
Skrypty i wyniki: `24s-drzewa/` obok tego raportu (kopia z `~/qwen-opt/tree/`). Dane pośrednie (100 MB npz) leżą w `~/qwen-opt/tree/ext{,_greedy}/`.

## 0. Werdykt

**NEGATYWNY. Żaden wariant nie osiąga progu +6% t/s na prozie, więc nie ma worktree `~/wt/tree` ani zadań GPU.**

1. **Drzewo statyczne** (ten sam kształt w każdym kroku, optymalny dla danych): najlepiej **+1.2%** netto (6 wierszy). Dziś liczony koszt wiersza to 0.85 ms (3.1% kroku), a 5. węzeł daje tylko +4.3% tokenów na krok.
2. **Drzewo dynamiczne** (w stylu EAGLE-2: kształt w każdym kroku z pewności MTP; łańcuch i liście-rodzeństwo):
   - **+3.9%** przy tych samych 5 wierszach (zmienia się tylko kształt);
   - **+4.7%** przy 6 wierszach, i to jest sufit;
   - przy T=0.8 (sampler web UI) +3.9% / +4.6%.
   - Te liczby nie uwzględniają narzutu implementacji: top-M w grafie MTP, maska przodków, stan GDN indeksowany rodzicem, przeniesienie stanu przyjętego liścia.
3. **Próg +6%** wymaga kosztu wiersza ≤ **0.57 ms** (dziś 0.85 ms) przy 7 wierszach.
4. **Temperatura draftu** (sprzężony Gumbel, `LLAMA_SPEC_COUPLED_DT`):
   - DT 0.7 daje +0.26% tok/krok względem DT 1.0, czyli szum;
   - DT 1.3 i 1.6 dają −0.6% i −1.5%;
   - zostaje DT = 1.
5. **Sprzężenie i drzewo sumują się słabo:** statyczne drzewo nad sprzężonym łańcuchem daje **+0.3%** netto.
6. **Pytanie z zadania (TensorFold, kryterium „go > 0.3”).** W pierwszej odrzuconej pozycji łańcucha-4 cel losuje 2. kandydata MTP w 29% odrzuceń na prozie (en 33%, pl 26%, en-czat 38%). Trzeciego kandydata losuje w 12%, a w 44% token celu jest poza top-6 MTP albo poza słownikiem 64k. Wartość jest na granicy progu, ale o werdykcie przesądza arytmetyka kosztu wiersza (pkt 1–3).

Implementacja drzewa dla hybrydy GDN zajmuje dni (raport 18: 10+ dni; lista prac w `qwen-opt/research/algorithms.md` §5). Nie mieści się też w regule użytkownika „≤ 20 min pracy do pierwszego testu”. Przy sufitach poniżej progu nie zaczynałem.

## 1. Metoda

- **Dane.** Faza 1 MTP (`~/qwen-opt/mtp-train/data/ext_p1`, 2026-10-12): 57 odpowiedzi celu Q4 przy samplerze GGUF (T=1, top-k 20, top-p 0.95, min-p 0.05, rozumowanie low). Tokeny celu top-32 log-prob na pozycję.
  - Proza to `pl-prose` i `en-prose`: 17 sekwencji, **17 692 starty** z pełnym horyzontem 5.
  - Do tego en-czat (8 728) i pl-czat (9 850).
- **Lustro MTP** (zgodność z llama.cpp: top-1 na głębokości 1 98.4%, łańcuch 97–99.6%, RESULTS §3).
  - Przejście `tree_extract.py`: łańcuch dostaje tokeny, które cel **faktycznie wylosował**.
    - Przy weryfikacji „losuj i dopasuj” (produkcja przy T>0, także sprzężona) węzeł spoza wylosowanej ścieżki nigdy nie jest przyjęty.
    - Logity na tej ścieżce są więc dokładnie logitami każdego węzła drzewa, który może przejść.
    - Każde drzewo jest przy takiej weryfikacji bezstratne: cel losuje jak zwykle, drzewo tylko sprawdza, czy zawiera wylosowany token.
  - Drugie przejście `--greedy` liczy łańcuch serwera (argmax). Daje ceny węzłów poza ścieżką dla drzew dynamicznych.
- **Estymator** (`tree_ceiling.py`, `tree_dynamic.py`):
  - wartość węzła = P(prefiks przyjęty) · p'(token węzła), wartość oczekiwana na ostatnim poziomie;
  - tok/krok = 1 + suma wartości węzłów;
  - wartość dziecka nie przekracza wartości rodzica, więc wybór „najpierw najlepszy” daje optymalne drzewo statyczne każdej wielkości;
  - wariant sprzężony: próbkowanie a posteriori szumu Gumbela przy danym tokenie celu (64 próbki na pozycję), z filtrami draftu top-k → top-p → min-p → /(T·DT) jak w `GGML_OP_GUMBEL_MAX`;
  - T=0.8: wagi ważności p₀.₈/p₁ na wylosowanej ścieżce.
- **Sprawdzenia:**
  - łańcuch-4 greedy offline: proza 2.482 tok/krok (RESULTS: en 2.49, pl 2.48);
  - wariant sprzężony z DT=0.01 odtwarza greedy (2.485);
  - sprzężony łańcuch-4 daje +4.2% tok/krok nad greedy, wobec +3.7% zmierzonych w 24p (tryb 1 vs 2).
- **Model kosztu:**
  - 27.6 ms przy 5 wierszach;
  - +0.85 ms na wiersz do 8 wierszy (24k);
  - 9. wiersz kosztuje +1.37 ms (próg MMVQ → WMMA);
  - dodatkowe przejście MTP przy głębokości 5 kosztuje +0.85 ms;
  - t/s = średnia tokenów / średni koszt.

## 2. Wyniki (proza = pl + en, T=1, n = 17 692)

| wariant | wiersze | tok/krok | Δ tok | Δ ms | **netto t/s** |
|---|---|---|---|---|---|
| łańcuch-4 greedy (topka dziś) | 5 | 2.482 | – | – | – |
| statyczne optymalne, 5 węzłów (łańcuch-4 + 2. kandydat na gł. 1) | 6 | 2.589 | +4.3% | +3.1% | **+1.2%** |
| statyczne, 6 węzłów (+ łańcuch gł. 5, 5. przejście MTP) | 7 | 2.672 | +7.6% | +9.2% | −1.5% |
| **dynamiczne, 4 węzły** (kształt z pewności MTP) | 5 | 2.580 | +3.9% | 0 | **+3.9%** |
| **dynamiczne, 5 węzłów** | 6 | 2.679 | +7.9% | +3.1% | **+4.7%** |
| dynamiczne, 6 węzłów | 7 | 2.741 | +10.4% | +6.2% | +4.0% |
| dynamiczne, 7 węzłów | 8 | 2.786 | +12.2% | +9.2% | +2.7% |
| łańcuch-4 + każdy liść o pewności ≥ 0.1 | 6.3 śr. | 2.689 | +8.3% | +4.1% | +4.1% |
| sprzężony łańcuch-4, DT 1.0 (dźwignia OptCoupledT1, odniesienie) | 5 | 2.587 | +4.2% | (+0.66% op) | – |
| sprzężony, DT 0.7 / 1.3 / 1.6 (względem DT 1.0) | 5 | 2.593 / 2.570 / 2.549 | +0.26% / −0.6% / −1.5% | 0 | ≈ 0 / ujemne |
| sprzężony + statyczne drzewo 5 węzłów (względem sprzężonego łańcucha) | 6 | 2.675 | +3.4% | +3.1% | +0.3% |

Dynamiczne 5 węzłów (6 wierszy) w podgrupach:

| podgrupa | T=1 netto | T=0.8 (top-k 40) netto |
|---|---|---|
| en-proza | +5.3% (sama odpowiedź +5.5%) | +5.2% (+5.4%) |
| pl-proza | +4.2% (sama odpowiedź +4.6%) | +4.2% (+4.6%) |
| en-czat | +4.5% | +4.4% |

Wrażliwość na koszt wiersza (proza, T=1, drzewo dynamiczne):

| koszt wiersza | 6 wierszy | 7 wierszy | 8 wierszy |
|---|---|---|---|
| 1.20 ms | +3.4% | +1.6% | −0.7% |
| **0.85 ms (dziś)** | **+4.7%** | +4.0% | +2.7% |
| 0.57 ms | +5.8% | **+6.0%** | +5.7% |
| 0.40 ms | +6.4% | +7.3% | +7.6% |

Pierwsze odrzucenie łańcucha-4 (realizacja; P(odrzucenie w 4 krokach) = 0.866 na prozie): ranga tokenu celu w logitach MTP.

| grupa | 2. kand. | 3. | 4. | 5. | 6. | poza top-6 / OOV |
|---|---|---|---|---|---|---|
| proza | **29.2%** | 11.5% | 7.3% | 4.8% | 3.5% | 43.8% |
| en-proza | 32.7% | 13.3% | 8.0% | 5.4% | 3.7% | 37.1% |
| pl-proza | 26.4% | 10.2% | 6.7% | 4.3% | 3.4% | 49.0% |
| en-czat | 37.8% | 14.3% | 8.2% | 4.7% | 3.5% | 31.5% |

## 3. Dlaczego tak mało

- **Proza jest płaska.** W 44% odrzuceń (pl: 49%) tokenu celu nie ma w top-6 MTP, więc żadne wąskie drzewo go nie złapie.
- **Rodzeństwo daje +1 token tylko wtedy, gdy łańcuch pękł dokładnie w tym miejscu.**
  - Drugi kandydat na głębokości 1 jest wart 0.107 tokenu na krok, czyli +4.3% tokenów przy koszcie +3.1%.
  - Głębiej wartość spada geometrycznie: 0.075 / 0.043 / 0.025 (głębokości 2–4).
- **Dynamika pomaga, ale tylko trochę.** Pewność MTP odróżnia kroki, w których warto dać liść zamiast 4. węzła łańcucha (+3.9% bez nowych wierszy). Sufit to wciąż ≈ +5% przy 6–7 wierszach.
- **Temperatura draftu nie ma czego poprawić.** Głowica MTP jest „za pewna”, a mimo to DT > 1 szkodzi. Sprzężony Gumbel już zbiera tę resztę, którą da się zebrać z q ≈ p.

## 4. Działania

1. **Brak zadań GPU i brak gałęzi `mtp-tree`.** Werdykt jest offline i nie wymaga pomiaru na GPU (sufit < próg).
2. **`LLAMA_SPEC_COUPLED_DT` zostaje na 1.0.** Wynik przekazałem OptCoupledT1.
3. **Warunek powrotu do drzew:** koszt wiersza 5 → 8 ≤ 0.57 ms, np. jądro wielokolumnowe, gdzie V8 − V5 ≤ 1.7 ms (dziś ~2.5 ms, raport 18).
   - Wtedy pierwszym krokiem jest drzewo dynamiczne o **stałych 5 wierszach** (+3.9%, sama zmiana kształtu, bez nowych szerokości grafu).
   - Potem 6–7 wierszy.
   - Uwaga dla OptMmvqN5: jądro wyspecjalizowane pod n=5 obniża V5, ale nie V6–V8, więc koszt wiersza 5 → 6 rośnie i drzewa jeszcze bardziej tracą.
4. **Narzędzie do ponownego użycia:** `tree_extract.py` + `tree_dynamic.py` liczą sufit dowolnego drzewa dla nowej głowicy MTP (np. po samodestylacji) w ~30 min CPU na prozie.
   - Należy je przeliczyć, gdy zmieni się drafter, bo drzewa zyskują na lepiej skalibrowanej głowicy.

## 5. Ograniczenia

- Kształty dynamiczne obejmują tylko łańcuch i liście-rodzeństwo, bez dzieci pod liśćmi. W drzewie statycznym pierwszy taki węzeł (1,0) jest dopiero 8. i wnosi ~+2%. Lepszy selektor (kalibracja pewności) może dodać [INFERENCE] ≤ 1 pp.
- Dane to 17 sekwencji prozy z 2026-10-12 (wcześniejszy build). Liczby są oczekiwaniami z lustra, a nie pomiarem serwera. Tok/krok łańcucha-4 zgadza się z serwerem (2.43–2.65).
- Model kosztu jest liniowy z 24k. Nie zawiera narzutu drzewa (top-M w łańcuchu MTP, maska przodków, GDN z indeksem rodzica, przeniesienie stanu przyjętego liścia), więc liczby netto są górnym ograniczeniem.

## Do bazy wiedzy

| folder | tytuł | treść |
|---|---|---|
| `eksperymenty/` | `2026-10-20-drzewa-mtp-proza-sufit.md` | Sufit offline (lustro MTP na CPU, 17.7k startów prozy, T=1, „losuj i dopasuj”): drzewo statyczne +1.2% netto. Dynamiczne (pewność MTP, łańcuch + liście) +3.9% przy 5 wierszach i +4.7% przy 6. T=0.8 +4.6%. Próg +6% wymaga ≤ 0.57 ms/wiersz (dziś 0.85). Drugi kandydat MTP jest celem w 29% pierwszych odrzuceń (en 33%, pl 26%, czat 38%); 44% poza top-6. Źródło: raport 24s, `24s-drzewa/`. |
| `metody/` | aktualizacja `sprzezone-probkowanie-draftu.md` | Temperatura draftu DT: 0.7 +0.26% tok/krok, 1.3 −0.6%, 1.6 −1.5% względem 1.0 (offline, proza) → DT = 1. Drzewo statyczne nad sprzężonym łańcuchem +0.3% netto. |
| `metody/` | aktualizacja `koszt-szerokosci-weryfikacji.md` | Drzewa MTP na XTX opłacają się (≥ +6% na prozie) dopiero przy koszcie wiersza ≤ 0.57 ms dla 5 → 8 wierszy. |
| `lekcje/` | `lekcja-drzewo-statyczne-vs-dynamiczne.md` | Na prozie drzewo statyczne daje 1/4 zysku dynamicznego (+1.2% vs +4.7%). Kształt z pewności draftera daje +3.9% bez żadnego nowego wiersza. Ocena drzew wymaga logitów łańcucha poza ścieżką (przejście `--greedy`), a nie tylko na ścieżce przyjętej. |
| aktualizacja `18-nastepna-fala.md` §5 / `algorithms.md` §5 | – | „Kill offline z top-2 MTP” zrobione (24s): drugi kandydat 29% odrzuceń na prozie; sufit dynamiczny +4.7% < +6% → odłożone do płaskiej V(N). |
