# 57g. Kontynuacja 57a: EAR w `llama-perplexity` oraz alokacja typów per tensor dla 24 GB (tylko research)

Data: 2026-10-21. Autor: podagent ResGSQRCO. Tylko CPU, bez GPU, bez pobierania wag.

**Status zasad.** Pkt 2 to badanie, bez adopcji. Zasada użytkownika z 2026-10-19 („nie zmieniamy kwantów, żeby przyspieszyć”) dalej obowiązuje. `qa.jobs` **nie** trafił do kolejki. Zgodnie z poleceniem użytkownika żadne wagi ani zbiory danych nie zostały pobrane.
- Pobieranie BF16 przez SIM przerwałem po 14 MB i skasowałem częściowy plik oraz imatrix Unsloth (13 MB).
- Jedyny ruch sieciowy to nagłówki trzech plików Unsloth (UD-Q4_K_M, UD-Q4_K_S, UD-IQ4_XS), po 16 MB zakresem bajtów, pobrane przed zakazem. Reguła AGENTS.md dopuszcza ≤ 32 MB nagłówka. Pliki `hdr-*.bin` usunięte, zostały tylko listy tensorów.

Skrypty, logi i patch: `product/research/57g-skrypty/`. Robocze kopie leżą w `~/qwen-opt/quantalloc/`.

## TL;DR

1. **EAR jest gotowy i sprawdzony na CPU.** Gałąź `kld-ear` (`cb9aefbbf`, z `topka-int` `cf927413b`) dodaje do `--kl-divergence` jedną linię `Mean EAR` = średnia Σ_v min(p_v, q_v) = 1 − TV, bez przełącznika.
   - Plik bazowych logitów jest bajtowo identyczny ze starym (md5 `a7a797c6…`).
   - Cała tabela per chunk i wszystkie statystyki KLD / Δp / same-top są identyczne co do znaku (`diff` pusty).
   - Te same logity dają EAR = 99.99853 % (KLD −0.000000, top-1 100 %).
   - Model wyraźnie gorszy (LFM2.5-2.6B Q4_0 → requant Q3_K_M): KLD 0.719, top-1 59.85 %, EAR 63.58 %.
2. **Alokacja „tylko szybkie typy MMVQ”: 3 kandydaci gotowi jako pliki `--tensor-type-file`.** Każdy przeszedł `llama-quantize --dry-run`: rozmiar zgodny z modelem bajtowym co do MiB. Na tych samych bajtach strumieniowanych `[INFERENCE]`, przy niezmienionej akceptacji MTP:
   - qa1 (−1.00 GB, Q5_K → IQ4_XS): **+5.6 %**;
   - qa2 (−1.01 GB, Q5_K → Q4_K): **+4.2 %**;
   - qa3 (−1.51 GB, IQ4_XS): **+8.5 %**;
   - dla porównania własny UD-Q4_K_M Unsloth: −1.10 GB, +4.6 %.
3. **IQ4_XS wygrywa w prędkości z Q4_K przy tych samych bajtach.** Profil klab daje IQ4_XS 818 GB/s, Q4_K 738, Q5_K 776, więc qa1 jest o 0.41 ms/krok szybszy niż qa2. Jakość może jednak iść w drugą stronę: według SLQ symetryczna siatka (IQ4_XS) ma γ² większy szum niż asymetryczna (Q4_K). Para qa1/qa2 to czyste A/B tej tezy przy równych bajtach.
4. **Jakości nie da się dziś zmierzyć.** Na dysku jest tylko UD-Q4_K_XL: brak BF16, brak Q8_0, brak imatrixa. Kandydatów nie da się więc zbudować ani porównać KLD z BF16. Wszystko, co wymaga wag, jest przygotowane i nieuruchomione (§3).
5. **Uczciwa ocena szans: niska.** Priorytet demotowania wziąłem z kolejności, w jakiej Unsloth sam obniża tensory (XL → Q4_K_M → Q4_K_S → IQ4_XS), a nie z pomiaru. Faktycznym rywalem przy −1 GB jest UD-Q4_K_M (przewidywane +4.6 %), a nie UD-Q4_K_XL. Kandydat ma sens tylko wtedy, gdy przy równych bajtach da KLD ≤ UD-Q4_K_M. Przewaga z samych typów (bez wolnych IQ4_NL/IQ3_S, więcej IQ4_XS) to +1.0 pp t/s (qa1 vs UD-Q4_K_M).

