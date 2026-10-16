---
typ: kernel
tags: [kernele, poprawnosc, q8-1]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/patches/llama.cpp-amd-opt/0023-*.patch (wiadomość commitu ba90baf3a); ~/KERNEL/qwen-opt/NOTES.md:259,271; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:98,440
status: aktualne
---
# Clamp (d, sum) bloków q8_1 do ±65504 (0023, poprawka)

**Poprawka poprawności (S1): pola d i sum każdego bloku q8_1 są przycinane do zakresu fp16 (±65504) we wszystkich miejscach, które piszą q8_1.**

- Łatka 0023, runda K2 (2026-10-13), oznaczona w NOTES jako S1 (poprawność).
- Gdzie: quantize, MMQ DS4, FA Q i producenci q8_1 z A6.
- Po co (wiadomość commitu): jedna duża aktywacja może wypchnąć sumę bloku (albo amax/127) poza zakres fp16; zapisane inf razy 0 w iloczynach daje NaN. Ten sam defekt co upstream ggml-org/llama.cpp#23606 i Strata #606.
- Testy w commicie: greedy md5 (plain i MTP) = 9f83f1f81; test-backend-ops MUL_MAT 2444/2444, FLASH_ATTN_EXT 4017/4017, RMS_NORM 53/53.
- Wpływ na wynik: bitowo bez zmian na normalnych (skończonych) danych; to nie jest optymalizacja prędkości.
- Wyłącznik: brak (build); w LOO liczona jako „nie-szybkościowa”.
- Raport 07 rekomenduje ją do upstreamu razem z samplerem i łatkami hosta.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[cache-q8-1]]
- [[fuzje-weryfikacji]]
- [[loo]]
- [[seria-amd-opt]]
