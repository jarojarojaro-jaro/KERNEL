---
typ: research
tags: [research, wyszukiwanie, meta]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/19-kb-wyszukiwanie.md:1-258
status: aktualne
---
# Raport 19: szybkie wyszukiwanie w bazie wiedzy (`kb`)

**Agenci nie znajdowali zapisanych faktów (rekord 130.2 t/s stał w `NOTES.md:331` i `REKORDY.md`), bo `wiki.py search` patrzy tylko na tytuły, streszczenia i tagi; nowe `kb search` (BM25F z polską analizą + multilingual-e5-small + indeks ~24 tys. faktów, fuzja RRF) daje na 80 prawdziwych pytaniach recall@5 0.963 (dev 0.975, held-out 0.950) przy 10–70 ms na zapytanie (2026-10-19).**

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
- [[research/_hub|research]]
- [[wiki-py]]
- [[lekcja-markdown-puste-linie]]
