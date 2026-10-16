---
typ: kernel
tags: [kernele, mmq, prefill]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/research/round6/mmq-epilogue.md:6-61,159-168; ~/KERNEL/qwen-opt/NOTES.md:394-397; ~/KERNEL/qwen-opt/STATUS-NEXT.md:3,31
status: aktualne
---
# Epilog MMQ w parach VOPD (0070)

**Prefill Q4_K/Q5_K na RDNA3: konwersje skal i akumulatora przepisane tak, żeby wszystkie operacje epilogu szły w parach VOPD; +2.2% pp4096 Qwena, bitowo identycznie.**

Skąd pomysł: ablacja rundy 5 pokazała, że ~66% prefillu to vec_dot MMQ (WMMA + epilog skal), a nie ładowania ([[ablacja]]). W bazie `v_fma_mix` i `v_cvt` nie mogą iść w parze (dual-issue).

Zmiana (`opt-mmq6`, ae1ef6a97, scalone jako f61994f58):
- skale x i y rozszerzone raz na krok k01 do f32;
- akumulator WMMA startuje od 0x4B400000, więc `(float)C` to jedno `v_add_f32`;
- tylko dla J ≥ 48 i kerneli bez fallbacku (J=16 tracił, Q5_K J=128 fallback spillował).

Pętla Q4_K J=128: 298 → 243 instrukcji, VALU 237 → 178, LDS bez zmian (3 bloki/WGP). Dowód bitowości w raporcie (iloczyn dwóch f16 dokładny w f32, |C| ≤ 2^19).

GPU 2026-10-15:
- test-backend-ops MUL_MAT 2486/2486, MUL_MAT_ID 933/933;
- logity prefillu (2048 tok., ub 512 i 64) bit w bit dla Qwen i LFM;
- Qwen pp4096 1099.5 → 1123.2 t/s (+2.2%, każda z 3 rund), pp512 +1.9%, LFM pp4096 +0.3%.

Szacunek offline był ~5%. Wyłącznik `GGML_HIP_MMQ_EPI=0` (stare kernele, ISA identyczne).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[prefill-mmq-fa]]
- [[ablacja]]
- [[runda-6]]
- [[rdna3-gfx1100]]
