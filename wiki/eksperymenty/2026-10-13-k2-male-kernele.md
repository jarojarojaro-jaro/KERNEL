---
typ: eksperyment
tags: [eksperymenty, dpp, fuzje]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:258-274
status: aktualne
---
# 2026-10-13: K2 — małe kernele weryfikacji i draftu

**Seria małych kerneli (para MMVQ, rms_norm i argmax z DPP, fuzje GDN) plus poprawka clamp q8_1: Qwen 33.17 → 32.14 ms/krok (97.8 t/s), bitowo identycznie.**

Gałąź `opt-k2` (ba90baf3a..849b69978), łatki 0023–0028:
- S1 (poprawność, 0023): clamp (d, sum) q8_1 do ±65504; bitowo bez zmian na normalnych danych;
- para MMVQ (0024, `GGML_HIP_MMVQ_PAIR`): ffn up/gate, GDN qkv/z jednym gridem;
- rms_norm·mul(+q8_1), 5120 kolumn (0025): 5.87 → 4.51 µs (wymagał jawnego łańcucha `fmaf`);
- argmax z DPP (0026): 16.8 → 4.3 µs;
- bramkowana norma GDN (0027): 2.68 + 1.84 µs → 1.87 µs;
- SSM_CONV + alpha/beta (0028): 4.68 + 4.90 µs → 5.54 µs.

Wynik: kernele weryfikacji 972 → ~831, przerwy 3.18 → ~2.8 ms. Potwierdzone: Qwen 32.14 ms/krok, 97.8 t/s; Uncensored 30.68 ms/krok, 99.6 t/s (bez CONV_AB Qwen 32.50). Greedy md5 (plain + MTP) równe 9f83f1f81 po każdym kroku.

Zostało z rankingu: set_rows K/V q4_0, FWHT V/wyjścia, rms_norm_mul_rope, GDN 17.7 µs (snapshoty stanu), swiglu, małe k/v MMVQ.

## Powiązane
- [[eksperymenty/_hub|Eksperymenty]]
- [[para-mmvq]]
- [[argmax-dpp]]
- [[gdn-fuzje-k2]]
- [[2026-10-13-k3-host]]
