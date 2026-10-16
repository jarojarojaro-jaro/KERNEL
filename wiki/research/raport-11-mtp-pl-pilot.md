---
typ: research
tags: [research, mtp, trening, wynik-negatywny]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/11-mtp-pl-pilot.md:1-189
status: aktualne
---
# Raport 11: pilot douczania głowicy MTP

**Wynik negatywny (2026-10-16, RunPod A40, $2.14): douczona głowica MTP Qwen3.8-27B na 1.7 M tokenów zmienia tok/krok o ±2% (offline +0.2% w najlepszym przebiegu); fabryczna głowica jest już blisko optimum dla tej skali danych.**

- Bramka offline (held-out on-policy): fabryczna głowica 3.266 tok/krok przy n=4, wyrocznia greedy 3.960 (+21%); PL-proza 3.009 vs 3.812 (+27%) – zapas jest u wyroczni, nie u głowicy.
- Trening FastMTP (K=5, β=0.65, 0.9·TV + 0.1·CE): train1 1.71 M tok −0.2%; train2 tylko on-policy 0.39 M +0.21%; train3 CE +0.02%. Dane off-policy szkodzą (3.281 → 3.235).
- Pomiar na A40 (spec_sweep ABBA): n=4 PL-proza 2.65 → 2.71 (+2.3%), pozostałe klasy 0 do −1.7%; ms/krok bez zmian.
- Pień nietknięty: greedy md5 plain `7f63dec8…` identyczne dla obu plików; bajty poza `blk.64.*` – 0 różnic.
- Głowica w pliku to Q6_K/Q8_0/F32 (351 008 768 B); IQ4_XS powstaje przy ładowaniu i kosztuje ok. −0.45% tok/krok offline.
- Lekcje: w kontenerze RunPod `llama-server` bierze 96 wątków przy limicie 7.65 CPU → `-t 6 -tb 6`; segfault forka z `--spec-mtp-type` i buforami CPU_REPACK (obejście `--no-repack`).
Rekomendacja: nie skalować do 10 M tokenów; test na XTX tylko jako potwierdzenie.

## Powiązane
- [[research/_hub|research]]
- [[raport-10-post-training]]
- [[raport-12-bit-exact]]
- [[2026-10-16-mtp-pl-pilot]]
- [[lekcja-mtp-glowica-optimum]]
- [[glowica-mtp]]
