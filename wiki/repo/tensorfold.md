---
typ: repo
tags: [repo, spekulacja, dflash, metal]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/tensorfold/README.md:1-25; ~/KERNEL/qwen-opt/research/repos/REPOS-PODSUMOWANIE.md:41
status: aktualne
---
# TensorFold (ashhart/TensorFold)

**Serwer Zig z kontraktem dokładności („drafted == plain”) dla 7 rodzin modeli (HEAD `0efbd447`, 2026-10-12, v1.0.8; aktualizacja do v1.0.11 2026-10-14).**

Repo: 1560 commitów na `main`, 32 tagi w 18 dni, 552 PR-y, 235 issues. Rdzeń „lanes”: jeden forward weryfikuje drafty MTP, drzewa DFlash2 i kopie n-gram. Najważniejsze lekcje: weryfikacja na WMMA, gdzie dodatkowe wiersze są prawie darmowe (R9700: 12 → 16 wierszy +1.2 ms; u nas kolumna ok. 1.4 ms), drzewa draftów nad GDN, rollback GDN przez „lagged state” (zob. conv-lag), głębokość draftu wyceniana kosztem mierzonym przy starcie (+6–7%). Na 27B są wolniejsi od nas: HIP na W7800 25.8–27.2 tok/s plain (#490), R9700 z DFlash2 95.7 chat / 126 code tok/s przy T=1 (#100). Aktualizacja v1.0.11: LFM2.5 na Metal z n-gramem, „wszystkie loady przed sumami”, bramka KL przepuściła 2 celowe błędy (stąd nasze kanarki KLD).

## Powiązane
- [[repo/_hub|repo]]
- [[strata]]
- [[hipfire]]
- [[conv-lag]]
- [[bramka-kld-kanarki]]
