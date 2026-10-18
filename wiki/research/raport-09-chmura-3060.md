---
typ: research
tags: [research, chmura, nvidia, sm-86, kwanty]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/09-chmura-3060.md:1-275; ~/qwen-opt/cloud/results/3060-20261016/NOTE-quantkld-overwrite.txt:1-5
status: aktualne
---
# Raport 09 (3060): Saluki i Bonsai na RTX 3060

**RTX 3060 12 GB (sm_86, Vast, 2026-10-16), tylko Saluki 27B i Bonsai 2 27B: nasz silnik daje jednocyfrowy zysk (Saluki 22.3 → 23.4 t/s, +4.8%; Bonsai Q2_0 33.15 → 35.51, +7.1%), PQ2_0 → Q2_0 to bezstratny repack, a KLD forka vs upstream jest na poziomie szumu.**

- Sprzęt: 170 W (stale na limicie), PCIe gen3 x16, Xeon E5-2698 v4; pomiary w trakcie kompilacji nieważne (Saluki 9.7 zamiast 22.5 t/s). Koszt ≈ $0.82, instancja zniszczona.
- Jakość (wikitext-2, 64×512): Saluki 7.6665, Bonsai 8.6154 (prism) / 8.6171 (Q2_0 upstream i fork); po polsku Saluki pisze czysto, Bonsai robi błędy językowe.
- Prędkość: Bonsai PTQ1_0 w forku prism **44.75 t/s** (6.8 GB VRAM) – najszybszy; nasz fork z Q2_0 35.5 t/s (−21% vs PTQ1_0).
- md5 DIFF-BUILD; diagnoza węzeł po węźle: pierwszy różny tensor `qkv_mixed` warstwy 0 (MMVQ multi-kolumna 0001/0002), drugie źródło 0013 (nowy przełącznik `GGML_CUDA_GDN_L2_FUSE=0`, commit `7b344114d`).
- Bramka KLD (16×512, logity upstream jako baza) **PASS**: Saluki fork 0.000650 vs szum upstream 0.000612; Bonsai 0.000323 vs 0.000206.
- `GGML_HIP_GATE_UP_Q8` szkodzi na i-quantach (+2.39% po wyłączeniu); KV f16 szybszy przy 8k (+3.7% / +5.7%); `-ub 1024`; eksperyment `GGML_CUDA_MMVQ_N1_WIDE` −12.6…−21% (odrzucony).
- n-gram neutralny; port naszych łatek na fork prism: 9 OK, 65 konfliktów.
Werdykt: teza raportu 08 potwierdzona co do rzędu wielkości dla modeli bez MTP – nie obiecywać ×1.5–2.

Uwaga (2026-10-18): `results/3060-20261016/hw/*` i część `build/*` zostały nadpisane danymi innej instancji 3060 (120 W, EPYC 7662); oryginały stracone ([[lekcja-unikalny-katalog-wynikow]]). Liczby w tej notatce pochodzą z raportu 09.

## Powiązane
- [[research/_hub|research]]
- [[raport-09-chmura-3090]]
- [[raport-09-chmura-5060ti]]
- [[rtx-3060]]
- [[saluki]]
- [[bonsai]]
