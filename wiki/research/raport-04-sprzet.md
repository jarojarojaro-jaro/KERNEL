---
typ: research
tags: [research, sprzet, estymacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/04-wykrywanie-sprzetu-i-dobor-modeli.md:9-57
status: aktualne
---
# Raport 04: wykrywanie sprzętu i dobór modeli

**Wykrywanie sprzętu dwuwarstwowe (inwentarz API + capability probe w podprocesie), estymacja pamięci z llama.cpp `--fit`, a prędkości z modelu dwuczłonowego pasmo + liczba kerneli.**

- Każde źródło potrafi kłamać (WMI `AdapterRAM` ucina do 4 GB; Strata wypisał „RTX 4080, 32.0 GB”), więc weryfikacja co najmniej dwoma API i pomiarem.
- Wzór pamięci sprawdzony na logach: Qwen3.8-27B przy 204 800 ctx: 22 593 MiB vs llama.cpp 22 569 MiB (+0,1%); LFM2.5 przy 131 072 ctx: 17 996 vs 17 997 MiB.
- `t_tok ≈ B_tok/(η_bw·BW) + N_kern·t_gap`: η Qwena 0,61–0,67; LFM 0,31 na upstreamie (169 t/s) i 0,55 po 70 łatkach (295 t/s).
- Udziały Steam 09/2026: NVIDIA ~76%, AMD ~16,7%, Intel ~7%; VRAM 16 GB 27,21%, 8 GB 26,71%.
- Priorytet celów: NVIDIA RTX 30/40/50 8–16 GB na Windows, Apple, NVIDIA 24–32 GB, AMD RDNA3/4, APU, CPU, Intel Arc.

## Powiązane
- [[research/_hub|research]]
- [[raport-05-chmura]]
- [[produkt-anatomia-l0-l3]]
- [[modele-katalogowe]]
- [[sufit-pasma-i-mapa-czasu]]
