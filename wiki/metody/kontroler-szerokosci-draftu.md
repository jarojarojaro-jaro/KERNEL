---
typ: metoda
tags: [metody, spekulacja, kontroler]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/16i-magnitude-co-robia-dobrze.md:16-21,65-80,222-235,258-271
status: aktualne
---
# Kontroler szerokości draftu (wzorzec Magnitude)

**Magnitude (`draft_control.rs`, domyślnie włączony) co rundę wybiera parę (wydraftowane, zweryfikowane) o największej liczbie tokenów na sekundę z drabinki szerokości wypełniających klasy wierszy 2/4/8/16; u nich propozycji/krok waha się od 0.23 (9B pl-proza) do 6.75 (27B pl-kod).**

Algorytm:
- Drabinka: k, dla których k+1 jest potęgą 2 (15 → (1, 3, 7, 15)), plus 0.
- Akceptacja per głębokość `right[k]`, start 1.0, EMA 0.25, monotonicznie przycinana; ocenia także **niezweryfikowane** propozycje względem tokenów zatwierdzonych później.
- Koszt launchy: EMA 0.25 per (wiersze, klasa kontekstu = potęga 2), monotoniczny, bez prognozy.
- Wybór: max `(1 + Σ right) / (draft(g) + verify(v+1))`; „looks” 1% czasu na szersze rundy; po drafcie `verify()` może zwęzić.

Różnice wobec naszej T2 (0039, 103.6 vs 102.7 t/s – nic): T2 testowano tylko na prozie i z łańcuchem MTP (~1.6 ms/poziom). Dla nas: drabinka 5/8/16 wierszy z ogonem lookupu, którego głębokości oceniamy za darmo na CPU; koszt per klasa kontekstu konieczny, bo W16 przy 64k szacunkowo 113 ms.

## Powiązane
- [[metody/_hub|Metody]]
- [[sprzezone-probkowanie-draftu]]
- [[2026-10-14-t1-t2-draft]]
- [[2026-10-16-lookup-kopiowalnosc]]
- [[magnitude]]
