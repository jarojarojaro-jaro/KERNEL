# kb — szybkie wyszukiwanie w bazie wiedzy KERNEL

Jedno polecenie odpowiada na „jaki był najlepszy X / czy mierzyliśmy Y / co zdecydowaliśmy o Z” z miejscem `plik:linia`. Przeszukuje cały `~/KERNEL` (wiki, `product/research`, `qwen-opt/*.md`, `STAN-PRAC.md`, `app/REPORT.md`, …). Używa BM25 z polską analizą, embeddingów multilingual-e5-small i indeksu faktów liczbowych. Działa tylko na CPU. Projekt i pomiary: `product/research/19-kb-wyszukiwanie.md`.

```bash
kb search najlepszy wynik Qwen XTX            # top 8 fragmentów: ~/KERNEL/plik:linia + linia z odpowiedzią
kb search dlaczego PM4 resetuje GPU --full    # całe fragmenty zamiast jednej linii
kb facts rekord pl-kod                         # liczby z jednostką pasujące do pytania, „najlepszy/rekord” = max t/s
kb facts KLD saluki --min                      # wymuszone sortowanie po wartości (--max/--min), filtr --unit t/s|ms|GB|%|×|$|KLD|RPM
kb search … --json / kb facts … --json        # dla agentów: path, line, start/end, heading, text, value/unit
kb reindex                                     # ręczne odświeżenie (zwykle niepotrzebne: search sam wykrywa zmiany)
kb stats                                       # rozmiar indeksu, liczba plików/fragmentów/faktów
kb eval --modes wiki.py,bm25,dense,hybrid,bm25-facts,hybrid-facts,facts --misses --explain
```

Tryby `--mode`:
- `hybrid-facts` (domyślny): BM25, e5 i fakty łączone przez RRF.
- `hybrid`: BM25 i e5.
- `bm25-facts`: bez modelu, ok. 70 ms w procesie.
- `bm25`
- `dense`

## Jak działa w praktyce

- **Odświeżanie.** Każde zapytanie sprawdza mtime i rozmiar plików (~2 ms). Zmienione pliki są dzielone ponownie, a brakujące embeddingi liczone (wektory są kluczowane hashem tekstu fragmentu).
- **Demon.** Model trzyma demon `kb serve`, który startuje sam przy pierwszym `kb search` (`setsid nice -n 19 taskset -c 0-3`). Gniazdo: `~/.cache/kb/index-*.sock`. Kończy pracę po 30 min bezczynności (`KB_IDLE`).
  - Z rozgrzanym demonem zapytanie trwa 10–70 ms.
  - Bez demona pierwsze zapytanie trwa ~0.9 s, bo samo ładowanie tokenizera i sesji ONNX zajmuje 0.4–1 s.
  - `KB_NO_DAEMON=1` liczy zawsze w procesie.
- **Gdy brakuje modelu albo ponad 400 fragmentów nie ma wektora,** `search` w procesie spada do `bm25-facts` i pisze o tym na stderr. Demon wtedy dolicza brakujące wektory.
- **Wątki i obciążenie.** Domyślnie 4 wątki (`KB_THREADS`), bo serwer jest współdzielony z eksperymentami. GPU nie jest używane.

## Pliki

| co | gdzie |
|---|---|
| źródła | `~/KERNEL/tools/kb/src` (Rust) |
| złoty zbiór pytań | `gold/gold.jsonl` (80 pytań, oczekiwane miejsca jako dosłowne `needle`) |
| indeks leksykalny + fakty | `~/.cache/kb/index-<hash korzenia>.bin` (~16 MB) |
| wektory | `~/.cache/kb/vectors-<hash>-multilingual-e5-small.bin` (~33 MB) |
| model | `~/models/kb/multilingual-e5-small/` (`model_quantized.onnx` 118 MB, `tokenizer.json`) |
| ONNX Runtime 1.22 (statycznie) | `tools/kb/.ort/` (poza gitem) |

Zmienne: `KB_ROOT` (korzeń, domyślnie `~/KERNEL`), `KB_CACHE`, `KB_MODEL`, `KB_THREADS`, `KB_IDLE`, `KB_NO_DAEMON`.
Strojenie (tylko do eksperymentów): `KB_W_TITLE`, `KB_W_HEAD` (wagi pól przy `reindex --full`), `KB_RRF_K`, `KB_W_DENSE`, `KB_W_FACTS`, `KB_PER_FILE`.

## Instalacja, testy

```bash
~/KERNEL/tools/kb/setup.sh        # ORT (sha256), model z HF, build i reindex pod /tmp/cpuheavy.lock, ~/.local/bin/kb
cd ~/KERNEL/tools/kb && flock /tmp/cpuheavy.lock nice -n 19 taskset -c 0-3 cargo test --release -j4   # testy + złoty zbiór (recall@5 ≥ 0.9, p95 < 200 ms)
```

Pierwszy pełny indeks embeddingów to ok. 21 tys. fragmentów. Na 8 wątkach z `nice` przy obciążonym serwerze trwał ~9 min. Później liczone są tylko zmienione fragmenty.

`python3 wiki/tools/wiki.py search …` deleguje do `kb search`, jeśli `kb` jest w PATH. `KB_NO_DELEGATE=1` przywraca stare wyszukiwanie po tytułach.