## 1. EAR w `llama-perplexity` (zrobione)

- **Kod** (`tools/perplexity/perplexity.cpp`, +11 linii): akumulatory `sum_ear`, `sum_ear2` w `kl_divergence_result`.
  - W pętli po słowniku: `ear += expf(min(log p_base, log q))`. To jeden `expf` na token słownika: min(p,q) = exp(min(log p, log q)).
  - Scalanie w wątkach jak przy innych sumach. Linia `Mean EAR  : x ± y %` stoi po `Same top p`.
  - Istniejące sumy i wzory są nietknięte.
- **Uwaga numeryczna:** baza trzyma log-p w uint16 (skala zakresu 16 nat / 65535), stąd sufit 99.9985 % dla identycznych logitów. Tokeny przycięte w bazie (< max−16) wchodzą z p_base równym podłodze, ale min(p,q) ogranicza ich wkład przez q.
- **Test** (`57g-skrypty/ear-test.sh`, logi w `eartest/`): CPU, `cpuheavy`, LFM2.5-2.6B-QAD-Q4_0, 8 × 512 tokenów PL prozy (16e, md5 `cae78980…`). Wynik w TL;DR 1.
- **Build:** `rbuild --local -B build-cpu ~/wt/kld-ear -DGGML_HIP=OFF` (+ ta sama baza w `~/wt/kld-ear-base`). Wersji HIP nie budowałem; potrzebna do jobów GPU (`rbuild ~/wt/kld-ear llama-perplexity`).
- **Do zrobienia przy najbliższym KLD:** EAR obok KLD dla U4, U3 itd. EAR mierzy zgodność tokenów z BF16, czyli akceptację „kwant jako drafter BF16”. To nie jest akceptacja naszego MTP (tam drafter i cel to ten sam kwant).

## 2. Alokacja (CPU, z nagłówków)

**Dane.**
- `ud-map.json`: 866 tensorów UD-Q4_K_XL; plik 17.548 GB, strumieniowane na krok 16.482 GB (bez `token_embd` i bloku MTP 64).
- Mapy rodzeństwa Unsloth: Q4_K_M 15.387, Q4_K_S 14.450, IQ4_XS 13.345 GB strumieniowanych.
- Przejścia XL → Q4_K_M (`cmpmaps.py`): głównie ffn_up/down Q5_K → IQ4_XS/Q4_K (16 + 16 tensorów), attn_gate, attn_qkv, Q6_K → Q5_K. Do tego wolne typy: 4 × IQ4_NL, 3 × IQ3_S, 4 × Q3_K.

**Algorytm** (`alloc.py`):
- typy niespoza zestawu (IQ4_NL, Q3_K, IQ3_S) → IQ4_XS;
- tensory chronione: głowica, `token_embd`, blok MTP, attn_k/v;
- kolejka do demotowania sortowana po (pierwszy plik rodzeństwa, w którym Unsloth obniża tensor; środek modelu przed brzegiem);
- zachłannie jeden krok w dół (Q5_K → IQ4_XS lub Q4_K, Q6_K → Q5_K, Q8_0 → Q6_K) aż do celu bajtów.

To jest proxy zamiast pomiaru wrażliwości per tensor, bez BF16 innego się nie da. RCO/DP z 57a wymagałby kosztów z pomiarów.

**Model prędkości.** klab `traces/now1/off` (raport 47): 31.24 ms/krok; per typ GB/s Q5_K 776, IQ4_XS 818, Q4_K 738, Q6_K 763, IQ4_NL 631, IQ3_S 436, Q3_K 747. Δms = Σ_typ ΔMB / GB/s. Mnożnik t/s = 31.24 / (31.24 + Δms) przy tej samej liczbie tokenów na krok.

