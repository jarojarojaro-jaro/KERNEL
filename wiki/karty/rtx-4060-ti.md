---
typ: karta
tags: [karty, nvidia, sm-89]
aktualizacja: 2026-10-20
zrodlo: ~/KERNEL/product/research/29-4060ti.md:3-5,9-21,25-28,56-71,77-82
status: aktualne
---
# NVIDIA RTX 4060 Ti 16 GB (Vast, serwer buildów)

**Ada sm_89, 16 GB GDDR6 288 GB/s; zmierzona 2026-10-20 na hoście Vast z limitem mocy 100 W i PCIe gen3 x8: nasz silnik daje Qwen3.8-27B UD-Q3_K_XL czat 18.6 → 35.4 t/s (×1.90) i LFM2.5 QAD-Q4_0 114.4 → 149.4 t/s (×1.31).**

- Sprzęt: 16380 MiB, domyślny limit 165 W (host ustawił 100 W, nie do zmiany w kontenerze), sterownik 595.84 (CUDA 13.2 uruchamia buildy CUDA 12.8); host Ryzen 9 3950X, 31 GB RAM (`29:25-28`).
- Qwen Q3_K_XL (MTP w pliku): czat T=1 U0 18.6 / U1 30.6 / T 35.4 t/s, krok 81.56 vs 97.74 ms; mvs 170.9 t/s (×3.42 vs U1); decode po 16k T=0 40.1 t/s (`29:56-62`).
- Mieści kontekst 32k: VRAM T 14848 MiB po załadowaniu (`29:70`).
- Prefill T w `llama-bench` −3.5…−3.9% (sm_89) – do zbadania (`29:66-67`).
- Raport: [[raport-29-4060ti]]. Bliźniak 16 GB: [[rtx-5060-ti]] (T 50.8 t/s przy 448 GB/s).

## Powiązane
- [[karty/_hub|karty]]
- [[raport-29-4060ti]]
- [[rtx-5060-ti]]
- [[rtx-3090]]
- [[REKORDY]]
