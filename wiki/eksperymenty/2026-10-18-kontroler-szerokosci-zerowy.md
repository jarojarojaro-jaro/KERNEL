---
typ: eksperyment
tags: [eksperymenty, spekulacja, kontroler, wyniki-negatywne]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:34-38,98-112,132-136; ~/qwen-opt/lookup/logs/e4_run2.txt (linie „widths”); ~/qwen-opt/lookup/logs/e4_postfix.txt:2-5
status: aktualne
---
# 2026-10-18: kontroler szerokości 5/8/16 – wynik zerowy

**Kontroler w stylu Magnitude (`LLAMA_SPEC_LOOKUP_ADAPT=1`, `586f1d596`) na każdym zestawie kopii wybiera 16 (`widths 5:0 8:0 16:662`), więc daje to samo co stałe W16 (±0.2%); kill 16i E-X3 („> 3% gorzej”) zaliczony, ale bez wartości dodanej.**

Konstrukcja: drabinka 5/8/16, akceptacja per głębokość liczona za darmo z propozycji lookupu (także niezweryfikowanych), zanik 0.99; koszt = zmierzony krok 5-wierszowy + ΔV z E2 (Δ8 = 2.45 + 0.025·k, Δ16 = 6.2 + 0.1·k, k = kontekst/1024).

Błędy:
1. Szacunek kroku 5-wierszowego na kopii 34–39 ms zamiast ~29.8 ms (mierzone rzadkie kroki bez ogona po chybieniach) – przesuwa wybór ku szerszym blokom.
2. Na czacie wybiera 16 dla 15 ogonów z akceptacją 18% (29/162), bo ocena warunkowa „pierwsze 4 trafione” jest za optymistyczna przy P(głębokość 4) = 0.158.

Zalecenie: stałe `LLAMA_SPEC_LOOKUP=3 LLAMA_SPEC_LOOKUP_W=16`; kontroler naprawiać dopiero przy workloadzie, gdzie 8 bije 16 (np. kopia ≥ 64k).

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[kontroler-szerokosci-draftu]]
- [[2026-10-18-lookup-ogon]]
- [[wyniki-negatywne]]
