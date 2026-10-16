---
typ: repo
tags: [repo, spekulacja, dflash, metal]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/tensorfold/README.md:1-25; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:41; ~/KERNEL/product/research/15c-nowe-silniki.md:34-37,93-102,210-221
status: aktualne
---
# TensorFold (ashhart/TensorFold)

**Serwer Zig z kontraktem dokładności („drafted == plain”) dla 7 rodzin modeli (HEAD `0efbd447`, 2026-10-12, v1.0.8; aktualizacja do v1.0.11 2026-10-14).**

Repo: 1560 commitów na `main`, 32 tagi w 18 dni, 552 PR-y, 235 issues. Rdzeń „lanes”: jeden forward weryfikuje drafty MTP, drzewa DFlash2 i kopie n-gram. Najważniejsze lekcje: weryfikacja na WMMA, gdzie dodatkowe wiersze są prawie darmowe (R9700: 12 → 16 wierszy +1.2 ms; u nas kolumna ok. 1.4 ms), drzewa draftów nad GDN, rollback GDN przez „lagged state” (zob. conv-lag), głębokość draftu wyceniana kosztem mierzonym przy starcie (+6–7%). Na 27B są wolniejsi od nas: HIP na W7800 25.8–27.2 tok/s plain (#490), R9700 z DFlash2 95.7 chat / 126 code tok/s przy T=1 (#100). Aktualizacja v1.0.11: LFM2.5 na Metal z n-gramem, „wszystkie loady przed sumami”, bramka KL przepuściła 2 celowe błędy (stąd nasze kanarki KLD).

## v1.0.12 (raport 15c, 2026-10-16)
- LFM2.5-24B-A2B tylko na Metal: M5 Ultra 261.5 t/s plain (30% pasma) i 299.5 na kodzie z n-gramem; nasz XTX 293.7 t/s na cięższym Q5_K_M (54%). Koszt okna weryfikacji LFM: 1.24–1.68× dla k = 2–4 (#868).
- Nowe techniki: „twins” (GEMV 1/2–7/8–32 wiersze z tą samą kolejnością fma co kafle prompt, sprawdzane bitowo przy ładowaniu), dokładny dekod 4-bit „half pair” 0x6400 (pre-scaling gubił subnormale: x = 2^-126 daje 0x0080 → 0x0000), Recall (trwały n-gram wyceniany wobec MTP; powtórki 2.4× na 27B), TP przez hosty z podziałem samych ekspertów (TP=2 == TP=1 bitowo).
- Super VL na 2×GB10: MTP 38.2 → 46.8 t/s (recipe:86-91).
- HIP to preview i nadal słaby: 2×W7800 TP2 39.0 t/s plain na 27B (#655) wobec naszego 1×XTX 43.2.

## Powiązane
- [[repo/_hub|repo]]
- [[strata]]
- [[hipfire]]
- [[conv-lag]]
- [[bramka-kld-kanarki]]
- [[raport-15c-nowe-silniki]]
