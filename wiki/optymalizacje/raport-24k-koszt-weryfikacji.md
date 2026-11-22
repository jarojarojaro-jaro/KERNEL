---
typ: optymalizacja
tags: [optymalizacje, weryfikacja, lookup, profil]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/24k-koszt-weryfikacji.md:3-12,18-34; ~/KERNEL/product/research/26-kolejka-gpu-wieczor.md:14
status: aktualne
technika: profil kosztu weryfikacji W16 vs MTP4
werdykt: w-toku
zysk: krok W16 35,61 ms vs MTP4 29,62 ms (+20%)
dowod: raport-24k-koszt-weryfikacji
model: qwen3-8-27b
karta: rx-7900-xtx
wyniki:
  - qwen3-8-27b | rx-7900-xtx | 35.61 ms | krok W16 mvs | 2026-10-19
  - qwen3-8-27b | rx-7900-xtx | 29.62 ms | krok MTP4 mvs | 2026-10-19
---
# Raport 24k: koszt szerokiej weryfikacji W16 vs MTP4 na XTX

**Na `mvs` krok W16 kosztuje 35.61 ms, a MTP4 29.62 ms (+20%); przy tym samym typie kroku 5 → 16 wierszy to ≈ 9.4 ms, w ~70% graf celu (głównie matmul 9–16 kolumn), a kopia logitów D2H to 0.045 ms/wiersz (2026-10-19).**

- Skok 8 → 9 kolumn (MMVQ → K4 WMMA) kosztuje 1.30–1.37 ms (`24k:7`).
- Odpadają hipotezy: przebudowa grafu per szerokość (cache już działa) i budowa ogona na CPU (6.8 µs/krok) (`24k:10-12`).
- Profil z kolejki 26: krok MTP 31.0 vs W16 37.3 ms, w tym bezczynność GPU +1.6 ms (`26:14`) → wprost do [[raport-24m-weryfikacja-gpu]].
- Metoda: [[koszt-szerokosci-weryfikacji]].

## Powiązane
- [[raporty-2026-10-19-20]]
- [[koszt-szerokosci-weryfikacji]]
- [[raport-24m-weryfikacja-gpu]]
- [[raport-24j-router]]
- [[raport-26-kolejka-gpu]]
