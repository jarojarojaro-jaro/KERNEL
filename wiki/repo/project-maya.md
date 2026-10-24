---
typ: repo
tags: [repo, konkurencja, moe]
aktualizacja: 2026-10-24
zrodlo: ~/KERNEL/product/research/21g-nowe-silniki.md:158-216; ~/KERNEL/product/research/21g-notatki/maya.md; https://github.com/mw00/project-maya (`a4e1ff0`, v1.1.15; `f26d8ba`, v1.1.26); ~/KERNEL/product/research/32a-maya-1117-strata-020-gyro.md:14-20; ~/KERNEL/product/research/39a-maya-1119.md:14-30; ~/KERNEL/product/research/60d-serving-kernels-cache.md:196-213,232-239
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

## Aktualizacja 2026-10-24 (v1.1.21–1.1.26, tylko DeepSeek `maya-ds4`)
- Prefill AMD 2.35–2.53× (Strix Halo, v1.1.21): sparse attention na `wmma_f32_16x16x16_bf16_w32` z Q/P rozbitym na BF16 hi+lo (~16 bitów mantysy), dense GEMM przez hipBLASLt z wyborem per kształt. RDNA4 (#370): 1.16–1.40×. RTX 3090 MMA (#369): prefill ~30K 957–992 → 1104–1234 tok/s.
- v1.1.26: `DS4_FAT_ROWS` (gorący ekspert raz do FP16 + cuBLAS) 1.3–1.56× prefillu na 3× V100; dokładny softmax FP32 na `wmma` dla Volta/Turing.
- v1.1.22: TP bez P2P (copy engine → pinned host, `allreduce_dma`), 9 GPU PCIe 3.0: dekod 42.9 → 66.8 t/s; drafting 8.5 → 15.9 t/s (strumienie HIP).
- **2× RX 7900 XTX (#382):** jeden launch kwantyzacji q8 zamiast wielu: 12.5 vs 13.1 t/s, bez zysku (gap 3.3 µs, praca ~2 µs). v1.1.25: sesje przeżywają restart (`MAYA_DS4_SLOT_KEEP=1`).
- Dla Qwen3.8/gfx1100 nic do wzięcia ([[raport-60d-serving-kernels-cache]]).

## Powiązane
- [[repo/_hub|repo]]
- [[strata]]
- [[raport-21g-nowe-silniki]]
- [[lekcja-bit-exact-wobec-siebie]]
