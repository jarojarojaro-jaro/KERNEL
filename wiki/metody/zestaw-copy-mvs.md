---
typ: metoda
tags: [metody, pomiar, spekulacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/16b-lookup-tail.md:40-43,72-79; ~/qwen-opt/lookup/copy_prompts.json; ~/qwen-opt/lookup/make_prompts.py:36-75
status: aktualne
---
# Zestawy kopii i edycji: `copy`, `mvs`, `long`

**Trzy zestawy z 16b do mierzenia spekulacji na ruchu agentowym (kopia i edycja), uzupełniające `spec_sweep` (nowe pisanie): `copy` (6 promptów), `mvs` (4 pliki code-edit z MagnitudeVs) i `long` (~30k tokenów).**

- `copy`: edycja pliku 2k/8k, `str_replace` w formacie wywołań narzędzi, edycja hashline po polsku, dosłowne cytowanie sekcji po polsku, refaktoryzacja; generator `make_prompts.py`, źródła zamrożone w `~/qwen-opt/lookup/src/`; 512 tok., T=0 i T=1 × 3 seedy.
- `mvs`: 4 pliki llama.cpp „zwróć cały plik z jedną zmianą” (jak xbench w [[2026-10-16-magnitude-vs-fork]]); 1024 tok., T=0 i T=1 × 2 seedy.
- `long`: `sampling.cpp` + `server-task.cpp` (~30k tokenów), „zmień nazwę funkcji, zwróć cały plik”; 512 tok.
- Runner `copy_bench.py`, ramiona `arm.sh` (świeży serwer, flagi produkcyjne), przeplot `e3_ab.sh` / `e4_ab.sh`.

Wyniki zawsze raportować osobno od `spec_sweep` ([[lekcja-benchmark-kopia]]). Najsłabszy prompt: hashline-pl (model przepisuje funkcje inaczej niż oryginał; r ≥ 8 tylko 31–38% pozycji).

## Powiązane
- [[metody/_hub|Metody]]
- [[spec-sweep]]
- [[zestaw-odlozony]]
- [[2026-10-18-lookup-ogon]]