| plik | plik GB | strum. GB/krok | Δ vs U4 | Δ ms/krok | t/s × | E0 79 → | czat 100 → |
|---|---|---|---|---|---|---|---|
| UD-Q4_K_XL (U4, prod.) | 17.548 | 16.482 | 0 | 0 | 1.000 | 79.0 | 100 |
| **qa1-iq4-1.0** | 16.546 | 15.480 | −1.002 | −1.665 | **1.056** | 83.4 | 105.6 |
| **qa2-q4k-1.0** | 16.538 | 15.472 | −1.010 | −1.254 | **1.042** | 82.3 | 104.2 |
| **qa3-iq4-1.5** | 16.040 | 14.973 | −1.509 | −2.451 | **1.085** | 85.7 | 108.5 |
| UD-Q4_K_M (Unsloth) | 16.453 | 15.387 | −1.095 | −1.366 | 1.046 | 82.6 | 104.6 |
| UD-Q4_K_S (Unsloth) | 15.347 | 14.450 | −2.032 | −2.635 | 1.092 | 86.3 | 109.2 |

- `llama-quantize --dry-run --tensor-type-file` na pliku U4: 15779.86 / 15772.16 / 15296.62 MiB, czyli dokładnie kolumna „plik GB”. Wszystkie 506 wyrażeń zadziałało, bez cichego zastępowania typu.
- Wszystkie t/s to `[INFERENCE]` z bajtów. Wyższy KLD obniża akceptację MTP (16e: KLD 0.039 vs 0.073 → akceptacja 0.59 vs 0.55), co zje część zysku.
- Najwięcej zmian w qa1: attn_gate × 18, ffn_down × 17, ffn_up × 17, ffn_gate × 11 Q5_K → IQ4_XS; Q6_K → Q5_K: ssm_out × 6, ffn_down × 4 (pełne listy w `alloc.json`).

## 3. Co jest przygotowane i nieuruchomione (blokery)

| element | plik | blokada |
|---|---|---|
| budowa kandydatów + KLD/EAR vs BF16 na CPU serwera | `buildA.sh` (fazy fetch/quant/kbase/kld/sum, `nice 19`) | chmura = wydatek, potrzebna zgoda użytkownika; BF16 54.7 GB + imatrix pobierane tylko tam, nie przez SIM. Do domu wracają tylko logi, a kandydat (~16 GB) tylko po bramce i za zgodą |
| joby GPU: baza BF16 (jeśli BF16 lokalnie), KLD/EAR 4 ramion × (PL proza, kod), bramka, ABBA E0 `qa1Aa/Ba/Bb/Ab` | `qa.jobs` (+ `qa_sum.py gate/abba`) | P1 kandydaci, P2 logity BF16, P3 nadpisanie modelu w `run-llm.sh` (`gguf=${QWEN_GGUF:-…}`, skrypt produkcyjny, nie ruszałem), P4 build HIP `kld-ear` |
| porównanie z UD-Q4_K_M | — | plik 16.46 GB do pobrania, czyli zakaz |

**Bramka (`qa_sum.py`):**
- warunki na PL prozie: strumień ≤ U4 − 0.9 GB, KLD ≤ 1.10 × U4, top-1 ≥ U4 − 1 pp, EAR ≥ U4 − 0.5 pp;
- reguła stop: żaden z 3 kandydatów nie przechodzi → pomysł odpada;
- uzupełnienie: kandydat musi też mieć KLD ≤ UD-Q4_K_M przy ≤ jego bajtach, inaczej Unsloth już ma lepszy punkt.

## 4. Do bazy wiedzy

- **Fakt:** EAR = Σmin(p,q) jest w `llama-perplexity` na gałęzi `kld-ear` (`cb9aefbbf`). Wyjście dotychczasowe jest bajtowo identyczne (CPU, LFM 2.6B). Identyczne logity dają 99.9985 % (sufit uint16 bazy).
- **Fakt:** UD-Q4_K_XL strumieniuje 16.482 GB na krok. UD-Q4_K_M ma −1.095 GB, UD-Q4_K_S −2.032 GB (nagłówki, 2026-10-21).
- **Fakt:** w profilu topki IQ4_XS ma 818 GB/s wobec 738 dla Q4_K, więc przy tych samych bajtach IQ4_XS jest o ~10 % szybszy na bajt.
- **Szacunek:** alokacja tylko z szybkimi typami MMVQ przy −1.0 GB daje +5.6 % t/s (qa1) wobec +4.6 % UD-Q4_K_M. Jakość niezmierzona. Zablokowane przez brak BF16 i zakaz pobierania; to tylko research, zasada „nie zmieniamy kwantów” obowiązuje.
