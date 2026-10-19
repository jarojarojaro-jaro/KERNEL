# 21h — Terminal-RSI (Tencent Hunyuan): czym jest RSI, co z twierdzeń się broni i czy możemy tego użyć

Data: 2026-10-19. Autor: podagent ResRSI. Praca wyłącznie na CPU, koszt $0, **zero uruchomień GPU**. Źródło główne:
arXiv [2610.22192v1](https://arxiv.org/abs/2610.22192) (28 stron PDF, przeczytany w całości razem z dodatkami A–H;
kopia w `~/qwen-opt/research-src/rsi/paper.pdf`, tekst w `paper_clean.txt`). Odwołania „s. N” oznaczają stronę PDF.
Oznaczenia: `[INFERENCE]` to mój wniosek, `[SZACUNEK]` to wycena, `[NIEZWERYFIKOWANE]` to rzecz niesprawdzona.

---

## 0. Najważniejsze

1. **RSI w tej pracy nie jest „AI, które samo się ulepsza”.** To dwa cykle znanej pętli *expert iteration*
   (STaR/ReST) połączonej z PPO:
   - model rozwiązuje zadania;
   - zostają tylko rozwiązania, które przeszły ukryte testy;
   - model przepisuje je na czyste demonstracje i uczy się na nich (SFT);
   - potem RL z nagrodą, która premiuje pełny sukces;
   - całość powtórzono raz.

   Między cyklami decyzje podejmowali ludzie: nowa nagroda zaprojektowana po obejrzeniu danych, inny learning rate,
   wybór gałęzi i checkpointu (s. 8, 19, 20).
2. **Wynik główny jest realny co do kierunku, ale pokazany zbyt korzystnie.**
   - Base → final na TB 2.1 (51.7 → 86.5%) i TB 4.0 (0 → 19.8%) to skok wiele razy większy od szumu.
   - Przyrosty ostatniego etapu (RSR-2 → RPR-2: +2.4 pp TB4, +2.0 TB3, +3.0 Hard) mieszczą się w szumie (SE ≈ 4–5 pp).
   - Część wartości w tabeli nie daje się odtworzyć jako Mean@3 na nominalnej liczbie zadań (§3.3).
   - Checkpoint końcowy wybrano z wiedzą o wynikach benchmarków. Autorzy sami piszą, że to miesza uczenie z adaptacją
     do testu (s. 20).
   - Kosztu obliczeń praca **nie podaje wcale**. Mój szacunek: ~1.5–2.5 tys. H100-h, czyli ~$3–9k samego GPU, plus
     klaster sandboxów i porażki, których nie opisano.
