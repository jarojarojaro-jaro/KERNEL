---
typ: eksperyment
tags: [eksperymenty, spekulacja, lookup, mtp]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:10-23,72-130,138-161; ~/qwen-opt/lookup/logs/e3_summary.txt:9-62; ~/qwen-opt/lookup/logs/e4_summary.txt:3-62; ~/qwen-opt/lookup/logs/e4_postfix.txt:2-5
status: aktualne
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

Kill: wszystkie zaliczone poza 15b E1 (udział ogona na prawdziwym ruchu), otwartym do tygodnia logowania. Włączenie w produkcji – decyzja użytkownika ([[otwarte-decyzje-produktu]]).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[raport-16b-lookup-tail]]
- [[2026-10-16-lookup-kopiowalnosc]]
- [[koszt-szerokosci-weryfikacji]]
- [[zestaw-copy-mvs]]
- [[2026-10-18-magnitude-vulkan-xtx]]
