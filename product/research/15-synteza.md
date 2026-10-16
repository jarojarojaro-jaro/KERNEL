# 15 — Synteza: nowe techniki optymalizacji (2026-10-16)

Zbiorczy wniosek z raportów 14 i 15a–15f. Każda liczba ma źródło w odpowiednim raporcie. `[SZACUNEK]` = wyliczenie, nie pomiar.

## 1. Audyt głośnych twierdzeń
| Twierdzenie | Werdykt | Dlaczego | Raport |
|---|---|---|---|
| vLLM MonoKernel: GLM-5.2, 8× MI350X, 13.70 → 5.92 ms | wiarygodne, inny reżim | vLLM używał 8% pasma HBM; wobec silnika ATOM tylko −22% czasu/token; harness usunięty z PR | 15a |
| HyperQwen (syv-ai): 381 t/s Qwen3.8-27B na 3090 | wiarygodne tylko dla zadania „przepisz dokument” | 14.97 tok/krok przy 39.3 ms/krok; na czacie 133 vs 131 t/s (w szumie ±3–5%) | 15b |
| Magnitude: 2.17–2.19× vs Ollama, „nie zmienia wyjścia” | wiarygodne tylko na kopiowaniu przy 64k; „nie zmienia wyjścia” fałszywe bitowo | tolerancja α = 8 ulp bf16, domyślny KV K8V4; wycofany pomiar vs llama.cpp: +19% decode | 15c |
| tqLLM: 273 t/s na 3090, „identyczne wyjście” | zweryfikowane w LocalMaxxing, ale T=0, 320 tok., 6.15 tok/krok, prywatny build | na zwykłych streszczeniach 131–155 t/s; „exact” tylko vs własny plain, naprawione 10-13 | 15c |
| Actual „e”: 455 t/s / >8000 t/s | zgodne z rooflinem, niezweryfikowane | tylko GB300, własne narzędzie, brak promptów i kontekstu | 15c |
| Lucebox PFlash v2: TTFT 3.7× | potwierdzone niezależnie (issue #752: 3.3/4.0/5.4×) | ale stratne: 92/124 vs 94; po polsku sonda trafia 1/10 | 15d |
| „2-bit to szum, GSQ-RCO to SOTA” | fałsz / tylko wąsko | GSQ IQ2_XS KLD 0.19–0.20 vs UD-Q4_K_XL 0.012; trellis ik_llama bije GSQ | 15e |
| Swift-1.5 GSQ-RCO „lepszy kwant” | to inny model (RL na krótsze myślenie), nie lepsza kwantyzacja | ten sam przydział typów co ISTA; głowica MTP bajtowo identyczna z Qwen; licencja < 1 mln $ | 15e |
| NVIDIA „nowa technika NVFP4” | CSF (bezstratna kompresja skal) + QAD | 4.27 bpw; model 125B tylko w vLLM | 15e |
| Sakana AI Scientist v3: „evidence generation” | izolacja w kodzie realna, ale werdykty bez testów istotności | agent zmienił protokół oceny w 2 z 3 przebiegów; złapał to ręczny audyt | 15f |

## 2. Najważniejsze odkrycia o nas samych
- **LFM na XTX: 36% czasu tokena to nie strumieniowanie wag** (3.40 ms = 1.95 ms wagi + 0.70 ms narzut matvec + 0.53 ms małe kernele + 0.22 ms host; granice kerneli to tylko 0.14–0.26 ms). Wcześniejsze „trwały kernel MoE ≈ 1.4%” liczyło tylko granice. [15a, wyliczenie z profili]
- **Nasza głowica MTP już kopiuje z kontekstu:** tam, gdzie lookup trafia, pierwszy draft MTP trafia w 96.8%. Lookup nadpisujący MTP (przepis HyperQwen) dałby u nas −1–2%. [15b, symulacja na 69 207 pozycjach]
- **Wyjścia agentów kodujących to inny świat:** edycje `old_string/new_string` 60% pozycji przewidywalnych lookupem, 38% w seriach ≥8 tokenów; zwykły czat 1–17%. [15b, 7.2M tokenów sesji omp]
- **Długi kontekst na NVIDIA to atencja, nie prefill:** upstream czyta cały KV raz na każdą głowicę Q (6× Qwen, 4× LFM). Model zgadza się z pomiarami (LFM +3.05 vs +2.80 ms). [15d]
- **Społeczne NVFP4 GGUF są słabe przez kwantyzator llama.cpp:** brak globalnej skali per tensor; 99.8–100% skal w zakresie subnormalnym. Globalna skala: −22–35% błędu wag (symulacja CPU). [15e]
- **Na 12 GB największy tani zysk to MTP na plikach 2-bitowych:** Saluki z głowicą MTP 41.2 → 66.2 t/s na RTX 3080 12 GB (społeczność, `[NIEZWERYFIKOWANE]` u nas). [15e]
- **Nasze dowody w commitach:** 25/70 łatek ma liczby przed → po, 0/70 ma przedział ufności, 5 wpisanych bez pomiaru; etykieta „base” wskazywała nadpisany katalog. [15f]
- **Nemotron 3.5 Bolt 74B-A9B na 3090:** 87.2 → 141.1 t/s (DFlash n=5 + nasze łatki + 2 nowe przełączniki), KLD jeszcze niezmierzone. [14]

## 3. Ranking działań: (zysk na naszym wąskim gardle × pewność) / wysiłek
| # | Działanie | Atakuje | Szac. zysk | Wysiłek | Koszt testu | Bezstratne? |
|---|---|---|---|---|---|---|
| 1 | **Fabryka v1:** karta twierdzenia + `ledger.jsonl` + skrypt-weryfikator poza zasięgiem implementującego, A/A, odłożony zestaw promptów | wiarygodność wszystkich wyników | — (warunek reszty) | ~8–9 dni-agenta | $0 | — |
| 2 | **Logowanie propozycji lookupu obok akceptacji MTP** (bez wpływu na wyjście) | dane do 3 | — | 0.5 dnia | $0 + 3 min GPU | tak |
| 3 | **Ogon lookupu szerokości 8 + łańcuchy bez draftera** (tylko gdy MTP się zgadza) | spec. na agentach kodujących | +2.4% mieszanka agentów, do +23% edycje `old_string` [SZACUNEK] | 2 dni | ~30 min GPU XTX | rozkład tak; bitowo zależnie od trybu bit-exact |
| 4 | **PM4-PDL** (bez granicy między sąsiednimi kernelami w taśmie PM4, wczesne ładowanie wag) | LFM na XTX: 0.53 ms małych kerneli + narzut | +5–15% LFM [SZACUNEK] | kilka dni | $0, GPU XTX | tak (bitowo) |
| 5 | **Port `kvq` na CUDA** | długi kontekst NVIDIA | 64k: Qwen 27.2 → ~37, LFM 147.7 → ~200 t/s [SZACUNEK] | 6–10 dni | <$1.5 | tak (kryterium KLD) |
| 6 | **Globalna skala w kwantyzatorze NVFP4** | jakość NVFP4 (prefill FP4 na RTX 50) | −22–35% błędu wag | 1–2 dni | $0 CPU | zmiana kwantu (KLD) |
| 7 | **MTP na plikach 2-bitowych (Saluki/ISTA `-mtp`) dla 12 GB** | karty 12 GB | do ~1.6× [NIEZWERYFIKOWANE] | mały | ~$0.6 (3060) | tak względem pliku |
| 8 | **Audyt cache agenta** (dlaczego start sesji przelicza 7–10k) + cache sesji na SSD | TTFT w sesjach | start sesji z dysku zamiast przeliczania (Lucebox: 56.2 → 2.6 s) | 0.5–3 dni | $0 | tak |
| 9 | **Prefetch do Infinity Cache** w czasie małych kerneli | LFM XTX | [SZACUNEK] w 15a | średni | $0 | tak |
| 10 | **PFlash jako opcjonalny „tryb szybkiego czytania”** z polską sondą | TTFT ≥16K nowych tokenów | 2.5–3.5× TTFT [SZACUNEK] | średni | $0 CPU + ~$2 | **nie (stratne)** |

Odrzucone / niski priorytet: lookup nadpisujący MTP, DFlash2 + lookup, bloki 32/64, KVFlash, pełny megakernel LFM (25–35 dni na backend), kompresja skal K-quantów (sufit 2.19%), AutoIllustrate.

## 4. Produkt: wnioski
- **Strojenie kerneli na komputerze użytkownika nie jest już unikalne** (Magnitude ma autotune 60 s). Wyróżnik: zweryfikowana poprawność (md5/KLD z publicznym raportem), przed → po wobec **dostrojonego** upstreamu, natywny AMD/ROCm (Magnitude nie ma HIP), agent-aware spekulacja. Propozycja zawężenia tezy w PLAN §0.1 — do decyzji użytkownika.
- **Raportować dwie klasy obciążenia osobno:** „nowe pisanie” (czat) i „kopiowanie” (edycje kodu, RAG). Wszyscy konkurenci mieszają je w nagłówkach.
- **LocalMaxxing:** dla RX 7900 XTX nie ma dziś zweryfikowanego wyniku Qwen3.8-27B — miejsce do zajęcia (wymaga konta użytkownika i ~15 min GPU).

## 5. Eksperymenty czekające na zgodę
| Eksperyment | Gdzie | Koszt |
|---|---|---|
| 15a X1–X3: PM4-PDL mikrobenchmark, PM4-PDL w taśmie LFM, prefetch | XTX | $0, GPU lokalne |
| 15a X5/X6: koszt granicy grafu CUDA na Ampere; PDL on/off na Blackwell | Vast 3090 / 5060 Ti | ~$0.6–0.75 |
| 15b E2/E3: przemiatanie szerokości/kontekstu weryfikacji; A/B ogona lookupu | XTX | $0, ~35 min GPU |
| 15c X1: Magnitude vs nasz fork | Vast 3090 + 5060 Ti | ~$1.5–2 |
| 15c X2: wyniki na LocalMaxxing | XTX lub Vast 3090 | 15 min GPU lub ~$0.3 |
| 15d E1: port kvq na CUDA (pomiar bazy → implementacja → weryfikacja) | Vast | <$1.5 |
| 15d E4: bisekcja regresji prefillu NVIDIA | Vast | ~$0.2 |
| 15e E1: Swift vs Saluki vs Bonsai vs Q3_K_XL (wariant B: KLD na CPU) | CPU + Vast | ~$1.5–2 |
| 14: KLD fuzji routingu Nemotrona | Vast 3090 | ~$0.3 |

Budżety: Vast ~$6.8, RunPod ~$3.9 (orientacyjnie, z raportów agentów).
