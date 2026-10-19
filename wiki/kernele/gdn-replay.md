---
typ: kernel
tags: [kernele, gdn, spekulacja]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:290-295; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:108-111; ~/KERNEL/qwen-opt/research/round6/test-tooling.md:26; ~/KERNEL/product/research/patch-manifest.json (0033); ~/KERNEL/product/research/23e-re-silniki.md:21
status: aktualne
---
# GDN z opóźnieniem: cofanie przez przeliczenie (S4)

**Zamiast zapisywać snapshot stanu rekurencyjnego po każdym tokenie weryfikacji, cache trzyma zatwierdzony stan i bufory wierszy oczekujących, a następna weryfikacja przelicza przyjęte wiersze.**

Łatki 0033–0036 (gałąź `opt-s4`, 3f8c8ddff..b1a203959, 2026-10-13): nowy op `GATED_DELTA_NET_LAG`, układ lag info (0034), prefetch następnego wiersza (0035: 661 → 638 µs/weryfikację), stan czytany z wiersza cache (0036).

Wynik:
- znika 720 MiB zapisów snapshotów na weryfikację;
- GDN 793 → 638 µs/weryfikację;
- VRAM stanów rekurencyjnych 748 → 195 MiB;
- Qwen 29.36 ms/krok, 102.9 t/s; Uncensored 28.27 ms/krok, 106.1 t/s;
- cache promptu działa (follow-up 0.64 s, powrót 1.35 s).

Koszt: zapis stanu przy każdym żądaniu +10–15 ms prefillu (48 kopii buforów oczekujących); poprawka leży w stash na `opt-s4`.

Poprawność: bitowo identyczne. Wyłącznik: `LLAMA_GDN_REPLAY=0` (gasi też 0034–0036 i 0038; manifest wymienia też `GGML_HIP_GDN_REPLAY`). Duża zmiana core: raport 07 ocenia szansę upstreamu jako średnią–niską.

Raport 23e (2026-10-19) proponował „rollback GDN przez replay” jako nowy pomysł ze Straty – to dokładnie ta technika, już w produkcji.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[conv-lag]]: ten sam pomysł dla stanu conv
- [[gdn-fast]]
- [[qwen3-8-27b]]
- [[glowica-mtp]]
