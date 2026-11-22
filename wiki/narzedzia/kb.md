---
typ: narzedzie
tags: [narzedzia, meta, wyszukiwanie]
aktualizacja: 2026-11-22
zrodlo: ~/KERNEL/product/research/19-kb-wyszukiwanie.md:1-40,170-215; ~/KERNEL/tools/kb/README.md; ~/KERNEL/tools/kb/gold/gold.jsonl; ~/KERNEL/product/research/19-kb-wyszukiwanie.md; ~/KERNEL/product/research/19-kb-wyszukiwanie.md:1-258
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

Raport i pomiar: [[narzedzia/kb]]; zasada użycia: [[najpierw-baza-kb]].

## Ze scalonej notatki: Raport 19: szybkie wyszukiwanie w bazie wiedzy (`kb`)

Agenci nie znajdowali zapisanych faktów (rekord 130.2 t/s stał w `NOTES.md:331` i `REKORDY.md`), bo `wiki.py search` patrzy tylko na tytuły, streszczenia i tagi; nowe `kb search` (BM25F z polską analizą + multilingual-e5-small + indeks ~24 tys. faktów, fuzja RRF) daje na 80 prawdziwych pytaniach recall@5 0.963 (dev 0.975, held-out 0.950) przy 10–70 ms na zapytanie (2026-10-19).

| tryb | recall@5 |
|---|---|
| hybryda + fakty (domyślny) | 0.963 |
| hybryda | 0.912 |
| BM25 + fakty | 0.875 |
| BM25 | 0.825 |
| `wiki.py search` (łagodnie, na pliku) | 0.750 |
| same embeddingi | 0.688 |
| same fakty | 0.550 |

Korpus 654 pliki, 21 600 fragmentów, 24 117 faktów; zapytanie w procesie p50 38 ms, p95 131 ms; indeks 16 MB + wektory 33 MB + model 118 MB; bez modelu spada do BM25 + faktów (0.875, 0.07 s). Nie trafia 3/80 (np. koszt kampanii NVIDIA po angielsku). Ograniczenia: pliki JSON wyników (`spec_sweep.jsonl`, scorecardy) nieindeksowane – rekordy idą przez [[REKORDY]]; złoty zbiór pisał agent. Narzędzie: [[kb]]; zasada: [[najpierw-baza-kb]].

## Powiązane
- [[narzedzia/_hub|narzedzia]]
- [[wiki-py]]
- [[serve-bench]]
- [[2026-10-16-wszystko-do-bazy-wiedzy]]
- [[REKORDY]]
