---
typ: kernel
tags: [kernele, host, dlugi-kontekst, maska]
aktualizacja: 2026-11-07
zrodlo: ~/KERNEL/product/research/66e-anatomia-serwowania-tqllm.md:96-115,185-187; ~/KERNEL/product/research/66e-skrypty/maskbench.cpp; ~/KERNEL/product/research/66d-saber-engine-rdna.md:122,163
status: do-sprawdzenia
---
# Maska KQ na hoście przy długim kontekście

**Topka buduje maskę KQ na CPU dla każdego grafu z atencją, w czasie liniowym od `n_kv`; mikrobench szybkiej ścieżki daje 0.25 ms na graf weryfikacji przy 199k (1 µs przy 2k), czyli ~0.5 ms na krok ≈ 1.1%, a nie 2–6 ms z hipotezy F5 (raport 66e, 2026-11-07).**

| `n_kv` | 1 wiersz (draft) | 5 wierszy (weryfikacja) |
|---|---|---|
| 2 048 | 0.7 µs | 1.0 µs |
| 98 304 | 33.6 µs | 54.3 µs |
| 199 936 | 69.1 µs | 234.7 µs |
| 262 144 | 91.4 µs | 257.7 µs |

Ryzen 7 5700X, `-O2 -march=native`, najlepszy z 200 powtórzeń, bez uploadu.

- Maska nie tłumaczy ~13 ms przyrostu kroku „niezwiązanego z pasmem” między 1.7k a 199k. F5 najpewniej mierzył ścieżkę generyczną sprzed `LLAMA_KV_MASK_FAST` `[INFERENCE]`.
- Precedens z Sabera (ws-h28): upload co krok bloba wielkości pojemności zamiast zmienionego zakresu kosztował +6.6 ms/krok. Reguła: wejścia kroku wysyłać przyrostowo.
- Bramka: `LLAMA_HOSTGAP_TRACE=1` przy 1.7k/94k/199k (~20 min GPU). Dopiero przy `graph→inputs` ≥ 0.2 ms przy 199k warto budować maskę w czasie draftu albo na GPU (+0.5…1.5%).

## Powiązane
- [[kernele/_hub|kernele]]
- [[raport-24o-luki-hosta]]
- [[latki-hostowe]]
- [[raport-37-proza-100]]
- [[saber-engine]]
- [[raport-66-synteza]]
