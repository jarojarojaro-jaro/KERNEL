---
typ: kernel
tags: [kernele, fuzje, qwen]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:221-234; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:87-94,162-163
status: aktualne
---
# Fuzje kroku weryfikacji Qwena (A3–A6)

**Seria fuzji z 2026-10-12, która zmniejszyła liczbę kerneli weryfikacji Qwena z 2156 do 972 i skróciła krok z 41.7 do 36.38 ms.**

**A3–A5 (0012–0014; 6da87d000, a180bea04, 92b14b8b2):**
- A3 (0012): epilog bias/residual ADD w MMVQ wielokolumnowym; bitowy;
- A4 (0013): prolog GATED_DELTA_NET (alpha/beta + softplus/sigmoid w jednym MMVQ, l2-norm q/k w kernelu GDN, stan z cache); **niebitowy**: KLD 0.0067 przy szumie samej bazy 0.0098, PPL 6.182 vs 6.191;
- A5 (0014): concat stanu conv + 5 kopii snapshotów + gather w jednym SSM_CONV; bitowy.
- Kernele weryfikacji 2156 → 1308, przerwy 6.99 → 4.30 ms. Qwen UD 41.7 → 37.71 ms/krok (74.8 → 83.3 t/s), Uncensored 39.6 → 35.83 (78.5 → 85.3).

**A6 (0015–0019; b9db88004..b1f8c19ac), wszystkie bitowe:** producenci piszą q8_1, alpha/beta MMVQ szablon po liczbie tokenów (9.05 → 6.1 µs), IMROPE w fuzji RMS_NORM+MUL+ROPE, FWHT (rotacja KV) w tej samej fuzji, cherry-pick poprawki wyścigu FA #30103 (0018). Kernele 1308 → 972, przerwy 4.30 → 3.23 ms; Qwen 36.38 ms/krok, 86.4 t/s; Uncensored 34.52 ms/krok, 88.5 t/s.

Wyłączniki: brak (build). Kod wspólny CUDA/HIP.

## Powiązane
- [[kernele/_hub|Kernele]]
- [[cache-q8-1]]
- [[gdn-fuzje-k2]]
- [[qwen3-8-27b]]
- [[2026-10-12-fuzje-a3-a6]]
