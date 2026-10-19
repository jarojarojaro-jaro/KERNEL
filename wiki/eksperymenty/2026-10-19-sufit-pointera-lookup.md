---
typ: eksperyment
tags: [eksperymenty, spekulacja, lookup, symulacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/21c-copy-paste-lm.md:112-155; ~/KERNEL/product/research/21c-cplm/oracle.py; ~/KERNEL/product/research/21c-cplm/chat.txt:10; ~/KERNEL/product/research/21c-cplm/agent.txt:3-7
status: aktualne
---
# 2026-10-19: sufit „idealnego pointera” nad lookup tail (CPU)

**Symulacja na CPU (69 207 tokenów czatu Qwena, 1 250 132 tokenów wyjść agenta z 40 epok sesji omp): wyrocznia wybierająca najlepszego kandydata lookupu (rola wyuczonego pointera CPLM) daje najwyżej +0.7% t/s na czacie i +5.5% na agencie; reguła AGR2 bez treningu łapie +3.7 z tych 5.5 pp.**

Model kroku: MTP n=4 (profil 0.779/0.565/0.404/0.293), 28.74 ms + 6.40 ms za W16 przy użyciu ogona.

| zestaw | BASE tok/krok | ORA4 | ORA2 | AGR4 | AGR2 | ORA1-HYB |
|---|---|---|---|---|---|---|
| czat | 3.05 | +0.3% | +0.7% | +0.2% | +0.6% | +4.9% |
| agent ALL | 3.34 | +3.8% | +5.5% | +2.3% | +3.7% | +29.8% |
| agent bash | 3.44 | +4.9% | +7.4% | +2.8% | +4.9% | +43.6% |
| agent edit-hashline | 3.63 | +6.0% | +8.3% | +3.8% | +5.4% | +51.8% |
| agent write | 3.17 | +1.6% | +2.5% | +1.2% | +1.9% | +14.5% |

ORA = wyrocznia spośród ≤ 64 kandydatów 4-/2-gram; AGR = kandydat, którego kontynuacja zgadza się z 4 draftami MTP ([[agr-lookup-zgodny-z-mtp]]). ORA1-HYB (+30%) to artefakt modelu: zakłada niezależność MTP od kopiowalności, a na żywo nadpisywanie draftów lookupem dało −0.9…−4% ([[lekcja-mtp-juz-kopiuje]]).

Ograniczenia: wyjścia agenta pisał Claude, nie Qwen; profil MTP uśredniony; wyrocznie nie płacą za fałszywe ogony. Wniosek: wyuczony pointer mógłby dodać ≤ 1.8 pp ponad AGR2 – nie trenujemy.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[2026-10-18-lookup-ogon]]
- [[2026-10-16-lookup-kopiowalnosc]]
- [[raport-21c-cplm]]
