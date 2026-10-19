# 18 — Następna fala: 15 pomysłów ponad dzisiejszy „roofline” (XTX + NVIDIA)

Data: 2026-10-19. Autor: podagent NextWave. Zakres: wyłącznie CPU i źródła zewnętrzne, bez GPU i bez chmury.
Wejście: `BENCHMARKI-PRZED-PO-2026-10-19.md` (dalej `BPP`), raporty 15, 15a–15f, 16a–16k, 17, wiki (`metody/wyniki-negatywne.md`, `lekcje/*`, `modele/*`).
Nowe pomiary CPU w tym raporcie:
- (a) workload agentów z sesji omp (§2);
- (b) rozkład bajtów Qwena z nagłówka GGUF (§3);
- (c) pilot certyfikowanej głowicy LM na prawdziwych stanach ukrytych Qwena (§4, pomysł #14): **KILL dla Qwena**.

Oznaczenia: `[SZACUNEK]` = wyliczenie, nie pomiar; `[INFERENCE]` = wniosek bez bezpośredniej obserwacji; `[NIEZWERYFIKOWANE]` = twierdzenie źródła zewnętrznego, którego nie sprawdziliśmy.

## 0. Najważniejsze

1. **„Roofline” liczony w bajtach wag na token nie jest sufitem, bo dzielnik nie musi wynosić 1 token.**
   - Qwen plain ma roofline 57 t/s przy 960 GB/s.
   - Ten sam silnik daje dziś 109 t/s z MTP i 401 t/s na code-edit z ogonem lookupu, czyli 7× roofline plain.
   - Następne mnożniki są dwa: (i) więcej tokenów na jeden odczyt wag (wiele strumieni, lookup dla LFM, tańsza szeroka weryfikacja); (ii) mniej bajtów na odczyt (przejścia po KV, kwant 4.25 bpw; głowica tylko dla LFM, jeśli przejdzie bramkę).
2. **Nowe fakty o workloadzie agentów** (21 673 unikalne tury omp, 34 h aktywności; §2):
   - przez **37% czasu aktywności w locie są ≥ 2 żądania** (średnia współbieżność 1.97), a nasz serwer ma `-np 1`, więc je szereguje;
   - prefill to **34%** czasu modelu, dekodowanie 57%, narzędzia 9% (przeliczone na tempo Qwena na XTX);
   - mediana kontekstu > 100k, więc liczy się atencja przy długim kontekście.
3. **Top 3 lokalnie** (zysk × prawdopodobieństwo / wysiłek):
   - **#2 lookup-spekulacja dla LFM** (nie było jej; code-edit ×2.3–2.8 `[SZACUNEK]`, 1–2 dni);
   - **#3 oficjalny QAD-Q4_0 LFM na XTX** (+9–14%, 1 dzień, stratne, decyzja użytkownika);
   - **#4 serwer wielostrumieniowy z batched MTP** (rój agentów ×1.6–1.8 wall-clock `[SZACUNEK]` z prawdziwego histogramu współbieżności).
   - Na NVIDIA: **#1 ogon lookupu W16 na CUDA** (gotowy kod wspólny, 3090 code-edit 105 → ~200 t/s `[SZACUNEK]`).
4. **Rzadkość aktywacji (TEAL/CATS) nie pasuje do Qwena z MTP.** Weryfikacja 5 tokenów czyta sumę aktywnych neuronów: przy 50% niezależnej rzadkości aktywne jest 1 − 0.5⁵ = 97%. Ma sens tylko dla LFM, który dziś nie spekuluje (#13).
5. **Infinity Cache (MALL) nie ratuje dekodowania batch 1.** Wewnątrz kroku nic nie jest czytane dwa razy. Między krokami odległość ponownego użycia wynosi ~16.8 GB wag przy 96 MB MALL (§3.5). To uzupełnia negatyw X3 z 16a o arytmetykę.
6. **Pilot certyfikowanej głowicy (CPU, 73 138 prawdziwych stanów Qwena, zwalidowane na zapisanych log-probach): KILL dla Qwena.**
   - Przy bazie PCA r = 0.36·d (jak knlp) baza łapie tylko 87% energii h, ρ/‖h‖ = 0.39.
   - Certyfikat top-1 wymaga otwarcia 97.5% bloków przy N=1 i 98.3% przy N=5; top-20 99–100%.
   - Głowica Q6_K jest już ~2.4× tańsza od bf16 u knlp, więc sam cień kosztuje 22–44% bajtów (§4 #14).
   - Dla LFM pozostaje tania bramka CPU.
7. **Kolejność eksperymentów ≠ ranking.**
   - Najpierw tanie bramki CPU i jeden 15-minutowy pomiar krzywych V(N) dla obu modeli; od niego zależą #2, #4, #5, #8.
   - Plan 30 dni (§6) zakłada jedno zadanie GPU naraz pod `flock`, `gpu-guard` i `GGML_HIP_PM4=0` do czasu poprawki Pm4Fix.

---

## 1. Czego nie proponuję ponownie (zmierzone negatywnie) i co jest nowym kątem

| zmierzone negatywnie | źródło | czy wracam? |
|---|---|---|
| PM4-PDL (X1), prefetch do MALL „touch” (X3) | 16a | nie; §3.5 dodaje arytmetykę, dlaczego MALL nie pomoże |
| fuzja gate+up w MMVQ 2–8 kolumn, nontemporal ładowania, LDS 16 B, warianty wierszy/fal MoE | wiki `wyniki-negatywne`, 16g §5 | nie; repack Qwena (#12) tylko po teście „sufitu wzorca” |
| douczanie głowicy MTP Qwena (±2%) | raport 11 | nie dla Qwena; **dla LFM nie ma żadnej głowicy** (#9), to inna sytuacja |
| lookup nadpisujący MTP, DFlash2 + lookup, bloki 32/64, kontroler szerokości | 15b, 16b | nie; nowy kąt to globalny cache sufiksów poza kontekstem (#6) i lookup dla LFM (#2) |
| sprzężone próbkowanie (netto ≈ 0) | 16k | to inna reguła: block verification (#10) zmienia regułę akceptacji, nie RNG; rozstrzyga symulacja offline |
| hak MTP w grafie prefillu (≤ 2.5%) | 16f E3 | #11 dotyczy kroku dekodowania (d1 następnego kroku w grafie weryfikacji), nie prefillu |
| podwójny bufor MMQ (wolniej) | wiki `qwen-runda-5` | #15 tylko po profilu per kernel prefillu |
| trellis KT ~3 bpw ≈ Q3_K_XL | 15e | #9 to IQ4_KS 4.25 bpw (skalarny, tani dekod), nie trellis 3 bpw |
| kompresja skal K-quantów (sufit 2.19%) | 15e | nie |

---

## 2. Co agenci naprawdę robią (nowy pomiar CPU, $0)

Dane:
- 458 plików sesji omp (`~/.omp/agent/sessions`, 1.1 GB);
- deduplikacja po `responseId` / `toolCallId`, bo sesje-dzieci kopiują wiadomości rodzica: 24 878 duplikatów;
- **21 673 unikalne tury** asystenta.

Tokeny pochodzą z `usage` API, czyli z tokenizera Claude. To proporcje, nie tokeny Qwena `[INFERENCE]`. Skrypty jednorazowe w `/tmp`, nie zachowane.

| wielkość | p10 | p25 | mediana | p75 | p90 | średnia |
|---|---|---|---|---|---|---|
| nowe tokeny wejścia na turę (input + cacheWrite = praca prefillu) | 431 | 734 | 1 476 | 3 190 | 6 743 | 4 352 |
| tokeny wyjścia na turę (z thinking) | 124 | 223 | 404 | 795 | 1 779 | 885 |
| kontekst na turę | 64k | 123k | 219k | 341k | 484k | 250k |
| czas narzędzia (ms) | 0 | 0 | 0 | 9 | 820 | 1 143 |

- **Proporcja prefill : dekod = 4.9 : 1 tokenów.**
- Model czasu Qwena na XTX: prefill 850 t/s (`BPP:30`), dekod 105 t/s (MTP przy długim kontekście, `BPP:33`).
  - Udziały: **prefill 34.4%, dekod 56.6%, narzędzia 8.9%**.
  - Dla LFM (prefill ~5000, dekod ~300 t/s) prefill to tylko ~17% `[SZACUNEK]`.
- **Współbieżność** (czas aktywności ważony liczbą żądań w locie, 33.9 h):

| żądań w locie | 1 | 2 | 3 | 4 | 5 | 6 | 7 | ≥ 8 |
|---|---|---|---|---|---|---|---|---|
| udział czasu | 63.1% | 14.5% | 7.2% | 5.9% | 4.1% | 2.2% | 1.1% | 1.8% |

Średnia 1.97. Te sesje obsługiwał równoległy dostawca. Lokalnie z `-np 1` wszystko poza pierwszym żądaniem czeka w kolejce.

- **15% tur wywołuje ≥ 2 narzędzia naraz** (średnio 1.18 wywołania na turę).
- Konsekwencje dla rankingu:
  1. wielostrumieniowość (#4) jest realnym, nie hipotetycznym mnożnikiem;
  2. długi kontekst (mediana > 100k; 15b §6.2: mediana ≥ 113k przy wyjściach agenta) przesuwa wagę na atencję (#5, #7);
  3. prefill (#15) to trzecia część czasu modelu Qwena, ale jest drogi do ruszenia.

---

## 3. „Roofline to nie sufit”: arytmetyka dla obu modeli na XTX

Przyjęte pasmo: 960 GB/s nominalnie, 900 GB/s realny strumień (`lfm-decode-round4` §1b: 789–925 GB/s).

### 3.1 Qwen3.8-27B UD-Q4_K_XL: bajty na token dziś

Rozkład z nagłówka GGUF (`15a-ggufls.py`, ten raport):
- plik 17.55 GB;
- `token_embd` 0.715 GB idzie przez get_rows i nie jest strumieniowany;
- MTP `blk.64` 0.351 GB, czytany tylko w drafcie.

| składnik (na krok dekodowania) | GB | uwagi |
|---|---|---|
| MLP (gate/up/down × 64 warstwy) | **10.62** | 17.11 B parametrów → **4.96 bpw** średnio (IQ4_XS/Q3_K/Q4_K/Q5_K) |
| głowica `output.weight` Q6_K [5120 × 248 320] | **1.043** | 6.2% bajtów; czytana co krok w całości |
| GDN qkv/gate/ssm_out + atencja q/k/v/o (48 + 16 warstw) | 4.82 | |
| **suma wag (plain)** | **16.48** | 15a liczył 16.83 z blokiem MTP |
| stan GDN: 48 warstw × 48 głowic × 128 × 128 × 4 B | 0.151 odczyt + 0.151 zapis | f32 `[INFERENCE]` z kształtów `ssm_*` |
| KV q4_0: 16 warstw × 4 głowy KV × 256 × 2 × 0.5625 B | **18 432 B/token kontekstu** | 0.037 GB @2k; 0.60 @32k; **2.08 @113k** |

Zgodność: ji-farthing mierzy 19.125 MiB/1024 tokenów = 19 584 B/token, czyli nasze 18 432 + 1 152 warstwy MTP.

| tryb | bajty/krok | roofline 960 GB/s | zmierzone | % roofline |
|---|---|---|---|---|
| plain @2k | 16.82 GB | 17.5 ms → **57.1 t/s** | 23.15 ms → 43.2 t/s (`BPP:27`) | 75.7% |
| plain @113k | 18.86 GB | 50.9 t/s | nie zmierzone | — |
| MTP n=4 @2k (V5 + 4 drafty) | 16.86 GB weryfikacji + draft 3.62 ms (15b §6.1) | 19.7 ms → **154 t/s** przy 3.02 tok/krok | 27.74 ms → 109.0 t/s (`BPP:25`) | 71% |
| MTP @113k (dziś 2 przejścia po KV na weryfikację N=5) | 20.95 GB | 23.9 ms → 126 t/s | 94k: 100.6 t/s (`BPP:33`, przed PM4) | ~80% |

**Które bajty można usunąć (Qwen):**

| bajty | ile | bezstratne? | pomysł |
|---|---|---|---|
| drugie przejście po KV przy N=5 (kafle 16 wierszy: `ceil(6·5/16)` = 2) | −2.08 GB/krok @113k; przy N=16: −5 × KV | **tak, bitowo** | #5 |
| głowica: odczyt wierszy, które nie mogą wygrać (certyfikat knlp) | **pilot CPU: ~0** (97.5% bloków przy N=1, r = 0.36·d; §4 #14) | tak | #14, KILL dla Qwena |
| głowica draftu 64k w 4 przebiegach (przybliżony argmax z cienia) | ≤ −0.5 ms/krok `[INFERENCE]`, nieprzetestowane, wątpliwe przy 77% energii dla r = 1024 | tak (drafty nie zmieniają wyjścia) | #14 |
| wagi 4.96 → 4.25 bpw (IQ4_KS) | −2.5 GB (×0.847) | **nie** (bramka KLD) | #9 |
| odczyt + zapis stanu GDN w f32 | 0.30 GB (1.8%) | nie (bf16) | odrzucone (§5) |
| MLP: rzadkość aktywacji | do −3.5 GB w plain, ~0 przy MTP (suma po 5 tokenach) | nie | odrzucone dla Qwena (§5) |

**Teoretyczne t/s po usunięciu** (model: krok = bajty/960 GB/s + draft; `[SZACUNEK]`):

| wariant | @2k: roofline / przy 85% sprawności | @113k: roofline / 85% |
|---|---|---|
| dziś (MTP, 3.02 tok/krok) | 154 / — (zmierzone 109) | 126 / — (zmierzone ~100) |
| bezstratne: KV jedno przejście (#5), d1 w grafie (#11: draft 2.1 → 1.6 ms roofline) | **158 / 136** | **142 / 122** |
| + IQ4_KS (stratne) | 185 / 160 | 164 / 141 |
| + 2 strumienie (rój agentów, §4 #4) | ×1.6–1.7 przepustowości łącznej | ×1.5–1.6 |

Wniosek: bezstratnie jest jeszcze do ~+25% na pojedynczym strumieniu w kroku MTP (136 vs 109 t/s @2k). Taki zysk wymaga jednak 85% sprawności strumienia, dziś jest 71–76%. Głowica nie pomoże (pilot). Większe mnożniki dają tokeny na odczyt: lookup na kopiach ×2.4 (zmierzone) i wielostrumieniowość ×1.6–1.8 `[SZACUNEK]`.

### 3.2 LFM2.5-24B-A2B Q5_K_M: bajty na token dziś

Z 15a §3.1: eksperci 4/64 1.016 GB, shortconv 0.347, głowica (tied `token_embd` Q6_K, [2048 × 128 000]) **0.215 GB = 12%**, gęste FFN 0.106, atencja 0.073, router 0.020; razem **1.777 GB**. KV q8_0: 10 warstw × 8 głowic × 64 × 2 × 1.0625 B = **10 880 B/token** (0.36 GB @32k, 1.23 GB @113k).

| tryb | bajty | roofline 960 GB/s | zmierzone | % |
|---|---|---|---|---|
| @0 | 1.78 GB | 1.85 ms → **540 t/s** | 3.40 ms → 293.7 t/s (`BPP:55`) | 54% |
| @98k | 2.84 GB | 338 t/s | 213.0 t/s (`BPP:62`) | 63% |

Czas LFM: 1.95 ms to strumień wag, a **1.45 ms to pula „DRAM prawie bezczynny”**: narzut matvec 0.70, małe kernele 0.53, host 0.22 (15a). Fizyczna podłoga z 15a: 2.56 ms (390 t/s).

| bajty / czas | ile | bezstratne? | pomysł | ms/token po zmianie `[SZACUNEK]` |
|---|---|---|---|---|
| głowica 215 MB: certyfikat zamiast pełnego odczytu | −0.17 GB, jeśli LFM przejdzie bramkę (na Qwenie KILL) | tak | #14 | 3.42 → 3.24 (309 t/s) |
| QAD-Q4_0 zamiast Q5_K_M (13.58 / 15.86 GiB) | −0.26 GB | nie (oficjalny QAD Liquid) | #3 | 3.42 → 3.14 (318 t/s) |
| KV q8_0 → 4 bity z rotacją przy długim kontekście | −0.58 GB @98k | nie | #7 | @98k 4.69 → ~4.05 (+15%) |
| rzadkość ekspertów (CATS, 40%, up+down) | −0.27 GB | nie | #13 | → 3.12 (+10%) |
| pula 1.45 ms (PM4/fuzje) | do −0.85 ms | tak | megakernel odrzucony (15a), PDL zabity (16a) | podłoga 2.56 |

Pełne złożenie (QAD + pula do 0.6 ms) daje 2.29 ms → 437 t/s; z certyfikatem głowicy, jeśli przejdzie, 2.13 ms → 470 t/s. To górna granica bez spekulacji, nie plan.

### 3.3 Tokeny na odczyt wag: tu jest prawdziwy zapas

| tryb (Qwen, XTX) | tok/krok | ms/krok | t/s | × roofline plain (57) |
|---|---|---|---|---|
| plain | 1 | 23.15 | 43.2 | 0.76 |
| MTP n=4 (czat) | 3.02 | 27.74 | 109 | 1.9 |
| MTP + ogon lookupu W16, code-edit (`mvs`) | 14.4 | ~35.9 | 400.9 (`BPP:79`) | **7.0** |
| k strumieni × MTP (§4 #4) | 3.02·k | V(5k) + draft | k=2: ~187, k=4: ~325 `[SZACUNEK]` | 3.3–5.7 |

LFM dziś ma **1 token na odczyt** i to jest jego największa luka. Szczegóły w #2, #4 i #8.

### 3.4 Model kosztu weryfikacji MoE (LFM), potrzebny do #2, #4, #8

Weryfikacja N tokenów czyta sumę ekspertów wszystkich N tokenów.
- Przy niezależnym routingu (pesymistycznie) u(N) = 64·(1 − (60/64)^N) ekspertów na warstwę.
- Bajty: B(N) = 0.761 GB (nie-eksperci) + 0.254 GB·u(N) (6.68 MB/ekspert × 38 warstw).
- Czas: T(N) ≈ 1.45 ms + B(N)/0.9 GB/ms. Kalibracja: T(1) = 3.42 ms, zmierzone 3.40.

| N | 1 | 2 | 3 | 4 | 5 | 8 | 16 |
|---|---|---|---|---|---|---|---|
| u(N) | 4.0 | 7.8 | 11.3 | 14.6 | 17.7 | 25.8 | 41.2 |
| B(N) GB | 1.78 | 2.73 | 3.62 | 4.46 | 5.24 | 7.32 | 11.23 |
| T(N) ms `[SZACUNEK]` | 3.42 | 4.48 | 5.47 | 6.41 | 7.28 | 9.58 | 13.93 |

Wnioski z modelu:
- tani drafter albo lookup opłaca się od α ≈ 0.4;
- LFM2.5-2.6B jako drafter nie: ma ten sam słownik 128 000 (sprawdzone w GGUF), ale 1.5 GB/token, czyli połowę kosztu celu;
- „self-spec” z top-1 ekspertem czyta 57% bajtów celu na token draftu, co daje wynik ujemny;
- **pierwszy pomiar GPU to T(N) dla N = 1..16** (§6, D1).

Literatura potwierdza zjawisko:
- „expert scattering”, EcoSpec ×1.62 dzięki wyborowi draftów pod koszt ekspertów (https://arxiv.org/abs/2607.12696);
- niestabilny koszt weryfikacji (https://arxiv.org/abs/2609.22156);
- MoESD (https://arxiv.org/abs/2505.19645);
- wpływ koaktywacji ekspertów (https://arxiv.org/abs/2609.22471).

### 3.5 Czego sprzęt nie da (arytmetyka, żeby nie wracać)

- **MALL 96 MB jako cache wag.**
  - Krok czyta każdą wagę raz. Następne użycie jest po ~16.8 GB (Qwen) albo ~1.8 GB (LFM) innych danych, więc przy LRU trafień nie ma.
  - Jedyny kandydat z ponownym użyciem między krokami to stan GDN Qwena: 151 MB f32 > 96 MB.
  - W bf16 (75 MB) przy wagach oznaczonych NOALLOC mieściłby się w MALL. Zysk ≤ 0.30 GB/krok (≤ 1.8%), stratnie.
  - NOALLOC istnieje w sterowniku dla PTE gfx11 (https://www.mail-archive.com/amd-gfx@lists.freedesktop.org/msg146311.html; Mesa umie wyłączyć MALL per bufor: https://www.phoronix.com/news/Mesa-22.2-Option-Disable-MALL). W HIP/KFD nie jest wystawiony `[NIEZWERYFIKOWANE]`. Odrzucone.
- **Draft MTP w MALL.** 4 przebiegi × ~0.53 GB (blok MTP 0.351 + głowica draftu `[INFERENCE]`) ≫ 96 MB. Zmieszczenie wymagałoby ~1.5 bpw, czyli straty akceptacji. Odrzucone.
- **VOPD / dual-issue / WMMA w dekodowaniu.** ATT pokazuje 85% czasu fali w `s_waitcnt vmcnt` (16g §1), więc VALU nie jest wąskim gardłem. WMMA ma sens w szerokiej weryfikacji (#4) i w prefillu (#15).
- **Podkręcanie pamięci / zmiana limitu 285 W.** Twarda zasada użytkownika z 2026-10-19 zakazuje optymalizacji kosztem bezpieczeństwa sprzętu. VRAM już dochodził do 90 °C. Nie proponuję.

---

## 4. Ranking top 15

Wynik = zysk (% na docelowym workloadzie) × prawdopodobieństwo / wysiłek (dni-agenta). Zysk podaję dla „mieszanki agenta” albo wskazanego workloadu, a nie dla najlepszego promptu.

| # | pomysł | model / karta | zysk | p | dni | wynik | bezstratne? |
|---|---|---|---|---|---|---|---|
| 1 | Ogon lookupu W16 na CUDA | Qwen, 3090 / 5060 Ti | code-edit ×1.8–2.3; mieszanka agenta +20% | 0.7 | 1 (+~$1) | 14 | tak (rozkład; md5 T=0 na XTX 11/11) |
| 2 | Lookup-spekulacja dla LFM (bez draftera) | LFM, wszystkie karty | code-edit ×2.3–2.8; mieszanka +20–40% | 0.65 | 2 | 10 | tak (rozkład) |
| 3 | Oficjalny QAD-Q4_0 LFM na XTX | LFM | +9–14% | 0.5 | 1 | 5.5 | **nie** |
| 4 | Serwer wielostrumieniowy: `-np k` + batched MTP/lookup | oba, wszystkie karty | rój agentów ×1.6–1.8 wall-clock | 0.5 | 7 | 5.4 | rozkład tak; bitowo nie |
| 5 | `kvq`: jedno przejście po KV dla wszystkich kafli N×G | Qwen (LFM też) | MTP @94–113k +8%; W16 @64k +12–15% | 0.6 | 5 | 1.2 | **tak, bitowo** |
| 6 | Globalny cache sufiksów (SuffixDecoding) | oba | mieszanka agenta +5–15% | 0.4 | 3 | 1.1 | tak |
| 7 | KV 4-bit z rotacją Hadamarda (długi kontekst) | LFM (Qwen +2%) | LFM @98k +15% | 0.35 | 6 | 0.9 | **nie** |
| 8 | Głowica EAGLE-3 dla LFM trenowana lokalnie | LFM | czat +23–37% | 0.3 | 12 | 0.75 | rozkład tak |
| 9 | IQ4_KS (4.25 bpw) dla Qwena | Qwen, 16–24 GB | plain +17%, MTP +14% | 0.35 | 7 | 0.75 | **nie** |
| 10 | Block verification przy T>0 | oba (gdy spekulacja) | czat T=1 +3–6% | 0.35 | 2 | 0.7 | rozkład tak |
| 11 | d1 draftu MTP liczony w grafie weryfikacji | Qwen | +2.5–3% | 0.6 | 3 | 0.6 | tak |
| 12 | Audyt sufitu wzorca + repack wag Qwena przy ładowaniu | Qwen | +10% | 0.3 | 8 | 0.38 | tak, bitowo |
| 13 | Rzadkość aktywacji ekspertów (CATS) | LFM | +5–10% | 0.25 | 8 | 0.28 | **nie** |
| 14 | Certyfikowana głowica LM (cel) + cień głowicy draftu | LFM (Qwen: **KILL w pilocie CPU**) | LFM +5–6% | 0.2 | 5 | 0.22 | tak |
| 15 | Prefill: 49% → 65% szczytu WMMA iu8 | Qwen | wall-clock agenta −8% | 0.25 | 10 | 0.2 | tak |

### #1 Ogon lookupu W16 na CUDA (3090, 5060 Ti)

- **Mechanizm.** Ten sam kod co na XTX (16b): `common_spec_lookup` w `common/speculative.cpp`, tryb 3 z łańcuchami, `LLAMA_SPEC_LOOKUP_W=16`. Kod jest wspólny dla backendów, więc brakuje tylko pomiaru V(N) na CUDA i A/B.
- **Zysk.**
  - XTX: `mvs` 166.2 → 400.9 t/s (×2.41) przy md5 T=0 identycznym 11/11 (`BPP:79`).
  - 3090: dziś 105.2 t/s code-edit (MTP4), Magnitude 156.1 (DFlash2 blok 8, 7.88 tok/krok, `BPP:116`, 16i §0). Przy ×1.8–2.3: **~190–240 t/s** `[SZACUNEK]`.
  - Mieszanka agenta +20%: 15b §6.2 (bash 20%, edit 26–38% pozycji z r ≥ 8).
- **Dowody.** 16b, 16i (Magnitude wygrywa sufitem bloku, nie kernelami), HyperQwen 15b.
- **Ryzyko.**
  - Na CUDA `kvq` liczy do 8 tokenów w jednym przejściu (wiki `kernele/fattn-kvq.md`). Dla W16 możliwa ścieżka MMA_F16 z buforem f16 całego KV, czyli drogo przy 64k (15d).
  - VRAM 16 GB na 5060 Ti.
- **Wysiłek.** 0.5–1 dnia, ~$1 Vast. **Poza planem lokalnym; wymaga zgody na chmurę.**
- **Kill.** `llama-bench -p 1,5,8,9,16 -n 0 -d 2048,32768` na 3090. Jeśli V16 − V5 > 15 ms @32k albo `mvs` < ×1.5 względem MTP4, kill.

### #2 Lookup-spekulacja dla LFM (bez draftera)

- **Mechanizm.**
  - LFM nie ma głowicy MTP ani DFlasha (wiki `modele/lfm2-5-24b-a2b.md`), więc dziś dekoduje 1 token na odczyt.
  - `common_spec_lookup` (16b) działa jako samodzielny drafter: propozycja tylko przy dopasowaniu sufiksu ≥ 6 tokenów; szerokość W ∈ {4, 8, 16} wg długości dopasowania i kosztu T(N) z §3.4, jak w EcoSpec.
  - Poza ogonami weryfikacja zostaje N=1, bez dodatkowego kosztu.
- **Zysk** (model §3.4, pesymistyczny niezależny routing).
  - W8: T(8) = 9.6 ms; przy ~7 przyjętych tokenach (Qwen `mvs` W8: 7.6 tok/krok, 16b §2) daje ~730 t/s.
  - W16: T(16) = 13.9 ms przy ~12 tokenach, czyli ~860 t/s.
  - Wobec dzisiejszego code-edit LFM 311.7–312.0 t/s (`BPP:114`): **×2.3–2.8** `[SZACUNEK]`.
  - Czat: lookup trafia w 13–15 krokach na ~4500 (16b §0), więc ≈ 0.
  - Mieszanka agenta +20–40%, ważona udziałami bash/edit/write z 15b §6.2 `[SZACUNEK]`.
- **Dowody.** 16b (mechanizm i bezstratność), SuffixDecoding (agentowe ×5.3 maks.; https://arxiv.org/abs/2411.04975), papiery MoE z §3.4.
- **Ryzyko.**
  - Kopiowany kod może mieć mniej skorelowany routing niż zakłada model; wtedy u(N) rośnie, choć model jest już pesymistyczny.
  - Weryfikacja MoE przy N>1 inną ścieżką (MMQ/MUL_MAT_ID wielokolumnowe) zmienia bity względem plain (wiki `modele/lfm-czulosc-na-podzial-batcha.md`), więc md5 T=0 może się różnić od plain. Bezstratność tylko rozkładowa.
  - `kvq` liczy do 8 tokenów w przejściu, więc W16 to 2 przejścia (koszt KV q8_0 przy długim kontekście).
- **Bezstratne.** Rozkładowo tak; bitowo nie (chyba że weryfikacja batch-invariant).
- **Wysiłek.** 1–2 dni (tryb bez MTP w istniejącym kodzie, gating, kontroler W pod T(N)).
- **Kill.** (a) Pomiar T(N) (§6 D1): T(8) > 13.6 ms (4 × T(1)) → zostaje tylko W4. (b) `copy_bench` `mvs` + copy przy T=0: < ×1.3 → kill. (c) `spec_sweep lfm`: spadek > 1% → zaostrzyć próg, a jeśli nie pomoże, kill.

### #3 Oficjalny QAD-Q4_0 LFM na XTX

- **Mechanizm.** Liquid wydał LFM2.5-24B-A2B po quantization-aware distillation w Q4_0, 13.58 GB. Na 5060 Ti: serwer 164.5 → 226.8 t/s względem upstreamu, Q4_K_M 207.86 (wiki `lfm2-5-24b-a2b`). Q4_0 ma najprostszy dekwant w MMVQ RDNA3 `[INFERENCE]`.
- **Zysk.**
  - Bajty 1.777 → ~1.52 GB (×0.856), T = 1.45 + 1.52/0.9 = 3.14 ms → 318 t/s (+9%).
  - Do tego prostszy dekwant Q4_0 w MMVQ `[INFERENCE]`; typ głowicy w pliku 24B QAD niesprawdzony (w lokalnym LFM2.5-2.6B-QAD-Q4_0 głowica jest Q6_K, czyli bez zysku na głowicy). Razem +9–14% `[SZACUNEK]`.
- **Jakość.**
  - Protokół KLD z 5060 Ti jest niejasny: QAD 0.2029 vs Q4_K_M 0.2008; PPL(Q)/PPL(Q8) = 0.869. QAD zmienia rozkład modelu, więc KLD do BF16 miesza „błąd” z „zamierzoną zmianą”.
  - Decyzja należy do użytkownika, jak przy KV q8_0 (wiki `decyzje/2026-10-14-lfm-kv-q8.md`).
- **Ryzyko.** Licencja LFM Open License v1.0 bez zmian. Jakość po polsku nieznana.
- **Wysiłek.** 1 dzień: pobranie, KLD na CPU, 20 min GPU.
- **Kill (CPU, przed GPU).**
  - KLD do BF16 (LFM BF16 ~48 GB mieści się w 62 GB RAM przez mmap; 2B aktywnych, więc CPU jest realny) na 5 korpusach z 16e (wiki / PL proza / czat / kod / long), plus 20 zadań z 16e.
  - Warunek: KLD(QAD-Q4_0) ≤ 1.2 × KLD(Q5_K_M) na każdym korpusie i brak regresji zadań; inaczej kill.
  - Dopiero po bramce: llama-bench ABBA i `spec_sweep lfm` 6 × 5 seedów.

### #4 Serwer wielostrumieniowy: `-np k`, batched MTP i lookup per slot

- **Mechanizm.**
  - Ciągłe batchowanie k żądań agentów. Jeden przebieg celu weryfikuje Σ(draft + 1) kolumn wszystkich slotów, więc wagi są czytane raz na krok dla k strumieni.
  - Upstream `common/speculative.cpp` ma już `n_seq` i samplery per sekwencja (`~/wt/lookup/common/speculative.cpp:182-406`).
  - Do zrobienia u nas:
    - stan MTP `pending_h` per sekwencja (dziś globalny; raport 12 §8 opisuje przeciek między requestami);
    - replay GDN i bufory wierszy per sekwencja;
    - cache grafu weryfikacji kluczowany kształtem batcha;
    - taśma PM4 per kształt, a do czasu Pm4Fix `GGML_HIP_PM4=0`;
    - unified KV `-kvu`;
    - chunked prefill (Sarathi-Serve, https://arxiv.org/abs/2403.02310), żeby 4k-tokenowy prefill jednego agenta (~4.7 s) nie zatrzymywał dekodowania innych.
- **Zysk (Qwen @2k)** `[SZACUNEK]`:
  - V(5k) z E2 (V5 24.14, V8 26.60, V9 27.97, V16 30.53; 16b §3) ekstrapolowane: V10 ≈ 28.3, V15 ≈ 30.2, V20 ≈ 32.5 ms;
  - draft k sekwencji w jednym batchu: 3.62·(1 + 0.1(k−1)) ms;
  - przepustowość łączna: k=1 109, **k=2 187**, k=3 263, k=4 325 t/s;
  - na strumień: 109 → 94 → 88 → 81 t/s.
  - Przy 113k każdy strumień dokłada własny odczyt KV 2.08 GB: dziś 2 przejścia ≈ 4.6 ms, po #5 2.3 ms; wtedy f(2) ≈ 1.6.
- **Zysk dla roju z histogramu §2.**
  - Czas pracy z `-np 1` = Σ w_k·k = 1.97 jednostki.
  - Z batchowaniem Σ w_k·k/f(k) ≈ 1.13, przy f(2..4) = 1.72 / 2.41 / 2.98 i f(≥5) = 3.3.
  - Daje to **×1.75 wall-clock** `[SZACUNEK]`; przy długim kontekście ×1.6.
- **Zysk LFM.** T(2) = 4.48 ms za 2 tokeny = 446 t/s łącznie (×1.53); T(4) = 6.41 ms = 624 t/s (×2.1) `[SZACUNEK]`.
- **Dowody.**
  - MTPLX 2.6.0: współbieżny MTP dla 2 agentów daje 1.6–2.25× per lane względem batchowania AR (https://mtplx.com/releases/2.6.0);
  - Marlin: prawie idealne skalowanie do batcha 16–32 przy W4 (https://arxiv.org/abs/2408.11743);
  - pułapki poprawności batch-spec (https://arxiv.org/abs/2510.22876).
- **Ryzyko.**
  - Każde z założeń jednej sekwencji w forku może dać ciche błędy.
  - VRAM: 2 × 113k = 4.2 GB KV + 2 × 151 MB stanu + checkpointy, przy 16.35 GiB wag.
  - Krzywa V(N) dla N > 16 niezmierzona.
  - Tekst per strumień różni się od `-np 1` (brak niezmienniczości względem batcha). Dla produktu wystarcza poprawność rozkładowa, ale md5-testy trzeba prowadzić na `-np 1`.
- **Wysiłek.** 5–8 dni.
- **Kill.**
  - (1) V(N) dla N = 10/15/20/24/32 (§6 D1): V20 > 40 ms @2k → kill dla k > 2.
  - (2) Smoke `-np 2 -kvu` z MTP, 2 równoległe klienty `spec_sweep`, 10 min: crash albo śmieci → napraw albo kill.
  - (3) Przepustowość łączna k=2 < 1.4 × pojedynczej albo na strumień < 0.75 × → kill.

### #5 `kvq`: jedno przejście po KV dla wszystkich kafli N×G (bitowo)

- **Mechanizm.**
  - Dziś kafel ma 16 wierszy Q, a wierszy jest N·6 (GQA 6: 24 głowy Q / 4 KV). Kafli jest więc `ceil(6N/16)`: N=5 → 2, N=8 → 3, N=16 → 6. **Każdy kafel czyta K/V warstwy od nowa** (15b §6.1, 16b E2).
  - Nowy wariant: blok KV (np. 64 pozycje × 256 × K+V f16 = 64 KiB LDS z 128 KiB na WGP) dekwantowany raz, a wszystkie kafle (jedna fala na kafel) iterują po nim.
  - Kolejność akumulacji w wierszu się nie zmienia, więc bitowo jest identycznie; do sprawdzenia przez `llama-bx-diff`.
- **Zysk.**
  - KV @113k = 2.08 GB/przejście. N=5 dziś robi 2 przejścia, więc −2.3 ms z ~30 ms kroku MTP: **+8% przy kontekstach typowych dla agentów** (mediana > 100k, §2) `[SZACUNEK]`.
  - W16 @64k: E2 V16 − V5 = 12.45 ms vs 6.40 @2k. Nadwyżka 6.05 ms, z czego ~4 dodatkowe przejścia × 1.18 GB / 0.9 ≈ 5.2 ms to ponowne odczyty. Code-edit/copy przy 32–64k +12–15%.
  - Warunek dla #4 przy długim kontekście.
- **Dowody.** Własny model kafli (15b §6.1, skalibrowany: +3.5 ms na kafel ponad 2 @32k); FlashInfer, upakowanie głowic GQA (https://arxiv.org/abs/2501.01005).
- **Ryzyko.** Obłożenie (LDS 64 KiB/blok), presja VGPR, kombinacja split-K bez zmian.
- **Bezstratne.** Bitowo (z konstrukcji).
- **Wysiłek.** 4–6 dni.
- **Kill.** Mikrobench `kvq` @64k dla N=5 i N=16 (rocprofv3, `GGML_HIP_PM4=0`). Nowy kernel < 25% szybszy w czasie atencji → kill.

### #6 Globalny cache sufiksów między żądaniami, sesjami i agentami

- **Mechanizm.**
  - Drugi indeks obok lookupu w kontekście (16b) obejmuje: (a) wyjścia wszystkich wcześniejszych tur i subagentów; (b) wyniki narzędzi wycięte kompakcją; (c) pliki repo przeczytane wcześniej.
  - Zapytanie idzie, gdy lookup w kontekście nie trafia. Długość spekulacji wg częstości z drzewa, jak w SuffixDecoding.
- **Zysk.** SuffixDecoding na SWE-Bench / Text-to-SQL: do ×5.3, ×2.8 względem EAGLE-2/3 (https://arxiv.org/abs/2411.04975; kod https://github.com/snowflakedb/ArcticInference). Nasz przyrost ponad lookup w kontekście jest nieznany; przyjmuję +5–15% na mieszance agenta `[SZACUNEK]`.
- **Dowody uzupełniające.** REST (https://arxiv.org/abs/2311.08252), SAM-decoding (https://arxiv.org/abs/2411.10666).
- **Ryzyko.**
  - Pamięć hosta (drzewo na ~100 M tokenów to kilka GB; trzeba limitu).
  - Dane między sesjami zostają lokalnie.
  - Wyjścia w sesjach pisał Claude, nie Qwen (to samo zastrzeżenie co 15b).
- **Bezstratne.** Tak.
- **Wysiłek.** 3 dni.
- **Kill (CPU).** Replay 21 673 tur z indeksem globalnym „leave-session-out”, tokenizer Qwena, symulacja jak w 15b §6.1. Dodatkowe pozycje z r ≥ 8 ponad lookup w kontekście < 3% tokenów wyjścia → kill.

### #7 KV 4-bit z rotacją Hadamarda dla długiego kontekstu

- **Mechanizm.** Ortogonalna rotacja K i Q (iloczyn QKᵀ niezmienniczy) i V (odwrócenie po PV) rozprasza wartości odstające, więc 4 (albo 3) bity wystarczają. Wariant `kvq` czyta format natywnie.
- **Zysk.**
  - LFM dziś trzyma KV q8_0 z wyboru jakości (KLD q4_0 0.128 vs q8_0 0.044, wiki `lfm2-5-24b-a2b`).
  - @98k: 1.07 GB → 0.53 GB, czyli −0.6 ms z 4.69 ms. **+15% przy 98k**, VRAM −0.5 GB przy 131k `[SZACUNEK]`.
  - Qwen (q4_0 → 3 bity): −0.46 GB/krok @113k (+1.7%) i −0.9 GB VRAM przy 204800, co ułatwia #4.
- **Dowody.** TurboQuant: poniżej 3 bitów przy znikomej stracie (https://arxiv.org/abs/2504.19874; dyskusja llama.cpp https://github.com/ggml-org/llama.cpp/discussions/20969); KIVI (https://arxiv.org/abs/2402.02750).
- **Ryzyko.** Jakość po polsku; koszt rotacji w grafie (mały: 64-wymiarowe głowice LFM).
- **Bezstratne.** Nie; bramka KLD.
- **Wysiłek.** 5–7 dni.
- **Kill (CPU).** LFM `llama-perplexity --kl-divergence` z rotowanym KV 4-bit (implementacja CPU op): KLD > 0.05 (q8_0 = 0.044) → kill.

### #8 Głowica EAGLE-3 dla LFM trenowana lokalnie

- **Mechanizm.** Lekka głowica: 1 warstwa d=2048 + słownik draftu 32k, łącznie ~100 MB odczytu na token draftu `[SZACUNEK]`. Fuzja cech z kilku warstw celu (EAGLE-3 „training-time test”). Dane: self-distillation na XTX przez narzędzie typu `llama-mtp-extract` (gałąź `mtp-train`).
- **Zysk** (model §3.4) `[SZACUNEK]`:
  - łańcuch 2 draftów przy α=0.7: E = 2.19 tok / (5.47 + 0.6) ms = 361 t/s (**+23%**);
  - α=0.8: 402 t/s (**+37%**);
  - 1 draft przy α=0.7: 356 t/s.
- **Dowody.** EAGLE-3 do ×6.5 (https://arxiv.org/abs/2503.01840); P-EAGLE, równoległe draftowanie (https://arxiv.org/abs/2602.01469); MoESD (https://arxiv.org/abs/2505.19645).
- **Różnica wobec negatywu z raportu 11.** Tam głowica już istniała i była blisko optimum. Tu startujemy od zera.
- **Ryzyko.**
  - Koszt danych: 10 M tokenów przy 294 t/s ≈ 9.5 h GPU.
  - Trening na XTX dzieli GPU z produkcją.
  - Suma ekspertów przy kodzie gorsza niż w modelu.
- **Bezstratne.** Rozkładowo.
- **Wysiłek.** 10–15 dni.
- **Kill.** (1) T(3) > 2.0 × T(1) = 6.8 ms (§6 D1) → kill całości. (2) Po 2 M tokenach treningu offline α₁ < 0.6 na zbiorze odłożonym → kill.

### #9 IQ4_KS (4.25 bpw) dla Qwena

- **Mechanizm.** Skalarny kwant ik_llama (IQ4_KS + IQ5_K + Q6_K) z jedną skalą na wiersz. To nie trellis, więc dekwant jest tani. Port typów do naszego HIP MMVQ/MMQ.
- **Zysk.**
  - Plik ji-farthing: 13.27 GiB rezydentne na GPU vs nasze ~16.83 GB, czyli ×0.847.
  - Plain 16.82 → 14.3 GB → przy dzisiejszej sprawności 43.2 → ~50.5 t/s (+17%); MTP 109 → ~124 (+14%) `[SZACUNEK]`.
  - Na 16 GB realna alternatywa dla Q3_K_XL.
- **Jakość.**
  - ji-farthing: PPL +0.7% (EN) / +0.6% (kod) do BF16 na tekście odłożonym (https://huggingface.co/ji-farthing/Qwen3.8-27B-ik-llama-GGUF) `[NIEZWERYFIKOWANE]`.
  - Nasze U4: KLD 0.0153 wiki / 0.0073 PL proza (`quantkld-20261016/kld-all/kld.md`).
  - Imatrix ji-farthing jest agentowy, bez polskiego.
- **Dowody.** ik_llama (https://github.com/ikawrakow/ik_llama.cpp); YAQA, rounding minimalizujący KL całego modelu (https://arxiv.org/abs/2505.22988); QTIP (https://arxiv.org/abs/2406.11235); AQLM (https://arxiv.org/abs/2401.06118). Trellis na 3 bpw nie wygrywa z U3 (15e §TL;DR 2).
- **Ryzyko.** Port kerneli 6–8 dni; blok MTP; jakość po polsku.
- **Bezstratne.** Nie.
- **Kill (CPU, 0.5–1 dnia).** ik_llama na CPU, referencja Q8_0 (KLD Q8 do BF16 = 0.0038), nasze 5 korpusów. KLD(IQ4_KS) > 1.1 × KLD(U4) na którymkolwiek korpusie → kill przed jakąkolwiek pracą GPU. Opcjonalnie własny imatrix z polskim.

### #10 Block verification przy T>0

- **Mechanizm.** Reguła akceptacji, która ocenia prefiks bloku łącznie zamiast tokenów po kolei. Dowodliwie nie gorsza od weryfikacji po tokenie i optymalna wśród poprawnych weryfikatorów. Zachowuje rozkład.
- **Dlaczego u nas.** Przy T=1 serwer próbkuje draft z q (`result_q`, 16b §1), więc spełnia założenia artykułu.
- **Zysk.** Artykuł: 5–8% wall-clock (ICLR 2025, https://arxiv.org/abs/2403.10444). U nas +3–6% na czacie T=1 `[SZACUNEK]`.
- **Różnica wobec 16k.** Sprzężone próbkowanie zmienia RNG (wspólny szum), a nie regułę. To alternatywy, nie da się ich złożyć wprost; rozstrzyga symulacja.
- **Ryzyko.** Rozkład resztowy na pozycji zatrzymania; koszt hosta.
- **Bezstratne.** Rozkładowo; bitowo nie.
- **Wysiłek.** 2 dni.
- **Kill (CPU + 10 min GPU logowania).** Log (p_i(x_i), q_i(x_i), rozkłady na pozycji odrzucenia) na `spec_sweep` 6×3, potem symulacja E[tok/krok]: token-wise vs block vs coupled. Block < +2% → kill.

### #11 d1 draftu MTP liczony w grafie weryfikacji

- **Mechanizm.**
  - Graf weryfikacji dostaje dwa dodatki: próbkowanie celu w grafie na każdej z N pozycji (op `GGML_OP_GUMBEL_MAX` z szumem kluczowanym pozycją; 16k, wiki `kernele/gumbel-max.md`) oraz przebieg warstwy MTP po N pozycjach naraz.
  - Po akceptacji d1 następnego kroku to wiersz przy przyjętej pozycji.
  - Odpada 1 z 4 sekwencyjnych przebiegów draftu i jedna synchronizacja hosta.
  - Przy T=0 wystarcza argmax. Przy T>0 wymaga trybu `LLAMA_SPEC_COUPLED`.
- **Zysk.** Draft 3.62 ms / 4 ≈ 0.9 ms. Batch MTP po 5 kolumnach kosztuje ~+0.2 ms, więc −0.7 ms/krok plus ~0.1–0.2 ms hosta: **+2.5–3%** `[SZACUNEK]`.
- **Różnica wobec 16f E3.** Tamto było prefillem; to jest pętla dekodowania.
- **Ryzyko.** Złożoność grafu i taśmy PM4.
- **Bezstratne.** Tak (zmienia tylko drafty).
- **Wysiłek.** 3 dni.
- **Kill.** PM4 trace (`GGML_HIP_PM4_DEBUG=3`) albo rocprofv3: pojedynczy przebieg draftu < 0.6 ms → kill.

### #12 Audyt sufitu wzorca + repack wag Qwena przy ładowaniu

- **Mechanizm.**
  - Lekcja z 16g: najpierw zmierzyć czysty odczyt tych samych bajtów tym samym wzorcem. Przy LFM 2 wiersze na falę czytały 22.4–24.4 µs, a 4 wiersze na blok 19.68 µs stabilnie (879 GB/s).
  - Dla Qwena (plain 727 GB/s = 76%) takiego audytu nie było.
  - Jeśli wzorzec jest sufitem: przepakowanie wag przy ładowaniu (przeplot wierszy, skale obok danych, ładowania 16 B ciągłe na falę, jak Marlin/Machete i EXL3, https://github.com/turboderp-org/exllamav3), z tą samą kolejnością sum, czyli bitowo.
- **Zysk.** 76% → 85%: plain 43.2 → 48.5 t/s (+12%), MTP +10% `[SZACUNEK]`.
- **Ryzyko.** Poprzednie rundy dużo już wyciągnęły. Limit mocy 285 W (lekcja 16g): szybszy kernel spowalnia inne.
- **Bezstratne.** Tak, bitowo.
- **Wysiłek.** Audyt 2 dni, implementacja 6–10.
- **Kill.** Czysty odczyt największych macierzy Qwena (ffn 5120 × 17408 w IQ4_XS / Q4_K / Q5_K / Q3_K) wzorcem produkcyjnym vs ciągły układ przepakowany: różnica < 5% → kill.

### #13 Rzadkość aktywacji ekspertów LFM (CATS)

- **Mechanizm.** Próg na |SiLU(gate)| per neuron eksperta. Pomijane są wiersze `up` (ciągłe w ggml) i kolumny `down`; `down` trzeba przechowywać transponowany, przekwantowany z BF16.
- **Zysk.**
  - Eksperci 1.016 GB; up+down = 2/3. Przy 40% rzadkości: −0.27 GB, T = 3.12 ms (+9.6%).
  - Sam `up`: −0.135 GB (+4.5%) `[SZACUNEK]`.
- **Dlaczego nie Qwen.** Weryfikacja N=5 czyta sumę aktywnych neuronów: niezależnie 1 − 0.5⁵ = 97%. Literatura o łączeniu z SD wymaga rzadkości na poziomie kawałków (BlockFFN, https://arxiv.org/abs/2507.08771) albo rzadkości w samej weryfikacji (https://arxiv.org/abs/2512.21911).
- **Dowody.** TEAL: 40–50% rzadkości, dekod ×1.53–1.8 (https://arxiv.org/abs/2408.14690); CATS (https://arxiv.org/abs/2404.08763); R-Sparse: 50% bez treningu (https://arxiv.org/abs/2504.19449); Deja Vu (https://arxiv.org/abs/2310.17157).
- **Ryzyko.**
  - Małe eksperty (ffn 1536) mogą być mniej rzadkie.
  - Gather wierszy łamie strumień (lekcja 16g).
  - Stratne; przekwantowanie `down`.
- **Wysiłek.** 8 dni.
- **Kill (CPU).** Próg w op SWIGLU MoE w backendzie CPU, KLD do gęstego Q5_K_M przy 40% rzadkości. > 0.01 na którymkolwiek z 5 korpusów → kill.

### #14 Certyfikowana głowica LM (cel) + cień głowicy draftu — **dla Qwena KILL w pilocie CPU**

- **Mechanizm (knlp).**
  - Słownik w 256 ciągłych blokach. Offline: baza B rzędu r z PCA prawdziwych stanów h, cień int8 `W_U·B` i normy reszt wierszy δ_v = ‖w_v − BBᵀw_v‖.
  - W dekodowaniu górna granica każdego logitu: U_v = (W_U B)_v·Bᵀh + ρ·δ_v, gdzie ρ = ‖h − BBᵀh‖ (Cauchy–Schwarz; plus luz na zaokrąglenie int8).
  - Bloki otwiera się malejąco po granicy, aż najlepszy dokładny logit przewyższy granicę każdego nieotwartego bloku.
  - Uogólnienie na top-k (k-ty najlepszy > granica) i min-p (otworzyć wszystko z granicą ≥ max + ln p_min). Kara powtórzeń obniża logity monotonicznie, więc granice zostają ważne.
  - **Draft** nie potrzebuje certyfikatu: wystarczy przybliżony argmax, bo drafty nie zmieniają wyjścia.
- **Dowody zewnętrzne.**
  - knlp: na W7900 (gfx1100) głowica przy batch 1 ×1.97 dla Qwen2.5-7B; ~5× mniej bajtów głowicy (cień 18% + ~2% otwartych bloków); batch 4/8: ×1.36/×1.41 (http://knlp.io/lm_head_decode.html; kernele Triton https://github.com/mcgrof/knlp/tree/main/lm_head/kernel). Baza r ≈ 0.36·d z PCA stanów.
  - VocabTrim, przycinanie słownika draftu (https://arxiv.org/abs/2506.22694).
- **Pilot CPU na Qwenie (ten raport, $0).**
  - Dane: stany `h` (wejście `output.weight`) z `~/qwen-opt/mtp-train/data/ext_p1/h.f16`, 73 138 pozycji, oraz głowica Q6_K zdekwantowana przez gguf-py.
  - Walidacja: h·W odtwarza różnice zapisanych log-probów top-32 (`top.bin`, rekord j ↔ h[pozycja − 1]) z medianą maks. błędu 0.28 logitu na 297 pozycjach, a top-1 = następny token w 90.6%.
  - Baza B: niecentrowane PCA z 20 000 pozycji. Test: 400 serii po 5 kolejnych pozycji; pozycje startowe spoza próbki PCA, choć pojedyncze dalsze pozycje serii mogą się z nią pokrywać.
  - Liczba bloków do otwarcia = #{b: U_b > M_k}, gdzie M_k to k-ty dokładny logit. To dokładny licznik procedury „otwieraj do certyfikatu”. N=5 to suma bloków z 5 pozycji weryfikacji.
  - Bajty cienia liczone względem głowicy Q6_K (1.043 GB). Uwaga: knlp liczy względem bf16, a u nas głowica jest już 6.56 bpw, więc cień jest relatywnie 2.4× droższy.

| rząd r | energia h w bazie | mediana ρ/‖h‖ | top-1: bloki N=1 / N=5 | top-20: N=1 / N=5 | cień int8 / int4 (część bajtów głowicy) |
|---|---|---|---|---|---|
| 512 | 64.6% | 0.607 | 99.9% / 100% | 100% / 100% | 12.2% / 6.1% |
| 1024 | 76.8% | 0.505 | 98.6% / 99.4% | 100% / 100% | 24.4% / 12.2% |
| 1843 (0.36·d, jak knlp) | 87.3% | 0.394 | 97.5% / 98.3% | 99.2% / 99.9% | 43.9% / 21.9% |
| 2560 | 92.6% | 0.319 | 91.0% / 97.6% | 98.5% / 99.3% | 61.0% / 30.5% |
| 3584 | 97.1% | 0.220 | 35.3% / 65.7% | 97.5% / 98.3% | 85.3% / 42.7% |

  - Wcześniejszy wariant z bazą z SVD samej głowicy (r ≤ 512) otwierał 100% bloków.
  - Skrypty jednorazowe (`/tmp/nextwave_head2.py`, `/tmp/nextwave_align3.py`), nie zachowane.
- **Werdykt dla Qwena: KILL.** Stany Qwen3.8-27B mają wysoki wymiar efektywny: przy r = 0.36·d baza łapie 87% energii, a ρ/‖h‖ = 0.39 (u knlp ρ „tiny”). Granica Cauchy'ego–Schwarza nie odcina prawie niczego. Najlepszy punkt (r = 3584, top-1, N=1) czyta 85% + 35% = 120% bajtów głowicy. Przy T=1 i top-20 nie ma żadnego zysku. Cień głowicy draftu (przybliżony argmax) pozostaje nieprzetestowany; przy 77% energii dla r = 1024 oczekuję słabej zgodności `[INFERENCE]`.
- **LFM (otwarte).** d = 2048, głowica 215 MB to 12% bajtów. Przy 20% bajtów jak u knlp: −0.17 GB, 3.42 → 3.24 ms (+5.6%) `[SZACUNEK]`. Wynik Qwena każe jednak oczekiwać podobnie wysokiego wymiaru, więc p = 0.2.
- **Ryzyko.** Luźność granicy (potwierdzona na Qwenie), dwa dodatkowe kernele (~10 µs), parzystość fp (knlp: 0.998 zgodności w części przebiegów), więc potrzebny fallback na pełną głowicę.
- **Bezstratne.** Tak z certyfikatem; otwarte wiersze liczone tym samym kernelem są bitowo te same.
- **Wysiłek.** 4–6 dni, tylko jeśli LFM przejdzie bramkę.
- **Kill (CPU).** Ten sam pilot na ~2k stanach LFM (llama.cpp CPU, 2B aktywnych, `nice -n 19`, 4 wątki). Bajty głowicy dla top-1 przy N=1 > 45% → kill całości.

### #15 Prefill Qwena: 49% → 65% szczytu WMMA iu8

- **Mechanizm.** 27.3 B parametrów × 2 = 54.6 GOP/token. Szczyt WMMA iu8 XTX ≈ 123 TOPS: 512 op/clk/CU × 96 × ~2.5 GHz `[INFERENCE]` z https://gpuopen.com/learn/wmma_on_rdna3. To 2250 t/s przy 100%; pp4096 1115 t/s = 49%.
- **Zysk.** 65% → 1470 t/s (+32% prefillu). Przy udziale prefillu 34% (§2) wall-clock agenta −8% `[SZACUNEK]`.
- **Ryzyko.** Runda 5: podwójny bufor MMQ zwalniał; ablacja wskazała epilog, poprawiony (+2.2%, wiki `kernele/mmq-epilog.md`). Udział kerneli GDN (chunked) w prefillu niezmierzony.
- **Dowody.** GPUOpen WMMA; przykład W4A16 WMMA na gfx1100 (https://github.com/kungfu-team/autellix/blob/main/csrc/rocm/q_gemm_rdna3_wmma.cu).
- **Bezstratne.** Tak (te same wyniki przy tej samej akumulacji int32; epilog jak dziś).
- **Wysiłek.** 10 dni.
- **Kill.** Profil per kernel prefillu @4k: MMQ < 60% czasu → zmienić cel na GDN. Mikrobench GEMM iu8 5120 × 17408 × 512: najlepszy osiągalny < 1.25 × dzisiejszy MMQ → kill.

---

## 5. Odrzucone albo odłożone (z arytmetyką)

| pomysł | dlaczego nie teraz |
|---|---|
| TEAL/CATS dla Qwena | suma po 5 tokenach weryfikacji: 97% aktywnych przy 50% rzadkości (§0 pkt 4); zysk tylko w plain, którego nie używamy |
| Drzewa draftów dla hybrydy GDN (STree, https://arxiv.org/abs/2505.14969) | przy dzisiejszej krzywej V(N) (V8 − V5 = +2.46 ms = +10% kroku) drzewo 8 węzłów musi dać > +10% tok/krok. Typowe +0.3–0.5 tok/krok przy 3.02 to +10–16%, czyli netto ≈ 0–5%, a do tego 10+ dni pracy nad gałęziowaniem stanu GDN. Wracać po #4/#5 (płaska V(N)); kill offline z top-2 MTP |
| MALL: rezydencja wag / draftu / stanu GDN | §3.5: brak ponownego użycia w zasięgu 96 MB; stan GDN 151 MB f32 |
| podkręcanie pamięci, zmiana limitu mocy, undervolting | twarda zasada bezpieczeństwa sprzętu (wiki `decyzje/2026-10-19-bezpieczenstwo-sprzetu.md`); VRAM już doszedł do 90 °C |
| LFM2.5-2.6B / 1.2B jako drafter LFM 24B | 2.6B: ten sam słownik 128 000, ale 1.5 GB/token ≈ połowa celu; próg opłacalności ~2.15 tok/krok przy α ~0.6 nieosiągalny `[SZACUNEK]` |
| self-spec LFM z top-1 ekspertem | draft czyta 57% bajtów celu; weryfikacja N=4 6.4 ms; wynik ujemny (§3.4) |
| stan GDN w bf16 | ≤ 1.8% bajtów, stratne |
| VOPD / dual-issue w dekodowaniu | 85% czasu fali w `s_waitcnt vmcnt` (16g) |
| FP4/NVFP4 MMA w szerokiej weryfikacji (Blackwell 5060 Ti / 5090) | najpierw globalna skala w kwantyzatorze NVFP4 (15e #6); poza kartami lokalnymi; po #4 jako „płaska V(N)” na sm_120 |
| Medusa / lookahead (https://arxiv.org/abs/2401.10774, https://arxiv.org/abs/2402.02057) | dla Qwena MTP jest silniejszy; dla LFM EAGLE-3 (#8) dominuje Medusę przy tym samym koszcie treningu |

---

## 6. Plan eksperymentów na 30 dni (lokalne XTX, sekwencyjnie)

### 6.1 Zasady bezpieczeństwa (obowiązkowe dla każdego bloku GPU)

1. **Jedno zadanie GPU naraz.**
   - Każdy blok GPU w `flock /tmp/gpu.lock`, a pomiary dodatkowo w `flock /tmp/quiet.lock`.
   - Kompilacje w `flock -s /tmp/quiet.lock nice -n 10 … -j6`.
   - Ciężkie zadania CPU (KLD, replay, numpy/torch) w `flock -s /tmp/quiet.lock nice -n 19` z `OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false` (polecenie Main z 2026-10-19).
   - Bez pętli odpytujących i bez ładowania całych modeli na CPU, jeśli nie jest to konieczne. KLD na CPU (#3, #9) to jawny wyjątek, wykonywany tylko w oknie bez pomiarów GPU.
   - **Nigdy nie usuwać ani nie odtwarzać `/tmp/*.lock`** (wiki `lekcje/lekcja-nie-odtwarzac-lockow.md`).
2. **`gpu-guard` włączony przez cały czas trwania bloku** (`~/KERNEL/qwen-opt/tools/gpu-guard.sh`; zabija procesy GPU poza :8080).
   - Kod 3 budzi Main.
   - Kod 4 (VRAM ≥ 85 °C albo hotspot ≥ 90 °C) oznacza pauzę, zanim limit się zbliży.
   - Wentylator 100% przy pracy (wiki `decyzje/2026-10-19-wentylator-100-przy-pracy.md`).
3. **`GGML_HIP_PM4=0`** we wszystkich eksperymentach, dopóki raport Pm4Fix nie wykaże bezpieczeństwa (R/17 §5–6). Bazy porównawcze mierzone też z PM4=0 (Qwen 103.7, LFM 259.3 t/s; `BPP:17`).
4. **Nowy build:**
   - najpierw `test-backend-ops` dotkniętych operacji i smoke greedy md5;
   - **pierwszy page fault, timeout ringu albo reset oznacza natychmiastowy stop tego builda na GPU**; dalej debug na CPU, bez „odrzuć blok i powtórz” (wiki `decyzje/2026-10-19-bezpieczenstwo-sprzetu.md`).
5. **Produkcja na :8080 nietknięta.** Sprawdzenie przez `pgrep -x llama-server` i `/proc/*/cmdline`, nie `pgrep -f`.
6. **Pomiar.**
   - Bloki ≤ 5 min z przerwami; ABBA, świeży serwer na ramię.
   - ≥ 5 seedów dla decyzji o efektach ±3% (lekcja 16f).
   - Kryterium zabicia i karta twierdzenia zapisane w `ledger.jsonl` przed pomiarem (Fabryka v1, 16h).
7. **Zakaz** zmian zegarów, napięć i limitów mocy.

### 6.2 Harmonogram

GPU ~12–15 h łącznie w 30 dni; CPU równolegle, gdy nie trwa pomiar.

| dzień | CPU (równolegle) | blok GPU (sekwencyjnie, pod lockami) | bramka |
|---|---|---|---|
| D1 | #14 pilot Qwena zrobiony (KILL); #14 pilot LFM: ~2k stanów z llama.cpp CPU (`nice -n 19`, 4 wątki); #6 replay globalnego indeksu (start) | **G1, 15 min: krzywe V(N).** LFM `llama-bench -fa 1 -ctk q8_0 -ctv q8_0 -p 1,2,3,4,5,8,16 -n 0 -d 0,32768`; Qwen `-ctk q4_0 -ctv q4_0 -p 1,5,10,15,20,24,32 -n 0 -d 2048,32768` | T(8) LFM ≤ 13.6 ms (#2); T(3) ≤ 6.8 ms (#8); V20 Qwen ≤ 40 ms (#4); #14 LFM ≤ 45% bajtów głowicy |
| D1–2 | tryb lookup bez MTP dla LFM (kod, CPU build) | — | — |
| D2 | pobranie LFM QAD-Q4_0 i LFM BF16; KLD na CPU (#3) | **G2, 30 min:** LFM lookup, `copy_bench` `mvs` / copy / long + `spec_sweep lfm` | #2: ≥ ×1.3 `mvs`, czat ≥ −1% |
| D3 | KLD IQ4_KS na CPU, ik_llama, referencja Q8_0 (#9) | **G3, 20 min** (jeśli #3 przeszedł KLD): QAD-Q4_0 llama-bench ABBA + `spec_sweep lfm` 6×5 | #3 → decyzja użytkownika |
| D4 | symulator block verification (#10) | **G4, 15 min:** log (p, q) na `spec_sweep` 6×3; PM4 trace jednego przebiegu draftu (#11); rocprofv3 per kernel Qwen plain i prefill @4k (#12, #15) | #10 ≥ +2%; #11 draft ≥ 0.6 ms; #12/#15 cele |
| D5 | poprawki per-sekwencja (`pending_h`, GDN replay) w kodzie | **G5, 15 min:** smoke `-np 2 -kvu` z MTP, 2 klienty | #4 brak crashu, poprawne teksty |
| D6–10 | #2 do produkcji: gating, kontroler W pod T(N), testy md5 T=0; #4: cache grafu i chunked prefill | G6–G9, po 20 min/dzień: A/B #2 (ABBA, 5 seedów) i #4 (przepustowość łączna k=2/3) | #4 k=2 ≥ 1.4× łącznie, ≥ 0.75× na strumień |
| D8–12 | #5 mikrobench `kvq` jednego przejścia (CPU-build, emulator ISA dla poprawności) | G10, 15 min: mikrobench @64k N=5/16 | #5 ≥ 25% szybciej |
| D13–17 | #5 integracja + `llama-bx-diff`; #14 kernel dla LFM, tylko jeśli bramka CPU z D1 przeszła | G11–G13: long_ctx_bench 29.5k/94k (#5); LFM tg128 ABBA (#14) | bitowo identycznie; zysk ≥ progu z karty |
| D16–20 | #6 implementacja, jeśli replay ≥ 3%; #10 implementacja, jeśli symulacja przeszła | G14–G15: replay omp (#6), `spec_sweep` T=1 (#10) | jak w kartach |
| D21–26 | #9 port IQ4_KS (jeśli KLD przeszedł) **albo** #8 generacja danych LFM (jeśli T(3) przeszedł; ~9.5 h GPU w blokach nocnych z `gpu-guard`); #7 CPU KLD rotowanego KV | G16–G18 | #9 KLD ≤ 1.1× U4; #8 α₁ ≥ 0.6 |
| D27–30 | ledger, wiki, raport 18b; **końcowe ABBA** wszystkich zwycięzców razem vs baza (stan PM4 wg Pm4Fix) | G19–G20: `spec_sweep`, xbench, long_ctx_bench, replay roju | — |

NVIDIA (#1, wariant sm_120 dla #4) jest **poza planem lokalnym**: wymaga zgody użytkownika na chmurę, ~$1–2.

---

## 7. Źródła zewnętrzne (wybrane, wszystkie sprawdzone 2026-10-19)

- Spekulacja:
  - SuffixDecoding https://arxiv.org/abs/2411.04975 (+ https://github.com/snowflakedb/ArcticInference);
  - EAGLE-3 https://arxiv.org/abs/2503.01840; P-EAGLE https://arxiv.org/abs/2602.01469;
  - Block verification https://arxiv.org/abs/2403.10444;
  - STree https://arxiv.org/abs/2505.14969;
  - REST https://arxiv.org/abs/2311.08252; SAM-decoding https://arxiv.org/abs/2411.10666;
  - Medusa https://arxiv.org/abs/2401.10774; Lookahead https://arxiv.org/abs/2402.02057;
  - batch-spec poprawność https://arxiv.org/abs/2510.22876;
  - MTPLX 2.6.0 https://mtplx.com/releases/2.6.0.
- MoE + SD: EcoSpec https://arxiv.org/abs/2607.12696; https://arxiv.org/abs/2609.22156; MoESD https://arxiv.org/abs/2505.19645; koaktywacja https://arxiv.org/abs/2609.22471; adaptacyjna weryfikacja MoE https://arxiv.org/abs/2605.00342.
- Rzadkość: TEAL https://arxiv.org/abs/2408.14690; R-Sparse https://arxiv.org/abs/2504.19449; CATS https://arxiv.org/abs/2404.08763; Deja Vu https://arxiv.org/abs/2310.17157; BlockFFN https://arxiv.org/abs/2507.08771; rzadka weryfikacja https://arxiv.org/abs/2512.21911.
- Niskie bity: QTIP https://arxiv.org/abs/2406.11235; AQLM https://arxiv.org/abs/2401.06118; YAQA https://arxiv.org/abs/2505.22988; ik_llama https://github.com/ikawrakow/ik_llama.cpp; Qwen3.8-27B IQ4_KS/IQ3_KT https://huggingface.co/ji-farthing/Qwen3.8-27B-ik-llama-GGUF.
- KV: TurboQuant https://arxiv.org/abs/2504.19874; KIVI https://arxiv.org/abs/2402.02750; https://github.com/ggml-org/llama.cpp/discussions/20969; FlashInfer https://arxiv.org/abs/2501.01005.
- Głowica: knlp certified LM-head http://knlp.io/lm_head_decode.html, https://github.com/mcgrof/knlp/tree/main/lm_head/kernel; VocabTrim https://arxiv.org/abs/2506.22694.
- Kernele i AMD:
  - Marlin https://arxiv.org/abs/2408.11743;
  - Sarathi-Serve https://arxiv.org/abs/2403.02310;
  - WMMA RDNA3 https://gpuopen.com/learn/wmma_on_rdna3; https://rocm-handbook.amd.com/projects/amd-rocm-optimization-guide/en/latest/compiler-builtins/rdna/rdna3-dense-wmma-builtins.html;
  - NOALLOC https://www.mail-archive.com/amd-gfx@lists.freedesktop.org/msg146311.html; Mesa MALL https://www.phoronix.com/news/Mesa-22.2-Option-Disable-MALL;
  - exllamav3 https://github.com/turboderp-org/exllamav3.

---

## Do bazy wiedzy

| folder | tytuł (plik) | streszczenie | liczby (źródło) |
|---|---|---|---|
| eksperymenty | Workload agentów omp: prefill, dekod, współbieżność (`2026-10-19-workload-omp.md`) | 21 673 unikalne tury (34 h); prefill : dekod = 4.9 : 1 tokenów; przy tempie Qwena na XTX prefill 34%, dekod 57%, narzędzia 9%; ≥ 2 żądania w locie przez 37% czasu, średnio 1.97; 15% tur z ≥ 2 narzędziami | 18 §2; `~/.omp/agent/sessions` (usage API, tokenizer Claude) |
| metody | Model kosztu weryfikacji MoE (`model-kosztu-weryfikacji-moe.md`) | u(N) = 64(1 − (15/16)^N), B(N) = 0.761 + 0.254·u(N) GB, T(N) ≈ 1.45 ms + B/0.9; T(1) 3.42 (zmierzone 3.40), T(8) 9.6, T(16) 13.9 ms `[SZACUNEK]`; do potwierdzenia G1 | 18 §3.4 |
| modele | Qwen3.8-27B: uzupełnić rozkład bajtów | MLP 10.62 GB (4.96 bpw), głowica Q6_K 1.043 GB (6.2%), plain 16.48 GB wag + stan GDN 151 MB f32 (48 × 48 × 128 × 128) + KV 18 432 B/token; roofline plain 57.1 t/s, zmierzone 75.7% | 18 §3.1; nagłówek GGUF |
| modele | LFM2.5-24B-A2B: uzupełnić | LFM2.5-2.6B-QAD ma ten sam słownik 128 000, ale jako drafter za drogi (1.5 GB/token); KV q8_0 10 880 B/token; głowica 12% bajtów | 18 §3.2, §5 |
| lekcje | Rzadkość aktywacji a spekulacja (`lekcja-rzadkosc-vs-weryfikacja.md`) | weryfikacja N tokenów czyta sumę aktywnych neuronów; przy 50% niezależnej rzadkości i N=5 aktywne 97%; TEAL/CATS tylko bez spekulacji (LFM) | 18 §0, #13 |
| lekcje | MALL nie pomaga dekodowaniu batch 1 (uzupełnić `lekcja-prefetch-mall-xtx.md`) | brak ponownego użycia w kroku; odległość między krokami 16.8 GB (Qwen) / 1.8 GB (LFM) ≫ 96 MB; stan GDN 151 MB f32 | 18 §3.5 |
| repo | knlp certified LM-head (`knlp-lm-head.md`) | certyfikat górnej granicy logitu z bazy PCA stanów (r ≈ 0.36·d) i cienia int8; u nich ~5× mniej bajtów głowicy przy 7B, W7900 batch 1 ×1.97, batch 4/8 ×1.36/×1.41; **na Qwen3.8-27B nie działa** (pilot 18 #14) | http://knlp.io/lm_head_decode.html; 18 §4 #14 |
| repo | MTPLX (`mtplx.md`) | współbieżny MTP (kohorty 3/8), 1.6–2.25× per lane dla 2 agentów vs AR batching; wsparcie LFM2 | https://mtplx.com/releases/2.6.0 |
| repo | SuffixDecoding / ArcticInference (`suffixdecoding.md`) | drzewa sufiksów z promptów i wcześniejszych wyjść; agentowe do ×5.3, ×2.8 vs EAGLE-2/3 | https://arxiv.org/abs/2411.04975 |
| research | Raport 18: następna fala (`raport-18-nastepna-fala.md`) | 15 pomysłów z rankingiem; top lokalnie: lookup dla LFM, QAD-Q4_0, serwer wielostrumieniowy; plan 30 dni pod lockami i `gpu-guard` | 18 §4, §6 |
| eksperymenty | Pilot certyfikowanej głowicy Qwena na CPU (`2026-10-19-certyfikowana-glowica-pilot.md`) | **wynik negatywny**: 73 138 stanów h (walidacja: h·W odtwarza zapisane log-proby, mediana maks. błędu 0.28 na top-32; top-1 = następny token 90.6%); baza PCA r = 1843 łapie 87.3% energii, ρ/‖h‖ = 0.39; certyfikat top-1 otwiera 97.5% bloków (N=1) / 98.3% (N=5); przy r = 3584 cień 85% + 35% bloków > 100% głowicy; cień liczony względem Q6_K jest 2.4× droższy niż u knlp (bf16) | 18 §4 #14 (tabela); `~/qwen-opt/mtp-train/data/ext_p1/{h.f16,top.bin,meta.txt}` |
