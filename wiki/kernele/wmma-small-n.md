---
typ: kernel
tags: [kernele, wmma, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:297-300; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:112; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:21; ~/KERNEL/product/research/patch-manifest.json (0037)
status: aktualne
---
# WMMA small-N: weryfikacja 9–16 tokenów (K4, 0037)

**Kernel WMMA iu8 (RDNA3) dla weryfikacji 9–16 kolumn, gdzie wielokolumnowe MMVQ (2–8) już nie sięga.**

- Łatka 0037 (d3a0973ae, 2026-10-13). Dla Q6_K działa od 7 kolumn; n ≤ 8 bez zmian.
- llama-bench Qwen: n=9 49.2 → 32.1 ms, n=16 51.0 → 35.0 ms; ~0.43 ms na kolumnę.
- Serwer po K4: n=5 105.4 t/s średnio (czat/proza słabiej), n=4 101.7. Draft ≥ 8 nadal przegrywał przez osobny „klif” w SSM_CONV (~470 dodatkowych kerneli cpy/concat), naprawiony później przez [[conv-lag]].
- Przy domyślnym drafcie n=4 kernel jest nieaktywny.
- Poprawność: zmiana numeryki; KLD 0.0122–0.0128 przy bazie 0.0124±0.0006 → PASS (raport 07).
- Wyłącznik: brak (build); revert czysty (LOO).
- Tylko gfx110x; RDNA4 wymaga portu (inny układ WMMA gfx12).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmvq-multikolumnowe]]
- [[conv-lag]]
- [[bramka-kld-kanarki]]
- [[rdna3-gfx1100]]
