---
typ: research
tags: [research, determinizm, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/12-bit-exact-spekulacja.md:1-13,82-112,144-197; ~/KERNEL/product/research/15b-spekulacja-frontier.md:22-26,136-143
status: aktualne
---
# Raport 12: bitowo identyczna spekulacja

**Plain greedy (`c4708318`) i MTP (`6f14e814`) dają różne md5, bo ta sama pozycja liczona jest innym kernelem przy N=1 i N=2..6; tryb `LLAMA_SPEC_BITEXACT=1` na GPU wyrównał warstwy 0–6, zostało wyjście atencji `kqv_out-3`, a następne komendy GPU czekają na zgodę.**

Data 2026-10-16, gałąź `batch-invariant`.
- Prototyp offline: `isadiff_bx.py` 862/862 bazowych kerneli MMVQ bajtowo identycznych; `mmvqemu.py` – n1_multi to ten sam węzeł DAG IEEE co kolumna kernela n-kolumnowego; `gdnseq.py` – plain i LAG identyczne dla 36 wyjść.
- Pierwszy test GPU (`c09ac6aab`): bez env plain = `c4708318`; z env plain `8cca9b70`, MTP `4c6d328b` – nadal różne.
- `llama-bx-diff` na GPU: warstwy 0–6 identyczne, pierwszy różny węzeł `kqv_out-3` (368/6144 słów, max |d| 1.19e-7); `--no-lag` to samo, Q/K/V przed FA identyczne.
- Poprawka `77240c9b3` (jeden token na blok) i wspólne kafle dają **bitowo te same** różnice → hipoteza sąsiednich kolumn obalona.
- Pozostali kandydaci: inne komórki cache w kontekście LAG, inna treść wiersza p0, inna maska, ścieżka bitexact niewykonana. Narzędzia: `GGML_HIP_BITEXACT_FA_LOG=1`, porównanie maski i wierszy cache (`6e261fdb4`).
- Następny krok: dwie komendy `llama-bx-diff` (< 2 min GPU), czekają na zgodę.
- Koszt (szacunki): weryfikacja MTP ~0, FA przy 32k ~0.5%, plain bez fuzji GLU ~0.3–1.3%.

Metodyka z tqLLM (raport 15b): test end-to-end na długim prompcie (3.7k tokenów, 512 wyjścia) z przemiataniem `ubatch` ∈ {64, 512, 4096} i kontekstu ∈ {16k, 64k}, bo u nich błąd wychodził tylko przy `-ub 4096` (`8bb1119`, wycofany w `015a14a`); test `memcmp` per kolumna 1..16 dla K4 WMMA jako warunek bitexact dla W > 8.

## Powiązane
- [[research/_hub|research]]
- [[raport-10-post-training]]
- [[raport-11-mtp-pl-pilot]]
- [[batch-invariant]]
- [[2026-10-16-bit-exact]]
- [[lekcja-bit-exact-attention]]
- [[tqllm]]
