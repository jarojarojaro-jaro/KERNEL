---
typ: test
tags: [testy, spekulacja, lookup, mtp]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:10-23,72-130,138-161; ~/qwen-opt/lookup/logs/e3_summary.txt:9-62; ~/qwen-opt/lookup/logs/e4_summary.txt:3-62; ~/qwen-opt/lookup/logs/e4_postfix.txt:2-5; ~/KERNEL/product/research/16b-lookup-tail.md:1-180; ~/KERNEL/product/research/21c-copy-paste-lm.md:176-205
status: aktualne
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 400.9 t/s | dekod mvs T=0; MTP4 + lookup W16 + łańcuchy (MTP4 166.2) | 2026-10-18
  - qwen3-8-27b | rx-7900-xtx | 375.8 t/s | dekod mvs T=1; W16 (MTP4 166.1) | 2026-10-18
  - qwen3-8-27b | rx-7900-xtx | 355.0 t/s | dekod copy T=0; W16 (MTP4 163.4) | 2026-10-18
  - qwen3-8-27b | rx-7900-xtx | 373.5 t/s | dekod long 30k T=0; W16 (MTP4 156.7) | 2026-10-18
---
# 2026-10-18/19: ogon z lookupu za MTP na XTX (W8/W16 + łańcuchy)

**MTP n=4 + ogon z lookupu kontekstu do 16 wierszy weryfikacji + łańcuchy bez draftera daje na edycjach kodu (`mvs`) ×2.41 przy T=0 (166.2 → 400.9 t/s) i ×2.26 przy T=1, bez zmiany tekstu greedy i bez kosztu na czacie (gałąź `lookup-tail` @ `6e12530cc`, `586f1d596`).**

| zestaw | MTP4 | W8 + łańcuchy | W16 + łańcuchy |
|---|---|---|---|
| mvs T=0 | 166.2 | 255.6 (+53.8%) | 400.9 (14.0–14.4 tok/krok) |
| mvs T=1 | 166.1 | 231.0 (+39.1%) | 375.8 |
| copy T=0 | 163.4 | 230.6 (+41.1%) | 355.0 (seria po naprawie wentylatorów, W8 235.8) |
| long ~30k T=0 | 156.7 | 239.6 (+52.9%) | 373.5 |

- `LLAMA_SPEC_LOOKUP`: 1 log na sucho, 2 ogon (dokleja tokeny lookupu do szerokości `_W`, gdy drafty MTP zgadzają się z lookupem przy dopasowaniu ≥ 6), 3 ogon + łańcuchy (po w pełni przyjętym bloku następny tylko z lookupu, bez draftu MTP; tylko przy drafcie greedy, więc przy T=1 tryby 2 = 3). Indeks n-gramów 4–12 tokenów na hoście, ≤ 10 µs/krok.
- Ogon trafia: 97.5% (copy) / 99.0% (mvs) przy W8, 96.0% przy W16 na mvs. Krok W16 34.6–35.2 ms (2–8k), 39.2 ms (30k) vs 29.8 ms MTP4.
- md5 T=0 identyczne 11/11 promptów kopii (W8, W16, kontroler); `greedy.sh` `c4708318` / `6f14e814` z `=0` i `=3 W16`. W16 jest poza zakresem `LLAMA_SPEC_BITEXACT` (≤ 8 kolumn).
- Czat (`spec_sweep`, T=1): ogon odpala 13–15 razy na ~4500 kroków, ms/krok w szumie (28.74 → 28.73); t/s −1.1% / +0.7% zależnie od seedów ([[lekcja-ogon-zmienia-tekst-t1]]).
- Kontroler szerokości 5/8/16: wynik zerowy ([[2026-10-18-kontroler-szerokosci-zerowy]]).

Kill: wszystkie zaliczone poza 15b E1 (udział ogona na prawdziwym ruchu), otwartym do tygodnia logowania. Włączenie w produkcji – decyzja użytkownika ([[otwarte-decyzje-techniczne]]).

## Ze scalonej notatki: Raport 16b: ogon z lookupu za MTP (15b E1–E3, 16i E-X0–E-X3)

Agent XtxLookupTail: MTP4 + ogon lookupu do 16 wierszy + łańcuchy daje na edycjach kodu ×2.26–×2.41 na XTX (mvs 401 t/s przy T=0) bez zmiany tekstu greedy i bez kosztu na czacie; kontroler szerokości nic nie dodaje ponad stałe W16.

- Zalecenie: `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16` w `run-llm.sh qwen` dla agentów kodujących, najpierw tydzień `LLAMA_SPEC_LOOKUP=1` (log na sucho) na prawdziwym ruchu omp – decyzja użytkownika ([[otwarte-decyzje-techniczne]]).
- Potwierdzenie 15b: MTP już kopiuje (P(MTP d1 | lookup d1) = 0.995), lookup wnosi tylko ogon i pominięcie draftu ([[lekcja-mtp-juz-kopiuje]]).
- Prognoza 16i (×2.07–2.41) zgodna z pomiarem; vs Magnitude: W16 14.4 tok/krok przy 35.5 ms, ich DFlash2 7.88 przy 50.2 ms (3090).
- Dalej: kopia ≥ 64k z W16, W16 w BITEXACT (16i #5), krzywa V(w) na CUDA, łańcuchy przy T=1.

Notatki: [[2026-10-18-lookup-ogon]], [[2026-10-18-kontroler-szerokosci-zerowy]], [[koszt-szerokosci-weryfikacji]], [[zestaw-copy-mvs]], [[lekcja-ogon-zmienia-tekst-t1]].

Dalej (21c, 2026-10-19): reguła AGR wyboru kandydata zgodnego z draftami MTP, symulacja +3.7% na agencie ([[agr-lookup-zgodny-z-mtp]]).

## Powiązane
- [[testy/2026-10-18-lookup-ogon]]
- [[2026-10-16-lookup-kopiowalnosc]]
- [[koszt-szerokosci-weryfikacji]]
- [[zestaw-copy-mvs]]
- [[2026-10-18-magnitude-vulkan-xtx]]
