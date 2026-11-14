---
typ: eksperyment
tags: [eksperymenty, nvidia, rtx-3090, vast, enigma, mtp, dlugi-kontekst]
aktualizacja: 2026-11-09
zrodlo: ~/qwen-opt/cloud/results/nv69q-3090-20261109/ (bench.jsonl, smi.csv, logs/, hw/); kopia w qwen-opt/cloud/nv69q/ (summary.txt, bench.jsonl, skrypty); product/research/69b-tensorfold-qwen-warp.md (Q1)
status: aktualne
---
# qwen-warp v0.8.0 kontra nasz fork CUDA na jednej RTX 3090 (2026-11-09)

**Na tej samej karcie (350 W), tych samych 6 promptach i tym samym kliencie qwen-warp jest ×1.34–×1.81 szybszy od `enigma-cuda-fork` przy każdej głębokości, więc reguła kill (< ×1.15) nie zachodzi: temat portu zostaje. Ok. ×1.24 z tego to lżejsze wagi (W4 g128 wobec UD-Q4_K_XL) [SZACUNEK].**

Warunki: Vast RTX 3090, limit 350 W = domyślny, mediana mocy pod obciążeniem 345 W, AVX2 jest, brak obcych procesów GPU. Fork: opublikowany `llama-kvqleana` (sha256 `b63ec233…`), cudart b12110, UD-Q4_K_XL, flagi z SITE-NVIDIA §4, `-c 262144 -ub 256`. qwen-warp: `689901c`, Swift-1.5 INT4, `--profile long --max-model-len 262144 --vision off` (KV int4 + tablice na hoście, MTP k3 + ogon lookupu). Klient: te same żądania OpenAI ze streamingiem. Parametry: `top_p 0.95, top_k 20, min_p 0, seed 1`, 400 tokenów. t/s = tokeny po pierwszym kawałku / czas od pierwszego do ostatniego kawałka; dla forka zgodne z `timings` co do 0.01. Dokument leży w prompcie systemowym (prefiks z cache), mediana z 6 promptów.

| kontekst | T | fork | qwen-warp | ×  |
|---|---|---|---|---|
| krótki | 0 / 1 | 82.9 / 76.9 | 121.2 / 124.0 | 1.46 / 1.61 |
| 16k | 0 / 1 | 76.8 / 66.7 | 114.0 / 121.0 | 1.48 / 1.81 |
| 64k | 0 / 1 | 69.5 / 63.7 | 110.1 / 101.4 | 1.58 / 1.59 |
| 128k | 0 / 1 | 59.4 / 54.3 | 95.2 / 89.6 | 1.60 / 1.65 |
| 262k | 0 / 1 | 51.1 / 45.1 | 68.3 / 68.6 | 1.34 / 1.52 |

- Powtórka forka (krótki) na końcu sesji: 81.8 / 76.6 (dryf −1.3% / −0.4%). warp z profilem domyślnym (bf16, 20 480): krótki 128.0 / 116.9, 16k 112.8 / 120.1. Deklarowane „155 czat” i „94 przy 262k” to u nas 117–128 i 68.
- Pierwszy kawałek warp ma ~4.8 tokenu, a liczę go jako 1, więc warp jest zawyżony o ≤ 1% (maks. 2.7%).
- Prefill 16k na zimno (TTFT klienta, przebieg 1 / 2): fork 881 / 1087, warp 864 / 1223 t/s. Głęboki prefill 130k → 262k: fork 420, warp 512 t/s.
- Maksymalny kontekst na 24 GB: oba obsłużyły 262 144 (prompt 261 572 + 400 tokenów). Szczyt VRAM: fork 23 726 MiB, warp 23 208 MiB plus 4.7 GiB przypiętej pamięci hosta.
- md5 nieporównywalne (inne wagi i silnik). Swift INT4 to inny model (fine-tune, AWQ+GPTQ), więc jakości nie mierzono.

**Skąd różnica (z czytania kodu).**
1. **Bajty wag:** ~13.2 GB na krok (W4 g128 4.125 b/w + głowica int4) wobec ~16.4 GB (UD-Q4_K_XL to głównie Q5_K/Q6_K, głowica Q6_K), czyli ×1.24 [SZACUNEK]. Port jest tani: lżejszy GGUF (IQ4_XS / Q4_0) + KLD + spec_sweep.
2. **T=1:** warp ma dokładne próbkowanie spekulacyjne na GPU (top-64, int4 + rescoring bf16), więc przy T=1 nie zwalnia, a fork traci 7–13%. Koszt portu średni.
3. **GEMV W4 na rdzeniach tensorowych dla ≤ 8 wierszy weryfikacji** (`gemv.cu`): koszt wysoki. Taniej przejąć upstream PR #31533.
4. **Cały cykl spekulacji jako jeden graf CUDA** (2 cykle na synchronizację hosta): koszt bardzo wysoki, bo trzeba przebudować pętlę serwera.
5. Atencja przy długim kontekście nie jest źródłem przewagi: warp traci −40% między 16k a 262k, fork −33%.

Koszt: $0.53 (różnica kredytu po rozliczeniu; instancja ~85 min × $0.358/h + dysk). Wliczone są: pierwszy host zniszczony po 4 min, bo miał 250 W, a domyślnie 390 (~$0.01), oraz ~42 min bezczynności po końcu łańcucha (~$0.25, zawieszone odpytywanie). Na końcu 0 instancji.

## Powiązane
- [[eksperymenty/_hub|eksperymenty]]
- [[qwen-warp]]
- [[final-recipes-nvidia]]
- [[rtx-3090]]
- [[swift-1-5]]
- [[2026-11-07-kampania-nvidia-vast]]
