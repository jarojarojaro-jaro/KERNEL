---
typ: narzedzie
tags: [narzedzia, meta, wyszukiwanie]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/19-kb-wyszukiwanie.md:1-40,170-215; ~/KERNEL/tools/kb/README.md; ~/KERNEL/tools/kb/gold/gold.jsonl
status: aktualne
---
# kb: szybkie wyszukiwanie w bazie wiedzy

**`kb search <pytanie>` i `kb facts <pytanie> [--max|--min]` (`~/.local/bin/kb`) przeszukują cały `~/KERNEL` (wiki, raporty, `NOTES.md`) i zwracają odpowiedź z `plik:linia`. Na 80 prawdziwych pytaniach recall@5 wynosi 0.963, a zapytanie trwa 10–70 ms.**

- **Jak szuka.** Łączy trzy listy przez RRF:
  - BM25F z polską analizą (bez ogonków, lekki stemmer, liczby `130.2`/`27k`, jednostki `t/s`);
  - embeddingi multilingual-e5-small (int8, CPU);
  - indeks ~24 tys. faktów „liczba + jednostka + kontekst”.

  Pytania „najlepszy/rekord” sortują fakty po wartości, najpierw z [[REKORDY]].
- **Wyniki z 2026-10-19 (recall@5).**

  | metoda | recall@5 |
  |---|---|
  | hybryda + fakty | 0.963 |
  | hybryda | 0.912 |
  | BM25 | 0.825 |
  | `wiki.py search` (liczone łagodnie, na poziomie pliku) | 0.750 |
  | same embeddingi | 0.688 |

  Zapytanie w procesie trwa p95 131 ms.
- **Indeks i demon.** Indeks zajmuje 16 MB, wektory 33 MB; leżą w `~/.cache/kb`, poza repo. Indeks sam się odświeża: sprawdzenie zmian trwa 0.04 s, pełna przebudowa leksykalna 0.33 s. Model trzyma demon `kb serve` (startuje sam, RSS ~0.7 GB, kończy pracę po 30 min bezczynności).
- **Pozostałe polecenia.** `--json` dla agentów, `kb eval` mierzy recall na złotym zbiorze. [[wiki-py]] `search` deleguje do `kb`.

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[wiki-py]]
- [[serve-bench]]
- [[2026-10-16-wszystko-do-bazy-wiedzy]]
- [[REKORDY]]
