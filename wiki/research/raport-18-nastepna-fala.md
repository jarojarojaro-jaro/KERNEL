---
typ: research
tags: [research, plan, roofline]
aktualizacja: 2026-10-19
zrodlo: ~/KERNEL/product/research/18-nastepna-fala.md:1-604
status: aktualne
---
# Raport 18: następna fala optymalizacji (15 pomysłów, plan 30 dni)

**Roofline w bajtach wag na token nie jest sufitem: Qwen plain ma 57.1 t/s przy 960 GB/s (zmierzone 43.2 = 75.7%), a ten sam silnik daje 109 t/s z MTP i 401 t/s z ogonem lookupu (7× roofline plain); następne mnożniki to więcej tokenów na odczyt wag (wiele strumieni, lookup dla LFM) i mniej bajtów na odczyt (KV w jednym przejściu, 4.25 bpw).**

| # | pomysł | zysk | p | dni | bezstratne |
|---|---|---|---|---|---|
| 1 | ogon lookupu W16 na CUDA | code-edit ×1.8–2.3 | 0.7 | 1 | tak |
| 2 | lookup-spekulacja dla LFM | code-edit ×2.3–2.8 | 0.65 | 2 | tak |
| 3 | oficjalny QAD-Q4_0 LFM na XTX | +9–14% | 0.5 | 1 | nie |
| 4 | serwer wielostrumieniowy (`-np k` + batched MTP/lookup) | rój agentów ×1.6–1.8 | 0.5 | 7 | rozkład tak |
| 5 | `kvq` jedno przejście po KV dla N×G | MTP @94–113k +8%, W16 @64k +12–15% | 0.6 | 5 | bitowo |
| 6 | globalny cache sufiksów ([[suffixdecoding]]) | agent +5–15% | 0.4 | 3 | tak |
| 7 | KV 4-bit z rotacją Hadamarda | LFM @98k +15% | 0.35 | 6 | nie |
| 8 | głowica EAGLE-3 dla LFM | czat +23–37% | 0.3 | 12 | rozkład tak |
| 9 | IQ4_KS (4.25 bpw) dla Qwena | MTP +14% | 0.35 | 7 | nie |
| 10 | block verification przy T>0 | czat T=1 +3–6% | 0.35 | 2 | rozkład tak |
| 11 | d1 draftu MTP w grafie weryfikacji | +2.5–3% | 0.6 | 3 | tak |
| 12 | sufit wzorca + repack wag Qwena | +10% | 0.3 | 8 | bitowo |
| 13 | rzadkość ekspertów LFM (CATS) | +5–10% | 0.25 | 8 | nie |
| 14 | certyfikowana głowica LM ([[knlp-lm-head]]) | Qwen KILL; LFM +5–6% | 0.2 | 5 | tak |
| 15 | prefill Qwena 49% → 65% szczytu WMMA iu8 | agent −8% wall-clock | 0.25 | 10 | tak |

Odrzucone z arytmetyką: TEAL/CATS dla Qwena ([[lekcja-rzadkosc-vs-weryfikacja]]), drzewa draftów dla GDN (V8 − V5 = +10% kroku), MALL ([[lekcja-prefetch-mall-xtx]]), LFM2.5-2.6B jako drafter (1.5 GB/token), self-spec LFM z top-1 ekspertem (57% bajtów celu), stan GDN w bf16 (≤ 1.8%), VOPD w dekodowaniu, podkręcanie/limity mocy (zasada bezpieczeństwa).

Plan 30 dni: GPU ~12–15 h, jedno zadanie naraz pod `flock`, [[gpu-guard]], PM4=0; D1 krzywe V(N) dla obu modeli (bramki #2, #4, #8), dalej #2, #3, #4, #5. NVIDIA (#1) poza planem lokalnym (chmura ~$1–2, zgoda). Notatki: [[2026-10-19-workload-omp]], [[model-kosztu-weryfikacji-moe]], [[2026-10-19-certyfikowana-glowica-pilot]], [[mtplx]].

## Powiązane
- [[research/_hub|research]]
- [[raport-15a-monokernel]]
- [[sufit-pasma-i-mapa-czasu]]
- [[2026-10-19-bezpieczenstwo-sprzetu]]