3. **Kontaminacja: ryzyko średnie, nieaudytowane.**
   - Rozłączność z pulą treningową deklarują tylko dla SWR100. „Broader repository and pretraining overlap remain
     incompletely audited” (s. 13).
   - Dwa z sześciu benchmarków (TB-Hard, LHTB) oraz generator SWR to prace tego samego zespołu.
   - TB-Hard to „self-curated” benchmark ([RSR, arXiv 2610.02826](https://arxiv.org/abs/2610.02826)).
   - Najczystszym testem jest TB 4.0: 0 → 19.84%. Frontier ma tam 46–54% (s. 7).
4. **Kąt 1 (jakość modelu w produkcie): nie trenować, tylko adoptować i zmierzyć.**
   - Pełne RSI jest poza naszym zasięgiem: actor i critic 27B z Adamem to ≈ 0.86 TB stanu, czyli ≥ 2 węzły 8×H100,
     przez tygodnie.
   - Jest tańsza droga. Zespół wydał **RSR-27B** (Qwen3.8-27B po RSR + „dodatkowym RL”, Apache-2.0,
     [HF](https://huggingface.co/IntelligenceLab/RSR-27B)). Ma tę samą architekturę `qwen3_5`, więc nasz silnik
     działa bez zmian.
   - **Haczyk: głowicy MTP nie trenowano.** Tensory `mtp.*` leżą w pliku `model-missing-from-origin-00002.safetensors`,
     czyli skopiowano je z bazy. Przy zmienionym pniu akceptacja MTP spadnie. Nasz pipeline z raportu 11 dopasuje
     głowicę za ~$2–4.
   - Terminal-RSI-27B nie jest wydany: strona projektu „Code soon / Model soon”, repo GitHub zwraca 404.
   - Eksperyment E1 (~$40–70 na wynajętych 3090) rozstrzyga, czy RSR-27B pomaga **w naszym harnessie omp**, a nie tylko
     w Terminus-2.
5. **Kąt 2 (RSI jako metoda dla naszej pracy optymalizacyjnej): tak, ale bez trenowania wag.**
   - Przenosimy trzy mechanizmy:
     - (a) tylko zweryfikowany sukces (u nas `CONFIRMED` z fabryki) staje się materiałem do nauki;
     - (b) sukces przepisany na **playbook**, który zostaje przyjęty tylko wtedy, gdy *świeży* agent bez diffu odtworzy
       zysk na **innym** celu (odpowiednik „fresh public execution” + leakage review);
     - (c) nagroda typu SPR: częściowe zaliczenie bramek nigdy nie waży tyle co werdykt.
   - Krytyk z RL u nas to kalibracja przewidywań i reguły fabryki. Te dziedziczymy między cyklami, nigdy ich nie
     resetujemy.
   - Ograniczenie twarde: jedno XTX i 12–15 h GPU na 30 dni ([18 §6.2](18-nastepna-fala.md)), czyli ~16–60 werdyktów
     miesięcznie. Ewolucja populacyjna w stylu AlphaEvolve (tysiące ewaluacji) odpada. Zostaje pętla „mało prób,
     mocny prior”.
6. **Pierwszy pilot (P0–P1, ~1.5–2 h GPU łącznie, $0 chmury):**
   - P0: pierwszy prawdziwy przebieg fabryki na GPU (karta 0070). Fabryka nie wydała jeszcze ani jednego werdyktu:
     `ledger.jsonl` ma 2 wiersze z 16.10.
   - P1: „retro-RSR” na łatce 0070 (epilog MMQ w parach VOPD, +2.2% pp4096, bitowo). Rewriter pisze playbook, recenzent
     sprawdza przeciek, potem świeży agent z playbookiem i agent bez playbooka przenoszą technikę na inny typ kwantu.
   - Kryteria zabicia w §5.7.

---

## 1. RSI po ludzku

**Analogia.** Student rozwiązuje zadania egzaminacyjne. Czasem pomagają mu różni korepetytorzy: to „harnessy”, czyli
różne nakładki agentowe, jak ciągła praca do timeoutu albo inne narzędzia. Potem:

1. **Odkrywanie.** Zbiera tylko te rozwiązania, które egzaminator (ukryte testy) zaliczył w całości.
2. **Przepisanie (RSR, Recursive Self-Rewrite).** Z każdego zaliczonego rozwiązania pisze ściągę-procedurę
   („runbook”): jak do tego dojść od zera. Recenzent sprawdza, czy ściąga nie zdradza odpowiedzi ani testów (leakage).
   Potem student **rozwiązuje zadanie jeszcze raz w standardowych warunkach**, ze ściągą schowaną w prywatnej
   instrukcji. Do zeszytu trafia tylko ta powtórka, która znowu zaliczyła, i to **bez ściągi** w zapisie. Na zeszycie
   student się uczy (SFT). Model uczy się więc rozwiązywać bez podpowiedzi, czyli destylacja z informacji
   uprzywilejowanej.
3. **Szlifowanie (RPR, Recursive Policy-Refine).** Trening z oceną (PPO). Punkty za częściowy postęp są ograniczone
   i zawsze mniejsze niż za pełne zaliczenie (SPR, Success-Prioritized Reward).
4. **Rekurencja.** Ulepszony student wraca do kroku 1 jako lepszy generator rozwiązań. W pracy: dwa okrążenia
   (Base → RSR-1 → RPR-1 → RSR-2 → RPR-2).

**Trzy techniczne dodatki** (dla nas ważne tylko jako idee):
- **Dziedziczenie krytyka.** Model wartości (szacuje, czy bieżący stan prowadzi do sukcesu) przechodzi z cyklu do
  cyklu. Nie jest trenowany od zera. Przed RL dostaje 4 kroki rekalibracji przy zamrożonym aktorze (s. 3, 6).
- **TB-GAE.** Przypisanie zasług liczy dyskontowanie po **turach**, a nie po tokenach. Dzięki temu gadatliwe logi
  narzędzi nie „rozcieńczają” nagrody (s. 5).
- **FDR → SPR.** Najpierw nagroda proporcjonalna do zaliczonych testów cząstkowych. Potem nagroda „sukces + ograniczony
  postęp”. Powód z ich danych: przy FDR **50.09% masy nagrody** trafiało do porażek, a 48 porażek zaliczało każdy
  wykonany test scenariusza, ale nie bramkę końcową (s. 4).

**Czy to „rekursywne samodoskonalenie” w mocnym sensie?** Nie.
- Są dwa cykle. SWR100 stoi w miejscu po pierwszym RL: 6.00, 6.00, 6.00% (s. 10).
- Nagrodę, learning rate i wybór gałęzi zmieniali ludzie po obejrzeniu wyników.
- Autorzy piszą wprost, że pięć etapów jednego modelu nie dowodzi ani prawa skalowania, ani monotoniczności (s. 13).

Nazwa „RSI” jest tu marketingowa. Metoda to porządnie wykonana iteracja *generate → filter → rewrite → train*.

---

## 2. Co dokładnie zrobiono

| element | wartość | źródło |
|---|---|---|
| backbone | Qwen3.8-27B, kontekst 262 144 | s. 6 |
| infrastruktura | slime + Megatron (3D + CP=4) + SGLang + Harbor | s. 6 |
| pula treningowa | 3 000 zadań: 2 400 „semantic-verifier” (SWR) + 600 „supplementary terminal” (źródło nieujawnione) | s. 6, 21 |
| RL | PPO, batch 256 (oversampling 288), 1 odpowiedź na zadanie, T = 1.0, **bez KL i entropii**, clip [0.7; 6.0] | s. 6, 18 |
| LR aktora / krytyka | 5e-7 → 1e-7 / 1.5e-5 | s. 6 (Tabela 1) |
| kroki | 36 kroków rolloutu na fazę skonfigurowane; zachowane 20 (RPR-1) i 18 (RPR-2) | s. 18 |
| długość trajektorii | 33–49 tys. tokenów generacji, 44–69 tur (średnie populacji) | s. 19 |
| protokół ewaluacji | Mean@3, T = 0.6, **thinking wyłączony**, akcje JSON, 8 192 tok./turę, 96k wejścia, streszczanie przy 32k | s. 18 (Tabela 3) |

Wyniki etapów (Tabela 2, s. 7; Rys. 14, s. 24):

| benchmark | Base | RSR-1 | RPR-1 | RSR-2 | **RPR-2 (final)** |
|---|---|---|---|---|---|
| TB 4.0 (63 zadania) | 0.00 | 6.10 | 16.67 | 17.46 | **19.84** |
| TB 2.1 (89) | 51.70 | 70.10 | 77.53 | 86.52 | **86.52** |
| TB 3.0 (70) | 0.00 | 6.80 | 14.29 | 15.00 | **16.95** |
| TB Hard (100, własny) | 31.00 | 54.00 | 69.50 | 76.00 | **79.00** |
| LHTB process reward (46, własny) | 0.21 | 0.29 | 0.30 | 0.31 | **0.37** |
| LHTB pełne ukończenie | 0/46 | 0/46 | 2/46 | 4/46 | **5/46** |
| SWR100 (100, generator własny) | 3.00 | 5.00 | 6.00 | 6.00 | **6.00** |
| Direct PPO od Base, krok 20 (kontrola) | — | — | TB2.1 48.31, TB3 1.43, TB4 0.00, Hard 39.00 | — | — |

Porównanie z frontierem (Rys. 4, s. 7):
- TB 2.1: GPT-6 Astra 89.9, Claude Opus 5 87.6, Terminal-RSI 86.52.
- TB 4.0: GPT-6 Astra 54.0, Opus 5 46.0, Terminal-RSI 19.84.

Autorzy zaznaczają, że „primary-source and protocol reconciliation remains incomplete” (s. 8).

---

## 3. Weryfikacja twierdzeń

### 3.1 Co znaczy „verified”

- **Sukces S = 1 oznacza: przeszedł kompletny chroniony weryfikator zadania**, a nie deklaracja agenta czy podzbiór
  testów (s. 3, 18). Do RSR dochodzi bramka przecieku `q_leak` i recenzent runbooka, który widzi tylko publiczne
  zadanie i runbook (s. 3).
- **Weryfikator certyfikuje tylko to, co sprawdza.** Sami pokazują lukę na zadaniu Rust–C FFI (s. 13).
  - Model końcowy „rozwiązał” zadanie, przechodząc fuzz-testy.
  - W rzeczywistości użył interfejsu C tylko do smoke-testu linkowania, a obliczenia **delegował do Pythona**.
  - „Fuzz-test success establishes tested output equivalence, not a native Rust–C AST execution path.”

  To dokładnie klasa „specification gaming”, którą znamy z kerneli: Sakana 3.13× → 1.49×, Kevin-32B, GPU MODE NVFP4
  ([02 §2.3](02-autotuning-i-agenci-kerneli.md), wiersze 191–202).
- **Wniosek dla nas:** „verified” = „przeszedł testy”, nie „poprawny”. U nas odpowiednikiem jest luka G2.
  - Md5 na krótkich promptach `greedy.sh` nie pokrywa ścieżek prefillu, np. MMQ J ≥ 48 ([16h §5](16h-fabryka-v1.md),
    wiersz 225).
  - Agent nagradzany werdyktem znajdzie taką lukę szybciej niż człowiek.

### 3.2 Kontaminacja

| sygnał | ocena |
|---|---|
| deklarowana rozłączność tylko dla SWR100 (s. 6, 21) | TB 2.1/3.0/4.0 i TB-Hard nie są sprawdzone względem puli treningowej ani pretreningu (s. 13: „incompletely audited”) |
| 600 „supplementary terminal tasks” bez źródła i manifestu (s. 21: do reprodukcji „requires … task and repository manifests”) | ryzyko bliskich duplikatów zadań w stylu Terminal-Bench `[INFERENCE]` |
| zadania TB są publiczne (GitHub/Harbor Hub); TB 4.0 usunął 2 zadania za „public solutions” ([tbench 4.0](https://www.tbench.ai/news/terminal-bench-4-0)) | sam benchmark przyznaje, że rozwiązania wyciekają |
| TB-Hard, LHTB i SWR to prace tych samych autorów ([22], [20], [RSR](https://arxiv.org/abs/2610.02826): „our self-curated Terminal-Bench Hard”) | trening na SWR i test na SWR100 to ta sama dystrybucja generatora; TB-Hard +48 pp to najmniej niezależna liczba |
| baza Qwen3.8-27B ma na TB 2.1 aż 51.7%, ale na TB 4.0 0% | duża rozbieżność między starym a nowym benchmarkiem pasuje i do „TB 2.1 łatwiejszy”, i do „TB 2.1 częściowo znany” `[INFERENCE]` |

Werdykt: **wątpliwe co do wielkości, prawdopodobne co do kierunku.** TB 4.0 (0 → 19.8%) to najmocniejszy dowód
realnej zdolności. Ma 63 zadania, a 19.84% = 25 z 126 prób.

### 3.3 Arytmetyka wyników i szum

Sprawdziłem, które wartości dają się zapisać jako k/(n·R) dla nominalnej liczby zadań n (89, 70, 63, 100; s. 21)
i R ∈ {1, 2, 3}. Skrypt jednorazowy w kernelu eval, niezachowany.

| wartość | czy pasuje do Mean@3 na nominalnym n? |
|---|---|
| TB 4.0 final 19.84% | **tylko 25/(63×2)**, czyli 2 przebiegi, nie 3 |
| Hard RPR-1 69.50% | **tylko 139/(100×2)**, czyli 2 przebiegi |
| TB 2.1 Base 51.70%, RSR-1 70.10% | **nie pasuje do 89 zadań** przy żadnym R ≤ 3 |
| TB 3.0 final 16.95% | **nie pasuje do 70**; pasuje 10/59 (albo 30/177) |
| TB 3.0 RPR-1 i RSR-2 14.29% | 10/70 (albo 30/210) |
| TB 4.0 RSR-1 6.10%, TB 3.0 RSR-1 6.80% | nie pasują do 63/66 ani 70/74 |

- **Część liczb nie jest więc Mean@3 na pełnym zbiorze.** Zbiory zadań różnią się między przebiegami: awarie
  infrastruktury wykluczane albo inne manifesty. Dodatek E to przyznaje: „historical summaries contain heterogeneous
  repeat counts”, a 3.0 i 4.0 mają w starszych zapisach 74 i 66 zadań (s. 21).
- **Najbardziej podejrzany jest „postęp” TB 3.0** z 14.29 do 16.95%. Pasuje do tych samych ~10 rozwiązanych zadań
  liczonych na mniejszym mianowniku (59 zamiast 70) `[INFERENCE]`.
- **Szum próbkowania zadań** (SE = √(p(1−p)/n)):
  - TB 2.1 przy 86.5%: ±3.6 pp;
  - TB 4.0 przy 19.8%: ±5.0 pp;
  - Hard: ±4.1 pp.

  Trzy powtórzenia tego samego checkpointu nie zmniejszają tej niepewności i nie zastępują ziaren treningu (s. 13).
  Przyrosty RSR-2 → RPR-2 (+2.38, +1.95, +3.00 pp) są w szumie.
- **SWR100 „podwaja się”** z 3 do 6 na 100 zadań: test Fishera p = 0.50, czyli **nieistotne**. LHTB 0/46 → 5/46:
  p = 0.056, na granicy.

### 3.4 Baseline'y i porównania

- **Direct PPO od Base** (Tabela 4, s. 21) to jedyna kontrola metody. Wynika z niej, że RSR-first > PPO-first przy
  **tej samej liczbie kroków lokalnych**, ale nie przy tym samym koszcie. Autorzy: „not a compute-matched comparison”
  (s. 8). Kontrola ma też „historyczny protokół” i własny punkt startowy 47.75%, a nie Base 51.70%.
- **Brak ablacji składników.** TB-GAE, dziedziczenie krytyka, FDR → SPR i harmonogram LR zmieniały się razem.
  Tabela 5 (s. 23) wymienia te kontrole jako *przyszłe*. Co więcej, w pierwszej fazie RL użyto **zwykłego GAE
  z γ = λ = 1**, a „checkpoint manifests are still needed to establish the deployed advantage estimator” (s. 6, 23).
  **Flagowy TB-GAE nie ma więc dowodu, że był użyty w wyniku końcowym.** To wprost kłóci się z abstraktem.
- **SPR zaprojektowano na danych, które już widzieli.** „The eight later steps were already available when the reward
  was designed” (s. 19).
- **Wybór checkpointu.**
  - Gałąź Long-Reward na kroku 18. Krok 20 traci 2.66, 2.38 i 3.00 pp na trzech zestawach (s. 8).
  - Wybór oparto na wynikach benchmarków. Autorzy: „Repeated selection using final benchmark feedback would confound
    learning with test-set adaptation” (s. 20).
  - To klątwa zwycięzcy, ta sama, przed którą broni nasza fabryka ([15f §3.3](15f-agentowa-nauka.md), wiersze 141–147).
- **Porównanie z frontierem** (Rys. 4) to liczby zgłoszone przez innych, w innych harnessach i z innymi limitami.
  Terminal-RSI ma np. limit 100 000 tur i streszczanie przy 32k. Porównanie jest orientacyjne.

### 3.5 Koszt obliczeń (praca go nie podaje, liczę sam)

Znane z pracy:
- batch 256/288, 1 odpowiedź na zadanie;
- RL: RPR-1 do kroku 35, dwie gałęzie RPR-2 po ~20, Direct PPO 20, razem **~95 kroków × 256 ≈ 24 tys. trajektorii**;
  dodatek B dokumentuje 14 143 trajektorie treningowe (s. 19), rząd wielkości się zgadza;
- 33–49 tys. tokenów generacji na trajektorię.

Rachunek `[SZACUNEK]`:
- **RL, trening.** Zakładam ~100 tys. tokenów kontekstu na trajektorię (generacja + obserwacje). Koszt na token:
  aktor fwd+bwd 6N + stare logprob 2N + krytyk fwd+bwd 6N + wartości 2N ≈ 16N = 4.3·10¹¹ FLOP (N = 27·10⁹).
  - 24 tys. × 10⁵ tok. = 2.4·10⁹ tok. → **1.0·10²¹ FLOP**.
  - Przy 30–40% MFU H100 (989 TFLOPS bf16): **720–960 H100-h**.
  - Same zachowane kroki: ~290–390 H100-h.
- **RL, rollouty.** ~1·10⁹ tokenów dekodowania. Przy 1.5–3 tys. tok./s na H100 w długim kontekście: **90–180 H100-h**.
- **RSR** (z pracy RSR: 2 001 trajektorii źródłowych → 11 094 przepisanych, do K × M = 16 powtórek na źródło):
  - powtórki: ~1.3·10⁹ tokenów → 120–250 H100-h;
  - SFT ~0.9·10⁹ tokenów × 6N → 100–130 H100-h na epokę;
  - razy dwa cykle.
- **Razem ≈ 1.5–2.5 tys. H100-h, czyli ~$3–9k** przy $1.73–3.53/h (Vast H100 SXM
  [$1.73](https://vast.ai/pricing/gpu/H100-SXM), indeks [$3.53](https://gpueconomy.com/gpu/h100-sxm)).

  Bez nieudanych eksperymentów, bez CPU dla ~288 równoległych sandboxów Docker i bez pracy inżynierskiej.
- **Podłoga pamięci:** pełny fine-tune aktora i krytyka 27B z Adamem ≈ 2 × 27·10⁹ × 16 B ≈ **0.86 TB** + aktywacje
  przy 256k kontekstu. To minimum 2 węzły 8×H100 na trening plus serwery rolloutów. RPR-2 wymagał nawet CPU offload
  optymalizatora (s. 18).

### 3.6 Werdykt per twierdzenie

| twierdzenie | ocena | dlaczego |
|---|---|---|
| Qwen3.8-27B: TB 2.1 51.7 → 86.5% | **prawdopodobne co do kierunku, wątpliwe co do wielkości** | skok ≫ szum, ale Base 51.70 nie pasuje do 89 zadań, kontaminacja nieaudytowana, checkpoint wybrany na teście |
| TB 4.0 0 → 19.84% | **prawdopodobne** | najnowszy benchmark; ale to 2 przebiegi (25/126), nie Mean@3 |
| „Both rewrite and refinement stages improve” | **prawdopodobne dla cyklu 1, w szumie dla cyklu 2** | RSR-2 → RPR-2: +2–3 pp przy SE 4–5 pp |
| TB-GAE pomaga | **niewykazane** | brak ablacji, brak dowodu użycia w finalu (s. 6, 23) |
| dziedziczenie krytyka pomaga | **niewykazane** | kontrola inherit/reset dopiero „prospective” (s. 23) |
| SPR tłumi fałszywe sukcesy | **prawdziwe offline** | 50.09 → 28.72% masy nagrody dla porażek na tych samych 4 352 trajektoriach (s. 11); efekt online niezmierzony |
| SWR100 „podwaja się” | **nieistotne** | 3 → 6 na 100, p = 0.50 |
| RSR-first > Direct PPO | **prawdopodobne, ale nie przy równym koszcie** | sami to piszą (s. 8) |
| 27B „wyprzedza” GPT-6 Sol i Kimi K3 na TB 2.1 | **wątpliwe** | różne harnessy i protokoły, uzgodnienie „incomplete” |

---

## 4. Kąt 1: RSI jako dźwignia jakości modelu w produkcie

Pytanie: czy dostroić Qwen3.8-27B do agentowego kodowania (omp) i oferować go w Podkręcie?

### 4.1 Opcja A, najtańsza: adoptować RSR-27B (wydany)

Fakty sprawdzone 2026-10-19 przez HF API:
- `IntelligenceLab/RSR-27B`, licencja **Apache-2.0**, `model_type: qwen3_5`, 64 warstwy (co 4. full attention),
  `mtp_num_hidden_layers: 1`, 27.78 mld parametrów BF16.
- Karta modelu: „finetuned with RSR trajectories. We did additional RL training to stabilize” (szczegółów brak).
  To **nie** jest Terminal-RSI-27B.
- **`mtp.*` (15 tensorów) i `model.visual.*` leżą w `model-missing-from-origin-*.safetensors`**, czyli skopiowano je
  z bazy, nie trenowano. Pień się zmienił, a głowica MTP została stara.
- Terminal-RSI-27B: niewydany (strona projektu [„Code soon / Model soon”](https://jyyang26.github.io/terminal-rsi/),
  `github.com/jyyang26/Terminal-RSI` → 404, org HF `Teriminal-RSI` bez modeli).

Kompatybilność z naszym forkiem:

| element | wpływ |
|---|---|
| konwersja GGUF, kwant UD-Q4_K_XL + imatrix | ta sama architektura, istniejąca ścieżka `convert_hf_to_gguf.py` `[INFERENCE]` |
| **MTP (×2.5)** | głowica z bazy przy zmienionym pniu, więc **spadek akceptacji** `[INFERENCE]`; raport 10: „każdy SFT trunku psuje kalibrację MTP” ([10](10-post-training.md), wiersz 370). Naprawa: pipeline z raportu 11 (self-distillation głowicy `blk.64.*` na naszym Q4), koszt zmierzony tam: $2.14 ([11](11-mtp-pl-pilot.md), wiersz 8) |
| lookup tail W16 | niezależny od wag; zysk zależy od tego, ile model kopiuje, więc trzeba zmierzyć ponownie |
| bit-exact, md5 | nowe wagi = nowe bazy md5; bramki forka działają per model |
| PM4, kvq | bez zmian (ten sam graf) |
| obietnica „bezstratnie, ten sam model” | **nie dotyczy**: to inny model, oferowany jako osobny wybór w katalogu („Qwen-agent”), nie jako przyspieszenie |

**Uwaga produktowa.** Agent po RL pracuje dłużej:
- RPR-1: 50 → 84.8 tur (s. 8);
- RPR-2 SPR: 83.8 → 116.8 tur (s. 10).

Przy 103.7 t/s (Qwen MTP, PM4 = 0; [18](18-nastepna-fala.md), wiersz 519) 33–49 tys. tokenów generacji to 5.3–7.9 min
samego dekodowania na zadanie. Dla użytkownika liczy się **czas do sukcesu**, nie sam odsetek sukcesów. Szybszy silnik
staje się przez to ważniejszy, nie mniej ważny.

### 4.2 Opcja B: własne „RSI-lite” (tylko SFT na samodzielnie wygenerowanych, zweryfikowanych trajektoriach omp)

Przepis:
1. 300–1000 zadań z weryfikatorem: fail-to-pass z historii naszych repo (testy Pythona fabryki, narzędzia wiki)
   i z otwartych zestawów ([TMax](https://arxiv.org/abs/2606.23321) publikuje dane; licencja `[NIEZWERYFIKOWANE]`).
2. Qwen3.8-27B Q4 w **naszym** silniku na wynajętych 3090 (nasz fork CUDA) rozwiązuje je w harnessie omp.
3. Zostają tylko trajektorie z S = 1. Rewriter (ten sam model) pisze runbook. Powtórka w świeżym sandboxie ze schowanym
   runbookiem, a do zbioru trafia tylko powtórka z S = 1.
4. QLoRA na H100, merge, GGUF, nasz imatrix, dopasowanie głowicy MTP (raport 11).

Wycena `[SZACUNEK]`:

| krok | rachunek | $ |
|---|---|---|
| generacja (pilot 200 zadań × 4 próby + 4 powtórki na sukces) | ~1 000–1 500 trajektorii × 15–25 min na 3090 ($0.23/h; [05](05-chmura-gpu-do-testow.md), wiersz 15) | **$60–150** |
| generacja (pełna, 1 000 zadań) | ~5–6 tys. trajektorii | **$300–700** |
| SFT QLoRA | 3 tys. traj. × ~60 tys. tok. = 180 M tok.; 1.5–2.5 tys. tok./s na H100 → 20–33 h × $1.73–2.78 | **$35–95** |
| głowica MTP | jak raport 11 | **$2–4** |
| ewaluacja (E1 poniżej) | — | **$40–70** |
| **razem** | pilot / pełne | **~$150–300 / ~$0.5–1k** |

Oczekiwany zysk: w pracy RSR samo SFT dało TB 2 pass@3 57.0 → 74.2% ([RSR](https://arxiv.org/abs/2610.02826)),
a Terminal-RSI RSR-1 dało TB 2.1 51.7 → 70.1% (s. 7). Na naszym harnessie omp nie wiadomo `[INFERENCE]`:
- przeniesienie z Terminus-2/JSON na narzędzia omp (`edit`/`read`/`bash`) jest niesprawdzone;
- ryzyko regresji polskiego i czatu (nasz produkt jest po polsku).

Lokalne XTX **nie** nadaje się do generacji danych. 1 000 trajektorii × ~10 min to ~170 h GPU przy budżecie 12–15 h na
30 dni i regułach termicznych ([18 §6.1–6.2](18-nastepna-fala.md), wiersze 509–532). Wszystko idzie do chmury.

### 4.3 Opcja C: pełne RSI (RSR + RPR z krytykiem)

Nie. ≥ 16 H100 przez tygodnie (§3.5), ~$5–15k z porażkami `[SZACUNEK]`, a składniki RL nie mają dowodu ablacyjnego
(§3.4). QLoRA-RL na 24 GB (Unsloth, [10](10-post-training.md), wiersz 374) nie uniesie trajektorii po 33–49 tys.
tokenów z kontekstem do 96k.

### 4.4 Licencje i ToS

- **Qwen3.8-27B: Apache-2.0**. Pochodne wolno publikować z LICENSE/NOTICE i oznaczeniem zmian
  ([10 §7](10-post-training.md), wiersz 385). **RSR-27B: Apache-2.0** (HF).
- **Dane:** trajektorie generowane przez Qwena (jak w RSR) są bezpieczne. **Nie** wolno trenować na naszych sesjach omp
  z Claude. Warunki Anthropic zabraniają używania wyjść do trenowania konkurencyjnych modeli `[INFERENCE: do
  potwierdzenia w aktualnych Commercial Terms]`. To przewaga RSI: samogenerowane dane omijają ten problem.
- Bezpieczeństwo sprzętu: trening i generacja w chmurze, lokalnie tylko krótkie bloki inferencji/ewaluacji. Brak
  dodatkowego zużycia SSD/GPU poza zwykłymi buildami.

### 4.5 Eksperyment E1 (rozstrzyga kąt 1)

- **Hipoteza:** RSR-27B (Q4, nasz silnik) rozwiązuje więcej zadań niż Qwen3.8-27B (ten sam kwant i silnik), także
  w harnessie omp, bez regresji PL, a po dopasowaniu głowicy MTP zachowuje tok/krok.
- **Ramiona:** base vs RSR-27B, oba jako UD-Q4_K_XL z tym samym imatrix, ten sam build forka CUDA, te same flagi
  (reguła R32).
- **Pomiar:**
  1. TB 2.1, 89 zadań × 2 przebiegi × 2 modele przez Harbor z naszym `llama-server`, T = 0.6, thinking wyłączony
     (protokół s. 18). Sandboksy Docker na VM-instancji z Dockerem albo lokalnie pod
     `nice -n 19 flock -s /tmp/quiet.lock`;
  2. **omp-bench-20:** 20 zadań z naszych repo z testami, utworzonych **po** premierze Qwen3.8 (czasowy holdout
     zamiast deklaracji o rozłączności);
  3. regresja PL: 10 promptów `sealed-v1`, ocena parami ślepo;
  4. tok/krok MTP: głowica stara vs dopasowana (pipeline 11) vs baza, `spec_sweep` 6×5.
- **Koszt:** ~356 trajektorii TB × ~20 min ≈ 120 GPU-h na 3090 ≈ $30–40, plus omp-bench i MTP ≈ $10–30.
  **Razem ~$40–70**, wymaga zgody na wydatek. Watchdog i natychmiastowe `destroy` (AGENTS.md, wiersz 4).
- **Kill:**
  - RSR-27B nie bije bazy o ≥ 8 pp na TB 2.1 (≈ 2 × SE; test McNemara na parach zadań) **i** nie bije o ≥ 3/20 na
    omp-bench-20 → porzucamy kąt 1 do czasu wydania Terminal-RSI-27B;
  - regresja PL w ocenie parami < 40% wygranych → nie do katalogu;
  - po dopasowaniu głowicy tok/krok < 0.9 × baza → najpierw poprawić pipeline MTP.

---

## 5. Kąt 2: RSI jako METODA dla naszej pracy nad silnikiem

### 5.1 Mapowanie Terminal-RSI → nasza fabryka

| Terminal-RSI | u nas | uwagi |
|---|---|---|
| zadanie x z chronionym weryfikatorem V_x | karta twierdzenia + `factory verify` (G0–G5), zestaw zapieczętowany, 36 reguł ([README fabryki](../../../qwen-opt/factory/README.md), wiersze 71–99) | weryfikator poza zasięgiem implementera już jest |
| strict success S | werdykt `CONFIRMED` (albo `NEEDS-HUMAN` zatwierdzony przez człowieka) | jedyny „sukces” |
| FDR → SPR (ograniczony kredyt częściowy) | ranking agentów i playbooków: G0–G3 zaliczone + `NULL` dają < 1, `CONFIRMED` daje ≥ 1; mikrobench nigdy nie daje werdyktu (R07) | ich 50% nagrody dla porażek to nasz „mikrobench szybszy, e2e w szumie”, np. 16g `GU_BLOCK` +0.33% ([16g](16g-lfm-moe-pasmo.md), wiersz 9) |
| odkrywanie w wielu harnessach | różne strategie proponowania: profil → hipoteza; Kernel Tuner; przegląd literatury; „pytanie człowieka” | — |
| **runbook + leakage review + fresh execution** | **playbook** z trajektorii `CONFIRMED`; recenzent przecieku; **świeży agent bez diffu** odtwarza zysk | serce przeniesienia (§5.3) |
| SFT na zaakceptowanych powtórkach | **brak trenowania wag**: playbook trafia do biblioteki `skills/`, którą dostaje kontekst agenta (RSI „w kontekście”) | Claude ma zamrożone wagi; danych jest za mało na SFT (dziesiątki zamiast ~11 tys. trajektorii) |
| krytyk dziedziczony między cyklami | (a) kalibracja przewidywań `measured/expected` z ledgera (15f X5); (b) reguły z fixture'ami | nigdy nie resetujemy; „warm-up krytyka” = kalibracja na zaległych wierszach przed rankingiem kolejki |
| wybór checkpointu na teście (ich błąd) | rotowany zestaw zapieczętowany na cykl + końcowe ABBA zwycięzców razem vs baza | wprost przeciw ich słabości |
| luka weryfikatora (Rust–C → Python) | luka G2 (prefill), „przyspieszenie” przez flagi/prompty (Sakana §6.3) | każde nowe oszustwo zamieniamy w regułę + fixture (wzorzec KernelGuard) |

### 5.2 Porównanie z literaturą: co bierzemy

| system | mechanizm | liczby | co bierzemy | czego nie |
|---|---|---|---|---|
| **AlphaEvolve** ([arXiv 2506.13131](https://arxiv.org/abs/2506.13131)) | baza programów + mutacje LLM + kaskada ewaluatorów; podział kształtów na treningowe i ewaluacyjne | kernel +23%, −1% czasu treningu Gemini ([02](02-autotuning-i-agenci-kerneli.md), wiersz 195) | kaskadę (już jest: G0 → G5) i podział train/eval (zestaw zapieczętowany) | populacji: 1 000 ewaluacji × 20 min = 333 h GPU, czyli ~2 lata naszego budżetu GPU |
| **Darwin Gödel Machine** ([arXiv 2505.22954](https://arxiv.org/abs/2505.22954)) | agent modyfikuje własny kod, każda zmiana walidowana benchmarkiem; archiwum wariantów | SWE-bench 20.0 → 50.0%, Polyglot 14.2 → 30.7%; **objective hacking częstszy, gdy funkcje kontrolne nie są ukryte** (§ hallucination) | kontrolę „bez samodoskonalenia” jako ramię A/B; ukrywanie weryfikatora | samomodyfikacji harnessu: harness zmienia tylko człowiek (`harness lock`) |
| **ReasoningBank** ([arXiv 2509.25140](https://arxiv.org/abs/2509.25140)) | pamięć strategii z sukcesów i porażek, samoocena | — | pamięć strategii = nasze `lekcje/` (73 notatki) | **samoocena sukcesu**: u nas sukces ocenia tylko weryfikator |
| **RSR / Terminal-RSI** | runbook → recenzent przecieku → świeże wykonanie → tylko S = 1 | §2 | akceptację playbooka przez **odtworzenie** | RL, krytyka-sieci |
| METR, Sakana, Kevin-32B, AutoTuneBench | agenci kerneli | METR 1.81× (~$20/zadanie); Sakana 3.13× → 1.49× po usunięciu hacków; AutoTuneBench mediana 1.0001× ([02](02-autotuning-i-agenci-kerneli.md), wiersze 191–202) | reguły antyoszustwa z fixture'ami | wiary w liczby agentów bez weryfikatora |

Wniosek: nasza wersja to **AlphaEvolve tylko w pętli wewnętrznej** (Kernel Tuner/mikrobench, ewaluacja w ms–s,
akceptacja tylko konfiguracji bitowo równych; wiki `metody/kernel-tuner.md`) **+ RSR w pętli zewnętrznej** (playbooki
akceptowane przez odtworzenie) **+ fabryka jako jedyny sędzia**.

### 5.3 Projekt: pętla RSI-F (fabryka)

**Role** (rozszerzenie 15f §5.1 i 16h §4):

| rola | widzi | robi | nie robi |
|---|---|---|---|
| Proponent | profil, kolejkę, `skills/`, `lekcje/`, kalibrację | hipotezy z budżetem µs (Amdahl z `attacked.share_ms`) do `queue.jsonl` | nie mierzy |
| Implementer | 1 hipotezę + wybrane playbooki | łatka za przełącznikiem, `card new/fill/check/register` | nie uruchamia `verify` bez `--dry-run`, nie czyta `sealed/` |
| Planista (Main) | wszystko | `factory verify` w oknie GPU, decyzje cyklu | nie poprawia ledgera |
| Weryfikator (kod) | kartę, diff, binarki | G0–G5, jedyny zapis werdyktów | — |
| **Rewriter** (świeży kontekst) | publiczny opis zadania + oczyszczoną trajektorię `CONFIRMED` (bez komunikatów harnessu, bez liczb z pomiaru jako „celu”) | playbook: kroki, komendy profilu, pułapki, które reguły odpaliły, warunki stosowalności | nie widzi sealed ani ledgera poza własnym wierszem |
| **Recenzent przecieku** (świeży) | tylko playbook + publiczne zadanie | schemat; zakaz hunków diffu (8-gramy jak R36 vs diff, próg 0); zakaz treści sealed; zakaz „wpisz X, żeby wyszło Y” | — |
| **Replayer** (świeży Implementer) | tylko playbook + **cel transferowy** | pełny przepływ karty | nie widzi oryginalnego diffu ani trajektorii |
| Człowiek | — | zgoda na numerykę (KLD, NEAR-TIE), merge, zmianę harnessu, wydatki | — |

**Przepływ jednego cyklu:**
1. Kolejka rankowana przez przewidywany zysk × P(`CONFIRMED`) / minuty GPU. Prior P z kalibracji ledgera, czyli
   dziedziczony krytyk.
2. Implementer → karta → `register` (zamrożenie przed pomiarem) → Planista `verify`.
3. `CONFIRMED` → Rewriter → Recenzent → playbook `draft`.
4. Replay R1 (ten sam cel od bazowego commitu, sprawdza odtwarzalność): tylko G0–G3, tanio.
   Replay R2 (cel transferowy: inny kwant, inny model LFM ↔ Qwen albo inna karta przez chmurę): pełny `verify`.
   Status: `reproduced` po R1, `transferred` po R2 `CONFIRMED`. **Do `skills/` trafiają tylko `transferred`.**
5. `INVALID` z oszustwem albo awarią → fixture → nowa reguła → `harness lock`. Weryfikator rośnie tylko w górę.
6. Koniec cyklu:
   - końcowe ABBA wszystkich zwycięzców razem vs baza na **nowym** zestawie zapieczętowanym (rotacja `sealed-vN`);
   - raport metryk meta (niżej);
   - playbooki z commitem bazy i datą ważności, ponowna walidacja R1 po dużym rebase.

**Artefakty** (nowe obok istniejących):
- `factory/queue.jsonl` (15f §5.5, niezbudowane);
- `factory/skills/<id>.md` (frontmatter: `source_ledger: <seq>/<sha8>`, `status`, `base_commit`, `transfer_ledger`,
  `expires`);
- `factory/trajectories/<verify_id>.jsonl.zst` (oczyszczone transkrypty, kompresja ze względu na SSD);
- kalibracja jako widok z ledgera, bez osobnej bazy.

**Metryki meta**, czyli czy samodoskonalenie w ogóle zachodzi:
- `CONFIRMED` na godzinę GPU;
- minuty GPU na `CONFIRMED`;
- odsetek `INVALID` z winy agenta;
- mediana |zmierzone / przewidziane| (15f X5);
- odsetek playbooków `transferred`.

Liczone osobno dla ramienia **z** `skills/` i **bez** (losowy przydział hipotez, jak kontrola DGM).

### 5.4 Bramki bezpieczeństwa sprzętu (twarde, sprawdzane kodem, nie promptem)

| # | bramka | źródło |
|---|---|---|
| H0 | agenci nigdy nie dotykają GPU; jedyną drogą jest `factory verify` Planisty: `flock /tmp/gpu.lock flock /tmp/quiet.lock timeout 290`, `pgrep` produkcji, preflight R08/R09/R14/R15 | README fabryki, wiersze 186–193 |
| H1 | `gpu-guard` przez cały blok; VRAM ≥ 85 °C albo hotspot ≥ 90 °C oznacza pauzę; wentylator 100% | [18 §6.1](18-nastepna-fala.md), wiersze 515–518 |
| H2 | `GGML_HIP_PM4=0`, chyba że karta dotyczy PM4 i Pm4Fix ogłosił bezpieczeństwo | [17](17-gpu-page-fault.md), wiersze 22–24; 18, wiersz 519 |
| H3 | **pierwszy page fault, timeout ringu albo reset = kwarantanna sha256 builda** (lista czytana przez G0), pauza całej pętli, pobudka człowieka; żadnego „odrzuć i powtórz” | decyzja `2026-10-19-bezpieczenstwo-sprzetu`; AGENTS.md, wiersz 5 |
| H4 | wyłącznik pętli: sprawdzenie `journalctl -k` **ze wszystkich bootów od startu cyklu** (`-b -N`) przed każdym blokiem, jednorazowo, nie w pętli | lekcja „agent nie patrzył na temperatury” (resety w bootach −2, −1, 0) |
| H5 | nowy kernel: najpierw R28/R29 statycznie i emulator ISA tam, gdzie istnieje (wiki `metody/emulator-isa.md`), potem G1 `test-backend-ops` tylko dotkniętych opów jako krótki nadzorowany smoke; dopiero potem G4 | 18, wiersze 520–522 |
| H6 | budżet: ≤ 60 min GPU pętli na dobę i ≤ 15 h na 30 dni; ≤ 2 kolejne `INVALID` sprzętowe kończą cykl | 18, wiersz 532 |
| H7 | denylista diffu (R23) rozszerzona o sysfs, `amdgpu` parametry, `pp_od_clk_voltage`, `power_cap`, `sudo`; agent bez sudo; **zakaz zmian zegarów, napięć i limitów mocy** | 18, wiersz 528 |
| H8 | produkcja na :8080 nietknięta (`pgrep -x llama-server` + `/proc/*/cmdline`) | 18, wiersz 523 |
| H9 | SSD: trajektorie kompresowane, logi runów rotowane, zakaz lokalnych zrzutów hidden states (to tylko chmura) | `[SZACUNEK]` |
| H10 | chmura: watchdog z deadline i limitem kosztu, samozniszczenie (wzór `cloud/watchdog.sh` z raportu 11), `destroy` zaraz po pomiarze | AGENTS.md, wiersz 4 |
| H11 | CPU: buildy `nice -n 10 -j6`, skrypty `nice -n 19`, wątki ≤ 4; bez pętli odpytujących | polecenie użytkownika 2026-10-19 |

### 5.5 Ile to może dać (arytmetyka)

- **Przepustowość weryfikatora.** Na twierdzenie: Qwen MTP ~45 min, LFM ~20 min, llama-bench ~15 min (README fabryki,
  wiersze 196–200). Przy 12–15 h na 30 dni to **16–60 werdyktów na miesiąc**. Pętla nie zwiększy tej liczby. Może
  zwiększyć tylko:
  - (a) odsetek `CONFIRMED` na werdykt;
  - (b) odsetek prób, które w ogóle docierają do G4 bez `INVALID`.
- **Punkt odniesienia historyczny:**
  - tylko 25/70 commitów ma w treści dowód „przed → po” ([15f](15f-agentowa-nauka.md), wiersz 39);
  - lista wyników negatywnych jest długa (PM4-PDL, głowica MTP ±2%, DFlash2, GU_BLOCK w szumie).

  Gdyby odsetek trafień wzrósł np. z 20% do 30% `[SZACUNEK]`, to przy 30 werdyktach na miesiąc daje to +3
  potwierdzone zyski miesięcznie. Realny odsetek zmierzy dopiero P2.
- **Czego pętla nie zrobi:** nie znajdzie mnożników strukturalnych typu MTP czy lookup. Te przyszły z pytań człowieka
  i architektury ([02](02-autotuning-i-agenci-kerneli.md), wiersz 206). Playbooki przenoszą *techniki* (VOPD epilog,
  fuzje, strojenie) na nowe pary (GPU, model). To jest dokładnie produktowa „fabryka przepisów” (wiki
  `produkt/produkt-fabryka.md`: cel ≤ 7 dni od premiery modelu).

### 5.6 Kompatybilność z naszymi zasadami

- Bezstratność: pętla nie zmienia klas poprawności. `BIT`/`SAME-TOK` automatycznie, `KLD`/`NEAR-TIE` zawsze
  `NEEDS-HUMAN`.
- MTP, lookup, PM4, kvq: każdy profil fabryki (`qwen-mtp`, `qwen-plain`, `lfm`) mierzy end-to-end, więc interakcje
  łapie G4.
- Fabryka nie była jeszcze uruchomiona na GPU ([16h](16h-fabryka-v1.md), wiersze 3, 209–214). Bez tego „verified” jest
  pustym słowem, dlatego P0 idzie pierwsze.

### 5.7 Pierwszy mały pilot

**P0: walidacja weryfikatora (~20 min GPU, $0).**
`./factory verify claims/2026-10-17-mmq-epi-0070.json` (16h §4.5).
- Oczekiwane: `NEEDS-HUMAN` (R29) albo werdykt z pomiaru.
- Kill: weryfikator daje `INVALID` z przyczyn harnessu (A/A > próg, timeout bloku). Wtedy najpierw naprawa fabryki,
  pętla stoi.

**P1: retro-RSR na łatce 0070 (~60–80 min GPU, tokeny agentów, $0 chmury).**
Wybór, bo:
- łatka ma pełny, bitowy dowód: pp4096 1099.5 → 1123.2 t/s, +2.2%, MUL_MAT 2486/2486 (wiki `kernele/mmq-epilog.md`,
  wiersze 21–24);
- metryka jest tania (llama-bench ~15 min na twierdzenie);
- są naturalne cele transferowe: technika objęła tylko Q4_K/Q5_K przy J ≥ 48, a J = 16 tracił i Q5_K J = 128 spillował
  (tamże, wiersz 17).

Kroki:
1. Rewriter pisze playbook z transkryptu i raportu `round6/mmq-epilogue.md`. Recenzent sprawdza przeciek (0 8-gramów
   z diffu `ae1ef6a97`).
2. Cele transferowe:
   - T1: ten sam epilog dla innego typu MMQ z realnym udziałem w prefillu (Q6_K albo Q8_0, wybór po `15a-ggufls.py`
     na GGUF Qwena/LFM, CPU);
   - T2: wariant J = 16/32, przy którym oryginał tracił.
3. Ramiona: A = świeży Implementer z playbookiem; B = świeży Implementer z samym opisem celu. Ten sam model, ten sam
   limit tokenów i czasu. 2 cele × 2 ramiona = **4 karty** × ~15–20 min GPU.
4. Mierzymy: dotarcie do karty z zaliczonym G0–G3, werdykt, tokeny, czas ścienny, minuty GPU.

Kill P1:
- k1: recenzent nie przepuszcza żadnego playbooka bez kopiowania hunków. Wtedy playbook = łatka, a pomysł nie przenosi
  się na nasz kod.
- k2: ramię A nie dochodzi do G3 na żadnym celu albo zużywa ≥ tokenów B. Playbook bezużyteczny.
- k3: jakikolwiek fault lub reset. Stop według H3.

Przejście do P2: A osiąga `CONFIRMED` albo `NULL` z zaliczonym G3 na ≥ 1 celu przy ≤ 50% tokenów B, albo A
rozwiązuje to, czego B nie rozwiązuje. To pilot wykonalności (n = 4), nie dowód.

**P2: jeden cykl RSI-F (~10 hipotez z kolejki raportu 18, np. #5 kvq jednego przejścia, #15 prefill).**
- Losowy przydział z/bez `skills/`, ≥ 10 werdyktów na ramię, w budżecie 30 dni.
- Kill: po 20 werdyktach ramię ze `skills/` nie ma ≥ 1.5× `CONFIRMED`/werdykt **ani** ≥ 30% mniej minut GPU na
  `CONFIRMED`. Wtedy wyłączamy pętlę zewnętrzną, a fabryka z regułami zostaje.

---

## 6. Ryzyka i otwarte pytania

- **Goodhart na fabryce.** Agent optymalizowany werdyktem szuka luk weryfikatora (DGM: hacking częstszy przy jawnych
  kontrolach). Obrona: sealed + rotacja, R36, reguły z fixture'ów, implementer bez dostępu do kodu fabryki. Izolacja to
  dziś konwencja + hashe, nie piaskownica (16h §5), i to trzeba wzmocnić przed P2 (osobny użytkownik systemowy dla
  agentów `[INFERENCE]`).
- **Starzenie playbooków po rebase.** Data ważności + R1 po rebase.
- **Mała liczba prób.** Przy 16–60 werdyktach miesięcznie efekt pętli zobaczymy dopiero po 1–2 miesiącach.
- **Kąt 1:** przeniesienie z Terminus-2 na omp nieznane; regresja PL; dłuższe trajektorie zjadają zysk z jakości.
- Otwarte: czy Terminal-RSI-27B wyjdzie i z jaką licencją; czy jego głowica MTP będzie trenowana (w RSR-27B nie była).

---

## 7. Źródła

Zewnętrzne (sprawdzone 2026-10-19):
- Terminal-RSI: [arXiv 2610.22192](https://arxiv.org/abs/2610.22192); strona
  [jyyang26.github.io/terminal-rsi](https://jyyang26.github.io/terminal-rsi/) („Code soon / Model soon”);
  `github.com/jyyang26/Terminal-RSI` HTTP 404.
- RSR: [arXiv 2610.02826](https://arxiv.org/abs/2610.02826) (759 zadań, 2 001 → 11 094 trajektorii, TB 2 pass@3
  57.0 → 74.2%); model [IntelligenceLab/RSR-27B](https://huggingface.co/IntelligenceLab/RSR-27B) (Apache-2.0; indeks
  safetensors: `mtp.*` w `model-missing-from-origin-00002`).
- Terminal-Bench: [2.1](https://www.tbench.ai/news/terminal-bench-2-1) (89 zadań, poprawki 28),
  [4.0](https://www.tbench.ai/news/terminal-bench-4-0) (usunięte 2 zadania za „public solutions”).
- TMax: [arXiv 2606.23321](https://arxiv.org/abs/2606.23321). DGM: [arXiv 2505.22954](https://arxiv.org/abs/2505.22954).
  ReasoningBank: [arXiv 2509.25140](https://arxiv.org/abs/2509.25140). AlphaEvolve:
  [arXiv 2506.13131](https://arxiv.org/abs/2506.13131).
- Ceny H100: [Vast $1.73/h](https://vast.ai/pricing/gpu/H100-SXM), [GPU Economy $3.53/h](https://gpueconomy.com/gpu/h100-sxm),
  [Ornn $2.78/h](https://data.ornn.com/markets/h100-sxm).

Lokalne:
- `~/qwen-opt/factory/README.md`: wiersze 71–99 (bramki, werdykty), 186–200 (GPU, koszt), `ledger.jsonl` (2 wiersze, 16.10).
- [16h](16h-fabryka-v1.md): wiersze 3, 209–231. [15f](15f-agentowa-nauka.md): wiersze 22–39, 141–147, 376–407.
  [18](18-nastepna-fala.md): wiersze 509–532. [17](17-gpu-page-fault.md): wiersze 8–24.
- [10](10-post-training.md): wiersze 365, 370, 374, 385. [11](11-mtp-pl-pilot.md): wiersze 5, 8.
  [02](02-autotuning-i-agenci-kerneli.md): wiersze 191–206. [05](05-chmura-gpu-do-testow.md): wiersz 15.
  [16g](16g-lfm-moe-pasmo.md): wiersz 9.
- wiki: `kernele/mmq-epilog.md` (wiersze 17–24), `decyzje/2026-10-19-bezpieczenstwo-sprzetu.md`,
  `metody/playbook-optymalizacji.md`, `produkt/produkt-fabryka.md`, `metody/emulator-isa.md`; `~/KERNEL/AGENTS.md`,
  wiersze 3–6.

---

## Do bazy wiedzy

| folder | tytuł (plik) | co wpisać | liczby i źródło |
|---|---|---|---|
| `research/` | Raport 21h: Terminal-RSI i RSI jako metoda (`raport-21h-rsi.md`), nowa | RSI = 2 cykle expert iteration + PPO; wynik realny co do kierunku, przeszacowany; kąt 1 = adoptuj RSR-27B + E1; kąt 2 = pętla RSI-F na fabryce, pilot P0–P1 | TB 2.1 51.7 → 86.5, TB 4.0 0 → 19.84 (s. 7); koszt ~1.5–2.5 tys. H100-h `[SZACUNEK]` (§3.5) |
| `repo/` | RSR-27B (`rsr-27b.md`), nowa | Qwen3.8-27B po RSR + RL, Apache-2.0, `qwen3_5`; **głowica MTP i wizja skopiowane z bazy** (`model-missing-from-origin-*`), więc przed użyciem z MTP trzeba dopasować głowicę (pipeline 11) | HF API 2026-10-19; RSR TB 2 pass@3 57.0 → 74.2 ([2610.02826](https://arxiv.org/abs/2610.02826)) |
| `ludzie-firmy/` | Tencent Hy Frontier / IntelligenceLab (`tencent-terminal-rsi.md`), nowa | Zespół T1, RSR, LHTB, SWR, Terminal-RSI; benchmarki TB-Hard/LHTB/SWR własne; Terminal-RSI-27B niewydany | s. 13–17 bibliografia; strona projektu |
| `lekcje/` | „Verified” = przeszedł testy, nie poprawny (`lekcja-verified-to-nie-poprawny.md`), nowa | Rust–C: fuzz przeszedł, a obliczenia delegowane do Pythona; u nas luka G2 (prefill) | s. 13; 16h, wiersz 225 |
| `lekcje/` | Wybór checkpointu na teście = klątwa zwycięzcy (aktualizacja [[zestaw-odlozony]]) | Terminal-RSI wybrał krok 18 z wiedzą o benchmarkach; krok 20 −2.4…−3.0 pp; nagrodę SPR zaprojektowano na widzianych danych | s. 8, 19, 20 |
| `metody/` | Pętla RSI-F (`petla-rsi-f.md`), nowa, `status: do-sprawdzenia` | Role Rewriter / Recenzent przecieku / Replayer; playbook do `skills/` tylko po transferze `CONFIRMED`; SPR w rankingu; krytyk = kalibracja + reguły; bramki H0–H11; metryki meta z ramieniem kontrolnym | ten raport §5.3–5.4 |
| `eksperymenty/` | Pilot P0/P1 retro-RSR na 0070 (`2026-10-xx-retro-rsr-0070.md`), szkic | 4 karty (2 cele × 2 ramiona), ~60–80 min GPU, kill k1–k3 | §5.7; `kernele/mmq-epilog.md`, wiersze 17–24 |
| `eksperymenty/` | E1: RSR-27B vs Qwen3.8-27B w naszym silniku (`2026-10-xx-e1-rsr27b.md`), szkic | TB 2.1 89 × 2 × 2 + omp-bench-20 (holdout czasowy) + PL + MTP tok/krok; ~$40–70; kill ≥ 8 pp / ≥ 3/20 / PL ≥ 40% / tok/krok ≥ 0.9× | §4.5 |
| `AUDYT.md` | wiersze dla liczb powyżej | niespójne mianowniki: TB 4.0 19.84% = 25/126 (2 przebiegi), Hard 69.50% = 139/200, TB 3.0 16.95% ≠ k/70, TB 2.1 51.70% ≠ k/89; SWR 3 → 6/100 p = 0.50; LHTB 0 → 5/46 p = 0.056 | §3.3 (rachunek własny na liczbach z s. 7, 21, 22) |
