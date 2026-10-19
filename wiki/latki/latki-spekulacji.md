---
typ: latka
tags: [latki, spekulacja, mtp]
aktualizacja: 2026-10-18
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:86-88,283-288,310-317,321,327,330; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:79,107,114,116,121; ~/KERNEL/product/research/16f-xtx-szybkie.md:94-115
status: aktualne
---
# Łatki spekulacji (słownik draftu, requant, okno, adaptacja)

**Łatki zmieniające sam mechanizm draftu MTP: część dała zysk (słownik 64k, draft IQ4_XS), część została opt-in albo okazała się negatywna.**

| łatka | co | wynik | status |
|---|---|---|---|
| 0004 (2026-10-09) | `--spec-draft-vocab`: głowica draftu liczy logity tylko dla N najczęstszych tokenów | 16k −5%, 32k +7%, 48–64k +7.5% (wybrane 64k), 96k +6% | domyślnie w `run-llm.sh` |
| 0032 (S2, 2026-10-13) | przekwantyzowanie głowicy/bloku MTP przy ładowaniu (`--spec-draft-head-type`, `--spec-mtp-type`) | draft 4.82 → 3.62 ms/krok; akceptacja −2–3%; netto +1–3% t/s; +0.4 GB VRAM | domyślnie IQ4_XS |
| 0039 (T2) | adaptacyjna długość draftu wyceniana kosztem (`--spec-draft-adaptive`) | Qwen 103.6 vs n=4 102.7 (czat/proza −5 t/s), Uncensored gorzej | opt-in, wyłączone |
| 0041 (T3) | warstwa MTP liczy tylko K/V dla wierszy promptu | prefill 6.6k 913 → 936 | bitowe, aktywne |
| 0046 (S3) | okno atencji warstwy MTP (`--spec-mtp-window`) | W=8192: 105 → 90 t/s (akceptacja 3.31 → 2.78) | negatywne, domyślnie 0 |

Weryfikacja zostaje bez zmian, więc 0004, 0032, 0039 zmieniają tylko drafty (klasa DIST): rozkład wyjścia ten sam, ale tekst greedy może się różnić przy remisie. Konfiguracja (bez łatki): KV draftu q4_0 włączone domyślnie (94k: 97.5 → 100.6 t/s), draft n=4.

Typ bloku MTP na żywo (16f E2, 2026-10-18, 5 seedów ABBA): IQ4_XS 113.2 t/s, 3.063 tok/krok, 28.14 ms/krok vs natywny Q6_K 109.4, 3.012, 28.76; q8_0 103.1 vs 106.4 t/s (2 seedy). Offline +0.45% z pilota 11 nie przenosi się; IQ4_XS zostaje.

## Powiązane
- [[latki/_hub|Łatki]]
- [[glowica-mtp]]
- [[mtp-draft-graf]]
- [[ms-na-krok]]
- [[latki-hostowe]]
