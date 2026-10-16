---
typ: latka
tags: [latki, manifest, platformy]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/product/research/patch-manifest.json (_meta i wpisy 0001–0070, policzone 2026-10-16; stat: 193045 B); ~/KERNEL/product/research/08-analiza-platformy-latek.md:5
status: aktualne
---
# Manifest łatek (patch-manifest.json)

**Maszynowy opis każdej z 70 łatek `amd-opt`: gdzie działa, jaka poprawność, jaki zysk i jaki wyłącznik; wynik analizy platformy z 2026-10-15.**

Plik: [patch-manifest.json](../../product/research/patch-manifest.json) (~193 KB). Baza upstream `e60eff95f` (2026-10-09), głowa `amd-opt` @ `f61994f58`. Klucz = numer łatki `0001`…`0070` plus `_meta` (legenda, kolumny, źródła, blokery).

Pola wpisu: `file`, `title`, `backends`, `effective_backend`, `guard`, `os`, `runtime`, `arch`, `model_family`, `env_switch` (zmienne, CLI, kategoria LOO, czy revert czysty), `correctness`, `gain_xtx`, `gain_ms`, `portability`, `evidence`, `notes`.

`portability` ma 19 kolumn (platforma × rodzina GPU) z werdyktem: `works+gain`, `works-neutral`, `excluded`, `unknown-needs-test`. Przykładowe sumy werdyktów:

| kolumna | works+gain | works-neutral | excluded | do testu |
|---|---|---|---|---|
| linux-amd-hip-rdna3 | 56 | 9 | 5 | 0 |
| windows-amd-hip-rdna3 | 14 | 8 | 7 | 41 |
| linux-nvidia-cuda-sm86 | 14 | 7 | 19 | 30 |
| macos-metal-apple | 8 | 8 | 47 | 7 |

Blokery globalne w `_meta`: 0060 dodaje bezwarunkowe `find_package(hsa-runtime64 REQUIRED)` (Windows HIP bez ROCr); `__builtin_popcountll` w testach (0019, 0057) pod MSVC. Jednostki zysku: suma per-łatkowa 14.14 ms/krok Qwena (zmierzone 41.7 → 27.74 = 13.96) i 1.736 ms/token LFM.

## Powiązane
- [[latki/_hub|Łatki]]
- [[seria-amd-opt]]
- [[wylaczniki-env]]
- [[analiza-platformy]]
- raport-08-platforma
