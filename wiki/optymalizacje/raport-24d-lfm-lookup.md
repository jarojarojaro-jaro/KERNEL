---
typ: optymalizacja
tags: [optymalizacje, lfm, lookup, wynik-negatywny]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24d-lfm-lookup.md:3,12-19,24-27,35-36,46
status: aktualne
technika: lookup kontekstowy bez draftera (LFM)
werdykt: odrzucone
zysk: +17% copy W8 (288,2 → 334,7 t/s), tekst T=0 ≠ plain
dowod: raport-24d-lfm-lookup
model: lfm2-5-24b-a2b
karta: rx-7900-xtx
wyniki:
  - lfm2-5-24b-a2b | rx-7900-xtx | 334.7 t/s | copy lookup W8; T=0 | 2026-10-19
  - lfm2-5-24b-a2b | rx-7900-xtx | 312.4 t/s | copy lookup W16; T=0 | 2026-10-19
  - lfm2-5-24b-a2b | rx-7900-xtx | 288.2 t/s | copy bez lookup; T=0 | 2026-10-19
---
# Raport 24d: lookup bez draftera dla LFM2.5 – nie adoptować

**Sam lookup kontekstowy na LFM2.5 daje copy +17% (W8, T=0) zamiast oczekiwanych ×2.3–2.8, bo LFM zawsze myśli i 512 tokenów to reasoning; tekst T=0 różni się od plain, dokładności nie udowodniono (2026-10-19).**

- ABBA: wyłączony 288.2/285.9, W16 312.4/313.8 (+9%), W8 334.7/341.8 t/s (+17%) (`24d:14-16`).
- Krok W16 kosztuje 11.9 ms wobec 3.5 ms plain (MoE ładuje więcej ekspertów); W8 > W16 (akceptacja 75% vs 59%) (`24d:19`).
- md5: wyłączony `894e56e4` = baza, `=3 W16` `2237ad17` ≠ (`24d:24-25`).
- GGUF LFM ustawia `repeat_penalty 1.05`, więc „T=0” nie jest argmaxem (`24d:46`).
- Naprawiony crash `graph_max_nodes` dla `n_rs_seq > 0` (`54d382932`). Profil LFM topki: `-b/-ub 2048`, lookup 0 (`24d:35-36`). Model: [[lfm2-5-24b-a2b]].

## Powiązane
- [[raporty-2026-10-19-20]]
- [[lfm2-5-24b-a2b]]
- [[lfm-czulosc-na-podzial-batcha]]
- [[testy/2026-10-18-lookup-ogon]]
