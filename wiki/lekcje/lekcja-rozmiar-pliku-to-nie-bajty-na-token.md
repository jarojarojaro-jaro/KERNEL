---
typ: lekcja
tags: [lekcje, pomiar, kwanty, pasmo]
aktualizacja: 2026-11-26
zrodlo: nagłówki safetensors ukisai/Swift-1.5-Qwen3.8-27b-INT4 i GGUF z ~/models (jaroserverai), policzone 2026-11-26; rozmowa 2026-11-26 01:55
status: aktualne
---
# Rozmiar pliku to nie bajty czytane na token

**2026-11-26 napisałem JARO, że qwen-warp „czyta więcej danych na token” (plik 19,47 GB vs nasz 17,66 GB), więc jego przewaga to silnik, nie kwant. Po policzeniu nagłówków było odwrotnie: ciało modelu warpa (MLP + atencja/GDN) to 12,59 GB, naszego UD-Q4_K_XL 15,44 GB (−18%). Plik warpa jest większy przez osadzenia bf16 (2,54 GB, czytany 1 wiersz na token), wizję (0,92 GB) i MTP w bf16, których dekod nie czyta.**

Reguła: zanim porównam „ile czyta” silnik, liczę bajty per kategoria z nagłówków (safetensors: `data_offsets`, GGUF: `n_bytes` per tensor) i sumuję tylko to, co przechodzi przez pasmo na token: ciało warstw + lm_head (+ draft). Rozmiar pliku podaję najwyżej jako ciekawostkę.

## Powiązane
- [[lekcje/_hub|lekcje]]
- [[qwen-warp]]
