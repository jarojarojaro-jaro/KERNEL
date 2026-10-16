---
typ: kernel
tags: [kernele, conv, spekulacja]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:222,299,305-309,314-318; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:89,113
status: aktualne
---
# Historia conv z opóźnieniem (T1, łatka 0038)

**Stan konwolucji Qwena trzymany jak stan GDN w S4: okno wokół wierszy oczekujących zamiast snapshotów, co usunęło „klif” przy drafcie ≥ 8 tokenów.**

Tło: A5 (0014, 2026-10-12) złożyło concat + 5 kopii snapshotów + gather w jednym SSM_CONV. Po K4 (2026-10-13) draft ≥ 8 nadal przegrywał przez limit `SSM_CONV_FUSED_MAX_SNAPSHOTS` 8: ~470 dodatkowych kerneli cpy/concat na krok.

0038 (gałąź `opt-t2`, b9b476c87; commit z 2026-10-13 wg daty autora, wpis w NOTES pod 2026-10-14): historia = GET_ROWS kroków n_keep..n_keep+2, zapis jednym transponowanym CPY, oba złożone w SSM_CONV. Bez snapshotów i bez limitu 8.

rocprof weryfikacji (kernele / wall / krok):
- draft 8: 1391 / 34.2 / 40.8 ms → 832 / 30.9 / 37.2 ms;
- draft 12: 1585 / 36.4 / 45.7 ms → 834 / 32.2 / 41.1 ms;
- draft 7 i n=4 bez zmian.

Greedy md5 = d3a0973ae (plain, n=4/8/12, oba modele, powrót z cache promptu): bitowo identyczne. Wyłącznik: `LLAMA_CONV_LAG=0`. Po scaleniu: Qwen 29.36 ms/krok 102.6 t/s; Uncensored 28.28 ms/krok 105.0 t/s.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[gdn-replay]]
- [[wmma-small-n]]
- [[2026-10-14-t1-t2-draft]]
- [[qwen3-8-27b]]
