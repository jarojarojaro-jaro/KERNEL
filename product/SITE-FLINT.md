# Flint na stronę — co dodać (dla sesji od enigmalabz.com)

Źródło wszystkich liczb: `product/research/59-flint.md` (sekcje „RTX 3090”, „RTX 3090 — pełna macierz”, „XTX”) i surowe dane
`~/qwen-opt/cloud/results/flint-3090-matrix-20261021/matrix.json`, `~/qwen-opt/flint/results/xtx/{base,now}/lb.jsonl`.
Zasady strony: tylko mierzone liczby; wiersz VS tylko gdy obie karty mają wartość; format **baseline → nasze → przyrost**.

## Model (nowy wpis)
- Nazwa: **Recursive Flint** (40B MoE, ~2,5B aktywnych), licencja Apache 2.0, wydany 2026-10-21.
- Kwant: oficjalny **NVFP4** (`RecursiveSI/flint-nvfp4-gguf`, 22,9 GB, trenowany pod kwantyzację), KV cache **q4_0**.
- Baseline = llama.cpp upstream z obsługą Flinta (PR #30928 + poprawka szablonu #30929). Nasze = + nasze poprawki kerneli.

## RTX 3090 (pełna macierz, llama-bench, FA on, KV q4_0, ub 1024; host z dławieniem termicznym → pokazujemy przyrost, nie rekordy)
| Kontekst | Generacja t/s | Prefill 2048 t/s |
|---|---|---|
| 0 | 110,1 → 126,8 (+15%) | ~bez zmian (kontrola w odwrotnej kolejności +0,9%) |
| 4 096 | 90,9 → 104,2 (+15%) | 2267 → 2116 (kolejność/termika; nie pokazywać jako spadek) |
| 16 384 | 79,3 → 89,0 (+12%) | 1686 → 1665 (0%) |
| 32 768 | 67,5 → 69,7 (+3%) | 1375 → 1372 (0%) |
| 65 536 | 42,2 → 42,1 (0%) | 1026 → 1040 (+1%) |
| 160 000 | 21,0 → 20,9 (0%) | 610 → 612 (0%) |
- Serwer e2e, prompt 8k: generacja 79,6 → 90,1 t/s (+13%), TTFT 4,1 s → 4,1 s.
- Maks. kontekst KV q4_0: **200k** (ub 1024, wolne 161 MiB), 235k (ub 512, z pierwszej 3090).
- Pierwsza (chłodna) 3090: generacja przy krótkim kontekście 130 → 147 t/s (+13%).

## RX 7900 XTX — TYLKO krótki/średni kontekst (długi kontekst NIE do publikacji: test igły 150k nierozstrzygnięty)
| Kontekst | Generacja t/s | Prefill 2048 t/s |
|---|---|---|
| 0 | 92,8 → 174,7 (+88%) | 3229 → 3687 (+14%) |
| 16 384 | 83,5 → 166,5 (+99%) | 2545 → 2855 (+12%) |
- Serwer e2e, prompt 8k: generacja 83,4 → 148,1 t/s, TTFT bez zmian.
- Część zysku przy krótkim kontekście to PM4 (smoke: 113,7 t/s bez PM4, 163,5 z PM4).
- Poprawność potwierdzona: czat, wywołanie narzędzia, druga tura po narzędziu.

## VS (3090 vs XTX) — tylko wiersze, które obie karty mają z tego samego harnessu
- Generacja przy kontekście 0 i 16k (llama-bench, ub 1024, KV q4_0): 3090 126,8 / 89,0 vs XTX 174,7 / 166,5 t/s.
- Uwaga: hosty 3090 różne (dławienie) — opisać jako „pomiar na wynajętej 3090”.
