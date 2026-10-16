---
typ: lekcja
tags: [lekcje, determinizm, mtp]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:264; ~/KERNEL/qwen-opt/NOTES.md:377; git -C ~/llama-master log -1 c09ac6aab; ~/.omp/agent/sessions/-tmp/2026-10-14T15-41-08-699Z_01a13b13-14db-71be-beb0-1fa2146a74f8.jsonl:5515
status: do-sprawdzenia
---
# Ten sam serwer, inna odpowiedź (pending_h)

**Ten sam greedy request bez cache dawał inny tekst przy 1. i 2. wywołaniu po starcie serwera (rozjazd po ~270 znakach); 2026-10-16 prawdopodobną przyczyną okazał się stan MTP `pending_h` nieczyszczony między zapytaniami.**

- 2026-10-14 (`det_probe.py`): identycznie przy PM4=1 i 0, upstream `e60eff95f` tak samo (nawet częściej) → reguła: greedy md5 zawsze na świeżym serwerze (tryb awarii #3 w raporcie 07).
- 2026-10-16 (BitExactSpec): `pending_h` (stan ukryty MTP) nie był resetowany między żądaniami, więc pierwszy token nowego żądania widział stan poprzedniego i dostawał inne drafty. Wyjaśnia to rozjazd tylko, jeśli `det_probe` biegł na serwerze MTP (domyślny `run-llm.sh qwen`) – niepotwierdzone.
- Poprawka: reset na pozycji 0 w `common/speculative.cpp`, commit `c09ac6aab` na `batch-invariant`. Do potwierdzenia: `det_probe.py` na serwerze plain.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[lekcja-bit-exact-attention]]
- [[det-probe]]
- [[batch-invariant]]
