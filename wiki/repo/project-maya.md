---
typ: repo
tags: [repo, konkurencja, moe]
aktualizacja: 2026-10-21
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:158-216; ~/KERNEL/product/research/21g-notatki/maya.md; https://github.com/mw00/project-maya (`a4e1ff0`, v1.1.15); ~/KERNEL/product/research/32a-maya-1117-strata-020-gyro.md:14-20; ~/KERNEL/product/research/39a-maya-1119.md:14-30
status: aktualne
---
# Project Maya (mw00): silnik jednego modelu GLM-5.3-Flash

**Pochodna Straty (nie fork llama.cpp) uruchamiająca tylko GLM-5.3-Flash (321B, 18B aktywnych) z ekspertami w trzech warstwach VRAM → przypięty RAM → NVMe (O_DIRECT); 81 t/s na RTX PRO 6000 = 41% pasma; liczby z README to najlepsze wiersze z różnych wersji, bez llama.cpp (raport 21g, 2026-10-19).**

- Jakość: „97.7–99.2% dokładności FP8” to marketing (5 testów MC po 400 pytań); uczciwie KL Maya-S 0.428 / top-1 83.3%, Maya-L 0.188 / 90.0% – poziom ~q2_K.
- Determinizm: domyślnie tylko 17/70 par restartów daje identyczne tokeny, v1.1.13 i v1.1.15 zmieniły domyślne tokeny.
- v1.1.14 Pascal: `-Xptxas -dlcm=ca`, P40 dekod ×1.7–3.0; P100 (sm_60) najpewniej się nie kompiluje (`__dp4a` wymaga CC 6.1) `[INFERENCE]`; nowy typ ekspertów Q6_K_XL/Q8_0.
- Przypina cały RAM poza 6 GB; buduje się 20–40 min ze źródeł; XTX eksperymentalnie, niezmierzony; polskiego brak.
- Do skopiowania: pętla społeczności `--bench` → `--report` → issue → README, rozgrzewka cache ekspertów z profilu (+15% na świeżym starcie), kalibracja MTP/DFlash2 per maszyna.

## Aktualizacja 2026-10-21
- v1.1.17: bez nowych kerneli ([[raport-32a-maya-strata-gyro]]); v1.1.19: #318 pomija martwe obliczenia DeepSeek, nie przenosi się na Qwen3.8; rozgrzewka przed READY (#285) ([[raport-39a-maya-1119]]).

## Powiązane
- [[repo/_hub|repo]]
- [[strata]]
- [[raport-21g-nowe-silniki]]
- [[lekcja-bit-exact-wobec-siebie]]
