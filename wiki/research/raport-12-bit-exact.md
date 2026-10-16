---
typ: research
tags: [research, determinizm, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/12-bit-exact-spekulacja.md:1-13,82-112
status: aktualne
---
# Raport 12: bitowo identyczna spekulacja

**Plain greedy (`c4708318`) i MTP (`6f14e814`) dają różne md5, bo ta sama pozycja liczona jest innym kernelem przy N=1 i N=2..6; tryb `LLAMA_SPEC_BITEXACT=1` daje N=1 arytmetykę kerneli wielokolumnowych.**

Data 2026-10-16, gałąź `batch-invariant` od `8c942e5a9`, bez GPU.
- Koszt (szacunki): weryfikacja MTP ~0 (MMVQ te same kernele), FA przy 32k ~0.5%, przy 98k ~1.5%; plain bez fuzji GLU ~0.3–1.3%.
- Prototyp offline: build HIP rc=0; `isadiff_bx.py` 862/862 bazowych kerneli MMVQ bajtowo identycznych; `mmvqemu.py` – każde słowo wyniku n1_multi to ten sam węzeł DAG IEEE co kolumna kernela n-kolumnowego (n=2..8, Q4_K…Q8_0); `gdnseq.py` – plain i LAG identyczne dla 36 wyjść.
- Niezweryfikowane offline: niezależność kolumn WMMA w FA, `gdn_conv_ab`, combine FA.
Później na GPU (2026-10-16) atencja okazała się kluczowa (zob. lekcja bit-exact attention).

## Powiązane
- [[research/_hub|research]]
- [[raport-10-post-training]]
- [[raport-13-rocm-10-1]]
- [[batch-invariant]]
- [[2026-10-16-bit-exact]]
