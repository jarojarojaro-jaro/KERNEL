---
typ: kernel
tags: [kernele, prefill, mmq]
aktualizacja: 2026-10-16
zrodlo: ~/KERNEL/qwen-opt/NOTES.md:320-324; ~/KERNEL/product/research/07-nasze-metody-uogolnienie.md:115-120
status: aktualne
---
# Prefill: kafle MMQ i FA (K5 + T3, 0040–0045)

**Runda prefillu z 2026-10-14: lepszy wybór kafla MMQ, kafel FA bez spilli z bitową kolejnością chunków i lżejsza warstwa MTP dla wierszy promptu.**

| łatka | co | zysk |
|---|---|---|
| 0040 | MMQ RDNA3: węższy kafel, gdy CU stoją (alpha/beta 5120×48 na 4 CU: 932 → 249 ms przy 32k) | pp2048 1059 → 1080 (+2%) |
| 0041 (T3) | warstwa MTP liczy tylko K/V dla wierszy promptu | prefill 6.6k 913 → 936, 29.5k 870 → 897 |
| 0042 | FA MMA D=256: Q w SRAM, bez spilli | 40.2 → 49.0 TFLOPS; FA 32k 4.36 → 3.42 s |
| 0043 | FA MMA: chunki K w kolejności (poprawka numeryki dla 0042) | KLD 0.0135 → 0 |
| 0044 | przypadki wydajnościowe test-backend-ops dla kształtów Qwena | narzędzie |
| 0045 | GDN: normalizacja q/k raz na (głowa, token) | pp2048 1082 → 1108 (+2.4%) |

Prefill serwera (przed → po): Qwen UD 6.6k 913 → 962, 29.5k 870 → 943, 94k 668 → 767 t/s (141 → 123 s); Uncensored 906 → 956, 867 → 941, 666 → 762. Decode bez zmian; KLD vs baza = 0 (te same logity).

Nie zadziałało: prefetch w GDN/FA, inne kafle FA, dequant + hipBLAS dla wszystkich typów (−15%), `-ub 1024`. Wyłączniki: brak (build). 0043 zmienia kolejność akumulacji także na NVIDIA (manifest).

## Powiązane
- [[kernele/_hub|Kernele]]
- [[mmq-epilog]]: kolejny krok prefillu
- [[gdn-fuzje-k2]]
- [[ablacja]]
- [[qwen3-8-27b]]
