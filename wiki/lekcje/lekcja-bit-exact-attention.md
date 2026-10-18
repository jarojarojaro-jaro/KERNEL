---
typ: lekcja
tags: [lekcje, determinizm, fa]
aktualizacja: 2026-10-16
zrodlo: /tmp/bxd/g1.log, g2.log, h1.log, h2.log, zm.plain.txt, zm.mtp.txt (testy na 7900 XTX 2026-10-16); ~/KERNEL/product/research/12-bit-exact-spekulacja.md §10–12; gałąź batch-invariant; ~/KERNEL/product/research/12-bit-exact-spekulacja.md:356
status: aktualne
---
# Bit-exact: WMMA reaguje na zamaskowane wiersze cache

**Ostatnia różnica między zwykłym dekodowaniem a weryfikacją MTP siedziała w atencji: zamaskowane (-inf) wiersze KV za pozycją tokena zmieniały wynik WMMA, choć matematycznie mnożą się przez 0; wyzerowanie ich (`GGML_HIP_BITEXACT_FA_ZERO_MASKED=1`) daje md5 zwykły = md5 MTP (`74952fd5…`) na Qwen3.8-27B (7900 XTX, 2026-10-16).**

Droga do przyczyny (`llama-bx-diff`):
- Z `LLAMA_SPEC_BITEXACT=1` warstwy 0–6 identyczne, pierwsza różnica `kqv_out-3` (368/6144 liczb, max |d| 1.19e-7).
- Q, maska i wiersze cache K/V do pozycji tokena identyczne; jeden token na blok (`77240c9b3`) i jeden podział (`NSPLIT1`) nic nie zmieniają.
- Jedyne różne wejście: wiersze za pozycją (w zwykłym trybie zera, w MTP K/V draftu). Z ich wyzerowaniem: „verify batch == plain for all 5 positions”, a pełna odpowiedź greedy (2783 znaki, Q4_K_XL, KV q4_0, ctx 8192, MTP n=4 + słownik 64k) ma identyczne md5 w obu trybach.

Lekcja: „mnożenie przez zero” w sprzętowych jednostkach macierzowych nie gwarantuje niezależności od danych; porównywać wszystkie bajty wchodzące do kernela, także zamaskowane.

Pełna lista źródeł rozbieżności (raport 12, kolejność znalezienia): MMVQ N=1 ≠ kolumna wielokolumnowa; fuzja gate/SwiGLU kontraktuje FMA inaczej; liczba splitów KV zależna od N i n_kv; zamaskowane wiersze KV (1–2 ulp w WMMA); podział promptu na ubatche zależny od `n_rs_seq`; `pending_h` nieresetowany.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[lekcja-spekulacja-zmienia-numeryke]]
- [[lekcja-md5-wzgledem-upstreamu]]
- [[llama-bx-diff]]
- [[fattn-kvq]]
- [[raport-12-bit-exact]]
